"""Cinematic dialogue system for DEADLOCK - glassmorphism panels with
animated borders, speaker avatars, typewriter text, and audio visualizer."""
import pygame
import math
import random
from game.constants import WIDTH, HEIGHT, C_BG, C_BORDER, C_ACCENT, C_TEXT_SEC, C_TEXT_PRI, C_NEON

C_CYBER_BLUE = (0, 180, 255)


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


def _draw_speaker_avatar(surface, x, y, speaker, t):
    """Draw an abstract geometric face/icon with subtle glitch effect."""
    size = 40
    av_s = pygame.Surface((size, size), pygame.SRCALPHA)

    # Background hexagon
    cx, cy = size // 2, size // 2
    pts = []
    for i in range(6):
        angle = math.radians(60 * i - 30)
        pts.append((cx + int(16 * math.cos(angle)), cy + int(16 * math.sin(angle))))
    pygame.draw.polygon(av_s, (15, 20, 30, 200), pts)
    pygame.draw.polygon(av_s, (*C_NEON[:3], 120), pts, 1)

    # Inner face geometry - abstract cyberpunk portrait
    # "Eyes" - two horizontal lines
    eye_y = cy - 4
    eye_pulse = int(180 + 60 * math.sin(t * 0.006))
    pygame.draw.line(av_s, (*C_NEON[:3], eye_pulse), (cx - 8, eye_y), (cx - 3, eye_y), 2)
    pygame.draw.line(av_s, (*C_NEON[:3], eye_pulse), (cx + 3, eye_y), (cx + 8, eye_y), 2)

    # "Mouth" - thin line
    mouth_w = int(6 + 2 * math.sin(t * 0.004))
    pygame.draw.line(av_s, (*C_CYBER_BLUE[:3], 140),
                     (cx - mouth_w, cy + 6), (cx + mouth_w, cy + 6), 1)

    # Vertical accent line (nose)
    pygame.draw.line(av_s, (*C_NEON[:3], 60), (cx, cy - 2), (cx, cy + 3), 1)

    # Glitch effect (occasional horizontal displacement)
    glitch_phase = math.sin(t * 0.01)
    if glitch_phase > 0.92:
        # Displace a strip
        gy = random.randint(5, size - 10)
        gh = random.randint(2, 5)
        gx_shift = random.randint(-3, 3)
        strip = av_s.subsurface((0, gy, size, gh)).copy()
        av_s.fill((0, 0, 0, 0), (0, gy, size, gh))
        av_s.blit(strip, (gx_shift, gy))

    surface.blit(av_s, (x, y))


def _draw_waveform(surface, x, y, w, h, t, active=True):
    """Audio waveform visualizer next to speaker name."""
    wave_s = pygame.Surface((w, h), pygame.SRCALPHA)
    num_bars = w // 3

    for i in range(num_bars):
        if active:
            bar_h = int(2 + (h - 4) * abs(math.sin(t * 0.008 + i * 0.7)))
            alpha = int(120 + 80 * abs(math.sin(t * 0.006 + i * 0.5)))
        else:
            bar_h = 2
            alpha = 40

        bar_y = (h - bar_h) // 2
        pygame.draw.rect(wave_s, (*C_NEON[:3], alpha), (i * 3, bar_y, 2, bar_h))

    surface.blit(wave_s, (x, y))


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

        self.box_height = 130
        self.box_y = HEIGHT - self.box_height
        self.text_max_width = WIDTH - 120
        self.font_speaker = pygame.font.SysFont("monospace", 14, bold=True)
        self.font_text = pygame.font.SysFont("monospace", 15)
        self.cursor_visible = True
        self.cursor_timer = 0
        self._first_char_shake = False
        self._shake_timer = 0

    def show(self, messages, on_complete=None):
        self.messages = messages
        self.current_index = 0
        self.char_index = 0
        self.char_timer = 0
        self.active = True
        self.finished = False
        self.on_complete = on_complete
        self._first_char_shake = True

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
            self._first_char_shake = True
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
                # Trigger shake on first character
                if self.char_index == 1 and self._first_char_shake:
                    self._shake_timer = 0.12
                    self._first_char_shake = False

        # Shake decay
        if self._shake_timer > 0:
            self._shake_timer -= dt
            if self._shake_timer < 0:
                self._shake_timer = 0

        self.cursor_timer += dt
        if self.cursor_timer > 0.5:
            self.cursor_visible = not self.cursor_visible
            self.cursor_timer = 0

    def draw(self, surface):
        if not self.active or self.current_index >= len(self.messages):
            return

        t = pygame.time.get_ticks()
        msg = self.messages[self.current_index]
        visible_text = msg["text"][:self.char_index]
        is_typing = self.char_index < len(msg["text"])

        # Word-wrap
        lines = _word_wrap(visible_text, self.font_text, self.text_max_width)
        line_h = self.font_text.get_linesize()
        needed_h = max(self.box_height, 60 + len(lines) * line_h + 16)
        box_y = HEIGHT - needed_h

        # Screen shake offset
        shake_x, shake_y = 0, 0
        if self._shake_timer > 0:
            intensity = self._shake_timer * 15
            shake_x = int(random.uniform(-intensity, intensity))
            shake_y = int(random.uniform(-intensity, intensity))

        # ── Glass panel background ──
        box_surf = pygame.Surface((WIDTH, needed_h), pygame.SRCALPHA)
        # Base glass
        box_surf.fill((6, 8, 16, 230))
        # Upper gradient (frosted glass effect)
        grad = pygame.Surface((WIDTH, needed_h // 3), pygame.SRCALPHA)
        grad.fill((20, 28, 45, 25))
        box_surf.blit(grad, (0, 0))

        # Scanline effect inside dialogue box
        for sy in range(0, needed_h, 3):
            pygame.draw.line(box_surf, (0, 0, 0, 10), (0, sy), (WIDTH, sy), 1)

        # ── Animated border (subtle color pulse) ──
        border_pulse = int(100 + 50 * math.sin(t * 0.003))
        # Top neon line
        pygame.draw.line(box_surf, (*C_NEON[:3], border_pulse), (0, 0), (WIDTH, 0), 2)
        # Side borders (fading)
        for i in range(min(needed_h, 60)):
            a = int(border_pulse * (1 - i / 60))
            if a > 0:
                pygame.draw.line(box_surf, (*C_NEON[:3], a), (0, i), (0, i + 1), 1)
                pygame.draw.line(box_surf, (*C_NEON[:3], a), (WIDTH - 1, i), (WIDTH - 1, i + 1), 1)

        surface.blit(box_surf, (shake_x, box_y + shake_y))

        # ── Corner brackets (decorative) ──
        bracket_len = 16
        bracket_col = C_NEON
        corners = [
            (8, box_y + 6, 1, 1),
            (WIDTH - 8, box_y + 6, -1, 1),
            (8, box_y + needed_h - 6, 1, -1),
            (WIDTH - 8, box_y + needed_h - 6, -1, -1),
        ]
        for cx, cy, dx, dy in corners:
            bx, by = cx + shake_x, cy + shake_y
            pygame.draw.line(surface, bracket_col, (bx, by),
                             (bx + dx * bracket_len, by), 1)
            pygame.draw.line(surface, bracket_col, (bx, by),
                             (bx, by + dy * bracket_len), 1)

        # ── Speaker avatar ──
        av_x = 18 + shake_x
        av_y = box_y + 10 + shake_y
        _draw_speaker_avatar(surface, av_x, av_y, msg["speaker"], t)

        # ── Speaker name with neon glow ──
        name_x = 66 + shake_x
        name_y = box_y + 12 + shake_y

        # Glow behind name
        speaker_text = self.font_speaker.render(msg["speaker"], True, C_NEON)
        glow_s = pygame.Surface((speaker_text.get_width() + 6, speaker_text.get_height() + 6),
                                pygame.SRCALPHA)
        glow_s.blit(self.font_speaker.render(msg["speaker"], True, C_NEON), (3, 3))
        glow_s.set_alpha(35)
        surface.blit(glow_s, (name_x - 3, name_y - 3))
        # Crisp name
        surface.blit(speaker_text, (name_x, name_y))

        # Waveform visualizer next to speaker name
        wave_x = name_x + speaker_text.get_width() + 8
        _draw_waveform(surface, wave_x, name_y + 2,
                       40, speaker_text.get_height() - 4, t, active=is_typing)

        # Separator line under speaker
        sep_y = name_y + speaker_text.get_height() + 4
        sep_s = pygame.Surface((WIDTH - 80, 1), pygame.SRCALPHA)
        for sx in range(WIDTH - 80):
            a = int(40 * (1 - abs(sx - (WIDTH - 80) // 2) / ((WIDTH - 80) // 2)))
            pygame.draw.line(sep_s, (*C_ACCENT[:3], max(0, a)), (sx, 0), (sx + 1, 0), 1)
        surface.blit(sep_s, (40 + shake_x, sep_y + shake_y))

        # ── Text lines ──
        text_start_y = sep_y + 8 + shake_y
        for i, line in enumerate(lines):
            text_surf = self.font_text.render(line, True, C_TEXT_PRI)
            surface.blit(text_surf, (66 + shake_x, text_start_y + i * line_h))

        # ── Typing cursor ──
        if is_typing and self.cursor_visible:
            last_line = lines[-1] if lines else ""
            cursor_x = 66 + self.font_text.size(last_line)[0] + shake_x
            cursor_y = text_start_y + (len(lines) - 1) * line_h
            # Blinking neon cursor
            cursor_s = pygame.Surface((2, line_h), pygame.SRCALPHA)
            cursor_alpha = int(180 + 60 * math.sin(t * 0.008))
            cursor_s.fill((*C_NEON[:3], cursor_alpha))
            surface.blit(cursor_s, (cursor_x, cursor_y))

        # ── Continue indicator (pulsing + blinking) ──
        if not is_typing:
            cont_t = t * 0.005
            cont_alpha = int(140 + 80 * math.sin(cont_t))
            bounce = math.sin(cont_t * 1.5) * 3

            # "CONTINUAR" text with pulse
            hint_font = self.font_speaker
            hint_text = "CONTINUAR >>"
            hint_s = hint_font.render(hint_text, True, C_NEON)

            hx = WIDTH - hint_s.get_width() - 30 + shake_x
            hy = int(box_y + needed_h - 24 + bounce + shake_y)

            # Glow behind hint
            hint_glow = pygame.Surface((hint_s.get_width() + 8, hint_s.get_height() + 8),
                                       pygame.SRCALPHA)
            hint_glow.blit(hint_font.render(hint_text, True, C_NEON), (4, 4))
            hint_glow.set_alpha(int(cont_alpha * 0.2))
            surface.blit(hint_glow, (hx - 4, hy - 4))

            # Blinking effect
            if math.sin(t * 0.004) > -0.3:
                hint_final = hint_font.render(hint_text, True, C_NEON)
                hint_final.set_alpha(cont_alpha)
                surface.blit(hint_final, (hx, hy))
