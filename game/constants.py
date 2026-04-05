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

# Spritesheet
SPRITE_PATH  = os.path.join(BASE_DIR, "assets", "spritesheet.png")
TILES_PATH   = os.path.join(BASE_DIR, "assets", "tiles.png")
TILE_SIZE    = 16

# Scenes order for linear fallback
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
