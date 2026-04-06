"""All game visuals generated with pygame.draw — no external image files.
Cinematic cyberpunk rendering engine for DEADLOCK."""
import pygame
import math
import random
from game.constants import (C_BG, C_BG2, C_BG3, C_BORDER, C_TEXT_SEC,
                            C_ACCENT, C_GREEN, C_NEON, C_AMBER, C_WHITE,
                            PLAYER_SIZE, WIDTH, HEIGHT)

# ── Color palette extensions ─────────────────────────────────────
C_CYBER_BLUE = (0, 180, 255)
C_CYBER_PINK = (255, 0, 120)
C_DARK_METAL = (45, 50, 62)
C_LIGHT_METAL = (75, 82, 95)
C_CHROME = (160, 168, 185)
C_SHADOW = (0, 0, 0, 40)

# ── Particle system state ────────────────────────────────────────
_particles = []


def _glow_circle(surface, color, center, radius, alpha=60):
    """Draw a soft glow circle using layered alpha surfaces."""
    for i in range(5, 0, -1):
        r = radius + i * 3
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        a = alpha // (i + 1)
        pygame.draw.circle(s, (*color[:3], a), (r, r), r)
        surface.blit(s, (center[0] - r, center[1] - r))


def _glow_rect(surface, color, rect, alpha=40, spread=4):
    """Draw a glowing rectangle using layered alpha surfaces."""
    for i in range(3, 0, -1):
        s = pygame.Surface((rect[2] + i * spread * 2, rect[3] + i * spread * 2),
                           pygame.SRCALPHA)
        a = alpha // (i + 1)
        s.fill((*color[:3], a))
        surface.blit(s, (rect[0] - i * spread, rect[1] - i * spread))


def _neon_line(surface, color, start, end, width=1, glow=True):
    """Draw a neon-glowing line."""
    if glow:
        gs = pygame.Surface((surface.get_width(), surface.get_height()), pygame.SRCALPHA)
        for i in range(3, 0, -1):
            pygame.draw.line(gs, (*color[:3], 20 // i), start, end, width + i * 2)
        surface.blit(gs, (0, 0))
    pygame.draw.line(surface, color, start, end, width)


# ── Player character ──────────────────────────────────────────────

def draw_player(surface, x, y, direction="down", moving=False):
    """Draw a cyberpunk operative with breathing animation, glowing visor,
    tactical suit with accent lines, and directional rendering."""
    t = pygame.time.get_ticks()
    s = PLAYER_SIZE

    # Breathing bob (subtle sine wave)
    breath = math.sin(t * 0.004) * 1.5
    y_base = y + breath

    # Walking leg animation
    walk_phase = math.sin(t * 0.012) * 3 if moving else 0

    # ── Shadow (gradient ellipse) ──
    shadow_s = pygame.Surface((s + 8, 12), pygame.SRCALPHA)
    for i in range(6, 0, -1):
        a = 10 * i
        ew = s - 4 + i * 2
        eh = 4 + i
        pygame.draw.ellipse(shadow_s, (0, 0, 0, a),
                            ((s + 8 - ew) // 2, (12 - eh) // 2, ew, eh))
    surface.blit(shadow_s, (x - 4, y + s + 2))

    # ── Legs ──
    leg_color = (35, 40, 55)
    leg_highlight = (45, 52, 70)
    left_off = int(walk_phase)
    right_off = int(-walk_phase)
    # Left leg
    pygame.draw.rect(surface, leg_color,
                     (x + 6, y_base + s * 0.65 + left_off, 6, s * 0.35))
    pygame.draw.rect(surface, leg_highlight,
                     (x + 6, y_base + s * 0.65 + left_off, 2, s * 0.35))
    # Right leg
    pygame.draw.rect(surface, leg_color,
                     (x + s - 12, y_base + s * 0.65 + right_off, 6, s * 0.35))
    pygame.draw.rect(surface, leg_highlight,
                     (x + s - 12, y_base + s * 0.65 + right_off, 2, s * 0.35))
    # Boots (small bright accent)
    pygame.draw.rect(surface, (50, 58, 78),
                     (x + 5, y_base + s - 3 + left_off, 8, 3))
    pygame.draw.rect(surface, (50, 58, 78),
                     (x + s - 13, y_base + s - 3 + right_off, 8, 3))

    # ── Body (tactical suit) ──
    body_color = (40, 46, 62)
    body_dark = (30, 34, 48)
    torso_y = y_base + s * 0.28
    torso_h = int(s * 0.42)
    # Main torso
    pygame.draw.rect(surface, body_color,
                     (x + 3, torso_y, s - 6, torso_h), border_radius=2)
    # Dark center panel
    pygame.draw.rect(surface, body_dark,
                     (x + s // 2 - 3, torso_y + 2, 6, torso_h - 4))

    # Glowing accent lines on suit
    accent_alpha = int(120 + 60 * math.sin(t * 0.003))
    accent_s = pygame.Surface((s, s), pygame.SRCALPHA)
    # Chest line
    pygame.draw.line(accent_s, (*C_NEON[:3], accent_alpha),
                     (s // 2, int(s * 0.30)), (s // 2, int(s * 0.50)), 1)
    # Left arm accent
    pygame.draw.line(accent_s, (*C_NEON[:3], accent_alpha),
                     (5, int(s * 0.32)), (5, int(s * 0.55)), 1)
    # Right arm accent
    pygame.draw.line(accent_s, (*C_NEON[:3], accent_alpha),
                     (s - 6, int(s * 0.32)), (s - 6, int(s * 0.55)), 1)
    # Shoulder bars
    pygame.draw.line(accent_s, (*C_NEON[:3], accent_alpha // 2),
                     (4, int(s * 0.28)), (s - 4, int(s * 0.28)), 1)
    surface.blit(accent_s, (x, y_base))

    # ── Shoulders / arms ──
    pygame.draw.rect(surface, (50, 56, 72),
                     (x + 1, torso_y, s - 2, 5), border_radius=2)

    # ── Head ──
    head_color = (160, 140, 120)
    head_y = y_base + 1
    head_h = int(s * 0.28)
    head_w = s - 10
    head_x = x + 5

    if direction == "up":
        # Back of head - darker, no visor
        pygame.draw.rect(surface, (100, 88, 72),
                         (head_x, head_y, head_w, head_h), border_radius=3)
        # Hair / helmet back detail
        pygame.draw.rect(surface, (50, 46, 40),
                         (head_x + 1, head_y, head_w - 2, head_h // 2), border_radius=2)
    else:
        # Face
        pygame.draw.rect(surface, head_color,
                         (head_x, head_y, head_w, head_h), border_radius=3)
        # Hair / top of head
        pygame.draw.rect(surface, (60, 52, 44),
                         (head_x, head_y, head_w, 4), border_radius=2)

        # ── Cyber visor with glow ──
        visor_y = head_y + 6
        visor_color = C_NEON
        visor_glow_alpha = int(80 + 40 * math.sin(t * 0.005))

        if direction == "down":
            # Full visor band
            vx1, vx2 = head_x + 2, head_x + head_w - 2
            vy = visor_y
            # Glow behind visor
            glow_s = pygame.Surface((head_w + 8, 10), pygame.SRCALPHA)
            pygame.draw.rect(glow_s, (*visor_color[:3], visor_glow_alpha // 2),
                             (0, 0, head_w + 8, 10), border_radius=4)
            surface.blit(glow_s, (head_x - 4, vy - 2))
            # Visor band
            pygame.draw.rect(surface, (40, 44, 55),
                             (vx1, vy, vx2 - vx1, 4), border_radius=1)
            # Eyes (two bright dots)
            _glow_circle(surface, visor_color, (head_x + 5, vy + 2), 1, 50)
            _glow_circle(surface, visor_color, (head_x + head_w - 6, vy + 2), 1, 50)
            pygame.draw.rect(surface, visor_color, (head_x + 4, vy + 1, 3, 2))
            pygame.draw.rect(surface, visor_color, (head_x + head_w - 7, vy + 1, 3, 2))

        elif direction == "left":
            # Side visor - left facing
            glow_s = pygame.Surface((8, 8), pygame.SRCALPHA)
            pygame.draw.rect(glow_s, (*visor_color[:3], visor_glow_alpha), (0, 0, 8, 8),
                             border_radius=3)
            surface.blit(glow_s, (head_x - 2, visor_y - 1))
            pygame.draw.rect(surface, (40, 44, 55),
                             (head_x + 1, visor_y, head_w - 4, 4), border_radius=1)
            pygame.draw.rect(surface, visor_color, (head_x + 1, visor_y + 1, 3, 2))

        elif direction == "right":
            # Side visor - right facing
            glow_s = pygame.Surface((8, 8), pygame.SRCALPHA)
            pygame.draw.rect(glow_s, (*visor_color[:3], visor_glow_alpha), (0, 0, 8, 8),
                             border_radius=3)
            surface.blit(glow_s, (head_x + head_w - 6, visor_y - 1))
            pygame.draw.rect(surface, (40, 44, 55),
                             (head_x + 3, visor_y, head_w - 4, 4), border_radius=1)
            pygame.draw.rect(surface, visor_color,
                             (head_x + head_w - 5, visor_y + 1, 3, 2))


# ── Office furniture (cyber/high-tech) ──────────────────────────

def draw_desk(surface, x, y, w=96, h=48):
    """Sleek metallic desk with edge lighting and glass top reflection."""
    t = pygame.time.get_ticks()

    # Legs (chrome cylinders)
    for lx in (x + 6, x + w - 10):
        pygame.draw.rect(surface, C_CHROME, (lx, y + h, 4, 14))
        pygame.draw.rect(surface, (180, 185, 200), (lx, y + h, 1, 14))

    # Main surface - dark metallic
    pygame.draw.rect(surface, C_DARK_METAL, (x, y, w, h), border_radius=2)
    # Top face lighter
    pygame.draw.rect(surface, C_LIGHT_METAL, (x + 1, y + 1, w - 2, h - 8), border_radius=2)

    # Glass top reflection (subtle diagonal shine)
    glass = pygame.Surface((w, h), pygame.SRCALPHA)
    for i in range(0, w, 12):
        a = 15 + int(8 * math.sin((t * 0.001 + i) * 0.3))
        pygame.draw.line(glass, (200, 220, 255, a), (i, 0), (i + 20, h), 1)
    surface.blit(glass, (x, y))

    # Edge neon lighting (thin lines)
    pulse = int(150 + 60 * math.sin(t * 0.003))
    edge_col = (*C_CYBER_BLUE[:3], pulse)
    edge_s = pygame.Surface((w + 4, h + 4), pygame.SRCALPHA)
    pygame.draw.rect(edge_s, edge_col, (0, 0, w + 4, h + 4), 1, border_radius=2)
    surface.blit(edge_s, (x - 2, y - 2))

    # Thin accent line on front edge
    _neon_line(surface, (*C_CYBER_BLUE[:3],), (x + 4, y + h - 2), (x + w - 4, y + h - 2), 1)

    # Drawer line (subtle)
    pygame.draw.line(surface, (70, 75, 88), (x + 12, y + h // 2), (x + w - 12, y + h // 2), 1)
    # Drawer handle (small neon dot)
    pygame.draw.rect(surface, C_CYBER_BLUE, (x + w // 2 - 4, y + h // 2 - 1, 8, 2))


def draw_monitor(surface, x, y, text="", text_color=C_NEON):
    """Holographic-style monitor with animated screen glow and scrolling terminal."""
    t = pygame.time.get_ticks()

    # Stand (chrome)
    pygame.draw.rect(surface, C_CHROME, (x + 15, y + 32, 10, 8))
    pygame.draw.rect(surface, (180, 185, 200), (x + 15, y + 32, 3, 8))
    # Base plate
    pygame.draw.rect(surface, C_LIGHT_METAL, (x + 6, y + 38, 28, 4), border_radius=1)
    _neon_line(surface, C_CYBER_BLUE, (x + 8, y + 39), (x + 32, y + 39), 1, glow=False)

    # Screen frame (dark with thin neon border)
    pygame.draw.rect(surface, (40, 44, 55), (x - 1, y - 1, 42, 34), border_radius=2)
    # Screen bezel glow
    pulse = int(40 + 20 * math.sin(t * 0.004))
    bezel_s = pygame.Surface((44, 36), pygame.SRCALPHA)
    pygame.draw.rect(bezel_s, (*C_CYBER_BLUE[:3], pulse), (0, 0, 44, 36), 1, border_radius=2)
    surface.blit(bezel_s, (x - 2, y - 2))

    # Screen background
    pygame.draw.rect(surface, (5, 8, 15), (x + 2, y + 2, 36, 28))

    # Screen content
    if text:
        font = pygame.font.SysFont("monospace", 8)
        ts = font.render(text, True, text_color)
        surface.blit(ts, (x + 4, y + 10))
    else:
        # Animated scrolling terminal lines
        scroll = (t // 200) % 6
        for i in range(4):
            row = (i + scroll) % 8
            lw = 8 + (row * 11) % 20
            ly = y + 5 + i * 6
            # Line with slight color variation
            c_val = 40 + (row * 17) % 60
            pygame.draw.rect(surface, (0, c_val, 0), (x + 4, ly, lw, 2))

    # Screen reflection (corner highlight)
    ref_s = pygame.Surface((14, 8), pygame.SRCALPHA)
    pygame.draw.rect(ref_s, (100, 140, 200, 15), (0, 0, 14, 8), border_radius=2)
    surface.blit(ref_s, (x + 3, y + 3))

    # Screen glow halo
    glow_alpha = int(25 + 15 * math.sin(t * 0.003))
    glow_s = pygame.Surface((50, 42), pygame.SRCALPHA)
    pygame.draw.rect(glow_s, (*C_CYBER_BLUE[:3], glow_alpha), (0, 0, 50, 42), border_radius=6)
    surface.blit(glow_s, (x - 5, y - 5))


def draw_server_rack(surface, x, y, h=80):
    """Server rack with blinking LEDs, data flow animation, and vent grills."""
    t = pygame.time.get_ticks()
    led_colors = [C_GREEN, C_NEON, C_CYBER_BLUE, C_AMBER, (200, 50, 50)]

    # Main body
    pygame.draw.rect(surface, (42, 48, 58), (x, y, 32, h), border_radius=1)
    # Side panel highlight
    pygame.draw.rect(surface, (28, 32, 40), (x, y, 3, h))

    # Top and bottom chrome trim
    pygame.draw.rect(surface, C_LIGHT_METAL, (x, y, 32, 3))
    pygame.draw.rect(surface, C_LIGHT_METAL, (x, y + h - 3, 32, 3))

    # Rack units
    num_units = h // 16
    for i in range(num_units):
        uy = y + 5 + i * 16

        # Unit background
        pygame.draw.rect(surface, (36, 40, 50), (x + 3, uy, 26, 12), border_radius=1)
        pygame.draw.rect(surface, (38, 42, 52), (x + 3, uy, 26, 12), 1, border_radius=1)

        # Blinking LED (phase offset per unit)
        led_phase = math.sin(t * 0.005 + i * 1.7)
        led_on = led_phase > -0.3
        led_col = led_colors[i % len(led_colors)]
        if led_on:
            # LED with glow halo
            led_x, led_y = x + 6, uy + 5
            _glow_circle(surface, led_col, (led_x, led_y), 1, 40)
            pygame.draw.rect(surface, led_col, (led_x - 1, led_y - 1, 3, 3))
        else:
            pygame.draw.rect(surface, (30, 32, 38), (x + 5, uy + 4, 3, 3))

        # Secondary LED
        led2_phase = math.sin(t * 0.003 + i * 2.3)
        if led2_phase > 0:
            pygame.draw.rect(surface, C_AMBER, (x + 10, uy + 5, 2, 2))

        # Ventilation grill pattern
        for j in range(3):
            vx = x + 16 + j * 4
            pygame.draw.line(surface, (32, 36, 44), (vx, uy + 2), (vx, uy + 10), 1)

    # Data flow animation (moving dots going upward)
    flow_s = pygame.Surface((32, h), pygame.SRCALPHA)
    for i in range(5):
        dot_y = (h - ((t // 30 + i * 17) % h)) % h
        dot_x = 22 + (i * 3) % 8
        dot_alpha = int(120 + 60 * math.sin(t * 0.008 + i))
        pygame.draw.circle(flow_s, (*C_NEON[:3], dot_alpha), (dot_x, dot_y), 1)
    surface.blit(flow_s, (x, y))

    # Outer neon trim (subtle)
    trim_s = pygame.Surface((36, h + 4), pygame.SRCALPHA)
    trim_alpha = int(30 + 15 * math.sin(t * 0.002))
    pygame.draw.rect(trim_s, (*C_NEON[:3], trim_alpha), (0, 0, 36, h + 4), 1, border_radius=2)
    surface.blit(trim_s, (x - 2, y - 2))


def draw_filing_cabinet(surface, x, y):
    """Metallic filing cabinet with electronic lock indicators."""
    t = pygame.time.get_ticks()

    # Body
    pygame.draw.rect(surface, (42, 46, 56), (x, y, 32, 56), border_radius=1)
    # Side highlight
    pygame.draw.rect(surface, (52, 56, 68), (x, y, 3, 56))
    # Top cap
    pygame.draw.rect(surface, C_LIGHT_METAL, (x, y, 32, 2))

    # Drawers
    for i in range(3):
        dy = y + 5 + i * 17
        # Drawer face
        pygame.draw.rect(surface, (50, 54, 66), (x + 3, dy, 26, 14), border_radius=1)
        pygame.draw.rect(surface, (62, 68, 80), (x + 3, dy, 26, 14), 1, border_radius=1)
        # Handle (chrome bar)
        pygame.draw.rect(surface, C_CHROME, (x + 10, dy + 5, 12, 3), border_radius=1)
        pygame.draw.rect(surface, (180, 185, 200), (x + 10, dy + 5, 12, 1))

        # Electronic lock LED
        led_phase = math.sin(t * 0.002 + i * 2.1)
        led_col = C_GREEN if led_phase > 0 else (180, 40, 40)
        pygame.draw.rect(surface, led_col, (x + 25, dy + 2, 2, 2))

    # Outer border
    pygame.draw.rect(surface, (35, 38, 48), (x, y, 32, 56), 1, border_radius=1)


def draw_chair(surface, x, y):
    """Modern ergonomic chair with chrome accents (top-down view)."""
    # Wheel base (chrome circle)
    pygame.draw.circle(surface, (45, 48, 56), (x + 14, y + 22), 11, 1)
    # Chrome spokes
    for angle in range(0, 360, 72):
        rad = math.radians(angle)
        ex = x + 14 + int(math.cos(rad) * 10)
        ey = y + 22 + int(math.sin(rad) * 10)
        pygame.draw.line(surface, (60, 65, 75), (x + 14, y + 22), (ex, ey), 1)
        # Wheel dots
        pygame.draw.circle(surface, (80, 85, 95), (ex, ey), 2)

    # Seat (dark mesh texture)
    pygame.draw.rect(surface, (50, 45, 42), (x + 4, y + 10, 20, 18), border_radius=4)
    # Mesh pattern
    for i in range(3):
        pygame.draw.line(surface, (58, 53, 50),
                         (x + 6, y + 13 + i * 5), (x + 22, y + 13 + i * 5), 1)

    # Backrest
    pygame.draw.rect(surface, (55, 50, 48), (x + 5, y + 1, 18, 10), border_radius=3)
    pygame.draw.rect(surface, (65, 60, 56), (x + 5, y + 1, 18, 10), 1, border_radius=3)
    # Chrome accent on backrest
    pygame.draw.line(surface, C_CHROME, (x + 8, y + 2), (x + 20, y + 2), 1)

    # Armrests (chrome)
    pygame.draw.rect(surface, C_CHROME, (x + 2, y + 12, 3, 10), border_radius=1)
    pygame.draw.rect(surface, C_CHROME, (x + 23, y + 12, 3, 10), border_radius=1)


def draw_plant(surface, x, y):
    """Bioluminescent potted plant with subtle green pulse."""
    t = pygame.time.get_ticks()
    bio_pulse = int(30 + 20 * math.sin(t * 0.003))

    # Pot (sleek dark container)
    pygame.draw.rect(surface, (60, 50, 42), (x + 5, y + 17, 18, 11), border_radius=2)
    pygame.draw.rect(surface, (80, 65, 50), (x + 3, y + 15, 22, 3), border_radius=1)
    # Neon ring on pot rim
    pot_glow = pygame.Surface((24, 5), pygame.SRCALPHA)
    pygame.draw.rect(pot_glow, (*C_NEON[:3], bio_pulse // 2), (0, 0, 24, 5), border_radius=1)
    surface.blit(pot_glow, (x + 2, y + 14))

    # Leaves with bioluminescent glow
    leaf_centers = [(x + 14, y + 10), (x + 9, y + 6), (x + 19, y + 8),
                    (x + 12, y + 3), (x + 17, y + 4)]
    leaf_sizes = [8, 6, 5, 5, 4]

    for (cx, cy), sz in zip(leaf_centers, leaf_sizes):
        # Glow behind leaf
        glow_s = pygame.Surface((sz * 3, sz * 3), pygame.SRCALPHA)
        pygame.draw.circle(glow_s, (*C_NEON[:3], bio_pulse),
                           (sz * 3 // 2, sz * 3 // 2), sz + 2)
        surface.blit(glow_s, (cx - sz * 3 // 2, cy - sz * 3 // 2))
        # Leaf body
        pygame.draw.circle(surface, (35, 100, 45), (cx, cy), sz)
        pygame.draw.circle(surface, (50, 130, 60), (cx, cy), sz - 2)


def draw_whiteboard(surface, x, y, w=64, h=40):
    """Interactive digital whiteboard with holographic display."""
    t = pygame.time.get_ticks()

    # Frame (dark metal)
    pygame.draw.rect(surface, C_DARK_METAL, (x - 2, y - 2, w + 4, h + 4), border_radius=2)

    # Screen
    pygame.draw.rect(surface, (40, 48, 60), (x, y, w, h))

    # Scan lines on the whiteboard
    scan_s = pygame.Surface((w, h), pygame.SRCALPHA)
    for sy in range(0, h, 3):
        pygame.draw.line(scan_s, (100, 120, 160, 8), (0, sy), (w, sy), 1)
    surface.blit(scan_s, (x, y))

    # Animated text lines (holographic)
    for i in range(5):
        lx = x + 5
        ly = y + 5 + i * 7
        lw = 15 + ((i * 17 + t // 2000) % 35)
        line_alpha = int(60 + 30 * math.sin(t * 0.002 + i))
        line_s = pygame.Surface((lw, 2), pygame.SRCALPHA)
        line_s.fill((*C_CYBER_BLUE[:3], line_alpha))
        surface.blit(line_s, (lx, ly))

    # Border glow
    frame_s = pygame.Surface((w + 8, h + 8), pygame.SRCALPHA)
    pulse_a = int(25 + 15 * math.sin(t * 0.003))
    pygame.draw.rect(frame_s, (*C_CYBER_BLUE[:3], pulse_a),
                     (0, 0, w + 8, h + 8), 1, border_radius=3)
    surface.blit(frame_s, (x - 4, y - 4))


def draw_door(surface, x, y, color=C_ACCENT, label="", locked=False, completed=False):
    """Electronic sliding door with scanning line, keypad, and status indicators."""
    t = pygame.time.get_ticks()
    w, h = 48, 64

    # Door frame (metallic)
    pygame.draw.rect(surface, C_LIGHT_METAL, (x - 3, y - 3, w + 6, h + 6), border_radius=1)
    pygame.draw.rect(surface, C_DARK_METAL, (x - 2, y - 2, w + 4, h + 4))

    # Door body
    if locked:
        door_col = (35, 30, 30)
    elif completed:
        door_col = (25, 45, 30)
    else:
        door_col = (38, 48, 62)
    pygame.draw.rect(surface, door_col, (x, y, w, h))

    # Center split line (sliding door)
    pygame.draw.line(surface, (55, 60, 72), (x + w // 2, y + 2), (x + w // 2, y + h - 2), 1)

    # Panel details
    pygame.draw.rect(surface, (door_col[0] + 8, door_col[1] + 8, door_col[2] + 8),
                     (x + 3, y + 3, w // 2 - 5, h - 6), 1)
    pygame.draw.rect(surface, (door_col[0] + 8, door_col[1] + 8, door_col[2] + 8),
                     (x + w // 2 + 2, y + 3, w // 2 - 5, h - 6), 1)

    # Scanning line animation (horizontal line sweeping down)
    scan_y = y + (t // 20 % h)
    scan_s = pygame.Surface((w, 3), pygame.SRCALPHA)
    scan_col = C_NEON if not locked else (200, 50, 50)
    scan_s.fill((*scan_col[:3], 80))
    surface.blit(scan_s, (x, scan_y))

    # Keypad (right side of frame)
    kx, ky = x + w - 10, y + h // 2 - 8
    pygame.draw.rect(surface, (25, 28, 35), (kx, ky, 8, 16), border_radius=1)
    # Keypad dots
    for row in range(3):
        for col in range(2):
            pygame.draw.rect(surface, (50, 55, 65),
                             (kx + 1 + col * 3, ky + 2 + row * 4, 2, 2))

    # Status LED on keypad
    if completed:
        led_col = C_NEON
    elif locked:
        led_col = (200, 50, 50)
    else:
        led_col = C_CYBER_BLUE
    _glow_circle(surface, led_col, (kx + 4, ky - 3), 2, 50)
    pygame.draw.circle(surface, led_col, (kx + 4, ky - 3), 2)

    # Danger tape for locked doors
    if locked:
        tape_s = pygame.Surface((w, h), pygame.SRCALPHA)
        for i in range(0, w + h, 12):
            pygame.draw.line(tape_s, (200, 180, 0, 40),
                             (i, 0), (i - h, h), 2)
        surface.blit(tape_s, (x, y))

    if completed:
        # Glowing checkmark
        pts = [(x + 16, y + 30), (x + 22, y + 38), (x + 34, y + 22)]
        check_s = pygame.Surface((w, h), pygame.SRCALPHA)
        for i in range(3, 0, -1):
            pygame.draw.lines(check_s, (*C_NEON[:3], 30 * i), False,
                              [(p[0] - x, p[1] - y) for p in pts], 2 + i * 2)
        surface.blit(check_s, (x, y))
        pygame.draw.lines(surface, C_NEON, False, pts, 2)

    elif locked:
        # Lock icon with glow
        lock_x, lock_y = x + w // 2 - 6, y + h // 2 - 8
        pygame.draw.rect(surface, (130, 60, 60), (lock_x, lock_y + 6, 12, 10), border_radius=1)
        pygame.draw.arc(surface, (130, 60, 60),
                        (lock_x + 1, lock_y - 2, 10, 14), 0, math.pi, 2)
        _glow_circle(surface, (200, 50, 50), (x + w // 2, y + h // 2), 6, 30)

    # Door frame neon accent
    accent_col = C_NEON if completed else (C_CYBER_BLUE if not locked else (200, 50, 50))
    accent_alpha = int(60 + 30 * math.sin(t * 0.003))
    frame_glow = pygame.Surface((w + 8, h + 8), pygame.SRCALPHA)
    pygame.draw.rect(frame_glow, (*accent_col[:3], accent_alpha),
                     (0, 0, w + 8, h + 8), 1, border_radius=2)
    surface.blit(frame_glow, (x - 4, y - 4))

    if label:
        font = pygame.font.SysFont("monospace", 9)
        # Neon label
        draw_neon_text(surface, label,
                       x + w // 2 - font.size(label)[0] // 2, y + h + 5,
                       font, color=accent_col, glow_radius=2)


# ── Floor and walls ──────────────────────────────────────────────

def draw_office_floor(surface, rect=None):
    """Industrial metal plate floor with hex grid pattern and subtle reflections."""
    r = rect or surface.get_rect()
    surface.fill(C_BG, r)
    tile = 48

    for tx in range(r.x, r.x + r.w, tile):
        for ty in range(r.y, r.y + r.h, tile):
            # Alternating tiles
            idx = (tx // tile + ty // tile)
            c = C_BG2 if (idx % 2 == 0) else C_BG
            pygame.draw.rect(surface, c, (tx, ty, tile, tile))

            # Subtle grid lines
            pygame.draw.rect(surface, C_BG3, (tx, ty, tile, tile), 1)

            # Metal plate rivets (corners of each tile)
            rivet_col = (42, 46, 56)
            for rx, ry in [(tx + 3, ty + 3), (tx + tile - 4, ty + 3),
                           (tx + 3, ty + tile - 4), (tx + tile - 4, ty + tile - 4)]:
                if r.x <= rx < r.x + r.w and r.y <= ry < r.y + r.h:
                    pygame.draw.circle(surface, rivet_col, (rx, ry), 1)

    # Hex pattern overlay (very subtle)
    hex_s = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
    hex_size = 24
    for hx in range(0, r.w, int(hex_size * 1.5)):
        for hy in range(0, r.h, int(hex_size * 0.866)):
            offset = hex_size * 0.75 if (hy // int(hex_size * 0.866)) % 2 else 0
            cx = int(hx + offset)
            cy = hy
            pts = []
            for a in range(6):
                angle = math.radians(60 * a + 30)
                pts.append((cx + int(hex_size * 0.4 * math.cos(angle)),
                            cy + int(hex_size * 0.4 * math.sin(angle))))
            if len(pts) >= 3:
                pygame.draw.polygon(hex_s, (C_BG3[0], C_BG3[1], C_BG3[2], 20), pts, 1)
    surface.blit(hex_s, (r.x, r.y))


def draw_wall(surface, y_pos, wall_h=40):
    """Wall section with conduits, emergency lighting, and panel rivets."""
    t = pygame.time.get_ticks()
    sw = surface.get_width()

    # Main wall
    wall_color = (18, 20, 28)
    pygame.draw.rect(surface, wall_color, (0, 0, sw, y_pos + wall_h))

    # Panel sections (subtle variation)
    panel_w = 120
    for px in range(0, sw, panel_w):
        pygame.draw.rect(surface, (42, 46, 56),
                         (px, 4, panel_w - 2, y_pos + wall_h - 8), 1)
        # Rivets at panel corners
        for rx, ry in [(px + 4, 6), (px + panel_w - 6, 6),
                       (px + 4, y_pos + wall_h - 6), (px + panel_w - 6, y_pos + wall_h - 6)]:
            pygame.draw.circle(surface, (28, 30, 38), (rx, ry), 1)

    # Conduit / cable channel (horizontal pipe near top)
    conduit_y = 8
    pygame.draw.rect(surface, (25, 28, 36), (0, conduit_y, sw, 6))
    pygame.draw.line(surface, (32, 36, 44), (0, conduit_y), (sw, conduit_y), 1)
    pygame.draw.line(surface, (32, 36, 44), (0, conduit_y + 6), (sw, conduit_y + 6), 1)
    # Conduit brackets
    for bx in range(30, sw, 100):
        pygame.draw.rect(surface, (35, 38, 48), (bx, conduit_y - 2, 8, 10))

    # Emergency lighting strips (pulsing along the baseboard)
    baseboard_y = y_pos + wall_h - 4
    pygame.draw.rect(surface, (30, 34, 45), (0, baseboard_y, sw, 4))

    # Animated emergency light strip
    strip_s = pygame.Surface((sw, 2), pygame.SRCALPHA)
    for sx in range(0, sw, 60):
        pulse_a = int(40 + 25 * math.sin(t * 0.002 + sx * 0.02))
        seg_w = 30
        pygame.draw.line(strip_s, (*C_NEON[:3], pulse_a),
                         (sx, 0), (sx + seg_w, 0), 1)
    surface.blit(strip_s, (0, baseboard_y + 1))

    # Baseboard border
    pygame.draw.line(surface, C_BORDER, (0, y_pos + wall_h), (sw, y_pos + wall_h), 1)


# ── Visual effects functions ─────────────────────────────────────

def draw_scanlines(surface, alpha=15, spacing=3):
    """CRT scanline overlay for the entire screen."""
    scan = pygame.Surface((surface.get_width(), surface.get_height()), pygame.SRCALPHA)
    for sy in range(0, surface.get_height(), spacing):
        pygame.draw.line(scan, (0, 0, 0, alpha), (0, sy),
                         (surface.get_width(), sy), 1)
    surface.blit(scan, (0, 0))


def draw_vignette(surface, intensity=25):
    """Subtle darkened corners/edges cinematic vignette effect."""
    w, h = surface.get_size()
    vig = pygame.Surface((w, h), pygame.SRCALPHA)

    # Top and bottom bands - very subtle
    for i in range(40):
        a = int(intensity * (1 - i / 40))
        pygame.draw.line(vig, (0, 0, 0, a), (0, i), (w, i), 1)
        pygame.draw.line(vig, (0, 0, 0, a), (0, h - 1 - i), (w, h - 1 - i), 1)

    # Left and right bands - very subtle
    for i in range(50):
        a = int(intensity * 0.5 * (1 - i / 50))
        pygame.draw.line(vig, (0, 0, 0, a), (i, 0), (i, h), 1)
        pygame.draw.line(vig, (0, 0, 0, a), (w - 1 - i, 0), (w - 1 - i, h), 1)

    surface.blit(vig, (0, 0))


def draw_glitch_line(surface, y_pos=None, width=None):
    """Random horizontal glitch distortion line."""
    w, h = surface.get_size()
    if y_pos is None:
        y_pos = random.randint(0, h - 1)
    if width is None:
        width = random.randint(1, 4)

    # Grab a horizontal strip and shift it
    strip_w = random.randint(40, 200)
    strip_x = random.randint(0, w - strip_w)
    shift = random.randint(-8, 8)

    # Draw colored glitch lines
    glitch_s = pygame.Surface((strip_w, width), pygame.SRCALPHA)
    r_shift = random.choice([C_NEON, C_CYBER_PINK, C_CYBER_BLUE])
    glitch_s.fill((*r_shift[:3], random.randint(30, 80)))
    surface.blit(glitch_s, (strip_x + shift, y_pos))


def draw_particles(surface, particles, dt):
    """Floating dust/data particles in the air.
    particles is a list of dicts: {x, y, vx, vy, life, max_life, color, size}
    Modifies particles in-place; removes dead particles."""
    t = pygame.time.get_ticks()
    to_remove = []
    part_s = pygame.Surface((surface.get_width(), surface.get_height()), pygame.SRCALPHA)

    for i, p in enumerate(particles):
        p["x"] += p.get("vx", 0) * dt
        p["y"] += p.get("vy", -10) * dt
        p["life"] -= dt

        if p["life"] <= 0:
            to_remove.append(i)
            continue

        ratio = p["life"] / p.get("max_life", 1)
        alpha = int(120 * ratio)
        color = p.get("color", C_NEON)
        size = p.get("size", 1)

        # Subtle float oscillation
        ox = math.sin(t * 0.003 + p["x"]) * 0.5

        px = int(p["x"] + ox)
        py = int(p["y"])

        if size <= 1:
            pygame.draw.circle(part_s, (*color[:3], alpha), (px, py), 1)
        else:
            pygame.draw.circle(part_s, (*color[:3], alpha), (px, py), size)
            pygame.draw.circle(part_s, (*color[:3], alpha // 3), (px, py), size + 1)

    surface.blit(part_s, (0, 0))

    for i in reversed(to_remove):
        particles.pop(i)


def draw_neon_text(surface, text, x, y, font, color=C_NEON, glow_radius=3):
    """Text with neon glow effect - renders blurred glow behind crisp text."""
    ts = font.render(text, True, color)
    tw, th = ts.get_size()

    # Glow layers behind text
    glow_s = pygame.Surface((tw + glow_radius * 4, th + glow_radius * 4), pygame.SRCALPHA)
    for i in range(glow_radius, 0, -1):
        a = 40 // (i + 1)
        glow_text = font.render(text, True, (*color[:3],))
        glow_layer = pygame.Surface((tw, th), pygame.SRCALPHA)
        glow_layer.blit(glow_text, (0, 0))
        glow_layer.set_alpha(a)
        # Blit at slight offsets to simulate blur
        for dx in range(-i, i + 1):
            for dy in range(-i, i + 1):
                if dx * dx + dy * dy <= i * i:
                    glow_s.blit(glow_layer, (glow_radius * 2 + dx, glow_radius * 2 + dy))

    surface.blit(glow_s, (x - glow_radius * 2, y - glow_radius * 2))

    # Crisp text on top
    surface.blit(ts, (x, y))


def draw_screen_noise(surface, rect, intensity=30):
    """Static noise effect for monitors/screens."""
    noise_s = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
    for _ in range(rect[2] * rect[3] // 8):
        nx = random.randint(0, rect[2] - 1)
        ny = random.randint(0, rect[3] - 1)
        a = random.randint(0, intensity)
        noise_s.set_at((nx, ny), (200, 220, 255, a))
    surface.blit(noise_s, (rect[0], rect[1]))


def draw_pulse_ring(surface, cx, cy, radius, color, t):
    """Expanding ring pulse effect (for interactions)."""
    ring_s = pygame.Surface((radius * 2 + 20, radius * 2 + 20), pygame.SRCALPHA)
    center = (radius + 10, radius + 10)

    # Multiple expanding rings
    for i in range(3):
        phase = (t * 0.002 + i * 2.1) % (math.pi * 2)
        r = int(radius * (0.5 + 0.5 * math.sin(phase)))
        a = int(80 * (1 - r / (radius + 1)))
        if r > 0 and a > 0:
            pygame.draw.circle(ring_s, (*color[:3], a), center, r, 1)

    surface.blit(ring_s, (cx - radius - 10, cy - radius - 10))


def draw_data_stream(surface, x, y1, y2, t, color=C_NEON):
    """Vertical data stream effect (Matrix-style falling characters)."""
    stream_s = pygame.Surface((12, abs(y2 - y1)), pygame.SRCALPHA)
    stream_h = abs(y2 - y1)
    chars = "01"
    font = pygame.font.SysFont("monospace", 8)

    for i in range(stream_h // 10):
        char_y = (t // 50 + i * 10) % stream_h
        char = chars[(t // 100 + i) % len(chars)]
        a = int(160 * (1 - char_y / stream_h))
        char_s = font.render(char, True, (*color[:3],))
        char_s.set_alpha(a)
        stream_s.blit(char_s, (2, char_y))

    surface.blit(stream_s, (x, min(y1, y2)))


# ── Interaction indicator ────────────────────────────────────────

def draw_interact_prompt(surface, x, y, key="E"):
    """Animated bouncing arrow + glowing [E] key with pulse ring."""
    t = pygame.time.get_ticks()
    font = pygame.font.SysFont("monospace", 12, bold=True)

    # Bouncing offset
    bounce = math.sin(t * 0.006) * 4

    # Pulse ring around interactable area
    draw_pulse_ring(surface, x, y + 10, 20, C_NEON, t)

    # Arrow (small downward pointing triangle)
    arrow_y = y - 28 + bounce
    arrow_pts = [(x - 4, int(arrow_y)), (x + 4, int(arrow_y)),
                 (x, int(arrow_y + 6))]
    arrow_s = pygame.Surface((20, 20), pygame.SRCALPHA)
    local_pts = [(10 - 4, 2), (10 + 4, 2), (10, 8)]
    pygame.draw.polygon(arrow_s, (*C_NEON[:3], 180), local_pts)
    surface.blit(arrow_s, (x - 10, int(arrow_y) - 2))

    # Key badge background with glow
    text = font.render(f"[{key}]", True, C_NEON)
    tw, th = text.get_size()
    badge_w = tw + 12
    badge_h = th + 6

    bx = x - badge_w // 2
    by = int(y - 42 + bounce)

    # Glow behind badge
    pulse_alpha = int(60 + 30 * math.sin(t * 0.005))
    glow = pygame.Surface((badge_w + 8, badge_h + 8), pygame.SRCALPHA)
    glow.fill((*C_NEON[:3], pulse_alpha // 3))
    surface.blit(glow, (bx - 4, by - 4))

    # Badge
    badge = pygame.Surface((badge_w, badge_h), pygame.SRCALPHA)
    badge.fill((0, 0, 0, 200))
    pygame.draw.rect(badge, (*C_NEON[:3], 120), (0, 0, badge_w, badge_h), 1, border_radius=3)
    surface.blit(badge, (bx, by))

    # Text
    surface.blit(text, (bx + 6, by + 3))


# ── Text rendering helpers ───────────────────────────────────────

def draw_text_box(surface, text, x, y, font, color=C_NEON, bg_alpha=200,
                  padding=8, max_width=0):
    """Glassmorphism text box with animated border and corner accents."""
    t = pygame.time.get_ticks()
    lines = word_wrap(text, font, max_width) if max_width > 0 else [text]
    rendered = [font.render(line, True, color) for line in lines]
    total_h = sum(r.get_height() for r in rendered) + padding * 2
    max_w = max(r.get_width() for r in rendered) + padding * 2

    # Glass background
    bg = pygame.Surface((max_w, total_h), pygame.SRCALPHA)
    bg.fill((8, 10, 18, bg_alpha))

    # Subtle inner gradient (lighter at top)
    grad = pygame.Surface((max_w, total_h // 3), pygame.SRCALPHA)
    grad.fill((40, 50, 70, 20))
    bg.blit(grad, (0, 0))

    surface.blit(bg, (x, y))

    # Animated border (color cycling pulse)
    pulse = int(80 + 40 * math.sin(t * 0.003))
    border_col = (*color[:3], pulse)
    border_s = pygame.Surface((max_w + 2, total_h + 2), pygame.SRCALPHA)
    pygame.draw.rect(border_s, border_col, (0, 0, max_w + 2, total_h + 2), 1, border_radius=2)
    surface.blit(border_s, (x - 1, y - 1))

    # Corner accents (decorative L-shapes)
    accent_len = min(10, max_w // 4)
    corners = [
        (x, y, 1, 1),                                      # top-left
        (x + max_w - 1, y, -1, 1),                         # top-right
        (x, y + total_h - 1, 1, -1),                       # bottom-left
        (x + max_w - 1, y + total_h - 1, -1, -1),          # bottom-right
    ]
    for cx, cy, dx, dy in corners:
        pygame.draw.line(surface, color, (cx, cy), (cx + dx * accent_len, cy), 1)
        pygame.draw.line(surface, color, (cx, cy), (cx, cy + dy * accent_len), 1)

    # Text
    cy_pos = y + padding
    for r in rendered:
        surface.blit(r, (x + padding, cy_pos))
        cy_pos += r.get_height()

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
