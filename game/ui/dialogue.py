import pygame
from game.constants import WIDTH, HEIGHT, C_BG, C_BORDER, C_ACCENT, C_TEXT_SEC, C_TEXT_PRI


class DialogueBox:
    def __init__(self):
        self.messages = []
        self.current_index = 0
        self.char_index = 0
        self.char_timer = 0
        self.char_delay = 0.025  # seconds per character
        self.active = False
        self.finished = False
        self.on_complete = None

        self.box_height = 100
        self.box_y = HEIGHT - self.box_height
        self.font_speaker = pygame.font.SysFont("monospace", 14, bold=True)
        self.font_text = pygame.font.SysFont("monospace", 16)
        self.cursor_visible = True
        self.cursor_timer = 0

    def show(self, messages, on_complete=None):
        self.messages = messages
        self.current_index = 0
        self.char_index = 0
        self.char_timer = 0
        self.active = True
        self.finished = False
        self.on_complete = on_complete

    def advance(self):
        if not self.active:
            return
        msg = self.messages[self.current_index]
        full_len = len(msg["text"])
        if self.char_index < full_len:
            self.char_index = full_len
        else:
            self.current_index += 1
            self.char_index = 0
            self.char_timer = 0
            if self.current_index >= len(self.messages):
                self.active = False
                self.finished = True
                if self.on_complete:
                    self.on_complete()

    def handle_event(self, event):
        if not self.active:
            return False
        if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1) or (
            event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE)
        ):
            self.advance()
            return True
        return False

    def update(self, dt):
        if not self.active or self.current_index >= len(self.messages):
            return
        msg = self.messages[self.current_index]
        full_len = len(msg["text"])
        if self.char_index < full_len:
            self.char_timer += dt
            while self.char_timer >= self.char_delay and self.char_index < full_len:
                self.char_timer -= self.char_delay
                self.char_index += 1
        self.cursor_timer += dt
        if self.cursor_timer > 0.5:
            self.cursor_visible = not self.cursor_visible
            self.cursor_timer = 0

    def draw(self, surface):
        if not self.active or self.current_index >= len(self.messages):
            return

        # Background
        box_surf = pygame.Surface((WIDTH, self.box_height), pygame.SRCALPHA)
        box_surf.fill((*C_BG, 240))
        pygame.draw.line(box_surf, C_BORDER, (0, 0), (WIDTH, 0), 2)
        surface.blit(box_surf, (0, self.box_y))

        msg = self.messages[self.current_index]
        # Speaker name
        speaker_surf = self.font_speaker.render(msg["speaker"], True, C_ACCENT)
        surface.blit(speaker_surf, (30, self.box_y + 14))

        # Text with typewriter
        visible_text = msg["text"][:self.char_index]
        text_surf = self.font_text.render(visible_text, True, C_TEXT_PRI)
        surface.blit(text_surf, (30, self.box_y + 40))

        # Cursor
        if self.char_index < len(msg["text"]) and self.cursor_visible:
            cursor_x = 30 + text_surf.get_width()
            cursor_surf = self.font_text.render("|", True, C_ACCENT)
            surface.blit(cursor_surf, (cursor_x, self.box_y + 40))

        # Continue indicator
        if self.char_index >= len(msg["text"]):
            hint = self.font_speaker.render("[CLICK para continuar]", True, C_TEXT_SEC)
            surface.blit(hint, (WIDTH - hint.get_width() - 30, self.box_y + 70))
