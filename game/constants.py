import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

WIDTH, HEIGHT = 1280, 720
FPS = 60
TITLE = "DEADLOCK \u2014 Operaci\u00f3n Descifrado"

# Paleta principal (thriller oscuro)
C_BG         = (10, 12, 16)
C_BG2        = (12, 14, 20)
C_BG3        = (14, 16, 24)
C_BORDER     = (26, 30, 48)
C_TEXT_PRI   = (200, 205, 216)
C_TEXT_SEC   = (90, 100, 120)
C_TEXT_HINT  = (58, 69, 96)
C_ACCENT     = (74, 106, 138)
C_GREEN      = (74, 138, 90)
C_RED        = (138, 58, 58)
C_AMBER      = (154, 138, 58)
C_CAESAR     = (74, 154, 90)
C_BASE64     = (74, 106, 176)
C_HASH       = (154, 74, 58)
C_DH         = (154, 138, 58)
C_WHITE      = (220, 225, 235)
C_PANEL      = (16, 18, 28)
C_NEON       = (57, 255, 20)     # Verde neon #39FF14 para legibilidad
C_TERM_BG    = (5, 5, 8)         # Fondo terminal
C_TERM_GREEN = (0, 200, 0)       # Texto terminal

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
