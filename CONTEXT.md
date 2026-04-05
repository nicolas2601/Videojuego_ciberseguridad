# DEADLOCK — Operación Descifrado
## Contexto de proyecto para Claude Code

---

## 1. Visión del juego

**DEADLOCK** es un juego de puzzle con narrativa ambientado en un thriller moderno de espionaje.
El jugador es un analista forense que entra a una sede abandonada de una organización criminal.
Cada habitación contiene evidencia cifrada con un método criptográfico distinto.
La criptografía **emerge del contexto narrativo** — nunca se presenta como una clase magistral.

### Principios de diseño — NO negociables
- **Sin comandos de texto.** Todo se resuelve con el mouse (drag, click, slider, conectar).
- **Mecánica única por escena.** Ninguna escena reutiliza la misma interacción.
- **Pixel art thriller moderno.** Paleta oscura (#0a0c10 base), acentos fríos azul/verde, estilo CRT.
- **Narrativa integrada.** Caja de diálogo inferior con personaje + texto que contextualiza cada puzzle.
- **Feedback visual inmediato.** El descifrado ocurre en tiempo real mientras el jugador interactúa.
- **Educación implícita.** Al resolver cada escena, un debriefing corto explica el concepto real.

---

## 2. Estructura de archivos

```
deadlock/
├── CLAUDE.md                  ← este archivo
├── main.py                    ← entry point, game loop, 60fps
├── assets/
│   ├── spritesheet.png        ← spritesheet de oficina (ya provisto)
│   ├── fonts/
│   │   └── pixel.ttf          ← fuente monospace pixelada (ej. Press Start 2P o similar)
│   └── sfx/
│       ├── ambient.ogg        ← sonido de fondo (opcional)
│       ├── success.ogg
│       └── error.ogg
├── game/
│   ├── __init__.py
│   ├── scene_manager.py       ← controla qué escena está activa, transiciones fade
│   ├── constants.py           ← WIDTH, HEIGHT, FPS, colores, paths
│   ├── intro.py               ← pantalla de título animada
│   ├── scene_caesar.py        ← Escena 1: Rueda giratoria César
│   ├── scene_base64.py        ← Escena 2: Drag-and-drop bloques Base64
│   ├── scene_hash.py          ← Escena 3: Conectar palabra→hash con líneas
│   ├── scene_dh.py            ← Escena 4: Slider Diffie-Hellman
│   ├── scene_ending.py        ← Pantalla final con score
│   └── ui/
│       ├── __init__.py
│       ├── dialogue.py        ← caja de diálogo inferior con typewriter effect
│       ├── hud.py             ← barra superior (escena, capa, estado)
│       ├── tile_renderer.py   ← carga y dibuja tiles del spritesheet
│       └── transition.py      ← fade in/out entre escenas
├── crypto/
│   ├── __init__.py
│   ├── caesar.py              ← encrypt/decrypt César
│   ├── b64_utils.py           ← helpers Base64 para el puzzle
│   ├── hash_utils.py          ← SHA-256, rainbow table simulada
│   └── dh_utils.py            ← cálculos Diffie-Hellman (g, p, A, B, K)
└── data/
    ├── dialogues.json         ← todos los textos narrativos por escena
    └── puzzles.json           ← configuración de cada puzzle (cipher, answer, hints)
```

---

## 3. Constantes globales (`game/constants.py`)

```python
WIDTH, HEIGHT = 1280, 720
FPS = 60
TITLE = "DEADLOCK — Operación Descifrado"

# Paleta principal (thriller oscuro)
C_BG         = (10, 12, 16)      # fondo base
C_BG2        = (12, 14, 20)      # superficies secundarias
C_BG3        = (14, 16, 24)      # elementos de UI
C_BORDER     = (26, 30, 48)      # bordes suaves
C_TEXT_PRI   = (200, 205, 216)   # texto primario
C_TEXT_SEC   = (90, 100, 120)    # texto secundario/muted
C_TEXT_HINT  = (58, 69, 96)      # hints muy apagados
C_ACCENT     = (74, 106, 138)    # azul frío principal
C_GREEN      = (74, 138, 90)     # verde éxito/terminal
C_RED        = (138, 58, 58)     # rojo error
C_AMBER      = (154, 138, 58)    # amarillo advertencia
C_CAESAR     = (74, 154, 90)     # color temático escena 1
C_BASE64     = (74, 106, 176)    # color temático escena 2
C_HASH       = (154, 74, 58)     # color temático escena 3
C_DH         = (154, 138, 58)    # color temático escena 4

# Spritesheet
SPRITE_PATH  = "assets/spritesheet.png"
TILE_SIZE    = 16               # px por tile en el spritesheet
```

---

## 4. Pantalla de título (`game/intro.py`)

### Visual
- Fondo: escena de oficina pixel art dibujada con tiles del spritesheet
- Centro: texto "DEADLOCK" en fuente pixelada grande, con efecto glitch sutil cada ~3s
- Subtítulo: "OPERACIÓN DESCIFRADO — 2031" en letra pequeña espaciada
- Efecto CRT: scanlines semitransparentes animadas de arriba hacia abajo en loop
- Viñeta: oscurecimiento en bordes con `pygame.draw` + alpha surface
- Badge superior izquierdo: "CLASIFICADO" con borde rojo oscuro
- Badge superior derecho: "CASO #DL-2031 // OPERACIÓN DEADLOCK"

### Elementos del fondo (usando spritesheet)
Distribuir en la escena de fondo:
- 2× escritorio marrón (center-left, center-right)  
- 1× monitor/PC (esquina izquierda, con "terminal" falsa)
- 2× archivador (pared derecha)
- 3–4× planta decorativa (esquinas y espacios)
- 1× silla de oficina (frente a escritorio)

### Menú inferior
```
[ NUEVA PARTIDA ]    [ CONTINUAR ]    [ ARCHIVOS ]    [ CRÉDITOS ]
```
Navegación con flechas o mouse. Enter/click inicia.

### Animaciones
- Fade-in del título al cargar (1.2s, ease-out)
- "INICIAR MISIÓN" parpadea con `blink` 1.2s cycle
- Scanline loop: surface con alpha 15, translateY de -h a +h en 5s
- Glitch del título: cada 4–6s random, desplaza ±2px en X por 3 frames

---

## 5. Escena 1 — Sala de interrogación: Cifrado César (`game/scene_caesar.py`)

### Narrativa
> "La nota estaba debajo del escritorio. El texto no tiene sentido...
>  parece un cifrado por desplazamiento simple. Gira la rueda hasta
>  que las palabras tengan sentido."

### Fondo
Oficina/sala de interrogación usando tiles:
- Mesa grande central
- Silla frente a la mesa
- Archivador lateral
- Planta en esquina
- Lámpara de escritorio (si existe tile)

### Mecánica: Rueda giratoria interactiva
El elemento central es una **rueda de dos anillos concéntricos** dibujada con `pygame.draw`:

```
Anillo exterior (fijo):    A B C D E F ... Z   ← alfabeto cifrado
Anillo interior (rota):    A B C D E F ... Z   ← alfabeto descifrado
Indicador triangular:      apunta a las 12 en punto (posición activa)
Centro:                    muestra el número de desplazamiento actual
```

**Interacción:**
- `MOUSEBUTTONDOWN` sobre la rueda → inicia drag
- `MOUSEMOTION` mientras drag → calcula `dx`, cada 6px de desplazamiento
  horizontal = +1 o -1 en shift (0–25)
- El texto cifrado en la nota se actualiza en **tiempo real** con cada cambio
- El color del texto descifrado cambia gradualmente: gris → verde cuando
  el shift es correcto (feedback visual sin spoiler)

**Nota interceptada** (panel izquierdo):
```
CIFRADO:    GBBW BL
DESCIFRADO: __ __ (actualiza en tiempo real)
```

**Puzzle config** (`data/puzzles.json` → escena_1):
```json
{
  "cipher_text": "GBBW BL",
  "correct_shift": 2,
  "plain_text": "FOOT ON",
  "context": "Coordenadas de reunión cifradas. Desplazamiento: 2"
}
```

**Validación:**
- Botón "VERIFICAR CLAVE" → comprueba `shift == correct_shift`
- Si correcto: flash verde + diálogo de éxito + debriefing César + transición a Escena 2
- Si incorrecto: flash rojo + diálogo de error (no penalización en primera versión)

**Pistas (3 niveles, cuestan 1 punto cada una):**
1. "El cifrado César desplaza cada letra un número fijo en el alfabeto."
2. "El texto descifrado debería ser una frase corta en inglés con sentido."
3. "El desplazamiento es un número menor que 5."

**Debriefing** (popup al completar):
> César inventó este cifrado en el siglo I a.C. Hoy es trivialmente
> rompible — solo 25 combinaciones posibles. La rueda que acabas de
> usar se llama 'disco de Alberti' y fue la primera máquina de cifrado
> portátil de la historia.

---

## 6. Escena 2 — Sala de servidores: Base64 (`game/scene_base64.py`)

### Narrativa
> "Los archivos del servidor están codificados. No están cifrados para
>  ocultar — Base64 es solo codificación. Pero necesitas decodificarlos
>  para leer el contenido. Arrastra los bloques al orden correcto."

### Fondo
Sala de servidores:
- Racks de servidores (archivadores verticales del spritesheet, repetidos)
- Monitor(es) con texto verde
- Cables en el suelo (dibujados con `pygame.draw.line`)

### Mecánica: Drag-and-drop de bloques
El string Base64 está dividido en **bloques de 4 caracteres** que aparecen
desordenados. El jugador debe arrastrarlos a las ranuras correctas.

**Layout:**
```
Panel izquierdo: bloques desordenados (pool)
  [ SGVs ] [ bG8g ] [ V29y ] [ bGQh ]   (mezclados aleatoriamente)

Panel derecho: ranuras numeradas
  Ranura 1: [        ]
  Ranura 2: [        ]
  Ranura 3: [        ]
  Ranura 4: [        ]

Panel inferior: resultado decodificado (actualiza cuando todas las ranuras tienen bloque)
  Resultado: __ __ __ __
```

**Interacción drag-and-drop:**
- `MOUSEBUTTONDOWN` sobre un bloque → lo "levanta" (renderiza encima de todo)
- `MOUSEMOTION` → mueve el bloque con el cursor
- `MOUSEBUTTONUP` → si el cursor está sobre una ranura, deposita el bloque;
  si no, devuelve al pool
- Al depositar en ranura correcta: borde verde tenue
- Al depositar en ranura incorrecta: borde rojo tenue, devuelve al pool

**Decodificación en tiempo real:**
Cada vez que cambia el estado de las ranuras, re-decodifica:
```python
import base64
partial = ''.join(slot or '    ' for slot in slots)
try:
    decoded = base64.b64decode(partial.encode()).decode('utf-8', errors='replace')
except Exception:
    decoded = '?????'
```

**Puzzle config:**
```json
{
  "encoded": "SGVsbG8gV29ybGQh",
  "blocks": ["SGVs", "bG8g", "V29y", "bGQh"],
  "decoded": "Hello World!",
  "hint_message": "Cada grupo de 4 chars Base64 representa 3 bytes de datos reales."
}
```

**Panel educativo lateral** (siempre visible):
```
BASE64
4 chars = 3 bytes
64 símbolos posibles
A-Z, a-z, 0-9, +, /
No es cifrado — es
codificación binaria
```

**Debriefing:**
> Base64 convierte datos binarios en texto ASCII transportable.
> Se inventó para enviar archivos por email (que solo soportaba texto).
> NO es cifrado — cualquiera puede decodificarlo. El padding '='
> indica bytes faltantes en el último bloque.

---

## 7. Escena 3 — Oficina del director: Hash SHA-256 (`game/scene_hash.py`)

### Narrativa
> "Encontré la base de datos de contraseñas. Están guardadas como hashes —
>  no puedo revertirlos directamente. Pero tengo una lista de contraseñas
>  comunes... si alguna coincide, tengo acceso."

### Fondo
Oficina ejecutiva:
- Escritorio grande (tile mesa grande del spritesheet)
- Silla ejecutiva
- Archivadores con carpetas
- Monitor con base de datos

### Mecánica: Conectar con líneas (visual matching)
**Dos columnas:**
```
Columna izquierda:          Columna derecha:
Palabras candidatas         Hashes (truncados a 16 chars)

[ password   ]  ————?————  [ 5f4dcc3b5aa765d6 ]
[ 123456     ]  ————?————  [ e10adc3949ba59ab ]
[ qwerty     ]  ————?————  [ d8578edf8458ce06 ]
[ letmein    ]  ————?————  [ 0d107d09f5bbe938 ]
[ deadlock   ]  ————?————  [ a1b2c3d4e5f67890 ]  ← objetivo real
```

**Interacción de conexión:**
- `MOUSEBUTTONDOWN` sobre una palabra → inicia línea (rubber band)
- `MOUSEMOTION` → dibuja línea desde la palabra hasta el cursor
- `MOUSEBUTTONUP` sobre un hash → crea conexión
  - Si es correcto: línea se vuelve verde, nodos resaltados
  - Si es incorrecto: línea roja, desaparece en 0.5s
- Una vez conectado correctamente, la palabra se "bloquea" (no se puede mover)

**Intento de ir al revés (enseña irreversibilidad):**
Si el jugador intenta arrastrar desde un hash hacia una palabra:
- El cursor cambia a "bloqueado"
- Diálogo: *"Los hashes son funciones de una sola vía. No puedes revertirlos."*

**Cálculo real:**
```python
import hashlib
def sha256_short(text):
    return hashlib.sha256(text.encode()).hexdigest()[:16]
```

Los hashes se calculan en tiempo real desde `data/puzzles.json`:
```json
{
  "candidates": ["password", "123456", "qwerty", "letmein", "deadlock"],
  "target_word": "deadlock",
  "context": "Contraseña del director del bunker"
}
```

**Panel lateral educativo:**
```
SHA-256
Siempre 256 bits / 64 hex
Mismo input = mismo output
IRREVERSIBLE por diseño
Avalancha: 1 bit cambiado
→ hash completamente distinto
```

**Debriefing:**
> Un hash criptográfico transforma cualquier dato en una huella digital
> de tamaño fijo. SHA-256 es estándar para almacenar contraseñas. Las
> 'rainbow tables' como la que usaste existen en el mundo real —
> por eso las contraseñas fuertes y el 'salting' son esenciales.

---

## 8. Escena 4 — Sala de comunicaciones: Diffie-Hellman (`game/scene_dh.py`)

### Narrativa
> "Intercepté una comunicación cifrada entre dos agentes. Están
>  negociando una clave compartida en tiempo real usando números públicos.
>  Si deduzco su clave antes de que terminen, puedo leer el mensaje."

### Fondo
Sala de comunicaciones/radio:
- Dos monitores (uno por "agente")
- Equipo de radio/antenas (dibujado con pygame.draw)
- Cables conectando equipos
- Luz parpadeante de "transmisión activa"

### Mecánica: Slider interactivo de negociación
**Layout en 3 columnas:**

```
[AGENTE A — TÚ]          [CANAL PÚBLICO]          [AGENTE B — SOSPECHOSO]

Número secreto: a         g = 5 (base)              Número secreto: b
[SLIDER: 1-20]           p = 23 (primo)             (oculto: 15)

A = g^a mod p  →  envia A  →  recibe B = g^b mod p

Calcula K:                                           Calcula K:
K = B^a mod p             ???                        K = A^b mod p
[SLIDER para K]                                      (oculto hasta confirmar)

[ CONFIRMAR CLAVE ]
```

**Interacción:**
1. Jugador arrastra slider para elegir `a` (1–20)
2. En tiempo real se muestra `A = pow(g, a, p)`
3. Sistema "envía" A al otro lado y muestra `B = pow(g, b, p)` (b=15, oculto)
4. Jugador calcula y ajusta segundo slider para `K = pow(B, a, p)`
5. Al confirmar: compara con `pow(A, b, p)` — deben ser iguales

**Visualización del protocolo:**
Flecha animada de izquierda a derecha cuando se "envía" A.
Flecha animada de derecha a izquierda cuando llega B.
Los valores públicos (g, p, A, B) siempre visibles.
Los valores privados (a, b, K) ocultos del "otro lado".

**Cálculos en tiempo real:**
```python
def dh_step(g, p, secret):
    return pow(g, secret, p)  # g^secret mod p

# Parámetros del puzzle
G, P = 5, 23
B_SECRET = 15  # secreto del agente B, nunca mostrado al jugador

# Cuando jugador mueve slider:
a = slider_value          # secreto del jugador (1-20)
A = dh_step(G, P, a)     # valor público del jugador
B = dh_step(G, P, B_SECRET)  # valor público del sospechoso (mostrado)
K_player = dh_step(B, P, a)  # clave calculada por el jugador
K_real   = dh_step(A, P, B_SECRET)  # clave real (para validar)
# assert K_player == K_real cuando está correcto
```

**Panel educativo lateral:**
```
DIFFIE-HELLMAN
g, p: parámetros públicos
a, b: secretos privados
A = g^a mod p  (público)
B = g^b mod p  (público)
K = B^a = A^b  (¡compartida!)
Nadie en el canal puede
calcular K sin a o b
```

**Debriefing:**
> Diffie-Hellman (1976) permitió por primera vez a dos personas crear
> una clave secreta compartida sobre un canal público inseguro.
> Es la base de HTTPS, SSH y Signal. El problema del logaritmo discreto
> hace que calcular 'a' a partir de A = g^a mod p sea computacionalmente
> inviable con números reales de 2048+ bits.

---

## 9. UI compartida

### Caja de diálogo (`game/ui/dialogue.py`)
- Barra inferior fija, altura 80px
- Fondo: `C_BG` con 95% alpha, borde superior `C_BORDER`
- Nombre del hablante: 9px, `C_ACCENT`, letra espaciada
- Texto: 11px, `C_TEXT_SEC`, typewriter effect (1 char cada 30ms)
- Cursor parpadeante `|` al final mientras escribe
- Click/Enter avanza al siguiente mensaje o salta el typewriter

### HUD superior (`game/ui/hud.py`)
```
[OPERACIÓN DEADLOCK]    [ESCENA 01 — SALA DE INTERROGACIÓN]    [CAPA 1/4 — CÉSAR]
```
- Altura 36px, fondo semitransparente
- Izquierda: nombre de la operación (`C_TEXT_HINT`)
- Centro: nombre de la escena actual (`C_TEXT_SEC`)
- Derecha: progreso de capas (`C_ACCENT`)
- Badge de estado en el centro-bajo: "Encuentra el desplazamiento correcto"

### Transiciones (`game/ui/transition.py`)
- Fade-out a negro (0.4s) → carga siguiente escena → Fade-in (0.4s)
- Surface negra con alpha que incrementa/decrementa cada frame

### Tile renderer (`game/ui/tile_renderer.py`)
Carga el spritesheet `assets/spritesheet.png` y permite extraer tiles:
```python
def get_tile(surface, col, row, tile_size=16, scale=3):
    rect = pygame.Rect(col * tile_size, row * tile_size, tile_size, tile_size)
    tile = surface.subsurface(rect).copy()
    return pygame.transform.scale(tile, (tile_size * scale, tile_size * scale))
```
Cada escena define qué tiles usa y dónde los posiciona en el fondo.

---

## 10. Sistema de puntuación

Al completar cada escena se registra:
- Tiempo empleado (segundos)
- Número de pistas usadas (0–3)
- Intentos fallidos

Score por escena = `max(100 - tiempo/10 - pistas*15 - intentos*5, 10)`

Rango final:
- 340–400 pts → **MAESTRO CRIPTÓGRAFO**
- 260–339 pts → **AGENTE SENIOR**  
- 160–259 pts → **ANALISTA**
- < 160 pts   → **RECLUTA**

---

## 11. `main.py` — Game loop

```python
import pygame
from game.scene_manager import SceneManager
from game.constants import WIDTH, HEIGHT, FPS, TITLE

def main():
    pygame.init()
    pygame.display.set_caption(TITLE)
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    manager = SceneManager(screen)
    manager.load_scene("intro")

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0  # delta time en segundos
        events = pygame.event.get()

        for event in events:
            if event.type == pygame.QUIT:
                running = False
            manager.handle_event(event)

        manager.update(dt)
        manager.draw()
        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
```

### `SceneManager` (`game/scene_manager.py`)
- Mantiene escena activa como objeto
- `load_scene(name)` → instancia la escena correcta
- `handle_event(event)` → delega a escena activa
- `update(dt)` → delega a escena activa + maneja transiciones
- `draw()` → dibuja escena activa + overlay de transición encima

**Orden de escenas:**
`intro` → `caesar` → `base64` → `hash` → `diffie_hellman` → `ending`

Cada escena llama `self.manager.next_scene()` cuando se completa.

---

## 12. Datos externos (`data/puzzles.json`)

```json
{
  "caesar": {
    "cipher_text": "GBBW BL",
    "correct_shift": 2,
    "plain_text": "FOOT ON",
    "hints": [
      "El cifrado César desplaza cada letra un número fijo en el alfabeto.",
      "El texto descifrado debería ser una frase corta en inglés con sentido.",
      "El desplazamiento correcto es un número entre 1 y 5."
    ]
  },
  "base64": {
    "encoded": "SGVsbG8gV29ybGQh",
    "blocks": ["SGVs", "bG8g", "V29y", "bGQh"],
    "decoded": "Hello World!",
    "hints": [
      "Base64 divide los datos en grupos de 6 bits, codificados como caracteres.",
      "Cada bloque de 4 chars Base64 representa exactamente 3 bytes.",
      "El orden correcto es el mismo que en el string original del servidor."
    ]
  },
  "hash": {
    "candidates": ["password", "123456", "qwerty", "letmein", "deadlock"],
    "target_word": "deadlock",
    "hints": [
      "Los hashes son funciones de una sola vía — no puedes revertirlos.",
      "Calcula el SHA-256 de cada candidato y compara con los hashes del archivo.",
      "La contraseña del director es el nombre de la operación."
    ]
  },
  "diffie_hellman": {
    "g": 5,
    "p": 23,
    "b_secret": 15,
    "hints": [
      "A = g elevado a tu número secreto, módulo p.",
      "Recibirás B del otro lado. Tu clave compartida es B^a mod p.",
      "Prueba con a=6. Calcula A=5^6 mod 23, luego K=B^6 mod 23."
    ]
  }
}
```

---

## 13. Instrucciones para subagentes de Claude Code

Este proyecto debe implementarse con los siguientes subagentes especializados:

### Subagente 1: `game-engine`
**Responsabilidad:** `main.py`, `game/scene_manager.py`, `game/constants.py`, `game/ui/transition.py`
**Tarea:** Implementar el game loop base, sistema de escenas, transiciones fade.
**Entregable:** Juego que arranca, muestra pantalla negra y maneja el ciclo correctamente.

### Subagente 2: `asset-renderer`
**Responsabilidad:** `game/ui/tile_renderer.py`, carga del spritesheet, fondos de todas las escenas
**Tarea:** Implementar el extractor de tiles del spritesheet y los fondos de cada escena.
**Nota:** El spritesheet está en `assets/spritesheet.png`. Tile base = 16px. Escalar ×3 para 48px display.

### Subagente 3: `ui-systems`
**Responsabilidad:** `game/ui/dialogue.py`, `game/ui/hud.py`, sistema de pistas, score
**Tarea:** Caja de diálogo con typewriter effect, HUD superior, panel de pistas.

### Subagente 4: `crypto-puzzles`
**Responsabilidad:** `crypto/`, `data/puzzles.json`, lógica de validación de cada puzzle
**Tarea:** Implementar las 4 mecánicas criptográficas. Sin UI — solo la lógica pura.

### Subagente 5: `scene-caesar`
**Responsabilidad:** `game/scene_caesar.py`
**Tarea:** Rueda giratoria interactiva con drag, actualización en tiempo real del descifrado.
**Depende de:** subagentes `crypto-puzzles` y `ui-systems`.

### Subagente 6: `scene-base64`
**Responsabilidad:** `game/scene_base64.py`
**Tarea:** Sistema drag-and-drop de bloques Base64 con ranuras y decodificación en tiempo real.
**Depende de:** subagentes `crypto-puzzles` y `ui-systems`.

### Subagente 7: `scene-hash`
**Responsabilidad:** `game/scene_hash.py`
**Tarea:** Sistema de conexión visual con líneas (rubber band), validación de pares palabra→hash.
**Depende de:** subagentes `crypto-puzzles` y `ui-systems`.

### Subagente 8: `scene-dh`
**Responsabilidad:** `game/scene_dh.py`
**Tarea:** Slider(s) para Diffie-Hellman, animación de intercambio de claves, cálculo en tiempo real.
**Depende de:** subagentes `crypto-puzzles` y `ui-systems`.

### Subagente 9: `intro-ending`
**Responsabilidad:** `game/intro.py`, `game/scene_ending.py`
**Tarea:** Pantalla de título con efectos CRT/glitch/scanline, menú, pantalla final con score y rango.

---

## 14. Orden de implementación recomendado

```
1. constants.py + main.py (loop vacío que abre ventana)
2. scene_manager.py (sistema de escenas con fade)
3. tile_renderer.py + spritesheet parsing
4. dialogue.py + hud.py (UI compartida)
5. crypto/ (lógica pura, sin pygame)
6. intro.py (pantalla de título)
7. scene_caesar.py (la más visual — valida el engine)
8. scene_base64.py
9. scene_hash.py
10. scene_dh.py
11. scene_ending.py
12. Integración final + testing
```

---

## 15. Dependencias Python

```
pygame>=2.5.0
```

Instalar con:
```bash
pip install pygame
```

Las librerías criptográficas (`hashlib`, `base64`, `math`) son de la stdlib de Python — no requieren instalación.

---

## 16. Notas de implementación críticas

1. **Delta time:** Todas las animaciones deben usar `dt` (segundos desde último frame), no frames fijos.
2. **Spritesheet:** Analizar visualmente el archivo `assets/spritesheet.png` antes de mapear coordenadas de tiles.
3. **Fuente:** Si no hay `.ttf` pixelada, usar `pygame.font.SysFont('monospace', size)` como fallback.
4. **Resolución:** 1280×720 fija. No soportar resize en v1.
5. **Mouse-only:** Ninguna escena del puzzle debe requerir teclado para resolverse (solo para navegación de menú está OK).
6. **Feedback inmediato:** Cada cambio de slider/rueda/drag debe actualizar la UI en el mismo frame.
7. **Sin hardcoding de posiciones en escenas:** Usar constantes o proporciones relativas a WIDTH/HEIGHT para que sea ajustable.
