"""All game visuals generated with pygame.draw — no external image files."""
import pygame
import math
from game.constants import (C_BG, C_BG2, C_BG3, C_BORDER, C_TEXT_SEC,
                            C_ACCENT, C_GREEN, C_NEON, C_AMBER, C_WHITE,
                            PLAYER_SIZE, WIDTH, HEIGHT)


# ── Player character ──────────────────────────────────────────────

def draw_player(surface, x, y, direction="down"):
    """Draw pixel-art-style character facing a direction (up/down/left/right)."""
    s = PLAYER_SIZE
    # Body
    body_color = (60, 70, 90)
    head_color = (180, 160, 140)
    eye_color = C_NEON

    # Shadow
    shadow = pygame.Surface((s, 8), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (0, 0, 0, 60), (0, 0, s, 8))
    surface.blit(shadow, (x, y + s - 4))

    # Body (torso)
    pygame.draw.rect(surface, body_color, (x + 4, y + s // 3, s - 8, s * 2 // 3))
    # Shoulders
    pygame.draw.rect(surface, (50, 60, 80), (x + 2, y + s // 3, s - 4, 6))

    # Head
    pygame.draw.rect(surface, head_color, (x + 6, y + 2, s - 12, s // 3))

    # Eyes based on direction
    ex, ey = x + 9, y + 8
    ex2 = x + s - 13
    if direction == "down":
        pygame.draw.rect(surface, eye_color, (ex, ey, 3, 3))
        pygame.draw.rect(surface, eye_color, (ex2, ey, 3, 3))
    elif direction == "up":
        pass  # Back of head, no eyes
    elif direction == "left":
        pygame.draw.rect(surface, eye_color, (ex - 2, ey, 3, 3))
    elif direction == "right":
        pygame.draw.rect(surface, eye_color, (ex2 + 2, ey, 3, 3))


# ── Office furniture ────────────────────────────────────────────

def draw_desk(surface, x, y, w=96, h=48):
    """Brown office desk."""
    top_color = (100, 70, 45)
    leg_color = (70, 50, 30)
    # Table top
    pygame.draw.rect(surface, top_color, (x, y, w, h))
    pygame.draw.rect(surface, leg_color, (x, y, w, h), 2)
    # Legs
    pygame.draw.rect(surface, leg_color, (x + 4, y + h, 6, 12))
    pygame.draw.rect(surface, leg_color, (x + w - 10, y + h, 6, 12))
    # Drawer line
    pygame.draw.line(surface, leg_color, (x + 10, y + h // 2), (x + w - 10, y + h // 2), 1)


def draw_monitor(surface, x, y, text="", text_color=C_NEON):
    """Computer monitor with optional text."""
    # Stand
    pygame.draw.rect(surface, (50, 50, 55), (x + 14, y + 32, 12, 8))
    pygame.draw.rect(surface, (60, 60, 65), (x + 8, y + 38, 24, 4))
    # Screen frame
    pygame.draw.rect(surface, (40, 42, 48), (x, y, 40, 32))
    # Screen
    pygame.draw.rect(surface, C_BG, (x + 3, y + 3, 34, 26))
    # Screen glow
    if text:
        font = pygame.font.SysFont("monospace", 8)
        ts = font.render(text, True, text_color)
        surface.blit(ts, (x + 5, y + 8))
    else:
        # Fake terminal lines
        for i in range(3):
            lw = 12 + (i * 7) % 15
            pygame.draw.rect(surface, (0, 60, 0), (x + 5, y + 6 + i * 7, lw, 2))


def draw_server_rack(surface, x, y, h=80):
    """Tall server rack."""
    rack_color = (35, 38, 45)
    led_colors = [C_GREEN, C_NEON, C_AMBER, (200, 50, 50)]
    # Main body
    pygame.draw.rect(surface, rack_color, (x, y, 32, h))
    pygame.draw.rect(surface, (45, 48, 55), (x, y, 32, h), 2)
    # Rack units
    for i in range(h // 16):
        uy = y + 4 + i * 16
        pygame.draw.rect(surface, (28, 30, 36), (x + 3, uy, 26, 12))
        pygame.draw.rect(surface, (50, 52, 58), (x + 3, uy, 26, 12), 1)
        # LED
        led = led_colors[i % len(led_colors)]
        pygame.draw.rect(surface, led, (x + 5, uy + 4, 3, 3))
        # Vent lines
        for j in range(3):
            pygame.draw.line(surface, (40, 42, 48),
                             (x + 14 + j * 5, uy + 2), (x + 14 + j * 5, uy + 10), 1)


def draw_filing_cabinet(surface, x, y):
    """Filing cabinet."""
    body = (55, 58, 65)
    drawer = (65, 68, 75)
    pygame.draw.rect(surface, body, (x, y, 32, 56))
    pygame.draw.rect(surface, (45, 48, 55), (x, y, 32, 56), 2)
    # Drawers
    for i in range(3):
        dy = y + 4 + i * 17
        pygame.draw.rect(surface, drawer, (x + 3, dy, 26, 14))
        pygame.draw.rect(surface, (75, 78, 85), (x + 3, dy, 26, 14), 1)
        # Handle
        pygame.draw.rect(surface, (90, 95, 100), (x + 12, dy + 5, 8, 3))


def draw_chair(surface, x, y):
    """Office chair (top-down view)."""
    # Base/wheels
    pygame.draw.circle(surface, (40, 42, 48), (x + 14, y + 24), 10, 1)
    # Seat
    pygame.draw.rect(surface, (60, 50, 45), (x + 4, y + 8, 20, 20), border_radius=4)
    # Backrest
    pygame.draw.rect(surface, (70, 58, 50), (x + 6, y, 16, 10), border_radius=3)


def draw_plant(surface, x, y):
    """Potted plant."""
    # Pot
    pygame.draw.rect(surface, (120, 80, 50), (x + 6, y + 16, 16, 12))
    pygame.draw.rect(surface, (100, 65, 40), (x + 4, y + 14, 20, 4))
    # Leaves
    pygame.draw.circle(surface, (40, 100, 45), (x + 14, y + 10), 8)
    pygame.draw.circle(surface, (50, 120, 55), (x + 10, y + 6), 6)
    pygame.draw.circle(surface, (45, 110, 50), (x + 18, y + 8), 5)


def draw_whiteboard(surface, x, y, w=64, h=40):
    """Whiteboard on wall."""
    pygame.draw.rect(surface, (200, 200, 195), (x, y, w, h))
    pygame.draw.rect(surface, (120, 120, 125), (x, y, w, h), 2)
    # Some scribbles
    for i in range(4):
        lx = x + 6
        ly = y + 6 + i * 8
        lw = 20 + (i * 13) % 30
        pygame.draw.line(surface, (80, 80, 85), (lx, ly), (lx + lw, ly), 1)


def draw_door(surface, x, y, color=C_ACCENT, label="", locked=False, completed=False):
    """Interactive door with status."""
    w, h = 48, 64
    # Door frame
    pygame.draw.rect(surface, (50, 52, 58), (x - 2, y - 2, w + 4, h + 4))
    # Door body
    door_col = color if not locked else (40, 42, 48)
    pygame.draw.rect(surface, door_col, (x, y, w, h))
    pygame.draw.rect(surface, (80, 85, 95), (x, y, w, h), 2)
    # Handle
    pygame.draw.circle(surface, (180, 170, 140), (x + w - 10, y + h // 2), 4)

    if completed:
        # Checkmark
        pts = [(x + 16, y + 30), (x + 22, y + 38), (x + 34, y + 22)]
        pygame.draw.lines(surface, C_NEON, False, pts, 3)
    elif locked:
        # Lock icon
        pygame.draw.rect(surface, (100, 100, 110), (x + 18, y + 28, 12, 10))
        pygame.draw.arc(surface, (100, 100, 110), (x + 19, y + 20, 10, 14), 0, math.pi, 2)

    if label:
        font = pygame.font.SysFont("monospace", 9)
        ts = font.render(label, True, C_WHITE)
        surface.blit(ts, (x + w // 2 - ts.get_width() // 2, y + h + 4))


# ── Floor and walls ─────────────────────────────────────────────

def draw_office_floor(surface, rect=None):
    """Draw tiled office floor pattern."""
    r = rect or surface.get_rect()
    surface.fill(C_BG, r)
    tile = 48
    for x in range(r.x, r.x + r.w, tile):
        for y in range(r.y, r.y + r.h, tile):
            c = C_BG2 if ((x // tile + y // tile) % 2 == 0) else C_BG
            pygame.draw.rect(surface, c, (x, y, tile, tile))
            pygame.draw.rect(surface, C_BG3, (x, y, tile, tile), 1)


def draw_wall(surface, y, wall_h=40):
    """Draw wall section at top."""
    wall_color = (22, 24, 32)
    pygame.draw.rect(surface, wall_color, (0, 0, surface.get_width(), y + wall_h))
    # Baseboard
    pygame.draw.rect(surface, (35, 38, 48), (0, y + wall_h - 4, surface.get_width(), 4))
    pygame.draw.line(surface, C_BORDER, (0, y + wall_h), (surface.get_width(), y + wall_h), 1)


# ── Interaction indicator ───────────────────────────────────────

def draw_interact_prompt(surface, x, y, key="E"):
    """Draw 'Press E' indicator above an object."""
    font = pygame.font.SysFont("monospace", 12, bold=True)
    text = font.render(f"[{key}]", True, C_NEON)
    bg = pygame.Surface((text.get_width() + 8, text.get_height() + 4), pygame.SRCALPHA)
    bg.fill((0, 0, 0, 180))
    surface.blit(bg, (x - bg.get_width() // 2, y - bg.get_height() - 4))
    surface.blit(text, (x - text.get_width() // 2, y - text.get_height() - 2))


# ── Text rendering helpers ──────────────────────────────────────

def draw_text_box(surface, text, x, y, font, color=C_NEON, bg_alpha=200,
                  padding=8, max_width=0):
    """Render text on a solid dark background box for legibility.
    If max_width > 0, word-wraps the text."""
    lines = word_wrap(text, font, max_width) if max_width > 0 else [text]
    rendered = [font.render(line, True, color) for line in lines]
    total_h = sum(r.get_height() for r in rendered) + padding * 2
    max_w = max(r.get_width() for r in rendered) + padding * 2

    bg = pygame.Surface((max_w, total_h), pygame.SRCALPHA)
    bg.fill((0, 0, 0, bg_alpha))
    surface.blit(bg, (x, y))

    cy = y + padding
    for r in rendered:
        surface.blit(r, (x + padding, cy))
        cy += r.get_height()
    return max_w, total_h


def word_wrap(text, font, max_width):
    """Split text into lines that fit within max_width pixels."""
    if max_width <= 0:
        return [text]
    words = text.split(' ')
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        if font.size(test)[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines if lines else [text]
