import pygame
import random
import time

from game.constants import (
    WIDTH, HEIGHT, C_BG, C_BG2, C_BG3, C_BORDER, C_TEXT_PRI,
    C_TEXT_SEC, C_TEXT_HINT, C_ACCENT, C_GREEN, C_RED, C_NEON, C_WHITE,
    C_PANEL, C_HASH, C_TERM_BG, C_TERM_GREEN, HINTS_CONFIG,
)
from game.ui.draw_assets import (
    draw_desk, draw_chair, draw_filing_cabinet,
    draw_monitor, draw_office_floor, draw_wall, draw_text_box, word_wrap,
)
from game.ui.dialogue import DialogueBox
from game.ui.hud import HUD
from crypto.hash_utils import sha256_short, build_rainbow_table


# ---------------------------------------------------------------------------
# Helper: rounded-corner rect
# ---------------------------------------------------------------------------
def _draw_rounded_rect(surface, rect, color, border_radius=6, border=0):
    pygame.draw.rect(surface, color, rect, border, border_radius=border_radius)


# ---------------------------------------------------------------------------
# HashScene -- SHA-256 matching puzzle with Terminal Code Interface
# ---------------------------------------------------------------------------
class HashScene:

    CANDIDATES = ["password", "123456", "qwerty", "letmein", "deadlock"]

    # -- LEFT panel geometry (DATABASE DE HASHES + connection) --
    LP_X = 40
    LP_W = 580
    WORD_X = 60
    HASH_X = 370
    BOX_W = 160
    BOX_H = 38
    BOX_GAP = 10
    FIRST_Y = 120

    # -- RIGHT panel geometry (TERMINAL DE CODIGO) --
    RP_X = 640
    RP_W = 600
    RP_Y = 50
    RP_H = 620

    # -- Terminal word buttons --
    TERM_BTN_Y = 540
    TERM_BTN_W = 108
    TERM_BTN_H = 32
    TERM_BTN_GAP = 8

    def __init__(self, manager):
        self.manager = manager
        self.puzzle_data = manager.puzzles.get("hash", {})
        self.dialogue_data = manager.dialogues.get("hash", {})

        # Difficulty-aware hints config
        diff = getattr(manager, "difficulty", 1)
        self.hints_cfg = HINTS_CONFIG.get(diff, HINTS_CONFIG.get(1, {}))

        # Fonts
        self.font_title = pygame.font.SysFont("monospace", 16, bold=True)
        self.font_word = pygame.font.SysFont("monospace", 15, bold=True)
        self.font_hash = pygame.font.SysFont("monospace", 12, bold=True)
        self.font_label = pygame.font.SysFont("monospace", 11, bold=True)
        self.font_term = pygame.font.SysFont("monospace", 14)
        self.font_term_result = pygame.font.SysFont("monospace", 16, bold=True)
        self.font_hint_btn = pygame.font.SysFont("monospace", 12, bold=True)
        self.font_score = pygame.font.SysFont("monospace", 13, bold=True)
        self.font_debrief = pygame.font.SysFont("monospace", 14)
        self.font_debrief_title = pygame.font.SysFont("monospace", 20, bold=True)
        self.font_debrief_btn = pygame.font.SysFont("monospace", 15, bold=True)
        self.font_btn = pygame.font.SysFont("monospace", 13, bold=True)

        # Rainbow table
        self.rainbow = build_rainbow_table(self.CANDIDATES)

        # Shuffled hash order for right column on LEFT panel
        self.hash_order = list(self.rainbow.values())
        random.shuffle(self.hash_order)

        # Build rects for word boxes and hash boxes (LEFT panel)
        self.word_rects = []
        self.hash_rects = []
        for i in range(5):
            y = self.FIRST_Y + i * (self.BOX_H + self.BOX_GAP)
            self.word_rects.append(
                pygame.Rect(self.WORD_X, y, self.BOX_W, self.BOX_H)
            )
            self.hash_rects.append(
                pygame.Rect(self.HASH_X, y, self.BOX_W, self.BOX_H)
            )

        # Terminal word buttons (on right panel)
        self.term_btn_rects = []
        start_x = self.RP_X + 20
        for i in range(5):
            bx = start_x + i * (self.TERM_BTN_W + self.TERM_BTN_GAP)
            self.term_btn_rects.append(
                pygame.Rect(bx, self.TERM_BTN_Y, self.TERM_BTN_W, self.TERM_BTN_H)
            )

        # Terminal state
        self.term_selected_word = None      # which word is loaded in terminal
        self.term_typing_timer = 0.0        # animation timer for typing effect
        self.term_typing_done = False
        self.term_flash_timer = 0.0         # flash on result
        self.term_typing_speed = 0.04       # seconds per character

        # Interaction state (rubber-band connections)
        self.dragging = False
        self.drag_from_word = None
        self.drag_from_hash = None
        self.drag_origin = (0, 0)
        self.drag_current = (0, 0)

        self.matched_pairs = {}
        self.matched_word_indices = set()
        self.matched_hash_indices = set()
        self.flash_lines = []               # [(start, end, color, timer, permanent)]

        # Timing / scoring
        self.start_time = time.time()
        self.time_elapsed = 0.0
        self.hints_used = 0
        self.failed_attempts = 0
        self.completed = False
        self.score = 0

        # Hints
        hints = self.puzzle_data.get("hints", [
            "Los hashes son funciones de una sola via.",
            "Usa la terminal para calcular el SHA-256 de cada palabra.",
            "La contrasena del director es el nombre de la operacion.",
        ])
        self.hints = hints
        self.hint_unlocked = [False] * len(hints)
        # Hint 0 is always free
        free_hints = self.hints_cfg.get("free_hints", 1)
        for i in range(min(free_hints, len(hints))):
            self.hint_unlocked[i] = True

        self.hint_rects = []
        for i in range(len(hints)):
            self.hint_rects.append(
                pygame.Rect(self.RP_X + 20, 590 + i * 36, self.RP_W - 40, 30)
            )

        # VOLVER button
        self.back_rect = pygame.Rect(20, HEIGHT - 48, 140, 36)

        # Debriefing
        self.show_debrief = False
        self.debrief_text = self.puzzle_data.get(
            "debriefing",
            "SHA-256 transforma datos en huellas digitales de tamano fijo. "
            "Las rainbow tables explotan contrasenas debiles.",
        )
        self.debrief_btn = pygame.Rect(
            WIDTH // 2 - 100, HEIGHT // 2 + 110, 200, 44
        )

        # HUD + Dialogue
        self.hud = HUD()
        self.hud.set_info(
            "ESCENA 03 -- OFICINA DEL DIRECTOR",
            "CAPA 3/4 -- SHA-256",
        )
        self.dialogue = DialogueBox()

        # Entrance dialogue
        enter_msgs = self.dialogue_data.get("enter", [])
        if enter_msgs:
            self.dialogue.show(enter_msgs)

    # =================================================================
    # EVENT HANDLING
    # =================================================================
    def handle_event(self, event):
        if self.dialogue.active:
            self.dialogue.handle_event(event)
            return

        if self.show_debrief:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.debrief_btn.collidepoint(event.pos):
                    self.manager.complete_puzzle("hash", self.score)
                    self.manager.change_scene("hub")
            return

        if self.completed:
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos

            # VOLVER button
            if self.back_rect.collidepoint(pos):
                self.manager.change_scene("hub")
                return

            # Terminal word buttons (right panel)
            for i, rect in enumerate(self.term_btn_rects):
                if rect.collidepoint(pos):
                    self._select_terminal_word(i)
                    return

            # Word boxes - start drag (left panel)
            for i, rect in enumerate(self.word_rects):
                if rect.collidepoint(pos) and i not in self.matched_word_indices:
                    self.dragging = True
                    self.drag_from_word = i
                    self.drag_from_hash = None
                    self.drag_origin = rect.center
                    self.drag_current = pos
                    return

            # Hash boxes - reverse drag detection
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

            # Reverse drag: hash -> word -> show message
            if self.drag_from_hash is not None:
                for i, rect in enumerate(self.word_rects):
                    if rect.collidepoint(pos):
                        msgs = self.dialogue_data.get("reverse_blocked", [
                            {
                                "speaker": "ANALISTA",
                                "text": (
                                    "Los hashes son funciones de una sola "
                                    "via. No puedes revertirlos."
                                ),
                            }
                        ])
                        self.dialogue.show(msgs)
                        break
                self.dragging = False
                self.drag_from_hash = None
                return

            # Normal drag: word -> hash
            if self.drag_from_word is not None:
                word = self.CANDIDATES[self.drag_from_word]
                word_center = self.word_rects[self.drag_from_word].center

                for j, rect in enumerate(self.hash_rects):
                    if rect.collidepoint(pos) and j not in self.matched_hash_indices:
                        target_hash = self.hash_order[j]
                        correct_hash = self.rainbow[word]
                        hash_center = rect.center

                        if target_hash == correct_hash:
                            self.matched_pairs[word] = target_hash
                            self.matched_word_indices.add(self.drag_from_word)
                            self.matched_hash_indices.add(j)
                            self.flash_lines.append(
                                (word_center, hash_center, C_GREEN, 0.0, True)
                            )
                            self._check_completion()
                        else:
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

    # -- terminal word selection -------------------------------------------
    def _select_terminal_word(self, idx):
        word = self.CANDIDATES[idx]
        self.term_selected_word = word
        self.term_typing_timer = 0.0
        self.term_typing_done = False
        self.term_flash_timer = 0.0

    # =================================================================
    # UPDATE
    # =================================================================
    def update(self, dt):
        self.dialogue.update(dt)

        if not self.completed:
            self.time_elapsed = time.time() - self.start_time

        # Terminal typing animation
        if self.term_selected_word and not self.term_typing_done:
            self.term_typing_timer += dt
            # Total chars to type: the word + some overhead
            total_chars = len(self.term_selected_word) + 40
            typed = int(self.term_typing_timer / self.term_typing_speed)
            if typed >= total_chars:
                self.term_typing_done = True
                self.term_flash_timer = 0.5

        # Flash timer for terminal result
        if self.term_flash_timer > 0:
            self.term_flash_timer -= dt
            if self.term_flash_timer < 0:
                self.term_flash_timer = 0

        # Update flash lines
        new_flash = []
        for start, end, color, timer, permanent in self.flash_lines:
            timer += dt
            if permanent or timer < 0.5:
                new_flash.append((start, end, color, timer, permanent))
        self.flash_lines = new_flash

    # =================================================================
    # COMPLETION
    # =================================================================
    def _check_completion(self):
        if len(self.matched_pairs) >= 5:
            self.completed = True
            self.score = max(
                100
                - int(self.time_elapsed / 10)
                - self.hints_used * 15
                - self.failed_attempts * 5,
                10,
            )
            success_msgs = self.dialogue_data.get("success", [])
            if success_msgs:
                self.dialogue.show(success_msgs, on_complete=self._show_debrief)
            else:
                self._show_debrief()

    def _show_debrief(self):
        self.show_debrief = True

    # =================================================================
    # DRAW
    # =================================================================
    def draw(self, surface):
        # Background: office floor + wall + furniture
        self._draw_background(surface)

        # LEFT panel: DATABASE DE HASHES + connection interface
        self._draw_left_panel(surface)

        # RIGHT panel: TERMINAL DE CODIGO
        self._draw_terminal_panel(surface)

        # Connection lines (permanent correct matches)
        for start, end, color, timer, permanent in self.flash_lines:
            if permanent:
                self._draw_connection_line(surface, start, end, color, 1.0)

        # Fading error lines
        for start, end, color, timer, permanent in self.flash_lines:
            if not permanent:
                alpha_frac = max(0.0, 1.0 - timer / 0.5)
                self._draw_connection_line(surface, start, end, color, alpha_frac)

        # Rubber-band line while dragging
        if self.dragging:
            self._draw_rubber_band(surface)

        # Score / timer (bottom-left area)
        self._draw_timer(surface)

        # VOLVER button
        self._draw_back_button(surface)

        # HUD
        self.hud.draw(surface)

        # Dialogue
        self.dialogue.draw(surface)

        # Debriefing popup
        if self.show_debrief:
            self._draw_debrief(surface)

    # -- background --------------------------------------------------------
    def _draw_background(self, surface):
        # Office floor
        draw_office_floor(surface)

        # Dark overlay for legibility
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        surface.blit(overlay, (0, 0))

        # Wall at top
        draw_wall(surface, 0, wall_h=46)

        # Office furniture (faded, decorative)
        furn_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        draw_desk(furn_surf, 80, 620, w=120, h=50)
        draw_chair(furn_surf, 160, 640)
        draw_monitor(furn_surf, 100, 594, text="SHA")
        draw_filing_cabinet(furn_surf, 1220, 580)
        draw_desk(furn_surf, 700, 650, w=100, h=40)
        furn_surf.set_alpha(40)
        surface.blit(furn_surf, (0, 0))

    # -- LEFT panel --------------------------------------------------------
    def _draw_left_panel(self, surface):
        # Panel background
        panel_rect = pygame.Rect(
            self.LP_X - 10, self.FIRST_Y - 50,
            self.LP_W + 20, 340
        )
        bg = pygame.Surface((panel_rect.w, panel_rect.h), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 200))
        surface.blit(bg, panel_rect.topleft)
        pygame.draw.rect(surface, C_BORDER, panel_rect, 1, border_radius=4)

        # Title
        title = self.font_title.render("DATABASE DE HASHES", True, C_NEON)
        surface.blit(title, (self.LP_X + 4, self.FIRST_Y - 40))
        pygame.draw.line(
            surface, C_BORDER,
            (self.LP_X, self.FIRST_Y - 18),
            (self.LP_X + self.LP_W, self.FIRST_Y - 18), 1,
        )

        # Column labels
        lbl_w = self.font_label.render("CONTRASENAS", True, C_TEXT_HINT)
        surface.blit(lbl_w, (self.WORD_X, self.FIRST_Y - 14))
        lbl_h = self.font_label.render("SHA-256 (16 hex)", True, C_TEXT_HINT)
        surface.blit(lbl_h, (self.HASH_X, self.FIRST_Y - 14))

        # Word boxes
        self._draw_word_boxes(surface)

        # Hash boxes
        self._draw_hash_boxes(surface)

    # -- word boxes --------------------------------------------------------
    def _draw_word_boxes(self, surface):
        mouse_pos = pygame.mouse.get_pos()
        for i, rect in enumerate(self.word_rects):
            word = self.CANDIDATES[i]
            matched = i in self.matched_word_indices
            hovered = (
                not self.completed
                and not self.dialogue.active
                and rect.collidepoint(mouse_pos)
                and not matched
            )

            # Background
            box_surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            if matched:
                box_surf.fill((*C_GREEN, 50))
            else:
                box_surf.fill((0, 0, 0, 220))
            surface.blit(box_surf, rect.topleft)

            # Border
            border_col = C_GREEN if matched else (C_NEON if hovered else C_BORDER)
            _draw_rounded_rect(surface, rect, border_col, border_radius=4, border=2)

            # Prefix
            prefix = self.font_label.render(f"[{i+1}]", True, C_TEXT_HINT)
            surface.blit(prefix, (rect.x + 6, rect.y + 12))

            # Word text
            word_color = C_GREEN if matched else C_NEON
            txt = self.font_word.render(word, True, word_color)
            surface.blit(txt, (rect.x + 36, rect.y + 10))

    # -- hash boxes --------------------------------------------------------
    def _draw_hash_boxes(self, surface):
        mouse_pos = pygame.mouse.get_pos()
        for j, rect in enumerate(self.hash_rects):
            h = self.hash_order[j]
            matched = j in self.matched_hash_indices
            hovered = (
                not self.completed
                and not self.dialogue.active
                and rect.collidepoint(mouse_pos)
                and not matched
            )

            box_surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            if matched:
                box_surf.fill((*C_GREEN, 50))
            else:
                box_surf.fill((0, 0, 0, 220))
            surface.blit(box_surf, rect.topleft)

            border_col = C_GREEN if matched else (C_HASH if hovered else C_BORDER)
            _draw_rounded_rect(surface, rect, border_col, border_radius=4, border=2)

            hash_color = C_GREEN if matched else C_HASH
            txt = self.font_hash.render(h, True, hash_color)
            surface.blit(txt, (rect.x + 8, rect.y + 12))

    # -- connection line with glow -----------------------------------------
    def _draw_connection_line(self, surface, start, end, color, alpha_frac):
        alpha = int(255 * alpha_frac)
        line_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        glow_alpha = int(60 * alpha_frac)
        pygame.draw.line(line_surf, (*color, glow_alpha), start, end, 6)
        pygame.draw.line(line_surf, (*color, alpha), start, end, 2)
        surface.blit(line_surf, (0, 0))

    # -- rubber band -------------------------------------------------------
    def _draw_rubber_band(self, surface):
        line_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.line(
            line_surf, (*C_ACCENT, 50),
            self.drag_origin, self.drag_current, 6,
        )
        pygame.draw.line(
            line_surf, (*C_ACCENT, 180),
            self.drag_origin, self.drag_current, 2,
        )
        pygame.draw.circle(
            line_surf, (*C_ACCENT, 120), self.drag_current, 6, 1,
        )
        surface.blit(line_surf, (0, 0))

    # -- TERMINAL panel (right side) ---------------------------------------
    def _draw_terminal_panel(self, surface):
        # Panel background
        panel_rect = pygame.Rect(self.RP_X, self.RP_Y, self.RP_W, self.RP_H)
        pygame.draw.rect(surface, C_TERM_BG, panel_rect)
        pygame.draw.rect(surface, C_BORDER, panel_rect, 1, border_radius=4)

        # Title bar
        title_rect = pygame.Rect(self.RP_X, self.RP_Y, self.RP_W, 28)
        pygame.draw.rect(surface, (15, 18, 25), title_rect)
        pygame.draw.line(
            surface, C_BORDER,
            (self.RP_X, self.RP_Y + 28),
            (self.RP_X + self.RP_W, self.RP_Y + 28), 1,
        )
        title = self.font_title.render("TERMINAL DE CODIGO", True, C_NEON)
        surface.blit(title, (self.RP_X + 12, self.RP_Y + 6))

        # Fake window buttons (decorative)
        for i, col in enumerate([(138, 58, 58), (154, 138, 58), (74, 138, 90)]):
            pygame.draw.circle(
                surface, col,
                (self.RP_X + self.RP_W - 50 + i * 16, self.RP_Y + 14), 5,
            )

        # Code area
        cx = self.RP_X + 16
        cy = self.RP_Y + 44
        line_h = 22

        # Determine what to show based on terminal state
        if self.term_selected_word is None:
            # No word selected - show template with blanks
            code_lines = [
                (">>> ", C_TERM_GREEN, "import hashlib", C_NEON),
                (">>> ", C_TERM_GREEN, 'palabra = "________"', C_TEXT_SEC),
                (">>> ", C_TERM_GREEN, "h = hashlib.sha256(palabra.encode())",
                 C_TEXT_SEC),
                (">>> ", C_TERM_GREEN, "print(h.hexdigest()[:16])", C_TEXT_SEC),
                ("", None, "", None),
                ("Resultado: ", C_TEXT_HINT, "________________", C_TEXT_HINT),
            ]
            for prompt_text, prompt_col, code_text, code_col in code_lines:
                if prompt_col:
                    ps = self.font_term.render(prompt_text, True, prompt_col)
                    surface.blit(ps, (cx, cy))
                    pw = ps.get_width()
                else:
                    pw = 0
                if code_col:
                    cs = self.font_term.render(code_text, True, code_col)
                    surface.blit(cs, (cx + pw, cy))
                cy += line_h

            # Instruction text
            cy += line_h
            draw_text_box(
                surface,
                "Haz clic en una palabra para calcular su hash.",
                cx, cy, self.font_label, color=C_TEXT_SEC,
                bg_alpha=0, max_width=self.RP_W - 40,
            )
        else:
            # Word selected - show animated typing
            word = self.term_selected_word
            hash_result = sha256_short(word)
            typed_chars = int(self.term_typing_timer / self.term_typing_speed)

            # Line 1: import hashlib (always fully visible)
            self._draw_term_line(
                surface, cx, cy, ">>> ", "import hashlib",
                C_TERM_GREEN, C_NEON, 999,
            )
            cy += line_h

            # Line 2: palabra = "word"
            line2_text = f'palabra = "{word}"'
            chars_for_line2 = len(line2_text)
            self._draw_term_line(
                surface, cx, cy, ">>> ", line2_text,
                C_TERM_GREEN, C_NEON, typed_chars,
            )
            cy += line_h

            # Line 3: h = hashlib.sha256(...)
            line3_text = "h = hashlib.sha256(palabra.encode())"
            chars_for_line3 = len(line3_text)
            remaining2 = typed_chars - chars_for_line2
            self._draw_term_line(
                surface, cx, cy, ">>> ", line3_text,
                C_TERM_GREEN, C_NEON, remaining2,
            )
            cy += line_h

            # Line 4: print(...)
            line4_text = "print(h.hexdigest()[:16])"
            remaining3 = remaining2 - chars_for_line3
            self._draw_term_line(
                surface, cx, cy, ">>> ", line4_text,
                C_TERM_GREEN, C_NEON, remaining3,
            )
            cy += line_h * 2

            # Result line (only if typing is done)
            if self.term_typing_done:
                lbl = self.font_term.render("Resultado: ", True, C_TEXT_SEC)
                surface.blit(lbl, (cx, cy))

                # Flash effect on result
                if self.term_flash_timer > 0:
                    flash_alpha = int(
                        255 * (self.term_flash_timer / 0.5)
                    )
                    flash_surf = pygame.Surface(
                        (self.RP_W - 32, line_h + 4), pygame.SRCALPHA,
                    )
                    flash_surf.fill((*C_NEON, min(flash_alpha, 40)))
                    surface.blit(flash_surf, (cx, cy - 2))

                result_surf = self.font_term_result.render(
                    hash_result, True, C_NEON,
                )
                surface.blit(result_surf, (cx + lbl.get_width(), cy))

                # Instruction after result
                cy += line_h * 2
                draw_text_box(
                    surface,
                    f'Conecta "{word}" con este hash en el panel izquierdo.',
                    cx, cy, self.font_label, color=C_TERM_GREEN,
                    bg_alpha=0, max_width=self.RP_W - 40,
                )
            else:
                # Blinking cursor
                cursor_blink = int(self.term_typing_timer * 4) % 2 == 0
                if cursor_blink:
                    cur = self.font_term.render("_", True, C_NEON)
                    surface.blit(cur, (cx, cy))

        # Separator line above word buttons
        sep_y = self.TERM_BTN_Y - 16
        pygame.draw.line(
            surface, C_BORDER,
            (self.RP_X + 16, sep_y),
            (self.RP_X + self.RP_W - 16, sep_y), 1,
        )

        # Label for word buttons
        btn_lbl = self.font_label.render(
            "PALABRAS CANDIDATAS:", True, C_TEXT_HINT,
        )
        surface.blit(btn_lbl, (self.RP_X + 20, self.TERM_BTN_Y - 12))

        # Terminal word buttons
        mouse_pos = pygame.mouse.get_pos()
        for i, rect in enumerate(self.term_btn_rects):
            word = self.CANDIDATES[i]
            is_selected = (self.term_selected_word == word)
            is_matched = word in self.matched_pairs
            hovered = rect.collidepoint(mouse_pos) and not self.completed

            # Button background
            btn_surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            if is_matched:
                btn_surf.fill((*C_GREEN, 60))
            elif is_selected:
                btn_surf.fill((*C_NEON, 30))
            else:
                btn_surf.fill((0, 0, 0, 200))
            surface.blit(btn_surf, rect.topleft)

            # Border
            if is_matched:
                bcol = C_GREEN
            elif is_selected:
                bcol = C_NEON
            elif hovered:
                bcol = C_TERM_GREEN
            else:
                bcol = C_BORDER
            _draw_rounded_rect(surface, rect, bcol, border_radius=3, border=2)

            # Text
            tcol = C_GREEN if is_matched else (C_NEON if is_selected else C_TEXT_PRI)
            txt = self.font_btn.render(word, True, tcol)
            surface.blit(
                txt,
                (rect.centerx - txt.get_width() // 2,
                 rect.centery - txt.get_height() // 2),
            )

        # Hints section (below terminal buttons)
        self._draw_hints(surface)

    # -- terminal line helper ----------------------------------------------
    def _draw_term_line(self, surface, x, y, prompt, code,
                        prompt_col, code_col, chars_available):
        if chars_available <= 0:
            return
        ps = self.font_term.render(prompt, True, prompt_col)
        surface.blit(ps, (x, y))
        visible = code[:chars_available]
        cs = self.font_term.render(visible, True, code_col)
        surface.blit(cs, (x + ps.get_width(), y))

    # -- hint buttons (inside right panel area) ----------------------------
    def _draw_hints(self, surface):
        hint_label = self.font_label.render("PISTAS", True, C_TEXT_HINT)
        surface.blit(hint_label, (self.RP_X + 20, 578))

        mouse_pos = pygame.mouse.get_pos()
        for i, rect in enumerate(self.hint_rects):
            if i >= len(self.hints):
                break
            if self.hint_unlocked[i]:
                # Show hint text on black background
                draw_text_box(
                    surface, self.hints[i],
                    rect.x, rect.y, self.font_label,
                    color=C_TEXT_SEC, bg_alpha=200,
                    max_width=rect.w - 16,
                )
            else:
                can_unlock = (
                    (i == 0 or self.hint_unlocked[i - 1])
                    and not self.completed
                )
                hovered = can_unlock and rect.collidepoint(mouse_pos)
                border_col = C_ACCENT if hovered else C_BORDER
                box_surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
                box_surf.fill((0, 0, 0, 180))
                surface.blit(box_surf, rect.topleft)
                _draw_rounded_rect(
                    surface, rect, border_col, border_radius=3, border=1,
                )
                label = self.font_hint_btn.render(
                    f"[ PISTA {i+1} ]  (-15 pts)", True,
                    C_ACCENT if can_unlock else C_TEXT_HINT,
                )
                surface.blit(label, (rect.x + 8, rect.y + 8))

    # -- score / timer display ---------------------------------------------
    def _draw_timer(self, surface):
        mins = int(self.time_elapsed) // 60
        secs = int(self.time_elapsed) % 60
        time_str = f"TIEMPO: {mins:02d}:{secs:02d}"
        matched_str = f"PARES: {len(self.matched_pairs)}/5"
        fails_str = f"FALLOS: {self.failed_attempts}"

        tx = self.LP_X
        ty = self.FIRST_Y + 5 * (self.BOX_H + self.BOX_GAP) + 16

        # Black background for stats
        stats_bg = pygame.Surface((260, 80), pygame.SRCALPHA)
        stats_bg.fill((0, 0, 0, 200))
        surface.blit(stats_bg, (tx - 4, ty - 4))

        for text in [time_str, matched_str, fails_str]:
            txt_surf = self.font_score.render(text, True, C_NEON)
            surface.blit(txt_surf, (tx, ty))
            ty += 20

        if self.completed:
            score_str = f"PUNTUACION: {self.score}"
            sc_surf = self.font_score.render(score_str, True, C_GREEN)
            surface.blit(sc_surf, (tx, ty))

    # -- VOLVER button -----------------------------------------------------
    def _draw_back_button(self, surface):
        mouse_pos = pygame.mouse.get_pos()
        hovered = self.back_rect.collidepoint(mouse_pos)

        btn_bg = pygame.Surface(
            (self.back_rect.w, self.back_rect.h), pygame.SRCALPHA,
        )
        btn_bg.fill((0, 0, 0, 220))
        surface.blit(btn_bg, self.back_rect.topleft)

        bcol = C_NEON if hovered else C_BORDER
        _draw_rounded_rect(
            surface, self.back_rect, bcol, border_radius=4, border=2,
        )
        lbl = self.font_btn.render("< VOLVER", True, C_NEON if hovered else C_TEXT_SEC)
        surface.blit(
            lbl,
            (self.back_rect.centerx - lbl.get_width() // 2,
             self.back_rect.centery - lbl.get_height() // 2),
        )

    # -- debriefing popup --------------------------------------------------
    def _draw_debrief(self, surface):
        # Full-screen dim
        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 200))
        surface.blit(dim, (0, 0))

        # Popup box
        pw, ph = 700, 340
        px = WIDTH // 2 - pw // 2
        py = HEIGHT // 2 - ph // 2

        # Solid black background
        pygame.draw.rect(surface, (0, 0, 0), (px, py, pw, ph))
        pygame.draw.rect(surface, C_NEON, (px, py, pw, ph), 2, border_radius=4)

        # Title
        title = self.font_debrief_title.render("MISION COMPLETADA", True, C_NEON)
        surface.blit(title, (px + pw // 2 - title.get_width() // 2, py + 20))

        # Score line
        score_line = self.font_score.render(
            f"PUNTUACION FINAL: {self.score}/100", True, C_WHITE,
        )
        surface.blit(
            score_line,
            (px + pw // 2 - score_line.get_width() // 2, py + 56),
        )

        pygame.draw.line(
            surface, C_BORDER,
            (px + 30, py + 84), (px + pw - 30, py + 84), 1,
        )

        # Debrief text with word wrap on black bg
        wrapped = word_wrap(self.debrief_text, self.font_debrief, pw - 60)
        dy = py + 96
        for line in wrapped:
            txt = self.font_debrief.render(line, True, C_TEXT_PRI)
            surface.blit(txt, (px + 30, dy))
            dy += 20

        # Continue button
        hovered = self.debrief_btn.collidepoint(pygame.mouse.get_pos())
        btn_bg = pygame.Surface(
            (self.debrief_btn.w, self.debrief_btn.h), pygame.SRCALPHA,
        )
        btn_bg.fill((0, 0, 0, 240))
        surface.blit(btn_bg, self.debrief_btn.topleft)

        border_col = C_NEON if hovered else C_BORDER
        _draw_rounded_rect(
            surface, self.debrief_btn, border_col, border_radius=4, border=2,
        )
        btn_text = self.font_debrief_btn.render("[ CONTINUAR ]", True, C_NEON)
        surface.blit(
            btn_text,
            (self.debrief_btn.centerx - btn_text.get_width() // 2,
             self.debrief_btn.centery - btn_text.get_height() // 2),
        )
