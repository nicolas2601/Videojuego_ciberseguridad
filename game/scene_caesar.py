import math
import pygame

from crypto.caesar import decrypt_caesar
from game.constants import (
    WIDTH, HEIGHT, C_BG, C_BG2, C_BG3, C_BORDER, C_TEXT_PRI,
    C_TEXT_SEC, C_TEXT_HINT, C_ACCENT, C_GREEN, C_RED, C_NEON, C_WHITE,
    C_PANEL, C_CAESAR, HINTS_CONFIG,
)
from game.ui.draw_assets import (
    draw_desk, draw_chair, draw_filing_cabinet, draw_office_floor,
    draw_wall, draw_text_box, word_wrap,
)
from game.ui.dialogue import DialogueBox
from game.ui.hud import HUD


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

        # Difficulty config
        config = HINTS_CONFIG[self.manager.difficulty]
        self.free_hints = config["free_hints"]
        self.visual_aids = config["visual_aids"]

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
        self.flash_color = None
        self.flash_timer = 0.0
        self.flash_duration = 0.6

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

        # Wheel geometry (right half of screen)
        self.wheel_cx = 860
        self.wheel_cy = 370
        self.outer_r = 210
        self.inner_r = 160
        self.letter_outer_r = self.outer_r - 18
        self.letter_inner_r = self.inner_r - 18

        # Button rects
        self.btn_verify = pygame.Rect(WIDTH - 230, HEIGHT - 70, 200, 44)
        self.btn_volver = pygame.Rect(20, HEIGHT - 70, 140, 44)
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

        # Background (cached)
        self._bg_ready = False
        self._bg_surface = None

        # Arrow pulse for visual aids
        self._aid_pulse = 0.0

    # ----- background -------------------------------------------------------
    def _build_bg(self):
        """Render the static background once using pygame.draw only."""
        self._bg_surface = pygame.Surface((WIDTH, HEIGHT))

        # Floor tiles
        draw_office_floor(self._bg_surface)

        # Wall
        draw_wall(self._bg_surface, 0, wall_h=50)

        # Darken floor to match thriller aesthetic
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((*C_BG, 180))
        self._bg_surface.blit(overlay, (0, 0))

        # Office furniture (all pygame.draw, no sprites)
        draw_desk(self._bg_surface, 40, 560, w=120, h=50)
        draw_desk(self._bg_surface, 250, 580, w=100, h=40)
        draw_chair(self._bg_surface, 100, 620)
        draw_chair(self._bg_surface, 300, 630)
        draw_filing_cabinet(self._bg_surface, 1100, 500)
        draw_filing_cabinet(self._bg_surface, 1140, 500)

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

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            # VOLVER button
            if self.btn_volver.collidepoint(event.pos):
                self.manager.change_scene("hub")
                return

            # Wheel drag
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
                        # Hint 0 is always free; others depend on config
                        if i < self.free_hints:
                            self.hint_revealed[i] = True
                            # Free hints don't count against score
                        else:
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
        raw = (100 - int(self.time_elapsed / 10)
               - self.hints_used * 15
               - self.failed_attempts * 5)
        return max(raw, 10)

    # ----- update -----------------------------------------------------------
    def update(self, dt):
        if not self.solved:
            self.time_elapsed += dt
        if self.flash_timer > 0:
            self.flash_timer = max(0.0, self.flash_timer - dt)
        self.dialogue.update(dt)
        self._aid_pulse += dt * 3.0

    # ----- draw -------------------------------------------------------------
    def draw(self, surface):
        # Background
        if not self._bg_ready:
            self._build_bg()
        surface.blit(self._bg_surface, (0, 0))

        # Left panel (cipher info)
        self._draw_left_panel(surface)

        # Wheel
        self._draw_wheel(surface)

        # Visual aids (Dummy mode)
        if self.visual_aids and not self.solved:
            self._draw_visual_aids(surface)

        # Verify button
        self._draw_button(surface, self.btn_verify, "VERIFICAR CLAVE", C_CAESAR)

        # VOLVER button
        self._draw_button(surface, self.btn_volver, "VOLVER", C_ACCENT)

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
        # Solid black background panel for legibility
        panel_rect = pygame.Rect(20, 60, 400, 340)
        pygame.draw.rect(surface, (0, 0, 0), panel_rect)
        pygame.draw.rect(surface, C_BORDER, panel_rect, 1)

        x0, y0 = 40, 78

        # Title
        draw_text_box(surface, "NOTA INTERCEPTADA", x0, y0,
                       self.font_title, color=C_NEON, bg_alpha=0)

        # Cipher text label
        lbl_c = self.font_label.render("CIFRADO:", True, C_TEXT_HINT)
        surface.blit(lbl_c, (x0, y0 + 40))

        # Cipher text in neon on black
        draw_text_box(surface, self.cipher_text, x0, y0 + 60,
                       self.font_cipher, color=C_NEON, bg_alpha=220, padding=6)

        # Decrypted text label
        lbl_d = self.font_label.render("DESCIFRADO:", True, C_TEXT_HINT)
        surface.blit(lbl_d, (x0, y0 + 110))

        # Decrypted text -- live update
        decrypted = decrypt_caesar(self.cipher_text, self.shift)
        is_correct = decrypted.upper() == self.expected_plain.upper()
        dec_color = C_GREEN if is_correct else C_NEON

        draw_text_box(surface, decrypted, x0, y0 + 130,
                       self.font_cipher, color=dec_color, bg_alpha=220, padding=6)

        # Shift indicator
        shift_txt = f"DESPLAZAMIENTO ACTUAL: {self.shift}"
        draw_text_box(surface, shift_txt, x0, y0 + 185,
                       self.font_label, color=C_TEXT_SEC, bg_alpha=0)

        # Stats
        stats_txt = (f"TIEMPO: {int(self.time_elapsed)}s   "
                     f"INTENTOS: {self.failed_attempts}   "
                     f"PISTAS: {self.hints_used}/3")
        draw_text_box(surface, stats_txt, x0, y0 + 215,
                       self.font_label, color=C_TEXT_HINT, bg_alpha=0)

        # Score preview
        score_preview = self._calc_score()
        sc_color = (C_GREEN if score_preview >= 70
                    else C_ACCENT if score_preview >= 40
                    else C_RED)
        draw_text_box(surface, f"PUNTUACION EST.: {score_preview}",
                       x0, y0 + 245, self.font_label, color=sc_color, bg_alpha=0)

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
            (cx - shift_surf.get_width() // 2,
             cy - shift_surf.get_height() // 2),
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

        # Ring labels
        lbl_outer = self.font_label.render("CIFRADO", True, C_TEXT_HINT)
        surface.blit(lbl_outer, (cx - self.outer_r - 10, cy + self.outer_r + 10))
        lbl_inner = self.font_label.render("DESCIFRADO", True, C_TEXT_HINT)
        surface.blit(lbl_inner, (cx + 30, cy + self.outer_r + 10))

        # Drag instruction
        if not self.solved:
            draw_text_box(
                surface,
                "Clic + arrastrar sobre la rueda para rotar",
                cx - 160, cy + self.outer_r + 30,
                self.font_hint, color=C_TEXT_HINT, bg_alpha=180,
            )

    # ----- visual aids (Dummy mode) -----------------------------------------
    def _draw_visual_aids(self, surface):
        """Draw arrows/highlights pointing to the correct shift area."""
        pulse = 0.5 + 0.5 * math.sin(self._aid_pulse)
        alpha = int(120 + 80 * pulse)

        # Arrow pointing to the shift number with hint text
        aid_surf = pygame.Surface((260, 36), pygame.SRCALPHA)
        aid_surf.fill((0, 0, 0, alpha))
        hint_font = self.font_label
        txt = hint_font.render(
            f"Prueba desplazamiento = {self.correct_shift}", True, C_NEON
        )
        aid_surf.blit(txt, (8, 8))
        surface.blit(aid_surf, (self.wheel_cx - 130, self.wheel_cy - self.outer_r - 50))

        # Animated arrow from hint to wheel center
        arrow_x = self.wheel_cx
        arrow_y1 = self.wheel_cy - self.outer_r - 16
        arrow_y0 = arrow_y1 - 20
        neon_alpha = int(180 + 75 * pulse)
        arrow_col = (*C_NEON[:2], min(255, C_NEON[2]), neon_alpha)
        arrow_surf = pygame.Surface((20, 24), pygame.SRCALPHA)
        # Arrow body
        pygame.draw.line(arrow_surf, arrow_col, (10, 0), (10, 16), 3)
        # Arrow head
        pygame.draw.polygon(arrow_surf, arrow_col,
                            [(4, 12), (16, 12), (10, 22)])
        surface.blit(arrow_surf, (arrow_x - 10, arrow_y0))

        # Highlight the correct letter position on inner ring
        angle_step = TWO_PI / 26
        start_angle = -math.pi / 2
        correct_idx = self.correct_shift % 26
        angle = start_angle + 0 * angle_step  # position 0 (12 o'clock)
        # The correct letter at position 0 when shift == correct_shift
        hx = self.wheel_cx + math.cos(angle) * (self.inner_r + 4)
        hy = self.wheel_cy + math.sin(angle) * (self.inner_r + 4)
        glow_r = int(14 + 4 * pulse)
        glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*C_NEON, int(60 * pulse)),
                           (glow_r, glow_r), glow_r)
        surface.blit(glow_surf, (int(hx) - glow_r, int(hy) - glow_r))

    # ----- hints ------------------------------------------------------------
    def _draw_hints(self, surface):
        for i, rect in enumerate(self.btn_hints):
            if self.hint_revealed[i]:
                # Show hint text on solid black bg with word-wrap
                hint_text = self.hints_list[i]
                draw_text_box(surface, hint_text, rect.x, rect.y,
                              self.font_hint, color=C_NEON,
                              bg_alpha=240, padding=10,
                              max_width=rect.width - 20)
            else:
                # Is this hint free?
                if i < self.free_hints:
                    label = f"PISTA {i + 1}  (GRATIS)"
                else:
                    label = f"PISTA {i + 1}  (-15 pts)"
                self._draw_button(
                    surface, rect, label, C_ACCENT, small=True,
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
        dim.fill((0, 0, 0, 200))
        surface.blit(dim, (0, 0))

        # Popup box - solid black for legibility
        pw, ph = 700, 360
        px = (WIDTH - pw) // 2
        py = (HEIGHT - ph) // 2

        pygame.draw.rect(surface, (0, 0, 0), (px, py, pw, ph))
        pygame.draw.rect(surface, C_CAESAR, (px, py, pw, ph), 2,
                         border_radius=6)

        # Title
        title = self.font_debrief_title.render("DEBRIEFING", True, C_NEON)
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
        surface.blit(score_txt,
                      (px + pw // 2 - score_txt.get_width() // 2, py + 62))

        # Debriefing text with word-wrap on solid black bg
        draw_text_box(surface, self.debriefing_text,
                       px + 30, py + 95,
                       self.font_debrief, color=C_NEON,
                       bg_alpha=0, padding=4,
                       max_width=pw - 60)

        # Continue button
        self.btn_continue = pygame.Rect(
            px + pw // 2 - 100, py + ph - 60, 200, 44
        )
        self._draw_button(surface, self.btn_continue, "CONTINUAR", C_CAESAR)
