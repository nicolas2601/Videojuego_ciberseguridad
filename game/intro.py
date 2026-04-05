import pygame
import random
import math
from game.constants import WIDTH, HEIGHT, C_BG, C_BG2, C_BORDER, C_TEXT_PRI, C_TEXT_SEC, C_TEXT_HINT, C_ACCENT, C_RED, C_GREEN
from game.ui.tile_renderer import get_separate_sprite


class IntroScene:
    def __init__(self, manager):
        self.manager = manager

        # Fonts
        self.font_title = pygame.font.SysFont("monospace", 72, bold=True)
        self.font_subtitle = pygame.font.SysFont("monospace", 18)
        self.font_badge = pygame.font.SysFont("monospace", 12, bold=True)
        self.font_menu = pygame.font.SysFont("monospace", 20, bold=True)
        self.font_hint = pygame.font.SysFont("monospace", 13)

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

        # Pre-render surfaces
        self._build_vignette()
        self._build_scanlines()

        # Load office sprites for background atmosphere
        self._load_bg_sprites()

    def _load_bg_sprites(self):
        """Load and position office furniture sprites for background."""
        self.bg_sprites = []
        sprite_defs = [
            ("Sprite-0002.png", 2, 120, 380),
            ("Sprite-0005.png", 2, 900, 420),
            ("Sprite-0013.png", 2, 60, 200),
            ("Sprite-0013.png", 2, 1140, 250),
            ("Sprite-0021.png", 2, 250, 500),
            ("Sprite-0022.png", 2, 1000, 480),
            ("Sprite-0007.png", 2, 550, 520),
            ("Sprite-0029.png", 2, 400, 560),
        ]
        for name, scale, x, y in sprite_defs:
            try:
                img = get_separate_sprite(name, scale=scale)
                self.bg_sprites.append((img, x, y))
            except Exception:
                pass

    def _build_vignette(self):
        """Create a vignette overlay that darkens edges."""
        self.vignette = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        cx, cy = WIDTH // 2, HEIGHT // 2
        max_dist = math.sqrt(cx * cx + cy * cy)
        # Draw concentric rectangles from outside in with decreasing alpha
        for i in range(40):
            t = i / 40.0
            alpha = int(180 * (1.0 - t) ** 2)
            margin_x = int(t * cx * 0.8)
            margin_y = int(t * cy * 0.8)
            rect = pygame.Rect(margin_x, margin_y,
                               WIDTH - margin_x * 2, HEIGHT - margin_y * 2)
            border_surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            # Only draw border ring
            pygame.draw.rect(border_surf, (0, 0, 0, alpha), border_surf.get_rect(), max(4, 20 - i))
            self.vignette.blit(border_surf, rect.topleft)
        # Extra dark corners
        for corner_x, corner_y in [(0, 0), (WIDTH, 0), (0, HEIGHT), (WIDTH, HEIGHT)]:
            for r in range(200, 50, -10):
                alpha = int(120 * (r / 200))
                pygame.draw.circle(self.vignette, (0, 0, 0, alpha), (corner_x, corner_y), r)

    def _build_scanlines(self):
        """Create a scanline texture that will scroll."""
        # Make it double height so we can scroll seamlessly
        self.scanline_height = HEIGHT * 2
        self.scanlines = pygame.Surface((WIDTH, self.scanline_height), pygame.SRCALPHA)
        for y in range(0, self.scanline_height, 3):
            pygame.draw.line(self.scanlines, (0, 0, 0, 28), (0, y), (WIDTH, y), 1)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.menu_hovered = self.menu_rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.menu_rect.collidepoint(event.pos):
                self.manager.change_scene("hub")

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

    def draw(self, surface):
        # Dark background
        surface.fill(C_BG)

        # Office sprites at low opacity
        sprite_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for img, x, y in self.bg_sprites:
            faded = img.copy()
            faded.set_alpha(30)
            sprite_surf.blit(faded, (x, y))
        surface.blit(sprite_surf, (0, 0))

        # Title "DEADLOCK" with glitch
        title_surf = self.font_title.render("DEADLOCK", True, C_TEXT_PRI)
        title_x = WIDTH // 2 - title_surf.get_width() // 2 + self.glitch_offset_x
        title_y = HEIGHT // 2 - 120
        surface.blit(title_surf, (title_x, title_y))

        # Glitch color artifacts during glitch frames
        if self.glitch_frames_left > 0:
            glitch_r = self.font_title.render("DEADLOCK", True, (200, 60, 60))
            glitch_r.set_alpha(80)
            surface.blit(glitch_r, (title_x + random.randint(-3, 3), title_y + random.randint(-1, 1)))
            glitch_b = self.font_title.render("DEADLOCK", True, (60, 60, 200))
            glitch_b.set_alpha(60)
            surface.blit(glitch_b, (title_x + random.randint(-3, 3), title_y + random.randint(-1, 1)))

        # Subtitle
        sub_surf = self.font_subtitle.render("OPERACION DESCIFRADO \u2014 2031", True, C_TEXT_SEC)
        sub_x = WIDTH // 2 - sub_surf.get_width() // 2
        sub_y = title_y + title_surf.get_height() + 12
        surface.blit(sub_surf, (sub_x, sub_y))

        # Decorative line under subtitle
        line_w = 260
        line_y = sub_y + sub_surf.get_height() + 10
        pygame.draw.line(surface, C_BORDER, (WIDTH // 2 - line_w // 2, line_y),
                         (WIDTH // 2 + line_w // 2, line_y), 1)

        # Top-left badge: CLASIFICADO
        self._draw_badge_left(surface)

        # Top-right badge: CASO #
        self._draw_badge_right(surface)

        # Bottom menu button
        self._draw_menu_button(surface)

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

    def _draw_badge_left(self, surface):
        """Draw CLASIFICADO badge in top-left corner."""
        text = self.font_badge.render("CLASIFICADO", True, C_RED)
        pad_x, pad_y = 10, 5
        bw = text.get_width() + pad_x * 2
        bh = text.get_height() + pad_y * 2
        badge_rect = pygame.Rect(20, 20, bw, bh)

        badge_surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
        badge_surf.fill((40, 12, 12, 200))
        pygame.draw.rect(badge_surf, (*C_RED, 200), badge_surf.get_rect(), 2)
        surface.blit(badge_surf, badge_rect.topleft)
        surface.blit(text, (badge_rect.x + pad_x, badge_rect.y + pad_y))

    def _draw_badge_right(self, surface):
        """Draw case number badge in top-right corner."""
        text = self.font_badge.render("CASO #DL-2031 // OPERACION DEADLOCK", True, C_TEXT_HINT)
        pad_x, pad_y = 10, 5
        bw = text.get_width() + pad_x * 2
        bh = text.get_height() + pad_y * 2
        badge_rect = pygame.Rect(WIDTH - bw - 20, 20, bw, bh)

        badge_surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
        badge_surf.fill((C_BG2[0], C_BG2[1], C_BG2[2], 200))
        pygame.draw.rect(badge_surf, (*C_BORDER, 200), badge_surf.get_rect(), 1)
        surface.blit(badge_surf, badge_rect.topleft)
        surface.blit(text, (badge_rect.x + pad_x, badge_rect.y + pad_y))

    def _draw_menu_button(self, surface):
        """Draw the NUEVA PARTIDA / INICIAR MISION button."""
        # Button background
        border_color = C_ACCENT if self.menu_hovered else C_BORDER
        bg_alpha = 180 if self.menu_hovered else 140

        btn_surf = pygame.Surface((self.menu_rect.w, self.menu_rect.h), pygame.SRCALPHA)
        btn_surf.fill((C_BG2[0], C_BG2[1], C_BG2[2], bg_alpha))
        pygame.draw.rect(btn_surf, (*border_color, 220), btn_surf.get_rect(), 2)
        surface.blit(btn_surf, self.menu_rect.topleft)

        # Label: NUEVA PARTIDA
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
