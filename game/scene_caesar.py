"""CaesarScene — 3-round progressive difficulty Caesar cipher puzzle.
Round 1: visible shift, learn the concept.
Round 2: hidden shift, frequency analysis panel.
Round 3: 3 simultaneous messages under pressure."""
import pygame
import random
import math
import time

from game.constants import (
    WIDTH, HEIGHT, C_BG, C_BG2, C_BG3, C_BORDER, C_TEXT_PRI,
    C_TEXT_SEC, C_TEXT_HINT, C_ACCENT, C_GREEN, C_RED, C_NEON, C_WHITE,
    C_PANEL, C_CAESAR, C_AMBER, HINTS_CONFIG,
)
from game.ui.draw_assets import (
    draw_desk, draw_chair, draw_filing_cabinet, draw_office_floor,
    draw_wall, draw_text_box, word_wrap,
)
from game.ui.dialogue import DialogueBox
from game.ui.hud import HUD
from crypto.caesar import encrypt_caesar, decrypt_caesar

# ---------------------------------------------------------------------------
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
TWO_PI = math.pi * 2


def _lerp_color(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _scanlines(surface, alpha=12):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for y in range(0, HEIGHT, 3):
        pygame.draw.line(overlay, (0, 0, 0, alpha), (0, y), (WIDTH, y))
    surface.blit(overlay, (0, 0))


def _vignette(surface, intensity=35):
    vig = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for i in range(intensity):
        alpha = int((i / intensity) * 35)
        pygame.draw.rect(vig, (0, 0, 0, alpha),
                         (i, i, WIDTH - 2 * i, HEIGHT - 2 * i), 3)
    surface.blit(vig, (0, 0))


def _neon_text(surface, text, x, y, font, color=(57, 255, 20)):
    for offset in [3, 2, 1]:
        glow = font.render(text, True, color)
        gs = pygame.Surface(glow.get_size(), pygame.SRCALPHA)
        gs.blit(glow, (0, 0))
        gs.set_alpha(40)
        surface.blit(gs, (x - offset, y - offset))
        surface.blit(gs, (x + offset, y))
    surface.blit(font.render(text, True, color), (x, y))


def _draw_ambient_light(surface, cx, cy, radius, color, alpha=18):
    light = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for r in range(radius, 0, -2):
        a = int(alpha * (r / radius))
        pygame.draw.circle(light, (*color[:3], a), (radius, radius), r)
    surface.blit(light, (cx - radius, cy - radius))


# ---------------------------------------------------------------------------
# Message wrapper
# ---------------------------------------------------------------------------
class _Message:
    """A single cipher message with its own timer and state."""
    __slots__ = ("plain", "shift", "cipher", "timer", "max_timer",
                 "solved", "expired", "glitch_timer", "slot")

    def __init__(self, plain, shift, timer, slot=0):
        self.plain = plain.upper()
        self.shift = shift
        self.cipher = encrypt_caesar(self.plain, shift)
        self.max_timer = float(timer)
        self.timer = self.max_timer
        self.solved = False
        self.expired = False
        self.glitch_timer = 0.0
        self.slot = slot


# ---------------------------------------------------------------------------
# Particle
# ---------------------------------------------------------------------------
class _Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "size", "alpha")

    def __init__(self):
        self.x = random.uniform(0, WIDTH)
        self.y = random.uniform(0, HEIGHT)
        self.vx = random.uniform(-6, 6)
        self.vy = random.uniform(-10, -2)
        self.max_life = random.uniform(4.0, 10.0)
        self.life = random.uniform(0, self.max_life)
        self.size = random.uniform(1.0, 2.5)
        self.alpha = 0

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        if self.life <= 0:
            self.__init__()
        self.alpha = int(40 * (self.life / self.max_life))

    def draw(self, surface):
        if self.alpha <= 0:
            return
        s = max(1, int(self.size))
        ps = pygame.Surface((s * 2, s * 2), pygame.SRCALPHA)
        pygame.draw.circle(ps, (200, 210, 230, self.alpha), (s, s), s)
        surface.blit(ps, (int(self.x) - s, int(self.y) - s))


# ---------------------------------------------------------------------------
# CaesarScene
# ---------------------------------------------------------------------------
class CaesarScene:
    """3-round progressive Caesar cipher puzzle."""

    # -- Constants --
    ROUND_COUNT = 3
    ROUND_BONUS = 20
    MSG_BASE_PTS = 30
    MSG_LOST_PTS = -20
    WHEEL_CX, WHEEL_CY = 770, 360
    OUTER_R, INNER_R = 160, 120

    def __init__(self, manager):
        self.manager = manager
        self.puzzle = manager.puzzles["caesar"]
        self.dlg_data = manager.dialogues["caesar"]

        # Difficulty
        config = HINTS_CONFIG[manager.difficulty]
        self.free_hints = config["free_hints"]
        self.visual_aids = config["visual_aids"]

        # State
        self.current_round = 0          # 0 = not started yet (enter dialogue)
        self.phase = "enter_dialogue"    # enter_dialogue | round_intro | playing | transition | debriefing
        self.score = 0
        self.messages_decoded = 0
        self.messages_lost = 0
        self.time_elapsed = 0.0

        # Wheel
        self.shift = 0
        self.dragging = False
        self.drag_last_x = 0
        self.drag_accum = 0.0
        self._wheel_visual_angle = 0.0

        # Active messages for current round
        self.active_msgs = []
        self.selected_msg_idx = 0

        # Frequency panel data (round 2)
        self.freq_counts = {}

        # Hint objects (diegetic)
        self.hints_data = self.dlg_data.get("hints", {})
        self.hints_revealed = {"hint_1": False, "hint_2": False, "hint_3": False}
        self.hints_used = 0

        # Transition screen
        self._transition_timer = 0.0
        self._transition_text = ""

        # Flash feedback
        self.flash_color = None
        self.flash_timer = 0.0

        # Tick pulse
        self._tick_pulse = 0.0

        # Fonts
        self.font_title = pygame.font.SysFont("monospace", 15, bold=True)
        self.font_cipher = pygame.font.SysFont("monospace", 22, bold=True)
        self.font_label = pygame.font.SysFont("monospace", 13, bold=True)
        self.font_letter = pygame.font.SysFont("monospace", 14, bold=True)
        self.font_shift = pygame.font.SysFont("monospace", 30, bold=True)
        self.font_btn = pygame.font.SysFont("monospace", 14, bold=True)
        self.font_hint = pygame.font.SysFont("monospace", 12)
        self.font_debrief = pygame.font.SysFont("monospace", 14)
        self.font_debrief_title = pygame.font.SysFont("monospace", 18, bold=True)
        self.font_freq = pygame.font.SysFont("monospace", 10, bold=True)
        self.font_round = pygame.font.SysFont("monospace", 28, bold=True)

        # Buttons
        self.btn_confirm = pygame.Rect(740, HEIGHT - 70, 200, 44)
        self.btn_volver = pygame.Rect(20, HEIGHT - 70, 140, 44)
        self.btn_continue_debrief = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 + 140, 200, 44)

        # Hint clickable zones (diegetic objects)
        self.hint_zones = {
            "hint_1": pygame.Rect(50, 570, 60, 40),     # post-it
            "hint_2": pygame.Rect(180, 580, 70, 35),     # papers
            "hint_3": pygame.Rect(1050, HEIGHT - 70, 180, 44),  # radio button
        }

        # HUD
        self.hud = HUD()
        self.hud.set_info("ESCENA 01 -- SALA DEL ARCHIVISTA", "RONDA 0/3")

        # Dialogue
        self.dialogue = DialogueBox()
        self.dialogue.show(self.dlg_data["enter"],
                           on_complete=self._start_round_1_intro)

        # Cached surfaces
        self._bg_surface = None
        self._overlay_surface = None
        self._particles = [_Particle() for _ in range(30)]
        self._debrief_border_t = 0.0

    # ── Round management ──────────────────────────────────────────

    def _start_round_1_intro(self):
        self.current_round = 1
        self.hud.set_info("ESCENA 01 -- SALA DEL ARCHIVISTA", "RONDA 1/3")
        self.phase = "round_intro"
        self.dialogue.show(self.dlg_data["round_1_intro"],
                           on_complete=self._start_round_1)

    def _start_round_1(self):
        self.phase = "playing"
        self._load_round_messages(1)

    def _start_round_2_intro(self):
        self.current_round = 2
        self.hud.set_info("ESCENA 01 -- SALA DEL ARCHIVISTA", "RONDA 2/3")
        self._show_transition("RONDA 2/3 -- SHIFT VARIABLE", self._do_round_2_intro)

    def _do_round_2_intro(self):
        self.phase = "round_intro"
        self.freq_counts = {}
        self.dialogue.show(self.dlg_data["round_2_intro"],
                           on_complete=self._start_round_2)

    def _start_round_2(self):
        self.phase = "playing"
        self._load_round_messages(2)

    def _start_round_3_intro(self):
        self.current_round = 3
        self.hud.set_info("ESCENA 01 -- SALA DEL ARCHIVISTA", "RONDA 3/3")
        self._show_transition("RONDA 3/3 -- PRESION MAXIMA", self._do_round_3_intro)

    def _do_round_3_intro(self):
        self.phase = "round_intro"
        self.dialogue.show(self.dlg_data["round_3_intro"],
                           on_complete=self._start_round_3)

    def _start_round_3(self):
        self.phase = "playing"
        self._load_round_messages(3)

    def _show_transition(self, text, callback):
        self.phase = "transition"
        self._transition_text = text
        self._transition_timer = 2.0
        self._transition_callback = callback

    def _load_round_messages(self, rnd):
        """Build message list from puzzles.json round data + message_pool."""
        rd = self.puzzle.get(f"round_{rnd}", {})
        pool = self.puzzle.get("message_pool", [])
        timer = rd.get("timer_per_msg", 20)
        msgs_data = list(rd.get("messages", []))

        # Add 1-2 random messages from pool for variety
        if pool:
            extra = random.sample(pool, min(2, len(pool)))
            for e in extra:
                shift = random.randint(e["shift_range"][0], e["shift_range"][1])
                msgs_data.append({"plain": e["plain"], "shift": shift})

        random.shuffle(msgs_data)
        self.active_msgs = []
        self.selected_msg_idx = 0
        self.shift = 0

        if rnd == 3:
            # Round 3: exactly 3 simultaneous, all share one timer
            pick = msgs_data[:3] if len(msgs_data) >= 3 else msgs_data
            for i, md in enumerate(pick):
                self.active_msgs.append(_Message(md["plain"], md["shift"], timer, slot=i))
        else:
            # Rounds 1-2: deliver one at a time, take first
            if msgs_data:
                md = msgs_data[0]
                self.active_msgs.append(_Message(md["plain"], md["shift"], timer, slot=0))
            self._pending_msgs = msgs_data[1:]  # queue the rest

        # Update frequency counts for round 2
        if rnd == 2:
            self._update_freq()

    def _advance_queue(self):
        """Pop next pending message (rounds 1-2)."""
        if hasattr(self, "_pending_msgs") and self._pending_msgs:
            md = self._pending_msgs.pop(0)
            rd = self.puzzle.get(f"round_{self.current_round}", {})
            timer = rd.get("timer_per_msg", 15)
            self.active_msgs = [_Message(md["plain"], md["shift"], timer)]
            self.selected_msg_idx = 0
            self.shift = 0
            if self.current_round == 2:
                self._update_freq()
        else:
            # Round complete
            self.score += self.ROUND_BONUS
            self._next_round()

    def _next_round(self):
        if self.current_round == 1:
            self._start_round_2_intro()
        elif self.current_round == 2:
            self._start_round_3_intro()
        else:
            self._finish_scene()

    def _finish_scene(self):
        self.dialogue.show(self.dlg_data["success"],
                           on_complete=self._show_debriefing)

    def _show_debriefing(self):
        self.phase = "debriefing"

    def _update_freq(self):
        """Rebuild letter frequency from all active cipher texts."""
        self.freq_counts = {}
        for m in self.active_msgs:
            for ch in m.cipher:
                if ch.isalpha():
                    ch_up = ch.upper()
                    self.freq_counts[ch_up] = self.freq_counts.get(ch_up, 0) + 1

    # ── Events ────────────────────────────────────────────────────

    def handle_event(self, event):
        if self.phase == "debriefing":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.btn_continue_debrief.collidepoint(event.pos):
                    self.manager.complete_puzzle("caesar", max(self.score, 10))
                    self.manager.change_scene("hub")
            return

        if self.phase == "transition":
            return

        if self.dialogue.active:
            self.dialogue.handle_event(event)
            return

        if self.phase != "playing":
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            # VOLVER
            if self.btn_volver.collidepoint(event.pos):
                self.manager.change_scene("hub")
                return

            # Hint zones
            for key, zone in self.hint_zones.items():
                if zone.collidepoint(event.pos) and not self.hints_revealed[key]:
                    self.hints_revealed[key] = True
                    hint_d = self.hints_data.get(key, {})
                    cost = hint_d.get("cost", "free")
                    if cost != "free":
                        self.hints_used += 1
                    self.dialogue.show([
                        {"speaker": "NOVA",
                         "text": f"[{hint_d.get('source', key)}] {hint_d.get('text', '')}"}
                    ])
                    return

            # Wheel drag start
            dist = math.hypot(mx - self.WHEEL_CX, my - self.WHEEL_CY)
            if dist <= self.OUTER_R + 20:
                self.dragging = True
                self.drag_last_x = mx
                self.drag_accum = 0.0
                return

            # Confirm button
            if self.btn_confirm.collidepoint(event.pos):
                self._on_confirm()
                return

            # Round 3: click a message box to select it
            if self.current_round == 3 and self.active_msgs:
                for i, m in enumerate(self.active_msgs):
                    if not m.solved and not m.expired:
                        box_y = 80 + i * 100
                        box_rect = pygame.Rect(20, box_y, 460, 90)
                        if box_rect.collidepoint(event.pos):
                            self.selected_msg_idx = i
                            self.shift = 0
                            return

            # Radio call button (hint_3)
            if self.hint_zones["hint_3"].collidepoint(event.pos):
                pass  # handled above

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

    def _on_confirm(self):
        """Player confirms current shift for the selected message."""
        if not self.active_msgs:
            return
        idx = min(self.selected_msg_idx, len(self.active_msgs) - 1)
        msg = self.active_msgs[idx]
        if msg.solved or msg.expired:
            return

        if self.shift == msg.shift:
            msg.solved = True
            self.messages_decoded += 1
            time_ratio = max(0, msg.timer / msg.max_timer)
            bonus = int(self.MSG_BASE_PTS * (1.0 + time_ratio))
            self.score += bonus
            self.flash_color = C_GREEN
            self.flash_timer = 0.4
            self.dialogue.show(self.dlg_data["reactive_correct"])
            self._check_round_complete()
        else:
            self.flash_color = C_RED
            self.flash_timer = 0.4
            # Check if close (off by 1-2)
            diff = abs(self.shift - msg.shift)
            if diff <= 2 or diff >= 24:
                self.dialogue.show(self.dlg_data["reactive_close"])
            else:
                self.dialogue.show(self.dlg_data["reactive_wrong"])

    def _check_round_complete(self):
        """After solving or expiring, check if round is done."""
        if self.current_round == 3:
            all_done = all(m.solved or m.expired for m in self.active_msgs)
            if all_done:
                self.score += self.ROUND_BONUS
                self._next_round()
        else:
            # Rounds 1-2: advance to next queued message
            self._advance_queue()

    # ── Update ────────────────────────────────────────────────────

    def update(self, dt):
        self.time_elapsed += dt
        self._tick_pulse += dt * 4.0
        self._debrief_border_t += dt * 2.0
        self.dialogue.update(dt)

        for p in self._particles:
            p.update(dt)

        if self.flash_timer > 0:
            self.flash_timer = max(0.0, self.flash_timer - dt)

        # Transition screen countdown
        if self.phase == "transition":
            self._transition_timer -= dt
            if self._transition_timer <= 0:
                self._transition_callback()
            return

        # Smooth wheel visual angle
        target = self.shift * (TWO_PI / 26)
        diff = target - self._wheel_visual_angle
        if diff > math.pi:
            diff -= TWO_PI
        elif diff < -math.pi:
            diff += TWO_PI
        self._wheel_visual_angle += diff * min(1.0, dt * 12.0)

        # Tick down message timers
        if self.phase == "playing" and not self.dialogue.active:
            for m in self.active_msgs:
                if m.solved or m.expired:
                    continue
                m.timer -= dt
                if m.timer <= 0:
                    m.expired = True
                    m.glitch_timer = 0.8
                    self.messages_lost += 1
                    self.score += self.MSG_LOST_PTS
                    self.dialogue.show(self.dlg_data["reactive_timeout"])
                    self._check_round_complete()
                    break
                # Glitch decay on expired messages
            for m in self.active_msgs:
                if m.expired and m.glitch_timer > 0:
                    m.glitch_timer -= dt

    # ── Draw ──────────────────────────────────────────────────────

    def draw(self, surface):
        if self._bg_surface is None:
            self._build_bg()
        if self._overlay_surface is None:
            self._build_overlay()

        surface.blit(self._bg_surface, (0, 0))

        for p in self._particles:
            p.draw(surface)

        if self.phase == "transition":
            self._draw_transition(surface)
        elif self.phase == "debriefing":
            self._draw_debriefing(surface)
        else:
            self._draw_message_panel(surface)
            self._draw_wheel(surface)
            if self.current_round == 1 and self.phase == "playing":
                self._draw_visible_shift(surface)
            if self.current_round == 2 and self.phase == "playing":
                self._draw_freq_panel(surface)
            self._draw_info_panel(surface)
            self._draw_hint_objects(surface)

            if self.phase == "playing":
                self._draw_neon_button(surface, self.btn_confirm, "CONFIRMAR", C_CAESAR)
            self._draw_neon_button(surface, self.btn_volver, "VOLVER", C_ACCENT)

        # Flash overlay
        if self.flash_timer > 0 and self.flash_color:
            alpha = int(50 * (self.flash_timer / 0.4))
            fs = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            fs.fill((*self.flash_color, alpha))
            surface.blit(fs, (0, 0))

        surface.blit(self._overlay_surface, (0, 0))
        self.hud.draw(surface)
        self.dialogue.draw(surface)

    # ── Background ────────────────────────────────────────────────

    def _build_bg(self):
        self._bg_surface = pygame.Surface((WIDTH, HEIGHT))
        draw_office_floor(self._bg_surface)
        draw_wall(self._bg_surface, 0, wall_h=50)
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((*C_BG, 180))
        self._bg_surface.blit(overlay, (0, 0))
        draw_desk(self._bg_surface, 40, 560, w=120, h=50)
        draw_desk(self._bg_surface, 250, 580, w=100, h=40)
        draw_chair(self._bg_surface, 100, 620)
        draw_filing_cabinet(self._bg_surface, 1100, 500)
        _draw_ambient_light(self._bg_surface, 100, 580, 120, (80, 70, 50), 14)
        _draw_ambient_light(self._bg_surface, self.WHEEL_CX, self.WHEEL_CY, 200, (20, 60, 30), 8)

    def _build_overlay(self):
        self._overlay_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        _scanlines(self._overlay_surface, alpha=10)
        _vignette(self._overlay_surface, intensity=25)

    # ── Message panel (LEFT 40%) ──────────────────────────────────

    def _draw_message_panel(self, surface):
        panel_x, panel_y, panel_w = 20, 55, 480
        # Panel background
        bg = pygame.Surface((panel_w, 420), pygame.SRCALPHA)
        bg.fill((12, 16, 24, 200))
        surface.blit(bg, (panel_x, panel_y))
        pygame.draw.rect(surface, C_BORDER, (panel_x, panel_y, panel_w, 420), 1)

        # Title
        _neon_text(surface, "MENSAJES INTERCEPTADOS", panel_x + 12, panel_y + 8,
                   self.font_title, C_NEON)

        if not self.active_msgs:
            return

        y_off = panel_y + 35
        for i, m in enumerate(self.active_msgs):
            is_selected = (i == self.selected_msg_idx)
            box_h = 90
            box_rect = pygame.Rect(panel_x + 8, y_off, panel_w - 16, box_h)

            if m.expired:
                # Glitch / destroyed effect
                self._draw_expired_msg(surface, box_rect, m)
            else:
                # Message box background
                bg_a = 180 if is_selected else 120
                mb = pygame.Surface((box_rect.w, box_rect.h), pygame.SRCALPHA)
                mb.fill((18, 22, 32, bg_a))
                surface.blit(mb, box_rect.topleft)

                border_c = C_NEON if is_selected else C_BORDER
                pygame.draw.rect(surface, border_c, box_rect, 1)

                # Cipher text
                ct_surf = self.font_cipher.render(m.cipher, True, C_AMBER)
                surface.blit(ct_surf, (box_rect.x + 8, box_rect.y + 6))

                # Real-time decoded preview (using current wheel shift)
                decoded = decrypt_caesar(m.cipher, self.shift)
                dec_col = C_GREEN if self.shift == m.shift else C_TEXT_SEC
                dec_surf = self.font_label.render(f">> {decoded}", True, dec_col)
                surface.blit(dec_surf, (box_rect.x + 8, box_rect.y + 32))

                if m.solved:
                    # Green check
                    _neon_text(surface, "DESCIFRADO", box_rect.x + 8,
                               box_rect.y + 52, self.font_label, C_GREEN)
                else:
                    # Timer bar
                    self._draw_timer_bar(surface, box_rect.x + 8,
                                         box_rect.y + box_h - 16,
                                         box_rect.w - 16, 8, m)

            y_off += box_h + 8

    def _draw_expired_msg(self, surface, rect, msg):
        """Red glitch dissolve effect for self-destructed messages."""
        gl = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        t = pygame.time.get_ticks()

        if msg.glitch_timer > 0:
            # Active glitch animation
            for row in range(0, rect.h, 3):
                offset = random.randint(-8, 8)
                alpha = int(200 * msg.glitch_timer)
                color = (200, 40, 40, min(255, alpha))
                pygame.draw.line(gl, color,
                                 (max(0, offset), row),
                                 (min(rect.w, rect.w + offset), row))
        else:
            # Faded remains
            gl.fill((40, 15, 15, 60))

        surface.blit(gl, rect.topleft)
        label = self.font_label.render("AUTODESTRUIDO", True, C_RED)
        surface.blit(label, (rect.x + rect.w // 2 - label.get_width() // 2,
                             rect.y + rect.h // 2 - label.get_height() // 2))

    def _draw_timer_bar(self, surface, x, y, w, h, msg):
        """Neon timer bar that shrinks and changes color."""
        ratio = max(0, msg.timer / msg.max_timer)
        if ratio > 0.5:
            color = _lerp_color(C_AMBER, C_GREEN, (ratio - 0.5) * 2)
        else:
            color = _lerp_color(C_RED, C_AMBER, ratio * 2)

        # Background
        pygame.draw.rect(surface, (30, 30, 30), (x, y, w, h))
        # Fill
        fill_w = int(w * ratio)
        if fill_w > 0:
            bar_s = pygame.Surface((fill_w, h), pygame.SRCALPHA)
            bar_s.fill((*color, 200))
            surface.blit(bar_s, (x, y))
            # Neon glow on edge
            if fill_w > 2:
                edge_s = pygame.Surface((4, h), pygame.SRCALPHA)
                edge_s.fill((*color, 100))
                surface.blit(edge_s, (x + fill_w - 2, y))

        # Time text
        txt = self.font_freq.render(f"{msg.timer:.1f}s", True, C_WHITE)
        surface.blit(txt, (x + w - txt.get_width() - 2, y - 1))

    # ── Visible shift indicator (Round 1) ─────────────────────────

    def _draw_visible_shift(self, surface):
        """Big prominent shift value display for round 1."""
        if not self.active_msgs:
            return
        msg = self.active_msgs[0]
        if msg.solved or msg.expired:
            return

        bx, by, bw, bh = 520, 80, 180, 80
        bg = pygame.Surface((bw, bh), pygame.SRCALPHA)
        bg.fill((20, 40, 20, 200))
        surface.blit(bg, (bx, by))

        t = pygame.time.get_ticks()
        pulse = int(200 + 55 * math.sin(t * 0.005))
        pygame.draw.rect(surface, (*C_GREEN[:3],), (bx, by, bw, bh), 2)

        _neon_text(surface, "SHIFT VISIBLE", bx + 20, by + 6,
                   self.font_label, C_GREEN)
        _neon_text(surface, str(msg.shift), bx + bw // 2 - 15, by + 28,
                   self.font_shift, C_GREEN)

    # ── Frequency panel (Round 2) ─────────────────────────────────

    def _draw_freq_panel(self, surface):
        """Letter frequency bar chart, right side."""
        px, py, pw, ph = 960, 55, 300, 350
        bg = pygame.Surface((pw, ph), pygame.SRCALPHA)
        bg.fill((12, 16, 24, 200))
        surface.blit(bg, (px, py))
        pygame.draw.rect(surface, C_BORDER, (px, py, pw, ph), 1)

        _neon_text(surface, "FRECUENCIA DE LETRAS", px + 10, py + 6,
                   self.font_label, C_ACCENT)

        if not self.freq_counts:
            return

        max_count = max(self.freq_counts.values()) if self.freq_counts else 1
        sorted_letters = sorted(self.freq_counts.items(), key=lambda x: -x[1])

        bar_x = px + 10
        bar_y_start = py + 30
        bar_max_w = pw - 60
        bar_h = 11
        spacing = 13

        for i, (letter, count) in enumerate(sorted_letters[:22]):
            y = bar_y_start + i * spacing
            if y + bar_h > py + ph - 10:
                break
            # Letter label
            lbl = self.font_freq.render(letter, True, C_WHITE)
            surface.blit(lbl, (bar_x, y))

            # Bar
            ratio = count / max_count
            bw = int(bar_max_w * ratio)
            color = C_GREEN if i == 0 else C_ACCENT
            if bw > 0:
                bs = pygame.Surface((bw, bar_h - 2), pygame.SRCALPHA)
                bs.fill((*color, 180))
                surface.blit(bs, (bar_x + 16, y + 1))

            # Count
            ct = self.font_freq.render(str(count), True, C_TEXT_SEC)
            surface.blit(ct, (bar_x + 18 + bw, y))

        # Hint text
        hint = self.font_freq.render("La letra mas comun en espanol = E", True, C_TEXT_HINT)
        surface.blit(hint, (px + 10, py + ph - 18))

    # ── Info panel (RIGHT) ────────────────────────────────────────

    def _draw_info_panel(self, surface):
        """Stats panel on the right (below frequency or standalone)."""
        py_base = 420 if self.current_round == 2 else 55
        px, pw, ph = 960, 300, 180
        if self.current_round == 2:
            py_base = 420
        bg = pygame.Surface((pw, ph), pygame.SRCALPHA)
        bg.fill((12, 16, 24, 180))
        surface.blit(bg, (px, py_base))
        pygame.draw.rect(surface, C_BORDER, (px, py_base, pw, ph), 1)

        y = py_base + 10
        x = px + 12
        lines = [
            (f"RONDA: {self.current_round}/3", C_WHITE),
            (f"DESCIFRADOS: {self.messages_decoded}", C_GREEN),
            (f"PERDIDOS: {self.messages_lost}", C_RED if self.messages_lost > 0 else C_TEXT_SEC),
            (f"TIEMPO: {int(self.time_elapsed)}s", C_TEXT_SEC),
            (f"PUNTUACION: {self.score}", C_NEON),
            (f"PISTAS USADAS: {self.hints_used}", C_AMBER if self.hints_used > 0 else C_TEXT_SEC),
        ]
        for text, color in lines:
            surf = self.font_label.render(text, True, color)
            surface.blit(surf, (x, y))
            y += 22

    # ── Hint diegetic objects ─────────────────────────────────────

    def _draw_hint_objects(self, surface):
        """Draw clickable hint objects in the scene."""
        t = pygame.time.get_ticks()

        # hint_1: POST-IT (yellow square near desk)
        zone = self.hint_zones["hint_1"]
        if not self.hints_revealed["hint_1"]:
            yellow = (210, 200, 60)
            pygame.draw.rect(surface, yellow, zone)
            pygame.draw.rect(surface, (180, 170, 40), zone, 1)
            lbl = self.font_freq.render("POST-IT", True, (40, 40, 20))
            surface.blit(lbl, (zone.x + 4, zone.y + 14))
            # Pulse glow on hover
            mx, my = pygame.mouse.get_pos()
            if zone.collidepoint(mx, my):
                gs = pygame.Surface((zone.w + 8, zone.h + 8), pygame.SRCALPHA)
                gs.fill((*yellow, 40))
                surface.blit(gs, (zone.x - 4, zone.y - 4))

        # hint_2: DOCUMENT (papers on desk)
        zone2 = self.hint_zones["hint_2"]
        if not self.hints_revealed["hint_2"]:
            paper = (180, 175, 160)
            pygame.draw.rect(surface, paper, zone2)
            pygame.draw.rect(surface, (140, 135, 120), zone2, 1)
            # Paper lines
            for ly in range(zone2.y + 6, zone2.y + zone2.h - 4, 5):
                pygame.draw.line(surface, (120, 115, 100),
                                 (zone2.x + 4, ly), (zone2.x + zone2.w - 4, ly))
            lbl = self.font_freq.render("DOC", True, (60, 55, 40))
            surface.blit(lbl, (zone2.x + 20, zone2.y + 10))

        # hint_3: RADIO CALL (button)
        zone3 = self.hint_zones["hint_3"]
        if not self.hints_revealed["hint_3"]:
            self._draw_neon_button(surface, zone3, "CONTACTAR BASE", C_AMBER)

    # ── Caesar wheel (CENTER) ─────────────────────────────────────

    def _draw_wheel(self, surface):
        cx, cy = self.WHEEL_CX, self.WHEEL_CY
        outer_r, inner_r = self.OUTER_R, self.INNER_R

        # Outer ring gradient
        for r in range(outer_r, inner_r, -1):
            frac = (r - inner_r) / (outer_r - inner_r)
            b = int(20 + 30 * math.sin(frac * math.pi))
            pygame.draw.circle(surface, (b + 5, b + 8, b + 18), (cx, cy), r)

        pygame.draw.circle(surface, (60, 70, 100), (cx, cy), outer_r, 2)

        # Inner ring
        for r in range(inner_r, 45, -1):
            frac = (r - 45) / (inner_r - 45)
            b = int(12 + 16 * frac)
            pygame.draw.circle(surface, (b, b + 2, b + 8), (cx, cy), r)

        pygame.draw.circle(surface, (50, 60, 90), (cx, cy), inner_r, 2)

        # Center disc
        for r in range(45, 0, -1):
            frac = r / 45.0
            b = int(20 + 18 * frac)
            pygame.draw.circle(surface, (b, b + 4, b + 12), (cx, cy), r)

        glow_col = C_CAESAR
        for w in range(4, 0, -1):
            a = 60 + (4 - w) * 40
            gs = pygame.Surface((100, 100), pygame.SRCALPHA)
            pygame.draw.circle(gs, (*glow_col, a), (50, 50), 45, w)
            surface.blit(gs, (cx - 50, cy - 50))

        # Shift number in center
        _neon_text(surface, str(self.shift), cx - 10, cy - 16,
                   self.font_shift, glow_col)

        # Letters
        angle_step = TWO_PI / 26
        start_angle = -math.pi / 2
        letter_outer_r = outer_r - 16
        letter_inner_r = inner_r - 16

        # Check if current shift matches any active message
        correct_shift = False
        if self.active_msgs:
            idx = min(self.selected_msg_idx, len(self.active_msgs) - 1)
            m = self.active_msgs[idx]
            correct_shift = (self.shift == m.shift and not m.solved and not m.expired)

        for i, ch in enumerate(ALPHABET):
            angle = start_angle + i * angle_step

            # Outer letter
            ox = cx + math.cos(angle) * letter_outer_r
            oy = cy + math.sin(angle) * letter_outer_r
            outer_color = C_WHITE if i == 0 else C_TEXT_PRI
            ls = self.font_letter.render(ch, True, outer_color)
            surface.blit(ls, (int(ox) - ls.get_width() // 2,
                              int(oy) - ls.get_height() // 2))

            # Inner letter (shifted)
            shifted_ch = ALPHABET[(i + self.shift) % 26]
            ix = cx + math.cos(angle) * letter_inner_r
            iy = cy + math.sin(angle) * letter_inner_r
            inner_color = C_GREEN if correct_shift else (C_CAESAR if i == 0 else C_ACCENT)
            ins = self.font_letter.render(shifted_ch, True, inner_color)
            surface.blit(ins, (int(ix) - ins.get_width() // 2,
                               int(iy) - ins.get_height() // 2))

            # Tick marks
            pulse = 0.5 + 0.5 * math.sin(self._tick_pulse + i * 0.3)
            tick_alpha = int(80 + 80 * pulse)
            t1r, t2r = inner_r + 2, outer_r - 2
            ta = angle - angle_step / 2
            t1x = cx + math.cos(ta) * t1r
            t1y = cy + math.sin(ta) * t1r
            t2x = cx + math.cos(ta) * t2r
            t2y = cy + math.sin(ta) * t2r
            ts = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.line(ts, (60, 70, 100, tick_alpha),
                             (int(t1x), int(t1y)), (int(t2x), int(t2y)), 1)
            surface.blit(ts, (0, 0))

        # Triangle indicator
        tri_y = cy - outer_r - 14
        tri_pts = [(cx, tri_y + 16), (cx - 10, tri_y), (cx + 10, tri_y)]
        pygame.draw.polygon(surface, C_CAESAR, tri_pts)
        pygame.draw.polygon(surface, C_WHITE, tri_pts, 1)

        # Drag hint
        draw_text_box(surface, "Arrastrar para rotar",
                      cx - 80, cy + outer_r + 10,
                      self.font_hint, color=C_TEXT_HINT, bg_alpha=160)

    # ── Transition screen ─────────────────────────────────────────

    def _draw_transition(self, surface):
        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 200))
        surface.blit(dim, (0, 0))

        _neon_text(surface, self._transition_text,
                   WIDTH // 2 - len(self._transition_text) * 7,
                   HEIGHT // 2 - 20, self.font_round, C_NEON)

        # Pulsing bar
        t = pygame.time.get_ticks()
        bw = int(300 * (0.5 + 0.5 * math.sin(t * 0.006)))
        bx = WIDTH // 2 - bw // 2
        bar = pygame.Surface((bw, 4), pygame.SRCALPHA)
        bar.fill((*C_NEON, 160))
        surface.blit(bar, (bx, HEIGHT // 2 + 30))

    # ── Debriefing popup ──────────────────────────────────────────

    def _draw_debriefing(self, surface):
        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 200))
        surface.blit(dim, (0, 0))

        pw, ph = 700, 360
        px = (WIDTH - pw) // 2
        py = (HEIGHT - ph) // 2

        glass = pygame.Surface((pw, ph), pygame.SRCALPHA)
        glass.fill((8, 12, 20, 230))
        surface.blit(glass, (px, py))

        t = self._debrief_border_t
        border_col = _lerp_color(C_CAESAR, C_NEON, 0.5 + 0.5 * math.sin(t))
        pygame.draw.rect(surface, border_col, (px, py, pw, ph), 2, border_radius=6)

        # Corner decorations
        clen = 20
        for (cx, cy, dx, dy) in [
            (px, py, 1, 1), (px + pw, py, -1, 1),
            (px, py + ph, 1, -1), (px + pw, py + ph, -1, -1),
        ]:
            pygame.draw.line(surface, C_NEON, (cx, cy), (cx + clen * dx, cy), 2)
            pygame.draw.line(surface, C_NEON, (cx, cy), (cx, cy + clen * dy), 2)

        _neon_text(surface, "DEBRIEFING", px + pw // 2 - 60, py + 20,
                   self.font_debrief_title, C_NEON)

        pygame.draw.line(surface, C_BORDER, (px + 30, py + 50), (px + pw - 30, py + 50), 1)

        _neon_text(surface, f"PUNTUACION FINAL: {max(self.score, 10)}",
                   px + pw // 2 - 100, py + 62, self.font_btn, C_GREEN)

        # Stats summary
        stats_lines = [
            f"Mensajes descifrados: {self.messages_decoded}",
            f"Mensajes perdidos: {self.messages_lost}",
            f"Pistas usadas: {self.hints_used}",
            f"Tiempo total: {int(self.time_elapsed)}s",
        ]
        for i, line in enumerate(stats_lines):
            s = self.font_debrief.render(line, True, C_TEXT_SEC)
            surface.blit(s, (px + 40, py + 90 + i * 22))

        # Narrative text
        narrative = ("El Archivista confiaba en Cesar porque nadie mas en "
                     "Phantom Protocol sabia criptografia. 25 intentos y "
                     "cualquier script lo rompe. El analisis de frecuencia "
                     "existe desde el siglo IX.")
        draw_text_box(surface, narrative, px + 40, py + 195,
                      self.font_debrief, color=C_NEON, bg_alpha=0,
                      padding=4, max_width=pw - 80)

        # Continue button
        self.btn_continue_debrief = pygame.Rect(px + pw // 2 - 100, py + ph - 60, 200, 44)
        self._draw_neon_button(surface, self.btn_continue_debrief, "CONTINUAR", C_CAESAR)

    # ── Neon button ───────────────────────────────────────────────

    def _draw_neon_button(self, surface, rect, text, color):
        mx, my = pygame.mouse.get_pos()
        hover = rect.collidepoint(mx, my)

        bg_col = _lerp_color(C_PANEL, color, 0.30 if hover else 0.12)
        pygame.draw.rect(surface, bg_col, rect, border_radius=5)

        border_col = color if hover else _lerp_color(C_BORDER, color, 0.4)
        pygame.draw.rect(surface, border_col, rect, 2, border_radius=5)

        if hover:
            glow = pygame.Surface((rect.w + 8, rect.h + 8), pygame.SRCALPHA)
            pygame.draw.rect(glow, (*color, 30), (0, 0, rect.w + 8, rect.h + 8),
                             border_radius=7)
            surface.blit(glow, (rect.x - 4, rect.y - 4))

        txt_color = C_WHITE if hover else C_TEXT_PRI
        lbl = self.font_btn.render(text, True, txt_color)
        surface.blit(lbl, (rect.centerx - lbl.get_width() // 2,
                           rect.centery - lbl.get_height() // 2))
