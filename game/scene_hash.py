import pygame
import random
import time
import math

from game.constants import (
    WIDTH, HEIGHT, C_BG, C_BG2, C_BG3, C_BORDER, C_TEXT_PRI,
    C_TEXT_SEC, C_TEXT_HINT, C_ACCENT, C_GREEN, C_RED, C_HASH,
    C_PANEL, C_WHITE,
)
from game.ui.dialogue import DialogueBox
from game.ui.hud import HUD
from game.ui.tile_renderer import get_separate_sprite, draw_floor
from crypto.hash_utils import sha256_short, build_rainbow_table


# ---------------------------------------------------------------------------
# Helper: rounded‑corner rect with optional glow
# ---------------------------------------------------------------------------
def _draw_rounded_rect(surface, rect, color, border_radius=6, border=0):
    """Draw a rounded rectangle (fill or border only)."""
    pygame.draw.rect(surface, color, rect, border, border_radius=border_radius)


# ---------------------------------------------------------------------------
# HashScene — SHA-256 matching puzzle
# ---------------------------------------------------------------------------
class HashScene:

    # -- column geometry ---------------------------------------------------
    LEFT_X = 140
    RIGHT_X = 710
    BOX_W = 200
    BOX_H = 48
    BOX_GAP = 16
    FIRST_Y = 140

    CANDIDATES = ["password", "123456", "qwerty", "letmein", "deadlock"]

    def __init__(self, manager):
        self.manager = manager
        self.puzzle_data = manager.puzzles.get("hash", {})
        self.dialogue_data = manager.dialogues.get("hash", {})

        # Fonts -----------------------------------------------------------
        self.font_word = pygame.font.SysFont("monospace", 18, bold=True)
        self.font_hash = pygame.font.SysFont("monospace", 14, bold=True)
        self.font_label = pygame.font.SysFont("monospace", 12, bold=True)
        self.font_panel = pygame.font.SysFont("monospace", 13)
        self.font_panel_title = pygame.font.SysFont("monospace", 15, bold=True)
        self.font_hint_btn = pygame.font.SysFont("monospace", 13, bold=True)
        self.font_score = pygame.font.SysFont("monospace", 14, bold=True)
        self.font_debrief = pygame.font.SysFont("monospace", 14)
        self.font_debrief_title = pygame.font.SysFont("monospace", 20, bold=True)
        self.font_debrief_btn = pygame.font.SysFont("monospace", 16, bold=True)

        # Rainbow table ---------------------------------------------------
        self.rainbow = build_rainbow_table(self.CANDIDATES)

        # Shuffled right‑column order
        self.hash_order = list(self.rainbow.values())
        random.shuffle(self.hash_order)

        # Build rect lists ------------------------------------------------
        self.word_rects = []
        self.hash_rects = []
        for i in range(5):
            y = self.FIRST_Y + i * (self.BOX_H + self.BOX_GAP)
            self.word_rects.append(pygame.Rect(self.LEFT_X, y, self.BOX_W, self.BOX_H))
            self.hash_rects.append(pygame.Rect(self.RIGHT_X, y, self.BOX_W, self.BOX_H))

        # Interaction state -----------------------------------------------
        self.dragging = False
        self.drag_from_word = None       # index into CANDIDATES
        self.drag_from_hash = None       # index into hash_order (for reverse detect)
        self.drag_origin = (0, 0)
        self.drag_current = (0, 0)

        self.matched_pairs = {}          # {word: hash_hex}
        self.matched_word_indices = set()
        self.matched_hash_indices = set()

        self.flash_lines = []            # [(start, end, color, timer)]

        # Timing / scoring ------------------------------------------------
        self.start_time = time.time()
        self.time_elapsed = 0.0
        self.hints_used = 0
        self.failed_attempts = 0
        self.completed = False
        self.score = 0

        # Hint buttons (3) -----------------------------------------------
        hints = self.puzzle_data.get("hints", [
            "Los hashes son funciones de una sola via.",
            "Calcula el SHA-256 de cada candidato.",
            "La contrasena del director es el nombre de la operacion.",
        ])
        self.hints = hints
        self.hint_unlocked = [False, False, False]
        self.hint_rects = []
        for i in range(3):
            bx = 960
            by = 530 + i * 42
            self.hint_rects.append(pygame.Rect(bx, by, 280, 34))

        # Debriefing popup -----------------------------------------------
        self.show_debrief = False
        self.debrief_text = self.puzzle_data.get(
            "debriefing",
            "SHA-256 transforma datos en huellas digitales de tamano fijo. "
            "Las rainbow tables explotan contrasenas debiles.",
        )
        self.debrief_btn = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 + 100, 200, 44)

        # HUD + Dialogue --------------------------------------------------
        self.hud = HUD()
        self.hud.set_info(
            "ESCENA 03 \u2014 OFICINA DEL DIRECTOR",
            "CAPA 3/4 \u2014 SHA-256",
        )
        self.dialogue = DialogueBox()

        # Background sprites -----------------------------------------------
        self._load_bg()

        # Floor surface (cached) -------------------------------------------
        self.floor_surf = pygame.Surface((WIDTH, HEIGHT))
        draw_floor(self.floor_surf, tile_col=2, tile_row=0)

        # Trigger entrance dialogue ----------------------------------------
        enter_msgs = self.dialogue_data.get("enter", [])
        if enter_msgs:
            self.dialogue.show(enter_msgs)

    # -- background sprites ------------------------------------------------
    def _load_bg(self):
        self.bg_sprites = []
        defs = [
            ("Sprite-0005.png", 3, 440, 440),
            ("Sprite-0013.png", 3, 30, 350),
            ("Sprite-0013.png", 3, 1180, 360),
        ]
        for name, scale, x, y in defs:
            try:
                img = get_separate_sprite(name, scale=scale)
                self.bg_sprites.append((img, x, y))
            except Exception:
                pass

    # =====================================================================
    # EVENT HANDLING
    # =====================================================================
    def handle_event(self, event):
        # Dialogue consumes events first
        if self.dialogue.active:
            self.dialogue.handle_event(event)
            return

        # Debriefing popup
        if self.show_debrief:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.debrief_btn.collidepoint(event.pos):
                    self.manager.complete_puzzle("hash", self.score)
                    self.manager.change_scene("hub")
            return

        if self.completed:
            return

        # ---- Mouse interaction with columns ----
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            # Check click on word boxes (left column)
            for i, rect in enumerate(self.word_rects):
                if rect.collidepoint(pos) and i not in self.matched_word_indices:
                    self.dragging = True
                    self.drag_from_word = i
                    self.drag_from_hash = None
                    self.drag_origin = rect.center
                    self.drag_current = pos
                    return
            # Check click on hash boxes (right column) — reverse drag
            for i, rect in enumerate(self.hash_rects):
                if rect.collidepoint(pos) and i not in self.matched_hash_indices:
                    self.dragging = True
                    self.drag_from_word = None
                    self.drag_from_hash = i
                    self.drag_origin = rect.center
                    self.drag_current = pos
                    return
            # Hint buttons
            for i, rect in enumerate(self.hint_rects):
                if rect.collidepoint(pos) and not self.hint_unlocked[i]:
                    # Unlock sequentially
                    if i == 0 or self.hint_unlocked[i - 1]:
                        self.hint_unlocked[i] = True
                        self.hints_used += 1
                    return

        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                self.drag_current = event.pos

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if not self.dragging:
                return

            pos = event.pos

            # --- Reverse drag: hash → word → show message ---
            if self.drag_from_hash is not None:
                for i, rect in enumerate(self.word_rects):
                    if rect.collidepoint(pos):
                        msgs = self.dialogue_data.get("reverse_blocked", [
                            {
                                "speaker": "ANALISTA",
                                "text": "Los hashes son funciones de una sola via. No puedes revertirlos.",
                            }
                        ])
                        self.dialogue.show(msgs)
                        break
                self.dragging = False
                self.drag_from_hash = None
                return

            # --- Normal drag: word → hash ---
            if self.drag_from_word is not None:
                word = self.CANDIDATES[self.drag_from_word]
                word_center = self.word_rects[self.drag_from_word].center
                released_on_hash = False

                for j, rect in enumerate(self.hash_rects):
                    if rect.collidepoint(pos) and j not in self.matched_hash_indices:
                        released_on_hash = True
                        target_hash = self.hash_order[j]
                        correct_hash = self.rainbow[word]
                        hash_center = rect.center

                        if target_hash == correct_hash:
                            # Correct match
                            self.matched_pairs[word] = target_hash
                            self.matched_word_indices.add(self.drag_from_word)
                            self.matched_hash_indices.add(j)
                            self.flash_lines.append(
                                (word_center, hash_center, C_GREEN, 0.0, True)
                            )
                            self._check_completion()
                        else:
                            # Wrong match
                            self.failed_attempts += 1
                            self.flash_lines.append(
                                (word_center, hash_center, C_RED, 0.0, False)
                            )
                            err = self.dialogue_data.get("error", [])
                            if err:
                                self.dialogue.show(err)
                        break

            self.dragging = False
            self.drag_from_word = None

    # =====================================================================
    # UPDATE
    # =====================================================================
    def update(self, dt):
        self.dialogue.update(dt)

        if not self.completed:
            self.time_elapsed = time.time() - self.start_time

        # Update flash lines (animate timers)
        new_flash = []
        for start, end, color, timer, permanent in self.flash_lines:
            timer += dt
            if permanent:
                new_flash.append((start, end, color, timer, permanent))
            elif timer < 0.5:
                new_flash.append((start, end, color, timer, permanent))
        self.flash_lines = new_flash

    # =====================================================================
    # COMPLETION
    # =====================================================================
    def _check_completion(self):
        if len(self.matched_pairs) >= 5:
            self.completed = True
            self.score = max(
                100 - int(self.time_elapsed / 10) - self.hints_used * 15 - self.failed_attempts * 5,
                10,
            )
            success_msgs = self.dialogue_data.get("success", [])
            if success_msgs:
                self.dialogue.show(success_msgs, on_complete=self._show_debrief)
            else:
                self._show_debrief()

    def _show_debrief(self):
        self.show_debrief = True

    # =====================================================================
    # DRAW
    # =====================================================================
    def draw(self, surface):
        # Floor
        surface.blit(self.floor_surf, (0, 0))

        # Dark overlay to keep readability
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((C_BG[0], C_BG[1], C_BG[2], 210))
        surface.blit(overlay, (0, 0))

        # Background sprites (low opacity)
        for img, x, y in self.bg_sprites:
            faded = img.copy()
            faded.set_alpha(35)
            surface.blit(faded, (x, y))

        # Column labels
        lbl_words = self.font_label.render("CONTRASENAS CANDIDATAS", True, C_TEXT_SEC)
        surface.blit(lbl_words, (self.LEFT_X, self.FIRST_Y - 24))
        lbl_hashes = self.font_label.render("HASHES SHA-256 (16 hex)", True, C_TEXT_SEC)
        surface.blit(lbl_hashes, (self.RIGHT_X, self.FIRST_Y - 24))

        # Draw word boxes (left)
        self._draw_word_boxes(surface)

        # Draw hash boxes (right)
        self._draw_hash_boxes(surface)

        # Draw permanent connection lines (correct matches)
        for start, end, color, timer, permanent in self.flash_lines:
            if permanent:
                self._draw_connection_line(surface, start, end, color, 1.0)

        # Draw fading error lines
        for start, end, color, timer, permanent in self.flash_lines:
            if not permanent:
                alpha_frac = max(0.0, 1.0 - timer / 0.5)
                self._draw_connection_line(surface, start, end, color, alpha_frac)

        # Rubber-band line while dragging
        if self.dragging:
            self._draw_rubber_band(surface)

        # Educational panel (right sidebar)
        self._draw_edu_panel(surface)

        # Hint buttons
        self._draw_hints(surface)

        # Score / timer display
        self._draw_timer(surface)

        # HUD
        self.hud.draw(surface)

        # Dialogue
        self.dialogue.draw(surface)

        # Debriefing popup
        if self.show_debrief:
            self._draw_debrief(surface)

    # -- word boxes --------------------------------------------------------
    def _draw_word_boxes(self, surface):
        for i, rect in enumerate(self.word_rects):
            word = self.CANDIDATES[i]
            matched = i in self.matched_word_indices
            hovered = (
                not self.completed
                and not self.dialogue.active
                and rect.collidepoint(pygame.mouse.get_pos())
                and not matched
            )

            # Background
            bg_color = (*C_BG2, 220) if not matched else (*C_GREEN, 50)
            box_surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            box_surf.fill(bg_color)
            surface.blit(box_surf, rect.topleft)

            # Border
            border_col = C_GREEN if matched else (C_HASH if hovered else C_BORDER)
            _draw_rounded_rect(surface, rect, border_col, border_radius=4, border=2)

            # DB-entry style prefix
            prefix = self.font_label.render(f"[{i+1}]", True, C_TEXT_HINT)
            surface.blit(prefix, (rect.x + 8, rect.y + 16))

            # Word text
            word_color = C_GREEN if matched else C_TEXT_PRI
            txt = self.font_word.render(word, True, word_color)
            surface.blit(txt, (rect.x + 42, rect.y + 14))

    # -- hash boxes --------------------------------------------------------
    def _draw_hash_boxes(self, surface):
        for j, rect in enumerate(self.hash_rects):
            h = self.hash_order[j]
            matched = j in self.matched_hash_indices
            hovered = (
                not self.completed
                and not self.dialogue.active
                and rect.collidepoint(pygame.mouse.get_pos())
                and not matched
            )

            bg_color = (*C_BG3, 220) if not matched else (*C_GREEN, 50)
            box_surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            box_surf.fill(bg_color)
            surface.blit(box_surf, rect.topleft)

            border_col = C_GREEN if matched else (C_HASH if hovered else C_BORDER)
            _draw_rounded_rect(surface, rect, border_col, border_radius=4, border=2)

            # Hash text (monospace)
            hash_color = C_GREEN if matched else C_HASH
            txt = self.font_hash.render(h, True, hash_color)
            surface.blit(txt, (rect.x + 12, rect.y + 16))

    # -- connection line with glow -----------------------------------------
    def _draw_connection_line(self, surface, start, end, color, alpha_frac):
        alpha = int(255 * alpha_frac)
        line_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        # Glow (thicker, lower alpha)
        glow_alpha = int(60 * alpha_frac)
        pygame.draw.line(line_surf, (*color, glow_alpha), start, end, 6)
        # Core
        pygame.draw.line(line_surf, (*color, alpha), start, end, 2)
        surface.blit(line_surf, (0, 0))

    # -- rubber band -------------------------------------------------------
    def _draw_rubber_band(self, surface):
        line_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        # Glow
        pygame.draw.line(line_surf, (*C_ACCENT, 50), self.drag_origin, self.drag_current, 6)
        # Core
        pygame.draw.line(line_surf, (*C_ACCENT, 180), self.drag_origin, self.drag_current, 2)
        # Small circle at cursor
        pygame.draw.circle(line_surf, (*C_ACCENT, 120), self.drag_current, 6, 1)
        surface.blit(line_surf, (0, 0))

    # -- educational panel -------------------------------------------------
    def _draw_edu_panel(self, surface):
        panel_x = 950
        panel_y = 130
        panel_w = 300
        panel_h = 260

        panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel_surf.fill((*C_PANEL, 220))
        surface.blit(panel_surf, (panel_x, panel_y))
        pygame.draw.rect(surface, C_BORDER, (panel_x, panel_y, panel_w, panel_h), 1)

        # Title
        title = self.font_panel_title.render("SHA-256", True, C_HASH)
        surface.blit(title, (panel_x + 14, panel_y + 12))
        pygame.draw.line(
            surface, C_BORDER,
            (panel_x + 14, panel_y + 34), (panel_x + panel_w - 14, panel_y + 34), 1,
        )

        lines = [
            "Siempre 256 bits / 64 hex",
            "Mismo input = mismo output",
            "IRREVERSIBLE por diseno",
            "",
            "Avalancha: 1 bit cambiado",
            "-> hash completamente",
            "   distinto",
            "",
            "Usado para verificar",
            "contrasenas sin guardarlas",
        ]
        y = panel_y + 44
        for line in lines:
            if line == "":
                y += 8
                continue
            color = C_RED if "IRREVERSIBLE" in line else C_TEXT_SEC
            txt = self.font_panel.render(line, True, color)
            surface.blit(txt, (panel_x + 14, y))
            y += 18

    # -- hint buttons ------------------------------------------------------
    def _draw_hints(self, surface):
        hint_label = self.font_label.render("PISTAS", True, C_TEXT_HINT)
        surface.blit(hint_label, (960, 510))

        for i, rect in enumerate(self.hint_rects):
            if self.hint_unlocked[i]:
                # Show hint text wrapped
                box_surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
                box_surf.fill((*C_BG3, 180))
                surface.blit(box_surf, rect.topleft)
                pygame.draw.rect(surface, C_ACCENT, rect, 1, border_radius=3)
                txt = self.font_panel.render(
                    self.hints[i][:42] if len(self.hints[i]) > 42 else self.hints[i],
                    True, C_TEXT_SEC,
                )
                surface.blit(txt, (rect.x + 8, rect.y + 10))
            else:
                can_unlock = (i == 0 or self.hint_unlocked[i - 1]) and not self.completed
                hovered = can_unlock and rect.collidepoint(pygame.mouse.get_pos())
                border_col = C_ACCENT if hovered else C_BORDER
                bg_alpha = 160 if hovered else 120
                box_surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
                box_surf.fill((*C_BG2, bg_alpha))
                surface.blit(box_surf, rect.topleft)
                pygame.draw.rect(surface, border_col, rect, 1, border_radius=3)
                label = self.font_hint_btn.render(
                    f"[ PISTA {i+1} ]  (-15 pts)", True,
                    C_ACCENT if can_unlock else C_TEXT_HINT,
                )
                surface.blit(label, (rect.x + 8, rect.y + 10))

    # -- timer / score display ---------------------------------------------
    def _draw_timer(self, surface):
        mins = int(self.time_elapsed) // 60
        secs = int(self.time_elapsed) % 60
        time_str = f"TIEMPO: {mins:02d}:{secs:02d}"
        matched_str = f"PARES: {len(self.matched_pairs)}/5"
        fails_str = f"FALLOS: {self.failed_attempts}"

        tx = 960
        ty = 415
        for text in [time_str, matched_str, fails_str]:
            txt_surf = self.font_score.render(text, True, C_TEXT_SEC)
            surface.blit(txt_surf, (tx, ty))
            ty += 22

        if self.completed:
            score_str = f"PUNTUACION: {self.score}"
            sc_surf = self.font_score.render(score_str, True, C_GREEN)
            surface.blit(sc_surf, (tx, ty))

    # -- debriefing popup --------------------------------------------------
    def _draw_debrief(self, surface):
        # Full-screen dim overlay
        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 180))
        surface.blit(dim, (0, 0))

        # Popup box
        pw, ph = 700, 340
        px = WIDTH // 2 - pw // 2
        py = HEIGHT // 2 - ph // 2
        popup = pygame.Surface((pw, ph), pygame.SRCALPHA)
        popup.fill((*C_PANEL, 240))
        surface.blit(popup, (px, py))
        pygame.draw.rect(surface, C_GREEN, (px, py, pw, ph), 2, border_radius=4)

        # Title
        title = self.font_debrief_title.render("MISION COMPLETADA", True, C_GREEN)
        surface.blit(title, (px + pw // 2 - title.get_width() // 2, py + 20))

        # Score line
        score_line = self.font_score.render(f"PUNTUACION FINAL: {self.score}/100", True, C_WHITE)
        surface.blit(score_line, (px + pw // 2 - score_line.get_width() // 2, py + 56))

        pygame.draw.line(surface, C_BORDER, (px + 30, py + 84), (px + pw - 30, py + 84), 1)

        # Debrief text (word wrap)
        self._draw_wrapped_text(
            surface, self.debrief_text,
            self.font_debrief, C_TEXT_SEC,
            px + 30, py + 96, pw - 60, 20,
        )

        # Continue button
        hovered = self.debrief_btn.collidepoint(pygame.mouse.get_pos())
        border_col = C_GREEN if hovered else C_BORDER
        btn_surf = pygame.Surface((self.debrief_btn.w, self.debrief_btn.h), pygame.SRCALPHA)
        btn_surf.fill((*C_BG2, 200))
        surface.blit(btn_surf, self.debrief_btn.topleft)
        pygame.draw.rect(surface, border_col, self.debrief_btn, 2, border_radius=4)
        btn_text = self.font_debrief_btn.render("[ CONTINUAR ]", True, C_WHITE)
        surface.blit(
            btn_text,
            (
                self.debrief_btn.centerx - btn_text.get_width() // 2,
                self.debrief_btn.centery - btn_text.get_height() // 2,
            ),
        )

    # -- text wrapping helper ----------------------------------------------
    def _draw_wrapped_text(self, surface, text, font, color, x, y, max_w, line_h):
        words = text.split(" ")
        line = ""
        cy = y
        for word in words:
            test = (line + " " + word).strip()
            if font.size(test)[0] > max_w:
                if line:
                    surface.blit(font.render(line, True, color), (x, cy))
                    cy += line_h
                line = word
            else:
                line = test
        if line:
            surface.blit(font.render(line, True, color), (x, cy))
