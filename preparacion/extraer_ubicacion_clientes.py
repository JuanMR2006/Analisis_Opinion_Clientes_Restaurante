"""Extrae la ubicación declarada por el autor de cada reseña (perfil de TripAdvisor) a un CSV crudo.

Fuente: TripAdvisor Restaurant Reviews v2.0.0 (Zenodo, DOI 10.5281/zenodo.14622324, CC BY 4.0), archivo Gijón.zip.
El zip trae tres tablas en pickle: items (restaurantes), reviews (reseñas, con userId) y users (userId, name,
location). Aquí se cruza reviews -> users para las reseñas que ya están en datasets/gijon_resenas_es_2017_2023.csv.

Salida: datasets/gijon_ubicacion_clientes.csv con DOS columnas:
    review_id      llave para unir con gijon_resenas_es_2017_2023.csv
    user_location  ubicación TAL COMO la escribió el usuario ("Gijon, Spain", "gijon", "" ...), sin limpiar

No se guardan userId ni name: no hacen falta para el análisis (privacidad). La limpieza de la ubicación NO se
hace aquí sino en el ETL (reglas R24-R27), para que quede documentada y validada como el resto.

Uso:
    pip install pandas
    python preparacion/extraer_ubicacion_clientes.py Gijon.zip
    (también acepta la carpeta ya descomprimida)
"""
import sys
import tempfile
import zipfile
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
RESENAS = RAIZ / "datasets" / "gijon_resenas_es_2017_2023.csv"
SALIDA = RAIZ / "datasets" / "gijon_ubicacion_clientes.csv"


def buscar(carpeta: Path, nombre: str) -> Path:
    encontrados = list(carpeta.rglob(nombre))
    if not encontrados:
        sys.exit(f"No encontré {nombre} dentro de {carpeta}")
    return encontrados[0]


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

    reviews = pd.read_pickle(buscar(carpeta, "reviews.pkl"))[["reviewId", "userId"]]
    users = pd.read_pickle(buscar(carpeta, "users.pkl"))[["userId", "location"]]
    nuestras = pd.read_csv(RESENAS, usecols=["review_id"], dtype=str)

    # userId "-1" es el marcador de "usuario desconocido" de la fuente: aparece varias veces con ubicaciones
    # distintas, así que no se puede saber cuál corresponde. Sus reseñas quedan sin ubicación (no se adivina).
    desconocido = users["userId"].astype(str) == "-1"
    users = users[~desconocido]
    if users["userId"].duplicated().any() or reviews["reviewId"].duplicated().any():
        sys.exit("userId o reviewId repetidos en la fuente: el cruce no sería uno a uno")
    anonimas = reviews["userId"].astype(str) == "-1"

    reviews["reviewId"] = reviews["reviewId"].astype(str)
    ids_anonimos = set(reviews.loc[anonimas, "reviewId"])
    salida = (nuestras.merge(reviews, left_on="review_id", right_on="reviewId", how="left")
                      .merge(users, on="userId", how="left"))
    sin_usuario = int(salida["review_id"].isin(ids_anonimos).sum() + salida["userId"].isna().sum())
    salida = salida.rename(columns={"location": "user_location"})[["review_id", "user_location"]]
    salida["user_location"] = salida["user_location"].fillna("")

    assert len(salida) == len(nuestras), "El cruce cambió el número de reseñas"
    salida.to_csv(SALIDA, index=False, encoding="utf-8")

    vacias = int((salida["user_location"].str.strip() == "").sum())
    print(f"Listo: {SALIDA.relative_to(RAIZ)} | {len(salida):,} reseñas | "
          f"sin usuario en la fuente: {sin_usuario:,} | ubicación vacía: {vacias:,} ({vacias / len(salida):.1%})")
    if tmp:
        tmp.cleanup()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python preparacion/extraer_ubicacion_clientes.py Gijon.zip")
    main(sys.argv[1])
