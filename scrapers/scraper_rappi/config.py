"""
Configuración del Scraper de Rappi - Proesa
Optimizado para maximizar el catálogo de Tabaco (Vapes con/sin nicotina, Cigarrillos, IQOS)
y Bebidas Alcohólicas (Cervezas, Destilados, Vinos) en Bogotá y Colombia, evitando falsos positivos de comida y hogar.
"""

# 3 Zonas estratégicas y perfectamente distribuidas de Bogotá (Norte, Centro/Salitre y Sur-Occidente)
LOCATIONS = {
    "bogota_norte": {
        "lat": 4.6850,
        "lng": -74.0550,
        "city": "Bogotá",
        "zone": "Norte / Chicó / Chapinero / Usaquén",
    },
    "bogota_centro_salitre": {
        "lat": 4.6350,
        "lng": -74.0820,
        "city": "Bogotá",
        "zone": "Centro / Teusaquillo / Salitre",
    },
    "bogota_sur_occidente": {
        "lat": 4.6280,
        "lng": -74.1550,
        "city": "Bogotá",
        "zone": "Sur-Occidente / Kennedy / Américas",
    },
}

# Términos de búsqueda refinados y específicos para evitar comida/restaurantes
TARGET_CATEGORIES = {
    "TABACO": [
        # Cigarrillos y marcas líderes
        "cigarrillos", "cigarros", "cigarro", "marlboro", "lucky strike",
        "rothmans", "chesterfield", "starlite", "dunhill", "camel",
        "parliament", "kent", "l&m", "boston", "cigarrillo mentolado",
        # Vapeo, Pods y Desechables (con o sin nicotina)
        "vape", "vapeador", "vapes", "vapo", "vuse", "vuse go",
        "relx", "elf bar", "waka", "ignite", "lost mary", "geek bar",
        "vape pod", "e-liquid", "sales de nicotina", "smok vape", "vape desechable",
        # Tabaco calentado
        "iqos", "iluma", "terea", "heets",
        # Puros, picadura y accesorios de tabaco
        "puros", "puro habano", "habanos", "montecristo puros", "cohiba", "romeo y julieta puros",
        "tabaco de liar", "picadura de tabaco", "papel de fumar", "sedas raw", "sedas ocb", "papel smoking", "filtros ocb", "blunt tabaco"
    ],
    "ALCOHOL": [
        # Cervezas
        "cerveza", "cervezas", "corona extra", "heineken", "club colombia", "cerveza aguila",
        "aguila light", "cerveza poker", "cerveza costeña", "cerveza pilsen", "cerveza andina", "stella artois",
        "budweiser", "bbc cerveza", "bogota beer company", "cerveza cusqueña", "miller lite",
        "peroni", "michelob ultra", "erdinger", "cerveza guinness", "paulaner", "cerveza artesanal",
        # Aguardientes
        "aguardiente", "antioqueño", "antioqueño verde", "antioqueño azul",
        "néctar azul", "néctar rojo", "amarillo de manzanares",
        "aguardiente llanero", "blanco del valle", "aguardiente caucano",
        # Ron
        "ron viejo de caldas", "ron medellín", "ron zacapa", "ron havana club",
        "ron bacardi", "flor de caña", "ron la hechicera", "ron santafé", "ron diplomático",
        # Whisky
        "whisky", "whiskey", "buchanans", "old parr", "johnnie walker",
        "black label", "red label", "double black", "chivas regal", "jack daniels",
        "black and white whisky", "glenfiddich", "macallan", "singleton", "jameson",
        "ballantines", "grants whisky", "jim beam", "monkey shoulder",
        # Tequila y Mezcal
        "tequila", "don julio", "don julio 70", "jose cuervo", "tequila patron",
        "tequila 1800", "herradura", "tequila olmeca", "mezcal", "mezcal 400 conejos", "mezcal ojo de tigre",
        # Vodka y Ginebra
        "vodka", "smirnoff", "absolut vodka", "grey goose", "belvedere", "ketel one",
        "ginebra", "gin tanqueray", "bombay sapphire", "beefeater", "hendricks gin", "gordons gin",
        # Vinos y Espumosos
        "vino tinto", "vino blanco", "vino rosado", "champagne",
        "vino prosecco", "vino cava", "gato negro vino", "casillero del diablo", "santa rita vino",
        "concha y toro", "navarro correas", "trapiche vino", "las moras vino", "undurraga vino",
        # Aperitivos y RTD
        "aperol", "campari", "baileys", "jagermeister", "smirnoff ice", "four loko"
    ]
}

# Diccionario de marcas conocidas para normalización precisa
KNOWN_BRANDS = [
    "Lucky Strike", "Marlboro", "Rothmans", "Chesterfield", "Starlite", "Dunhill", "Camel", "Parliament",
    "Kent", "L&M", "Vuse", "Relx", "Elf Bar", "Waka", "Ignite", "Lost Mary", "Geek Bar", "Iqos", "Terea",
    "Heets", "Smok", "Raw", "OCB", "Smoking", "Montecristo", "Cohiba", "Romeo y Julieta", "Carlton",
    "Corona", "Heineken", "Club Colombia", "Aguila", "Poker", "Costeña", "Pilsen", "Stella Artois",
    "Budweiser", "BBC", "Bogota Beer Company", "Andina", "Cusqueña", "Miller", "Peroni", "Michelob",
    "Antioqueño", "Aguardiente Antioqueño", "Néctar", "Llanero", "Amarillo de Manzanares", "Blanco del Valle",
    "Viejo de Caldas", "Ron Medellín", "Zacapa", "Havana Club", "Bacardí", "Flor de Caña", "La Hechicera",
    "Buchanan's", "Old Parr", "Johnnie Walker", "Chivas Regal", "Jack Daniel's", "Black & White", "Glenfiddich",
    "The Macallan", "Singleton", "Jameson", "Ballantine's", "Grant's", "Jim Beam",
    "Don Julio", "José Cuervo", "Patrón", "1800", "Herradura", "Olmeca", "400 Conejos", "Ojo de Tigre",
    "Smirnoff", "Absolut", "Grey Goose", "Belvedere", "Ketel One", "Tanqueray", "Bombay Sapphire",
    "Beefeater", "Hendrick's", "Gordon's", "Bulldog", "Gato Negro", "Casillero del Diablo", "Santa Rita",
    "Concha y Toro", "Navarro Correas", "Trapiche", "Las Moras", "Undurraga", "Frontera", "Marqués de Riscal",
    "Moët & Chandon", "Aperol", "Campari", "Baileys", "Jägermeister"
]
