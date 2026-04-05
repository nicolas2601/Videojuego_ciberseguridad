import pygame
import random
import math
import time

from game.constants import (
    WIDTH, HEIGHT, C_BG, C_BG2, C_BG3, C_BORDER, C_TEXT_PRI,
    C_TEXT_SEC, C_TEXT_HINT, C_ACCENT, C_GREEN, C_RED, C_NEON, C_WHITE,
    C_PANEL, C_BASE64, HINTS_CONFIG,
)
from game.ui.draw_assets import (
    draw_server_rack, draw_office_floor, draw_wall,
    draw_text_box, word_wrap,
)
from game.ui.dialogue import DialogueBox
from game.ui.hud import HUD
from crypto.b64_utils import decode_partial


# ---------------------------------------------------------------------------
# Draggable block representing a 4-char Base64 fragment
# ---------------------------------------------------------------------------
class _Block:
    W = 120
    H = 50
    CORNER = 8

    def __init__(self, text, correct_index):
        self.text = text
        self.correct_index = correct_index
        self.x = 0.0
        self.y = 0.0
        self.home_x = 0.0
        self.home_y = 0.0
        self.dragging = False
        self.locked = False
        self.slot_index = -1
        self.flash_timer = 0.0
        self.lock_pulse = 0.0
        self.font = pygame.font.SysFont("monospace", 22, bold=True)

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.W, self.H)

    def draw(self, surface):
        r = self.rect
        # Shadow when dragging
        if self.dragging:
            shadow = pygame.Surface((r.w + 6, r.h + 6), pygame.SRCALPHA)
            pygame.draw.rect(shadow, (0, 0, 0, 60), shadow.get_rect(),
                             border_radius=self.CORNER)
            surface.blit(shadow, (r.x + 3, r.y + 5))

        # Body
        body = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
        fill = (*C_BG2, 230) if not self.locked else (*C_BG3, 240)
        pygame.draw.rect(body, fill, body.get_rect(), border_radius=self.CORNER)

        # Border colour
        if self.flash_timer > 0:
            border_col = C_RED
        elif self.locked:
            border_col = C_GREEN
        elif self.dragging:
            border_col = C_BASE64
        else:
            border_col = C_BORDER

        border_w = 3 if self.lock_pulse > 0 else 2
        pygame.draw.rect(body, border_col, body.get_rect(), border_w,
                         border_radius=self.CORNER)

        # Green pulse glow
        if self.lock_pulse > 0:
            glow = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
            a = int(80 * self.lock_pulse)
            pygame.draw.rect(glow, (*C_GREEN, a), glow.get_rect(),
                             border_radius=self.CORNER)
            body.blit(glow, (0, 0))

        surface.blit(body, r.topleft)

        # Text
        txt = self.font.render(self.text, True,
                               C_WHITE if self.locked else C_BASE64)
        tx = r.centerx - txt.get_width() // 2
        ty = r.centery - txt.get_height() // 2
        surface.blit(txt, (tx, ty))

    def update(self, dt):
        if self.flash_timer > 0:
            self.flash_timer = max(0, self.flash_timer - dt)
        if self.lock_pulse > 0:
            self.lock_pulse = max(0, self.lock_pulse - dt * 1.5)


# ---------------------------------------------------------------------------
# Base64 reference table data
# ---------------------------------------------------------------------------
_B64_CHARS = ("ABCDEFGHIJKLMNOPQRSTUVWXYZ"
              "abcdefghijklmnopqrstuvwxyz"
              "0123456789+/")


def _build_ref_lines():
    """Build the base64 lookup table lines for the in-game panel."""
    lines = ["BASE64 TABLA DE REFERENCIA"]
    # Character rows, 6 per line
    for row_start in range(0, 64, 6):
        parts = []
        for j in range(6):
            idx = row_start + j
            if idx < 64:
                ch = _B64_CHARS[idx]
                parts.append(f"{ch}={idx:<3}")
        lines.append(" ".join(parts))
    lines.append("")
    lines.append("Cada 4 chars = 3 bytes ASCII")
    lines.append("")
    lines.append("SGVs -> S(18) G(6) V(21) s(44)")
    lines.append("  -> 010010 000110 010101 101100")
    lines.append("  -> 01001000 01100101 01101100")
    lines.append("  ->    H        e        l")
    lines.append("")
    lines.append("'=' = padding (bytes faltantes)")
    return lines


_REF_LINES = _build_ref_lines()


# ---------------------------------------------------------------------------
# Base64Scene -- drag-and-drop ordering puzzle
# ---------------------------------------------------------------------------
class Base64Scene:
    POOL_X = 80
    POOL_Y = 140
    POOL_W = 300
    SLOT_X = 500
    SLOT_Y = 140
    SLOT_GAP = 80
    RESULT_Y = 540

    def __init__(self, manager):
        self.manager = manager
        self.puzzle = manager.puzzles["base64"]
        self.dialogues_data = manager.dialogues["base64"]

        # Difficulty config
        config = HINTS_CONFIG[self.manager.difficulty]
        self.free_hints = config["free_hints"]
        self.visual_aids = config["visual_aids"]

        # Fonts
        self.font_slot_label = pygame.font.SysFont("monospace", 13, bold=True)
        self.font_result_label = pygame.font.SysFont("monospace", 16, bold=True)
        self.font_result_value = pygame.font.SysFont("monospace", 22, bold=True)
        self.font_ref = pygame.font.SysFont("monospace", 11)
        self.font_ref_title = pygame.font.SysFont("monospace", 12, bold=True)
        self.font_hint_btn = pygame.font.SysFont("monospace", 13, bold=True)
        self.font_debrief_title = pygame.font.SysFont("monospace", 18, bold=True)
        self.font_debrief = pygame.font.SysFont("monospace", 14)
        self.font_debrief_btn = pygame.font.SysFont("monospace", 15, bold=True)

        # HUD + dialogue
        self.hud = HUD()
        self.hud.set_info("ESCENA 02 -- SALA DE SERVIDORES",
                          "CAPA 2/4 -- BASE64")
        self.dialogue = DialogueBox()

        # Blocks
        block_texts = list(self.puzzle["blocks"])
        self.blocks = [_Block(t, i) for i, t in enumerate(block_texts)]
        random.shuffle(self.blocks)
        self._layout_pool()

        # Slots
        self.slots = [None, None, None, None]
        self.slot_rects = []
        for i in range(4):
            rx = self.SLOT_X
            ry = self.SLOT_Y + i * self.SLOT_GAP
            self.slot_rects.append(pygame.Rect(rx, ry, _Block.W, _Block.H))

        # Drag state
        self.dragged_block = None
        self.drag_offset_x = 0
        self.drag_offset_y = 0

        # Decoded result text
        self.decoded_text = ""

        # Timing / scoring
        self.start_time = time.time()
        self.time_elapsed = 0.0
        self.hints_used = 0
        self.failed_attempts = 0
        self.completed = False

        # Hint buttons (3)
        self.hint_rects = []
        for i in range(3):
            bx = self.POOL_X + i * 105
            by = self.RESULT_Y + 80
            self.hint_rects.append(pygame.Rect(bx, by, 95, 30))
        self.hints_revealed = [False, False, False]

        # VOLVER button
        self.btn_volver = pygame.Rect(20, HEIGHT - 70, 140, 44)

        # Debriefing popup
        self.show_debrief = False
        self.debrief_rect = pygame.Rect(
            WIDTH // 2 - 280, HEIGHT // 2 - 180, 560, 360
        )
        self.debrief_close_rect = pygame.Rect(0, 0, 180, 40)
        self.debrief_close_rect.centerx = self.debrief_rect.centerx
        self.debrief_close_rect.y = self.debrief_rect.bottom - 60

        # Dashed border animation
        self.dash_offset = 0.0

        # Fade in
        self.fade_alpha = 255
        self.fade_timer = 0.0

        # Background (cached)
        self._bg_ready = False
        self._bg_surface = None

        # Reference table scroll offset
        self.ref_scroll = 0

        # Visual aid pulse
        self._aid_pulse = 0.0

        # Entrance dialogue
        self.phase = "dialogue_enter"
        self.dialogue.show(self.dialogues_data["enter"],
                           on_complete=self._enter_done)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _build_bg(self):
        """Render static background with pygame.draw only."""
        self._bg_surface = pygame.Surface((WIDTH, HEIGHT))
        draw_office_floor(self._bg_surface)
        draw_wall(self._bg_surface, 0, wall_h=50)

        # Dark overlay
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((*C_BG, 180))
        self._bg_surface.blit(overlay, (0, 0))

        # Server racks (drawn with pygame.draw)
        draw_server_rack(self._bg_surface, 30, 90, h=100)
        draw_server_rack(self._bg_surface, 70, 90, h=100)
        draw_server_rack(self._bg_surface, 1180, 90, h=100)
        draw_server_rack(self._bg_surface, 1220, 90, h=100)
        draw_server_rack(self._bg_surface, 30, 350, h=80)
        draw_server_rack(self._bg_surface, 1180, 350, h=80)

        self._bg_ready = True

    def _layout_pool(self):
        pool_blocks = [b for b in self.blocks
                       if b.slot_index == -1 and not b.locked]
        start_y = self.POOL_Y
        for i, b in enumerate(pool_blocks):
            b.home_x = self.POOL_X + 40
            b.home_y = start_y + i * 70
            if not b.dragging:
                b.x = b.home_x
                b.y = b.home_y

    def _enter_done(self):
        self.phase = "playing"

    def _update_decoded(self):
        parts = []
        for s in self.slots:
            parts.append(s.text if s else None)
        self.decoded_text = decode_partial(parts)

    def _check_completion(self):
        if any(s is None for s in self.slots):
            return
        for i, s in enumerate(self.slots):
            if s.correct_index != i:
                return
        # All correct
        self.completed = True
        self.time_elapsed = time.time() - self.start_time
        score = max(100 - int(self.time_elapsed / 10)
                    - self.hints_used * 15
                    - self.failed_attempts * 5, 10)
        self.manager.complete_puzzle("base64", score)
        self.dialogue.show(self.dialogues_data["success"],
                           on_complete=self._show_debrief)

    def _show_debrief(self):
        self.show_debrief = True

    def _slot_index_at(self, pos):
        for i, r in enumerate(self.slot_rects):
            if r.inflate(20, 20).collidepoint(pos):
                return i
        return -1

    # ------------------------------------------------------------------
    # event handling
    # ------------------------------------------------------------------
    def handle_event(self, event):
        # Debriefing popup close
        if self.show_debrief:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.debrief_close_rect.collidepoint(event.pos):
                    self.manager.change_scene("hub")
            return

        # Dialogue eats events
        if self.dialogue.active:
            self.dialogue.handle_event(event)
            return

        if self.completed:
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            # VOLVER button
            if self.btn_volver.collidepoint((mx, my)):
                self.manager.change_scene("hub")
                return

            # Hint buttons
            for i, hr in enumerate(self.hint_rects):
                if hr.collidepoint((mx, my)) and not self.hints_revealed[i]:
                    self.hints_revealed[i] = True
                    if i >= self.free_hints:
                        self.hints_used += 1
                    return

            # Drag and drop -- pick up block
            for b in reversed(self.blocks):
                if b.locked:
                    continue
                if b.rect.collidepoint(mx, my):
                    if b.slot_index >= 0:
                        self.slots[b.slot_index] = None
                        b.slot_index = -1
                        self._update_decoded()
                    b.dragging = True
                    self.drag_offset_x = b.x - mx
                    self.drag_offset_y = b.y - my
                    self.dragged_block = b
                    self.blocks.remove(b)
                    self.blocks.append(b)
                    break

        elif event.type == pygame.MOUSEMOTION:
            if self.dragged_block:
                mx, my = event.pos
                self.dragged_block.x = mx + self.drag_offset_x
                self.dragged_block.y = my + self.drag_offset_y

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragged_block:
                b = self.dragged_block
                b.dragging = False
                slot_i = self._slot_index_at(event.pos)
                placed = False
                if slot_i >= 0:
                    if self.slots[slot_i] is None:
                        if b.correct_index == slot_i:
                            b.locked = True
                            b.lock_pulse = 1.0
                            b.slot_index = slot_i
                            b.x = float(self.slot_rects[slot_i].x)
                            b.y = float(self.slot_rects[slot_i].y)
                            self.slots[slot_i] = b
                            placed = True
                            self._update_decoded()
                            self._check_completion()
                        else:
                            b.flash_timer = 0.6
                            self.failed_attempts += 1
                            self.dialogue.show(self.dialogues_data["error"])
                if not placed:
                    b.slot_index = -1
                    self._layout_pool()
                    b.x = b.home_x
                    b.y = b.home_y
                self.dragged_block = None

    # ------------------------------------------------------------------
    # update
    # ------------------------------------------------------------------
    def update(self, dt):
        # Fade
        if self.fade_timer < 1.0:
            self.fade_timer += dt
            t = min(self.fade_timer / 1.0, 1.0)
            self.fade_alpha = int(255 * (1.0 - t))

        self.dialogue.update(dt)
        for b in self.blocks:
            b.update(dt)

        # Dashed border animation
        self.dash_offset += dt * 30
        if self.dash_offset > 20:
            self.dash_offset -= 20

        # Visual aid pulse
        self._aid_pulse += dt * 3.0

    # ------------------------------------------------------------------
    # draw
    # ------------------------------------------------------------------
    def draw(self, surface):
        # Background
        if not self._bg_ready:
            self._build_bg()
        surface.blit(self._bg_surface, (0, 0))

        # Left panel label
        draw_text_box(surface, "BLOQUES  BASE64",
                      self.POOL_X + 40, self.POOL_Y - 30,
                      self.font_slot_label, color=C_TEXT_SEC, bg_alpha=200)

        # Right panel label
        draw_text_box(surface, "ORDEN  DE  DECODIFICACION",
                      self.SLOT_X, self.SLOT_Y - 30,
                      self.font_slot_label, color=C_TEXT_SEC, bg_alpha=200)

        # Draw slots
        for i, sr in enumerate(self.slot_rects):
            if self.slots[i] is None:
                self._draw_dashed_rect(surface, sr, C_BORDER)
            num = self.font_slot_label.render(f"SLOT {i + 1}", True, C_TEXT_HINT)
            surface.blit(num, (sr.right + 14, sr.y + 16))

        # Visual aids for slots (Dummy mode)
        if self.visual_aids and not self.completed:
            self._draw_visual_aids(surface)

        # Draw blocks (non-dragged first)
        for b in self.blocks:
            if not b.dragging:
                b.draw(surface)
        if self.dragged_block:
            self.dragged_block.draw(surface)

        # Result panel
        self._draw_result_panel(surface)

        # Reference table panel (replaces old edu panel)
        self._draw_ref_table(surface)

        # Hint buttons
        self._draw_hint_buttons(surface)

        # VOLVER button
        self._draw_button(surface, self.btn_volver, "VOLVER", C_ACCENT)

        # HUD
        self.hud.draw(surface)

        # Dialogue
        self.dialogue.draw(surface)

        # Debriefing
        if self.show_debrief:
            self._draw_debrief(surface)

        # Fade
        if self.fade_alpha > 0:
            fade = pygame.Surface((WIDTH, HEIGHT))
            fade.fill((0, 0, 0))
            fade.set_alpha(self.fade_alpha)
            surface.blit(fade, (0, 0))

    # ------------------------------------------------------------------
    # sub-draw helpers
    # ------------------------------------------------------------------
    def _draw_dashed_rect(self, surface, rect, color):
        dash_len = 8
        gap_len = 6
        offset = int(self.dash_offset)
        sides = [
            (rect.topleft, rect.topright, True),
            (rect.topright, rect.bottomright, False),
            (rect.bottomright, rect.bottomleft, True),
            (rect.bottomleft, rect.topleft, False),
        ]
        for (x1, y1), (x2, y2), horizontal in sides:
            length = abs(x2 - x1) if horizontal else abs(y2 - y1)
            dx = 1 if x2 > x1 else (-1 if x2 < x1 else 0)
            dy = 1 if y2 > y1 else (-1 if y2 < y1 else 0)
            pos = offset % (dash_len + gap_len)
            while pos < length:
                end = min(pos + dash_len, length)
                sx = x1 + dx * pos
                sy = y1 + dy * pos
                ex = x1 + dx * end
                ey = y1 + dy * end
                pygame.draw.line(surface, color, (sx, sy), (ex, ey), 2)
                pos = end + gap_len

    def _draw_result_panel(self, surface):
        panel_w = 460
        panel_h = 60
        px = self.POOL_X
        py = self.RESULT_Y

        # Solid black background
        pygame.draw.rect(surface, (0, 0, 0), (px, py, panel_w, panel_h))
        pygame.draw.rect(surface, C_BORDER, (px, py, panel_w, panel_h), 1,
                         border_radius=6)

        lbl = self.font_result_label.render("RESULTADO:", True, C_TEXT_SEC)
        surface.blit(lbl, (px + 16, py + 8))

        display = self.decoded_text if self.decoded_text else "________"
        col = C_GREEN if self.completed else C_NEON
        val = self.font_result_value.render(display, True, col)
        surface.blit(val, (px + 16, py + 30))

    def _draw_ref_table(self, surface):
        """Draw the built-in Base64 reference/lookup table panel."""
        ex = 680
        ey = self.POOL_Y - 10
        pw = 580
        line_h = 15
        ph = len(_REF_LINES) * line_h + 30

        # Solid black background for full legibility
        pygame.draw.rect(surface, (0, 0, 0), (ex, ey, pw, ph))
        pygame.draw.rect(surface, C_BASE64, (ex, ey, pw, ph), 1,
                         border_radius=4)

        # Title line
        title = self.font_ref_title.render(_REF_LINES[0], True, C_NEON)
        surface.blit(title, (ex + 10, ey + 8))

        # Separator
        pygame.draw.line(surface, C_BORDER,
                         (ex + 10, ey + 24), (ex + pw - 10, ey + 24), 1)

        # Table lines
        ly = ey + 30
        for line in _REF_LINES[1:]:
            if line:
                # Use neon for the worked example lines, dimmer for data
                if line.startswith("  ->") or line.startswith("SGVs"):
                    col = C_NEON
                elif line.startswith("Cada") or line.startswith("'='"):
                    col = C_BASE64
                else:
                    col = C_TEXT_PRI
                txt = self.font_ref.render(line, True, col)
                surface.blit(txt, (ex + 10, ly))
            ly += line_h

    def _draw_hint_buttons(self, surface):
        for i, hr in enumerate(self.hint_rects):
            revealed = self.hints_revealed[i]
            if revealed:
                # Show hint on solid black bg
                hint_text = self.puzzle["hints"][i]
                draw_text_box(surface, hint_text, hr.x, hr.y,
                              self.font_ref, color=C_NEON, bg_alpha=240,
                              padding=8, max_width=280)
            else:
                # Button
                if i < self.free_hints:
                    label = f"PISTA {i + 1} (GRATIS)"
                else:
                    label = f"PISTA {i + 1} (-15pts)"
                self._draw_button(surface, hr, label, C_ACCENT, small=True)

    def _draw_visual_aids(self, surface):
        """Dummy mode: arrows pointing blocks to their correct slots."""
        pulse = 0.5 + 0.5 * math.sin(self._aid_pulse)

        for b in self.blocks:
            if b.locked or b.dragging:
                continue
            # Draw arrow from block to its correct slot
            slot_r = self.slot_rects[b.correct_index]
            sx = int(b.x + _Block.W)
            sy = int(b.y + _Block.H // 2)
            ex = slot_r.x
            ey = slot_r.y + _Block.H // 2

            alpha = int(100 + 80 * pulse)
            arrow_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            col = (*C_NEON, alpha)
            pygame.draw.line(arrow_surf, col, (sx, sy), (ex, ey), 2)
            # Arrowhead
            angle = math.atan2(ey - sy, ex - sx)
            head_len = 10
            p1 = (ex - int(head_len * math.cos(angle - 0.4)),
                  ey - int(head_len * math.sin(angle - 0.4)))
            p2 = (ex - int(head_len * math.cos(angle + 0.4)),
                  ey - int(head_len * math.sin(angle + 0.4)))
            pygame.draw.polygon(arrow_surf, col, [(ex, ey), p1, p2])
            surface.blit(arrow_surf, (0, 0))

            # Label the correct slot number on the block
            lbl_surf = pygame.Surface((50, 18), pygame.SRCALPHA)
            lbl_surf.fill((0, 0, 0, int(180 * pulse)))
            font_tiny = pygame.font.SysFont("monospace", 10, bold=True)
            lbl = font_tiny.render(f"SLOT {b.correct_index + 1}", True, C_NEON)
            lbl_surf.blit(lbl, (2, 2))
            surface.blit(lbl_surf, (int(b.x + _Block.W - 52), int(b.y - 14)))

    def _draw_button(self, surface, rect, text, color, small=False):
        mx, my = pygame.mouse.get_pos()
        hover = rect.collidepoint(mx, my)

        bg_t = 0.25 if hover else 0.10
        bg = tuple(int(C_PANEL[i] + (color[i] - C_PANEL[i]) * bg_t)
                   for i in range(3))
        border = color if hover else C_BORDER

        pygame.draw.rect(surface, bg, rect, border_radius=4)
        pygame.draw.rect(surface, border, rect, 1, border_radius=4)

        font = self.font_ref if small else self.font_hint_btn
        txt_color = C_WHITE if hover else C_TEXT_PRI
        lbl = font.render(text, True, txt_color)
        surface.blit(
            lbl,
            (rect.centerx - lbl.get_width() // 2,
             rect.centery - lbl.get_height() // 2),
        )

    def _draw_debrief(self, surface):
        # Dark overlay
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        surface.blit(overlay, (0, 0))

        r = self.debrief_rect
        # Solid black popup
        pygame.draw.rect(surface, (0, 0, 0), r)
        pygame.draw.rect(surface, C_BASE64, r, 2, border_radius=8)

        # Title
        title = self.font_debrief_title.render(
            "DEBRIEFING -- BASE64", True, C_NEON
        )
        surface.blit(title, (r.x + 20, r.y + 20))

        # Body text with word-wrap
        text = self.puzzle["debriefing"]
        draw_text_box(surface, text, r.x + 20, r.y + 55,
                      self.font_debrief, color=C_NEON,
                      bg_alpha=0, padding=4, max_width=r.w - 40)

        # Score
        elapsed = self.time_elapsed
        score = max(100 - int(elapsed / 10) - self.hints_used * 15
                    - self.failed_attempts * 5, 10)
        score_txt = self.font_debrief_title.render(
            f"PUNTUACION: {score}/100", True, C_GREEN
        )
        surface.blit(score_txt, (r.x + 20, r.bottom - 90))

        # Close button
        cr = self.debrief_close_rect
        pygame.draw.rect(surface, (0, 0, 0), cr)
        pygame.draw.rect(surface, C_ACCENT, cr, 2, border_radius=4)
        cl = self.font_debrief_btn.render("[ VOLVER AL HUB ]", True, C_NEON)
        surface.blit(cl, (cr.centerx - cl.get_width() // 2,
                          cr.centery - cl.get_height() // 2))
