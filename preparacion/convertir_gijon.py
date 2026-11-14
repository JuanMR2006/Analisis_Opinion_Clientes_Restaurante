"""
Convierte el subconjunto de Gijón del dataset "TripAdvisor Restaurant Reviews v2.0.0"
(Zenodo, DOI 10.5281/zenodo.14622324, licencia CC BY 4.0) a un CSV con reseñas en español.

Uso:
    pip install pandas
    python preparacion/convertir_gijon.py Gijón.zip
    (también acepta la carpeta ya descomprimida: python convertir_gijon.py Gijón)

Salida:
    gijon_resenas_es.csv  (UTF-8, separado por comas)
"""

import sys
import zipfile
import tempfile
from pathlib import Path

import pandas as pd

SALIDA = "gijon_resenas_es.csv"

# Cocinas que aparecen en la encuesta del profesor (columna PreferredCuisine)
COCINAS_ENCUESTA = ["Italian", "Chinese", "Mexican", "Indian", "American"]


def buscar_pkl(carpeta: Path, nombre: str) -> Path:
    encontrados = list(carpeta.rglob(nombre))
    if not encontrados:
        sys.exit(f"No encontré {nombre} dentro de {carpeta}")
    return encontrados[0]


def es_espanol(valor) -> bool:
    if pd.isna(valor):
        return False
    v = str(valor).strip().lower()
    return v in {"es", "spa", "spanish", "español", "espanol"} or v.startswith("es-") or v.startswith("es_")


def lista_a_texto(valor) -> str:
    if isinstance(valor, (list, tuple, set)):
        return "; ".join(str(x) for x in valor)
    if pd.isna(valor):
        return ""
    return str(valor)


def emparejar_cocina(tipos: str) -> str:
    """Devuelve las cocinas de la encuesta presentes en el restaurante (o 'Other')."""
    t = tipos.lower()
    coincidencias = [c for c in COCINAS_ENCUESTA if c.lower() in t]
    return "; ".join(coincidencias) if coincidencias else "Other"


def main(ruta: str) -> None:
    ruta = Path(ruta)
    tmp = None
    if ruta.suffix.lower() == ".zip":
        tmp = tempfile.TemporaryDirectory()
        with zipfile.ZipFile(ruta) as z:
            z.extractall(tmp.name)
        carpeta = Path(tmp.name)
    else:
        carpeta = ruta

    items = pd.read_pickle(buscar_pkl(carpeta, "items.pkl"))
    reviews = pd.read_pickle(buscar_pkl(carpeta, "reviews.pkl"))

    print(f"Restaurantes: {len(items):,} | Reseñas totales: {len(reviews):,}")
    print("Columnas items:  ", list(items.columns))
    print("Columnas reviews:", list(reviews.columns))
    print("Idiomas (top 10):")
    print(reviews["language"].value_counts().head(10).to_string())

    # 1) Solo reseñas en español
    rev = reviews[reviews["language"].apply(es_espanol)].copy()
    print(f"\nReseñas en español: {len(rev):,}")

    # 2) Columnas del restaurante (se renombran para no chocar con las de la reseña)
    rest = items[["itemId", "name", "city", "priceInterval", "type", "rating"]].rename(
        columns={
            "itemId": "restaurant_id",
            "name": "restaurant_name",
            "priceInterval": "price_interval",
            "type": "cuisine_types",
            "rating": "restaurant_avg_rating",
        }
    )
    rest["cuisine_types"] = rest["cuisine_types"].apply(lista_a_texto)
    rest["cuisine_match_encuesta"] = rest["cuisine_types"].apply(emparejar_cocina)

    rev = rev[["reviewId", "itemId", "date", "rating", "title", "text", "language"]].rename(
        columns={"reviewId": "review_id", "itemId": "restaurant_id", "rating": "rating_raw"}
    )

    df = rev.merge(rest, on="restaurant_id", how="left")

    # 3) Calificación: viene de 0 a 50 -> escala 1 a 5
    df["rating"] = pd.to_numeric(df["rating_raw"], errors="coerce") / 10
    restaurante = pd.to_numeric(df["restaurant_avg_rating"], errors="coerce")
    if restaurante.max() > 5:  # por si el promedio también viene en escala 0-50
        restaurante = restaurante / 10
    df["restaurant_avg_rating"] = restaurante

    # 4) Fecha normalizada (AAAA-MM-DD) y mes (AAAA-MM) para la tendencia mensual
    try:  # pandas >= 2.0: acepta formatos mezclados en la misma columna
        fechas = pd.to_datetime(df["date"], errors="coerce", format="mixed", dayfirst=True)
    except (TypeError, ValueError):
        fechas = df["date"].apply(lambda x: pd.to_datetime(x, errors="coerce", dayfirst=True))
    fechas = pd.to_datetime(fechas, errors="coerce")
    print(f"Fechas que no se pudieron interpretar: {fechas.isna().sum():,}")
    df["review_date"] = fechas.dt.strftime("%Y-%m-%d")
    df["year_month"] = fechas.dt.strftime("%Y-%m")

    # 5) Limpieza de texto (saltos de línea que rompen algunos lectores de CSV)
    for col in ["title", "text"]:
        df[col] = df[col].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
    df = df[df["text"].str.len() > 0]
    df = df.drop_duplicates(subset=["review_id"])

    columnas = [
        "review_id", "restaurant_id", "restaurant_name", "city", "price_interval",
        "cuisine_types", "cuisine_match_encuesta", "restaurant_avg_rating",
        "review_date", "year_month", "rating", "title", "text", "language",
    ]
    df = df[columnas].sort_values(["review_date", "restaurant_id"])
    df.to_csv(SALIDA, index=False, encoding="utf-8")

    tam_mb = Path(SALIDA).stat().st_size / 1024 / 1024
    print(f"\nListo: {SALIDA} | {len(df):,} filas x {len(df.columns)} columnas | {tam_mb:.1f} MB")
    print(f"Restaurantes distintos: {df['restaurant_id'].nunique():,}")
    print(f"Rango de fechas: {df['review_date'].min()} a {df['review_date'].max()}")
    print("Rangos de precio:", df["price_interval"].value_counts(dropna=False).to_dict())
    print("Distribución de calificaciones:", df["rating"].value_counts().sort_index().to_dict())
    if tam_mb > 30:
        print("AVISO: supera 30 MB. Puedes filtrar por años, p. ej. df[df.year_month >= '2015-01'].")

    if tmp:
        tmp.cleanup()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python preparacion/convertir_gijon.py Gijón.zip")
    main(sys.argv[1])
