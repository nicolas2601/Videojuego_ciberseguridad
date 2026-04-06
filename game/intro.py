import pygame
import random
import math
from game.constants import (WIDTH, HEIGHT, C_BG, C_BG2, C_BORDER, C_TEXT_PRI, C_TEXT_SEC,
    C_TEXT_HINT, C_ACCENT, C_RED, C_GREEN, C_NEON, C_WHITE, C_PANEL, C_AMBER,
    DIFFICULTY_DUMMY, DIFFICULTY_MID, DIFFICULTY_SENIOR, DIFFICULTY_NOOB,
    DIFFICULTY_NAMES, DIFFICULTY_DESC)
from game.ui.draw_assets import (draw_desk, draw_monitor, draw_chair, draw_plant,
    draw_filing_cabinet, draw_office_floor, draw_wall, draw_text_box)


# ── Constants ──────────────────────────────────────────────────────
_PHASE_MAIN = 0
_PHASE_DIFFICULTY = 1

_DIFF_COLORS = {
    DIFFICULTY_DUMMY:  (74, 255, 120),
    DIFFICULTY_MID:    (74, 200, 255),
    DIFFICULTY_SENIOR: (255, 200, 74),
    DIFFICULTY_NOOB:   (255, 74, 74),
}

_TITLE_TEXT = "DEADLOCK"
_SUBTITLE_TEXT = "OPERACION DESCIFRADO \u2014 2031"
_GLITCH_CHARS = "!@#$%^&*01<>{}|/\\~`"
_MATRIX_CHARS = "01ABCDEF:.;/\\|{}[]<>~`!@#$%"

_CYAN = (0, 255, 220)
_NEON_GREEN = (57, 255, 20)
_DARK_CYAN = (0, 80, 70)
_DARK_GREEN = (0, 40, 10)


# ── Inline VFX helpers (scanlines, vignette, neon text) ────────────

def _build_vignette_surface(w, h):
    """Subtle vignette - just a light darkening at the very edges."""
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    # Only darken the outermost 30px on each edge, very subtly
    for i in range(30):
        a = int(20 * (1 - i / 30))
        if a <= 0:
            continue
        pygame.draw.line(surf, (0, 0, 0, a), (0, i), (w, i), 1)
        pygame.draw.line(surf, (0, 0, 0, a), (0, h - 1 - i), (w, h - 1 - i), 1)
        pygame.draw.line(surf, (0, 0, 0, a), (i, 0), (i, h), 1)
        pygame.draw.line(surf, (0, 0, 0, a), (w - 1 - i, 0), (w - 1 - i, h), 1)
    return surf


def _build_scanline_texture(w, h):
    """CRT scanlines texture, double height for scrolling."""
    total_h = h * 2
    surf = pygame.Surface((w, total_h), pygame.SRCALPHA)
    for y in range(0, total_h, 2):
        alpha = 12 if y % 4 == 0 else 6
        pygame.draw.line(surf, (0, 0, 0, alpha), (0, y), (w, y), 1)
    return surf, total_h


def _draw_neon_text(surface, text, font, x, y, color, glow_radius=6, alpha_base=60):
    """Render text with layered neon glow effect."""
    base = font.render(text, True, color)
    bw, bh = base.get_size()
    glow_surf = pygame.Surface((bw + glow_radius * 4, bh + glow_radius * 4), pygame.SRCALPHA)
    for i in range(glow_radius, 0, -1):
        t = i / glow_radius
        a = int(alpha_base * (1.0 - t))
        layer = font.render(text, True, (*color[:3], ))
        temp = pygame.Surface((bw, bh), pygame.SRCALPHA)
        temp.blit(layer, (0, 0))
        temp.set_alpha(a)
        scale_w = bw + i * 4
        scale_h = bh + i * 2
        scaled = pygame.transform.smoothscale(temp, (scale_w, scale_h))
        ox = (glow_surf.get_width() - scale_w) // 2
        oy = (glow_surf.get_height() - scale_h) // 2
        glow_surf.blit(scaled, (ox, oy))
    gx = x - glow_radius * 2
    gy = y - glow_radius * 2
    surface.blit(glow_surf, (gx, gy))
    surface.blit(base, (x, y))


# ── Particle system ────────────────────────────────────────────────

class _Particle:
    __slots__ = ('x', 'y', 'vx', 'vy', 'life', 'max_life', 'size', 'color')

    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.vx = random.uniform(-8, 8)
        self.vy = random.uniform(-40, -15)
        self.life = 0.0
        self.max_life = random.uniform(2.5, 5.0)
        self.size = random.randint(1, 3)
        self.color = color


class _ParticleSystem:
    def __init__(self, max_particles=120):
        self.particles = []
        self.max = max_particles
        self.spawn_timer = 0.0
        self.spawn_rate = 0.03

    def update(self, dt):
        self.spawn_timer += dt
        while self.spawn_timer >= self.spawn_rate and len(self.particles) < self.max:
            self.spawn_timer -= self.spawn_rate
            color = random.choice([_CYAN, _NEON_GREEN, (0, 180, 160), (40, 255, 80)])
            p = _Particle(random.randint(40, WIDTH - 40), HEIGHT + 10, color)
            self.particles.append(p)
        alive = []
        for p in self.particles:
            p.life += dt
            if p.life < p.max_life:
                p.x += p.vx * dt
                p.y += p.vy * dt
                p.vx += random.uniform(-5, 5) * dt
                alive.append(p)
        self.particles = alive

    def draw(self, surface):
        for p in self.particles:
            t = p.life / p.max_life
            alpha = int(180 * (1.0 - t))
            if alpha <= 0:
                continue
            s = pygame.Surface((p.size * 2, p.size * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*p.color, alpha), (p.size, p.size), p.size)
            surface.blit(s, (int(p.x) - p.size, int(p.y) - p.size))


# ── Matrix rain columns ───────────────────────────────────────────

class _MatrixColumn:
    __slots__ = ('x', 'y', 'speed', 'chars', 'spacing', 'fade_len', 'timer', 'change_rate')

    def __init__(self, x):
        self.x = x
        self.y = random.uniform(-HEIGHT, 0)
        self.speed = random.uniform(60, 160)
        self.chars = [random.choice(_MATRIX_CHARS) for _ in range(random.randint(8, 22))]
        self.spacing = 14
        self.fade_len = len(self.chars)
        self.timer = 0.0
        self.change_rate = random.uniform(0.05, 0.15)


class _MatrixRain:
    def __init__(self, side_width=80):
        self.font = None
        self.side_width = side_width
        self.columns_left = []
        self.columns_right = []
        self._init_columns()

    def _init_columns(self):
        for x in range(0, self.side_width, 14):
            self.columns_left.append(_MatrixColumn(x))
        for x in range(WIDTH - self.side_width, WIDTH, 14):
            self.columns_right.append(_MatrixColumn(x))

    def update(self, dt):
        for col in self.columns_left + self.columns_right:
            col.y += col.speed * dt
            if col.y > HEIGHT + 200:
                col.y = random.uniform(-HEIGHT, -100)
                col.speed = random.uniform(60, 160)
            col.timer += dt
            if col.timer >= col.change_rate:
                col.timer = 0.0
                idx = random.randint(0, len(col.chars) - 1)
                col.chars[idx] = random.choice(_MATRIX_CHARS)

    def draw(self, surface):
        if self.font is None:
            self.font = pygame.font.SysFont("monospace", 11)
        for col in self.columns_left + self.columns_right:
            for i, ch in enumerate(col.chars):
                cy = int(col.y + i * col.spacing)
                if cy < -20 or cy > HEIGHT + 20:
                    continue
                t = i / max(col.fade_len, 1)
                if i == 0:
                    color = (200, 255, 200)
                    alpha = 220
                else:
                    alpha = int(140 * (1.0 - t * 0.8))
                    color = (0, max(80, 255 - int(t * 180)), 0)
                if alpha <= 0:
                    continue
                cs = self.font.render(ch, True, color)
                cs.set_alpha(alpha)
                surface.blit(cs, (col.x, cy))


# ── IntroScene ─────────────────────────────────────────────────────

class IntroScene:
    def __init__(self, manager):
        self.manager = manager

        # Fonts
        self.font_title = pygame.font.SysFont("monospace", 86, bold=True)
        self.font_subtitle = pygame.font.SysFont("monospace", 16)
        self.font_badge = pygame.font.SysFont("monospace", 11, bold=True)
        self.font_menu = pygame.font.SysFont("monospace", 22, bold=True)
        self.font_hint = pygame.font.SysFont("monospace", 13)
        self.font_diff_name = pygame.font.SysFont("monospace", 22, bold=True)
        self.font_diff_desc = pygame.font.SysFont("monospace", 12)
        self.font_diff_title = pygame.font.SysFont("monospace", 26, bold=True)
        self.font_circuit = pygame.font.SysFont("monospace", 8)

        # Phase
        self.phase = _PHASE_MAIN

        # Fade-in from black
        self.fade_timer = 0.0
        self.fade_duration = 1.5
        self.fade_alpha = 255

        # Boot flash (brief white flash on title appear)
        self.boot_flash_timer = 0.0
        self.boot_flash_duration = 0.12
        self.boot_triggered = False

        # Title glitch system
        self.glitch_timer = 0.0
        self.glitch_interval = random.uniform(3.0, 5.0)
        self.glitch_active = False
        self.glitch_frame = 0
        self.glitch_total_frames = 8
        self.glitch_offset_x = 0
        self.glitch_corrupt_text = _TITLE_TEXT
        self.glitch_lines = []

        # Title shimmer/pulse
        self.shimmer_timer = 0.0

        # Subtitle staggered reveal
        self.subtitle_timer = 0.0
        self.subtitle_chars_visible = 0
        self.subtitle_char_delay = 0.05
        self.subtitle_fully_revealed = False

        # CRT scanlines
        self.scanlines_surf, self.scanline_total_h = _build_scanline_texture(WIDTH, HEIGHT)
        self.scanline_offset = 0.0

        # Vignette
        self.vignette_surf = _build_vignette_surface(WIDTH, HEIGHT)

        # Particles
        self.particles = _ParticleSystem(100)

        # Matrix rain
        self.matrix = _MatrixRain(70)

        # Random ambient glitch lines
        self.ambient_glitch_timer = 0.0
        self.ambient_glitch_interval = random.uniform(1.5, 4.0)
        self.ambient_glitch_lines = []

        # Monitor glow
        self.monitor_glow_timer = 0.0

        # Menu blink
        self.blink_timer = 0.0
        self.blink_cycle = 1.2
        self.menu_visible = True

        # Menu button
        self.menu_rect = pygame.Rect(0, 0, 320, 52)
        self.menu_rect.centerx = WIDTH // 2
        self.menu_rect.centery = HEIGHT - 130
        self.menu_hovered = False
        self.menu_pulse_timer = 0.0

        # Click flash
        self.click_flash_timer = 0.0
        self.click_flash_duration = 0.1

        # Badge pulsing
        self.badge_pulse_timer = 0.0

        # Circuit line animation for badges
        self.circuit_timer = 0.0

        # Difficulty buttons
        self.diff_buttons = []
        self.diff_hovered = -1
        self._build_difficulty_buttons()

        # Difficulty phase transition
        self.diff_fade_timer = 0.0
        self.diff_fade_duration = 0.4

        # Pre-render furniture layer (static)
        self._build_furniture_layer()

    # ── Setup ──────────────────────────────────────────────────────

    def _build_difficulty_buttons(self):
        btn_w, btn_h = 500, 60
        start_y = 250
        gap = 18
        self.diff_buttons = []
        for i, diff in enumerate([DIFFICULTY_DUMMY, DIFFICULTY_MID,
                                  DIFFICULTY_SENIOR, DIFFICULTY_NOOB]):
            r = pygame.Rect(0, 0, btn_w, btn_h)
            r.centerx = WIDTH // 2
            r.y = start_y + i * (btn_h + gap)
            self.diff_buttons.append((r, diff))

    def _build_furniture_layer(self):
        """Pre-render the dim office furniture background."""
        self.furniture_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        draw_desk(self.furniture_surf, 80, 380, w=120, h=55)
        draw_monitor(self.furniture_surf, 105, 335)
        draw_monitor(self.furniture_surf, 155, 340)
        draw_chair(self.furniture_surf, 140, 445)
        draw_desk(self.furniture_surf, 900, 400, w=120, h=55)
        draw_monitor(self.furniture_surf, 920, 355)
        draw_monitor(self.furniture_surf, 970, 360)
        draw_chair(self.furniture_surf, 960, 465)
        draw_desk(self.furniture_surf, 500, 450, w=100, h=45)
        draw_monitor(self.furniture_surf, 520, 410)
        draw_plant(self.furniture_surf, 30, 220)
        draw_plant(self.furniture_surf, 1210, 260)
        draw_plant(self.furniture_surf, 620, 500)
        draw_filing_cabinet(self.furniture_surf, 260, 520)
        draw_filing_cabinet(self.furniture_surf, 300, 510)
        draw_filing_cabinet(self.furniture_surf, 1020, 500)
        draw_filing_cabinet(self.furniture_surf, 1060, 490)

    # ── Events ─────────────────────────────────────────────────────

    def handle_event(self, event):
        if self.phase == _PHASE_MAIN:
            self._handle_main_event(event)
        elif self.phase == _PHASE_DIFFICULTY:
            self._handle_difficulty_event(event)

    def _handle_main_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.menu_hovered = self.menu_rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.menu_rect.collidepoint(event.pos):
                self.click_flash_timer = self.click_flash_duration
                self.phase = _PHASE_DIFFICULTY
                self.diff_hovered = -1
                self.diff_fade_timer = 0.0

    def _handle_difficulty_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.diff_hovered = -1
            for i, (r, _) in enumerate(self.diff_buttons):
                if r.collidepoint(event.pos):
                    self.diff_hovered = i
                    break
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for r, diff in self.diff_buttons:
                if r.collidepoint(event.pos):
                    self.manager.difficulty = diff
                    self.manager.change_scene("hub")
                    return

    # ── Update ─────────────────────────────────────────────────────

    def update(self, dt):
        # Fade-in
        if self.fade_timer < self.fade_duration:
            self.fade_timer += dt
            t = min(self.fade_timer / self.fade_duration, 1.0)
            self.fade_alpha = int(255 * (1.0 - t))
            # Trigger boot flash when mostly faded in
            if t > 0.7 and not self.boot_triggered:
                self.boot_triggered = True
                self.boot_flash_timer = self.boot_flash_duration

        # Boot flash decay
        if self.boot_flash_timer > 0:
            self.boot_flash_timer -= dt

        # Click flash
        if self.click_flash_timer > 0:
            self.click_flash_timer -= dt

        # Title glitch system
        self.glitch_timer += dt
        if self.glitch_active:
            self.glitch_frame += 1
            if self.glitch_frame <= 4:
                # RGB split + displacement phase
                self.glitch_offset_x = random.randint(-5, 5)
            elif self.glitch_frame <= 6:
                # Corruption phase: random chars
                chars = list(_TITLE_TEXT)
                num_corrupt = random.randint(2, 4)
                for _ in range(num_corrupt):
                    idx = random.randint(0, len(chars) - 1)
                    chars[idx] = random.choice(_GLITCH_CHARS)
                self.glitch_corrupt_text = "".join(chars)
                self.glitch_offset_x = random.randint(-3, 3)
            else:
                # End glitch
                self.glitch_active = False
                self.glitch_frame = 0
                self.glitch_offset_x = 0
                self.glitch_corrupt_text = _TITLE_TEXT
                self.glitch_timer = 0.0
                self.glitch_interval = random.uniform(3.0, 5.0)
                self.glitch_lines.clear()

            # Generate horizontal glitch lines during active glitch
            if self.glitch_active:
                self.glitch_lines = []
                for _ in range(random.randint(2, 5)):
                    gy = random.randint(0, HEIGHT)
                    gh = random.randint(1, 4)
                    gw = random.randint(100, WIDTH)
                    gx = random.randint(0, WIDTH - gw)
                    self.glitch_lines.append((gx, gy, gw, gh))
        elif self.glitch_timer >= self.glitch_interval:
            self.glitch_active = True
            self.glitch_frame = 0

        # Title shimmer
        self.shimmer_timer += dt

        # Subtitle reveal
        if not self.subtitle_fully_revealed:
            self.subtitle_timer += dt
            new_count = int(self.subtitle_timer / self.subtitle_char_delay)
            self.subtitle_chars_visible = min(new_count, len(_SUBTITLE_TEXT))
            if self.subtitle_chars_visible >= len(_SUBTITLE_TEXT):
                self.subtitle_fully_revealed = True

        # Scanline scroll
        self.scanline_offset += dt * 25.0
        if self.scanline_offset >= HEIGHT:
            self.scanline_offset -= HEIGHT

        # Particles
        self.particles.update(dt)

        # Matrix rain
        self.matrix.update(dt)

        # Ambient glitch lines
        self.ambient_glitch_timer += dt
        if self.ambient_glitch_timer >= self.ambient_glitch_interval:
            self.ambient_glitch_timer = 0.0
            self.ambient_glitch_interval = random.uniform(1.5, 4.0)
            self.ambient_glitch_lines = []
            for _ in range(random.randint(1, 3)):
                gy = random.randint(0, HEIGHT)
                gh = random.randint(1, 3)
                gw = random.randint(200, WIDTH)
                gx = random.randint(0, max(1, WIDTH - gw))
                self.ambient_glitch_lines.append((gx, gy, gw, gh, 0.15))
        # Decay ambient glitch lines
        new_lines = []
        for gx, gy, gw, gh, life in self.ambient_glitch_lines:
            life -= dt
            if life > 0:
                new_lines.append((gx, gy, gw, gh, life))
        self.ambient_glitch_lines = new_lines

        # Monitor glow
        self.monitor_glow_timer += dt

        # Menu blink
        self.blink_timer += dt
        if self.blink_timer >= self.blink_cycle:
            self.blink_timer -= self.blink_cycle
        self.menu_visible = self.blink_timer < (self.blink_cycle * 0.65)

        # Menu pulse
        self.menu_pulse_timer += dt

        # Badge pulse
        self.badge_pulse_timer += dt

        # Circuit animation
        self.circuit_timer += dt

        # Difficulty fade
        if self.phase == _PHASE_DIFFICULTY and self.diff_fade_timer < self.diff_fade_duration:
            self.diff_fade_timer += dt

    # ── Draw ───────────────────────────────────────────────────────

    def draw(self, surface):
        # Base dark background
        draw_office_floor(surface)
        draw_wall(surface, 0, wall_h=90)

        # Ambient monitor glow (pulsing colored light on background)
        self._draw_monitor_glow(surface)

        # Furniture layer - visible but subtle
        self.furniture_surf.set_alpha(80)
        surface.blit(self.furniture_surf, (0, 0))

        # Matrix rain on sides
        self.matrix.draw(surface)

        # Floating particles
        self.particles.draw(surface)

        # Ambient glitch lines
        for gx, gy, gw, gh, life in self.ambient_glitch_lines:
            alpha = int(120 * (life / 0.15))
            color = random.choice([_CYAN, _NEON_GREEN])
            gs = pygame.Surface((gw, gh), pygame.SRCALPHA)
            gs.fill((*color, alpha))
            surface.blit(gs, (gx, gy))

        # Phase content
        if self.phase == _PHASE_MAIN:
            self._draw_main(surface)
        elif self.phase == _PHASE_DIFFICULTY:
            self._draw_difficulty(surface)

        # Active glitch lines (during title glitch)
        if self.glitch_active:
            for gx, gy, gw, gh in self.glitch_lines:
                color = random.choice([(255, 0, 0), (0, 255, 0), (0, 200, 255)])
                gs = pygame.Surface((gw, gh), pygame.SRCALPHA)
                gs.fill((*color, random.randint(60, 140)))
                surface.blit(gs, (gx, gy))

        # CRT scanlines
        scan_y = -int(self.scanline_offset)
        surface.blit(self.scanlines_surf, (0, scan_y))

        # Vignette
        surface.blit(self.vignette_surf, (0, 0))

        # Boot flash overlay
        if self.boot_flash_timer > 0:
            t = self.boot_flash_timer / self.boot_flash_duration
            flash = pygame.Surface((WIDTH, HEIGHT))
            flash.fill((220, 240, 255))
            flash.set_alpha(int(180 * t))
            surface.blit(flash, (0, 0))

        # Click flash
        if self.click_flash_timer > 0:
            t = self.click_flash_timer / self.click_flash_duration
            flash = pygame.Surface((WIDTH, HEIGHT))
            flash.fill(C_NEON)
            flash.set_alpha(int(100 * t))
            surface.blit(flash, (0, 0))

        # Fade-in from black
        if self.fade_alpha > 0:
            fade_surf = pygame.Surface((WIDTH, HEIGHT))
            fade_surf.fill((0, 0, 0))
            fade_surf.set_alpha(self.fade_alpha)
            surface.blit(fade_surf, (0, 0))

    # ── Monitor glow ───────────────────────────────────────────────

    def _draw_monitor_glow(self, surface):
        """Subtle ambient screen glow from monitors."""
        glow_alpha = int(12 + 6 * math.sin(self.monitor_glow_timer * 1.2))
        positions = [(130, 340), (880, 360), (540, 415)]
        for mx, my in positions:
            glow = pygame.Surface((160, 120), pygame.SRCALPHA)
            for r in range(60, 10, -5):
                a = int(glow_alpha * (1.0 - r / 60.0))
                color = (0, 60, 50, a) if mx < WIDTH // 2 else (0, 40, 60, a)
                pygame.draw.ellipse(glow, color, (80 - r, 60 - r, r * 2, r * 2))
            surface.blit(glow, (mx - 80, my - 60))

    # ── Main screen ────────────────────────────────────────────────

    def _draw_main(self, surface):
        self._draw_badges(surface)
        self._draw_title(surface)
        self._draw_subtitle(surface)
        self._draw_menu_button(surface)

    # ── Title with neon glow + glitch ──────────────────────────────

    def _draw_title(self, surface):
        title_y = HEIGHT // 2 - 140

        # Determine text to render
        if self.glitch_active and self.glitch_frame > 4:
            display_text = self.glitch_corrupt_text
        else:
            display_text = _TITLE_TEXT

        # Measure for centering
        measure = self.font_title.render(display_text, True, C_NEON)
        title_w = measure.get_width()
        title_x = WIDTH // 2 - title_w // 2 + self.glitch_offset_x

        # Dark backing panel
        panel_w = title_w + 80
        panel_h = measure.get_height() + 30
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 200))
        surface.blit(panel, (WIDTH // 2 - panel_w // 2, title_y - 15))

        # Shimmer pulse on glow intensity
        shimmer = 0.7 + 0.3 * math.sin(self.shimmer_timer * 2.5)
        glow_alpha = int(50 * shimmer)

        if self.glitch_active and self.glitch_frame <= 4:
            # RGB channel split
            r_text = self.font_title.render(display_text, True, (255, 0, 0))
            r_text.set_alpha(90)
            surface.blit(r_text, (title_x - 4 + random.randint(-2, 0),
                                  title_y + random.randint(-1, 1)))

            b_text = self.font_title.render(display_text, True, (0, 80, 255))
            b_text.set_alpha(80)
            surface.blit(b_text, (title_x + 4 + random.randint(0, 2),
                                  title_y + random.randint(-1, 1)))

        # Main neon title
        _draw_neon_text(surface, display_text, self.font_title,
                        title_x, title_y, _NEON_GREEN,
                        glow_radius=5, alpha_base=glow_alpha)

        # Underline accent
        line_y = title_y + measure.get_height() + 8
        line_half = title_w // 2 + 20
        glow_val = int(80 + 40 * shimmer)
        pygame.draw.line(surface, (0, glow_val, 0),
                         (WIDTH // 2 - line_half, line_y),
                         (WIDTH // 2 + line_half, line_y), 1)

    # ── Subtitle with staggered character reveal ───────────────────

    def _draw_subtitle(self, surface):
        title_measure = self.font_title.render(_TITLE_TEXT, True, C_NEON)
        sub_y = HEIGHT // 2 - 140 + title_measure.get_height() + 28

        visible_text = _SUBTITLE_TEXT[:self.subtitle_chars_visible]
        if not visible_text:
            return

        # Letter-spaced rendering
        total_w = 0
        char_surfaces = []
        spacing = 3
        for ch in visible_text:
            cs = self.font_subtitle.render(ch, True, _CYAN)
            char_surfaces.append(cs)
            total_w += cs.get_width() + spacing
        total_w -= spacing

        start_x = WIDTH // 2 - total_w // 2

        # Background
        bg = pygame.Surface((total_w + 24, char_surfaces[0].get_height() + 12),
                            pygame.SRCALPHA)
        bg.fill((0, 0, 0, 190))
        surface.blit(bg, (start_x - 12, sub_y - 6))

        # Draw each character with subtle glow on the last revealed one
        cx = start_x
        for i, cs in enumerate(char_surfaces):
            if i == len(char_surfaces) - 1 and not self.subtitle_fully_revealed:
                # Bright cursor-like glow on latest char
                glow = pygame.Surface((cs.get_width() + 4, cs.get_height() + 4),
                                      pygame.SRCALPHA)
                glow.fill((*_CYAN, 40))
                surface.blit(glow, (cx - 2, sub_y - 2))
            surface.blit(cs, (cx, sub_y))
            cx += cs.get_width() + spacing

        # Subtle glow on fully revealed subtitle
        if self.subtitle_fully_revealed:
            shimmer = 0.6 + 0.4 * math.sin(self.shimmer_timer * 1.8 + 1.0)
            glow_s = pygame.Surface((total_w + 30, 24), pygame.SRCALPHA)
            glow_s.fill((*_CYAN, int(15 * shimmer)))
            surface.blit(glow_s, (start_x - 15, sub_y - 3))

    # ── Badges ─────────────────────────────────────────────────────

    def _draw_badges(self, surface):
        self._draw_badge_clasificado(surface)
        self._draw_badge_caso(surface)

    def _draw_badge_clasificado(self, surface):
        """CLASIFICADO badge with pulsing red corner dots."""
        text = self.font_badge.render("CLASIFICADO", True, C_RED)
        pad_x, pad_y = 12, 6
        bw = text.get_width() + pad_x * 2
        bh = text.get_height() + pad_y * 2
        bx, by = 24, 24

        # Background
        badge = pygame.Surface((bw, bh), pygame.SRCALPHA)
        badge.fill((0, 0, 0, 230))
        pygame.draw.rect(badge, (*C_RED, 220), badge.get_rect(), 2)
        surface.blit(badge, (bx, by))
        surface.blit(text, (bx + pad_x, by + pad_y))

        # Pulsing red corner dots
        pulse = 0.5 + 0.5 * math.sin(self.badge_pulse_timer * 3.0)
        dot_alpha = int(100 + 155 * pulse)
        dot_size = 3
        corners = [(bx + 1, by + 1), (bx + bw - 2, by + 1),
                    (bx + 1, by + bh - 2), (bx + bw - 2, by + bh - 2)]
        for dx, dy in corners:
            ds = pygame.Surface((dot_size * 2, dot_size * 2), pygame.SRCALPHA)
            pygame.draw.circle(ds, (255, 50, 50, dot_alpha), (dot_size, dot_size), dot_size)
            surface.blit(ds, (dx - dot_size, dy - dot_size))

    def _draw_badge_caso(self, surface):
        """CASO #DL-2031 badge with tech border and circuit lines."""
        text = self.font_badge.render("CASO #DL-2031", True, C_TEXT_SEC)
        pad_x, pad_y = 12, 6
        bw = text.get_width() + pad_x * 2
        bh = text.get_height() + pad_y * 2
        bx = WIDTH - bw - 24
        by = 24

        # Background
        badge = pygame.Surface((bw, bh), pygame.SRCALPHA)
        badge.fill((0, 0, 0, 230))
        # Tech-style double border
        pygame.draw.rect(badge, (*C_BORDER, 200), badge.get_rect(), 1)
        inner = badge.get_rect().inflate(-4, -4)
        pygame.draw.rect(badge, (*C_BORDER, 100), inner, 1)
        surface.blit(badge, (bx, by))
        surface.blit(text, (bx + pad_x, by + pad_y))

        # Animated circuit lines extending from badge
        ct = self.circuit_timer * 40
        circuit_color = (*_DARK_CYAN, 120)
        # Right side circuit
        seg_len = int(20 + 10 * math.sin(ct * 0.05))
        cs = pygame.Surface((seg_len + 6, 2), pygame.SRCALPHA)
        cs.fill((0, 150, 130, 80))
        surface.blit(cs, (bx + bw + 2, by + bh // 2 - 1))
        # Small node at end
        node_x = bx + bw + 2 + seg_len
        ns = pygame.Surface((4, 4), pygame.SRCALPHA)
        pygame.draw.circle(ns, (0, 200, 180, 160), (2, 2), 2)
        surface.blit(ns, (node_x, by + bh // 2 - 2))

    # ── Menu button ────────────────────────────────────────────────

    def _draw_menu_button(self, surface):
        r = self.menu_rect
        pulse = 0.5 + 0.5 * math.sin(self.menu_pulse_timer * 2.5)

        # Button background
        bg_alpha = 210 if self.menu_hovered else 180
        btn = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
        if self.menu_hovered:
            btn.fill((10, 30, 20, bg_alpha))
        else:
            btn.fill((0, 0, 0, bg_alpha))

        # Neon border with pulse
        if self.menu_hovered:
            border_color = _NEON_GREEN
            border_w = 2
            # Outer glow
            glow = pygame.Surface((r.w + 12, r.h + 12), pygame.SRCALPHA)
            pygame.draw.rect(glow, (*_NEON_GREEN, int(40 * pulse)),
                             glow.get_rect(), 0, border_radius=2)
            surface.blit(glow, (r.x - 6, r.y - 6))
        else:
            g = int(120 + 60 * pulse)
            border_color = (0, g, int(g * 0.3))
            border_w = 1

        pygame.draw.rect(btn, (*border_color, 220), btn.get_rect(), border_w)
        surface.blit(btn, r.topleft)

        # Label
        if self.menu_hovered:
            label_color = _NEON_GREEN
        else:
            label_color = C_TEXT_PRI
        label = self.font_menu.render("[ NUEVA PARTIDA ]", True, label_color)
        lx = r.centerx - label.get_width() // 2
        ly = r.centery - label.get_height() // 2
        surface.blit(label, (lx, ly))

        # Neon glow on text when hovered
        if self.menu_hovered:
            glow_text = self.font_menu.render("[ NUEVA PARTIDA ]", True, _NEON_GREEN)
            glow_text.set_alpha(int(60 * pulse))
            surface.blit(glow_text, (lx, ly))

        # Blinking "INICIAR MISION" below
        if self.menu_visible:
            blink_color = (*_NEON_GREEN[:3],)
            blink_surf = self.font_hint.render("INICIAR MISION", True, blink_color)
            bx = WIDTH // 2 - blink_surf.get_width() // 2
            by = r.bottom + 16
            surface.blit(blink_surf, (bx, by))

    # ── Difficulty selection ───────────────────────────────────────

    def _draw_difficulty(self, surface):
        # Dim overlay
        fade_t = min(self.diff_fade_timer / self.diff_fade_duration, 1.0)
        dim_alpha = int(100 * fade_t)
        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, dim_alpha))
        surface.blit(dim, (0, 0))

        if fade_t < 0.3:
            return

        content_alpha = min(int(255 * ((fade_t - 0.3) / 0.7)), 255)

        # Title with glitch effect
        title_text = "SELECCIONA NIVEL DE ACCESO"
        # Occasional glitch on difficulty title
        if random.random() < 0.02:
            chars = list(title_text)
            for _ in range(2):
                idx = random.randint(0, len(chars) - 1)
                chars[idx] = random.choice(_GLITCH_CHARS)
            title_text = "".join(chars)

        title_surf = self.font_diff_title.render(title_text, True, _NEON_GREEN)
        tx = WIDTH // 2 - title_surf.get_width() // 2
        ty = 170

        # Title bg
        tbg = pygame.Surface((title_surf.get_width() + 30, title_surf.get_height() + 16),
                              pygame.SRCALPHA)
        tbg.fill((0, 0, 0, 230))
        tbg.set_alpha(content_alpha)
        surface.blit(tbg, (tx - 15, ty - 8))

        title_surf.set_alpha(content_alpha)
        surface.blit(title_surf, (tx, ty))

        # Decorative line
        line_y = ty + title_surf.get_height() + 14
        ls = pygame.Surface((420, 1), pygame.SRCALPHA)
        ls.fill((*C_BORDER, content_alpha))
        surface.blit(ls, (WIDTH // 2 - 210, line_y))

        # Difficulty buttons
        for i, (rect, diff) in enumerate(self.diff_buttons):
            hovered = (i == self.diff_hovered)
            color = _DIFF_COLORS[diff]
            name = DIFFICULTY_NAMES[diff]
            desc = DIFFICULTY_DESC[diff]
            self._draw_diff_button(surface, rect, name, desc, color, hovered,
                                   content_alpha)

        # Hint
        hint = self.font_hint.render("Haz clic en una dificultad para comenzar",
                                     True, C_TEXT_HINT)
        hx = WIDTH // 2 - hint.get_width() // 2
        hy = self.diff_buttons[-1][0].bottom + 28

        hbg = pygame.Surface((hint.get_width() + 20, hint.get_height() + 10),
                              pygame.SRCALPHA)
        hbg.fill((0, 0, 0, 180))
        hbg.set_alpha(content_alpha)
        surface.blit(hbg, (hx - 10, hy - 5))
        hint.set_alpha(content_alpha)
        surface.blit(hint, (hx, hy))

    def _draw_diff_button(self, surface, rect, name, desc, color, hovered,
                          content_alpha):
        """Difficulty button with color-coded accent bar, hover glow, circuit bg."""
        btn = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)

        # Background
        bg_alpha = min(220 if hovered else 170, content_alpha)
        btn.fill((0, 0, 0, bg_alpha))

        # Circuit pattern background
        circuit_offset = int(self.circuit_timer * 20) % 40
        for cx in range(0, rect.w, 40):
            for cy_off in [15, 35]:
                lx = cx + circuit_offset
                if lx < rect.w - 20:
                    pygame.draw.line(btn, (color[0] // 6, color[1] // 6, color[2] // 6, 60),
                                     (lx, cy_off), (lx + 12, cy_off), 1)
                    # Node dot
                    pygame.draw.circle(btn,
                                       (color[0] // 5, color[1] // 5, color[2] // 5, 80),
                                       (lx + 12, cy_off), 2)

        # Color-coded left accent bar
        bar_w = 6 if not hovered else 14
        pygame.draw.rect(btn, (*color, 255), (0, 0, bar_w, rect.h))

        # Border
        if hovered:
            pygame.draw.rect(btn, (*color, 200), btn.get_rect(), 2)
            # Glow effect
            glow = pygame.Surface((rect.w + 8, rect.h + 8), pygame.SRCALPHA)
            glow.fill((*color, 20))
            surface.blit(glow, (rect.x - 4, rect.y - 4))
        else:
            dim_color = (color[0] // 3, color[1] // 3, color[2] // 3)
            pygame.draw.rect(btn, (*dim_color, 180), btn.get_rect(), 1)

        btn.set_alpha(content_alpha)
        surface.blit(btn, rect.topleft)

        # Name on left
        name_color = color if hovered else C_TEXT_PRI
        name_surf = self.font_diff_name.render(f"[ {name} ]", True, name_color)
        name_surf.set_alpha(content_alpha)
        nx = rect.x + 28
        ny = rect.y + rect.h // 2 - name_surf.get_height() // 2
        surface.blit(name_surf, (nx, ny))

        # Description on right
        desc_color = C_WHITE if hovered else C_TEXT_SEC
        desc_surf = self.font_diff_desc.render(desc, True, desc_color)
        desc_surf.set_alpha(content_alpha)
        dx = rect.x + rect.w - desc_surf.get_width() - 16
        dy = rect.y + rect.h // 2 - desc_surf.get_height() // 2
        surface.blit(desc_surf, (dx, dy))
