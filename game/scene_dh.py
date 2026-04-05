import pygame
import math
import colorsys
from game.constants import (WIDTH, HEIGHT, C_BG, C_BG2, C_BG3, C_BORDER, C_TEXT_PRI,
    C_TEXT_SEC, C_TEXT_HINT, C_ACCENT, C_GREEN, C_RED, C_NEON, C_WHITE, C_PANEL,
    C_DH, C_AMBER, C_CAESAR, C_BASE64, C_HASH, HINTS_CONFIG)
from game.ui.draw_assets import (draw_office_floor, draw_wall, draw_text_box, word_wrap,
    draw_desk, draw_monitor, draw_server_rack)
from game.ui.dialogue import DialogueBox
from game.ui.hud import HUD
from crypto.dh_utils import dh_public, dh_shared_key


# DH parameters (small primes for simplicity)
_G = 5
_P = 23
_B_SECRET = 15
_B_PUBLIC = dh_public(_G, _P, _B_SECRET)

# Layout constants
_COL_LEFT_X = 30
_COL_CENTER_X = 440
_COL_RIGHT_X = 870
_COL_W = 390
_COL_TOP = 70
_SLIDER_Y = 230
_SLIDER_W = 300
_SLIDER_H = 12
_HANDLE_W = 18
_HANDLE_H = 28
_BUTTON_W = 280
_BUTTON_H = 48
_COLOR_SQ = 50  # color square size


def _number_to_color(n, p):
    """Map a number in range [0, p) to an HSV color, return RGB tuple."""
    hue = (n / p)
    r, g, b = colorsys.hsv_to_rgb(hue, 0.85, 0.95)
    return (int(r * 255), int(g * 255), int(b * 255))


def _blend_colors(c1, c2, ratio=0.5):
    """Blend two RGB colors together."""
    return (
        int(c1[0] * ratio + c2[0] * (1 - ratio)),
        int(c1[1] * ratio + c2[1] * (1 - ratio)),
        int(c1[2] * ratio + c2[2] * (1 - ratio)),
    )


# Base color (yellow-ish, represents g)
_BASE_COLOR = (230, 210, 50)


class DHScene:
    def __init__(self, manager):
        self.manager = manager

        # Fonts
        self.font_title = pygame.font.SysFont("monospace", 16, bold=True)
        self.font_label = pygame.font.SysFont("monospace", 14, bold=True)
        self.font_value = pygame.font.SysFont("monospace", 28, bold=True)
        self.font_small = pygame.font.SysFont("monospace", 13)
        self.font_math = pygame.font.SysFont("monospace", 15)
        self.font_edu = pygame.font.SysFont("monospace", 12)
        self.font_btn = pygame.font.SysFont("monospace", 16, bold=True)
        self.font_big = pygame.font.SysFont("monospace", 22, bold=True)
        self.font_channel = pygame.font.SysFont("monospace", 11)

        # State
        self.secret_a = 7
        self.dragging_slider = False
        self.phase = "interact"  # interact -> success
        self.confirmed = False
        self.hints_used = 0
        self.start_time = 0.0
        self.elapsed = 0.0

        # Animation timers
        self.arrow_left_timer = 0.0
        self.arrow_right_timer = 0.0
        self.arrow_left_active = False
        self.arrow_right_active = True
        self.transmit_blink = 0.0
        self.pulse_timer = 0.0

        # Success animation
        self.success_timer = 0.0

        # Slider rect
        self.slider_x = _COL_LEFT_X + (_COL_W - _SLIDER_W) // 2
        self.slider_rect = pygame.Rect(self.slider_x, _SLIDER_Y, _SLIDER_W, _SLIDER_H)
        self.handle_rect = pygame.Rect(0, 0, _HANDLE_W, _HANDLE_H)
        self._update_handle_pos()

        # Confirm button
        self.btn_rect = pygame.Rect(
            WIDTH // 2 - _BUTTON_W // 2, 640,
            _BUTTON_W, _BUTTON_H
        )
        self.btn_hovered = False

        # Back button
        self.back_rect = pygame.Rect(20, HEIGHT - 44, 140, 32)
        self.back_hovered = False

        # Hint button
        self.hint_rect = pygame.Rect(WIDTH - 160, HEIGHT - 44, 140, 32)
        self.hint_hovered = False

        # HUD
        self.hud = HUD()
        self.hud.set_info(
            scene_name="ESCENA 04 -- SALA DE COMUNICACIONES",
            layer_text="CAPA 4/4 -- DIFFIE-HELLMAN"
        )

        # Dialogue
        self.dialogue = DialogueBox()
        enter_msgs = manager.dialogues.get("diffie_hellman", {}).get("enter", [])
        if enter_msgs:
            self.dialogue.show(enter_msgs)

    # ------------------------------------------------------------------
    # Computed DH values
    # ------------------------------------------------------------------

    @property
    def a_public(self):
        return dh_public(_G, _P, self.secret_a)

    @property
    def shared_key_player(self):
        return dh_shared_key(_B_PUBLIC, _P, self.secret_a)

    @property
    def shared_key_real(self):
        return dh_shared_key(self.a_public, _P, _B_SECRET)

    # ------------------------------------------------------------------
    # Color helpers
    # ------------------------------------------------------------------

    @property
    def secret_color_a(self):
        return _number_to_color(self.secret_a, _P)

    @property
    def mixed_color_a(self):
        return _number_to_color(self.a_public, _P)

    @property
    def secret_color_b(self):
        return _number_to_color(_B_SECRET, _P)

    @property
    def mixed_color_b(self):
        return _number_to_color(_B_PUBLIC, _P)

    @property
    def final_color_player(self):
        return _number_to_color(self.shared_key_player, _P)

    @property
    def final_color_real(self):
        return _number_to_color(self.shared_key_real, _P)

    # ------------------------------------------------------------------
    # Slider helpers
    # ------------------------------------------------------------------

    def _update_handle_pos(self):
        t = (self.secret_a - 1) / 19.0
        hx = self.slider_x + int(t * (_SLIDER_W - _HANDLE_W))
        hy = _SLIDER_Y + _SLIDER_H // 2 - _HANDLE_H // 2
        self.handle_rect.topleft = (hx, hy)

    def _value_from_mouse(self, mx):
        rel = mx - self.slider_x - _HANDLE_W // 2
        usable = _SLIDER_W - _HANDLE_W
        t = max(0.0, min(1.0, rel / usable))
        return int(round(t * 19)) + 1

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def handle_event(self, event):
        if self.dialogue.active:
            self.dialogue.handle_event(event)
            return

        if self.phase == "success":
            if event.type == pygame.MOUSEMOTION:
                self.back_hovered = self.back_rect.collidepoint(event.pos)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.back_rect.collidepoint(event.pos):
                    self.manager.change_scene("hub")
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.handle_rect.inflate(8, 8).collidepoint(event.pos):
                self.dragging_slider = True
            elif self.btn_rect.collidepoint(event.pos):
                self._confirm()
            elif self.back_rect.collidepoint(event.pos):
                self.manager.change_scene("hub")
            elif self.hint_rect.collidepoint(event.pos):
                self._show_hint()

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging_slider = False

        elif event.type == pygame.MOUSEMOTION:
            if self.dragging_slider:
                old_a = self.secret_a
                self.secret_a = self._value_from_mouse(event.pos[0])
                self._update_handle_pos()
                if self.secret_a != old_a:
                    self.arrow_left_active = True
                    self.arrow_left_timer = 0.0
            self.btn_hovered = self.btn_rect.collidepoint(event.pos)
            self.back_hovered = self.back_rect.collidepoint(event.pos)
            self.hint_hovered = self.hint_rect.collidepoint(event.pos)

    def _confirm(self):
        if self.shared_key_player == self.shared_key_real:
            self.phase = "success"
            self.success_timer = 0.0
            score = self._calculate_score()
            self.manager.complete_puzzle("diffie_hellman", score)
            msgs = self.manager.dialogues.get("diffie_hellman", {}).get("success", [])
            if msgs:
                self.dialogue.show(msgs)
        else:
            msgs = self.manager.dialogues.get("diffie_hellman", {}).get("error", [])
            if msgs:
                self.dialogue.show(msgs)

    def _show_hint(self):
        self.hints_used += 1
        hint_msgs = [
            {"speaker": "CONTROL",
             "text": "Cualquier valor de 'a' funciona. DH siempre produce la misma clave compartida."},
            {"speaker": "CONTROL",
             "text": "Piensa en los colores: mezclas TU secreto con la base, el otro hace lo mismo. "
                     "Al final ambos llegan al MISMO color."},
        ]
        self.dialogue.show(hint_msgs)

    def _calculate_score(self):
        base = 100
        penalty = max(0, self.hints_used - 1) * 15  # hint 0 is free
        time_penalty = max(0, int(self.elapsed - 30) // 10) * 5
        return max(10, base - penalty - time_penalty)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, dt):
        self.dialogue.update(dt)

        if self.phase == "interact":
            self.elapsed += dt

        self.transmit_blink += dt
        self.pulse_timer += dt

        if self.arrow_left_active:
            self.arrow_left_timer += dt
            if self.arrow_left_timer > 1.2:
                self.arrow_left_active = False

        if self.arrow_right_active:
            self.arrow_right_timer += dt

        if self.phase == "success":
            self.success_timer += dt

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, surface):
        # Solid black background for legibility
        surface.fill((0, 0, 0))

        # Three columns
        self._draw_column_left(surface)
        self._draw_column_center(surface)
        self._draw_column_right(surface)

        # Arrows between columns
        self._draw_arrows(surface)

        # Bottom: final key display
        self._draw_final_key(surface)

        # Confirm button
        if self.phase == "interact":
            self._draw_button(surface, self.btn_rect, "CONFIRMAR CLAVE",
                              self.btn_hovered, C_NEON)

        # Bottom bar buttons
        self._draw_button(surface, self.back_rect, "< VOLVER",
                          self.back_hovered, C_ACCENT, small=True)
        if self.phase == "interact":
            self._draw_button(surface, self.hint_rect, "PISTA",
                              self.hint_hovered, C_AMBER, small=True)

        # Transmit indicator
        self._draw_transmit_indicator(surface)

        # Success overlay
        if self.phase == "success" and self.success_timer > 0.5:
            self._draw_success_overlay(surface)

        # HUD
        self.hud.draw(surface)

        # Dialogue on top
        self.dialogue.draw(surface)

    # ------------------------------------------------------------------
    # Color square drawing helper
    # ------------------------------------------------------------------

    def _draw_color_square(self, surface, x, y, color, size=_COLOR_SQ, label=None):
        """Draw a colored square with optional label below."""
        pygame.draw.rect(surface, color, (x, y, size, size))
        pygame.draw.rect(surface, C_WHITE, (x, y, size, size), 1)
        if label:
            lbl = self.font_edu.render(label, True, C_TEXT_SEC)
            surface.blit(lbl, (x + size // 2 - lbl.get_width() // 2, y + size + 3))

    def _draw_mix_equation(self, surface, x, y, c1, c2, c_result, size=36):
        """Draw: [c1] + [c2] = [c_result] as color squares."""
        sq = size
        gap = 6
        self._draw_color_square(surface, x, y, c1, sq)
        plus = self.font_label.render("+", True, C_WHITE)
        surface.blit(plus, (x + sq + gap, y + sq // 2 - plus.get_height() // 2))
        x2 = x + sq + gap + plus.get_width() + gap
        self._draw_color_square(surface, x2, y, c2, sq)
        eq = self.font_label.render("=", True, C_WHITE)
        x3 = x2 + sq + gap
        surface.blit(eq, (x3, y + sq // 2 - eq.get_height() // 2))
        x4 = x3 + eq.get_width() + gap
        self._draw_color_square(surface, x4, y, c_result, sq)

    # ------------------------------------------------------------------
    # Column panel helper
    # ------------------------------------------------------------------

    def _draw_column_panel(self, surface, x, y, w, h, title, color):
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        panel.fill((C_PANEL[0], C_PANEL[1], C_PANEL[2], 200))
        pygame.draw.rect(panel, (*color, 180), panel.get_rect(), 2)
        pygame.draw.line(panel, (*color, 200), (0, 0), (w, 0), 3)
        surface.blit(panel, (x, y))

        title_surf = self.font_title.render(title, True, color)
        surface.blit(title_surf, (x + w // 2 - title_surf.get_width() // 2, y + 8))

    # ------------------------------------------------------------------
    # LEFT COLUMN: Agent A (player)
    # ------------------------------------------------------------------

    def _draw_column_left(self, surface):
        x, y, w, h = _COL_LEFT_X, _COL_TOP, _COL_W, 320
        self._draw_column_panel(surface, x, y, w, h, "AGENTE A -- TU", C_NEON)

        # Secret color display
        cy = y + 34
        lbl = self.font_label.render("Tu color secreto:", True, C_TEXT_SEC)
        surface.blit(lbl, (x + 16, cy))
        self._draw_color_square(surface, x + 200, cy - 4, self.secret_color_a, 40)

        # Slider for secret number
        label = self.font_label.render("Secreto a:", True, C_TEXT_SEC)
        surface.blit(label, (x + 16, _SLIDER_Y - 28))

        # Slider track
        pygame.draw.rect(surface, C_BORDER,
                         (self.slider_x, _SLIDER_Y, _SLIDER_W, _SLIDER_H), 0, 4)
        # Filled portion
        fill_w = self.handle_rect.centerx - self.slider_x
        if fill_w > 0:
            pygame.draw.rect(surface, C_NEON,
                             (self.slider_x, _SLIDER_Y, fill_w, _SLIDER_H), 0, 4)

        # Tick marks
        for i in range(20):
            t = i / 19.0
            tx = self.slider_x + int(t * (_SLIDER_W - _HANDLE_W)) + _HANDLE_W // 2
            if (i + 1) % 5 == 0:
                pygame.draw.line(surface, C_TEXT_HINT,
                                 (tx, _SLIDER_Y + _SLIDER_H + 2),
                                 (tx, _SLIDER_Y + _SLIDER_H + 8), 1)
                num = self.font_edu.render(str(i + 1), True, C_TEXT_HINT)
                surface.blit(num, (tx - num.get_width() // 2,
                                   _SLIDER_Y + _SLIDER_H + 10))

        # Handle
        handle_color = C_NEON if self.dragging_slider else C_ACCENT
        pygame.draw.rect(surface, handle_color, self.handle_rect, 0, 3)
        pygame.draw.rect(surface, C_WHITE, self.handle_rect, 1, 3)

        # Current value
        val_surf = self.font_value.render(str(self.secret_a), True, C_NEON)
        surface.blit(val_surf, (self.slider_x + _SLIDER_W + 16, _SLIDER_Y - 10))

        # Color mixing visualization: base + secret = mixed
        mix_y = _SLIDER_Y + 48
        mix_lbl = self.font_edu.render("Mezcla:", True, C_TEXT_SEC)
        surface.blit(mix_lbl, (x + 16, mix_y))
        self._draw_mix_equation(surface, x + 16, mix_y + 16,
                                _BASE_COLOR, self.secret_color_a,
                                self.mixed_color_a, 30)

        # Math formula
        cy2 = mix_y + 58
        a_label = self.font_math.render(
            f"A = {_G}^{self.secret_a} mod {_P}", True, C_TEXT_SEC)
        surface.blit(a_label, (x + 16, cy2))
        a_val = self.font_big.render(f"A = {self.a_public}", True, C_NEON)
        surface.blit(a_val, (x + 16, cy2 + 20))

    # ------------------------------------------------------------------
    # CENTER COLUMN: Public channel
    # ------------------------------------------------------------------

    def _draw_column_center(self, surface):
        x, y, w, h = _COL_CENTER_X, _COL_TOP, _COL_W, 320
        self._draw_column_panel(surface, x, y, w, h, "CANAL PUBLICO", C_ACCENT)

        # Public parameters
        cy = y + 34
        base_lbl = self.font_label.render("Color base (publico):", True, C_TEXT_PRI)
        surface.blit(base_lbl, (x + 16, cy))
        self._draw_color_square(surface, x + 240, cy - 4, _BASE_COLOR, 36)

        cy += 28
        g_text = self.font_label.render(f"g = {_G}  (base)", True, C_TEXT_PRI)
        surface.blit(g_text, (x + w // 2 - g_text.get_width() // 2, cy))
        p_text = self.font_label.render(f"p = {_P}  (primo)", True, C_TEXT_PRI)
        surface.blit(p_text, (x + w // 2 - p_text.get_width() // 2, cy + 20))

        # Divider
        div_y = cy + 50
        pygame.draw.line(surface, C_BORDER, (x + 16, div_y), (x + w - 16, div_y), 1)

        # Public values with color squares
        pub_y = div_y + 12
        a_pub = self.font_math.render(f"A (publico) = {self.a_public}", True, C_NEON)
        surface.blit(a_pub, (x + 16, pub_y))
        self._draw_color_square(surface, x + w - 60, pub_y - 2, self.mixed_color_a, 24)

        b_pub = self.font_math.render(f"B (publico) = {_B_PUBLIC}", True, C_RED)
        surface.blit(b_pub, (x + 16, pub_y + 30))
        self._draw_color_square(surface, x + w - 60, pub_y + 28, self.mixed_color_b, 24)

        # Warning text
        warn_y = pub_y + 70
        lines = [
            "Los colores mezclados viajan",
            "por el canal publico.",
            "Pero nadie puede separar",
            "los colores originales.",
        ]
        for i, line in enumerate(lines):
            warn = self.font_channel.render(line, True, C_TEXT_HINT)
            surface.blit(warn, (x + w // 2 - warn.get_width() // 2, warn_y + i * 15))

    # ------------------------------------------------------------------
    # RIGHT COLUMN: Agent B (suspect)
    # ------------------------------------------------------------------

    def _draw_column_right(self, surface):
        x, y, w, h = _COL_RIGHT_X, _COL_TOP, _COL_W, 320
        self._draw_column_panel(surface, x, y, w, h, "AGENTE B -- SOSPECHOSO", C_RED)

        cy = y + 34
        # Secret hidden
        sec_lbl = self.font_label.render("Color secreto: ???", True, C_RED)
        surface.blit(sec_lbl, (x + 16, cy))
        # Draw a mystery square with question marks
        qx = x + 230
        pygame.draw.rect(surface, C_PANEL, (qx, cy - 4, 40, 40))
        pygame.draw.rect(surface, C_RED, (qx, cy - 4, 40, 40), 2)
        q = self.font_label.render("?", True, C_RED)
        surface.blit(q, (qx + 15, cy + 6))

        # Color mixing (hidden secret)
        mix_y = cy + 48
        mix_lbl = self.font_edu.render("Mezcla:", True, C_TEXT_SEC)
        surface.blit(mix_lbl, (x + 16, mix_y))
        # Show: base + ??? = mixed_b
        sq = 30
        gap = 6
        mx = x + 16
        self._draw_color_square(surface, mx, mix_y + 16, _BASE_COLOR, sq)
        plus = self.font_label.render("+", True, C_WHITE)
        surface.blit(plus, (mx + sq + gap, mix_y + 16 + sq // 2 - plus.get_height() // 2))
        mx2 = mx + sq + gap + plus.get_width() + gap
        # Hidden square
        pygame.draw.rect(surface, C_PANEL, (mx2, mix_y + 16, sq, sq))
        pygame.draw.rect(surface, C_RED, (mx2, mix_y + 16, sq, sq), 2)
        q2 = self.font_edu.render("?", True, C_RED)
        surface.blit(q2, (mx2 + sq // 2 - q2.get_width() // 2,
                          mix_y + 16 + sq // 2 - q2.get_height() // 2))
        eq = self.font_label.render("=", True, C_WHITE)
        mx3 = mx2 + sq + gap
        surface.blit(eq, (mx3, mix_y + 16 + sq // 2 - eq.get_height() // 2))
        mx4 = mx3 + eq.get_width() + gap
        self._draw_color_square(surface, mx4, mix_y + 16, self.mixed_color_b, sq)

        # Math
        cy2 = mix_y + 60
        b_label = self.font_math.render(
            f"B = {_G}^? mod {_P}", True, C_TEXT_SEC)
        surface.blit(b_label, (x + 16, cy2))
        b_val = self.font_big.render(f"B = {_B_PUBLIC}", True, C_RED)
        surface.blit(b_val, (x + 16, cy2 + 20))

        # Shared key hidden
        cy3 = cy2 + 52
        k_label = self.font_math.render("K = A^b mod p = ???", True, C_TEXT_SEC)
        surface.blit(k_label, (x + 16, cy3))

        if self.phase == "success":
            k_val = self.font_big.render(f"K = {self.shared_key_real}", True, C_AMBER)
        else:
            k_val = self.font_big.render("K = ???", True, C_TEXT_HINT)
        surface.blit(k_val, (x + 16, cy3 + 20))

    # ------------------------------------------------------------------
    # Final key display at bottom
    # ------------------------------------------------------------------

    def _draw_final_key(self, surface):
        bx = 30
        by = 420
        bw = WIDTH - 60
        bh = 190
        panel = pygame.Surface((bw, bh), pygame.SRCALPHA)
        panel.fill((C_PANEL[0], C_PANEL[1], C_PANEL[2], 200))
        pygame.draw.rect(panel, (*C_DH, 120), panel.get_rect(), 1)
        surface.blit(panel, (bx, by))

        # Title
        title = self.font_label.render(
            "TU CLAVE FINAL: mix(B_publico, tu_secreto) = K", True, C_NEON)
        surface.blit(title, (bx + 20, by + 12))

        # Show the color mixing: mixed_b + secret_a = final_color
        cy = by + 38
        lbl = self.font_edu.render("Color B publico + Tu secreto = Clave compartida:",
                                   True, C_TEXT_SEC)
        surface.blit(lbl, (bx + 20, cy))
        self._draw_mix_equation(surface, bx + 20, cy + 18,
                                self.mixed_color_b, self.secret_color_a,
                                self.final_color_player, 40)

        # Math
        k_math = self.font_math.render(
            f"K = B^a mod p = {_B_PUBLIC}^{self.secret_a} mod {_P} = "
            f"{self.shared_key_player}", True, C_AMBER)
        surface.blit(k_math, (bx + 20, cy + 68))

        # Show final color square large
        fsx = bx + bw - 180
        fsy = cy + 10
        self._draw_color_square(surface, fsx, fsy, self.final_color_player, 60,
                                label=f"K = {self.shared_key_player}")

        # Educational sidebar within this panel
        edu_x = bx + 400
        edu_y = by + 12
        edu_lines = [
            ("DIFFIE-HELLMAN (Metafora de color)", C_DH, True),
            ("", None, False),
            ("Cada agente mezcla su color secreto", C_TEXT_SEC, False),
            ("con la base publica (amarilla).", C_TEXT_SEC, False),
            ("Los colores mezclados viajan publicos.", C_TEXT_SEC, False),
            ("Al mezclar el color ajeno con tu secreto,", C_TEXT_SEC, False),
            ("ambos obtienen el MISMO color final.", C_NEON, False),
            ("", None, False),
            ("Nadie en el canal puede calcular K", C_TEXT_HINT, False),
            ("sin conocer a o b.", C_TEXT_HINT, False),
        ]
        for text, color, bold in edu_lines:
            if not text:
                edu_y += 5
                continue
            font = self.font_label if bold else self.font_edu
            txt = font.render(text, True, color)
            surface.blit(txt, (edu_x, edu_y))
            edu_y += txt.get_height() + 2

    # ------------------------------------------------------------------
    # Arrows between columns
    # ------------------------------------------------------------------

    def _draw_arrows(self, surface):
        mid_y_top = _COL_TOP + 180
        mid_y_bot = _COL_TOP + 210
        left_end = _COL_LEFT_X + _COL_W
        center_start = _COL_CENTER_X
        center_end = _COL_CENTER_X + _COL_W
        right_start = _COL_RIGHT_X

        # Left -> Center (sending A, green / neon)
        if self.arrow_left_active:
            progress = min(1.0, self.arrow_left_timer / 1.0)
            ax = left_end + int(progress * (center_start - left_end))
            # Animated colored blob
            pygame.draw.line(surface, C_NEON, (left_end + 4, mid_y_top), (ax, mid_y_top), 2)
            pygame.draw.polygon(surface, C_NEON, [
                (ax, mid_y_top),
                (ax - 8, mid_y_top - 5),
                (ax - 8, mid_y_top + 5),
            ])
            # Small color blob traveling
            blob_x = left_end + int(progress * (center_start - left_end - 10))
            pygame.draw.circle(surface, self.mixed_color_a,
                               (blob_x, mid_y_top), 6)
            pygame.draw.circle(surface, C_WHITE, (blob_x, mid_y_top), 6, 1)
            if progress < 0.8:
                lbl = self.font_edu.render("enviando A...", True, C_NEON)
                surface.blit(lbl, (left_end + 8, mid_y_top - 18))
        else:
            pygame.draw.line(surface, C_NEON,
                             (left_end + 4, mid_y_top),
                             (center_start - 4, mid_y_top), 1)
            _draw_arrowhead(surface, center_start - 4, mid_y_top, C_NEON)

        # Center -> Left (receiving B, red)
        pygame.draw.line(surface, C_RED,
                         (center_start - 4, mid_y_bot),
                         (left_end + 4, mid_y_bot), 1)
        _draw_arrowhead_left(surface, left_end + 4, mid_y_bot, C_RED)
        # Color blob for B
        blob_bx = (center_start + left_end) // 2
        pygame.draw.circle(surface, self.mixed_color_b, (blob_bx, mid_y_bot), 6)
        pygame.draw.circle(surface, C_WHITE, (blob_bx, mid_y_bot), 6, 1)
        lbl_b = self.font_edu.render(f"B={_B_PUBLIC}", True, C_RED)
        surface.blit(lbl_b, (left_end + 8, mid_y_bot + 4))

        # Right -> Center (B published)
        pygame.draw.line(surface, C_RED,
                         (right_start - 4, mid_y_top),
                         (center_end + 4, mid_y_top), 1)
        _draw_arrowhead_left(surface, center_end + 4, mid_y_top, C_RED)

        # Center -> Right (A published)
        pygame.draw.line(surface, C_NEON,
                         (center_end + 4, mid_y_bot),
                         (right_start - 4, mid_y_bot), 1)
        _draw_arrowhead(surface, right_start - 4, mid_y_bot, C_NEON)

    # ------------------------------------------------------------------
    # Transmit indicator
    # ------------------------------------------------------------------

    def _draw_transmit_indicator(self, surface):
        blink_on = math.sin(self.transmit_blink * 4.0) > 0
        color = C_RED if blink_on else C_TEXT_HINT
        indicator_x = WIDTH - 240
        indicator_y = 52

        pygame.draw.circle(surface, color, (indicator_x, indicator_y + 6), 5)
        txt = self.font_label.render("TRANSMISION ACTIVA", True, color)
        surface.blit(txt, (indicator_x + 12, indicator_y))

    # ------------------------------------------------------------------
    # Buttons
    # ------------------------------------------------------------------

    def _draw_button(self, surface, rect, text, hovered, color, small=False):
        panel = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        bg_alpha = 200 if hovered else 150
        panel.fill((C_PANEL[0], C_PANEL[1], C_PANEL[2], bg_alpha))
        border_c = tuple(min(c + 40, 255) for c in color) if hovered else color
        bw = 2 if hovered else 1
        pygame.draw.rect(panel, (*border_c, 220), panel.get_rect(), bw)
        surface.blit(panel, rect.topleft)

        font = self.font_small if small else self.font_btn
        lbl = font.render(text, True, color if not hovered else C_WHITE)
        surface.blit(lbl, (
            rect.centerx - lbl.get_width() // 2,
            rect.centery - lbl.get_height() // 2
        ))

    # ------------------------------------------------------------------
    # Success overlay
    # ------------------------------------------------------------------

    def _draw_success_overlay(self, surface):
        alpha = min(200, int((self.success_timer - 0.5) * 300))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, alpha))
        surface.blit(overlay, (0, 0))

        if self.success_timer > 1.0:
            # Green glow text
            txt = self.font_value.render("CLAVE COMPARTIDA VERIFICADA", True, C_NEON)
            tx = WIDTH // 2 - txt.get_width() // 2
            ty = HEIGHT // 2 - 100

            glow = self.font_value.render("CLAVE COMPARTIDA VERIFICADA", True, C_NEON)
            glow.set_alpha(60)
            surface.blit(glow, (tx - 2, ty - 1))
            surface.blit(glow, (tx + 2, ty + 1))
            surface.blit(txt, (tx, ty))

            # Matching keys
            key_text = self.font_big.render(
                f"K(A) = {self.shared_key_player}  ==  K(B) = {self.shared_key_real}",
                True, C_AMBER)
            surface.blit(key_text, (
                WIDTH // 2 - key_text.get_width() // 2, ty + 50
            ))

            # Matching colors side by side
            cx = WIDTH // 2 - 70
            cy = ty + 90
            self._draw_color_square(surface, cx, cy, self.final_color_player, 50,
                                    label="Tu K")
            eq_s = self.font_big.render("=", True, C_NEON)
            surface.blit(eq_s, (cx + 58, cy + 14))
            self._draw_color_square(surface, cx + 80, cy, self.final_color_real, 50,
                                    label="K de B")

            # Score
            score = self.manager.scores.get("diffie_hellman", 0)
            score_txt = self.font_label.render(
                f"Puntuacion: {score} pts", True, C_TEXT_SEC)
            surface.blit(score_txt, (
                WIDTH // 2 - score_txt.get_width() // 2, ty + 170
            ))


# ------------------------------------------------------------------
# Module-level helper drawing functions
# ------------------------------------------------------------------

def _draw_arrowhead(surface, x, y, color):
    pygame.draw.polygon(surface, color, [
        (x, y),
        (x - 7, y - 4),
        (x - 7, y + 4),
    ])


def _draw_arrowhead_left(surface, x, y, color):
    pygame.draw.polygon(surface, color, [
        (x, y),
        (x + 7, y - 4),
        (x + 7, y + 4),
    ])
