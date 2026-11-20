"""Configuración central del ETL: rutas, contratos de esquema, rangos de dominio y umbrales.

Todo lo que es una DECISIÓN (un rango, un conjunto permitido, un umbral) vive aquí y no dentro del código,
para poder defenderla en la presentación y cambiarla en un solo lugar.
"""
from pathlib import Path

# ============================================================================ RUTAS
RAIZ = Path(__file__).resolve().parent.parent
CRUDOS = RAIZ / "datasets"            # capa bronce: NUNCA se modifica (solo se agrega _manifiesto.json)
LIMPIOS = RAIZ / "datos_limpios"      # capa oro: modelo estrella en CSV (utf-8-sig) + parquet/
CUARENTENA = RAIZ / "rechazados"      # filas que no pasaron las reglas, con su Motivo
BASE_DATOS = RAIZ / "base_datos" / "opiniones_restaurantes.db"   # mismo modelo estrella en SQLite

ARCHIVO_ENCUESTA = CRUDOS / "dataset_raw.csv"
ARCHIVO_RESENAS = CRUDOS / "gijon_resenas_es_2017_2023.csv"
ARCHIVO_UBICACION = CRUDOS / "gijon_ubicacion_clientes.csv"   # ubicación del autor de cada reseña (preparacion/)
MANIFIESTO = CRUDOS / "_manifiesto.json"

# Marcas de "sin dato" que se convierten en nulo (comparación en minúsculas, después de trim).
# OJO: solo se aplican a columnas estructuradas. En texto libre (title, text) solo "" es nulo:
# un comentario que dice "NA" o "unknown" es una opinión, no un dato faltante.
TEXTOS_NULOS = {"", "na", "n/a", "nan", "null", "none", "?", "-"}

MAX_NULOS_COLUMNA = 0.20   # columna con > 20 % de nulos se evalúa y la decisión queda en el reporte

# ============================================================================ ENCUESTA (Iznia)
# Contrato: columnas que DEBEN venir en el archivo. Si falta alguna, el ETL se detiene.
# Se renombran a español para el modelo (el valor original se conserva en rechazados/).
COLUMNAS_ENCUESTA = {
    "CustomerID": "ID_Cliente",
    "Age": "Edad",
    "Gender": "Genero",
    "Income": "Ingreso",
    "VisitFrequency": "Frecuencia_Visita",
    "AverageSpend": "Gasto_Promedio",
    "PreferredCuisine": "Cocina_Preferida",
    "TimeOfVisit": "Franja_Visita",
    "GroupSize": "Tamano_Grupo",
    "DiningOccasion": "Ocasion",
    "MealType": "Tipo_Comida",
    "OnlineReservation": "Reserva_Online",
    "DeliveryOrder": "Pedido_Domicilio",
    "LoyaltyProgramMember": "Miembro_Lealtad",
    "WaitTime": "Tiempo_Espera_Min",
    "ServiceRating": "Calif_Servicio",
    "FoodRating": "Calif_Comida",
    "AmbianceRating": "Calif_Ambiente",
    "HighSatisfaction": "Alta_Satisfaccion",
}

# Rangos de DOMINIO (lo imposible o fuera del instrumento), no estadísticos: un cliente que gasta mucho
# o espera mucho es un atípico real y se conserva.
RANGO_EDAD = (18, 100)            # la encuesta es a clientes adultos; > 100 años es error de captura
RANGO_INGRESO = (0, 1_000_000)    # ingreso anual > 0; el tope solo atrapa errores de dígitos
RANGO_GASTO = (0, 1_000)          # gasto por visita > 0 y < 1.000 (moneda de la fuente)
RANGO_ESPERA_MIN = (0, 240)       # minutos; negativo es imposible, > 4 h no es una espera de restaurante
RANGO_GRUPO = (1, 30)             # personas por mesa
RANGO_CALIFICACION = (1, 5)       # escala Likert 1-5 del cuestionario
BINARIAS = {"0", "1"}

CATEGORIAS_ENCUESTA = {
    "Genero": {"Male", "Female"},
    "Frecuencia_Visita": {"Daily", "Weekly", "Monthly", "Rarely"},
    "Cocina_Preferida": {"Italian", "Chinese", "Mexican", "Indian", "American"},
    "Franja_Visita": {"Breakfast", "Lunch", "Dinner"},
    "Ocasion": {"Business", "Casual", "Celebration"},
    "Tipo_Comida": {"Dine-in", "Takeaway"},
}

# Dimensiones pequeñas para Power BI: código original -> (etiqueta en español, orden)
DIM_COCINA = {"American": ("Americana", 1), "Chinese": ("China", 2), "Indian": ("India", 3),
              "Italian": ("Italiana", 4), "Mexican": ("Mexicana", 5)}
DIM_OCASION = {"Business": ("Negocios", 1), "Casual": ("Casual", 2), "Celebration": ("Celebración", 3)}
DIM_FRANJA = {"Breakfast": ("Desayuno", 1), "Lunch": ("Almuerzo", 2), "Dinner": ("Cena", 3)}
DIM_FRECUENCIA = {"Daily": ("Diaria", 1), "Weekly": ("Semanal", 2), "Monthly": ("Mensual", 3), "Rarely": ("Rara vez", 4)}
ETIQUETA_GENERO = {"Male": "Masculino", "Female": "Femenino"}
ETIQUETA_TIPO_COMIDA = {"Dine-in": "En el local", "Takeaway": "Para llevar"}

# ============================================================================ RESEÑAS (TripAdvisor Gijón)
COLUMNAS_RESENAS = ["review_id", "restaurant_id", "restaurant_name", "city", "price_interval", "cuisine_types",
                    "cuisine_match_encuesta", "restaurant_avg_rating", "review_date", "year_month", "rating",
                    "title", "text", "language"]
TEXTO_LIBRE = {"title", "text"}

FORMATO_FECHA = "%Y-%m-%d"
FORMATO_ANIO_MES = "%Y-%m"
ANIO_INICIO, ANIO_FIN = 2017, 2023      # periodo declarado del dataset
RANGO_RATING = (1, 5)
RANGO_RATING_RESTAURANTE = (1.0, 5.0)
IDIOMA_ESPERADO = "es"
CIUDAD_ESPERADA = "Gijon"

# price_interval -> nivel ordenado. Los nulos quedan como "Sin dato" (ver decisión en PIPELINE.md)
NIVEL_PRECIO = {"$": (1, "Económico"), "$$ - $$$": (2, "Medio"), "$$$$": (3, "Alto")}
ETIQUETA_SIN_DATO = "Sin dato"
SEPARADOR_COCINAS = ";"

CATEGORIAS_COCINA_ENCUESTA = {"Other", "Italian", "Mexican", "American", "Italian; American", "Indian",
                              "Chinese", "Chinese; Indian"}
MIN_RESENAS_CATEGORIA = 100              # categorías de cuisine_match_encuesta con menos reseñas -> "Otras"

# Origen del cliente (ubicación que declara en su perfil de TripAdvisor). El catálogo está en etl/ubicaciones.py
COLUMNAS_UBICACION = ["review_id", "user_location"]
CIUDAD_LOCAL = "Gijón"
COMUNIDAD_LOCAL = "Principado de Asturias"
ETIQUETA_NO_IDENTIFICADA = "No identificada"      # se sabe el país, pero no la ciudad o la región
ETIQUETA_NO_DETERMINADO = "No determinado"        # escribió algo, pero no permite saber el país ("World")
REGION_EXTRANJERO = "Extranjero"
TIPO_ORIGEN = {"Gijón (local)": 1, "Resto de Asturias": 2, "Resto de España": 3, "Extranjero": 4,
               "No determinado": 5, "Sin dato": 6}

# Palabras clave (R28). La lista de palabras vacías está en etl/palabras_vacias.py
PATRON_PALABRA = r"[a-záéíóúüñ]+"       # sobre el texto en minúsculas: solo letras (sin números ni signos)
MIN_LARGO_PALABRA = 3                    # "de", "la", "es"... quedan fuera por largo, además de por la lista
TOP_PALABRAS = 200                       # se guardan las 200 palabras presentes en más reseñas

# Sentimiento derivado del rating (regla de negocio, no viene de la fuente)
SENTIMIENTO = {1: "Negativo", 2: "Negativo", 3: "Neutro", 4: "Positivo", 5: "Positivo"}
ORDEN_SENTIMIENTO = {"Negativo": 1, "Neutro": 2, "Positivo": 3}

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
         "Septiembre", "Octubre", "Noviembre", "Diciembre"]
DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
