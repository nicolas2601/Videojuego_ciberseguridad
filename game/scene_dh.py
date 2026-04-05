import pygame
import math
from game.constants import (WIDTH, HEIGHT, C_BG, C_BG2, C_BG3, C_BORDER, C_TEXT_PRI,
    C_TEXT_SEC, C_TEXT_HINT, C_ACCENT, C_GREEN, C_RED, C_DH, C_PANEL, C_WHITE, C_AMBER)
from game.ui.dialogue import DialogueBox
from game.ui.hud import HUD
from game.ui.tile_renderer import get_separate_sprite, draw_floor
from crypto.dh_utils import dh_public, dh_shared_key


# DH parameters
_G = 5
_P = 23
_B_SECRET = 15
_B_PUBLIC = dh_public(_G, _P, _B_SECRET)

# Layout constants
_COL_LEFT_X = 40
_COL_CENTER_X = 440
_COL_RIGHT_X = 860
_COL_W = 380
_COL_TOP = 80
_SLIDER_Y = 260
_SLIDER_W = 300
_SLIDER_H = 12
_HANDLE_W = 18
_HANDLE_H = 28
_BUTTON_W = 280
_BUTTON_H = 48


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
        self.debriefing_shown = False

        # Slider rect
        self.slider_x = _COL_LEFT_X + (_COL_W - _SLIDER_W) // 2
        self.slider_rect = pygame.Rect(self.slider_x, _SLIDER_Y, _SLIDER_W, _SLIDER_H)
        self.handle_rect = pygame.Rect(0, 0, _HANDLE_W, _HANDLE_H)
        self._update_handle_pos()

        # Confirm button
        self.btn_rect = pygame.Rect(
            WIDTH // 2 - _BUTTON_W // 2, 620,
            _BUTTON_W, _BUTTON_H
        )
        self.btn_hovered = False

        # Back button
        self.back_rect = pygame.Rect(20, HEIGHT - 44, 140, 32)
        self.back_hovered = False

        # Hint button
        self.hint_rect = pygame.Rect(WIDTH - 160, HEIGHT - 44, 140, 32)
        self.hint_hovered = False

        # Pre-render floor
        self.floor_surf = pygame.Surface((WIDTH, HEIGHT))
        draw_floor(self.floor_surf, tile_col=0, tile_row=0)
        dark = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dark.fill((0, 0, 0, 180))
        self.floor_surf.blit(dark, (0, 0))

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

        # Load optional decoration
        self.decor_sprites = []
        for name, scale, x, y in [
            ("Sprite-0005.png", 2, 80, 500),
            ("Sprite-0022.png", 2, 1080, 500),
        ]:
            try:
                img = get_separate_sprite(name, scale=scale)
                self.decor_sprites.append((img, x, y))
            except Exception:
                pass

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
            # Should not happen with correct DH math, but safety fallback
            msgs = self.manager.dialogues.get("diffie_hellman", {}).get("error", [])
            if msgs:
                self.dialogue.show(msgs)

    def _show_hint(self):
        self.hints_used += 1
        hint_msgs = [
            {"speaker": "CONTROL", "text": "Cualquier valor de 'a' funciona. DH siempre produce la misma clave compartida."},
            {"speaker": "CONTROL", "text": "Lo importante: ni 'a' ni 'b' viajan por el canal. Solo A y B publicos."},
        ]
        self.dialogue.show(hint_msgs)

    def _calculate_score(self):
        base = 100
        penalty = self.hints_used * 15
        time_penalty = max(0, int(self.elapsed - 30) // 10) * 5
        return max(10, base - penalty - time_penalty)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, dt):
        self.dialogue.update(dt)

        if self.phase == "interact":
            self.elapsed += dt

        # Animation timers
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
        surface.blit(self.floor_surf, (0, 0))

        # Decorative sprites
        for img, x, y in self.decor_sprites:
            faded = img.copy()
            faded.set_alpha(25)
            surface.blit(faded, (x, y))

        # Three columns
        self._draw_column_left(surface)
        self._draw_column_center(surface)
        self._draw_column_right(surface)

        # Arrows between columns
        self._draw_arrows(surface)

        # Educational sidebar
        self._draw_sidebar(surface)

        # Confirm button
        if self.phase == "interact":
            self._draw_button(surface, self.btn_rect, "CONFIRMAR CLAVE",
                              self.btn_hovered, C_DH)

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
    # Column renderers
    # ------------------------------------------------------------------

    def _draw_column_panel(self, surface, x, y, w, h, title, color):
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        panel.fill((C_PANEL[0], C_PANEL[1], C_PANEL[2], 200))
        pygame.draw.rect(panel, (*color, 180), panel.get_rect(), 2)
        pygame.draw.line(panel, (*color, 200), (0, 0), (w, 0), 3)
        surface.blit(panel, (x, y))

        title_surf = self.font_title.render(title, True, color)
        surface.blit(title_surf, (x + w // 2 - title_surf.get_width() // 2, y + 10))

    def _draw_column_left(self, surface):
        x, y, w, h = _COL_LEFT_X, _COL_TOP, _COL_W, 230
        self._draw_column_panel(surface, x, y, w, h, "AGENTE A -- TU", C_GREEN)

        # Secret slider
        label = self.font_label.render("Secreto a:", True, C_TEXT_SEC)
        surface.blit(label, (x + 20, _SLIDER_Y - 30))

        # Slider track
        track_color = C_BORDER
        pygame.draw.rect(surface, track_color,
                         (self.slider_x, _SLIDER_Y, _SLIDER_W, _SLIDER_H), 0, 4)

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
        handle_color = C_DH if self.dragging_slider else C_ACCENT
        pygame.draw.rect(surface, handle_color, self.handle_rect, 0, 3)
        pygame.draw.rect(surface, C_WHITE, self.handle_rect, 1, 3)

        # Current value display
        val_surf = self.font_value.render(str(self.secret_a), True, C_DH)
        surface.blit(val_surf, (
            self.slider_x + _SLIDER_W + 16,
            _SLIDER_Y - 10
        ))

        # Calculated A
        cy = _SLIDER_Y + 50
        a_label = self.font_math.render(
            f"A = g^a mod p = {_G}^{self.secret_a} mod {_P}", True, C_TEXT_SEC)
        surface.blit(a_label, (x + 20, cy))
        a_val = self.font_big.render(f"A = {self.a_public}", True, C_GREEN)
        surface.blit(a_val, (x + 20, cy + 22))

        # Shared key
        cy2 = cy + 56
        k_label = self.font_math.render(
            f"K = B^a mod p = {_B_PUBLIC}^{self.secret_a} mod {_P}", True, C_TEXT_SEC)
        surface.blit(k_label, (x + 20, cy2))
        k_val = self.font_big.render(f"K = {self.shared_key_player}", True, C_AMBER)
        surface.blit(k_val, (x + 20, cy2 + 22))

    def _draw_column_center(self, surface):
        x, y, w, h = _COL_CENTER_X, _COL_TOP, _COL_W, 230
        self._draw_column_panel(surface, x, y, w, h, "CANAL PUBLICO", C_ACCENT)

        # Parameters
        cy = y + 40
        g_text = self.font_label.render(f"g = {_G}  (base)", True, C_TEXT_PRI)
        surface.blit(g_text, (x + w // 2 - g_text.get_width() // 2, cy))
        p_text = self.font_label.render(f"p = {_P}  (primo)", True, C_TEXT_PRI)
        surface.blit(p_text, (x + w // 2 - p_text.get_width() // 2, cy + 24))

        # Divider
        div_y = cy + 60
        pygame.draw.line(surface, C_BORDER, (x + 20, div_y), (x + w - 20, div_y), 1)

        # Public values
        pub_y = div_y + 14
        a_pub = self.font_math.render(f"A (publico) = {self.a_public}", True, C_GREEN)
        surface.blit(a_pub, (x + w // 2 - a_pub.get_width() // 2, pub_y))

        b_pub = self.font_math.render(f"B (publico) = {_B_PUBLIC}", True, C_RED)
        surface.blit(b_pub, (x + w // 2 - b_pub.get_width() // 2, pub_y + 28))

        # Warning text
        warn_y = pub_y + 68
        warn = self.font_edu.render("Visible para cualquier interceptor", True, C_TEXT_HINT)
        surface.blit(warn, (x + w // 2 - warn.get_width() // 2, warn_y))

    def _draw_column_right(self, surface):
        x, y, w, h = _COL_RIGHT_X, _COL_TOP, _COL_W, 230
        self._draw_column_panel(surface, x, y, w, h, "AGENTE B -- SOSPECHOSO", C_RED)

        cy = y + 44
        # Secret hidden
        sec = self.font_label.render("Secreto: ???", True, C_RED)
        surface.blit(sec, (x + 20, cy))

        # B public
        cy2 = cy + 36
        b_label = self.font_math.render(
            f"B = g^b mod p = {_G}^? mod {_P}", True, C_TEXT_SEC)
        surface.blit(b_label, (x + 20, cy2))
        b_val = self.font_big.render(f"B = {_B_PUBLIC}", True, C_RED)
        surface.blit(b_val, (x + 20, cy2 + 22))

        # Shared key hidden
        cy3 = cy2 + 58
        k_label = self.font_math.render("K = A^b mod p = ???", True, C_TEXT_SEC)
        surface.blit(k_label, (x + 20, cy3))

        if self.phase == "success":
            k_val = self.font_big.render(f"K = {self.shared_key_real}", True, C_AMBER)
        else:
            k_val = self.font_big.render("K = ???", True, C_TEXT_HINT)
        surface.blit(k_val, (x + 20, cy3 + 22))

    # ------------------------------------------------------------------
    # Arrows
    # ------------------------------------------------------------------

    def _draw_arrows(self, surface):
        mid_y_top = _COL_TOP + 130
        mid_y_bot = _COL_TOP + 170
        left_end = _COL_LEFT_X + _COL_W
        center_start = _COL_CENTER_X
        center_end = _COL_CENTER_X + _COL_W
        right_start = _COL_RIGHT_X

        # Left -> Center arrow (sending A)
        if self.arrow_left_active:
            progress = min(1.0, self.arrow_left_timer / 1.0)
            ax = left_end + int(progress * (center_start - left_end))
            color = C_GREEN
            # Arrow line
            pygame.draw.line(surface, color, (left_end + 4, mid_y_top), (ax, mid_y_top), 2)
            # Arrowhead
            pygame.draw.polygon(surface, color, [
                (ax, mid_y_top),
                (ax - 8, mid_y_top - 5),
                (ax - 8, mid_y_top + 5),
            ])
            # Label
            if progress < 0.8:
                lbl = self.font_edu.render("enviando A...", True, C_GREEN)
                surface.blit(lbl, (left_end + 8, mid_y_top - 18))
        else:
            # Static completed arrow
            pygame.draw.line(surface, (*C_GREEN, 80), (left_end + 4, mid_y_top),
                             (center_start - 4, mid_y_top), 1)
            _draw_arrowhead(surface, center_start - 4, mid_y_top, C_GREEN)

        # Center -> Left arrow (receiving B)
        color_b = (*C_RED, 160) if not self.arrow_right_active else C_RED
        pygame.draw.line(surface, C_RED,
                         (center_start - 4, mid_y_bot),
                         (left_end + 4, mid_y_bot), 1)
        _draw_arrowhead_left(surface, left_end + 4, mid_y_bot, C_RED)
        lbl_b = self.font_edu.render(f"B={_B_PUBLIC}", True, C_RED)
        surface.blit(lbl_b, (left_end + 8, mid_y_bot + 4))

        # Right -> Center arrow (B published)
        pygame.draw.line(surface, C_RED,
                         (right_start - 4, mid_y_top),
                         (center_end + 4, mid_y_top), 1)
        _draw_arrowhead_left(surface, center_end + 4, mid_y_top, C_RED)

        # Center -> Right arrow (A published)
        pygame.draw.line(surface, C_GREEN,
                         (center_end + 4, mid_y_bot),
                         (right_start - 4, mid_y_bot), 1)
        _draw_arrowhead(surface, right_start - 4, mid_y_bot, C_GREEN)

    # ------------------------------------------------------------------
    # Educational sidebar
    # ------------------------------------------------------------------

    def _draw_sidebar(self, surface):
        sx, sy = 440, 340
        sw, sh = 380, 240
        panel = pygame.Surface((sw, sh), pygame.SRCALPHA)
        panel.fill((C_PANEL[0], C_PANEL[1], C_PANEL[2], 180))
        pygame.draw.rect(panel, (*C_DH, 120), panel.get_rect(), 1)
        surface.blit(panel, (sx, sy))

        lines = [
            ("DIFFIE-HELLMAN", C_DH, True),
            ("", None, False),
            ("g, p: parametros publicos", C_TEXT_SEC, False),
            ("a, b: secretos privados", C_TEXT_SEC, False),
            ("", None, False),
            ("A = g^a mod p  (publico)", C_GREEN, False),
            ("B = g^b mod p  (publico)", C_RED, False),
            ("", None, False),
            ("K = B^a = A^b  (compartida!)", C_AMBER, False),
            ("", None, False),
            ("Nadie en el canal puede", C_TEXT_HINT, False),
            ("calcular K sin a o b", C_TEXT_HINT, False),
        ]

        cy = sy + 10
        for text, color, bold in lines:
            if not text:
                cy += 6
                continue
            font = self.font_label if bold else self.font_edu
            txt = font.render(text, True, color)
            surface.blit(txt, (sx + 16, cy))
            cy += txt.get_height() + 3

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
        alpha = min(180, int((self.success_timer - 0.5) * 300))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, alpha))
        surface.blit(overlay, (0, 0))

        if self.success_timer > 1.0:
            # Green glow text
            txt = self.font_value.render("CLAVE COMPARTIDA VERIFICADA", True, C_GREEN)
            tx = WIDTH // 2 - txt.get_width() // 2
            ty = HEIGHT // 2 - 60
            # Glow
            glow = self.font_value.render("CLAVE COMPARTIDA VERIFICADA", True, C_GREEN)
            glow.set_alpha(60)
            surface.blit(glow, (tx - 2, ty - 1))
            surface.blit(glow, (tx + 2, ty + 1))
            surface.blit(txt, (tx, ty))

            # Show matching keys
            key_text = self.font_big.render(
                f"K(A) = {self.shared_key_player}  ==  K(B) = {self.shared_key_real}",
                True, C_AMBER)
            surface.blit(key_text, (
                WIDTH // 2 - key_text.get_width() // 2,
                ty + 50
            ))

            # Score
            score = self.manager.scores.get("diffie_hellman", 0)
            score_txt = self.font_label.render(
                f"Puntuacion: {score} pts", True, C_TEXT_SEC)
            surface.blit(score_txt, (
                WIDTH // 2 - score_txt.get_width() // 2,
                ty + 90
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
