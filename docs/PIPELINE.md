# Pipeline ETL – Análisis de Opiniones de Clientes en Restaurante

Este documento explica **qué hace el pipeline, por qué y cómo se comprueba que quedó bien**. Sirve de base para
la sección "Descripción del ETL" del informe y para la presentación. La arquitectura sigue el repositorio de
referencia *Consumo_Energia_Residencial* (bitácora de reglas, cuarentena con motivo, contrato de esquema,
validación independiente), adaptada a **pandas** (los datos son pequeños y no se necesita Spark ni Java).

---

## 1. Visión general

Hay **dos pipelines independientes**. Los datasets no comparten ninguna clave, así que **no se cruzan**:
cada uno produce su propio modelo y en Power BI quedan como dos modelos separados.

```
              EXTRACT (pandas, todo como texto)        TRANSFORM (reglas E/R)          LOAD
 ┌──────────────────────────────┐                ┌──────────────────────┐     ┌─────────────────────────┐
 │ datasets/dataset_raw.csv     │──────────────▶ │ etl_encuesta.py      │───▶ │ Fact_Encuesta + 4 Dim   │
 │ (encuesta Iznia, 1.500)      │                │ E00 … E16            │     │                         │
 └──────────────────────────────┘                └──────────┬───────────┘     │ datos_limpios/          │
 ┌──────────────────────────────┐                ┌──────────┴───────────┐     │   *.csv  (utf-8-sig)    │
 │ datasets/gijon_resenas_…csv  │──────────────▶ │ etl_resenas.py       │───▶ │   parquet/*.parquet     │
 │ (TripAdvisor, 53.382)        │                │ R00 … R28            │     │ Fact_Resenas, Dim_Rest.,│
 │ datasets/gijon_ubicacion_…csv│──────────────▶ │ (+ ubicaciones.py,   │     │ Dim_Fecha, Dim_Origen_  │
 │ (origen del autor, 53.382)   │                │  palabras_vacias.py) │     │ Cliente, Fact_Palabras  │
 └──────────────────────────────┘                └──────────┬───────────┘     │ base_datos/             │
                                                            │                 │   opiniones_restaurantes│
                                                            │                 │   .db (SQLite, PK + FK) │
                                                            │                 └────────────┬────────────┘
                                                            ▼                              │
                                                      rechazados/                          ▼
                                               (cuarentena + Codigo_Regla + Motivo)  validar_calidad.py
                                                                                     (71 pruebas PASA/FALLA)
```

| Capa | Carpeta | Regla |
|---|---|---|
| Bronce (crudo) | `datasets/` | Se guarda exactamente lo que entregó la fuente. **Nunca se edita.** Solo se agrega `_manifiesto.json`. |
| Oro (negocio) | `datos_limpios/` | Modelo estrella listo para Power BI, en CSV y Parquet. Se regenera completo en cada corrida. |
| Oro (base de datos) | `base_datos/` | El mismo modelo estrella en una base SQLite (`opiniones_restaurantes.db`), con llaves primarias y foráneas. Se regenera en cada corrida. |
| Cuarentena | `rechazados/` | Lo que no pasó las reglas, con su valor original, `Codigo_Regla` y `Motivo`. |

Comandos (en este orden):

```bash
pip install -r requirements.txt
python etl/etl_main.py          # Extract + Transform + Load + reportes
python etl/validar_calidad.py   # validación independiente; código 1 si algo falla
```

| Archivo | Para qué |
|---|---|
| `etl/config.py` | Rutas, contratos de esquema, rangos de dominio, conjuntos permitidos, umbrales. Todas las decisiones en un solo lugar. |
| `etl/utilidades.py` | `Bitacora` (registra cada regla), `Cuarentena` (guarda rechazos con motivo), `a_nulo`, `exigir_columnas`, manifiesto SHA-256. |
| `etl/etl_encuesta.py` | Pipeline de la encuesta (reglas E). |
| `etl/etl_resenas.py` | Pipeline de TripAdvisor (reglas R) y construcción del modelo estrella. |
| `etl/ubicaciones.py` | Catálogo para normalizar la ubicación del autor: ciudad → comunidad autónoma, países, alias. |
| `etl/palabras_vacias.py` | Palabras vacías del español y de dominio que se excluyen del análisis de palabras clave (R28). |
| `preparacion/*.py` | Cómo se construyeron los crudos de TripAdvisor a partir de Zenodo (se corren una sola vez, ver §2.2). |
| `etl/cargar_sqlite.py` | Carga el modelo estrella en la base SQLite con DDL explícito (tipos, PRIMARY KEY, FOREIGN KEY) y la tabla `Bitacora_Reglas`. |
| `etl/etl_main.py` | Ejecuta ambos, carga las tablas (CSV, Parquet y SQLite), escribe `reporte_calidad.md` y `metricas_etl.json`. |
| `etl/validar_calidad.py` | Pruebas independientes (no importa nada del ETL; relee parquet y CSV crudos). |

---

## 2. EXTRACT

Las fuentes ya estaban descargadas, así que "extraer" es **leer los CSV** de `datasets/`:

- `dtype=str` y `keep_default_na=False`: **todo entra como texto** y nada se convierte a NaN por sorpresa.
  Cada conversión de tipo es explícita (`pd.to_numeric(..., errors="coerce")`, fechas con `format="%Y-%m-%d"`).
  Si un valor no convierte, queda nulo y una regla lo manda a cuarentena con su motivo.
- `encoding="utf-8"` estricto: si el archivo no fuera UTF-8 válido, la lectura falla en vez de producir texto roto.
- **Contrato de esquema** (`exigir_columnas`): si falta una columna esperada, el ETL se detiene.
- **Manifiesto** `datasets/_manifiesto.json`: nombre, tamaño y huella **SHA-256** de cada crudo. Si alguien
  cambia el archivo, la huella cambia: se sabe con qué versión exacta se hizo el análisis.

### 2.1 Auditoría inicial (paso 0, antes de escribir reglas)

| | Encuesta (`dataset_raw.csv`) | TripAdvisor (`gijon_resenas_es_2017_2023.csv`) |
|---|---|---|
| Filas × columnas | 1.500 × 19 | 53.382 × 14 |
| Codificación | UTF-8 sin BOM, fin de línea LF | UTF-8 sin BOM, fin de línea CRLF |
| Filas con nº de campos incorrecto | 0 | 0 |
| Duplicados exactos | 0 | 0 |
| Nulos | 0 en todas las columnas | `price_interval` 1.462 (2,7 %), `cuisine_types` 784 (1,5 %) |
| Id | `CustomerID` 654–2153, único | `review_id` único; 779 `restaurant_id` |
| Rangos | Age 18–69, Income 20.012–149.875, AverageSpend 10,3–200, WaitTime 0–60, GroupSize 1–9, ratings 1–5, binarias 0/1 | rating 1.0–5.0 (siempre entero), `restaurant_avg_rating` 1–5 en pasos de 0,5 |
| Fechas | (no tiene) | 2017-01-01 a **2023-09-05**; `year_month` coincide en el 100 % |
| Otros | Categorías limpias, sin erratas | 1 sola ciudad (Gijon), 1 solo idioma (es); 26 reseñas con texto repetido (13 textos); 4 nombres usados por 2 restaurantes (cadenas: Burger King, Al Peso…) |

Columnas reales de la encuesta: `CustomerID, Age, Gender, Income, VisitFrequency, AverageSpend,
PreferredCuisine, TimeOfVisit, GroupSize, DiningOccasion, MealType, OnlineReservation, DeliveryOrder,
LoyaltyProgramMember, WaitTime, ServiceRating, FoodRating, AmbianceRating, HighSatisfaction`.

Tercer archivo, `gijon_ubicacion_clientes.csv` (53.382 × 2: `review_id`, `user_location`): una fila por reseña,
`review_id` único y el mismo conjunto de ids que el archivo de reseñas. `user_location` es texto libre del
perfil del autor: **17.543 vacíos (32,9 %)** y 1.916 valores distintos con formatos mezclados
("Gijon, Spain", "gijon", "Gijón, Asturias, Spain", "Munich, Germany", "World").

**Conclusión de la auditoría:** ambos archivos llegan limpios. Por eso las reglas de rechazo afectan **0 filas**
en la corrida real. Las reglas se mantienen igual: son la red de seguridad si mañana llega otra versión del
archivo. Para comprobar que funcionan se hizo una prueba con filas sucias inyectadas (ver §6).

### 2.2 Cómo se construyeron los crudos de TripAdvisor (`preparacion/`)

Fuente: *TripAdvisor Restaurant Reviews* v2.0.0 (Zenodo, DOI 10.5281/zenodo.14622324, CC BY 4.0), archivo
`Gijón.zip` con tres tablas en pickle: `items` (restaurantes), `reviews` y `users`.

| Script | Qué hace | Resultado |
|---|---|---|
| `convertir_gijon.py` | Deja solo reseñas en español, une cada reseña con su restaurante, pasa el rating de 0–50 a 1–5 y normaliza fechas | 78.790 reseñas (37,1 MB) |
| `reducir_gijon.py` | Conserva años **completos y continuos** (2017–2023) para bajar de 30 MB sin distorsionar la tendencia mensual | `gijon_resenas_es_2017_2023.csv` (53.382, 24,7 MB) |
| `extraer_ubicacion_clientes.py` | Cruza `reviews → users` y guarda la ubicación **tal cual** la escribió el autor. No guarda `userId` ni nombre | `gijon_ubicacion_clientes.csv` |

En `users`, `userId = -1` es el marcador de "usuario desconocido" y aparece 7 veces con ubicaciones distintas;
sus 16 reseñas quedan con ubicación vacía en vez de asignarles una al azar. La **limpieza** de la ubicación no
se hace aquí sino en el ETL (R24–R27), para que quede documentada y validada como el resto.

---

## 3. Política de calidad

1. Lo inválido (nulos, imposibles, duplicados) **se elimina** y va a `rechazados/` con su `Motivo`.
   **No se imputa** con media, mediana ni moda.
2. **Nada se pierde en silencio**: cada regla registra cuántas filas afectó (`reporte_calidad.md`,
   `metricas_etl.json`) y se verifica que **leídas = válidas + rechazadas**.
3. **Valor atípico ≠ error.** Los rangos son de **dominio** (lo imposible: rating 7, edad 150, espera negativa),
   no estadísticos. Un cliente que gasta 200 o espera 59 minutos es un dato real y se conserva.
4. Normalización antes de validar: `trim` y `""`, `NA`, `N/A`, `nan`, `null`, `none`, `?`, `-` → nulo en columnas
   estructuradas. En **texto libre** (`title`, `text`) solo el vacío es nulo: un comentario que dice "NA"
   o "unknown" es una opinión, no un dato faltante.
5. Columnas con **más de 20 % de nulos** se evalúan y la decisión se documenta (en estos datos no hay ninguna).
6. Duplicados: se define el **grano** de cada tabla. Duplicado exacto → se conserva la primera copia.
   Mismo id con contenido distinto → **a investigar** (todas las versiones a cuarentena; no se elige una al azar).
7. Ids como **entero**, nunca decimal.
8. Carga **idempotente**: `datos_limpios/` y `rechazados/` se borran y regeneran en cada corrida.

---

## 4. TRANSFORM – Encuesta (Iznia) · reglas E

Grano de `Fact_Encuesta`: **una fila por encuestado** (`ID_Cliente`).

| Código | Dimensión | Regla y porqué | Filas |
|---|---|---|---:|
| E00 | Validez | Normalización (trim + marcas de nulo) | 0 |
| E01 | Completitud | Columnas con > 20 % de nulos: se evalúan | 0 |
| E02 | Completitud | `ID_Cliente` nulo → sin id no se sabe quién respondió | 0 |
| E03 | Validez | `ID_Cliente` no es entero positivo | 0 |
| E04 | Unicidad | Fila duplicada exacta → se conserva la primera | 0 |
| E05 | Unicidad | Mismo id con respuestas distintas → **A INVESTIGAR** (todas a cuarentena) | 0 |
| E06 | Completitud | Respuesta obligatoria nula → no se imputa | 0 |
| E07 | Validez | Texto no numérico, o decimal donde va un entero (ej. grupo 2,5) | 0 |
| E08 | Validez | Edad fuera de 18–100 (encuesta a adultos) | 0 |
| E09 | Validez | Ingreso ≤ 0 o > 1.000.000 | 0 |
| E10 | Validez | Gasto promedio ≤ 0 o > 1.000 | 0 |
| E11 | Validez | Espera fuera de 0–240 min | 0 |
| E12 | Validez | Grupo fuera de 1–30 personas | 0 |
| E13 | Validez | Calificación fuera de la escala Likert 1–5 | 0 |
| E14 | Validez | Banderas (reserva, domicilio, lealtad, alta satisfacción) distintas de 0/1 | 0 |
| E15 | Validez | Categoría fuera del conjunto permitido (detecta erratas tipo "Mle") | 0 |
| E16 | Consistencia | Derivadas: `Calif_Promedio`, `Genero_ES`, `Tipo_Comida_ES`, `Alta_Satisfaccion_ES` | 1.500 |

**Resultado:** 1.500 leídas · **1.500 válidas** · 0 rechazadas.

Salida:

| Tabla | Filas | Contenido |
|---|---:|---|
| `Fact_Encuesta` | 1.500 | 19 columnas originales renombradas a español + 4 derivadas. Los valores categóricos se conservan en su código original (inglés) y sirven de llave hacia las dimensiones. |
| `Dim_Cocina_Preferida` | 5 | Código → etiqueta en español + orden |
| `Dim_Ocasion` | 3 | Negocios, Casual, Celebración |
| `Dim_Franja_Visita` | 3 | Desayuno, Almuerzo, Cena (orden cronológico) |
| `Dim_Frecuencia_Visita` | 4 | Diaria → Rara vez (orden para ejes de gráficos) |

---

## 5. TRANSFORM – TripAdvisor Gijón · reglas R

| Código | Dimensión | Regla y porqué | Acción | Filas |
|---|---|---|---|---:|
| R00 | Validez | Normalización (texto libre: solo `""` es nulo) | Transformar | 2.246 nulos |
| R01 | Completitud | Columnas con > 20 % de nulos | Evaluar | 0 |
| R02–R03 | Completitud / Validez | `review_id` nulo o no entero | Eliminar | 0 |
| R04 | Unicidad | Reseña duplicada exacta | Eliminar copia | 0 |
| R05 | Unicidad | `review_id` repetido con contenido distinto | A investigar | 0 |
| R06 | Completitud | Obligatorio nulo (restaurante, fecha, rating, texto, idioma…) | Eliminar | 0 |
| R07 | Validez | `restaurant_id` no entero | Eliminar | 0 |
| R08 | Validez | `review_date` no cumple `AAAA-MM-DD` (formato explícito, nunca se adivina día/mes) | Eliminar | 0 |
| R09 | Consistencia | `year_month` ≠ año-mes de `review_date` | Eliminar | 0 |
| R10 | Validez | Fecha fuera de 2017–2023 | Eliminar | 0 |
| R11 | Validez | `rating` no numérico o con decimales (viene `5.0`; la escala es entera) | Eliminar | 0 |
| R12 | Validez | `rating` fuera de 1–5 | Eliminar | 0 |
| R13 | Validez | `restaurant_avg_rating` fuera de 1–5 o no múltiplo de 0,5 | Eliminar | 0 |
| R14 | Validez | `language` ≠ `es` | Eliminar | 0 |
| R15 | Validez | `city` ≠ `Gijon` | Eliminar | 0 |
| R16 | Validez | `price_interval` fuera de {$, $$ - $$$, $$$$} | Eliminar | 0 |
| R17 | Validez | `cuisine_match_encuesta` fuera de sus 8 categorías | Eliminar | 0 |
| R18 | Consistencia | Restaurante con atributos distintos entre sus reseñas (rompería `Dim_Restaurante`) | A investigar | 0 |
| R19 | Completitud | `price_interval` nulo → **se conserva** como "Sin dato" | Conservar y marcar | 1.462 |
| R20 | Completitud | `cuisine_types` nulo → **se conserva** como "Sin dato" | Conservar y marcar | 784 |
| R21 | Unicidad | Texto repetido en reseñas distintas → `Texto_Repetido = "Sí"` | Marcar (no borrar) | 26 |
| R22 | Validez | Caracteres corruptos de codificación (U+FFFD, mojibake `Ã©`) | Eliminar | 0 |
| R23 | Consistencia | `cuisine_match_encuesta` con < 100 reseñas → "Otras" en columna aparte | Derivar | 49 |
| R24 | Completitud | Reseña sin fila en el archivo de ubicaciones → origen "Sin dato" | Conservar y marcar | 0 |
| R25 | Completitud | Ubicación vacía en el perfil → `Tipo_Origen = "Sin dato"` (no se imputa) | Conservar y marcar | 17.543 |
| R26 | Validez | Ubicación que no permite saber el país ("World", "Europe", "viajero16") → "No determinado" | Conservar y marcar | 130 |
| R27 | Consistencia | Lugar de España fuera del catálogo `etl/ubicaciones.py` (o solo "Spain") → región "No identificada" | Conservar y marcar | 1.900 |
| R28 | Validez | Palabras clave: minúsculas, solo letras, ≥ 3 letras, sin palabras vacías; se guardan las 200 presentes en más reseñas (de 50.082 distintas) | Derivar tabla | 448.687 filas |

**Resultado:** 53.382 leídas · **53.382 válidas** · 0 rechazadas · 26 marcadas a investigar.

### Decisiones explicadas

- **Precio nulo (R19).** El precio es un atributo de la *ficha del restaurante*, no de la reseña. Las 1.462
  reseñas (210 restaurantes) tienen rating, fecha y texto válidos. Borrarlas sacaría del análisis de sentimiento a
  esos restaurantes sin motivo. Se conservan con `Nivel_Precio` nulo y `Precio_Etiqueta = "Sin dato"`, sin
  imputar. En Power BI se pueden excluir con un filtro cuando el análisis sea por precio.
- **`Nivel_Precio`**: `$` → 1 Económico, `$$ - $$$` → 2 Medio, `$$$$` → 3 Alto. El original queda en `Precio_Original`.
- **Cocina (R20).** `cuisine_types` es una lista en texto separada por `;` (en este archivo nunca tiene más de 2
  tipos). Se crean `Cocina_Principal` (el primer tipo) y `Num_Tipos_Cocina`; la lista original queda en `Cocinas_Original`.
- **`cuisine_match_encuesta` NO viene de TripAdvisor**: la derivó un compañero para relacionar cocinas con las
  de la encuesta. Se conserva tal cual (`Cocina_Encuesta_Original`). Aparte, `Cocina_Encuesta_Agrupada` junta
  `Chinese` (47) y `Chinese; Indian` (2) en "Otras". Ojo: "Other" (87 % de las reseñas, cocinas que no están en
  la encuesta) y "Otras" (categorías pequeñas) son cosas distintas.
- **`Sentimiento`** es una columna **derivada** (regla de negocio, no viene de la fuente): rating 1–2 Negativo,
  3 Neutro, 4–5 Positivo. `Sentimiento_Orden` (1-2-3) sirve para ordenar en Power BI.
- **Textos repetidos (R21).** 13 textos aparecen en 26 reseñas. Algunos parecen la misma persona publicando dos
  veces (ej. restaurante 23652638, mismo día, título, texto y rating, ids distintos); otros son textos idénticos en
  restaurantes distintos (posible spam o copia). Sin evidencia no se borran: se marcan y se listan en
  `rechazados/resenas_a_investigar.csv`.
- **Origen del cliente (R24–R27).** Es la ubicación que el autor declara en su perfil de TripAdvisor, no la del
  restaurante (todos están en Gijón). Responde al objetivo de "satisfacción de clientes por región". El texto se
  normaliza (minúsculas, sin tildes, la coma y los paréntesis separan partes) y se busca en un catálogo propio:
  - País: la última parte ("Spain", "Germany"; los estados de EE. UU. y las provincias de Canadá también cuentan).
    Si la última parte es un lugar español conocido ("gijon", "madrid") el país es España.
  - Ciudad y comunidad autónoma: primera parte que esté en el catálogo. Un nombre de región o provincia sin
    ciudad ("Asturias", "Province of Leon") da la región con ciudad "No identificada".
  - **Solo se mapea lo que no es ambiguo**: "San Lorenzo" o "Villamartín" existen en varias comunidades y quedan
    como "No identificada". El catálogo identifica la comunidad autónoma en el **94,5 %** de las reseñas de autores españoles.
  - `Tipo_Origen`: *Gijón (local)* (incluye Somió, Roces, La Calzada), *Resto de Asturias*, *Resto de España*,
    *Extranjero*, *No determinado*, *Sin dato*.
  - Nada se borra: una reseña sin ubicación sigue siendo válida para todos los demás análisis.
- **Palabras clave (R28).** Cada reseña se parte en palabras (solo letras, en minúsculas), se quitan las palabras
  vacías (`etl/palabras_vacias.py`: artículos, preposiciones, verbos auxiliares y palabras de dominio que no opinan,
  como "restaurante", "sitio", "fuimos" o "Gijón") y se unifican variantes con y sin tilde ("menu" → "menú").
  Se conservan a propósito las que sí describen la experiencia aunque sean frecuentes (comida, servicio, precio,
  caro, espera) y los adjetivos de valoración (buena, mal, excelente), que permiten comparar positivas y negativas.
  Cada palabra cuenta **una vez por reseña**, así que contar filas de `Fact_Palabras` da "reseñas que la mencionan".
  Se guardan las 200 más frecuentes: alcanzan para cualquier top y mantienen la tabla en 8 MB.
- **Quejas específicas.** No se calculan en el ETL sino en Power BI con `SEARCH` (requerimiento DAX 7). Los
  términos y los conteos esperados están en [MEDIDAS_DAX.md](MEDIDAS_DAX.md).
- **Dos promedios por restaurante.** `Rating_Promedio_TripAdvisor` es el que publica TripAdvisor (todas sus
  reseñas, todos los idiomas, redondeado a 0,5). `Rating_Promedio_Resenas` se calcula con *nuestras* reseñas en
  español 2017–2023. No tienen por qué coincidir.

### Modelo estrella

```
                  Dim_Fecha (2.556 días)
                 Fecha ◄──────────┐
                                   │ N:1
  Dim_Restaurante (779)      Fact_Resenas (53.382)              Dim_Origen_Cliente (1.515)
  Restaurant_ID ◄────────── Restaurant_ID, Origen_ID, Fecha ───► Origen_ID, Ciudad, Región,
                             Rating, Sentimiento, Texto…          País, Tipo_Origen
                                   ▲ 1:N
                             Fact_Palabras (448.687)
                             Review_ID, Palabra
```

| Tabla | Grano | Columnas clave |
|---|---|---|
| `Fact_Resenas` | 1 fila por reseña | `Review_ID` (PK), `Restaurant_ID` (FK), `Fecha` (FK), `Rating`, `Sentimiento`, `Titulo`, `Texto`, `Longitud_Texto`, `Texto_Repetido`, `Idioma`, `Origen_ID` (FK, última columna) |
| `Dim_Restaurante` | 1 fila por restaurante | `Restaurant_ID` (PK), nombre, precio (original, nivel, etiqueta), cocina (original, principal, nº tipos, encuesta original/agrupada), los dos promedios, `Num_Resenas` |
| `Dim_Origen_Cliente` | 1 fila por tipo + país + región + ciudad del autor | `Origen_ID` (PK), `Ciudad_Cliente`, `Region_Cliente` (comunidad autónoma, "Extranjero", "No identificada"…), `Pais_Cliente`, `Tipo_Origen`, `Tipo_Origen_Orden`, `Num_Resenas` |
| `Fact_Palabras` | 1 fila por reseña y palabra clave (solo las 200 más frecuentes) | `Review_ID` (FK a `Fact_Resenas`), `Palabra` |
| `Dim_Fecha` | 1 fila por día, 2017-01-01 a 2023-12-31 | `Fecha` (PK), `Anio`, `Semestre`, `Trimestre`, `Mes`, `Nombre_Mes`, `Anio_Mes`, `Dia`, `Dia_Semana` (1 = lunes), `Nombre_Dia`, `Es_Fin_De_Semana` |

`Dim_Fecha` cubre **años completos** (aunque las reseñas acaban el 2023-09-05) porque la inteligencia de tiempo de
Power BI exige un calendario continuo.

### Base de datos SQLite (`base_datos/opiniones_restaurantes.db`)

Además de los CSV y Parquet, el LOAD escribe las 10 tablas en una base **SQLite** (un solo archivo, sin servidor).
Cada tabla se crea con DDL explícito: tipos (`INTEGER`, `REAL`, `TEXT`), `PRIMARY KEY` y `FOREIGN KEY`
(`Fact_Resenas` → `Dim_Restaurante`, `Dim_Fecha`, `Dim_Origen_Cliente`; `Fact_Palabras` → `Fact_Resenas`;
`Fact_Encuesta` → sus 4 dimensiones). Las fechas se guardan como texto ISO (`AAAA-MM-DD`). Se agrega la tabla
`Bitacora_Reglas` con cada regla aplicada y las filas que afectó. Al terminar, `PRAGMA foreign_key_check` debe dar
cero huérfanos o el ETL se detiene. El ANOVA (`analisis/anova.py`) lee sus datos de esta base con SQL.

Ejemplo de consulta (con `sqlite3` o DB Browser for SQLite):

```sql
SELECT d.Cocina_Principal, COUNT(*) AS Resenas, ROUND(AVG(r.Rating), 2) AS Rating
FROM Fact_Resenas r JOIN Dim_Restaurante d ON d.Restaurant_ID = r.Restaurant_ID
GROUP BY d.Cocina_Principal HAVING COUNT(*) >= 1000 ORDER BY Rating DESC;
```

---

## 6. VALIDACIÓN (`etl/validar_calidad.py`)

Es **independiente**: no importa ningún módulo del ETL. Relee los parquet y los CSV crudos y recalcula por su
cuenta. Resultado real: **71/71 PASA** (detalle en `datos_limpios/reporte_validacion.md`).

| Dimensión | Qué se prueba |
|---|---|
| Completitud | Sin nulos en columnas obligatorias de las 10 tablas; filas del crudo = válidas + rechazadas; toda fila rechazada tiene `Motivo` y `Codigo_Regla`; los restaurantes sin precio dicen "Sin dato" |
| Validez | Rangos de dominio y categorías permitidas en ambas fuentes; UTF-8 sin caracteres de reemplazo; `Tipo_Origen` en sus 6 categorías y coherente con país y región; palabras clave solo con letras, ≥ 3 letras y como máximo 200 |
| Unicidad | Las 9 llaves primarias sin repetir; ids enteros; una fila de `Dim_Origen_Cliente` por combinación de origen; cada palabra una sola vez por reseña |
| Integridad referencial | `Fact_Resenas` → `Dim_Restaurante`, `Dim_Fecha` y `Dim_Origen_Cliente`; `Fact_Palabras` → `Fact_Resenas`; `Fact_Encuesta` → sus 4 dimensiones; sin huérfanas; el archivo de ubicaciones tiene exactamente una fila por reseña |
| Consistencia | Sentimiento coherente con rating; calendario continuo; Trimestre/Semestre/Año-Mes coherentes; `Calif_Promedio` correcto; `Num_Resenas` = conteo real (restaurante y origen); `Nivel_Precio` coherente con el original |
| Exactitud | Recalculado **desde el crudo**: promedio de rating por restaurante (779), reseñas por año, promedio de FoodRating y % de HighSatisfaction, gasto total; las reseñas con origen "Sin dato" son exactamente las que tienen ubicación vacía en el crudo; reseñas que contienen la palabra clave más frecuente ("comida", 18.786) |
| Base de datos | El `.db` existe y pasa `PRAGMA integrity_check`; tiene las 10 tablas y `Bitacora_Reglas`; mismas filas que `datos_limpios/` tabla por tabla; `PRAGMA foreign_key_check` sin huérfanos; rating promedio y reseñas negativas por SQL = datos limpios |

**Prueba de las reglas con datos sucios.** Como los archivos reales no tienen errores, se corrió el ETL sobre una
copia (fuera del proyecto) con filas inyectadas: edad 150, rating 7, "Mle", ingreso "NA", grupo 2,5, reserva = 2,
espera −3, gasto "abc", duplicados exactos, ids repetidos, fecha `05/03/2019`, `year_month` incoherente, idioma
`en`, texto vacío, fecha 2024. **Cada fila sucia fue atrapada por la regla esperada** (E04–E08, E11, E13–E15,
R04, R06, R08–R10, R12, R14) y el balance leídas = válidas + rechazadas se mantuvo.

---

## 7. Limitaciones

- **Una sola ciudad (Gijón)** y solo reseñas en español: las conclusiones no se generalizan a otras ciudades ni a
  turistas que escriben en otro idioma.
- **2023 está incompleto** (hasta el 5 de septiembre) y 2020–2021 tienen menos reseñas (pandemia): comparar
  años con conteos absolutos es engañoso; conviene usar promedios o proporciones.
- `cuisine_match_encuesta` es una clasificación hecha por el equipo, no por TripAdvisor; 87 % cae en "Other".
- La encuesta y las reseñas **no se pueden cruzar** a nivel de registro (no comparten clave ni población).
  Solo se pueden comparar a nivel agregado (por ejemplo, por tipo de cocina), y con cuidado.
- La encuesta no trae fecha ni moneda explícita para ingreso y gasto.
- El **origen del cliente** es lo que el autor escribió en su perfil: puede estar desactualizado, el 32,9 % no lo
  tiene y "Asturias" sin ciudad cuenta como *Resto de Asturias* aunque pudiera ser de Gijón. Se analiza por región
  del **cliente**, no por ciudad del restaurante (todos los restaurantes están en Gijón).
