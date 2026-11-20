"""Load a base de datos: escribe el modelo estrella en una base SQLite (un solo archivo .db).

Cada tabla se crea con DDL explícito: tipos, PRIMARY KEY y FOREIGN KEY. Así la base valida por sí misma
que no haya llaves repetidas ni registros huérfanos. Se borra y se regenera en cada corrida (idempotente).

    base_datos/opiniones_restaurantes.db
        Modelo encuesta:  Fact_Encuesta -> Dim_Cocina_Preferida, Dim_Ocasion, Dim_Franja_Visita, Dim_Frecuencia_Visita
        Modelo reseñas:   Fact_Resenas  -> Dim_Restaurante, Dim_Fecha, Dim_Origen_Cliente;  Fact_Palabras -> Fact_Resenas
        Auditoría:        Bitacora_Reglas (cada regla aplicada y cuántas filas afectó)

Consultar:  sqlite3 base_datos/opiniones_restaurantes.db   o   DB Browser for SQLite
"""
import sqlite3

import pandas as pd

import config

# Orden de creación: primero las dimensiones, después los hechos que las referencian
ESQUEMA = {
    "Dim_Cocina_Preferida": {"pk": ["Cocina_Preferida"]},
    "Dim_Ocasion": {"pk": ["Ocasion"]},
    "Dim_Franja_Visita": {"pk": ["Franja_Visita"]},
    "Dim_Frecuencia_Visita": {"pk": ["Frecuencia_Visita"]},
    "Fact_Encuesta": {"pk": ["ID_Cliente"], "fk": {
        "Cocina_Preferida": "Dim_Cocina_Preferida", "Ocasion": "Dim_Ocasion",
        "Franja_Visita": "Dim_Franja_Visita", "Frecuencia_Visita": "Dim_Frecuencia_Visita"}},
    "Dim_Restaurante": {"pk": ["Restaurant_ID"]},
    "Dim_Fecha": {"pk": ["Fecha"]},
    "Dim_Origen_Cliente": {"pk": ["Origen_ID"]},
    "Fact_Resenas": {"pk": ["Review_ID"], "fk": {
        "Restaurant_ID": "Dim_Restaurante", "Fecha": "Dim_Fecha", "Origen_ID": "Dim_Origen_Cliente"}},
    "Fact_Palabras": {"pk": ["Review_ID", "Palabra"], "fk": {"Review_ID": "Fact_Resenas"}},
}

# Índices para que las consultas por llave foránea sean rápidas
INDICES = [("Fact_Resenas", "Restaurant_ID"), ("Fact_Resenas", "Fecha"), ("Fact_Resenas", "Origen_ID")]


def tipo_sql(serie):
    if pd.api.types.is_bool_dtype(serie) or pd.api.types.is_integer_dtype(serie):
        return "INTEGER"
    if pd.api.types.is_float_dtype(serie):
        return "REAL"
    return "TEXT"   # texto y fechas (las fechas se guardan como 'AAAA-MM-DD', formato ISO que SQLite entiende)


def preparar(df):
    """Convierte fechas a texto ISO y los nulos de pandas a None para que sqlite3 los guarde como NULL."""
    df = df.copy()
    for c in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[c]):
            df[c] = df[c].dt.strftime("%Y-%m-%d")
    return df.astype(object).where(df.notna(), None)


def ddl(nombre, df):
    spec = ESQUEMA[nombre]
    cols = [f'    "{c}" {tipo_sql(df[c])}' + (" NOT NULL" if c in spec["pk"] else "") for c in df.columns]
    cols.append(f"    PRIMARY KEY ({', '.join(spec['pk'])})")
    for col, ref in spec.get("fk", {}).items():
        cols.append(f"    FOREIGN KEY ({col}) REFERENCES {ref}({ESQUEMA[ref]['pk'][0]})")
    return f'CREATE TABLE "{nombre}" (\n' + ",\n".join(cols) + "\n);"


def cargar(tablas, pasos):
    """tablas: dict nombre -> DataFrame (las mismas que se guardan en CSV/parquet). pasos: bitácora de reglas."""
    config.BASE_DATOS.parent.mkdir(parents=True, exist_ok=True)
    if config.BASE_DATOS.exists():
        config.BASE_DATOS.unlink()
    con = sqlite3.connect(config.BASE_DATOS)
    try:
        con.execute("PRAGMA foreign_keys = ON")
        for nombre in ESQUEMA:
            df = tablas[nombre]
            con.execute(ddl(nombre, df))
            datos = preparar(df)
            marcadores = ", ".join("?" * len(df.columns))
            con.executemany(f'INSERT INTO "{nombre}" VALUES ({marcadores})', datos.itertuples(index=False, name=None))
            print(f"  {nombre:28s} {len(df):>8,} filas -> {config.BASE_DATOS.name}")
        for tabla, col in INDICES:
            con.execute(f"CREATE INDEX ix_{tabla}_{col} ON {tabla}({col})")
        bit = pd.DataFrame(pasos)[["fuente", "codigo", "regla", "dimension", "accion", "filas"]]
        bit.columns = ["Fuente", "Codigo", "Regla", "Dimension", "Accion", "Filas"]
        bit.to_sql("Bitacora_Reglas", con, index=False)
        huerfanos = con.execute("PRAGMA foreign_key_check").fetchall()
        if huerfanos:
            raise SystemExit(f"La base tiene {len(huerfanos)} registros huérfanos: {huerfanos[:5]}")
        con.commit()
        con.execute("VACUUM")
    finally:
        con.close()
    mb = config.BASE_DATOS.stat().st_size / 1e6
    print(f"  Base de datos: {config.BASE_DATOS.relative_to(config.RAIZ)} ({mb:.1f} MB, llaves foráneas verificadas)")
