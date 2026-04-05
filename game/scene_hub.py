import pygame
from game.constants import (WIDTH, HEIGHT, C_BG, C_BG2, C_BG3, C_BORDER, C_TEXT_PRI,
    C_TEXT_SEC, C_TEXT_HINT, C_ACCENT, C_GREEN, C_RED, C_PANEL, C_WHITE, PUZZLE_SCENES)
from game.ui.tile_renderer import draw_floor, get_separate_sprite
from game.ui.dialogue import DialogueBox
from game.ui.hud import HUD


# Door layout positions (x, y) for 4 puzzle rooms + exit
_DOOR_POSITIONS = {
    "caesar":        (140,  160),
    "base64":        (740,  160),
    "hash":          (140,  420),
    "diffie_hellman": (740, 420),
}
_EXIT_POS = (440, 310)
_DOOR_W = 360
_DOOR_H = 180
_EXIT_W = 360
_EXIT_H = 80


class HubScene:
    def __init__(self, manager):
        self.manager = manager

        # Fonts
        self.font_name = pygame.font.SysFont("monospace", 20, bold=True)
        self.font_sub = pygame.font.SysFont("monospace", 14)
        self.font_status = pygame.font.SysFont("monospace", 13, bold=True)
        self.font_icon = pygame.font.SysFont("monospace", 28, bold=True)
        self.font_count = pygame.font.SysFont("monospace", 14, bold=True)

        # HUD
        self.hud = HUD()
        completed = len(manager.completed_scenes & {"caesar", "base64", "hash", "diffie_hellman"})
        self.hud.set_info(
            scene_name="SEDE PRINCIPAL",
            layer_text=f"SALAS: {completed}/4"
        )

        # Dialogue
        self.dialogue = DialogueBox()
        self._show_initial_dialogue()

        # Build door rects
        self.door_rects = {}
        for key, (dx, dy) in _DOOR_POSITIONS.items():
            self.door_rects[key] = pygame.Rect(dx, dy, _DOOR_W, _DOOR_H)

        # Exit door (only shown when all complete)
        self.exit_rect = pygame.Rect(_EXIT_POS[0], _EXIT_POS[1], _EXIT_W, _EXIT_H)

        self.hovered_door = None

        # Pre-render floor
        self.floor_surf = pygame.Surface((WIDTH, HEIGHT))
        draw_floor(self.floor_surf, tile_col=0, tile_row=0)
        # Darken the floor
        dark = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dark.fill((0, 0, 0, 160))
        self.floor_surf.blit(dark, (0, 0))

        # Load decorative office sprites
        self._load_decor()

    def _load_decor(self):
        """Load decorative sprites placed between doors."""
        self.decor_sprites = []
        decor_defs = [
            ("Sprite-0002.png", 2, 560, 200),
            ("Sprite-0021.png", 2, 110, 360),
            ("Sprite-0022.png", 2, 1130, 360),
            ("Sprite-0007.png", 2, 660, 560),
            ("Sprite-0005.png", 2, 440, 560),
        ]
        for name, scale, x, y in decor_defs:
            try:
                img = get_separate_sprite(name, scale=scale)
                self.decor_sprites.append((img, x, y))
            except Exception:
                pass

    def _show_initial_dialogue(self):
        """Show welcome or all-done dialogue."""
        if self.manager.all_puzzles_complete():
            msgs = self.manager.dialogues.get("hub", {}).get("all_done", [])
        else:
            msgs = self.manager.dialogues.get("hub", {}).get("enter", [])
        if msgs:
            self.dialogue.show(msgs)

    def handle_event(self, event):
        # Dialogue takes priority
        if self.dialogue.active:
            self.dialogue.handle_event(event)
            return

        if event.type == pygame.MOUSEMOTION:
            self.hovered_door = None
            for key, rect in self.door_rects.items():
                if rect.collidepoint(event.pos):
                    self.hovered_door = key
                    break
            if self.manager.all_puzzles_complete() and self.exit_rect.collidepoint(event.pos):
                self.hovered_door = "__exit__"

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for key, rect in self.door_rects.items():
                if rect.collidepoint(event.pos):
                    self.manager.change_scene(key)
                    return
            if self.manager.all_puzzles_complete() and self.exit_rect.collidepoint(event.pos):
                self.manager.change_scene("ending")

    def update(self, dt):
        self.dialogue.update(dt)

        # Update HUD count
        completed = len(self.manager.completed_scenes & {"caesar", "base64", "hash", "diffie_hellman"})
        self.hud.set_info(
            scene_name="SEDE PRINCIPAL",
            layer_text=f"SALAS: {completed}/4"
        )

    def draw(self, surface):
        # Floor background
        surface.blit(self.floor_surf, (0, 0))

        # Decorative sprites
        for img, x, y in self.decor_sprites:
            faded = img.copy()
            faded.set_alpha(50)
            surface.blit(faded, (x, y))

        # Draw puzzle doors
        for key, rect in self.door_rects.items():
            self._draw_door(surface, key, rect)

        # Draw exit door if all puzzles complete
        if self.manager.all_puzzles_complete():
            self._draw_exit_door(surface)

        # HUD
        self.hud.draw(surface)

        # Dialogue on top
        self.dialogue.draw(surface)

    def _draw_door(self, surface, key, rect):
        """Draw a single puzzle door."""
        info = PUZZLE_SCENES[key]
        is_completed = key in self.manager.completed_scenes
        is_hovered = (self.hovered_door == key)
        color = info["color"]

        # Panel background
        panel = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        panel.fill((C_PANEL[0], C_PANEL[1], C_PANEL[2], 210))

        # Border - brighter on hover
        if is_hovered:
            border_color = tuple(min(c + 60, 255) for c in color)
            border_width = 3
        else:
            border_color = color
            border_width = 2
        pygame.draw.rect(panel, (*border_color, 220), panel.get_rect(), border_width)

        # Top accent line
        pygame.draw.line(panel, (*color, 180), (0, 0), (rect.w, 0), 3)

        surface.blit(panel, rect.topleft)

        # Icon number in top-left of door
        icon_text = self.font_icon.render(info["icon"], True, color)
        surface.blit(icon_text, (rect.x + 16, rect.y + 14))

        # Room name
        name_surf = self.font_name.render(info["name"], True, C_TEXT_PRI)
        surface.blit(name_surf, (rect.x + 60, rect.y + 20))

        # Subtitle
        sub_surf = self.font_sub.render(info["subtitle"], True, C_TEXT_SEC)
        surface.blit(sub_surf, (rect.x + 60, rect.y + 48))

        # Divider line
        div_y = rect.y + 76
        pygame.draw.line(surface, (*C_BORDER, 120), (rect.x + 16, div_y),
                         (rect.x + rect.w - 16, div_y), 1)

        # Status and icon
        if is_completed:
            status_text = "COMPLETADA"
            status_color = C_GREEN
            # Checkmark drawn with lines
            cx = rect.x + 30
            cy = rect.y + 110
            pygame.draw.line(surface, C_GREEN, (cx, cy), (cx + 8, cy + 8), 3)
            pygame.draw.line(surface, C_GREEN, (cx + 8, cy + 8), (cx + 20, cy - 6), 3)
        else:
            status_text = "DISPONIBLE"
            status_color = C_ACCENT
            # Lock icon drawn with rect + arc
            lx = rect.x + 26
            ly = rect.y + 100
            # Lock body
            pygame.draw.rect(surface, C_ACCENT, (lx, ly + 8, 16, 12), 2)
            # Lock shackle
            pygame.draw.arc(surface, C_ACCENT, (lx + 2, ly, 12, 14), 0, 3.14, 2)

        status_surf = self.font_status.render(status_text, True, status_color)
        surface.blit(status_surf, (rect.x + 56, rect.y + 104))

        # Hover hint
        if is_hovered and not is_completed:
            hint = self.font_sub.render("[CLICK para entrar]", True, C_TEXT_HINT)
            surface.blit(hint, (rect.x + rect.w - hint.get_width() - 16, rect.y + rect.h - 30))
        elif is_hovered and is_completed:
            hint = self.font_sub.render("[Repetir sala]", True, C_TEXT_HINT)
            surface.blit(hint, (rect.x + rect.w - hint.get_width() - 16, rect.y + rect.h - 30))

    def _draw_exit_door(self, surface):
        """Draw the EXIT door when all puzzles are complete."""
        rect = self.exit_rect
        is_hovered = (self.hovered_door == "__exit__")

        panel = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        panel.fill((C_PANEL[0], C_PANEL[1], C_PANEL[2], 220))

        border_color = C_GREEN if not is_hovered else (120, 200, 130)
        border_w = 3 if is_hovered else 2
        pygame.draw.rect(panel, border_color, panel.get_rect(), border_w)
        pygame.draw.line(panel, C_GREEN, (0, 0), (rect.w, 0), 3)

        surface.blit(panel, rect.topleft)

        # EXIT label
        exit_label = self.font_name.render("SALIDA  >>  INFORME FINAL", True, C_GREEN)
        lx = rect.centerx - exit_label.get_width() // 2
        ly = rect.centery - exit_label.get_height() // 2
        surface.blit(exit_label, (lx, ly))

        if is_hovered:
            hint = self.font_sub.render("[CLICK para finalizar]", True, C_TEXT_HINT)
            surface.blit(hint, (rect.right - hint.get_width() - 12, rect.bottom - 22))
