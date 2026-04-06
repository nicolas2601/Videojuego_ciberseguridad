import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

WIDTH, HEIGHT = 1280, 720
FPS = 60
TITLE = "DEADLOCK \u2014 Operaci\u00f3n Descifrado"

# Paleta principal (thriller — brillo ajustado para visibilidad)
C_BG         = (22, 26, 34)      # Fondo base (subido)
C_BG2        = (30, 34, 44)      # Superficies (subido)
C_BG3        = (38, 42, 54)      # UI elements (subido)
C_BORDER     = (55, 62, 85)      # Bordes (subido)
C_TEXT_PRI   = (230, 235, 245)   # Texto primario (mas brillante)
C_TEXT_SEC   = (140, 150, 170)   # Texto secundario (subido)
C_TEXT_HINT  = (90, 100, 130)    # Hints (subido)
C_ACCENT     = (90, 140, 200)    # Azul acento (mas brillante)
C_GREEN      = (90, 190, 120)    # Verde exito (mas brillante)
C_RED        = (200, 75, 75)     # Rojo error (mas brillante)
C_AMBER      = (210, 190, 70)    # Ambar (mas brillante)
C_CAESAR     = (90, 210, 120)    # Color tematico 1
C_BASE64     = (90, 140, 220)    # Color tematico 2
C_HASH       = (210, 100, 75)    # Color tematico 3
C_DH         = (210, 190, 70)    # Color tematico 4
C_WHITE      = (240, 245, 255)   # Blanco
C_PANEL      = (28, 32, 42)      # Panel (subido)
C_NEON       = (57, 255, 20)     # Verde neon #39FF14
C_TERM_BG    = (12, 14, 20)      # Fondo terminal (subido)
C_TERM_GREEN = (30, 230, 30)     # Texto terminal (mas brillante)

# Difficulty levels
DIFFICULTY_DUMMY  = 0   # Ayudas visuales constantes
DIFFICULTY_MID    = 1   # Pistas normales
DIFFICULTY_SENIOR = 2   # Pocas pistas
DIFFICULTY_NOOB   = 3   # Sin pistas, logica pura

DIFFICULTY_NAMES = {
    DIFFICULTY_DUMMY: "DUMMY",
    DIFFICULTY_MID: "MID",
    DIFFICULTY_SENIOR: "SENIOR",
    DIFFICULTY_NOOB: "YOU ARE NOT NOOB",
}

DIFFICULTY_DESC = {
    DIFFICULTY_DUMMY: "Ayudas visuales constantes, guia paso a paso",
    DIFFICULTY_MID: "Pistas disponibles, interfaz con ayudas",
    DIFFICULTY_SENIOR: "Pocas pistas, sin ayudas visuales extra",
    DIFFICULTY_NOOB: "Sin pistas. Logica pura. Buena suerte.",
}

# Free hints per difficulty (hint 0 is always free)
HINTS_CONFIG = {
    DIFFICULTY_DUMMY: {"free_hints": 3, "visual_aids": True},
    DIFFICULTY_MID: {"free_hints": 1, "visual_aids": False},
    DIFFICULTY_SENIOR: {"free_hints": 1, "visual_aids": False},
    DIFFICULTY_NOOB: {"free_hints": 0, "visual_aids": False},
}

# Player movement
PLAYER_SPEED = 180  # px/s
PLAYER_SIZE  = 28   # px (character square)

# Scenes order
SCENE_ORDER = ["intro", "hub", "caesar", "base64", "hash", "diffie_hellman", "ending"]

# Puzzle scenes (for hub)
PUZZLE_SCENES = {
    "caesar": {
        "name": "Sala de Interrogaci\u00f3n",
        "subtitle": "Cifrado C\u00e9sar",
        "color": C_CAESAR,
        "icon": "01",
    },
    "base64": {
        "name": "Sala de Servidores",
        "subtitle": "Codificaci\u00f3n Base64",
        "color": C_BASE64,
        "icon": "02",
    },
    "hash": {
        "name": "Oficina del Director",
        "subtitle": "Hash SHA-256",
        "color": C_HASH,
        "icon": "03",
    },
    "diffie_hellman": {
        "name": "Sala de Comunicaciones",
        "subtitle": "Diffie-Hellman",
        "color": C_DH,
        "icon": "04",
    },
}
