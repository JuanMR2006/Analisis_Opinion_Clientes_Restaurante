"""
Reduce gijon_resenas_es.csv por debajo de un tamaño máximo conservando un periodo
CONTINUO y reciente (años completos), para no distorsionar la tendencia mensual.

Uso:
    python preparacion/reducir_gijon.py            -> máximo 10 MB (por defecto)
    python preparacion/reducir_gijon.py 30         -> máximo 30 MB
"""

import sys
from pathlib import Path

import pandas as pd

ENTRADA = "gijon_resenas_es.csv"


def main(max_mb: float) -> None:
    df = pd.read_csv(ENTRADA, encoding="utf-8", dtype={"price_interval": str})
    df["year"] = df["review_date"].str[:4].astype(int)

    # Tamaño aproximado que ocupa cada fila en el CSV
    lineas = df.drop(columns="year").to_csv(index=False, header=False, lineterminator="\n")
    bytes_fila = pd.Series(
        [len(l.encode("utf-8")) + 2 for l in lineas.split("\n")[:-1]], index=df.index
    )  # +2 por el salto de línea de Windows (\r\n)
    por_anio = (
        pd.DataFrame({"year": df["year"], "bytes": bytes_fila})
        .groupby("year")
        .agg(resenas=("bytes", "size"), mb=("bytes", lambda b: b.sum() / 1024 / 1024))
        .sort_index()
    )
    print("Reseñas por año:")
    print(por_anio.round(2).to_string())

    # Revisar si hay muchas fechas exactamente el 1 de enero (posible valor por defecto)
    primero_enero = (df["review_date"].str[5:] == "01-01").sum()
    print(f"\nReseñas fechadas un 1 de enero: {primero_enero:,}")

    # Acumular años desde el más reciente hasta llenar el límite
    acumulado, anio_inicio = 0.0, None
    for anio in sorted(por_anio.index, reverse=True):
        if acumulado + por_anio.loc[anio, "mb"] > max_mb * 0.97:  # margen por el encabezado
            break
        acumulado += por_anio.loc[anio, "mb"]
        anio_inicio = anio
    if anio_inicio is None:
        sys.exit("Ni siquiera el último año cabe en ese tamaño; prueba con un límite mayor.")

    recorte = df[df["year"] >= anio_inicio].drop(columns="year")
    salida = f"gijon_resenas_es_{anio_inicio}_{df['year'].max()}.csv"
    recorte.to_csv(salida, index=False, encoding="utf-8")

    tam = Path(salida).stat().st_size / 1024 / 1024
    print(f"\nListo: {salida}")
    print(f"{len(recorte):,} reseñas | {recorte['restaurant_id'].nunique():,} restaurantes | {tam:.1f} MB")
    print(f"Periodo: {recorte['review_date'].min()} a {recorte['review_date'].max()}")
    print("Rangos de precio:", recorte["price_interval"].fillna("(vacío)").value_counts().to_dict())
    print("Calificaciones:", recorte["rating"].value_counts().sort_index().to_dict())


if __name__ == "__main__":
    main(float(sys.argv[1]) if len(sys.argv) > 1 else 10)
