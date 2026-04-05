import pygame
import random
import math
import time

from game.constants import (
    WIDTH, HEIGHT, C_BG, C_BG2, C_BG3, C_BORDER, C_TEXT_PRI,
    C_TEXT_SEC, C_TEXT_HINT, C_ACCENT, C_GREEN, C_RED, C_BASE64,
    C_PANEL, C_WHITE,
)
from game.ui.dialogue import DialogueBox
from game.ui.hud import HUD
from game.ui.tile_renderer import get_separate_sprite, draw_floor
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
        self.slot_index = -1          # which slot this block sits in (-1 = pool)
        self.flash_timer = 0.0        # red flash on wrong placement
        self.lock_pulse = 0.0         # green pulse on correct placement
        self.font = pygame.font.SysFont("monospace", 22, bold=True)

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.W, self.H)

    def draw(self, surface):
        r = self.rect
        # --- shadow ---
        if self.dragging:
            shadow = pygame.Surface((r.w + 6, r.h + 6), pygame.SRCALPHA)
            pygame.draw.rect(shadow, (0, 0, 0, 60), shadow.get_rect(),
                             border_radius=self.CORNER)
            surface.blit(shadow, (r.x + 3, r.y + 5))

        # --- body ---
        body = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
        fill = (*C_BG2, 230) if not self.locked else (*C_BG3, 240)
        pygame.draw.rect(body, fill, body.get_rect(), border_radius=self.CORNER)

        # border colour
        if self.flash_timer > 0:
            border_col = C_RED
        elif self.locked:
            border_col = C_GREEN
        elif self.dragging:
            border_col = C_BASE64
        else:
            border_col = C_BORDER

        border_w = 2
        if self.lock_pulse > 0:
            border_w = 3
        pygame.draw.rect(body, border_col, body.get_rect(), border_w,
                         border_radius=self.CORNER)

        # green pulse glow
        if self.lock_pulse > 0:
            glow = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
            a = int(80 * self.lock_pulse)
            pygame.draw.rect(glow, (*C_GREEN, a), glow.get_rect(),
                             border_radius=self.CORNER)
            body.blit(glow, (0, 0))

        surface.blit(body, r.topleft)

        # --- text ---
        txt = self.font.render(self.text, True, C_WHITE if self.locked else C_BASE64)
        tx = r.centerx - txt.get_width() // 2
        ty = r.centery - txt.get_height() // 2
        surface.blit(txt, (tx, ty))

    def update(self, dt):
        if self.flash_timer > 0:
            self.flash_timer = max(0, self.flash_timer - dt)
        if self.lock_pulse > 0:
            self.lock_pulse = max(0, self.lock_pulse - dt * 1.5)


# ---------------------------------------------------------------------------
# Base64Scene -- drag-and-drop ordering puzzle
# ---------------------------------------------------------------------------
class Base64Scene:
    # layout constants
    POOL_X = 80
    POOL_Y = 140
    POOL_W = 300
    SLOT_X = 500
    SLOT_Y = 140
    SLOT_GAP = 80
    RESULT_Y = 540
    EDU_X = 950

    def __init__(self, manager):
        self.manager = manager
        self.puzzle = manager.puzzles["base64"]
        self.dialogues_data = manager.dialogues["base64"]

        # fonts
        self.font_slot_label = pygame.font.SysFont("monospace", 13, bold=True)
        self.font_result_label = pygame.font.SysFont("monospace", 16, bold=True)
        self.font_result_value = pygame.font.SysFont("monospace", 22, bold=True)
        self.font_edu_title = pygame.font.SysFont("monospace", 16, bold=True)
        self.font_edu = pygame.font.SysFont("monospace", 13)
        self.font_hint_btn = pygame.font.SysFont("monospace", 13, bold=True)
        self.font_debrief_title = pygame.font.SysFont("monospace", 18, bold=True)
        self.font_debrief = pygame.font.SysFont("monospace", 14)
        self.font_debrief_btn = pygame.font.SysFont("monospace", 15, bold=True)

        # HUD + dialogue
        self.hud = HUD()
        self.hud.set_info("ESCENA 02 -- SALA DE SERVIDORES", "CAPA 2/4 -- BASE64")
        self.dialogue = DialogueBox()

        # blocks
        block_texts = list(self.puzzle["blocks"])
        self.blocks = [_Block(t, i) for i, t in enumerate(block_texts)]
        random.shuffle(self.blocks)
        self._layout_pool()

        # slots: list of 4, each None or a _Block reference
        self.slots = [None, None, None, None]
        self.slot_rects = []
        for i in range(4):
            rx = self.SLOT_X
            ry = self.SLOT_Y + i * self.SLOT_GAP
            self.slot_rects.append(pygame.Rect(rx, ry, _Block.W, _Block.H))

        # drag state
        self.dragged_block = None
        self.drag_offset_x = 0
        self.drag_offset_y = 0

        # decoded result text
        self.decoded_text = ""

        # timing / scoring
        self.start_time = time.time()
        self.time_elapsed = 0.0
        self.hints_used = 0
        self.failed_attempts = 0
        self.completed = False

        # hint buttons (3)
        self.hint_rects = []
        for i in range(3):
            bx = self.POOL_X + i * 105
            by = self.RESULT_Y + 80
            self.hint_rects.append(pygame.Rect(bx, by, 95, 30))
        self.hints_revealed = [False, False, False]

        # debriefing popup
        self.show_debrief = False
        self.debrief_rect = pygame.Rect(WIDTH // 2 - 280, HEIGHT // 2 - 160, 560, 320)
        self.debrief_close_rect = pygame.Rect(0, 0, 180, 40)
        self.debrief_close_rect.centerx = self.debrief_rect.centerx
        self.debrief_close_rect.y = self.debrief_rect.bottom - 60

        # dashed border animation
        self.dash_offset = 0.0

        # background sprites
        self.bg_sprites = []
        self._load_bg()

        # floor surface (cached)
        self.floor_surf = pygame.Surface((WIDTH, HEIGHT))
        draw_floor(self.floor_surf, tile_col=0, tile_row=0)

        # fade in
        self.fade_alpha = 255
        self.fade_timer = 0.0

        # entrance dialogue
        self.phase = "dialogue_enter"
        self.dialogue.show(self.dialogues_data["enter"], on_complete=self._enter_done)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _load_bg(self):
        positions = [
            ("Sprite-0013.png", 2, 30, 90),
            ("Sprite-0013.png", 2, 1100, 90),
            ("Sprite-0013.png", 2, 30, 350),
            ("Sprite-0013.png", 2, 1100, 350),
        ]
        for name, scale, x, y in positions:
            try:
                img = get_separate_sprite(name, scale=scale)
                self.bg_sprites.append((img, x, y))
            except Exception:
                pass

    def _layout_pool(self):
        pool_blocks = [b for b in self.blocks if b.slot_index == -1 and not b.locked]
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
        # all correct
        self.completed = True
        self.time_elapsed = time.time() - self.start_time
        score = max(100 - int(self.time_elapsed / 10) - self.hints_used * 15
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
        # debriefing popup close
        if self.show_debrief:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.debrief_close_rect.collidepoint(event.pos):
                    self.manager.change_scene("hub")
            return

        # dialogue eats events
        if self.dialogue.active:
            self.dialogue.handle_event(event)
            return

        if self.completed:
            return

        # hint buttons
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, hr in enumerate(self.hint_rects):
                if hr.collidepoint(event.pos) and not self.hints_revealed[i]:
                    self.hints_revealed[i] = True
                    self.hints_used += 1
                    return

        # ---- drag and drop ----
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            # pick up block (topmost first -- iterate reversed draw order)
            for b in reversed(self.blocks):
                if b.locked:
                    continue
                if b.rect.collidepoint(mx, my):
                    # if block is in a slot, remove it first
                    if b.slot_index >= 0:
                        self.slots[b.slot_index] = None
                        b.slot_index = -1
                        self._update_decoded()
                    b.dragging = True
                    self.drag_offset_x = b.x - mx
                    self.drag_offset_y = b.y - my
                    self.dragged_block = b
                    # move to end so it draws on top
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
                        # check correctness
                        if b.correct_index == slot_i:
                            # correct
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
                            # wrong -- flash red and return
                            b.flash_timer = 0.6
                            self.failed_attempts += 1
                            self.dialogue.show(self.dialogues_data["error"])
                if not placed:
                    b.slot_index = -1
                    self._layout_pool()
                    # snap back
                    b.x = b.home_x
                    b.y = b.home_y
                self.dragged_block = None

    # ------------------------------------------------------------------
    # update
    # ------------------------------------------------------------------
    def update(self, dt):
        # fade
        if self.fade_timer < 1.0:
            self.fade_timer += dt
            t = min(self.fade_timer / 1.0, 1.0)
            self.fade_alpha = int(255 * (1.0 - t))

        self.dialogue.update(dt)
        for b in self.blocks:
            b.update(dt)

        # dashed border animation
        self.dash_offset += dt * 30
        if self.dash_offset > 20:
            self.dash_offset -= 20

    # ------------------------------------------------------------------
    # draw
    # ------------------------------------------------------------------
    def draw(self, surface):
        # floor
        floor_copy = self.floor_surf.copy()
        dark = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dark.fill((0, 0, 0, 180))
        floor_copy.blit(dark, (0, 0))
        surface.blit(floor_copy, (0, 0))

        # bg sprites (server racks)
        for img, x, y in self.bg_sprites:
            faded = img.copy()
            faded.set_alpha(40)
            surface.blit(faded, (x, y))

        # -- left panel label --
        lbl = self.font_slot_label.render("BLOQUES  BASE64", True, C_TEXT_SEC)
        surface.blit(lbl, (self.POOL_X + 40, self.POOL_Y - 30))

        # -- right panel label --
        lbl2 = self.font_slot_label.render("ORDEN  DE  DECODIFICACION", True, C_TEXT_SEC)
        surface.blit(lbl2, (self.SLOT_X, self.SLOT_Y - 30))

        # -- draw slots --
        for i, sr in enumerate(self.slot_rects):
            if self.slots[i] is None:
                self._draw_dashed_rect(surface, sr, C_BORDER)
            # slot number label
            num = self.font_slot_label.render(f"SLOT {i + 1}", True, C_TEXT_HINT)
            surface.blit(num, (sr.right + 14, sr.y + 16))

        # -- draw blocks (non-dragged first) --
        for b in self.blocks:
            if not b.dragging:
                b.draw(surface)
        # dragged block on top
        if self.dragged_block:
            self.dragged_block.draw(surface)

        # -- result panel --
        self._draw_result_panel(surface)

        # -- educational panel --
        self._draw_edu_panel(surface)

        # -- hint buttons --
        self._draw_hint_buttons(surface)

        # -- HUD --
        self.hud.draw(surface)

        # -- dialogue --
        self.dialogue.draw(surface)

        # -- debriefing --
        if self.show_debrief:
            self._draw_debrief(surface)

        # -- fade --
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
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((*C_PANEL, 200))
        pygame.draw.rect(panel, C_BORDER, panel.get_rect(), 1,
                         border_radius=6)
        surface.blit(panel, (px, py))

        lbl = self.font_result_label.render("RESULTADO:", True, C_TEXT_SEC)
        surface.blit(lbl, (px + 16, py + 8))

        display = self.decoded_text if self.decoded_text else "________"
        col = C_GREEN if self.completed else C_BASE64
        val = self.font_result_value.render(display, True, col)
        surface.blit(val, (px + 16, py + 30))

    def _draw_edu_panel(self, surface):
        ex = self.EDU_X
        ey = self.POOL_Y - 10
        pw = 300
        ph = 290
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((*C_PANEL, 180))
        pygame.draw.rect(panel, C_BORDER, panel.get_rect(), 1,
                         border_radius=6)
        surface.blit(panel, (ex, ey))

        title = self.font_edu_title.render("BASE64", True, C_BASE64)
        surface.blit(title, (ex + 16, ey + 14))

        lines = [
            "",
            "4 chars = 3 bytes",
            "64 simbolos posibles",
            "",
            "A-Z, a-z, 0-9, +, /",
            "",
            "No es cifrado -- es",
            "codificacion binaria",
            "",
            "Padding: '=' indica",
            "bytes faltantes",
        ]
        ly = ey + 44
        for line in lines:
            if line:
                txt = self.font_edu.render(line, True, C_TEXT_SEC)
                surface.blit(txt, (ex + 16, ly))
            ly += 20

    def _draw_hint_buttons(self, surface):
        for i, hr in enumerate(self.hint_rects):
            revealed = self.hints_revealed[i]
            btn = pygame.Surface((hr.w, hr.h), pygame.SRCALPHA)
            if revealed:
                btn.fill((*C_BG3, 200))
            else:
                btn.fill((*C_PANEL, 200))
            border_c = C_TEXT_HINT if not revealed else C_ACCENT
            pygame.draw.rect(btn, border_c, btn.get_rect(), 1,
                             border_radius=4)
            surface.blit(btn, hr.topleft)

            label = f"PISTA {i + 1}" if not revealed else f"PISTA {i + 1}"
            txt = self.font_hint_btn.render(label, True,
                                            C_ACCENT if not revealed else C_TEXT_SEC)
            tx = hr.centerx - txt.get_width() // 2
            ty = hr.centery - txt.get_height() // 2
            surface.blit(txt, (tx, ty))

            if revealed:
                hint_text = self.puzzle["hints"][i]
                ht = self.font_edu.render(hint_text, True, C_TEXT_HINT)
                surface.blit(ht, (hr.x, hr.bottom + 6))

    def _draw_debrief(self, surface):
        # overlay
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))

        r = self.debrief_rect
        panel = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
        panel.fill((*C_PANEL, 240))
        pygame.draw.rect(panel, C_BASE64, panel.get_rect(), 2,
                         border_radius=8)
        surface.blit(panel, r.topleft)

        # title
        title = self.font_debrief_title.render("DEBRIEFING -- BASE64", True, C_BASE64)
        surface.blit(title, (r.x + 20, r.y + 20))

        # body -- word wrap
        text = self.puzzle["debriefing"]
        self._draw_wrapped(surface, text, self.font_debrief, C_TEXT_SEC,
                           r.x + 20, r.y + 55, r.w - 40, 20)

        # score
        elapsed = self.time_elapsed
        score = max(100 - int(elapsed / 10) - self.hints_used * 15
                    - self.failed_attempts * 5, 10)
        score_txt = self.font_debrief_title.render(
            f"PUNTUACION: {score}/100", True, C_GREEN)
        surface.blit(score_txt, (r.x + 20, r.bottom - 90))

        # close button
        cr = self.debrief_close_rect
        btn = pygame.Surface((cr.w, cr.h), pygame.SRCALPHA)
        btn.fill((*C_BG2, 220))
        pygame.draw.rect(btn, C_ACCENT, btn.get_rect(), 2, border_radius=4)
        surface.blit(btn, cr.topleft)
        cl = self.font_debrief_btn.render("[ VOLVER AL HUB ]", True, C_ACCENT)
        surface.blit(cl, (cr.centerx - cl.get_width() // 2,
                          cr.centery - cl.get_height() // 2))

    def _draw_wrapped(self, surface, text, font, color, x, y, max_w, line_h):
        words = text.split()
        line = ""
        cy = y
        for word in words:
            test = (line + " " + word).strip()
            tw = font.size(test)[0]
            if tw > max_w and line:
                rendered = font.render(line, True, color)
                surface.blit(rendered, (x, cy))
                cy += line_h
                line = word
            else:
                line = test
        if line:
            rendered = font.render(line, True, color)
            surface.blit(rendered, (x, cy))
