# Análisis de Opiniones de Clientes en Restaurante

Proyecto de Ingeniería de Software: ETL en Python, validación de calidad, análisis estadístico (ANOVA) y
dashboard en Power BI (`powerbi/`).

## Fuentes (`datasets/`, no se modifican)

| Archivo | Descripción | Filas |
|---|---|---:|
| `dataset_raw.csv` | Encuesta de clientes (dataset del profesor, Iznia) | 1.500 |
| `gijon_resenas_es_2017_2023.csv` | Reseñas de TripAdvisor en español, Gijón, 2017–2023 | 53.382 |
| `gijon_ubicacion_clientes.csv` | Ubicación que declara el autor de cada reseña (texto libre, sin limpiar) | 53.382 |

Los dos archivos de TripAdvisor se generaron desde Zenodo con los scripts de `preparacion/` (ver
[docs/PIPELINE.md §2.2](docs/PIPELINE.md)); no hace falta volver a correrlos.

Se procesan como **dos pipelines independientes** (no comparten clave).

## Cómo ejecutar

```bash
pip install -r requirements.txt
```

```bash
python etl/etl_main.py
```

```bash
python etl/validar_calidad.py
```

```bash
python analisis/anova.py
```

## Salidas (se regeneran en cada corrida; están en `.gitignore`)

- `datos_limpios/` — `Fact_Encuesta`, `Dim_Cocina_Preferida`, `Dim_Ocasion`, `Dim_Franja_Visita`,
  `Dim_Frecuencia_Visita`, `Fact_Resenas`, `Dim_Restaurante`, `Dim_Fecha`, `Dim_Origen_Cliente` en CSV (utf-8-sig) y `parquet/`,
  más `reporte_calidad.md`, `reporte_validacion.md` y `metricas_etl.json`.
- `rechazados/` — filas eliminadas con `Codigo_Regla` y `Motivo`, y `resenas_a_investigar.csv` (marcadas, no eliminadas).
- `datasets/_manifiesto.json` — tamaño y SHA-256 de cada crudo.

Explicación completa de reglas y decisiones: [docs/PIPELINE.md](docs/PIPELINE.md).

## Análisis estadístico (`analisis/`)

`analisis/anova.py` lee `datos_limpios/` y prueba si las calificaciones cambian entre grupos
(17 pruebas sobre la encuesta y 3 sobre las reseñas). Para cada una comprueba los supuestos
(Shapiro-Wilk y Levene), aplica ANOVA o Kruskal-Wallis, corrige por comparaciones múltiples (Holm),
calcula el tamaño del efecto (η² / ε²) y hace post-hoc de Tukey cuando sale significativa.

Salidas en `analisis/resultados/`: `resultados_anova.md` (informe legible), `resumen_pruebas.csv`,
`descriptivos.csv`, `posthoc.csv` y `graficos/` (media ± IC 95 % por grupo).
