import pygame
import math
import random
from game.constants import (WIDTH, HEIGHT, C_BG, C_BG2, C_BG3, C_BORDER, C_TEXT_PRI,
    C_TEXT_SEC, C_TEXT_HINT, C_ACCENT, C_GREEN, C_RED, C_NEON, C_WHITE, C_PANEL,
    C_DH, C_AMBER, C_CAESAR, C_BASE64, C_HASH, HINTS_CONFIG)
from game.ui.draw_assets import (draw_office_floor, draw_wall, draw_text_box, word_wrap,
    draw_desk, draw_monitor, draw_server_rack)
from game.ui.dialogue import DialogueBox
from game.ui.hud import HUD


# Score row config: (key, display_name, color)
_SCORE_ROWS = [
    ("caesar",         "CESAR",          C_CAESAR),
    ("base64",         "BASE64",         C_BASE64),
    ("hash",           "SHA-256",        C_HASH),
    ("diffie_hellman", "DIFFIE-HELLMAN", C_DH),
]

# Rank thresholds
_RANKS = [
    (340, "MAESTRO CRIPTOGRAFO", C_AMBER),
    (260, "AGENTE SENIOR",       C_GREEN),
    (160, "ANALISTA",            C_ACCENT),
    (0,   "RECLUTA",             C_TEXT_HINT),
]

_BUTTON_W = 280
_BUTTON_H = 48
_ROW_FADE_DELAY = 0.5  # seconds between each row fade-in


# ---------------------------------------------------------------------------
# Star particle (background twinkle)
# ---------------------------------------------------------------------------
class _Star:
    __slots__ = ("x", "y", "size", "alpha", "twinkle_speed", "twinkle_offset")

    def __init__(self):
        self.x = random.uniform(0, WIDTH)
        self.y = random.uniform(0, HEIGHT)
        self.size = random.choice([1, 1, 1, 1, 2])
        self.alpha = random.randint(30, 120)
        self.twinkle_speed = random.uniform(1.5, 4.0)
        self.twinkle_offset = random.uniform(0, 2 * math.pi)


# ---------------------------------------------------------------------------
# Ember particle (floating upward)
# ---------------------------------------------------------------------------
class _Ember:
    __slots__ = ("x", "y", "vx", "vy", "size", "alpha", "max_alpha", "color")

    def __init__(self):
        self.x = random.uniform(0, WIDTH)
        self.y = random.uniform(0, HEIGHT)
        self.vx = random.uniform(-8, 8)
        self.vy = random.uniform(-18, -5)
        self.size = random.choice([1, 1, 1, 2, 2, 3])
        self.max_alpha = random.randint(60, 180)
        self.alpha = random.randint(20, self.max_alpha)
        base_colors = [C_NEON, C_AMBER, C_ACCENT, C_GREEN]
        self.color = random.choice(base_colors)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.alpha += random.uniform(-40, 40) * dt
        self.alpha = max(10, min(self.max_alpha, self.alpha))
        if self.y < -10 or self.x < -10 or self.x > WIDTH + 10:
            self.x = random.uniform(0, WIDTH)
            self.y = HEIGHT + random.randint(0, 30)
            self.vy = random.uniform(-18, -5)


# ---------------------------------------------------------------------------
# Golden particle for top rank explosion
# ---------------------------------------------------------------------------
class _GoldParticle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "size")

    def __init__(self, cx, cy):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(30, 150)
        self.x = float(cx)
        self.y = float(cy)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = random.uniform(0.8, 2.0)
        self.max_life = self.life
        self.size = random.choice([2, 3, 4])

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 30 * dt  # gravity
        self.vx *= (1.0 - 0.5 * dt)
        self.life -= dt
        return self.life > 0


# ---------------------------------------------------------------------------
# Glitch effect data
# ---------------------------------------------------------------------------
class _GlitchSlice:
    __slots__ = ("y", "h", "offset", "timer")

    def __init__(self):
        self.y = random.randint(0, HEIGHT)
        self.h = random.randint(2, 8)
        self.offset = random.randint(-15, 15)
        self.timer = random.uniform(0.03, 0.1)


class EndingScene:
    def __init__(self, manager):
        self.manager = manager

        # Fonts
        self.font_title = pygame.font.SysFont("monospace", 48, bold=True)
        self.font_subtitle = pygame.font.SysFont("monospace", 18)
        self.font_row_name = pygame.font.SysFont("monospace", 17, bold=True)
        self.font_row_score = pygame.font.SysFont("monospace", 17, bold=True)
        self.font_total_label = pygame.font.SysFont("monospace", 20, bold=True)
        self.font_total_val = pygame.font.SysFont("monospace", 26, bold=True)
        self.font_rank = pygame.font.SysFont("monospace", 32, bold=True)
        self.font_rank_sub = pygame.font.SysFont("monospace", 14)
        self.font_btn = pygame.font.SysFont("monospace", 16, bold=True)
        self.font_small = pygame.font.SysFont("monospace", 13)

        # Timers
        self.elapsed = 0.0
        self.fade_in_duration = 0.6

        # Scores from manager
        self.row_scores = []
        for key, name, color in _SCORE_ROWS:
            pts = manager.scores.get(key, 0)
            self.row_scores.append((name, pts, color))
        self.total = manager.total_score()

        # Slot machine counters (for counting-up effect)
        self.displayed_scores = [0] * len(self.row_scores)
        self.displayed_total = 0
        self.score_count_speed = 200  # pts per second

        # Rank
        self.rank_name = "RECLUTA"
        self.rank_color = C_TEXT_HINT
        for threshold, rname, rcolor in _RANKS:
            if self.total >= threshold:
                self.rank_name = rname
                self.rank_color = rcolor
                break

        # Button
        self.btn_rect = pygame.Rect(
            WIDTH // 2 - _BUTTON_W // 2, HEIGHT - 100,
            _BUTTON_W, _BUTTON_H
        )
        self.btn_hovered = False

        # HUD
        self.hud = HUD()
        self.hud.set_info(scene_name="INFORME FINAL", layer_text="MISION COMPLETADA")

        # Dialogue
        self.dialogue = DialogueBox()
        ending_msgs = manager.dialogues.get("ending", {}).get("complete", [])
        if ending_msgs:
            self.dialogue.show(ending_msgs)

        # CRT scanlines (pre-rendered with pygame.draw only)
        self._scanline_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for y in range(0, HEIGHT, 3):
            pygame.draw.line(self._scanline_surf, (0, 0, 0, 18), (0, y), (WIDTH, y))

        # Vignette
        self._vignette_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for i in range(0, 140, 3):
            a = int((i / 140) * 100)
            pygame.draw.rect(
                self._vignette_surf, (0, 0, 0, a),
                (i, i, WIDTH - 2 * i, HEIGHT - 2 * i), 4,
            )

        # Star field
        self.stars = [_Star() for _ in range(80)]

        # Ember particles
        self.embers = [_Ember() for _ in range(50)]

        # Gold particles (spawn on rank reveal if top rank)
        self.gold_particles = []
        self.gold_spawned = False

        # Glitch effect for title appear
        self.glitch_slices = []
        self.glitch_timer = 0.0
        self.glitch_active = True

        # Glow pulse
        self.glow_timer = 0.0

    # ------------------------------------------------------------------
    # Neon text helper
    # ------------------------------------------------------------------
    def _neon_text(self, surface, text, x, y, font, color=C_NEON, intensity=1.0):
        for off in [3, 2, 1]:
            g = font.render(text, True, color)
            gs = pygame.Surface(g.get_size(), pygame.SRCALPHA)
            gs.blit(g, (0, 0))
            gs.set_alpha(int(50 * intensity))
            surface.blit(gs, (x - off, y))
            surface.blit(gs, (x + off, y))
            surface.blit(gs, (x, y - off))
            surface.blit(gs, (x, y + off))
        surface.blit(font.render(text, True, color), (x, y))

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def handle_event(self, event):
        if self.dialogue.active:
            self.dialogue.handle_event(event)
            return

        if event.type == pygame.MOUSEMOTION:
            self.btn_hovered = self.btn_rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.btn_rect.collidepoint(event.pos):
                self.manager.change_scene("intro")

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, dt):
        self.elapsed += dt
        self.glow_timer += dt
        self.dialogue.update(dt)

        for e in self.embers:
            e.update(dt)

        # Update glitch effect (active for first ~1 second)
        if self.glitch_active:
            self.glitch_timer += dt
            if self.glitch_timer > 1.0:
                self.glitch_active = False
                self.glitch_slices = []
            elif random.random() < 0.3:
                self.glitch_slices = [_GlitchSlice() for _ in range(random.randint(2, 6))]

        # Update slot machine score counters
        for i, (name, target_pts, color) in enumerate(self.row_scores):
            row_start = 0.6 + i * _ROW_FADE_DELAY + 0.4  # start counting after fade-in
            if self.elapsed > row_start and self.displayed_scores[i] < target_pts:
                self.displayed_scores[i] = min(
                    target_pts,
                    self.displayed_scores[i] + int(self.score_count_speed * dt)
                )

        # Update total counter
        total_start = 0.6 + len(self.row_scores) * _ROW_FADE_DELAY + 0.6
        if self.elapsed > total_start and self.displayed_total < self.total:
            self.displayed_total = min(
                self.total,
                self.displayed_total + int(self.score_count_speed * 1.5 * dt)
            )

        # Spawn golden explosion once if top rank
        rank_fade_start = 0.6 + (len(self.row_scores) + 1) * _ROW_FADE_DELAY + 0.5
        if (self.total >= 340 and not self.gold_spawned
                and self.elapsed > rank_fade_start + 0.3):
            self.gold_spawned = True
            cx = WIDTH // 2
            cy = 445
            for _ in range(60):
                self.gold_particles.append(_GoldParticle(cx, cy))

        # Update gold particles
        self.gold_particles = [gp for gp in self.gold_particles if gp.update(dt)]

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, surface):
        # Pure black background
        surface.fill((0, 0, 0))

        # Star field
        self._draw_stars(surface)

        # Ember particles (behind content)
        self._draw_embers(surface)

        # Title block with glitch
        self._draw_title(surface)

        # Score table
        self._draw_score_table(surface)

        # Rank
        self._draw_rank(surface)

        # Golden particles
        self._draw_gold_particles(surface)

        # Return button
        self._draw_button(surface)

        # CRT scanlines
        surface.blit(self._scanline_surf, (0, 0))

        # Vignette
        surface.blit(self._vignette_surf, (0, 0))

        # HUD
        self.hud.draw(surface)

        # Dialogue
        self.dialogue.draw(surface)

    # ------------------------------------------------------------------
    # Sub-renderers
    # ------------------------------------------------------------------

    def _draw_stars(self, surface):
        for s in self.stars:
            twinkle = math.sin(self.glow_timer * s.twinkle_speed + s.twinkle_offset)
            alpha = int(s.alpha * (0.5 + 0.5 * twinkle))
            alpha = max(0, min(255, alpha))
            if s.size <= 1:
                ps = pygame.Surface((2, 2), pygame.SRCALPHA)
                ps.fill((255, 255, 255, alpha))
                surface.blit(ps, (int(s.x), int(s.y)))
            else:
                ps = pygame.Surface((s.size * 2 + 2, s.size * 2 + 2), pygame.SRCALPHA)
                cx = s.size + 1
                # Soft glow
                pygame.draw.circle(ps, (255, 255, 255, alpha // 3), (cx, cx), s.size + 1)
                pygame.draw.circle(ps, (255, 255, 255, alpha), (cx, cx), s.size)
                surface.blit(ps, (int(s.x) - cx, int(s.y) - cx))

    def _draw_embers(self, surface):
        for e in self.embers:
            alpha = max(0, min(255, int(e.alpha)))
            color = (*e.color, alpha)
            if e.size <= 1:
                ps = pygame.Surface((2, 2), pygame.SRCALPHA)
                ps.fill(color)
                surface.blit(ps, (int(e.x), int(e.y)))
            else:
                ps = pygame.Surface((e.size * 4, e.size * 4), pygame.SRCALPHA)
                c = e.size * 2
                pygame.draw.circle(ps, (*e.color, alpha // 3), (c, c), e.size * 2)
                pygame.draw.circle(ps, color, (c, c), e.size)
                surface.blit(ps, (int(e.x) - c, int(e.y) - c))

    def _draw_gold_particles(self, surface):
        for gp in self.gold_particles:
            frac = gp.life / gp.max_life
            alpha = int(255 * frac)
            size = max(1, int(gp.size * frac))
            ps = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
            c = size * 2
            # Gold glow
            pygame.draw.circle(ps, (255, 200, 50, alpha // 3), (c, c), size * 2)
            pygame.draw.circle(ps, (255, 215, 80, alpha), (c, c), size)
            pygame.draw.circle(ps, (255, 240, 180, min(alpha, 200)), (c, c), max(1, size // 2))
            surface.blit(ps, (int(gp.x) - c, int(gp.y) - c))

    def _draw_title(self, surface):
        """MISION COMPLETADA in massive neon with glitch effect."""
        title_text = "MISION COMPLETADA"
        title_surf = self.font_title.render(title_text, True, C_NEON)
        tw = title_surf.get_width()
        tx = WIDTH // 2 - tw // 2
        ty = 55

        # Fade in
        fade_t = min(1.0, self.elapsed / self.fade_in_duration)

        # Intense neon glow (multi-layer)
        glow_pulse = 0.7 + 0.3 * math.sin(self.glow_timer * 2.5)
        for off in [5, 4, 3, 2, 1]:
            glow = self.font_title.render(title_text, True, C_NEON)
            glow.set_alpha(int(25 * glow_pulse * fade_t))
            surface.blit(glow, (tx - off, ty))
            surface.blit(glow, (tx + off, ty))
            surface.blit(glow, (tx, ty - off))
            surface.blit(glow, (tx, ty + off))

        # Main title
        title_surf.set_alpha(int(255 * fade_t))
        surface.blit(title_surf, (tx, ty))

        # Glitch effect (horizontal slices displaced)
        if self.glitch_active:
            for gs in self.glitch_slices:
                if ty <= gs.y <= ty + title_surf.get_height():
                    slice_y = gs.y - ty
                    slice_h = min(gs.h, title_surf.get_height() - slice_y)
                    if slice_h > 0:
                        slice_surf = pygame.Surface((tw, slice_h), pygame.SRCALPHA)
                        slice_surf.blit(title_surf, (0, -slice_y))
                        # Tint slice with chromatic aberration
                        red_slice = slice_surf.copy()
                        red_slice.fill((255, 0, 0, 60), special_flags=pygame.BLEND_RGBA_MULT)
                        surface.blit(red_slice, (tx + gs.offset + 3, gs.y))
                        cyan_slice = slice_surf.copy()
                        cyan_slice.fill((0, 255, 255, 60), special_flags=pygame.BLEND_RGBA_MULT)
                        surface.blit(cyan_slice, (tx + gs.offset - 3, gs.y))

        # Decorative line under title with neon glow
        line_w = tw + 60
        line_x = WIDTH // 2 - line_w // 2
        line_y = ty + title_surf.get_height() + 6
        line_alpha = int(150 * fade_t)
        # Glow line
        for loff in [3, 2, 1]:
            line_glow = pygame.Surface((line_w, 2 + loff * 2), pygame.SRCALPHA)
            pygame.draw.line(line_glow, (*C_NEON, int(20 * fade_t)),
                             (0, loff), (line_w, loff), 1)
            surface.blit(line_glow, (line_x, line_y - loff))
        line_surf = pygame.Surface((line_w, 2), pygame.SRCALPHA)
        pygame.draw.line(line_surf, (*C_NEON, line_alpha), (0, 0), (line_w, 0), 2)
        surface.blit(line_surf, (line_x, line_y))

        # Subtitle
        sub_text = "OPERACION DEADLOCK -- NEUTRALIZADA"
        sub_surf = self.font_subtitle.render(sub_text, True, C_TEXT_SEC)
        sub_fade = min(1.0, max(0, (self.elapsed - 0.3) / self.fade_in_duration))
        sub_surf.set_alpha(int(255 * sub_fade))
        sx = WIDTH // 2 - sub_surf.get_width() // 2
        surface.blit(sub_surf, (sx, line_y + 10))

    def _draw_score_table(self, surface):
        table_x = WIDTH // 2 - 200
        table_y = 185
        row_h = 40
        table_w = 400
        dot_char = "."

        # Panel background
        panel_h = len(self.row_scores) * row_h + row_h + 36
        panel = pygame.Surface((table_w + 40, panel_h), pygame.SRCALPHA)
        panel.fill((C_PANEL[0], C_PANEL[1], C_PANEL[2], 200))
        pygame.draw.rect(panel, (*C_NEON, 60), panel.get_rect(), 1)
        surface.blit(panel, (table_x - 20, table_y - 10))

        # Individual rows with staggered fade-in
        for i, (name, pts, color) in enumerate(self.row_scores):
            row_fade_start = 0.6 + i * _ROW_FADE_DELAY
            fade_t = min(1.0, max(0, (self.elapsed - row_fade_start) / 0.4))
            if fade_t <= 0:
                continue

            ry = table_y + i * row_h

            # Row accent color left bar (neon line)
            bar_surf = pygame.Surface((3, row_h - 8), pygame.SRCALPHA)
            bar_surf.fill((*color, int(200 * fade_t)))
            surface.blit(bar_surf, (table_x - 16, ry + 2))

            # Thin neon line at bottom of row
            row_line = pygame.Surface((table_w, 1), pygame.SRCALPHA)
            row_line.fill((*color, int(30 * fade_t)))
            surface.blit(row_line, (table_x, ry + row_h - 4))

            # Name with puzzle accent color
            name_surf = self.font_row_name.render(name, True, color)
            name_surf.set_alpha(int(255 * fade_t))
            surface.blit(name_surf, (table_x, ry))

            # Dots
            name_w = name_surf.get_width()
            display_pts = self.displayed_scores[i]
            score_text = f"{display_pts} pts"
            score_surf = self.font_row_score.render(score_text, True, C_TEXT_PRI)
            score_w = score_surf.get_width()
            dot_space = table_w - name_w - score_w - 16
            dot_count = max(0, dot_space // 8)
            dots = self.font_small.render(dot_char * dot_count, True, C_TEXT_HINT)
            dots.set_alpha(int(180 * fade_t))
            surface.blit(dots, (table_x + name_w + 8, ry + 3))

            # Score value (slot machine counting up)
            score_surf.set_alpha(int(255 * fade_t))
            surface.blit(score_surf, (table_x + table_w - score_w, ry))

        # Divider line
        div_fade_start = 0.6 + len(self.row_scores) * _ROW_FADE_DELAY
        div_fade = min(1.0, max(0, (self.elapsed - div_fade_start) / 0.3))
        if div_fade > 0:
            div_y = table_y + len(self.row_scores) * row_h
            # Neon divider
            line_surf = pygame.Surface((table_w, 2), pygame.SRCALPHA)
            line_surf.fill((*C_NEON, int(150 * div_fade)))
            surface.blit(line_surf, (table_x, div_y))
            # Glow
            glow_line = pygame.Surface((table_w, 6), pygame.SRCALPHA)
            glow_line.fill((*C_NEON, int(30 * div_fade)))
            surface.blit(glow_line, (table_x, div_y - 2))

            # Total row
            total_fade_start = div_fade_start + 0.3
            total_fade = min(1.0, max(0, (self.elapsed - total_fade_start) / 0.4))
            if total_fade > 0:
                ty_row = div_y + 12
                self._neon_text(surface, "TOTAL", table_x, ty_row,
                                self.font_total_label, C_NEON)

                total_text = f"{self.displayed_total} pts"
                total_val = self.font_total_val.render(total_text, True, C_WHITE)
                total_val.set_alpha(int(255 * total_fade))
                surface.blit(total_val, (
                    table_x + table_w - total_val.get_width(), ty_row - 3))

    def _draw_rank(self, surface):
        rank_fade_start = 0.6 + (len(self.row_scores) + 1) * _ROW_FADE_DELAY + 0.5
        fade_t = min(1.0, max(0, (self.elapsed - rank_fade_start) / 0.5))
        if fade_t <= 0:
            return

        ry = 430

        # Rank panel with decorative border
        rw = 400
        rh = 90
        rx_panel = WIDTH // 2 - rw // 2
        panel = pygame.Surface((rw, rh), pygame.SRCALPHA)
        panel.fill((C_PANEL[0], C_PANEL[1], C_PANEL[2], int(180 * fade_t)))
        # Decorative double border
        pygame.draw.rect(panel, (*self.rank_color, int(80 * fade_t)),
                         panel.get_rect(), 2)
        inner_rect = panel.get_rect().inflate(-8, -8)
        pygame.draw.rect(panel, (*self.rank_color, int(40 * fade_t)),
                         inner_rect, 1)
        surface.blit(panel, (rx_panel, ry - 10))

        # Corner accents
        corner_len = 12
        for corner in [(rx_panel, ry - 10), (rx_panel + rw, ry - 10),
                       (rx_panel, ry - 10 + rh), (rx_panel + rw, ry - 10 + rh)]:
            cx, cy = corner
            alpha = int(160 * fade_t)
            cs = pygame.Surface((corner_len * 2, corner_len * 2), pygame.SRCALPHA)
            # Draw L-shaped corner
            dx = 1 if cx == rx_panel else -1
            dy = 1 if cy == ry - 10 else -1
            start_x = 0 if dx == 1 else corner_len * 2
            start_y = 0 if dy == 1 else corner_len * 2
            pygame.draw.line(cs, (*self.rank_color, alpha),
                             (start_x, start_y),
                             (start_x + dx * corner_len, start_y), 2)
            pygame.draw.line(cs, (*self.rank_color, alpha),
                             (start_x, start_y),
                             (start_x, start_y + dy * corner_len), 2)
            surface.blit(cs, (cx - corner_len, cy - corner_len))

        # Sub-label above rank
        sub = self.font_rank_sub.render("RANGO ASIGNADO", True, C_TEXT_HINT)
        sub.set_alpha(int(200 * fade_t))
        surface.blit(sub, (WIDTH // 2 - sub.get_width() // 2, ry + 2))

        # Rank name with intense glow
        rank_text = self.rank_name
        rx = WIDTH // 2 - self.font_rank.size(rank_text)[0] // 2
        rank_y = ry + 24

        # Glow intensity based on rank
        glow_intensity = 1.5 if self.total >= 340 else 1.0
        pulse = 0.7 + 0.3 * math.sin(self.glow_timer * 3.0)
        for off in [4, 3, 2, 1]:
            g = self.font_rank.render(rank_text, True, self.rank_color)
            g.set_alpha(int(35 * glow_intensity * pulse * fade_t))
            surface.blit(g, (rx - off, rank_y))
            surface.blit(g, (rx + off, rank_y))
            surface.blit(g, (rx, rank_y - off))
            surface.blit(g, (rx, rank_y + off))
        rank_surf = self.font_rank.render(rank_text, True, self.rank_color)
        rank_surf.set_alpha(int(255 * fade_t))
        surface.blit(rank_surf, (rx, rank_y))

    def _draw_button(self, surface):
        btn_fade_start = 0.6 + (len(self.row_scores) + 2) * _ROW_FADE_DELAY + 0.8
        fade_t = min(1.0, max(0, (self.elapsed - btn_fade_start) / 0.4))
        if fade_t <= 0:
            return

        rect = self.btn_rect
        panel = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        bg_alpha = int((200 if self.btn_hovered else 150) * fade_t)
        panel.fill((C_PANEL[0], C_PANEL[1], C_PANEL[2], bg_alpha))

        border_c = C_WHITE if self.btn_hovered else C_NEON
        bw = 2 if self.btn_hovered else 1
        border_alpha = int(220 * fade_t)
        pygame.draw.rect(panel, (*border_c, border_alpha), panel.get_rect(), bw)
        surface.blit(panel, rect.topleft)

        # Neon glow on hover
        if self.btn_hovered:
            glow_rect = rect.inflate(6, 6)
            glow_surf = pygame.Surface((glow_rect.w, glow_rect.h), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, (*C_NEON, int(30 * fade_t)),
                             glow_surf.get_rect(), 2, border_radius=4)
            surface.blit(glow_surf, glow_rect.topleft)

        btn_text = "VOLVER AL INICIO"
        color = C_WHITE if self.btn_hovered else C_NEON
        lbl = self.font_btn.render(btn_text, True, color)
        lbl.set_alpha(int(255 * fade_t))
        surface.blit(lbl, (
            rect.centerx - lbl.get_width() // 2,
            rect.centery - lbl.get_height() // 2
        ))
