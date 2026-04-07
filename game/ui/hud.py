"""Cyberpunk HUD overlay for DEADLOCK - professional game UI."""
import pygame
import math
from game.constants import WIDTH, C_BG, C_BORDER, C_TEXT_HINT, C_TEXT_SEC, C_ACCENT, C_NEON, C_WHITE


class HUD:
    def __init__(self):
        self.height = 40
        self.font = pygame.font.SysFont("monospace", 13, bold=True)
        self.font_sm = pygame.font.SysFont("monospace", 10)
        self.font_title = pygame.font.SysFont("monospace", 14, bold=True)
        self.scene_name = ""
        self.layer_text = ""
        self.status_text = ""

    def set_info(self, scene_name="", layer_text="", status_text=""):
        self.scene_name = scene_name
        self.layer_text = layer_text
        self.status_text = status_text

    def draw(self, surface):
        t = pygame.time.get_ticks()

        # ── Main bar (semi-transparent dark glass with gradient) ──
        bar = pygame.Surface((WIDTH, self.height), pygame.SRCALPHA)
        # Dark base
        bar.fill((6, 8, 14, 210))
        # Subtle gradient (lighter at top)
        grad = pygame.Surface((WIDTH, self.height // 2), pygame.SRCALPHA)
        grad.fill((20, 24, 36, 30))
        bar.blit(grad, (0, 0))

        # Tiny grid pattern in background
        for gx in range(0, WIDTH, 16):
            pygame.draw.line(bar, (30, 34, 50, 15), (gx, 0), (gx, self.height), 1)
        for gy in range(0, self.height, 8):
            pygame.draw.line(bar, (30, 34, 50, 15), (0, gy), (WIDTH, gy), 1)

        surface.blit(bar, (0, 0))

        # ── Neon accent line at bottom ──
        pulse = int(140 + 60 * math.sin(t * 0.003))
        line_s = pygame.Surface((WIDTH, 2), pygame.SRCALPHA)
        # Gradient line (brighter in center)
        for lx in range(0, WIDTH, 4):
            dist_center = abs(lx - WIDTH // 2) / (WIDTH // 2)
            a = int(pulse * (1 - dist_center * 0.6))
            pygame.draw.line(line_s, (*C_NEON[:3], max(0, min(255, a))),
                             (lx, 0), (lx + 4, 0), 1)
        surface.blit(line_s, (0, self.height - 2))

        # Thin darker line above the neon
        pygame.draw.line(surface, C_BORDER, (0, self.height - 3), (WIDTH, self.height - 3), 1)

        # ── Left section: OPERACION DEADLOCK + signal bars ──
        lx = 16

        # Blinking "LIVE" indicator dot
        live_phase = math.sin(t * 0.005)
        if live_phase > -0.2:
            live_alpha = int(180 + 75 * live_phase)
            live_s = pygame.Surface((8, 8), pygame.SRCALPHA)
            # Glow
            pygame.draw.circle(live_s, (*C_NEON[:3], live_alpha // 3), (4, 4), 4)
            pygame.draw.circle(live_s, (*C_NEON[:3], live_alpha), (4, 4), 2)
            surface.blit(live_s, (lx, 16))
        else:
            pygame.draw.circle(surface, (40, 50, 30), (lx + 4, 20), 2)

        lx += 14

        # Signal bars icon (animated)
        bar_heights = [5, 8, 11, 14]
        for i, bh in enumerate(bar_heights):
            bar_alpha = int(120 + 80 * math.sin(t * 0.004 + i * 0.8))
            bar_s = pygame.Surface((3, bh), pygame.SRCALPHA)
            bar_s.fill((*C_NEON[:3], bar_alpha))
            surface.blit(bar_s, (lx + i * 5, 24 - bh))
        lx += 26

        # Title text with subtle glow
        title = "OPERACION DEADLOCK"
        # Glow layer
        title_glow = self.font_title.render(title, True, C_NEON)
        glow_s = pygame.Surface((title_glow.get_width() + 4, title_glow.get_height() + 4),
                                pygame.SRCALPHA)
        glow_s.blit(title_glow, (2, 2))
        glow_s.set_alpha(30)
        surface.blit(glow_s, (lx - 2, 11))
        # Crisp text
        title_s = self.font_title.render(title, True, C_NEON)
        surface.blit(title_s, (lx, 13))

        # ── Center section: scene name with decorative brackets ──
        if self.scene_name:
            sc = self.font.render(self.scene_name, True, C_WHITE)
            sc_x = WIDTH // 2 - sc.get_width() // 2
            sc_y = 14

            # Pulsing decorative brackets
            bracket_pulse = int(160 + 60 * math.sin(t * 0.004))
            bracket_col = (*C_ACCENT[:3],)
            bracket_font = self.font

            # Left bracket group
            lb1 = bracket_font.render("//", True, (*C_TEXT_HINT[:3],))
            surface.blit(lb1, (sc_x - lb1.get_width() - 12, sc_y))

            lb2_s = pygame.Surface((8, sc.get_height()), pygame.SRCALPHA)
            pygame.draw.line(lb2_s, (*bracket_col, bracket_pulse),
                             (6, 0), (0, sc.get_height() // 2), 1)
            pygame.draw.line(lb2_s, (*bracket_col, bracket_pulse),
                             (0, sc.get_height() // 2), (6, sc.get_height()), 1)
            surface.blit(lb2_s, (sc_x - 10, sc_y))

            # Scene name
            surface.blit(sc, (sc_x, sc_y))

            # Right bracket group
            rb2_s = pygame.Surface((8, sc.get_height()), pygame.SRCALPHA)
            pygame.draw.line(rb2_s, (*bracket_col, bracket_pulse),
                             (2, 0), (8, sc.get_height() // 2), 1)
            pygame.draw.line(rb2_s, (*bracket_col, bracket_pulse),
                             (8, sc.get_height() // 2), (2, sc.get_height()), 1)
            surface.blit(rb2_s, (sc_x + sc.get_width() + 4, sc_y))

            rb1 = bracket_font.render("//", True, (*C_TEXT_HINT[:3],))
            surface.blit(rb1, (sc_x + sc.get_width() + 16, sc_y))

        # ── Right section: layer/progress tech badge + time ──
        rx = WIDTH - 16

        # Mission timer aesthetic
        secs = t // 1000
        mins = secs // 60
        time_str = f"{mins:02d}:{secs % 60:02d}"
        time_s = self.font_sm.render(time_str, True, C_TEXT_SEC)
        rx -= time_s.get_width()
        surface.blit(time_s, (rx, 28))

        # Separator dot
        rx -= 12
        pygame.draw.circle(surface, C_TEXT_HINT, (rx + 4, 22), 1)

        if self.layer_text:
            ly_text = self.font.render(self.layer_text, True, C_ACCENT)
            ly_w = ly_text.get_width()

            # Tech badge (rounded pill with border)
            badge_w = ly_w + 20
            badge_h = 22
            badge_x = rx - badge_w - 4
            badge_y = 11

            # Badge background
            badge_s = pygame.Surface((badge_w, badge_h), pygame.SRCALPHA)
            pygame.draw.rect(badge_s, (20, 30, 45, 140),
                             (0, 0, badge_w, badge_h), border_radius=11)
            # Badge border
            badge_pulse = int(100 + 40 * math.sin(t * 0.003))
            pygame.draw.rect(badge_s, (*C_ACCENT[:3], badge_pulse),
                             (0, 0, badge_w, badge_h), 1, border_radius=11)
            surface.blit(badge_s, (badge_x, badge_y))

            # Badge text
            surface.blit(ly_text, (badge_x + 10, badge_y + 4))
