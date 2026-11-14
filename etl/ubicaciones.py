"""Catálogo para normalizar la ubicación que escriben los usuarios de TripAdvisor (regla R26-R27).

La ubicación viene como texto libre ("Gijon, Spain", "gijon", "Madrid, Comunidad de Madrid, Spain",
"Munich, Germany", "World", ""). Las claves de este catálogo están NORMALIZADAS: minúsculas, sin tildes y con
espacios simples (ver normalizar() en etl_resenas.py).

Criterios (para defender en la presentación):
- Solo se mapean lugares que se pueden atribuir sin ambigüedad. Si un nombre es dudoso (p. ej. "San Lorenzo",
  "Villamartín", que existen en varias comunidades) NO se incluye: queda con región "No identificada".
- "Gijón (local)" incluye los barrios/parroquias de Gijón que aparecen en los datos (Somió, Roces, La Calzada).
- Un nombre de región o provincia sin ciudad ("Asturias", "Province of Leon") da la región, con ciudad
  "No identificada".
- Las islas sin ciudad ("Tenerife", "Majorca") se tratan como región (Canarias / Illes Balears).
"""

# ------------------------------------------------------------------------------------------- ESPAÑA
ESPANA = "España"

# Comunidad autónoma -> {clave normalizada: nombre de ciudad para mostrar, o None si la clave es la región}
_POR_COMUNIDAD = {
    "Principado de Asturias": {
        "asturias": None, "principado de asturias": None, "principality of asturias": None, "asturies": None,
        "gijon": "Gijón", "xixon": "Gijón", "gijon/xixon": "Gijón", "gijon xixon": "Gijón",
        "somio": "Gijón", "roces": "Gijón", "roces-sur": "Gijón", "la calzada": "Gijón",
        "oviedo": "Oviedo", "uvieu": "Oviedo", "aviles": "Avilés", "mieres": "Mieres",
        "mieres municipality": "Mieres", "langreo": "Langreo", "villaviciosa": "Villaviciosa",
        "pola de siero": "Pola de Siero", "siero": "Siero", "siero municipality": "Siero",
        "ribadesella": "Ribadesella", "navia": "Navia", "el entrego": "El Entrego", "candas": "Candás",
        "luanco": "Luanco", "pola de laviana": "Pola de Laviana", "laviana": "Laviana",
        "la felguera": "La Felguera", "piedras blancas": "Piedras Blancas",
        "corvera de asturias": "Corvera de Asturias", "corvera de asturias municipality": "Corvera de Asturias",
        "norena": "Noreña", "pola de lena": "Pola de Lena", "lena": "Lena", "lugones": "Lugones",
        "llanes": "Llanes", "cudillero": "Cudillero", "salinas": "Salinas", "cangas de onis": "Cangas de Onís",
        "grado": "Grado", "deva": "Deva", "llanera": "Llanera", "llanera municipality": "Llanera",
        "posada de llanera": "Llanera", "tapia de casariego": "Tapia de Casariego", "teverga": "Teverga",
        "teverga municipality": "Teverga", "carreno": "Carreño", "carreno municipality": "Carreño",
        "nava": "Nava", "cangas del narcea": "Cangas del Narcea", "pravia": "Pravia", "blimea": "Blimea",
        "colunga": "Colunga", "tineo": "Tineo", "quintueles": "Quintueles", "las caldas": "Las Caldas",
        "luarca": "Luarca", "taramundi": "Taramundi", "castrillon": "Castrillón", "sama": "Sama",
        "lastres": "Lastres", "arriondas": "Arriondas", "moreda": "Moreda", "ferrones": "Ferrones",
        "valdes": "Valdés", "sotrondio": "Sotrondio", "infiesto": "Infiesto", "vegadeo": "Vegadeo",
        "corvera": "Corvera de Asturias", "san martin del rey aurelio": "San Martín del Rey Aurelio",
        "san martin del rey aurelio municipality": "San Martín del Rey Aurelio", "lugo de llanera": "Llanera",
        "proaza": "Proaza", "soto del barco": "Soto del Barco", "san juan de la arena": "San Juan de la Arena",
        "covadonga": "Covadonga", "gozon": "Gozón", "gozon municipality": "Gozón", "perlora": "Perlora",
        "castrillon municipality": "Castrillón", "torazo": "Torazo", "sevares": "Sevares",
    },
    "Comunidad de Madrid": {
        "community of madrid": None, "comunidad de madrid": None, "region of madrid": None,
        "madrid": "Madrid", "alcala de henares": "Alcalá de Henares", "alcorcon": "Alcorcón",
        "torrejon de ardoz": "Torrejón de Ardoz", "pozuelo de alarcon": "Pozuelo de Alarcón",
        "boadilla del monte": "Boadilla del Monte", "las rozas": "Las Rozas", "las rozas de madrid": "Las Rozas",
        "mostoles": "Móstoles", "leganes": "Leganés", "getafe": "Getafe", "tres cantos": "Tres Cantos",
        "majadahonda": "Majadahonda", "fuenlabrada": "Fuenlabrada", "pinto": "Pinto", "alpedrete": "Alpedrete",
        "alcobendas": "Alcobendas", "guadarrama": "Guadarrama", "san sebastian de los reyes": "San Sebastián de los Reyes",
        "valdemoro": "Valdemoro", "parla": "Parla", "collado villalba": "Collado Villalba", "coslada": "Coslada",
        "arganda del rey": "Arganda del Rey", "daganzo de arriba": "Daganzo de Arriba",
        "vaciamadrid": "Rivas-Vaciamadrid", "rivas-vaciamadrid": "Rivas-Vaciamadrid", "galapagar": "Galapagar",
        "san lorenzo de el escorial": "San Lorenzo de El Escorial", "colmenar viejo": "Colmenar Viejo",
        "villaviciosa de odon": "Villaviciosa de Odón", "torrelodones": "Torrelodones", "aranjuez": "Aranjuez",
        "san fernando de henares": "San Fernando de Henares", "navalcarnero": "Navalcarnero",
        "arroyomolinos": "Arroyomolinos", "villanueva de la canada": "Villanueva de la Cañada",
        "los molinos": "Los Molinos", "san martin de valdeiglesias": "San Martín de Valdeiglesias",
        "sevilla la nueva": "Sevilla la Nueva", "manzanares el real": "Manzanares el Real",
    },
    "Castilla y León": {
        "castile and leon": None, "castilla y leon": None, "castilla leon": None,
        "province of valladolid": None, "province of burgos": None, "province of zamora": None,
        "province of salamanca": None, "province of leon": None, "province of palencia": None,
        "province of avila": None, "province of segovia": None, "province of soria": None,
        "valladolid": "Valladolid", "leon": "León", "salamanca": "Salamanca", "burgos": "Burgos",
        "palencia": "Palencia", "zamora": "Zamora", "avila": "Ávila", "ponferrada": "Ponferrada",
        "segovia": "Segovia", "soria": "Soria", "miranda de ebro": "Miranda de Ebro",
        "aranda de duero": "Aranda de Duero", "laguna de duero": "Laguna de Duero",
        "medina del campo": "Medina del Campo", "astorga": "Astorga", "benavente": "Benavente",
        "villaobispo de las regueras": "Villaobispo de las Regueras",
        "arroyo de la encomienda": "Arroyo de la Encomienda", "aguilar de campoo": "Aguilar de Campoo",
        "medina de pomar": "Medina de Pomar", "la baneza": "La Bañeza", "puente de sanabria": "Puente de Sanabria",
        "bembibre": "Bembibre", "villablino": "Villablino", "san andres del rabanedo": "San Andrés del Rabanedo",
        "santa marta de tormes": "Santa Marta de Tormes", "fuensaldana": "Fuensaldaña", "la lastrilla": "La Lastrilla",
        "san esteban de gormaz": "San Esteban de Gormaz", "el burgo de osma": "El Burgo de Osma",
        "valencia de don juan": "Valencia de Don Juan", "arevalo": "Arévalo", "villamuriel de cerrato": "Villamuriel de Cerrato",
        "trobajo del camino": "Trobajo del Camino", "pucela": "Valladolid",
    },
    "País Vasco": {
        "basque country": None, "pais vasco": None, "euskadi": None, "province of guipuzcoa": None,
        "province of gipuzkoa": None, "province of biscay": None, "vizcaya": None, "bizkaia": None,
        "alava": None, "province of alava": None,
        "bilbao": "Bilbao", "vitoria-gasteiz": "Vitoria-Gasteiz", "vitoria": "Vitoria-Gasteiz",
        "san sebastian - donostia": "Donostia-San Sebastián", "san sebastian": "Donostia-San Sebastián",
        "donostia": "Donostia-San Sebastián", "donostia-san sebastian": "Donostia-San Sebastián",
        "getxo": "Getxo", "algorta": "Getxo", "barakaldo": "Barakaldo", "baracaldo": "Barakaldo",
        "portugalete": "Portugalete", "santurtzi": "Santurtzi", "durango": "Durango", "oiartzun": "Oiartzun",
        "leioa": "Leioa", "galdakao": "Galdakao", "zarautz": "Zarautz", "sopelana": "Sopela", "sopela": "Sopela",
        "muskiz": "Muskiz", "amorebieta": "Amorebieta", "sestao": "Sestao", "lasarte-oria": "Lasarte-Oria",
        "basauri": "Basauri", "irun": "Irun", "eibar": "Eibar", "erandio": "Erandio", "mungia": "Mungia",
        "bermeo": "Bermeo", "gernika": "Gernika", "hondarribia": "Hondarribia", "errenteria": "Errenteria",
        "tolosa": "Tolosa", "deba": "Deba", "gipuzkoa": None, "guipuzcoa": None, "gernika-lumo": "Gernika",
        "amurrio": "Amurrio", "llodio": "Llodio", "azkoitia": "Azkoitia", "ondarroa": "Ondarroa",
        "amorebieta-etxano": "Amorebieta",
    },
    "Cataluña": {
        "catalonia": None, "cataluna": None, "catalunya": None, "province of barcelona": None,
        "province of girona": None, "province of tarragona": None, "province of lleida": None,
        "barcelona": "Barcelona", "castelldefels": "Castelldefels", "sabadell": "Sabadell",
        "tarragona": "Tarragona", "girona": "Girona", "terrassa": "Terrassa", "lleida": "Lleida",
        "mataro": "Mataró", "badalona": "Badalona", "reus": "Reus", "viladecans": "Viladecans",
        "sant cugat del valles": "Sant Cugat del Vallès", "salou": "Salou", "manresa": "Manresa",
        "vilanova i la geltru": "Vilanova i la Geltrú", "ripollet": "Ripollet", "figueres": "Figueres",
        "rubi": "Rubí", "l'hospitalet de llobregat": "L'Hospitalet de Llobregat",
        "hospitalet de llobregat": "L'Hospitalet de Llobregat", "granollers": "Granollers", "sitges": "Sitges",
        "cornella de llobregat": "Cornellà de Llobregat", "el prat de llobregat": "El Prat de Llobregat",
        "costa de barcelona": None, "vila seca": "Vila-seca", "premia de mar": "Premià de Mar",
        "martorell": "Martorell", "lloret de mar": "Lloret de Mar", "vilassar de mar": "Vilassar de Mar",
    },
    "Galicia": {
        "galicia": None, "province of a coruna": None, "province of lugo": None,
        "province of pontevedra": None, "province of ourense": None,
        "la coruna": "A Coruña", "a coruna": "A Coruña", "coruna": "A Coruña",
        "santiago de compostela": "Santiago de Compostela", "vigo": "Vigo", "lugo": "Lugo", "ferrol": "Ferrol",
        "ourense": "Ourense", "pontevedra": "Pontevedra", "viveiro": "Viveiro", "naron": "Narón",
        "ribadeo": "Ribadeo", "ribeira": "Ribeira", "culleredo": "Culleredo", "ponteareas": "Ponteareas",
        "burela": "Burela", "sanxenxo": "Sanxenxo", "pontedeume": "Pontedeume", "tomino": "Tomiño",
        "vilagarcia de arousa": "Vilagarcía de Arousa", "moana": "Moaña", "marin": "Marín",
        "oleiros": "Oleiros", "arteixo": "Arteixo", "betanzos": "Betanzos", "monforte de lemos": "Monforte de Lemos",
        "foz": "Foz", "noia": "Noia", "bertamirans": "Bertamiráns", "baiona": "Baiona", "cambados": "Cambados",
    },
    "Cantabria": {
        "cantabria": None,
        "santander": "Santander", "castro urdiales": "Castro Urdiales", "torrelavega": "Torrelavega",
        "reinosa": "Reinosa", "laredo": "Laredo", "suances": "Suances", "potes": "Potes", "santona": "Santoña",
        "noja": "Noja", "comillas": "Comillas", "san vicente de la barquera": "San Vicente de la Barquera",
        "camargo": "Camargo", "el astillero": "El Astillero", "maliano": "Maliaño",
    },
    "Aragón": {
        "aragon": None, "province of zaragoza": None, "province of huesca": None, "province of teruel": None,
        "zaragoza": "Zaragoza", "huesca": "Huesca", "teruel": "Teruel", "calatayud": "Calatayud", "jaca": "Jaca",
        "utebo": "Utebo", "monzon": "Monzón",
    },
    "Comunitat Valenciana": {
        "valencian community": None, "comunidad valenciana": None, "comunitat valenciana": None,
        "province of alicante": None, "province of valencia": None, "province of castellon": None,
        "valencia": "Valencia", "alicante": "Alicante", "elche": "Elche",
        "castellon de la plana": "Castellón de la Plana", "castellon": "Castellón de la Plana",
        "torrevieja": "Torrevieja", "paterna": "Paterna", "denia": "Dénia", "benicarlo": "Benicarló",
        "alcoy": "Alcoy", "benidorm": "Benidorm", "sant vicent del raspeig": "Sant Vicent del Raspeig",
        "gandia": "Gandia", "orihuela": "Orihuela", "sagunto": "Sagunto", "javea": "Jávea", "xativa": "Xàtiva",
        "moraira": "Moraira", "villajoyosa": "Villajoyosa", "catarroja": "Catarroja", "naquera": "Náquera",
        "alcoy/alcoi": "Alcoy",
    },
    "Andalucía": {
        "andalucia": None, "andalusia": None, "province of malaga": None, "province of seville": None,
        "province of cadiz": None, "province of granada": None, "province of cordoba": None,
        "seville": "Sevilla", "sevilla": "Sevilla", "malaga": "Málaga", "granada": "Granada",
        "cordoba": "Córdoba", "cadiz": "Cádiz", "almeria": "Almería", "huelva": "Huelva", "jaen": "Jaén",
        "marbella": "Marbella", "chiclana de la frontera": "Chiclana de la Frontera",
        "jerez de la frontera": "Jerez de la Frontera", "algeciras": "Algeciras",
        "el puerto de santa maria": "El Puerto de Santa María", "dos hermanas": "Dos Hermanas",
        "torremolinos": "Torremolinos", "rincon de la victoria": "Rincón de la Victoria",
        "benalmadena": "Benalmádena", "mairena del aljarafe": "Mairena del Aljarafe", "la carolina": "La Carolina",
        "antequera": "Antequera", "san fernando": "San Fernando", "fuengirola": "Fuengirola",
        "estepona": "Estepona", "motril": "Motril", "ronda": "Ronda", "linares": "Linares", "ubeda": "Úbeda",
        "roquetas de mar": "Roquetas de Mar", "nerja": "Nerja", "velez-malaga": "Vélez-Málaga",
        "province of huelva": None, "la linea de la concepcion": "La Línea de la Concepción",
        "arroyo de la miel": "Arroyo de la Miel", "fernan-nunez": "Fernán-Núñez", "aguadulce": "Aguadulce",
    },
    "Región de Murcia": {
        "region of murcia": None, "region de murcia": None,
        "murcia": "Murcia", "cartagena": "Cartagena", "lorca": "Lorca", "molina de segura": "Molina de Segura",
        "san pedro del pinatar": "San Pedro del Pinatar", "alhama de murcia": "Alhama de Murcia",
    },
    "La Rioja": {
        "la rioja": None, "logrono": "Logroño", "calahorra": "Calahorra", "haro": "Haro", "fuenmayor": "Fuenmayor",
    },
    "Comunidad Foral de Navarra": {
        "navarra": None, "navarre": None,
        "pamplona": "Pamplona", "tudela": "Tudela", "leiza": "Leitza", "leitza": "Leitza", "huarte": "Huarte",
        "estella": "Estella", "burlada": "Burlada", "baranain": "Barañáin",
    },
    "Castilla-La Mancha": {
        "castilla-la mancha": None, "castile-la mancha": None, "province of guadalajara": None,
        "province of toledo": None,
        "toledo": "Toledo", "albacete": "Albacete", "guadalajara": "Guadalajara", "ciudad real": "Ciudad Real",
        "almonacid de toledo": "Almonacid de Toledo", "talavera de la reina": "Talavera de la Reina",
        "alcazar de san juan": "Alcázar de San Juan", "cuenca": "Cuenca", "el casar": "El Casar",
        "azuqueca de henares": "Azuqueca de Henares", "puertollano": "Puertollano", "azuqueca": "Azuqueca de Henares",
        "torrijos": "Torrijos", "almagro": "Almagro", "cabanillas del campo": "Cabanillas del Campo",
        "valdepenas": "Valdepeñas",
    },
    "Extremadura": {
        "extremadura": None,
        "badajoz": "Badajoz", "caceres": "Cáceres", "plasencia": "Plasencia", "merida": "Mérida",
        "navalmoral de la mata": "Navalmoral de la Mata", "trujillo": "Trujillo", "eljas": "Eljas",
        "don benito": "Don Benito", "almendralejo": "Almendralejo",
    },
    "Illes Balears": {
        "balearic islands": None, "illes balears": None, "islas baleares": None, "majorca": None,
        "mallorca": None, "ibiza": None, "menorca": None,
        "palma de mallorca": "Palma", "palma": "Palma", "santa ponsa": "Santa Ponsa", "manacor": "Manacor",
        "inca": "Inca",
    },
    "Canarias": {
        "canary islands": None, "canarias": None, "islas canarias": None, "tenerife": None,
        "gran canaria": None, "lanzarote": None, "fuerteventura": None, "la palma": None,
        "las palmas de gran canaria": "Las Palmas de Gran Canaria", "las palmas": "Las Palmas de Gran Canaria",
        "santa cruz de tenerife": "Santa Cruz de Tenerife", "san cristobal de la laguna": "San Cristóbal de La Laguna",
        "la laguna": "San Cristóbal de La Laguna", "villa de mazo": "Villa de Mazo", "arrecife": "Arrecife",
        "puerto de la cruz": "Puerto de la Cruz", "los llanos de aridane": "Los Llanos de Aridane",
    },
    "Ceuta": {"ceuta": "Ceuta"},
    "Melilla": {"melilla": "Melilla"},
}

# Clave normalizada -> (ciudad para mostrar o None, comunidad autónoma)
LUGARES_ESPANA = {clave: (ciudad, comunidad)
                  for comunidad, lugares in _POR_COMUNIDAD.items()
                  for clave, ciudad in lugares.items()}
_total = sum(len(v) for v in _POR_COMUNIDAD.values())
assert len(LUGARES_ESPANA) == _total, "Hay una clave repetida en dos comunidades: el catálogo sería ambiguo"

ALIAS_ESPANA = {"spain", "espana", "espanya", "reino de espana", "spainspain", "espanol", "espanola",
                "espaa±a"}  # las dos últimas: texto mal codificado o escrito así en el perfil

# ------------------------------------------------------------------------------------------- EXTRANJERO
PAISES = {
    "argentina": "Argentina", "italy": "Italia", "italia": "Italia", "germany": "Alemania",
    "deutschland": "Alemania", "alemania": "Alemania", "united kingdom": "Reino Unido", "uk": "Reino Unido",
    "reino unido": "Reino Unido", "england": "Reino Unido", "scotland": "Reino Unido", "wales": "Reino Unido",
    "northern ireland": "Reino Unido", "mexico": "México", "df": "México", "cdmx": "México",
    "belgium": "Bélgica", "belgica": "Bélgica", "portugal": "Portugal", "france": "Francia", "francia": "Francia",
    "japan": "Japón", "the netherlands": "Países Bajos", "netherlands": "Países Bajos", "holanda": "Países Bajos",
    "chile": "Chile", "switzerland": "Suiza", "suiza": "Suiza", "andorra": "Andorra",
    "dominican republic": "República Dominicana", "norway": "Noruega", "venezuela": "Venezuela",
    "puerto rico": "Puerto Rico", "czech republic": "Chequia", "czechia": "Chequia", "slovakia": "Eslovaquia",
    "colombia": "Colombia", "ireland": "Irlanda", "canada": "Canadá", "bolivia": "Bolivia", "russia": "Rusia",
    "peru": "Perú", "uruguay": "Uruguay", "united arab emirates": "Emiratos Árabes Unidos", "greece": "Grecia",
    "turkiye": "Turquía", "turkey": "Turquía", "israel": "Israel", "thailand": "Tailandia", "vietnam": "Vietnam",
    "philippines": "Filipinas", "luxembourg": "Luxemburgo", "estonia": "Estonia", "iceland": "Islandia",
    "sweden": "Suecia", "kuwait": "Kuwait", "panama": "Panamá", "singapore": "Singapur", "indonesia": "Indonesia",
    "denmark": "Dinamarca", "romania": "Rumanía", "sri lanka": "Sri Lanka", "malta": "Malta", "poland": "Polonia",
    "united states": "Estados Unidos", "usa": "Estados Unidos", "estados unidos": "Estados Unidos",
    "brazil": "Brasil", "brasil": "Brasil", "cuba": "Cuba", "ecuador": "Ecuador", "paraguay": "Paraguay",
    "costa rica": "Costa Rica", "guatemala": "Guatemala", "el salvador": "El Salvador", "honduras": "Honduras",
    "nicaragua": "Nicaragua", "austria": "Austria", "finland": "Finlandia", "hungary": "Hungría",
    "china": "China", "india": "India", "australia": "Australia", "new zealand": "Nueva Zelanda",
    "south africa": "Sudáfrica", "morocco": "Marruecos", "egypt": "Egipto", "croatia": "Croacia",
    "slovenia": "Eslovenia", "bulgaria": "Bulgaria", "serbia": "Serbia", "ukraine": "Ucrania",
    "lithuania": "Lituania", "latvia": "Letonia", "cyprus": "Chipre", "qatar": "Catar",
    "saudi arabia": "Arabia Saudita", "south korea": "Corea del Sur", "taiwan": "Taiwán", "hong kong": "Hong Kong",
    "malaysia": "Malasia", "monaco": "Mónaco", "mongolia": "Mongolia", "barbados": "Barbados",
    # ciudades extranjeras escritas sin país
    "london": "Reino Unido", "buenos aires": "Argentina", "bangkok": "Tailandia", "taipei": "Taiwán",
}

# TripAdvisor escribe "Ciudad, Estado" para EE. UU. y "Ciudad, Provincia" para Canadá
SUBDIVISIONES_EXTRANJERAS = {
    **{estado: "Estados Unidos" for estado in [
        "florida", "texas", "california", "new york", "alaska", "new jersey", "georgia", "michigan", "connecticut",
        "illinois", "massachusetts", "pennsylvania", "ohio", "virginia", "washington", "arizona", "colorado",
        "nevada", "oregon", "north carolina", "south carolina", "maryland", "tennessee", "louisiana",
        "minnesota", "wisconsin", "indiana", "missouri", "utah", "hawaii", "district of columbia", "new mexico"]},
    **{provincia: "Canadá" for provincia in ["ontario", "quebec", "british columbia", "alberta"]},
    "sp": "Brasil", "ba": "Brasil",   # "Sao Paulo, SP", "Salvador, BA": códigos de estado de Brasil
}

# Ubicaciones que no permiten atribuir un país
NO_DETERMINABLES = {"world", "europe", "europa", "earth", "planet earth", "mundo", "everywhere",
                    "the world", "around the world"}
