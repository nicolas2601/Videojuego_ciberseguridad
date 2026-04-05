import pygame
from game.constants import WIDTH, HEIGHT, C_BG, C_BORDER, C_ACCENT, C_TEXT_SEC, C_TEXT_PRI, C_NEON


def _word_wrap(text, font, max_width):
    """Split text into lines that fit within max_width pixels."""
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


class DialogueBox:
    def __init__(self):
        self.messages = []
        self.current_index = 0
        self.char_index = 0
        self.char_timer = 0
        self.char_delay = 0.025
        self.active = False
        self.finished = False
        self.on_complete = None

        self.box_height = 110
        self.box_y = HEIGHT - self.box_height
        self.text_max_width = WIDTH - 80  # padding for word wrap
        self.font_speaker = pygame.font.SysFont("monospace", 14, bold=True)
        self.font_text = pygame.font.SysFont("monospace", 15)
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

        msg = self.messages[self.current_index]
        visible_text = msg["text"][:self.char_index]

        # Word-wrap the visible text
        lines = _word_wrap(visible_text, self.font_text, self.text_max_width)
        line_h = self.font_text.get_linesize()
        needed_h = max(self.box_height, 50 + len(lines) * line_h + 10)
        box_y = HEIGHT - needed_h

        # Solid black background for legibility
        box_surf = pygame.Surface((WIDTH, needed_h), pygame.SRCALPHA)
        box_surf.fill((0, 0, 0, 240))
        pygame.draw.line(box_surf, C_NEON, (0, 0), (WIDTH, 0), 2)
        surface.blit(box_surf, (0, box_y))

        # Speaker name in neon green
        speaker_surf = self.font_speaker.render(msg["speaker"], True, C_NEON)
        surface.blit(speaker_surf, (30, box_y + 12))

        # Text lines - white on black for max legibility
        for i, line in enumerate(lines):
            text_surf = self.font_text.render(line, True, C_TEXT_PRI)
            surface.blit(text_surf, (30, box_y + 34 + i * line_h))

        # Cursor on last line
        if self.char_index < len(msg["text"]) and self.cursor_visible:
            last_line = lines[-1] if lines else ""
            cursor_x = 30 + self.font_text.size(last_line)[0]
            cursor_y = box_y + 34 + (len(lines) - 1) * line_h
            cursor_surf = self.font_text.render("|", True, C_NEON)
            surface.blit(cursor_surf, (cursor_x, cursor_y))

        # Continue indicator
        if self.char_index >= len(msg["text"]):
            hint = self.font_speaker.render("[CLICK / SPACE]", True, C_TEXT_SEC)
            surface.blit(hint, (WIDTH - hint.get_width() - 30, box_y + needed_h - 22))
