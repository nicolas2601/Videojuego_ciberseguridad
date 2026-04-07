# DEADLOCK - Operacion Descifrado

Videojuego educativo sobre criptografia desarrollado en Python con Pygame para la materia de ciberseguridad.

El juego te pone en el rol de un agente que tiene que resolver puzzles de distintos metodos criptograficos para descifrar mensajes interceptados de una organizacion criminal.

## Que tiene el juego

- 4 escenas jugables con puzzles de criptografia:
  - **Cifrado Cesar** - descifrar mensajes con desplazamiento
  - **Base64** - corregir transmisiones corruptas en codificacion Base64
  - **Hash SHA-256** - verificar integridad de archivos con funciones hash
  - **Diffie-Hellman** - interceptar un intercambio de claves y calcular el secreto compartido
- Hub central donde seleccionas a que sala entrar
- Sistema de dificultad (Dummy, Mid, Senior, Noob)
- Dialogos con el asistente NOVA que te va guiando
- Musica de fondo ambiental
- Puntaje por escena y puntaje total

## Requisitos

- Python 3.10 o superior
- pygame-ce (pygame community edition)

## Como instalarlo y probarlo

1. Clonar el repositorio:

```bash
git clone https://github.com/nicolas2601/Videojuego_ciberseguridad.git
cd Videojuego_ciberseguridad
```

2. (Opcional) Crear un entorno virtual:

```bash
python3 -m venv venv
source venv/bin/activate
```

En Windows seria:
```bash
python -m venv venv
venv\Scripts\activate
```

3. Instalar pygame-ce:

```bash
pip install pygame-ce
```

4. Ejecutar el juego:

```bash
python main.py
```

Si te sale un error de que no encuentra algun modulo, asegurate de estar en la carpeta raiz del proyecto (donde esta `main.py`).

## Estructura del proyecto

```
├── main.py                 # Punto de entrada del juego
├── musica.mp3              # Musica de fondo
├── game/
│   ├── constants.py        # Colores, dimensiones, config de dificultad
│   ├── intro.py            # Escena de introduccion
│   ├── scene_hub.py        # Hub central de seleccion
│   ├── scene_caesar.py     # Puzzle de cifrado Cesar
│   ├── scene_base64.py     # Puzzle de Base64
│   ├── scene_hash.py       # Puzzle de Hash SHA-256
│   ├── scene_dh.py         # Puzzle de Diffie-Hellman
│   ├── scene_ending.py     # Escena final
│   ├── scene_manager.py    # Control de escenas y transiciones
│   └── ui/
│       ├── dialogue.py     # Sistema de dialogos
│       ├── hud.py          # Barra superior de info
│       └── draw_assets.py  # Graficos generados con codigo
├── crypto/
│   ├── caesar.py           # Logica del cifrado Cesar
│   ├── b64_utils.py        # Utilidades de Base64
│   ├── hash_utils.py       # Funciones de hash
│   └── dh_utils.py         # Funciones de Diffie-Hellman
├── data/
│   ├── puzzles.json        # Configuracion de puzzles por ronda
│   └── dialogues.json      # Textos de dialogos del juego
└── tests/
    └── test_game.py        # Tests unitarios
```

## Controles

- **Click izquierdo** - Interactuar con botones, seleccionar opciones, escribir en campos
- **Teclado numerico** - Ingresar valores en los campos de texto
- **Enter** - Confirmar respuesta
- **Tab** - Siguiente campo

## Dificultades

| Nivel | Pistas | Ayudas visuales |
|-------|--------|-----------------|
| Dummy | 3 gratis | Si, guia completa |
| Mid | 1 gratis | Parcial |
| Senior | 1 gratis | No |
| Noob | 0 | No, suerte |

## Tests

Para correr los tests:

```bash
pip install pytest
python -m pytest tests/ -v
```

## Notas

- Todos los graficos se generan por codigo (no necesita imagenes externas)
- La resolucion es 1280x720
- Si no se escucha la musica verifica que tengas el archivo `musica.mp3` en la carpeta raiz
