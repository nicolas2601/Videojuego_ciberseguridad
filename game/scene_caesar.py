import math
import pygame

from crypto.caesar import decrypt_caesar
from game.constants import (
    WIDTH, HEIGHT, C_BG, C_BG2, C_BG3, C_BORDER, C_TEXT_PRI,
    C_TEXT_SEC, C_TEXT_HINT, C_ACCENT, C_GREEN, C_RED, C_CAESAR,
    C_PANEL, C_WHITE,
)
from game.ui.dialogue import DialogueBox
from game.ui.hud import HUD
from game.ui.tile_renderer import get_separate_sprite, draw_floor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
TWO_PI = math.pi * 2


def _lerp_color(a, b, t):
    """Linearly interpolate between two RGB tuples."""
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# ---------------------------------------------------------------------------
# CaesarScene
# ---------------------------------------------------------------------------
class CaesarScene:
    """Interactive rotary-wheel Caesar cipher puzzle."""

    def __init__(self, manager):
        self.manager = manager
        puzzle = manager.puzzles["caesar"]

        # Puzzle data
        self.cipher_text = puzzle["cipher_text"]
        self.correct_shift = puzzle["correct_shift"]
        self.expected_plain = puzzle["plain_text"]
        self.hints_list = puzzle["hints"]
        self.debriefing_text = puzzle["debriefing"]

        # State
        self.shift = 0
        self.dragging = False
        self.drag_last_x = 0
        self.drag_accum = 0.0

        self.hints_used = 0
        self.failed_attempts = 0
        self.time_elapsed = 0.0
        self.solved = False
        self.showing_debriefing = False

        # Flash feedback
        self.flash_color = None   # C_GREEN or C_RED
        self.flash_timer = 0.0
        self.flash_duration = 0.6

        # Success delay before scene change
        self.success_timer = 0.0
        self.waiting_for_exit = False

        # Fonts
        self.font_title = pygame.font.SysFont("monospace", 15, bold=True)
        self.font_cipher = pygame.font.SysFont("monospace", 28, bold=True)
        self.font_label = pygame.font.SysFont("monospace", 13, bold=True)
        self.font_letter = pygame.font.SysFont("monospace", 16, bold=True)
        self.font_shift = pygame.font.SysFont("monospace", 38, bold=True)
        self.font_btn = pygame.font.SysFont("monospace", 14, bold=True)
        self.font_hint = pygame.font.SysFont("monospace", 12)
        self.font_debrief = pygame.font.SysFont("monospace", 14)
        self.font_debrief_title = pygame.font.SysFont("monospace", 18, bold=True)

        # Wheel geometry  (right half of screen)
        self.wheel_cx = 860
        self.wheel_cy = 370
        self.outer_r = 210
        self.inner_r = 160
        self.letter_outer_r = self.outer_r - 18
        self.letter_inner_r = self.inner_r - 18

        # Button rects (built once, drawn every frame)
        self.btn_verify = pygame.Rect(WIDTH - 230, HEIGHT - 70, 200, 44)
        self.btn_hints = []
        for i in range(3):
            self.btn_hints.append(pygame.Rect(30, 460 + i * 48, 340, 38))

        self.hint_revealed = [False, False, False]

        # Debriefing continue button
        self.btn_continue = pygame.Rect(
            WIDTH // 2 - 100, HEIGHT // 2 + 140, 200, 44
        )

        # HUD
        self.hud = HUD()
        self.hud.set_info(
            "ESCENA 01 -- SALA DE INTERROGACION",
            "CAPA 1/4 -- CESAR",
        )

        # Dialogue
        self.dialogue = DialogueBox()
        enter_msgs = manager.dialogues["caesar"]["enter"]
        self.dialogue.show(enter_msgs)

        # Background sprites (loaded lazily on first draw)
        self._bg_ready = False
        self._bg_surface = None

    # ----- background -------------------------------------------------------
    def _build_bg(self, surface):
        """Render the static background once and cache it."""
        self._bg_surface = pygame.Surface((WIDTH, HEIGHT))
        draw_floor(self._bg_surface, 0, 0)

        # Darken the floor heavily to match the thriller aesthetic
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((*C_BG, 200))
        self._bg_surface.blit(overlay, (0, 0))

        # Place office sprites
        try:
            desk = get_separate_sprite("Sprite-0002.png", scale=3)
            self._bg_surface.blit(desk, (40, 520))
        except Exception:
            pass
        try:
            desk2 = get_separate_sprite("Sprite-0005.png", scale=3)
            self._bg_surface.blit(desk2, (250, 540))
        except Exception:
            pass
        try:
            cabinet = get_separate_sprite("Sprite-0013.png", scale=3)
            self._bg_surface.blit(cabinet, (1100, 480))
        except Exception:
            pass

        self._bg_ready = True

    # ----- events -----------------------------------------------------------
    def handle_event(self, event):
        if self.showing_debriefing:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.btn_continue.collidepoint(event.pos):
                    score = self._calc_score()
                    self.manager.complete_puzzle("caesar", score)
                    self.manager.change_scene("hub")
            return

        # Dialogue eats events first
        if self.dialogue.active:
            self.dialogue.handle_event(event)
            return

        if self.solved:
            return

        # Wheel drag
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            dist = math.hypot(mx - self.wheel_cx, my - self.wheel_cy)
            if dist <= self.outer_r + 20:
                self.dragging = True
                self.drag_last_x = mx
                self.drag_accum = 0.0
            elif self.btn_verify.collidepoint(event.pos):
                self._on_verify()
            else:
                for i, r in enumerate(self.btn_hints):
                    if r.collidepoint(event.pos) and not self.hint_revealed[i]:
                        self.hint_revealed[i] = True
                        self.hints_used += 1

        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False

        elif event.type == pygame.MOUSEMOTION and self.dragging:
            mx = event.pos[0]
            dx = mx - self.drag_last_x
            self.drag_last_x = mx
            self.drag_accum += dx
            while self.drag_accum >= 6:
                self.shift = (self.shift + 1) % 26
                self.drag_accum -= 6
            while self.drag_accum <= -6:
                self.shift = (self.shift - 1) % 26
                self.drag_accum += 6

    # ----- verify -----------------------------------------------------------
    def _on_verify(self):
        decrypted = decrypt_caesar(self.cipher_text, self.shift)
        if decrypted.upper() == self.expected_plain.upper():
            self.solved = True
            self.flash_color = C_GREEN
            self.flash_timer = self.flash_duration
            success_msgs = self.manager.dialogues["caesar"]["success"]
            self.dialogue.show(
                success_msgs,
                on_complete=self._show_debriefing,
            )
        else:
            self.failed_attempts += 1
            self.flash_color = C_RED
            self.flash_timer = self.flash_duration
            error_msgs = self.manager.dialogues["caesar"]["error"]
            self.dialogue.show(error_msgs)

    def _show_debriefing(self):
        self.showing_debriefing = True

    def _calc_score(self):
        raw = 100 - int(self.time_elapsed / 10) - self.hints_used * 15 - self.failed_attempts * 5
        return max(raw, 10)

    # ----- update -----------------------------------------------------------
    def update(self, dt):
        if not self.solved:
            self.time_elapsed += dt
        if self.flash_timer > 0:
            self.flash_timer = max(0.0, self.flash_timer - dt)
        self.dialogue.update(dt)

    # ----- draw -------------------------------------------------------------
    def draw(self, surface):
        # Background
        if not self._bg_ready:
            self._build_bg(surface)
        surface.blit(self._bg_surface, (0, 0))

        # Left panel (cipher info)
        self._draw_left_panel(surface)

        # Wheel
        self._draw_wheel(surface)

        # Verify button
        self._draw_button(
            surface, self.btn_verify, "VERIFICAR CLAVE", C_CAESAR
        )

        # Hint buttons
        self._draw_hints(surface)

        # Flash overlay
        if self.flash_timer > 0 and self.flash_color:
            alpha = int(60 * (self.flash_timer / self.flash_duration))
            flash_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            flash_surf.fill((*self.flash_color, alpha))
            surface.blit(flash_surf, (0, 0))

        # HUD on top
        self.hud.draw(surface)

        # Debriefing popup
        if self.showing_debriefing:
            self._draw_debriefing(surface)

        # Dialogue on very top
        self.dialogue.draw(surface)

    # ----- left panel -------------------------------------------------------
    def _draw_left_panel(self, surface):
        panel = pygame.Surface((400, 340), pygame.SRCALPHA)
        panel.fill((*C_PANEL, 220))
        pygame.draw.rect(panel, C_BORDER, panel.get_rect(), 1)
        surface.blit(panel, (20, 60))

        x0, y0 = 40, 78

        # Title
        title = self.font_title.render("NOTA INTERCEPTADA", True, C_ACCENT)
        surface.blit(title, (x0, y0))

        # Cipher text label
        lbl_c = self.font_label.render("CIFRADO:", True, C_TEXT_HINT)
        surface.blit(lbl_c, (x0, y0 + 40))

        cipher_surf = self.font_cipher.render(self.cipher_text, True, C_WHITE)
        surface.blit(cipher_surf, (x0, y0 + 62))

        # Decrypted text label
        lbl_d = self.font_label.render("DESCIFRADO:", True, C_TEXT_HINT)
        surface.blit(lbl_d, (x0, y0 + 110))

        # Decrypted text -- live update
        decrypted = decrypt_caesar(self.cipher_text, self.shift)
        is_correct = decrypted.upper() == self.expected_plain.upper()
        if is_correct:
            dec_color = C_GREEN
        elif self.shift == 0:
            dec_color = C_TEXT_SEC
        else:
            # transition from gray to slightly warmer as shift changes
            dec_color = C_TEXT_PRI

        dec_surf = self.font_cipher.render(decrypted, True, dec_color)
        surface.blit(dec_surf, (x0, y0 + 132))

        # Shift indicator
        shift_lbl = self.font_label.render(
            f"DESPLAZAMIENTO ACTUAL: {self.shift}", True, C_TEXT_SEC
        )
        surface.blit(shift_lbl, (x0, y0 + 185))

        # Stats
        stats = self.font_label.render(
            f"TIEMPO: {int(self.time_elapsed)}s   "
            f"INTENTOS: {self.failed_attempts}   "
            f"PISTAS: {self.hints_used}/3",
            True, C_TEXT_HINT,
        )
        surface.blit(stats, (x0, y0 + 220))

        # Score preview
        score_preview = self._calc_score()
        score_color = C_GREEN if score_preview >= 70 else C_ACCENT if score_preview >= 40 else C_RED
        sc = self.font_label.render(f"PUNTUACION EST.: {score_preview}", True, score_color)
        surface.blit(sc, (x0, y0 + 250))

    # ----- wheel drawing ----------------------------------------------------
    def _draw_wheel(self, surface):
        cx, cy = self.wheel_cx, self.wheel_cy

        # Outer ring background
        pygame.draw.circle(surface, C_BG2, (cx, cy), self.outer_r)
        pygame.draw.circle(surface, C_BORDER, (cx, cy), self.outer_r, 2)

        # Inner ring background
        pygame.draw.circle(surface, C_BG3, (cx, cy), self.inner_r)
        pygame.draw.circle(surface, C_BORDER, (cx, cy), self.inner_r, 2)

        # Center disc
        pygame.draw.circle(surface, C_PANEL, (cx, cy), 55)
        pygame.draw.circle(surface, C_BORDER, (cx, cy), 55, 2)

        # Shift number at center
        shift_surf = self.font_shift.render(str(self.shift), True, C_CAESAR)
        surface.blit(
            shift_surf,
            (cx - shift_surf.get_width() // 2, cy - shift_surf.get_height() // 2),
        )

        # Draw letters
        angle_step = TWO_PI / 26
        start_angle = -math.pi / 2  # 12 o'clock

        for i, ch in enumerate(ALPHABET):
            angle = start_angle + i * angle_step

            # Outer ring -- fixed alphabet
            ox = cx + math.cos(angle) * self.letter_outer_r
            oy = cy + math.sin(angle) * self.letter_outer_r
            outer_color = C_WHITE if i == 0 else C_TEXT_PRI
            letter_s = self.font_letter.render(ch, True, outer_color)
            surface.blit(
                letter_s,
                (int(ox) - letter_s.get_width() // 2,
                 int(oy) - letter_s.get_height() // 2),
            )

            # Inner ring -- shifted alphabet
            shifted_ch = ALPHABET[(i + self.shift) % 26]
            ix = cx + math.cos(angle) * self.letter_inner_r
            iy = cy + math.sin(angle) * self.letter_inner_r

            # Highlight the letter that maps to position 0 (the aligned one)
            inner_color = C_CAESAR if i == 0 else C_ACCENT
            inner_s = self.font_letter.render(shifted_ch, True, inner_color)
            surface.blit(
                inner_s,
                (int(ix) - inner_s.get_width() // 2,
                 int(iy) - inner_s.get_height() // 2),
            )

            # Tick marks between rings
            tick_inner = self.inner_r + 2
            tick_outer = self.outer_r - 2
            t1x = cx + math.cos(angle - angle_step / 2) * tick_inner
            t1y = cy + math.sin(angle - angle_step / 2) * tick_inner
            t2x = cx + math.cos(angle - angle_step / 2) * tick_outer
            t2y = cy + math.sin(angle - angle_step / 2) * tick_outer
            pygame.draw.line(
                surface, C_BORDER,
                (int(t1x), int(t1y)), (int(t2x), int(t2y)), 1,
            )

        # Triangle indicator at 12 o'clock
        tri_y = cy - self.outer_r - 14
        tri_pts = [
            (cx, tri_y + 16),
            (cx - 10, tri_y),
            (cx + 10, tri_y),
        ]
        pygame.draw.polygon(surface, C_CAESAR, tri_pts)
        pygame.draw.polygon(surface, C_WHITE, tri_pts, 1)

        # Ring label
        lbl_outer = self.font_label.render("CIFRADO", True, C_TEXT_HINT)
        surface.blit(lbl_outer, (cx - self.outer_r - 10, cy + self.outer_r + 10))
        lbl_inner = self.font_label.render("DESCIFRADO", True, C_TEXT_HINT)
        surface.blit(lbl_inner, (cx + 30, cy + self.outer_r + 10))

        # Drag instruction
        if not self.solved:
            instr = self.font_hint.render(
                "Clic + arrastrar sobre la rueda para rotar", True, C_TEXT_HINT
            )
            surface.blit(
                instr,
                (cx - instr.get_width() // 2, cy + self.outer_r + 30),
            )

    # ----- hints ------------------------------------------------------------
    def _draw_hints(self, surface):
        for i, rect in enumerate(self.btn_hints):
            if self.hint_revealed[i]:
                # Show hint text
                panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                panel.fill((*C_BG3, 200))
                pygame.draw.rect(panel, C_BORDER, panel.get_rect(), 1)
                surface.blit(panel, rect.topleft)

                txt = self.font_hint.render(
                    self.hints_list[i], True, C_TEXT_PRI
                )
                surface.blit(txt, (rect.x + 10, rect.y + 12))
            else:
                self._draw_button(
                    surface, rect,
                    f"PISTA {i + 1}  (-15 pts)",
                    C_ACCENT, small=True,
                )

    # ----- generic button ---------------------------------------------------
    def _draw_button(self, surface, rect, text, color, small=False):
        mx, my = pygame.mouse.get_pos()
        hover = rect.collidepoint(mx, my)

        bg = _lerp_color(C_PANEL, color, 0.25 if hover else 0.10)
        border = color if hover else C_BORDER

        pygame.draw.rect(surface, bg, rect, border_radius=4)
        pygame.draw.rect(surface, border, rect, 1, border_radius=4)

        font = self.font_hint if small else self.font_btn
        txt_color = C_WHITE if hover else C_TEXT_PRI
        lbl = font.render(text, True, txt_color)
        surface.blit(
            lbl,
            (rect.centerx - lbl.get_width() // 2,
             rect.centery - lbl.get_height() // 2),
        )

    # ----- debriefing popup -------------------------------------------------
    def _draw_debriefing(self, surface):
        # Dim backdrop
        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 180))
        surface.blit(dim, (0, 0))

        # Popup box
        pw, ph = 700, 340
        px = (WIDTH - pw) // 2
        py = (HEIGHT - ph) // 2

        popup = pygame.Surface((pw, ph), pygame.SRCALPHA)
        popup.fill((*C_PANEL, 245))
        pygame.draw.rect(popup, C_CAESAR, popup.get_rect(), 2, border_radius=6)
        surface.blit(popup, (px, py))

        # Title
        title = self.font_debrief_title.render("DEBRIEFING", True, C_CAESAR)
        surface.blit(title, (px + pw // 2 - title.get_width() // 2, py + 20))

        # Separator line
        pygame.draw.line(
            surface, C_BORDER,
            (px + 30, py + 50), (px + pw - 30, py + 50), 1,
        )

        # Score
        score = self._calc_score()
        score_txt = self.font_btn.render(
            f"PUNTUACION FINAL: {score}/100", True, C_GREEN
        )
        surface.blit(score_txt, (px + pw // 2 - score_txt.get_width() // 2, py + 62))

        # Debriefing text -- word-wrap
        self._draw_wrapped_text(
            surface, self.debriefing_text,
            self.font_debrief, C_TEXT_PRI,
            px + 30, py + 95, pw - 60, 20,
        )

        # Continue button
        self.btn_continue = pygame.Rect(
            px + pw // 2 - 100, py + ph - 60, 200, 44
        )
        self._draw_button(surface, self.btn_continue, "CONTINUAR", C_CAESAR)

    # ----- text wrapping helper ---------------------------------------------
    @staticmethod
    def _draw_wrapped_text(surface, text, font, color, x, y, max_w, line_h):
        words = text.split()
        line = ""
        cy = y
        for word in words:
            test = line + (" " if line else "") + word
            if font.size(test)[0] <= max_w:
                line = test
            else:
                if line:
                    surface.blit(font.render(line, True, color), (x, cy))
                    cy += line_h
                line = word
        if line:
            surface.blit(font.render(line, True, color), (x, cy))
