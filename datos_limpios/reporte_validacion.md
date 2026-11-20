# Reporte de validación

Generado por `etl/validar_calidad.py` (independiente del ETL).

Pruebas: 71 | Pasan: 71 | Fallan: 0

| Resultado | Dimensión | Prueba | Detalle |
|---|---|---|---|
| PASA | Completitud | Fact_Encuesta: sin nulos en columnas obligatorias | 0 nulos |
| PASA | Completitud | Dim_Cocina_Preferida: sin nulos en columnas obligatorias | 0 nulos |
| PASA | Completitud | Dim_Ocasion: sin nulos en columnas obligatorias | 0 nulos |
| PASA | Completitud | Dim_Franja_Visita: sin nulos en columnas obligatorias | 0 nulos |
| PASA | Completitud | Dim_Frecuencia_Visita: sin nulos en columnas obligatorias | 0 nulos |
| PASA | Completitud | Fact_Resenas: sin nulos en columnas obligatorias | 0 nulos |
| PASA | Completitud | Dim_Restaurante: sin nulos en columnas obligatorias | 0 nulos |
| PASA | Completitud | Dim_Fecha: sin nulos en columnas obligatorias | 0 nulos |
| PASA | Completitud | Dim_Origen_Cliente: sin nulos en columnas obligatorias | 0 nulos |
| PASA | Completitud | Fact_Palabras: sin nulos en columnas obligatorias | 0 nulos |
| PASA | Completitud | encuesta: leídas (crudo) = válidas + rechazadas | 1,500 = 1,500 + 0 |
| PASA | Completitud | encuesta: el ETL leyó todas las filas del crudo | 1,500 vs 1,500 |
| PASA | Completitud | encuesta: toda fila rechazada tiene Motivo y Codigo_Regla | 0 rechazadas |
| PASA | Completitud | resenas: leídas (crudo) = válidas + rechazadas | 53,382 = 53,382 + 0 |
| PASA | Completitud | resenas: el ETL leyó todas las filas del crudo | 53,382 vs 53,382 |
| PASA | Completitud | resenas: toda fila rechazada tiene Motivo y Codigo_Regla | 0 rechazadas |
| PASA | Completitud | Restaurantes sin precio etiquetados 'Sin dato' (no imputados) | 210 restaurantes |
| PASA | Validez | Encuesta: edad 18-100 | 18-69 |
| PASA | Validez | Encuesta: calificaciones enteras 1-5 |  |
| PASA | Validez | Encuesta: espera 0-240 min, grupo 1-30, ingreso y gasto > 0 |  |
| PASA | Validez | Encuesta: banderas binarias 0/1 |  |
| PASA | Validez | Encuesta: categorías dentro del conjunto permitido |  |
| PASA | Validez | Reseñas: rating entero 1-5 |  |
| PASA | Validez | Reseñas: fechas dentro de 2017-2023 | 2017-01-01 a 2023-09-05 |
| PASA | Validez | Reseñas: idioma 'es' y texto no vacío |  |
| PASA | Validez | Reseñas: sin caracteres de reemplazo U+FFFD (UTF-8 correcto) |  |
| PASA | Validez | Restaurante: Nivel_Precio en {1,2,3} o nulo; promedio TripAdvisor 1-5 |  |
| PASA | Validez | Origen: Tipo_Origen dentro de las 6 categorías y Tipo_Origen_Orden coherente |  |
| PASA | Validez | Palabras clave: solo letras en minúsculas, mínimo 3, a lo sumo 200 distintas | 200 palabras distintas |
| PASA | Validez | Origen: país extranjero <-> región 'Extranjero'; España <-> tipos locales/España |  |
| PASA | Unicidad | Fact_Encuesta: llave ID_Cliente sin repetir | 0 repetidas |
| PASA | Unicidad | Dim_Cocina_Preferida: llave Cocina_Preferida sin repetir | 0 repetidas |
| PASA | Unicidad | Dim_Ocasion: llave Ocasion sin repetir | 0 repetidas |
| PASA | Unicidad | Dim_Franja_Visita: llave Franja_Visita sin repetir | 0 repetidas |
| PASA | Unicidad | Dim_Frecuencia_Visita: llave Frecuencia_Visita sin repetir | 0 repetidas |
| PASA | Unicidad | Fact_Resenas: llave Review_ID sin repetir | 0 repetidas |
| PASA | Unicidad | Dim_Restaurante: llave Restaurant_ID sin repetir | 0 repetidas |
| PASA | Unicidad | Dim_Fecha: llave Fecha sin repetir | 0 repetidas |
| PASA | Unicidad | Dim_Origen_Cliente: llave Origen_ID sin repetir | 0 repetidas |
| PASA | Unicidad | Fact_Palabras: cada palabra cuenta una sola vez por reseña | 0 repetidas |
| PASA | Unicidad | Dim_Origen_Cliente: una fila por tipo + país + región + ciudad | 0 repetidas |
| PASA | Unicidad | IDs como entero (no decimal) |  |
| PASA | Integridad ref. | Fact_Resenas.Restaurant_ID -> Dim_Restaurante.Restaurant_ID | 0 huérfanas |
| PASA | Integridad ref. | Fact_Resenas.Origen_ID -> Dim_Origen_Cliente.Origen_ID | 0 huérfanas |
| PASA | Integridad ref. | Fact_Palabras.Review_ID -> Fact_Resenas.Review_ID | 0 huérfanas |
| PASA | Integridad ref. | Fact_Resenas.Fecha -> Dim_Fecha.Fecha | 0 huérfanas |
| PASA | Integridad ref. | Fact_Encuesta.Cocina_Preferida -> Dim_Cocina_Preferida.Cocina_Preferida | 0 huérfanas |
| PASA | Integridad ref. | Fact_Encuesta.Ocasion -> Dim_Ocasion.Ocasion | 0 huérfanas |
| PASA | Integridad ref. | Fact_Encuesta.Franja_Visita -> Dim_Franja_Visita.Franja_Visita | 0 huérfanas |
| PASA | Integridad ref. | Fact_Encuesta.Frecuencia_Visita -> Dim_Frecuencia_Visita.Frecuencia_Visita | 0 huérfanas |
| PASA | Integridad ref. | Todo restaurante de la dimensión tiene al menos una reseña | 0 sin reseñas |
| PASA | Integridad ref. | Archivo de ubicaciones: exactamente una fila por reseña del crudo | 53,382 filas |
| PASA | Consistencia | Sentimiento coherente con rating (1-2 Neg, 3 Neu, 4-5 Pos) |  |
| PASA | Consistencia | Dim_Fecha: calendario continuo de años completos (2017-01-01 a 2023-12-31) | 2,556 días |
| PASA | Consistencia | Dim_Fecha: Anio_Mes, Trimestre y Semestre coherentes con la fecha |  |
| PASA | Consistencia | Encuesta: Calif_Promedio = media de las 3 calificaciones |  |
| PASA | Consistencia | Dim_Restaurante.Num_Resenas = conteo real en Fact_Resenas |  |
| PASA | Consistencia | Dim_Origen_Cliente.Num_Resenas = conteo real en Fact_Resenas |  |
| PASA | Consistencia | Nivel_Precio coherente con price_interval original |  |
| PASA | Exactitud | Promedio de rating por restaurante = recalculado desde el crudo | máxima diferencia 0.000050 en 779 restaurantes |
| PASA | Exactitud | Reseñas por año = conteo desde el crudo | {2017: 12143, 2018: 11340, 2019: 10268, 2020: 5861, 2021: 5103, 2022: 5497, 2023: 3170} |
| PASA | Exactitud | Encuesta: promedio FoodRating y % HighSatisfaction = crudo | 2.9973 / 13.40% |
| PASA | Exactitud | Gasto promedio total de la encuesta = crudo |  |
| PASA | Exactitud | Palabra clave más frecuente: reseñas que la contienen = recalculado desde el crudo | 'comida': 18,786 vs 18,786 |
| PASA | Exactitud | Origen 'Sin dato' = reseñas con ubicación vacía en el crudo (nada imputado) | 17,543 reseñas |
| PASA | Base de datos | Existe base_datos/opiniones_restaurantes.db |  |
| PASA | Base de datos | Integridad del archivo (PRAGMA integrity_check = ok) |  |
| PASA | Base de datos | Tiene las 10 tablas del modelo y la bitácora de reglas | 11 tablas |
| PASA | Base de datos | Mismas filas en la base que en datos_limpios/ (tabla por tabla) | 508,434 filas |
| PASA | Base de datos | Llaves foráneas sin huérfanos (PRAGMA foreign_key_check) | 0 huérfanos |
| PASA | Base de datos | Rating promedio y reseñas negativas por SQL = datos_limpios/ | 3.8682 / 10,152 |
