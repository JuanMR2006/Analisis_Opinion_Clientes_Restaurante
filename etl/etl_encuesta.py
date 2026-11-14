"""Pipeline 1: encuesta de clientes (dataset del profesor, Iznia) -> Fact_Encuesta + dimensiones pequeñas.

Grano de Fact_Encuesta: UNA fila por encuestado (CustomerID). No tiene ninguna relación con TripAdvisor.

Reglas E01..E16 (cada una con su dimensión de calidad). Se aplican en orden y cada fila rechazada sale
UNA sola vez a rechazados/encuesta_rechazados.csv con el código y el motivo de la PRIMERA regla que falló.
"""
import pandas as pd

import config
from utilidades import (a_nulo, a_numero, exigir_columnas, fuera_de, leer_csv_texto, no_es_entero,
                        no_es_numero, perfil_nulos)

FUENTE = "Encuesta"


def procesar(bit, cua):
    print(f"\n== {FUENTE}: {config.ARCHIVO_ENCUESTA.name}")

    # ---------------------------------------------------------------- EXTRACT
    crudo = leer_csv_texto(config.ARCHIVO_ENCUESTA)
    exigir_columnas(crudo, config.COLUMNAS_ENCUESTA, FUENTE)
    leidas = len(crudo)
    bit.metrica("encuesta_filas_leidas", leidas)
    print(f"  filas leídas: {leidas:,}")

    # ---------------------------------------------------------------- NORMALIZACIÓN DE TEXTO
    # trim + marcas de "sin dato" -> nulo, ANTES de validar (si no, " 5" o "NA" engañan a las reglas)
    df = crudo[list(config.COLUMNAS_ENCUESTA)].rename(columns=config.COLUMNAS_ENCUESTA)
    antes = int(sum((df[c].str.strip() != df[c]).sum() for c in df.columns))
    for c in df.columns:
        df[c] = a_nulo(df[c])
    bit.registrar(FUENTE, "E00", "Validez", "Normalización: celdas con espacios sobrantes recortadas", "Transformar", antes)

    def rechazar(mascara, codigo, regla, dimension):
        nonlocal df
        df = cua.rechazar(df, mascara, crudo, FUENTE, codigo, regla, dimension, bit)

    # E01 Completitud: % de nulos por columna (> 20 % se evalúa y se documenta; no se borra la columna a ciegas)
    altas = perfil_nulos(df, df.columns, FUENTE, "E01", bit)
    if altas:
        bit.decision(FUENTE, f"Columnas con > 20 % de nulos: {altas}. Revisar antes de usarlas en el análisis.")

    # E02 Completitud: sin identificador no se puede saber quién respondió ni detectar duplicados
    rechazar(df["ID_Cliente"].isna(), "E02", "ID_Cliente nulo", "Completitud")

    # E03 Validez: el id debe ser un entero (nunca decimal: 654.0 no es un id)
    id_num = a_numero(df["ID_Cliente"])
    rechazar(no_es_numero(df["ID_Cliente"], id_num) | no_es_entero(id_num) | (id_num <= 0),
             "E03", "ID_Cliente no es un entero positivo", "Validez")

    # E04 Unicidad: duplicado EXACTO (todas las columnas iguales) = la misma respuesta cargada dos veces.
    # Se conserva la primera aparición y las copias van a cuarentena.
    rechazar(df.duplicated(keep="first"), "E04", "Fila duplicada exacta (se conserva la primera)", "Unicidad")

    # E05 Unicidad: mismo ID con respuestas DISTINTAS. No se puede saber cuál es la buena sin inventar,
    # así que TODAS las versiones van a cuarentena marcadas "A INVESTIGAR" (no se elige una al azar).
    rechazar(df["ID_Cliente"].duplicated(keep=False), "E05",
             "ID_Cliente repetido con respuestas distintas - A INVESTIGAR", "Unicidad")

    # E06 Completitud: en la encuesta todas las preguntas son obligatorias; NO se imputa con media/moda
    rechazar(df.isna().any(axis=1), "E06", "Alguna respuesta obligatoria nula (no se imputa)", "Completitud")

    # E07 Validez: conversión explícita de tipos. Si no convierte, es un error de captura.
    enteros = ["Edad", "Ingreso", "Tamano_Grupo", "Calif_Servicio", "Calif_Comida", "Calif_Ambiente",
               "Reserva_Online", "Pedido_Domicilio", "Miembro_Lealtad", "Alta_Satisfaccion"]
    decimales = ["Gasto_Promedio", "Tiempo_Espera_Min"]
    num = {c: a_numero(df[c]) for c in enteros + decimales}
    malo = pd.Series(False, index=df.index)
    for c in enteros + decimales:
        malo |= no_es_numero(df[c], num[c])
    for c in enteros:
        malo |= no_es_entero(num[c])
    rechazar(malo, "E07", "Valor no numérico o decimal donde se espera un entero", "Validez")
    num = {c: s.loc[df.index] for c, s in num.items()}

    # E08-E13 Validez: rangos de DOMINIO (lo imposible), no estadísticos (los atípicos reales se quedan)
    rangos = [
        ("E08", "Edad", config.RANGO_EDAD, "Edad fuera de 18-100 años"),
        ("E09", "Ingreso", config.RANGO_INGRESO, "Ingreso <= 0 o > 1.000.000"),
        ("E10", "Gasto_Promedio", config.RANGO_GASTO, "Gasto promedio <= 0 o > 1.000"),
        ("E11", "Tiempo_Espera_Min", config.RANGO_ESPERA_MIN, "Tiempo de espera fuera de 0-240 min"),
        ("E12", "Tamano_Grupo", config.RANGO_GRUPO, "Tamaño de grupo fuera de 1-30 personas"),
    ]
    for codigo, col, rango, regla in rangos:
        s = num[col].loc[df.index]
        mascara = fuera_de(s, rango)
        if col in ("Ingreso", "Gasto_Promedio"):
            mascara |= s <= 0          # un ingreso o gasto de 0 no tiene sentido en la encuesta
        rechazar(mascara, codigo, regla, "Validez")

    califs = ["Calif_Servicio", "Calif_Comida", "Calif_Ambiente"]
    m = pd.Series(False, index=df.index)
    for c in califs:
        m |= fuera_de(num[c].loc[df.index], config.RANGO_CALIFICACION)
    rechazar(m, "E13", "Calificación fuera de la escala 1-5", "Validez")

    # E14 Validez: las banderas sí/no solo pueden ser 0 o 1
    banderas = ["Reserva_Online", "Pedido_Domicilio", "Miembro_Lealtad", "Alta_Satisfaccion"]
    m = pd.Series(False, index=df.index)
    for c in banderas:
        m |= ~df[c].isin(config.BINARIAS)
    rechazar(m, "E14", "Bandera binaria distinta de 0/1", "Validez")

    # E15 Validez: categorías contra un conjunto PERMITIDO (detecta erratas como 'Itallian' o 'male ')
    m = pd.Series(False, index=df.index)
    for c, permitidas in config.CATEGORIAS_ENCUESTA.items():
        m |= ~df[c].isin(permitidas)
    rechazar(m, "E15", "Categoría fuera del conjunto permitido", "Validez")

    # ---------------------------------------------------------------- TIPOS FINALES
    fact = df.copy()
    for c in enteros:
        fact[c] = num[c].loc[fact.index].astype("int64")
    for c in decimales:
        fact[c] = num[c].loc[fact.index].astype("float64").round(4)
    fact["ID_Cliente"] = a_numero(fact["ID_Cliente"]).astype("int64")
    for c in config.CATEGORIAS_ENCUESTA:
        fact[c] = fact[c].astype(str)

    # Columnas derivadas (documentadas): promedio de las 3 calificaciones y etiquetas en español
    fact["Calif_Promedio"] = fact[califs].mean(axis=1).round(4)
    fact["Genero_ES"] = fact["Genero"].map(config.ETIQUETA_GENERO)
    fact["Tipo_Comida_ES"] = fact["Tipo_Comida"].map(config.ETIQUETA_TIPO_COMIDA)
    fact["Alta_Satisfaccion_ES"] = fact["Alta_Satisfaccion"].map({1: "Sí", 0: "No"})
    bit.registrar(FUENTE, "E16", "Consistencia",
                  "Derivadas: Calif_Promedio (media de 3 calificaciones) y etiquetas en español", "Derivar", len(fact))
    fact = fact.sort_values("ID_Cliente").reset_index(drop=True)

    validas = len(fact)
    rechazadas = cua.total(FUENTE)
    bit.metrica("encuesta_filas_validas", validas)
    bit.metrica("encuesta_filas_rechazadas", rechazadas)
    assert leidas == validas + rechazadas, "Balance roto: se perdieron filas en silencio"
    print(f"  válidas: {validas:,} | rechazadas: {rechazadas:,}")

    # ---------------------------------------------------------------- DIMENSIONES PEQUEÑAS
    def dim(mapa, clave, nombre):
        return pd.DataFrame([(k, v[0], v[1]) for k, v in mapa.items()], columns=[clave, nombre, f"{nombre}_Orden"])

    tablas = {
        "Fact_Encuesta": fact,
        "Dim_Cocina_Preferida": dim(config.DIM_COCINA, "Cocina_Preferida", "Cocina"),
        "Dim_Ocasion": dim(config.DIM_OCASION, "Ocasion", "Ocasion_ES"),
        "Dim_Franja_Visita": dim(config.DIM_FRANJA, "Franja_Visita", "Franja"),
        "Dim_Frecuencia_Visita": dim(config.DIM_FRECUENCIA, "Frecuencia_Visita", "Frecuencia"),
    }
    # Métricas para la conciliación independiente (exactitud)
    bit.metrica("encuesta_promedio_calif_comida", float(fact["Calif_Comida"].mean()))
    bit.metrica("encuesta_pct_alta_satisfaccion", float(fact["Alta_Satisfaccion"].mean()))
    return tablas, list(crudo.columns)
