import pygame
from game.constants import WIDTH, C_BG, C_BORDER, C_TEXT_HINT, C_TEXT_SEC, C_ACCENT


class HUD:
    def __init__(self):
        self.height = 40
        self.font = pygame.font.SysFont("monospace", 13, bold=True)
        self.scene_name = ""
        self.layer_text = ""
        self.status_text = ""

    def set_info(self, scene_name="", layer_text="", status_text=""):
        self.scene_name = scene_name
        self.layer_text = layer_text
        self.status_text = status_text

    def draw(self, surface):
        bar = pygame.Surface((WIDTH, self.height), pygame.SRCALPHA)
        bar.fill((*C_BG, 220))
        pygame.draw.line(bar, C_BORDER, (0, self.height - 1), (WIDTH, self.height - 1), 1)
        surface.blit(bar, (0, 0))

        # Left - operation name
        op = self.font.render("OPERACION DEADLOCK", True, C_TEXT_HINT)
        surface.blit(op, (16, 12))

        # Center - scene name
        if self.scene_name:
            sc = self.font.render(self.scene_name, True, C_TEXT_SEC)
            surface.blit(sc, (WIDTH // 2 - sc.get_width() // 2, 12))

        # Right - layer/progress
        if self.layer_text:
            ly = self.font.render(self.layer_text, True, C_ACCENT)
            surface.blit(ly, (WIDTH - ly.get_width() - 16, 12))
