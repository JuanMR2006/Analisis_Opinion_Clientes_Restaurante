# Medidas DAX del dashboard

Todas las medidas viven en la tabla `medidas` del archivo `powerbi/powerbiProyecto.pbix`. Este documento sirve
para la sección **"Medidas DAX explicadas"** del informe. Para cada medida se indica qué calcula, a qué
requerimiento DAX del enunciado responde y el **valor esperado sin filtros**, recalculado en Python desde
`datos_limpios/`, para comprobar que la fórmula está bien.

Si una fórmula da error de sintaxis, es porque Power BI está configurado con `;` como separador de listas:
cambia las comas que separan argumentos por punto y coma.

## Requerimientos DAX del enunciado y dónde se cumplen

| # | Requerimiento | Medidas |
|---|---|---|
| 1 | Agregación: SUM, AVERAGE, COUNT | `Total Reseñas` (COUNTROWS), `Rating Promedio` (AVERAGE), `Total Caracteres` y `Gasto Total Encuesta` (SUM) |
| 2 | Filtros: CALCULATE + contexto | `% Positivas`, `% Neutras`, `% Negativas`, `Reseñas Negativas` |
| 3 | Segmentación temporal (año, mes, día, trimestre) | `Reseñas Promedio por Mes` y los visuales por `Anio`, `Mes_Fecha`, `Trimestre` y `Nombre_Dia` |
| 4 | Inteligencia de tiempo (YTD, MTD, SAMEPERIODLASTYEAR) | `Rating Año Anterior`, `Reseñas YTD`, `Reseñas MTD` |
| 5 | Clasificación (RANKX) | `Ranking Restaurante` |
| 6 | Variables (VAR … RETURN) | `Variación vs Año Anterior`, las 8 medidas de quejas, `Correlación Longitud-Rating`, `Ranking Restaurante` |
| 7 | Texto o búsqueda (SEARCH, FIND) | Las 8 medidas `Quejas - …` |
| 8 | Relación entre dos variables (visual + DAX) | `Correlación Longitud-Rating` + gráfico de dispersión |
| 9 | KPI personalizado | `Índice Neto de Satisfacción`, `% Alta Satisfacción`, `% Negativas con Queja` |
| 10 | Tendencia o desviación estándar | `Desviación Rating`, `Coeficiente de Variación` + línea de tendencia en el gráfico mensual |

---

## 1. Reseñas: agregación y filtros

| Medida | Fórmula | Esperado |
|---|---|---|
| Total Reseñas | `COUNTROWS(Fact_Resenas)` | 53.382 |
| Rating Promedio | `AVERAGE(Fact_Resenas[Rating])` | 3,87 |
| Restaurantes | `DISTINCTCOUNT(Fact_Resenas[Restaurant_ID])` | 779 |
| Total Caracteres | `SUM(Fact_Resenas[Longitud_Texto])` | 18.685.810 |
| Longitud Promedio | `AVERAGE(Fact_Resenas[Longitud_Texto])` | 350,0 |
| Reseñas Negativas | `CALCULATE([Total Reseñas], Fact_Resenas[Sentimiento] = "Negativo")` | 10.152 |
| % Positivas | `DIVIDE(CALCULATE([Total Reseñas], Fact_Resenas[Sentimiento] = "Positivo"), [Total Reseñas])` | 70,9 % |
| % Neutras | igual, con `"Neutro"` | 10,1 % |
| % Negativas | igual, con `"Negativo"` | 19,0 % |
| Rating (mín. 30 reseñas) | `IF([Total Reseñas] >= 30, [Rating Promedio])` | (por restaurante) |

**CALCULATE** cambia el contexto de filtro: cuenta las reseñas como si solo existieran las de un sentimiento,
pero respeta los demás filtros de la página (año, precio, origen).

## 2. Tiempo

| Medida | Fórmula | Esperado |
|---|---|---|
| Reseñas Promedio por Mes | `AVERAGEX(VALUES(Dim_Fecha[Anio_Mes]), [Total Reseñas])` | 659,04 (2017: 1.011,92; 2023: 352,22) |
| Rating Año Anterior | `CALCULATE([Rating Promedio], SAMEPERIODLASTYEAR(Dim_Fecha[Fecha]))` | 2018 → 3,89 (el de 2017) |
| Reseñas YTD | `TOTALYTD([Total Reseñas], Dim_Fecha[Fecha])` | junio de 2019 → 4.363 |
| Reseñas MTD | `TOTALMTD([Total Reseñas], Dim_Fecha[Fecha])` | igual que el total del mes, en un visual por día |

`Reseñas Promedio por Mes` existe porque 2023 llega solo hasta septiembre y 2020–2021 tienen menos reseñas por
la pandemia: comparar totales anuales engaña, el promedio mensual no. `AVERAGEX` ignora los meses sin reseñas
(octubre a diciembre de 2023), así que no bajan el promedio.

```DAX
Variación vs Año Anterior =
VAR Actual = [Rating Promedio]
VAR Anterior = [Rating Año Anterior]
RETURN
    IF ( HASONEVALUE ( Dim_Fecha[Anio] ) && NOT ISBLANK ( Anterior ), Actual - Anterior )
```
Esperado: 2018 +0,01 · 2019 −0,05 · 2020 +0,08 · 2021 −0,12 · 2022 +0,03 · 2023 −0,11. `HASONEVALUE` deja vacía
la fila de total, donde la comparación no tiene sentido.

## 3. Clasificación (RANKX)

```DAX
Ranking Restaurante =
VAR MinResenas = 30
RETURN
    IF (
        HASONEVALUE ( Dim_Restaurante[Nombre] ) && [Total Reseñas] >= MinResenas,
        RANKX (
            FILTER ( ALL ( Dim_Restaurante[Nombre] ), [Total Reseñas] >= MinResenas ),
            [Rating Promedio], , DESC, DENSE
        )
    )
```
Esperado: 1 Aroma Pizza Artesana (4,97) · 2 Primero Cafe (4,88) · 3 Arti pizza (4,87) · 4 Sidreria Parrilla La
Allandesa (4,83) · 5 Flow Food (4,81). Entran 367 restaurantes con al menos 30 reseñas; el último puesto
(352, por empates con `DENSE`) es Burger King con 1,32. El mínimo de 30 evita que un restaurante con 2 reseñas
de 5 estrellas quede primero.

## 4. Quejas específicas (SEARCH + VAR)

Cuentan cuántas **reseñas negativas** (rating 1–2) mencionan cada tema. `SEARCH` no distingue mayúsculas y
devuelve 0 (último argumento) si no encuentra el texto. Se incluyen las variantes con y sin tilde. Es una
**detección por palabras clave**: aproximada (no entiende negaciones ni ironía), pero transparente y fácil de
explicar. Los términos se revisaron con ejemplos reales para quitar falsos positivos ("borde" encontraba
"bordes de pizza"; "timo" encontraba "último").

Patrón de todas las medidas:

```DAX
Quejas - Lentitud =
VAR Negativas = FILTER ( Fact_Resenas, Fact_Resenas[Sentimiento] = "Negativo" )
RETURN
    COUNTROWS (
        FILTER (
            Negativas,
            VAR t = Fact_Resenas[Texto]
            RETURN
                SEARCH ( "lento", t, 1, 0 ) > 0 || SEARCH ( "lenta", t, 1, 0 ) > 0
                    || SEARCH ( "lentos", t, 1, 0 ) > 0 || SEARCH ( "lentas", t, 1, 0 ) > 0
                    || SEARCH ( "lentitud", t, 1, 0 ) > 0 || SEARCH ( "tardaron", t, 1, 0 ) > 0
                    || SEARCH ( "tardan", t, 1, 0 ) > 0 || SEARCH ( "tardó", t, 1, 0 ) > 0
                    || SEARCH ( "tardamos", t, 1, 0 ) > 0 || SEARCH ( "tardanza", t, 1, 0 ) > 0
                    || SEARCH ( "tardísimo", t, 1, 0 ) > 0 || SEARCH ( "esperamos", t, 1, 0 ) > 0
                    || SEARCH ( "esperando", t, 1, 0 ) > 0 || SEARCH ( "esperar", t, 1, 0 ) > 0
                    || SEARCH ( "tiempo de espera", t, 1, 0 ) > 0 || SEARCH ( "hora de espera", t, 1, 0 ) > 0
                    || SEARCH ( "mucha espera", t, 1, 0 ) > 0 || SEARCH ( "larga espera", t, 1, 0 ) > 0
        )
    ) + 0
```

| Medida | Términos buscados | Esperado | % de negativas |
|---|---|---:|---:|
| Quejas - Lentitud | lento, lenta, lentos, lentas, lentitud, tardaron, tardan, tardó, tardamos, tardanza, tardísimo, esperamos, esperando, esperar, tiempo de espera, hora de espera, mucha espera, larga espera | 2.243 | 22,1 % |
| Quejas - Precio | caro, caros, carísim, carisim, excesiv, abusiv, precio elevado, precios elevados, no vale lo que, clavada, un timo, es un robo, un robo | 1.472 | 14,5 % |
| Quejas - Calidad del Plato | insípid, insipid, sin sabor, quemad, grasient, aceitos, congelad, recalentad | 1.344 | 13,2 % |
| Quejas - Mal Trato | muy borde, un borde, una borde, bastante borde, algo borde, fue borde, unos bordes, unas bordes, antipátic, antipatic, maleducad, mal educad, grosero, grosera, desagradable, mala educación, malas maneras, prepotente, chulería, mal trato, maltrato, mala atención, mal atendid | 1.094 | 10,8 % |
| Quejas - Cantidad | escas, poca cantidad, cantidades pequeñas, raciones pequeñas, porciones pequeñas, ración pequeña, racion pequeña, poca comida | 823 | 8,1 % |
| Quejas - Comida Fría | frío, fría, fríos, frías, frio, fria, frios, frias, templad | 729 | 7,2 % |
| Quejas - Higiene | sucio, sucia, sucios, sucias, suciedad, higiene, cucaracha, mosca | 360 | 3,5 % |
| Quejas - Ruido | ruido, ruidos, ruidoso, ruidosa | 102 | 1,0 % |

Las demás medidas se escriben igual que `Quejas - Lentitud`, cambiando la lista de `SEARCH`. El 56,2 % de las
reseñas negativas (5.708) menciona al menos uno de estos temas. Pueden salir diferencias de unas pocas reseñas
si Power BI trata las tildes distinto que Python.

KPI asociado (la queja como proporción de las negativas):

```DAX
% Negativas con Queja de Lentitud = DIVIDE ( [Quejas - Lentitud], [Reseñas Negativas] )
```

Para mostrar las 8 quejas en **un solo gráfico de barras** (página *Reseñas - Texto*) se usa una tabla
desconectada con los nombres de las categorías y una medida que elige la medida correcta según la fila:

```DAX
Tipos_Queja =
DATATABLE ( "Queja", STRING,
    { { "Lentitud y espera" }, { "Precio alto" }, { "Calidad del plato" }, { "Mal trato" },
      { "Cantidad escasa" }, { "Comida fría" }, { "Higiene" }, { "Ruido" } } )

Menciones de Queja =
SWITCH ( SELECTEDVALUE ( Tipos_Queja[Queja] ),
    "Lentitud y espera", [Quejas - Lentitud],
    "Precio alto", [Quejas - Precio],
    "Calidad del plato", [Quejas - Calidad del Plato],
    "Mal trato", [Quejas - Mal Trato],
    "Cantidad escasa", [Quejas - Cantidad],
    "Comida fría", [Quejas - Comida Fría],
    "Higiene", [Quejas - Higiene],
    "Ruido", [Quejas - Ruido] )

% Negativas con la Queja = DIVIDE ( [Menciones de Queja], [Reseñas Negativas] )
```

## 5. Palabras clave (tabla `Fact_Palabras`)

| Medida | Fórmula | Esperado |
|---|---|---|
| Reseñas con la Palabra | `COUNTROWS(Fact_Palabras)` | comida 18.786 · buena 12.249 · calidad 12.232 · precio 11.954 · servicio 10.729 |
| % Reseñas que la Mencionan | `DIVIDE([Reseñas con la Palabra], [Total Reseñas])` | comida 35,2 % |

`Fact_Palabras` tiene una fila por reseña y palabra (cada palabra cuenta una vez por reseña), relacionada con
`Fact_Resenas` por `Review_ID`. Por eso los filtros de sentimiento, año, restaurante u origen se le aplican solos.
Con el filtro de sentimiento:
- **Positivas:** comida, buena, calidad, precio, trato, servicio, atención, buen, recomendable, platos, excelente.
- **Negativas:** comida, servicio, **mal**, **camarero**, **mesa**, calidad, precio, camareros, plato, **hora**, **mala**.

## 6. Relación entre dos variables

```DAX
Correlación Longitud-Rating =
VAR MX = AVERAGE ( Fact_Resenas[Longitud_Texto] )
VAR MY = AVERAGE ( Fact_Resenas[Rating] )
VAR Cov = SUMX ( Fact_Resenas, ( Fact_Resenas[Longitud_Texto] - MX ) * ( Fact_Resenas[Rating] - MY ) )
VAR SX = SQRT ( SUMX ( Fact_Resenas, ( Fact_Resenas[Longitud_Texto] - MX ) ^ 2 ) )
VAR SY = SQRT ( SUMX ( Fact_Resenas, ( Fact_Resenas[Rating] - MY ) ^ 2 ) )
RETURN
    DIVIDE ( Cov, SX * SY )
```
Esperado: **−0,24**. Es el coeficiente de Pearson: las reseñas más largas tienden a ser más negativas. La longitud
promedio por estrella es 1★ 478 · 2★ 501 · 3★ 409 · 4★ 331 · 5★ 293 caracteres: quien se queja explica más.
Visual: gráfico de dispersión con un punto por restaurante, `Longitud Promedio` en X y `Rating Promedio` en Y.

## 7. KPI y dispersión

| Medida | Fórmula | Esperado |
|---|---|---|
| Índice Neto de Satisfacción | `[% Positivas] - [% Negativas]` | 51,9 % |
| Desviación Rating | `STDEV.S(Fact_Resenas[Rating])` | 1,40 |
| Coeficiente de Variación | `DIVIDE([Desviación Rating], [Rating Promedio])` | 36,2 % |

El **Índice Neto** resume el sentimiento en un número, como el NPS: de cada 100 reseñas, cuántas positivas
"sobran" después de restar las negativas. La **desviación estándar** mide qué tan dispersas son las opiniones:
1,40 sobre una escala de 1 a 5 indica opiniones muy polarizadas (muchos 5 y bastantes 1).

## 8. Encuesta

| Medida | Fórmula | Esperado |
|---|---|---|
| Total Encuestados | `COUNTROWS(Fact_Encuesta)` | 1.500 |
| % Alta Satisfacción | `AVERAGE(Fact_Encuesta[Alta_Satisfaccion])` | 13,4 % |
| Calif. Servicio / Comida / Ambiente | `AVERAGE(Fact_Encuesta[Calif_Servicio])`, etc. | 3,0 aprox. |
| Calif. Promedio Encuesta | `AVERAGE(Fact_Encuesta[Calif_Promedio])` | 3,01 |
| Espera Promedio (min) | `AVERAGE(Fact_Encuesta[Tiempo_Espera_Min])` | 30,16 |
| Gasto Promedio | `AVERAGE(Fact_Encuesta[Gasto_Promedio])` | 105,66 |
| Gasto Total Encuesta | `SUM(Fact_Encuesta[Gasto_Promedio])` | 158.488,51 |
| % Reserva Online / % Pedido Domicilio / % Miembros Lealtad | `AVERAGE` de cada bandera 0/1 | 29,7 % / 40,5 % / 48,0 % |

`% Alta Satisfacción` es el KPI tipo "tasa de conversión" de la encuesta: proporción de clientes que pasan a
estar muy satisfechos. El promedio de una columna 0/1 es directamente esa proporción.

## 9. Columnas calculadas

No son medidas, pero se crean con DAX en el modelo para poder agrupar y ordenar los visuales.

| Tabla | Columna | Fórmula | Para qué |
|---|---|---|---|
| `Dim_Fecha` | `Mes_Fecha` | `DATE ( Dim_Fecha[Anio], Dim_Fecha[Mes], 1 )` | Eje continuo de meses (sin barra de desplazamiento) y línea de tendencia |
| `Fact_Encuesta` | `Rango_Espera` | `SWITCH ( TRUE (), [Tiempo_Espera_Min] < 15, "0-15 min", … )` | Alta satisfacción según tiempo de espera |
| `Fact_Encuesta` | `Rango_Edad` / `Rango_Edad_Orden` | ver abajo | Perfil del cliente por edad |
| `Fact_Encuesta` | `Rango_Ingreso` / `Rango_Ingreso_Orden` | ver abajo | Perfil del cliente por ingreso |

```DAX
Rango_Edad =
SWITCH ( TRUE (),
    Fact_Encuesta[Edad] <= 25, "18-25",
    Fact_Encuesta[Edad] <= 35, "26-35",
    Fact_Encuesta[Edad] <= 45, "36-45",
    Fact_Encuesta[Edad] <= 55, "46-55",
    "56 o más" )

Rango_Ingreso =
SWITCH ( TRUE (),
    Fact_Encuesta[Ingreso] < 40000, "Menos de 40 mil",
    Fact_Encuesta[Ingreso] < 70000, "40 a 70 mil",
    Fact_Encuesta[Ingreso] < 100000, "70 a 100 mil",
    "100 mil o más" )
```

Las columnas `_Orden` repiten la misma lógica devolviendo 1, 2, 3… y se usan en **Ordenar por columna**
para que los rangos salgan en orden y no alfabéticos.

Valores esperados de `% Alta Satisfacción` (página *Encuesta - Perfil del cliente*):

| Edad | Encuestados | % Alta Satisf. | Ingreso | Encuestados | % Alta Satisf. |
|---|---:|---:|---|---:|---:|
| 18-25 | 233 | 11,6 % | Menos de 40 mil | 236 | 6,8 % |
| 26-35 | 256 | 12,9 % | 40 a 70 mil | 333 | 11,1 % |
| 36-45 | 304 | 11,5 % | 70 a 100 mil | 320 | 16,3 % |
| 46-55 | 287 | 14,6 % | 100 mil o más | 611 | 15,7 % |
| 56 o más | 420 | 15,2 % | | | |

Por género: Femenino 759 (13,2 %), Masculino 741 (13,6 %). Son diferencias descriptivas de la muestra; no se
aplicó prueba de hipótesis sobre ellas.

## 10. Páginas del dashboard y requerimientos analíticos

| # | Requerimiento analítico | Página |
|---|---|---|
| 1 | Calificación promedio por restaurante | Reseñas - Restaurantes |
| 2 | Sentimiento por categoría | Reseñas - Cocina (barras 100 % por tipo de cocina, 15 con más reseñas) |
| 3 | Palabras clave más frecuentes | Reseñas - Texto |
| 4 | Tendencia mensual | Reseñas - General (con línea de tendencia) |
| 5 | Calificación por ciudad | Reseñas - Origen |
| 6 | Precio vs satisfacción | Reseñas - Restaurantes |
| 7 | Top 10 restaurantes | Reseñas - Restaurantes e Indicadores (RANKX) |
| 8 | Frecuencia de quejas específicas | Reseñas - Texto |
| 9 | Negativas vs positivas | Reseñas - General |
| 10 | Segmentación del perfil del cliente | Encuesta - Perfil del cliente (edad, ingreso, género) y Encuesta (lealtad, reserva, domicilio) |
