# Reporte de calidad del ETL

Generado automáticamente por `etl/etl_main.py`. Cada fila es una regla aplicada y cuántos registros afectó. Las filas eliminadas están en `rechazados/` con las columnas `Codigo_Regla` y `Motivo`.


## Encuesta

Leídas: **1,500** | Válidas: **1,500** | Rechazadas: **0**

| Código | Regla | Dimensión | Acción | Filas |
|---|---|---|---|---:|
| E00 | Normalización: celdas con espacios sobrantes recortadas | Validez | Transformar | 0 |
| E01 | Columnas con > 20% de nulos (se evalúan, no se borran) | Completitud | Evaluar | 0 |
| E02 | ID_Cliente nulo | Completitud | Eliminar (cuarentena) | 0 |
| E03 | ID_Cliente no es un entero positivo | Validez | Eliminar (cuarentena) | 0 |
| E04 | Fila duplicada exacta (se conserva la primera) | Unicidad | Eliminar (cuarentena) | 0 |
| E05 | ID_Cliente repetido con respuestas distintas - A INVESTIGAR | Unicidad | Eliminar (cuarentena) | 0 |
| E06 | Alguna respuesta obligatoria nula (no se imputa) | Completitud | Eliminar (cuarentena) | 0 |
| E07 | Valor no numérico o decimal donde se espera un entero | Validez | Eliminar (cuarentena) | 0 |
| E08 | Edad fuera de 18-100 años | Validez | Eliminar (cuarentena) | 0 |
| E09 | Ingreso <= 0 o > 1.000.000 | Validez | Eliminar (cuarentena) | 0 |
| E10 | Gasto promedio <= 0 o > 1.000 | Validez | Eliminar (cuarentena) | 0 |
| E11 | Tiempo de espera fuera de 0-240 min | Validez | Eliminar (cuarentena) | 0 |
| E12 | Tamaño de grupo fuera de 1-30 personas | Validez | Eliminar (cuarentena) | 0 |
| E13 | Calificación fuera de la escala 1-5 | Validez | Eliminar (cuarentena) | 0 |
| E14 | Bandera binaria distinta de 0/1 | Validez | Eliminar (cuarentena) | 0 |
| E15 | Categoría fuera del conjunto permitido | Validez | Eliminar (cuarentena) | 0 |
| E16 | Derivadas: Calif_Promedio (media de 3 calificaciones) y etiquetas en español | Consistencia | Derivar | 1,500 |

## Resenas

Leídas: **53,382** | Válidas: **53,382** | Rechazadas: **0**

| Código | Regla | Dimensión | Acción | Filas |
|---|---|---|---|---:|
| R00 | Normalización: trim + marcas de nulo ('', NA, ?, -) en columnas estructuradas (texto libre solo ''); nulos resultantes | Validez | Transformar | 2,246 |
| R01 | Columnas con > 20% de nulos (se evalúan, no se borran) | Completitud | Evaluar | 0 |
| R02 | review_id nulo | Completitud | Eliminar (cuarentena) | 0 |
| R03 | review_id no es un entero positivo | Validez | Eliminar (cuarentena) | 0 |
| R04 | Reseña duplicada exacta (se conserva la primera) | Unicidad | Eliminar (cuarentena) | 0 |
| R05 | review_id repetido con contenido distinto - A INVESTIGAR | Unicidad | Eliminar (cuarentena) | 0 |
| R06 | Campo obligatorio nulo (id restaurante, fecha, rating, texto...) | Completitud | Eliminar (cuarentena) | 0 |
| R07 | restaurant_id no es un entero positivo | Validez | Eliminar (cuarentena) | 0 |
| R08 | review_date no cumple el formato AAAA-MM-DD | Validez | Eliminar (cuarentena) | 0 |
| R09 | year_month no coincide con review_date | Consistencia | Eliminar (cuarentena) | 0 |
| R10 | Fecha fuera del periodo 2017-2023 | Validez | Eliminar (cuarentena) | 0 |
| R11 | rating no numérico o con decimales (la escala es entera) | Validez | Eliminar (cuarentena) | 0 |
| R12 | rating fuera de 1-5 | Validez | Eliminar (cuarentena) | 0 |
| R13 | restaurant_avg_rating fuera de 1-5 o no múltiplo de 0,5 | Validez | Eliminar (cuarentena) | 0 |
| R14 | Idioma distinto de 'es' | Validez | Eliminar (cuarentena) | 0 |
| R15 | Ciudad distinta de Gijon | Validez | Eliminar (cuarentena) | 0 |
| R16 | price_interval fuera de {$, $$ - $$$, $$$$} | Validez | Eliminar (cuarentena) | 0 |
| R17 | cuisine_match_encuesta fuera de las 8 categorías conocidas | Validez | Eliminar (cuarentena) | 0 |
| R18 | Restaurante con atributos contradictorios entre reseñas - A INVESTIGAR | Consistencia | Eliminar (cuarentena) | 0 |
| R19 | price_interval nulo -> se conserva con Nivel_Precio 'Sin dato' | Completitud | Conservar y marcar | 1,462 |
| R20 | cuisine_types nulo -> se conserva con Cocina_Principal 'Sin dato' | Completitud | Conservar y marcar | 784 |
| R21 | Texto repetido en reseñas distintas -> se marca Texto_Repetido='Sí' y se lista en rechazados/resenas_a_investigar.csv (no se borra) | Unicidad | Marcar | 26 |
| R22 | Texto con caracteres corruptos de codificación | Validez | Eliminar (cuarentena) | 0 |
| R24 | Reseña sin fila en el archivo de ubicaciones -> se conserva con Tipo_Origen 'Sin dato' | Completitud | Conservar y marcar | 0 |
| R25 | Ubicación vacía en el perfil -> Tipo_Origen 'Sin dato' (no se imputa) | Completitud | Conservar y marcar | 17,543 |
| R26 | Ubicación que no permite saber el país ('World', 'Europe'...) -> 'No determinado' | Validez | Conservar y marcar | 130 |
| R27 | Lugar de España fuera del catálogo de etl/ubicaciones.py -> Region_Cliente 'No identificada' (la ciudad se conserva como viene) | Consistencia | Conservar y marcar | 1,900 |
| R23 | cuisine_match_encuesta con < 100 reseñas agrupadas en 'Otras': ['Chinese', 'Chinese; Indian'] (reseñas afectadas) | Consistencia | Derivar columna aparte | 49 |
| R28 | Palabras clave: texto en minúsculas, solo letras, >= 3 letras, sin palabras vacías (etl/palabras_vacias.py); se guardan las 200 presentes en más reseñas de 50,082 distintas (filas de Fact_Palabras) | Validez | Derivar tabla | 448,687 |

## Tablas cargadas

| Tabla | Filas |
|---|---:|
| Fact_Encuesta | 1,500 |
| Dim_Cocina_Preferida | 5 |
| Dim_Ocasion | 3 |
| Dim_Franja_Visita | 3 |
| Dim_Frecuencia_Visita | 4 |
| Fact_Resenas | 53,382 |
| Dim_Restaurante | 779 |
| Dim_Fecha | 2,556 |
| Dim_Origen_Cliente | 1,515 |
| Fact_Palabras | 448,687 |
