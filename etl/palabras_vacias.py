"""Palabras vacías para el análisis de palabras clave (regla R28).

Dos grupos:
1. Palabras funcionales del español (artículos, preposiciones, pronombres, conjunciones, verbos auxiliares y
   adverbios muy generales): no dicen nada de la experiencia.
2. Palabras de dominio que aparecen en casi todas las reseñas sin aportar opinión ("restaurante", "sitio",
   "fuimos", "pedimos", "Gijón"...).

Se CONSERVAN a propósito las palabras que sí describen la experiencia aunque sean frecuentes: comida, servicio,
calidad, precio, trato, atención, caro, rápido, espera, ambiente, y los adjetivos de valoración (buena, excelente,
mal, mala...), porque permiten comparar reseñas positivas y negativas.

También van aquí las palabras de expresiones hechas que no aportan por sí solas ("sin DUDA", "vale la PENA",
"fin de semana", "darse CUENTA") y las ambiguas ("tarde": hora del día o retraso).
"""

FUNCIONALES = set("""
a al algo algún alguna algunas alguno algunos allí allá ante antes aquel aquella aquellas aquellos aquí así aun aún
aunque bajo bastante cada casi como cómo con contra cual cuál cuales cuando cuándo cuanto cuánto cuantos de del
desde donde dónde durante e el él ella ellas ellos en encima entre era eran éramos eres es esa esas ese eso esos
esta está estaba estaban estábamos estado estamos están estar estas este esto estos estoy estuve estuvimos estuvo
fue fuera fueron fui fuimos ha había habíamos habían han has hasta hay haya he hemos hice hicimos hizo hubo la las
le les lo los mas más me mi mis mía mío mucha muchas mucho muchos muy nada ni ningún ninguna ninguno no nos
nosotras nosotros nuestra nuestras nuestro nuestros nunca o os otra otras otro otros para pero poca pocas poco
pocos por porque pues que qué quien quién quienes se sea según ser será si sí sido siempre sin sino sobre sois
solo sólo somos son soy su sus suya suyo también tampoco tan tanta tantas tanto tantos te tenemos tener tenga
tengo tenía teníamos tenían ti tiene tienen toda todas todo todos tras tu tú tus tuve tuvimos tuvo un una unas
uno unos usted ustedes vosotros vuestra vuestro y ya yo
bien además después luego ahora hoy ayer mañana entonces cosa cosas veces vez parte hace hacer hacen hecho puede
pueden puedo puedes poder decir dicho creo parece pareció cierto caso tipo medio mismo misma igual cualquier
demás demasiada etc super súper
duda verdad pena gran menos primera primero segundo punto zona seguro momento varias varios fin ver media lado
vida resto ganas nota decidimos único destacar dentro llegamos general salimos pesar final quedamos poner opción
mundo pasado totalmente gracias visita merece cuenta tarde
""".split())

DOMINIO = set("""
restaurante restaurantes sitio sitios local locales lugar lugares gijón gijon xixón asturias comer comimos comido
cenar cenamos cena fuimos ido vamos voy volvimos fui pedimos pedido pedir pusieron ponen sirven tomamos
tomar probamos probar probado dos tres cuatro día días semana año años gente persona personas amigos pareja
familia grupo casa
""".split())

PALABRAS_VACIAS = FUNCIONALES | DOMINIO

# Variantes que se unifican antes de contar (misma palabra escrita con o sin tilde)
VARIANTES = {"menu": "menú", "cafe": "café", "jamon": "jamón", "sidreria": "sidrería", "atencion": "atención",
             "relacion": "relación", "racion": "ración"}
