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
_ROW_FADE_DELAY = 0.3  # seconds between each row fade-in


class _Particle:
    """A single background star / particle."""

    __slots__ = ("x", "y", "vx", "vy", "size", "alpha", "max_alpha", "color")

    def __init__(self):
        self.x = random.uniform(0, WIDTH)
        self.y = random.uniform(0, HEIGHT)
        self.vx = random.uniform(-8, 8)
        self.vy = random.uniform(-12, -3)
        self.size = random.choice([1, 1, 1, 2, 2, 3])
        self.max_alpha = random.randint(60, 160)
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
            self.y = HEIGHT + random.randint(0, 20)
            self.vy = random.uniform(-12, -3)


class EndingScene:
    def __init__(self, manager):
        self.manager = manager

        # Fonts
        self.font_title = pygame.font.SysFont("monospace", 42, bold=True)
        self.font_subtitle = pygame.font.SysFont("monospace", 18)
        self.font_row_name = pygame.font.SysFont("monospace", 17, bold=True)
        self.font_row_score = pygame.font.SysFont("monospace", 17, bold=True)
        self.font_total_label = pygame.font.SysFont("monospace", 20, bold=True)
        self.font_total_val = pygame.font.SysFont("monospace", 26, bold=True)
        self.font_rank = pygame.font.SysFont("monospace", 28, bold=True)
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
        self._build_scanlines()

        # Particles
        self.particles = [_Particle() for _ in range(60)]

        # Glow pulse
        self.glow_timer = 0.0

    def _build_scanlines(self):
        """CRT scanlines effect using only pygame.draw."""
        self.scanline_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for y in range(0, HEIGHT, 3):
            pygame.draw.line(self.scanline_surf, (0, 0, 0, 22), (0, y), (WIDTH, y), 1)

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

        for p in self.particles:
            p.update(dt)

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, surface):
        # Solid black background for legibility
        surface.fill((0, 0, 0))

        # Particles background
        self._draw_particles(surface)

        # Title block
        self._draw_title(surface)

        # Score table
        self._draw_score_table(surface)

        # Rank
        self._draw_rank(surface)

        # Return button
        self._draw_button(surface)

        # CRT scanlines
        surface.blit(self.scanline_surf, (0, 0))

        # HUD
        self.hud.draw(surface)

        # Dialogue
        self.dialogue.draw(surface)

    # ------------------------------------------------------------------
    # Sub-renderers
    # ------------------------------------------------------------------

    def _draw_particles(self, surface):
        for p in self.particles:
            alpha = max(0, min(255, int(p.alpha)))
            color = (*p.color, alpha)
            if p.size <= 1:
                ps = pygame.Surface((2, 2), pygame.SRCALPHA)
                ps.fill(color)
                surface.blit(ps, (int(p.x), int(p.y)))
            else:
                ps = pygame.Surface((p.size * 2, p.size * 2), pygame.SRCALPHA)
                pygame.draw.circle(ps, color, (p.size, p.size), p.size)
                surface.blit(ps, (int(p.x) - p.size, int(p.y) - p.size))

    def _draw_title(self, surface):
        """MISION COMPLETADA with neon glow on solid black."""
        title_text = "MISION COMPLETADA"
        title_surf = self.font_title.render(title_text, True, C_NEON)
        tx = WIDTH // 2 - title_surf.get_width() // 2
        ty = 70

        # Pulsing glow using C_NEON
        glow_alpha = int(40 + 25 * math.sin(self.glow_timer * 2.5))
        glow = self.font_title.render(title_text, True, C_NEON)
        glow.set_alpha(glow_alpha)
        surface.blit(glow, (tx - 2, ty - 1))
        surface.blit(glow, (tx + 2, ty + 1))
        surface.blit(glow, (tx, ty - 2))
        surface.blit(glow, (tx, ty + 2))

        # Fade in title
        fade_t = min(1.0, self.elapsed / self.fade_in_duration)
        title_surf.set_alpha(int(255 * fade_t))
        surface.blit(title_surf, (tx, ty))

        # Decorative line under title
        line_w = title_surf.get_width() + 40
        line_x = WIDTH // 2 - line_w // 2
        line_y = ty + title_surf.get_height() + 4
        line_alpha = int(120 * fade_t)
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
        table_y = 190
        row_h = 36
        table_w = 400
        dot_char = "."

        # Panel background
        panel_h = len(self.row_scores) * row_h + row_h + 30
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

            # Name
            name_surf = self.font_row_name.render(name, True, color)
            name_surf.set_alpha(int(255 * fade_t))
            surface.blit(name_surf, (table_x, ry))

            # Dots
            name_w = name_surf.get_width()
            score_text = f"{pts} pts"
            score_surf = self.font_row_score.render(score_text, True, C_TEXT_PRI)
            score_w = score_surf.get_width()
            dot_space = table_w - name_w - score_w - 16
            dot_count = max(0, dot_space // 8)
            dots = self.font_small.render(dot_char * dot_count, True, C_TEXT_HINT)
            dots.set_alpha(int(180 * fade_t))
            surface.blit(dots, (table_x + name_w + 8, ry + 3))

            # Score value
            score_surf.set_alpha(int(255 * fade_t))
            surface.blit(score_surf, (table_x + table_w - score_w, ry))

        # Divider line
        div_fade_start = 0.6 + len(self.row_scores) * _ROW_FADE_DELAY
        div_fade = min(1.0, max(0, (self.elapsed - div_fade_start) / 0.3))
        if div_fade > 0:
            div_y = table_y + len(self.row_scores) * row_h
            line_surf = pygame.Surface((table_w, 1), pygame.SRCALPHA)
            line_surf.fill((*C_NEON, int(120 * div_fade)))
            surface.blit(line_surf, (table_x, div_y))

            # Total row
            total_fade_start = div_fade_start + 0.3
            total_fade = min(1.0, max(0, (self.elapsed - total_fade_start) / 0.4))
            if total_fade > 0:
                ty = div_y + 10
                total_label = self.font_total_label.render("TOTAL", True, C_NEON)
                total_label.set_alpha(int(255 * total_fade))
                surface.blit(total_label, (table_x, ty))

                total_val = self.font_total_val.render(
                    f"{self.total} pts", True, C_WHITE)
                total_val.set_alpha(int(255 * total_fade))
                surface.blit(total_val, (
                    table_x + table_w - total_val.get_width(), ty - 3))

    def _draw_rank(self, surface):
        rank_fade_start = 0.6 + (len(self.row_scores) + 1) * _ROW_FADE_DELAY + 0.5
        fade_t = min(1.0, max(0, (self.elapsed - rank_fade_start) / 0.5))
        if fade_t <= 0:
            return

        ry = 430

        # Rank panel background
        rw = 400
        rh = 80
        rx_panel = WIDTH // 2 - rw // 2
        panel = pygame.Surface((rw, rh), pygame.SRCALPHA)
        panel.fill((C_PANEL[0], C_PANEL[1], C_PANEL[2], int(180 * fade_t)))
        pygame.draw.rect(panel, (*self.rank_color, int(80 * fade_t)),
                         panel.get_rect(), 1)
        surface.blit(panel, (rx_panel, ry - 10))

        # Sub-label above rank
        sub = self.font_rank_sub.render("RANGO ASIGNADO", True, C_TEXT_HINT)
        sub.set_alpha(int(200 * fade_t))
        surface.blit(sub, (WIDTH // 2 - sub.get_width() // 2, ry))

        # Rank name
        rank_surf = self.font_rank.render(self.rank_name, True, self.rank_color)
        rank_surf.set_alpha(int(255 * fade_t))
        rx = WIDTH // 2 - rank_surf.get_width() // 2
        surface.blit(rank_surf, (rx, ry + 22))

        # Glow for high rank
        if self.total >= 340:
            glow_a = int(30 + 20 * math.sin(self.glow_timer * 3.0))
            glow = self.font_rank.render(self.rank_name, True, self.rank_color)
            glow.set_alpha(int(glow_a * fade_t))
            surface.blit(glow, (rx - 1, ry + 21))
            surface.blit(glow, (rx + 1, ry + 23))

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

        lbl = self.font_btn.render("VOLVER AL INICIO", True,
                                   C_WHITE if self.btn_hovered else C_NEON)
        lbl.set_alpha(int(255 * fade_t))
        surface.blit(lbl, (
            rect.centerx - lbl.get_width() // 2,
            rect.centery - lbl.get_height() // 2
        ))
