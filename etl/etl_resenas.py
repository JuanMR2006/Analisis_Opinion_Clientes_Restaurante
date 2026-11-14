"""Pipeline 2: reseñas de TripAdvisor (Gijón, español, 2017-2023) -> modelo estrella.

    Fact_Resenas        una fila por reseña (grano: review_id)
    Dim_Restaurante     una fila por restaurante (grano: restaurant_id)
    Dim_Fecha           calendario continuo 2017-01-01 .. 2023-12-31 (una fila por día)
    Dim_Origen_Cliente  una fila por origen normalizado del autor (ciudad, región, país, tipo de origen)

Reglas R01..R27. Igual que en la encuesta: lo inválido se ELIMINA a cuarentena con su motivo, nada se imputa.
"""
import re
import unicodedata

import pandas as pd

import config
import ubicaciones as cat
from utilidades import (a_nulo, a_numero, exigir_columnas, fuera_de, leer_csv_texto, no_es_entero,
                        no_es_numero, perfil_nulos)

FUENTE = "Resenas"


def procesar(bit, cua):
    print(f"\n== {FUENTE}: {config.ARCHIVO_RESENAS.name}")

    # ---------------------------------------------------------------- EXTRACT
    crudo = leer_csv_texto(config.ARCHIVO_RESENAS)     # falla aquí si el archivo no es UTF-8 válido
    exigir_columnas(crudo, config.COLUMNAS_RESENAS, FUENTE)
    leidas = len(crudo)
    bit.metrica("resenas_filas_leidas", leidas)
    print(f"  filas leídas: {leidas:,}")

    # ---------------------------------------------------------------- NORMALIZACIÓN
    df = crudo[config.COLUMNAS_RESENAS].copy()
    for c in df.columns:
        df[c] = a_nulo(df[c], texto_libre=c in config.TEXTO_LIBRE)
    bit.registrar(FUENTE, "R00", "Validez",
                  "Normalización: trim + marcas de nulo ('', NA, ?, -) en columnas estructuradas "
                  f"(texto libre solo ''); nulos resultantes", "Transformar", int(df.isna().sum().sum()))

    def rechazar(mascara, codigo, regla, dimension):
        nonlocal df
        df = cua.rechazar(df, mascara, crudo, FUENTE, codigo, regla, dimension, bit)

    # R01 Completitud: perfil de nulos (price_interval ~2,7 % y cuisine_types ~1,5 %: bajo el umbral)
    altas = perfil_nulos(df, df.columns, FUENTE, "R01", bit)
    if altas:
        bit.decision(FUENTE, f"Columnas con > 20 % de nulos: {altas}")

    # R02-R03 Completitud/Validez del identificador (grano de la tabla de hechos)
    rechazar(df["review_id"].isna(), "R02", "review_id nulo", "Completitud")
    rid = a_numero(df["review_id"])
    rechazar(no_es_numero(df["review_id"], rid) | no_es_entero(rid) | (rid <= 0),
             "R03", "review_id no es un entero positivo", "Validez")

    # R04 Unicidad: duplicado exacto -> se conserva la primera aparición
    rechazar(df.duplicated(keep="first"), "R04", "Reseña duplicada exacta (se conserva la primera)", "Unicidad")
    # R05 Unicidad: mismo review_id con contenido distinto -> todas las versiones A INVESTIGAR
    rechazar(df["review_id"].duplicated(keep=False), "R05",
             "review_id repetido con contenido distinto - A INVESTIGAR", "Unicidad")

    # R06 Completitud: campos obligatorios. price_interval y cuisine_types NO son obligatorios
    # (son atributos del restaurante, no de la reseña; ver R19-R20). title tampoco (la opinión está en text).
    obligatorias = ["restaurant_id", "restaurant_name", "city", "cuisine_match_encuesta", "restaurant_avg_rating",
                    "review_date", "year_month", "rating", "text", "language"]
    rechazar(df[obligatorias].isna().any(axis=1), "R06",
             "Campo obligatorio nulo (id restaurante, fecha, rating, texto...)", "Completitud")

    rest = a_numero(df["restaurant_id"])
    rechazar(no_es_numero(df["restaurant_id"], rest) | no_es_entero(rest) | (rest <= 0),
             "R07", "restaurant_id no es un entero positivo", "Validez")

    # R08-R10 Fechas: formato EXPLÍCITO (nunca adivinar día/mes), coherencia con year_month y periodo
    fecha = pd.to_datetime(df["review_date"], format=config.FORMATO_FECHA, errors="coerce")
    rechazar(fecha.isna(), "R08", "review_date no cumple el formato AAAA-MM-DD", "Validez")
    fecha = fecha.loc[df.index]
    rechazar(fecha.dt.strftime(config.FORMATO_ANIO_MES) != df["year_month"], "R09",
             "year_month no coincide con review_date", "Consistencia")
    fecha = fecha.loc[df.index]
    rechazar((fecha.dt.year < config.ANIO_INICIO) | (fecha.dt.year > config.ANIO_FIN), "R10",
             f"Fecha fuera del periodo {config.ANIO_INICIO}-{config.ANIO_FIN}", "Validez")

    # R11-R12 rating: viene como '5.0' (decimal) pero la escala es entera 1-5
    rating = a_numero(df["rating"])
    rechazar(no_es_numero(df["rating"], rating) | no_es_entero(rating), "R11",
             "rating no numérico o con decimales (la escala es entera)", "Validez")
    rechazar(fuera_de(a_numero(df["rating"]), config.RANGO_RATING), "R12", "rating fuera de 1-5", "Validez")

    # R13 promedio del restaurante en TripAdvisor: 1-5 en pasos de 0,5
    prom = a_numero(df["restaurant_avg_rating"])
    rechazar(prom.isna() | fuera_de(prom, config.RANGO_RATING_RESTAURANTE) | ((prom * 2) % 1 != 0),
             "R13", "restaurant_avg_rating fuera de 1-5 o no múltiplo de 0,5", "Validez")

    # R14-R15 Alcance del dataset: solo español y solo Gijón
    rechazar(df["language"] != config.IDIOMA_ESPERADO, "R14", "Idioma distinto de 'es'", "Validez")
    rechazar(df["city"] != config.CIUDAD_ESPERADA, "R15", "Ciudad distinta de Gijon", "Validez")

    # R16-R17 Categorías contra conjunto permitido (los nulos de price_interval se tratan en R19)
    rechazar(df["price_interval"].notna() & ~df["price_interval"].isin(config.NIVEL_PRECIO), "R16",
             "price_interval fuera de {$, $$ - $$$, $$$$}", "Validez")
    rechazar(~df["cuisine_match_encuesta"].isin(config.CATEGORIAS_COCINA_ENCUESTA), "R17",
             "cuisine_match_encuesta fuera de las 8 categorías conocidas", "Validez")

    # R18 Consistencia: un restaurante debe tener los MISMOS atributos en todas sus reseñas; si no,
    # Dim_Restaurante no tendría una sola fila por restaurante. Esas reseñas quedan A INVESTIGAR.
    atributos = ["restaurant_name", "price_interval", "cuisine_types", "cuisine_match_encuesta", "restaurant_avg_rating"]
    variantes = df[["restaurant_id"] + atributos].fillna("<nulo>").groupby("restaurant_id").nunique()
    conflicto = variantes[(variantes > 1).any(axis=1)].index
    rechazar(df["restaurant_id"].isin(conflicto), "R18",
             "Restaurante con atributos contradictorios entre reseñas - A INVESTIGAR", "Consistencia")

    # R19-R20 Nulos de atributos del restaurante: se CONSERVAN como "Sin dato" (no se imputan ni se borran).
    # Razón: la reseña (rating, texto, fecha) es válida; el precio/cocina faltan en la ficha del restaurante.
    # Borrarlas sesgaría el análisis de sentimiento contra esos restaurantes. En Power BI se filtran si hace falta.
    bit.registrar(FUENTE, "R19", "Completitud", "price_interval nulo -> se conserva con Nivel_Precio 'Sin dato'",
                  "Conservar y marcar", df["price_interval"].isna().sum())
    bit.registrar(FUENTE, "R20", "Completitud", "cuisine_types nulo -> se conserva con Cocina_Principal 'Sin dato'",
                  "Conservar y marcar", df["cuisine_types"].isna().sum())

    # R21 Unicidad (a investigar, NO se borra): mismo texto en reseñas con review_id distinto.
    # Pueden ser copias/spam o reseñas cortas que coinciden; sin evidencia no se borran, se marcan.
    repetido = df["text"].duplicated(keep=False)
    bit.registrar(FUENTE, "R21", "Unicidad", "Texto repetido en reseñas distintas -> se marca Texto_Repetido='Sí' "
                  "y se lista en rechazados/resenas_a_investigar.csv (no se borra)", "Marcar", repetido.sum())

    # R22 Validez de codificación: caracteres de reemplazo (U+FFFD) o mojibake típico de UTF-8 leído como Latin-1
    raro = (df["text"].str.contains("�|Ã[\u0080-¿]", regex=True, na=False)
            | df["title"].str.contains("�|Ã[\u0080-¿]", regex=True, na=False))
    rechazar(raro, "R22", "Texto con caracteres corruptos de codificación", "Validez")

    # ---------------------------------------------------------------- ORIGEN DEL CLIENTE (R24-R27)
    df = asignar_origen(df, bit)

    # ---------------------------------------------------------------- TRANSFORMACIÓN / DERIVADAS
    df = df.copy()
    df["Fecha"] = pd.to_datetime(df["review_date"], format=config.FORMATO_FECHA)
    df["Rating"] = a_numero(df["rating"]).astype("int64")
    df["Sentimiento"] = df["Rating"].map(config.SENTIMIENTO)
    df["Sentimiento_Orden"] = df["Sentimiento"].map(config.ORDEN_SENTIMIENTO).astype("int64")
    df["Texto_Repetido"] = df["text"].duplicated(keep=False).map({True: "Sí", False: "No"})

    a_investigar = df[df["Texto_Repetido"] == "Sí"].sort_values(["text", "review_id"])
    a_investigar = crudo.loc[a_investigar.index].assign(
        Motivo="Texto repetido en reseñas distintas (conservada en Fact_Resenas, marcada)")

    dim_origen = construir_dim_origen(df)
    claves_origen = ["Tipo_Origen", "Pais_Cliente", "Region_Cliente", "Ciudad_Cliente"]
    origen_id = df[claves_origen].merge(dim_origen[claves_origen + ["Origen_ID"]], on=claves_origen,
                                        how="left")["Origen_ID"].to_numpy()

    fact = pd.DataFrame({
        "Review_ID": a_numero(df["review_id"]).astype("int64"),
        "Restaurant_ID": a_numero(df["restaurant_id"]).astype("int64"),
        "Fecha": df["Fecha"],
        "Rating": df["Rating"],
        "Sentimiento": df["Sentimiento"],
        "Sentimiento_Orden": df["Sentimiento_Orden"],
        "Titulo": df["title"].astype("string"),
        "Texto": df["text"].astype(str),
        "Longitud_Texto": df["text"].str.len().astype("int64"),
        "Texto_Repetido": df["Texto_Repetido"],
        "Idioma": df["language"].astype(str),
        # al final a propósito: si se agregara en medio, las consultas de Power BI ya creadas se desplazarían
        "Origen_ID": pd.Series(origen_id, index=df.index).astype("int64"),
    }).sort_values(["Fecha", "Review_ID"]).reset_index(drop=True)

    dim_rest = construir_dim_restaurante(df, fact, bit)
    dim_fecha = construir_dim_fecha()

    validas = len(fact)
    rechazadas = cua.total(FUENTE)
    bit.metrica("resenas_filas_validas", validas)
    bit.metrica("resenas_filas_rechazadas", rechazadas)
    bit.metrica("resenas_a_investigar", len(a_investigar))
    assert leidas == validas + rechazadas, "Balance roto: se perdieron filas en silencio"
    print(f"  válidas: {validas:,} | rechazadas: {rechazadas:,} | marcadas a investigar: {len(a_investigar):,}")

    bit.metrica("resenas_rating_promedio", float(fact["Rating"].mean()))
    bit.metrica("resenas_restaurantes", int(dim_rest.shape[0]))
    bit.metrica("resenas_periodo", [str(fact["Fecha"].min().date()), str(fact["Fecha"].max().date())])
    por_tipo = fact.merge(dim_origen, on="Origen_ID").groupby("Tipo_Origen").size()
    bit.metrica("resenas_por_tipo_origen", {k: int(v) for k, v in por_tipo.items()})

    tablas = {"Fact_Resenas": fact, "Dim_Restaurante": dim_rest, "Dim_Fecha": dim_fecha,
              "Dim_Origen_Cliente": dim_origen}
    return tablas, list(crudo.columns), a_investigar


# ==================================================================================== ORIGEN DEL CLIENTE
def normalizar_lugar(texto):
    """Minúsculas, sin tildes y espacios simples: 'Gijón ' -> 'gijon'. Solo para BUSCAR en el catálogo."""
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto.lower()).strip()


_MINUSCULAS = {"de", "del", "la", "las", "los", "el", "y", "i", "da", "do", "dos"}


def nombre_visible(clave):
    """Para lugares que NO están en el catálogo: 'pola de siero' -> 'Pola de Siero' (sin tildes: no se adivinan)."""
    palabras = clave.split(" ")
    return " ".join(p if (i and p in _MINUSCULAS) else p[:1].upper() + p[1:] for i, p in enumerate(palabras))


def interpretar_ubicacion(texto):
    """Texto libre del perfil -> (ciudad, región, país, tipo_origen, regla_aplicada).

    regla_aplicada es None si se identificó todo, o el código de la regla que explica por qué no (R25-R27)."""
    sd, nd, ni = config.ETIQUETA_SIN_DATO, config.ETIQUETA_NO_DETERMINADO, config.ETIQUETA_NO_IDENTIFICADA
    # Los paréntesis también separan: "Toledo (España)" -> "Toledo, España"
    partes = [normalizar_lugar(p) for p in re.split(r"[,()]", str(texto))]
    partes = [p for p in partes if p]
    if not partes:
        return sd, sd, sd, "Sin dato", "R25"

    ultima = partes[-1]
    if ultima in cat.ALIAS_ESPANA:
        pais, lugares = cat.ESPANA, partes[:-1]
    elif ultima in cat.PAISES:
        pais, lugares = cat.PAISES[ultima], partes[:-1]
    elif ultima in cat.SUBDIVISIONES_EXTRANJERAS:
        pais, lugares = cat.SUBDIVISIONES_EXTRANJERAS[ultima], partes[:-1]
    elif ultima in cat.LUGARES_ESPANA:                       # "gijon", "madrid, comunidad de madrid"
        pais, lugares = cat.ESPANA, partes
    else:                                                     # "World", "Europe", o algo irreconocible
        return nd, nd, nd, "No determinado", "R26"

    if pais != cat.ESPANA:
        ciudad = nombre_visible(lugares[0]) if lugares else ni
        return ciudad, config.REGION_EXTRANJERO, pais, "Extranjero", None

    # España: primera parte que sea ciudad del catálogo; si solo hay región/provincia, ciudad "No identificada"
    ciudad, region = None, None
    for lugar in lugares:
        if lugar in cat.LUGARES_ESPANA:
            c, r = cat.LUGARES_ESPANA[lugar]
            region = region or r
            if c:
                ciudad, region = c, r
                break
    regla = None
    if ciudad is None and region is None:                     # ciudad española fuera del catálogo, o solo "Spain"
        ciudad = nombre_visible(lugares[0]) if lugares else ni
        region, regla = ni, "R27"
    elif ciudad is None:
        ciudad = ni
    if ciudad == config.CIUDAD_LOCAL:
        tipo = "Gijón (local)"
    elif region == config.COMUNIDAD_LOCAL:
        tipo = "Resto de Asturias"
    else:
        tipo = "Resto de España"
    return ciudad, region, pais, tipo, regla


def asignar_origen(df, bit):
    """Une la ubicación del autor (archivo aparte) y la normaliza. Nada se borra: lo que no se puede saber se
    etiqueta ('Sin dato', 'No determinado', 'No identificada') y se cuenta en la bitácora."""
    ub = leer_csv_texto(config.ARCHIVO_UBICACION)
    exigir_columnas(ub, config.COLUMNAS_UBICACION, "Ubicacion")
    ub["review_id"] = ub["review_id"].str.strip()
    if ub["review_id"].duplicated().any():
        raise ValueError("[Ubicacion] review_id repetido en el archivo de ubicaciones: el cruce no sería 1 a 1")

    df = df.copy()
    ubic = df["review_id"].map(ub.set_index("review_id")["user_location"])
    bit.registrar(FUENTE, "R24", "Completitud", "Reseña sin fila en el archivo de ubicaciones -> se conserva con "
                  "Tipo_Origen 'Sin dato'", "Conservar y marcar", int(ubic.isna().sum()))

    resultado = ubic.fillna("").map(interpretar_ubicacion)
    df["Ciudad_Cliente"] = resultado.str[0]
    df["Region_Cliente"] = resultado.str[1]
    df["Pais_Cliente"] = resultado.str[2]
    df["Tipo_Origen"] = resultado.str[3]
    regla = resultado.str[4]

    bit.registrar(FUENTE, "R25", "Completitud", "Ubicación vacía en el perfil -> Tipo_Origen 'Sin dato' "
                  "(no se imputa)", "Conservar y marcar", int((regla == "R25").sum()))
    bit.registrar(FUENTE, "R26", "Validez", "Ubicación que no permite saber el país ('World', 'Europe'...) -> "
                  "'No determinado'", "Conservar y marcar", int((regla == "R26").sum()))
    bit.registrar(FUENTE, "R27", "Consistencia", "Lugar de España fuera del catálogo de etl/ubicaciones.py -> "
                  "Region_Cliente 'No identificada' (la ciudad se conserva como viene)", "Conservar y marcar",
                  int((regla == "R27").sum()))
    return df


def construir_dim_origen(df):
    """Una fila por combinación tipo de origen + país + región + ciudad."""
    claves = ["Tipo_Origen", "Pais_Cliente", "Region_Cliente", "Ciudad_Cliente"]
    dim = df.groupby(claves).size().rename("Num_Resenas").reset_index()
    dim["Tipo_Origen_Orden"] = dim["Tipo_Origen"].map(config.TIPO_ORIGEN).astype("int64")
    dim = dim.sort_values(["Tipo_Origen_Orden", "Pais_Cliente", "Region_Cliente", "Ciudad_Cliente"]).reset_index(drop=True)
    dim.insert(0, "Origen_ID", range(1, len(dim) + 1))
    return dim[["Origen_ID", "Ciudad_Cliente", "Region_Cliente", "Pais_Cliente", "Tipo_Origen",
                "Tipo_Origen_Orden", "Num_Resenas"]].astype({"Origen_ID": "int64", "Num_Resenas": "int64"})


def construir_dim_restaurante(df, fact, bit):
    """Una fila por restaurante. Conserva los valores ORIGINALES y añade columnas normalizadas."""
    r = (df.drop_duplicates("restaurant_id")
           [["restaurant_id", "restaurant_name", "city", "price_interval", "cuisine_types",
             "cuisine_match_encuesta", "restaurant_avg_rating"]].copy())
    r["Restaurant_ID"] = a_numero(r["restaurant_id"]).astype("int64")

    # Precio: nivel ordenado 1-3 (nulo se queda nulo, con etiqueta "Sin dato" para los filtros)
    r["Nivel_Precio"] = r["price_interval"].map(lambda v: config.NIVEL_PRECIO[v][0] if pd.notna(v) else None).astype("Int64")
    r["Precio_Etiqueta"] = r["price_interval"].map(
        lambda v: config.NIVEL_PRECIO[v][1] if pd.notna(v) else config.ETIQUETA_SIN_DATO)

    # Cocina: lista en texto "Mediterranean; Spanish" -> tipo principal (el primero) y cuántos tipos hay
    lista = r["cuisine_types"].str.split(config.SEPARADOR_COCINAS)
    r["Cocina_Principal"] = lista.str[0].str.strip().fillna(config.ETIQUETA_SIN_DATO)
    r["Num_Tipos_Cocina"] = lista.map(lambda x: len(x) if isinstance(x, list) else 0).astype("int64")

    # cuisine_match_encuesta (derivada por un compañero, NO viene de TripAdvisor): se conserva tal cual y,
    # aparte, se agrupan las categorías con < 100 reseñas en "Otras" para que los gráficos sean legibles
    por_cat = df["cuisine_match_encuesta"].value_counts()
    pequenas = set(por_cat[por_cat < config.MIN_RESENAS_CATEGORIA].index)
    r["Cocina_Encuesta_Agrupada"] = r["cuisine_match_encuesta"].where(~r["cuisine_match_encuesta"].isin(pequenas), "Otras")
    bit.registrar(FUENTE, "R23", "Consistencia",
                  f"cuisine_match_encuesta con < {config.MIN_RESENAS_CATEGORIA} reseñas agrupadas en 'Otras': "
                  f"{sorted(pequenas)} (reseñas afectadas)", "Derivar columna aparte",
                  int(por_cat[list(pequenas)].sum()) if pequenas else 0)

    # Agregados calculados desde NUESTRAS reseñas (distinto del promedio global que publica TripAdvisor)
    agg = fact.groupby("Restaurant_ID").agg(Num_Resenas=("Review_ID", "size"),
                                            Rating_Promedio_Resenas=("Rating", "mean")).reset_index()
    agg["Rating_Promedio_Resenas"] = agg["Rating_Promedio_Resenas"].round(4)

    dim = (r.rename(columns={"restaurant_name": "Nombre", "city": "Ciudad", "price_interval": "Precio_Original",
                             "cuisine_types": "Cocinas_Original", "cuisine_match_encuesta": "Cocina_Encuesta_Original"})
             .assign(Rating_Promedio_TripAdvisor=lambda x: a_numero(x["restaurant_avg_rating"]).astype("float64"))
             .merge(agg, on="Restaurant_ID", how="left"))
    cols = ["Restaurant_ID", "Nombre", "Ciudad", "Precio_Original", "Nivel_Precio", "Precio_Etiqueta",
            "Cocinas_Original", "Cocina_Principal", "Num_Tipos_Cocina", "Cocina_Encuesta_Original",
            "Cocina_Encuesta_Agrupada", "Rating_Promedio_TripAdvisor", "Num_Resenas", "Rating_Promedio_Resenas"]
    return dim[cols].sort_values("Restaurant_ID").reset_index(drop=True)


def construir_dim_fecha():
    """Calendario CONTINUO de años completos (requisito de la inteligencia de tiempo de Power BI)."""
    f = pd.date_range(f"{config.ANIO_INICIO}-01-01", f"{config.ANIO_FIN}-12-31", freq="D")
    return pd.DataFrame({
        "Fecha": f,
        "Anio": f.year,
        "Semestre": ((f.month - 1) // 6 + 1),
        "Trimestre": f.quarter,
        "Mes": f.month,
        "Nombre_Mes": [config.MESES[m - 1] for m in f.month],
        "Anio_Mes": f.strftime("%Y-%m"),
        "Dia": f.day,
        "Dia_Semana": f.dayofweek + 1,                      # 1 = lunes ... 7 = domingo
        "Nombre_Dia": [config.DIAS[d] for d in f.dayofweek],
        "Es_Fin_De_Semana": ["Sí" if d >= 5 else "No" for d in f.dayofweek],
    }).astype({"Anio": "int64", "Semestre": "int64", "Trimestre": "int64", "Mes": "int64", "Dia": "int64",
               "Dia_Semana": "int64"})
