import pygame
import random
import math
from game.constants import (WIDTH, HEIGHT, C_BG, C_BG2, C_BORDER, C_TEXT_PRI, C_TEXT_SEC,
    C_TEXT_HINT, C_ACCENT, C_RED, C_GREEN, C_NEON, C_WHITE, C_PANEL,
    DIFFICULTY_DUMMY, DIFFICULTY_MID, DIFFICULTY_SENIOR, DIFFICULTY_NOOB,
    DIFFICULTY_NAMES, DIFFICULTY_DESC)
from game.ui.draw_assets import (draw_desk, draw_monitor, draw_chair, draw_plant,
    draw_filing_cabinet, draw_office_floor, draw_wall, draw_text_box)


# Difficulty button colors
_DIFF_COLORS = {
    DIFFICULTY_DUMMY:  (74, 180, 90),    # Green
    DIFFICULTY_MID:    (74, 130, 200),    # Blue
    DIFFICULTY_SENIOR: (200, 170, 60),    # Amber
    DIFFICULTY_NOOB:   (200, 60, 60),     # Red
}

_PHASE_MAIN = 0
_PHASE_DIFFICULTY = 1


class IntroScene:
    def __init__(self, manager):
        self.manager = manager

        # Fonts
        self.font_title = pygame.font.SysFont("monospace", 72, bold=True)
        self.font_subtitle = pygame.font.SysFont("monospace", 18)
        self.font_badge = pygame.font.SysFont("monospace", 12, bold=True)
        self.font_menu = pygame.font.SysFont("monospace", 20, bold=True)
        self.font_hint = pygame.font.SysFont("monospace", 13)
        self.font_diff_name = pygame.font.SysFont("monospace", 22, bold=True)
        self.font_diff_desc = pygame.font.SysFont("monospace", 13)
        self.font_diff_title = pygame.font.SysFont("monospace", 28, bold=True)

        # Scene phase
        self.phase = _PHASE_MAIN

        # Fade-in
        self.fade_timer = 0.0
        self.fade_duration = 1.2
        self.fade_alpha = 255

        # Glitch effect
        self.glitch_timer = 0.0
        self.glitch_interval = random.uniform(4.0, 6.0)
        self.glitch_frames_left = 0
        self.glitch_offset_x = 0

        # CRT scanlines scroll
        self.scanline_offset = 0.0

        # Menu blink
        self.blink_timer = 0.0
        self.blink_cycle = 1.2
        self.menu_visible = True

        # Menu button rect
        self.menu_rect = pygame.Rect(0, 0, 300, 50)
        self.menu_rect.centerx = WIDTH // 2
        self.menu_rect.centery = HEIGHT - 140
        self.menu_hovered = False

        # Difficulty buttons (built once, positioned in center)
        self.diff_buttons = []
        self.diff_hovered = -1
        self._build_difficulty_buttons()

        # Pre-render surfaces
        self._build_vignette()
        self._build_scanlines()

    # ── Difficulty button layout ───────────────────────────────────

    def _build_difficulty_buttons(self):
        """Create rects for the 4 difficulty options."""
        btn_w, btn_h = 480, 56
        start_y = 240
        gap = 16
        self.diff_buttons = []
        for i, diff in enumerate([DIFFICULTY_DUMMY, DIFFICULTY_MID,
                                  DIFFICULTY_SENIOR, DIFFICULTY_NOOB]):
            r = pygame.Rect(0, 0, btn_w, btn_h)
            r.centerx = WIDTH // 2
            r.y = start_y + i * (btn_h + gap)
            self.diff_buttons.append((r, diff))

    # ── Pre-built surfaces ─────────────────────────────────────────

    def _build_vignette(self):
        """Create a vignette overlay that darkens edges."""
        self.vignette = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        cx, cy = WIDTH // 2, HEIGHT // 2
        for i in range(40):
            t = i / 40.0
            alpha = int(180 * (1.0 - t) ** 2)
            margin_x = int(t * cx * 0.8)
            margin_y = int(t * cy * 0.8)
            rect = pygame.Rect(margin_x, margin_y,
                               WIDTH - margin_x * 2, HEIGHT - margin_y * 2)
            border_surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            pygame.draw.rect(border_surf, (0, 0, 0, alpha),
                             border_surf.get_rect(), max(4, 20 - i))
            self.vignette.blit(border_surf, rect.topleft)
        for corner_x, corner_y in [(0, 0), (WIDTH, 0), (0, HEIGHT), (WIDTH, HEIGHT)]:
            for r in range(200, 50, -10):
                alpha = int(120 * (r / 200))
                pygame.draw.circle(self.vignette, (0, 0, 0, alpha),
                                   (corner_x, corner_y), r)

    def _build_scanlines(self):
        """Create a scanline texture that will scroll."""
        self.scanline_height = HEIGHT * 2
        self.scanlines = pygame.Surface((WIDTH, self.scanline_height), pygame.SRCALPHA)
        for y in range(0, self.scanline_height, 3):
            pygame.draw.line(self.scanlines, (0, 0, 0, 28),
                             (0, y), (WIDTH, y), 1)

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
                self.phase = _PHASE_DIFFICULTY
                self.diff_hovered = -1

    def _handle_difficulty_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.diff_hovered = -1
            for i, (r, _) in enumerate(self.diff_buttons):
                if r.collidepoint(event.pos):
                    self.diff_hovered = i
                    break
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, (r, diff) in enumerate(self.diff_buttons):
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

        # Glitch
        self.glitch_timer += dt
        if self.glitch_frames_left > 0:
            self.glitch_offset_x = random.randint(-2, 2)
            self.glitch_frames_left -= 1
            if self.glitch_frames_left <= 0:
                self.glitch_offset_x = 0
                self.glitch_timer = 0.0
                self.glitch_interval = random.uniform(4.0, 6.0)
        elif self.glitch_timer >= self.glitch_interval:
            self.glitch_frames_left = 3

        # Scanline scroll
        self.scanline_offset += dt * 30.0
        if self.scanline_offset >= HEIGHT:
            self.scanline_offset -= HEIGHT

        # Menu blink
        self.blink_timer += dt
        if self.blink_timer >= self.blink_cycle:
            self.blink_timer -= self.blink_cycle
        self.menu_visible = self.blink_timer < (self.blink_cycle * 0.65)

    # ── Draw ───────────────────────────────────────────────────────

    def draw(self, surface):
        # Dark background with office floor
        draw_office_floor(surface)

        # Wall at top
        draw_wall(surface, 0, wall_h=80)

        # Office furniture at low opacity
        furniture_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        furniture_surf.set_alpha(35)
        draw_desk(furniture_surf, 100, 360, w=110, h=50)
        draw_monitor(furniture_surf, 120, 320)
        draw_chair(furniture_surf, 160, 420)
        draw_desk(furniture_surf, 860, 400, w=110, h=50)
        draw_monitor(furniture_surf, 880, 360)
        draw_chair(furniture_surf, 940, 460)
        draw_plant(furniture_surf, 50, 200)
        draw_plant(furniture_surf, 1180, 240)
        draw_filing_cabinet(furniture_surf, 240, 500)
        draw_filing_cabinet(furniture_surf, 1000, 480)
        surface.blit(furniture_surf, (0, 0))

        if self.phase == _PHASE_MAIN:
            self._draw_main(surface)
        elif self.phase == _PHASE_DIFFICULTY:
            self._draw_difficulty(surface)

        # Scanlines overlay
        scan_y = -int(self.scanline_offset)
        surface.blit(self.scanlines, (0, scan_y))

        # Vignette overlay
        surface.blit(self.vignette, (0, 0))

        # Fade-in overlay
        if self.fade_alpha > 0:
            fade_surf = pygame.Surface((WIDTH, HEIGHT))
            fade_surf.fill((0, 0, 0))
            fade_surf.set_alpha(self.fade_alpha)
            surface.blit(fade_surf, (0, 0))

    # ── Main screen draw ───────────────────────────────────────────

    def _draw_main(self, surface):
        # Title "DEADLOCK" with glitch
        title_surf = self.font_title.render("DEADLOCK", True, C_NEON)
        title_w = title_surf.get_width()
        title_h = title_surf.get_height()
        title_x = WIDTH // 2 - title_w // 2 + self.glitch_offset_x
        title_y = HEIGHT // 2 - 120

        # Black box behind title for legibility
        title_bg = pygame.Surface((title_w + 40, title_h + 10), pygame.SRCALPHA)
        title_bg.fill((0, 0, 0, 210))
        surface.blit(title_bg, (WIDTH // 2 - title_w // 2 - 20, title_y - 5))

        surface.blit(title_surf, (title_x, title_y))

        # Glitch color artifacts during glitch frames
        if self.glitch_frames_left > 0:
            glitch_r = self.font_title.render("DEADLOCK", True, (200, 60, 60))
            glitch_r.set_alpha(80)
            surface.blit(glitch_r, (title_x + random.randint(-3, 3),
                                    title_y + random.randint(-1, 1)))
            glitch_b = self.font_title.render("DEADLOCK", True, (60, 60, 200))
            glitch_b.set_alpha(60)
            surface.blit(glitch_b, (title_x + random.randint(-3, 3),
                                    title_y + random.randint(-1, 1)))

        # Subtitle on black box
        sub_text = "OPERACION DESCIFRADO \u2014 2031"
        sub_surf = self.font_subtitle.render(sub_text, True, C_TEXT_SEC)
        sub_x = WIDTH // 2 - sub_surf.get_width() // 2
        sub_y = title_y + title_h + 12

        sub_bg = pygame.Surface((sub_surf.get_width() + 20, sub_surf.get_height() + 8),
                                pygame.SRCALPHA)
        sub_bg.fill((0, 0, 0, 200))
        surface.blit(sub_bg, (sub_x - 10, sub_y - 4))
        surface.blit(sub_surf, (sub_x, sub_y))

        # Decorative line under subtitle
        line_w = 260
        line_y = sub_y + sub_surf.get_height() + 10
        pygame.draw.line(surface, C_BORDER,
                         (WIDTH // 2 - line_w // 2, line_y),
                         (WIDTH // 2 + line_w // 2, line_y), 1)

        # Top-left badge: CLASIFICADO
        self._draw_badge_left(surface)

        # Top-right badge: CASO #DL-2031
        self._draw_badge_right(surface)

        # Bottom menu button
        self._draw_menu_button(surface)

    # ── Difficulty selection screen ────────────────────────────────

    def _draw_difficulty(self, surface):
        # Dark overlay to dim the background
        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 160))
        surface.blit(dim, (0, 0))

        # Title: SELECCIONAR DIFICULTAD on black box
        title_text = "SELECCIONAR DIFICULTAD"
        title_surf = self.font_diff_title.render(title_text, True, C_NEON)
        tx = WIDTH // 2 - title_surf.get_width() // 2
        ty = 160

        draw_text_box(surface, title_text, tx - 12, ty - 6,
                      self.font_diff_title, color=C_NEON, bg_alpha=230, padding=10)

        # Decorative line
        line_y = ty + title_surf.get_height() + 18
        pygame.draw.line(surface, C_BORDER,
                         (WIDTH // 2 - 200, line_y),
                         (WIDTH // 2 + 200, line_y), 1)

        # Draw each difficulty button
        for i, (rect, diff) in enumerate(self.diff_buttons):
            hovered = (i == self.diff_hovered)
            color = _DIFF_COLORS[diff]
            name = DIFFICULTY_NAMES[diff]
            desc = DIFFICULTY_DESC[diff]
            self._draw_diff_button(surface, rect, name, desc, color, hovered)

        # Back hint at bottom
        hint_text = "Haz clic en una dificultad para comenzar"
        hint_surf = self.font_hint.render(hint_text, True, C_TEXT_HINT)
        hx = WIDTH // 2 - hint_surf.get_width() // 2
        hy = self.diff_buttons[-1][0].bottom + 30

        hint_bg = pygame.Surface((hint_surf.get_width() + 16, hint_surf.get_height() + 8),
                                 pygame.SRCALPHA)
        hint_bg.fill((0, 0, 0, 180))
        surface.blit(hint_bg, (hx - 8, hy - 4))
        surface.blit(hint_surf, (hx, hy))

    def _draw_diff_button(self, surface, rect, name, desc, color, hovered):
        """Draw a single difficulty button with hover effect."""
        # Background
        bg_alpha = 220 if hovered else 180
        btn_surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        btn_surf.fill((0, 0, 0, bg_alpha))

        # Border — thicker and colored when hovered
        border_w = 2 if not hovered else 3
        border_color = color if hovered else (color[0] // 2, color[1] // 2, color[2] // 2)
        pygame.draw.rect(btn_surf, (*border_color, 255),
                         btn_surf.get_rect(), border_w)

        # Hover glow bar on left edge
        if hovered:
            pygame.draw.rect(btn_surf, (*color, 255), (0, 0, 4, rect.h))

        surface.blit(btn_surf, rect.topleft)

        # Name label
        name_color = color if hovered else C_TEXT_PRI
        name_surf = self.font_diff_name.render(f"[ {name} ]", True, name_color)
        nx = rect.x + 24
        ny = rect.y + 8
        surface.blit(name_surf, (nx, ny))

        # Description
        desc_color = C_TEXT_SEC if not hovered else C_WHITE
        desc_surf = self.font_diff_desc.render(desc, True, desc_color)
        dx = rect.x + 24
        dy = rect.y + 34
        surface.blit(desc_surf, (dx, dy))

    # ── Badges ─────────────────────────────────────────────────────

    def _draw_badge_left(self, surface):
        """Draw CLASIFICADO badge in top-left corner."""
        text = self.font_badge.render("CLASIFICADO", True, C_RED)
        pad_x, pad_y = 10, 5
        bw = text.get_width() + pad_x * 2
        bh = text.get_height() + pad_y * 2
        badge_rect = pygame.Rect(20, 20, bw, bh)

        badge_surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
        badge_surf.fill((0, 0, 0, 220))
        pygame.draw.rect(badge_surf, (*C_RED, 200), badge_surf.get_rect(), 2)
        surface.blit(badge_surf, badge_rect.topleft)
        surface.blit(text, (badge_rect.x + pad_x, badge_rect.y + pad_y))

    def _draw_badge_right(self, surface):
        """Draw case number badge in top-right corner."""
        text = self.font_badge.render("CASO #DL-2031", True, C_TEXT_HINT)
        pad_x, pad_y = 10, 5
        bw = text.get_width() + pad_x * 2
        bh = text.get_height() + pad_y * 2
        badge_rect = pygame.Rect(WIDTH - bw - 20, 20, bw, bh)

        badge_surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
        badge_surf.fill((0, 0, 0, 220))
        pygame.draw.rect(badge_surf, (*C_BORDER, 200), badge_surf.get_rect(), 1)
        surface.blit(badge_surf, badge_rect.topleft)
        surface.blit(text, (badge_rect.x + pad_x, badge_rect.y + pad_y))

    # ── Menu button ────────────────────────────────────────────────

    def _draw_menu_button(self, surface):
        """Draw the NUEVA PARTIDA button."""
        border_color = C_ACCENT if self.menu_hovered else C_BORDER
        bg_alpha = 220 if self.menu_hovered else 190

        btn_surf = pygame.Surface((self.menu_rect.w, self.menu_rect.h), pygame.SRCALPHA)
        btn_surf.fill((0, 0, 0, bg_alpha))
        pygame.draw.rect(btn_surf, (*border_color, 220), btn_surf.get_rect(), 2)
        surface.blit(btn_surf, self.menu_rect.topleft)

        label = self.font_menu.render("[ NUEVA PARTIDA ]", True, C_TEXT_PRI)
        lx = self.menu_rect.centerx - label.get_width() // 2
        ly = self.menu_rect.centery - label.get_height() // 2
        surface.blit(label, (lx, ly))

        # Blinking "INICIAR MISION" below button
        if self.menu_visible:
            blink_surf = self.font_hint.render("INICIAR MISION", True, C_ACCENT)
            bx = WIDTH // 2 - blink_surf.get_width() // 2
            by = self.menu_rect.bottom + 14
            surface.blit(blink_surf, (bx, by))
