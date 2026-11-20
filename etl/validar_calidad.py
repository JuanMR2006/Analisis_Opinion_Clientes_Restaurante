"""Validación INDEPENDIENTE del ETL: ¿quedaron bien los datos limpios?

No importa nada de los pipelines: relee los parquet de datos_limpios/ y los CSV CRUDOS de datasets/ con
pandas y recalcula por su cuenta (para no "corregirse la tarea a sí mismo"). Cada prueba imprime PASA o FALLA;
si alguna falla termina con código 1 (compuerta antes de cargar a Power BI).

    Completitud ........ sin nulos en obligatorias; leídas = válidas + rechazadas; todo rechazo tiene motivo
    Validez ............ rangos de dominio y categorías permitidas
    Unicidad ........... llaves primarias sin repetir
    Integridad ref. .... toda FK existe en su dimensión (sin huérfanas)
    Consistencia ....... Sentimiento coherente con rating; calendario continuo; derivadas coherentes
    Exactitud .......... agregados recalculados DESDE EL CRUDO y comparados con el resultado
    Base de datos ...... el .db SQLite tiene las mismas tablas y filas, sin huérfanos y sin corrupción

Uso:   python etl/validar_calidad.py
"""
import json
import re
import sqlite3
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parent.parent
LIMPIOS = RAIZ / "datos_limpios"
RECHAZADOS = RAIZ / "rechazados"
BASE_DATOS = RAIZ / "base_datos" / "opiniones_restaurantes.db"
CRUDO_ENC = RAIZ / "datasets" / "dataset_raw.csv"
CRUDO_RES = RAIZ / "datasets" / "gijon_resenas_es_2017_2023.csv"
CRUDO_UBI = RAIZ / "datasets" / "gijon_ubicacion_clientes.csv"
TIPOS_ORIGEN = {"Gijón (local)": 1, "Resto de Asturias": 2, "Resto de España": 3, "Extranjero": 4,
                "No determinado": 5, "Sin dato": 6}
TOL = 1e-6

resultados = []


def prueba(dimension, nombre, ok, detalle=""):
    ok = bool(ok)
    resultados.append((dimension, nombre, ok, detalle))
    print(f"[{'PASA' if ok else 'FALLA'}] {dimension:16s} {nombre}" + (f"  ({detalle})" if detalle else ""))


def leer(nombre):
    return pd.read_parquet(LIMPIOS / "parquet" / f"{nombre}.parquet")


def main():
    nombres = ["Fact_Encuesta", "Dim_Cocina_Preferida", "Dim_Ocasion", "Dim_Franja_Visita", "Dim_Frecuencia_Visita",
               "Fact_Resenas", "Dim_Restaurante", "Dim_Fecha", "Dim_Origen_Cliente", "Fact_Palabras"]
    t = {n: leer(n) for n in nombres}
    m = json.loads((LIMPIOS / "metricas_etl.json").read_text("utf-8"))["metricas"]
    enc, res, rest, cal = t["Fact_Encuesta"], t["Fact_Resenas"], t["Dim_Restaurante"], t["Dim_Fecha"]
    org, pal = t["Dim_Origen_Cliente"], t["Fact_Palabras"]
    res["Fecha"] = pd.to_datetime(res["Fecha"])
    cal["Fecha"] = pd.to_datetime(cal["Fecha"])
    crudo_enc = pd.read_csv(CRUDO_ENC, dtype=str, keep_default_na=False)
    crudo_res = pd.read_csv(CRUDO_RES, dtype=str, keep_default_na=False)
    crudo_ubi = pd.read_csv(CRUDO_UBI, dtype=str, keep_default_na=False)

    # ------------------------------------------------------------------ COMPLETITUD
    # Columnas que pueden tener nulos por decisión documentada (R19/R20, título opcional)
    opcionales = {"Dim_Restaurante": {"Precio_Original", "Nivel_Precio", "Cocinas_Original"},
                  "Fact_Resenas": {"Titulo"}}
    for n, df in t.items():
        cols = [c for c in df.columns if c not in opcionales.get(n, set())]
        nulos = int(df[cols].isna().sum().sum())
        prueba("Completitud", f"{n}: sin nulos en columnas obligatorias", nulos == 0, f"{nulos} nulos")

    for fuente, crudo, fact in (("encuesta", crudo_enc, enc), ("resenas", crudo_res, res)):
        rech = pd.read_csv(RECHAZADOS / f"{fuente}_rechazados.csv", dtype=str, keep_default_na=False)
        prueba("Completitud", f"{fuente}: leídas (crudo) = válidas + rechazadas", len(crudo) == len(fact) + len(rech),
               f"{len(crudo):,} = {len(fact):,} + {len(rech):,}")
        prueba("Completitud", f"{fuente}: el ETL leyó todas las filas del crudo",
               m[f"{fuente}_filas_leidas"] == len(crudo), f"{m[f'{fuente}_filas_leidas']:,} vs {len(crudo):,}")
        prueba("Completitud", f"{fuente}: toda fila rechazada tiene Motivo y Codigo_Regla",
               (rech["Motivo"].str.strip() != "").all() and (rech["Codigo_Regla"].str.strip() != "").all(),
               f"{len(rech)} rechazadas")
    # Nulos de precio/cocina: deben coincidir con el crudo y tener etiqueta "Sin dato" (no imputados)
    sin_precio = rest["Nivel_Precio"].isna()
    prueba("Completitud", "Restaurantes sin precio etiquetados 'Sin dato' (no imputados)",
           (rest.loc[sin_precio, "Precio_Etiqueta"] == "Sin dato").all() and rest.loc[sin_precio, "Precio_Original"].isna().all(),
           f"{int(sin_precio.sum())} restaurantes")

    # ------------------------------------------------------------------ VALIDEZ
    prueba("Validez", "Encuesta: edad 18-100", enc["Edad"].between(18, 100).all(), f"{enc['Edad'].min()}-{enc['Edad'].max()}")
    prueba("Validez", "Encuesta: calificaciones enteras 1-5",
           all(enc[c].between(1, 5).all() and pd.api.types.is_integer_dtype(enc[c])
               for c in ["Calif_Servicio", "Calif_Comida", "Calif_Ambiente"]))
    prueba("Validez", "Encuesta: espera 0-240 min, grupo 1-30, ingreso y gasto > 0",
           enc["Tiempo_Espera_Min"].between(0, 240).all() and enc["Tamano_Grupo"].between(1, 30).all()
           and (enc["Ingreso"] > 0).all() and (enc["Gasto_Promedio"] > 0).all())
    prueba("Validez", "Encuesta: banderas binarias 0/1",
           all(enc[c].isin([0, 1]).all() for c in ["Reserva_Online", "Pedido_Domicilio", "Miembro_Lealtad", "Alta_Satisfaccion"]))
    permitidas = {"Genero": {"Male", "Female"}, "Frecuencia_Visita": {"Daily", "Weekly", "Monthly", "Rarely"},
                  "Tipo_Comida": {"Dine-in", "Takeaway"}}
    prueba("Validez", "Encuesta: categorías dentro del conjunto permitido",
           all(enc[c].isin(v).all() for c, v in permitidas.items()))
    prueba("Validez", "Reseñas: rating entero 1-5",
           pd.api.types.is_integer_dtype(res["Rating"]) and res["Rating"].between(1, 5).all())
    prueba("Validez", "Reseñas: fechas dentro de 2017-2023", res["Fecha"].dt.year.between(2017, 2023).all(),
           f"{res['Fecha'].min().date()} a {res['Fecha'].max().date()}")
    prueba("Validez", "Reseñas: idioma 'es' y texto no vacío",
           (res["Idioma"] == "es").all() and (res["Texto"].str.strip().str.len() > 0).all())
    prueba("Validez", "Reseñas: sin caracteres de reemplazo U+FFFD (UTF-8 correcto)",
           not res["Texto"].str.contains("�").any())
    prueba("Validez", "Restaurante: Nivel_Precio en {1,2,3} o nulo; promedio TripAdvisor 1-5",
           rest["Nivel_Precio"].dropna().isin([1, 2, 3]).all() and rest["Rating_Promedio_TripAdvisor"].between(1, 5).all())
    prueba("Validez", "Origen: Tipo_Origen dentro de las 6 categorías y Tipo_Origen_Orden coherente",
           org["Tipo_Origen"].isin(TIPOS_ORIGEN).all() and (org["Tipo_Origen"].map(TIPOS_ORIGEN) == org["Tipo_Origen_Orden"]).all())
    prueba("Validez", "Palabras clave: solo letras en minúsculas, mínimo 3, a lo sumo 200 distintas",
           pal["Palabra"].str.fullmatch(r"[a-záéíóúüñ]{3,}").all() and pal["Palabra"].nunique() <= 200,
           f"{pal['Palabra'].nunique()} palabras distintas")
    ext = org["Tipo_Origen"] == "Extranjero"
    prueba("Validez", "Origen: país extranjero <-> región 'Extranjero'; España <-> tipos locales/España",
           (org.loc[ext, "Pais_Cliente"] != "España").all() and (org.loc[ext, "Region_Cliente"] == "Extranjero").all()
           and (org.loc[org["Tipo_Origen"].isin(["Gijón (local)", "Resto de Asturias", "Resto de España"]), "Pais_Cliente"] == "España").all())

    # ------------------------------------------------------------------ UNICIDAD
    pks = {"Fact_Encuesta": "ID_Cliente", "Dim_Cocina_Preferida": "Cocina_Preferida", "Dim_Ocasion": "Ocasion",
           "Dim_Franja_Visita": "Franja_Visita", "Dim_Frecuencia_Visita": "Frecuencia_Visita",
           "Fact_Resenas": "Review_ID", "Dim_Restaurante": "Restaurant_ID", "Dim_Fecha": "Fecha",
           "Dim_Origen_Cliente": "Origen_ID"}
    for n, pk in pks.items():
        dup = int(t[n][pk].duplicated().sum())
        prueba("Unicidad", f"{n}: llave {pk} sin repetir", dup == 0, f"{dup} repetidas")
    dup = int(pal.duplicated(["Review_ID", "Palabra"]).sum())
    prueba("Unicidad", "Fact_Palabras: cada palabra cuenta una sola vez por reseña", dup == 0, f"{dup} repetidas")
    dup = int(org.duplicated(["Tipo_Origen", "Pais_Cliente", "Region_Cliente", "Ciudad_Cliente"]).sum())
    prueba("Unicidad", "Dim_Origen_Cliente: una fila por tipo + país + región + ciudad", dup == 0, f"{dup} repetidas")
    prueba("Unicidad", "IDs como entero (no decimal)",
           all(pd.api.types.is_integer_dtype(df[c]) for df, c in
               ((enc, "ID_Cliente"), (res, "Review_ID"), (res, "Restaurant_ID"), (rest, "Restaurant_ID"))))

    # ------------------------------------------------------------------ INTEGRIDAD REFERENCIAL
    fks = [("Fact_Resenas", "Restaurant_ID", "Dim_Restaurante", "Restaurant_ID"),
           ("Fact_Resenas", "Origen_ID", "Dim_Origen_Cliente", "Origen_ID"),
           ("Fact_Palabras", "Review_ID", "Fact_Resenas", "Review_ID"),
           ("Fact_Resenas", "Fecha", "Dim_Fecha", "Fecha"),
           ("Fact_Encuesta", "Cocina_Preferida", "Dim_Cocina_Preferida", "Cocina_Preferida"),
           ("Fact_Encuesta", "Ocasion", "Dim_Ocasion", "Ocasion"),
           ("Fact_Encuesta", "Franja_Visita", "Dim_Franja_Visita", "Franja_Visita"),
           ("Fact_Encuesta", "Frecuencia_Visita", "Dim_Frecuencia_Visita", "Frecuencia_Visita")]
    for hija, fk, padre, pk in fks:
        huerfanas = int((~t[hija][fk].isin(t[padre][pk])).sum())
        prueba("Integridad ref.", f"{hija}.{fk} -> {padre}.{pk}", huerfanas == 0, f"{huerfanas} huérfanas")
    sin_resenas = int((~rest["Restaurant_ID"].isin(res["Restaurant_ID"])).sum())
    prueba("Integridad ref.", "Todo restaurante de la dimensión tiene al menos una reseña", sin_resenas == 0,
           f"{sin_resenas} sin reseñas")
    prueba("Integridad ref.", "Archivo de ubicaciones: exactamente una fila por reseña del crudo",
           len(crudo_ubi) == len(crudo_res) and not crudo_ubi["review_id"].duplicated().any()
           and set(crudo_ubi["review_id"]) == set(crudo_res["review_id"]), f"{len(crudo_ubi):,} filas")

    # ------------------------------------------------------------------ CONSISTENCIA
    esperado = res["Rating"].map({1: "Negativo", 2: "Negativo", 3: "Neutro", 4: "Positivo", 5: "Positivo"})
    prueba("Consistencia", "Sentimiento coherente con rating (1-2 Neg, 3 Neu, 4-5 Pos)", (esperado == res["Sentimiento"]).all())
    f = cal["Fecha"].sort_values()
    prueba("Consistencia", "Dim_Fecha: calendario continuo de años completos (2017-01-01 a 2023-12-31)",
           (f.diff().dropna() == pd.Timedelta(days=1)).all() and str(f.iloc[0].date()) == "2017-01-01"
           and str(f.iloc[-1].date()) == "2023-12-31", f"{len(cal):,} días")
    prueba("Consistencia", "Dim_Fecha: Anio_Mes, Trimestre y Semestre coherentes con la fecha",
           (cal["Anio_Mes"] == cal["Fecha"].dt.strftime("%Y-%m")).all() and (cal["Trimestre"] == cal["Fecha"].dt.quarter).all()
           and (cal["Semestre"] == (cal["Mes"] > 6) + 1).all())
    prueba("Consistencia", "Encuesta: Calif_Promedio = media de las 3 calificaciones",
           ((enc[["Calif_Servicio", "Calif_Comida", "Calif_Ambiente"]].mean(axis=1) - enc["Calif_Promedio"]).abs() < 1e-3).all())
    cnt = res.groupby("Restaurant_ID").size()
    prueba("Consistencia", "Dim_Restaurante.Num_Resenas = conteo real en Fact_Resenas",
           (rest.set_index("Restaurant_ID")["Num_Resenas"] == cnt.reindex(rest["Restaurant_ID"]).values).all())
    cnt_o = res.groupby("Origen_ID").size()
    prueba("Consistencia", "Dim_Origen_Cliente.Num_Resenas = conteo real en Fact_Resenas",
           (org.set_index("Origen_ID")["Num_Resenas"] == cnt_o.reindex(org["Origen_ID"]).values).all())
    precio_map = {"$": 1, "$$ - $$$": 2, "$$$$": 3}
    prueba("Consistencia", "Nivel_Precio coherente con price_interval original",
           (rest["Precio_Original"].map(precio_map).astype("Int64").fillna(-1) == rest["Nivel_Precio"].fillna(-1)).all())

    # ------------------------------------------------------------------ EXACTITUD (recalculado desde el CRUDO)
    cr = crudo_res.copy()
    cr["r"] = cr["rating"].astype(float)
    ref = cr.groupby(cr["restaurant_id"].astype("int64"))["r"].mean()
    comp = rest.set_index("Restaurant_ID")["Rating_Promedio_Resenas"]
    peor = (ref.reindex(comp.index) - comp).abs().max()
    prueba("Exactitud", "Promedio de rating por restaurante = recalculado desde el crudo", peor < 1e-3,
           f"máxima diferencia {peor:.6f} en {len(comp)} restaurantes")
    por_anio_crudo = cr.groupby(cr["review_date"].str[:4].astype(int)).size()
    por_anio = res.groupby(res["Fecha"].dt.year).size()
    prueba("Exactitud", "Reseñas por año = conteo desde el crudo", por_anio.equals(por_anio_crudo), por_anio.to_dict())
    ce = crudo_enc
    prueba("Exactitud", "Encuesta: promedio FoodRating y % HighSatisfaction = crudo",
           abs(ce["FoodRating"].astype(float).mean() - enc["Calif_Comida"].mean()) < TOL
           and abs(ce["HighSatisfaction"].astype(float).mean() - enc["Alta_Satisfaccion"].mean()) < TOL,
           f"{enc['Calif_Comida'].mean():.4f} / {enc['Alta_Satisfaccion'].mean():.2%}")
    prueba("Exactitud", "Gasto promedio total de la encuesta = crudo",
           abs(ce["AverageSpend"].astype(float).sum() - enc["Gasto_Promedio"].sum()) < 0.01 * len(enc))
    # La palabra más frecuente: cuántas reseñas del CRUDO la contienen como palabra suelta = filas en Fact_Palabras
    top = pal["Palabra"].value_counts()
    palabra, n_tabla = top.index[0], int(top.iloc[0])
    patron = re.compile(r"[a-záéíóúüñ]+")
    n_crudo = int(cr["text"].map(lambda x: palabra in set(patron.findall(x.lower()))).sum())
    prueba("Exactitud", "Palabra clave más frecuente: reseñas que la contienen = recalculado desde el crudo",
           n_tabla == n_crudo, f"'{palabra}': {n_tabla:,} vs {n_crudo:,}")
    # 'Sin dato' debe ser EXACTAMENTE las reseñas cuya ubicación cruda está vacía (no se imputó nada)
    vacias = set(crudo_ubi.loc[crudo_ubi["user_location"].str.strip() == "", "review_id"].astype("int64"))
    sin_dato = set(res.merge(org, on="Origen_ID").query("Tipo_Origen == 'Sin dato'")["Review_ID"])
    prueba("Exactitud", "Origen 'Sin dato' = reseñas con ubicación vacía en el crudo (nada imputado)",
           vacias == sin_dato, f"{len(sin_dato):,} reseñas")

    # ------------------------------------------------------------------ BASE DE DATOS (SQLite)
    prueba("Base de datos", "Existe base_datos/opiniones_restaurantes.db", BASE_DATOS.exists())
    if BASE_DATOS.exists():
        con = sqlite3.connect(BASE_DATOS)
        try:
            prueba("Base de datos", "Integridad del archivo (PRAGMA integrity_check = ok)",
                   con.execute("PRAGMA integrity_check").fetchone()[0] == "ok")
            en_db = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            prueba("Base de datos", "Tiene las 10 tablas del modelo y la bitácora de reglas",
                   set(nombres) | {"Bitacora_Reglas"} <= en_db, f"{len(en_db)} tablas")
            filas = {n: con.execute(f'SELECT COUNT(*) FROM "{n}"').fetchone()[0] for n in nombres if n in en_db}
            distintas = {n: (filas.get(n), len(t[n])) for n in nombres if filas.get(n) != len(t[n])}
            prueba("Base de datos", "Mismas filas en la base que en datos_limpios/ (tabla por tabla)",
                   not distintas, distintas or f"{sum(filas.values()):,} filas")
            huerfanos = con.execute("PRAGMA foreign_key_check").fetchall()
            prueba("Base de datos", "Llaves foráneas sin huérfanos (PRAGMA foreign_key_check)", not huerfanos,
                   f"{len(huerfanos)} huérfanos")
            r_db = con.execute("SELECT AVG(Rating), SUM(Rating <= 2) FROM Fact_Resenas").fetchone()
            prueba("Base de datos", "Rating promedio y reseñas negativas por SQL = datos_limpios/",
                   abs(r_db[0] - res["Rating"].mean()) < TOL and r_db[1] == int((res["Rating"] <= 2).sum()),
                   f"{r_db[0]:.4f} / {r_db[1]:,}")
        finally:
            con.close()

    # ------------------------------------------------------------------ RESUMEN
    fallas = [r for r in resultados if not r[2]]
    lineas = ["# Reporte de validación", "", "Generado por `etl/validar_calidad.py` (independiente del ETL).", "",
              f"Pruebas: {len(resultados)} | Pasan: {len(resultados) - len(fallas)} | Fallan: {len(fallas)}", "",
              "| Resultado | Dimensión | Prueba | Detalle |", "|---|---|---|---|"]
    lineas += [f"| {'PASA' if ok else '**FALLA**'} | {dim} | {nom} | {det} |" for dim, nom, ok, det in resultados]
    (LIMPIOS / "reporte_validacion.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"\n{len(resultados) - len(fallas)}/{len(resultados)} pruebas pasan. Detalle en datos_limpios/reporte_validacion.md")
    sys.exit(1 if fallas else 0)


if __name__ == "__main__":
    main()
