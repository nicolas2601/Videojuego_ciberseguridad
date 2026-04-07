"""Diffie-Hellman signal-interceptor puzzle -- 3 rounds of increasing difficulty.
Round 1: guided worksheet, Round 2: timed no-guide, Round 3: MITM detection."""
import pygame, random, math
from game.constants import (WIDTH, HEIGHT, C_BG, C_BG2, C_BG3, C_BORDER, C_TEXT_PRI,
    C_TEXT_SEC, C_TEXT_HINT, C_ACCENT, C_GREEN, C_RED, C_NEON, C_WHITE, C_PANEL,
    C_DH, C_AMBER, C_TERM_BG, C_TERM_GREEN, HINTS_CONFIG,
    DIFFICULTY_DUMMY, DIFFICULTY_MID, DIFFICULTY_SENIOR, DIFFICULTY_NOOB)
from game.ui.draw_assets import (draw_server_rack, draw_monitor,
    draw_office_floor, draw_wall, draw_text_box, word_wrap)
from game.ui.dialogue import DialogueBox
from game.ui.hud import HUD
from crypto.dh_utils import dh_public, dh_shared_key

# ── Legacy exports for test compatibility ──
import colorsys as _colorsys
_G, _P, _B_SECRET = 5, 23, 15
_B_PUBLIC = dh_public(_G, _P, _B_SECRET)
_BASE_COLOR = (230, 210, 50)

def _number_to_color(n, p):
    h = n / p; r, g, b = _colorsys.hsv_to_rgb(h, 0.85, 0.95)
    return (int(r * 255), int(g * 255), int(b * 255))

def _blend_colors(c1, c2, ratio=0.5):
    return tuple(int(c1[i] * ratio + c2[i] * (1 - ratio)) for i in range(3))

# ── Round configs ──
_ROUNDS = [
    {"g": 5, "p": 23, "b_secret": 15, "timer": 0, "guided": True, "mitm": False},
    {"g": 7, "p": 41, "b_secret": 12, "timer": 90, "guided": False, "mitm": False},
    {"g": 3, "p": 29, "b_secret": 9, "timer": 45, "guided": False, "mitm": True},
]

def _dighash(val, p):
    return sum(int(d) for d in str(abs(val))) % p

# ── UI helpers ──
def _ctxt(s, f, txt, x, w, y, c):
    t = f.render(txt, True, c); s.blit(t, (x + (w - t.get_width()) // 2, y))

def _panel(surface, r, border_col):
    bg = pygame.Surface((r.w, r.h), pygame.SRCALPHA); bg.fill((12, 14, 22, 210))
    surface.blit(bg, r.topleft); pygame.draw.rect(surface, border_col, r, 1, border_radius=4)

def _btn(surface, rect, text, font, col, sel=False):
    hover = rect.collidepoint(pygame.mouse.get_pos())
    bc = col if (hover or sel) else C_BORDER
    pygame.draw.rect(surface, C_BG3, rect, border_radius=3)
    pygame.draw.rect(surface, bc, rect, 2 if sel else 1, border_radius=3)
    t = font.render(text, True, C_TEXT_PRI if not sel else col)
    surface.blit(t, (rect.x + (rect.w - t.get_width()) // 2, rect.y + (rect.h - t.get_height()) // 2))

# ── Calculator ──
class _Calculator:
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)
        self.display = ""; self.result = None
        self.fd = pygame.font.SysFont("monospace", 18, bold=True)
        self.fb = pygame.font.SysFont("monospace", 16, bold=True)
        self._keys = [["7","8","9","^"],["4","5","6","mod"],
                      ["1","2","3","DEL"],["0","C",".","="]]
        pad, dh, cols, rows = 4, 34, 4, 4
        bw = (w - pad * (cols + 1)) // cols; bh = (h - dh - pad * (rows + 2)) // rows
        self.dr = pygame.Rect(x + pad, y + pad, w - pad * 2, dh)
        self.br = {}
        top = y + dh + pad * 2
        for r, row in enumerate(self._keys):
            for c, lb in enumerate(row):
                self.br[lb] = pygame.Rect(x + pad + c * (bw + pad), top + r * (bh + pad), bw, bh)

    def press(self, key):
        if key == "C": self.display = ""; self.result = None
        elif key == "DEL": self.display = self.display[:-1]
        elif key == "=": self._eval()
        else: self.display += str(key)

    def _eval(self):
        e = self.display.replace(" ", "")
        try:
            if "^" in e and "mod" in e:
                a, rest = e.split("^", 1); b, m = rest.split("mod", 1)
                self.result = pow(int(a), int(b), int(m))
            else:
                self.result = int(e)
        except Exception:
            self.result = None; return
        self.display = str(self.result)

    def handle_click(self, pos):
        for lb, r in self.br.items():
            if r.collidepoint(pos): self.press(lb); return True
        return False

    def draw(self, surface):
        _panel(surface, self.rect, C_DH)
        pygame.draw.rect(surface, C_TERM_BG, self.dr, border_radius=3)
        pygame.draw.rect(surface, C_BORDER, self.dr, 1, border_radius=3)
        t = self.fd.render(self.display[-28:] or "0", True, C_TERM_GREEN)
        surface.blit(t, (self.dr.x + 6, self.dr.y + (self.dr.h - t.get_height()) // 2))
        for lb, r in self.br.items():
            hov = r.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(surface, C_ACCENT if hov else C_BG3, r, border_radius=3)
            pygame.draw.rect(surface, C_BORDER, r, 1, border_radius=3)
            tc = C_DH if lb in ("^", "mod", "=") else C_TEXT_PRI
            ts = self.fb.render(lb, True, tc)
            surface.blit(ts, (r.x + (r.w - ts.get_width()) // 2, r.y + (r.h - ts.get_height()) // 2))

# ── Step (field) ──
class _Step:
    def __init__(self, label, x, y, w, expected_fn, rng=None):
        self.label = label; self.rect = pygame.Rect(x, y, w, 28)
        self.fn = expected_fn; self.rng = rng
        self.value = ""; self.locked = False; self.correct = None
        self.active = False; self.blink = 0.0

    def confirm(self):
        if self.locked or not self.value.strip(): return None
        try: v = int(self.value)
        except ValueError: self.correct = False; return False
        if self.rng and not (self.rng[0] <= v <= self.rng[1]):
            self.correct = False; return False
        self.correct = self.fn(v)
        if self.correct: self.locked = True
        else: self.value = ""
        return self.correct

    def draw(self, surface, font):
        bc = C_GREEN if (self.locked and self.correct) else (
             C_RED if self.correct is False else (C_DH if self.active else C_BORDER))
        pygame.draw.rect(surface, C_TERM_BG, self.rect, border_radius=2)
        pygame.draw.rect(surface, bc, self.rect, 2 if self.active else 1, border_radius=2)
        ts = font.render(self.value, True, C_TEXT_PRI)
        surface.blit(ts, (self.rect.x + 4, self.rect.y + 5))
        if self.active and not self.locked:
            self.blink += 0.06
            if math.sin(self.blink * 4) > 0:
                cx = self.rect.x + 4 + ts.get_width() + 1
                pygame.draw.line(surface, C_DH, (cx, self.rect.y + 4), (cx, self.rect.y + 24))

# ── Main scene ──
class DHScene:
    def __init__(self, manager):
        self.manager = manager
        self.diff = getattr(manager, "difficulty", DIFFICULTY_MID)
        self.hcfg = HINTS_CONFIG.get(self.diff, HINTS_CONFIG[DIFFICULTY_MID])
        self.ft = pygame.font.SysFont("monospace", 15, bold=True)
        self.fl = pygame.font.SysFont("monospace", 13, bold=True)
        self.fv = pygame.font.SysFont("monospace", 14)
        self.ff = pygame.font.SysFont("monospace", 14, bold=True)
        self.fi = pygame.font.SysFont("monospace", 12)
        self.fb = pygame.font.SysFont("monospace", 20, bold=True)
        self.hud = HUD()
        self.hud.set_info(scene_name="ESCENA 04 -- SALA DE COMUNICACIONES", layer_text="RONDA 1/3")
        self.dialogue = DialogueBox()
        self.calc = _Calculator(WIDTH // 2 - 170, 490, 340, 200)
        self.round_idx = 0; self.score = 0; self.errors = 0; self.phase = "dialogue"
        self.timer = 0.0; self.timer_max = 0.0; self.steps = []; self.afi = -1
        self.nova_msg = ""; self.nova_timer = 0.0; self.anim_t = 0.0
        self.mitm_answer = None; self.mitm_which = None
        self.mitm_is_attack = False; self.mitm_signed_hash = 0; self._pa = 0
        self._cfg = _ROUNDS[0]; self._g = 5; self._p = 23; self._B = 0; self._Br = 0
        self.hints_used = 0; self.free_left = self.hcfg["free_hints"]
        self.back_rect = pygame.Rect(20, HEIGHT - 40, 120, 30)
        self.conf_rect = pygame.Rect(0, 0, 90, 24)
        self.btn_si = pygame.Rect(970, 370, 60, 26); self.btn_no = pygame.Rect(1040, 370, 60, 26)
        self.btn_a = pygame.Rect(970, 410, 60, 26); self.btn_b = pygame.Rect(1040, 410, 60, 26)
        self.btn_mc = pygame.Rect(970, 445, 130, 26)
        self.hint_rects = [pygame.Rect(940, 300 + i * 32, 130, 26) for i in range(3)]
        self.hint_states = [False, False, False]
        msgs = manager.dialogues.get("diffie_hellman", {}).get("enter", [])
        if msgs: self.dialogue.show(msgs, on_complete=self._intro_round)
        else: self._intro_round()

    def _intro_round(self):
        key = f"round_{self.round_idx + 1}_intro"
        msgs = self.manager.dialogues.get("diffie_hellman", {}).get(key, [])
        if msgs: self.dialogue.show(msgs, on_complete=self._start_round)
        else: self._start_round()

    def _start_round(self):
        cfg = _ROUNDS[self.round_idx]
        g, p, bs = cfg["g"], cfg["p"], cfg["b_secret"]
        B_real = dh_public(g, p, bs)
        self.timer_max = cfg["timer"]; self.timer = float(self.timer_max)
        self.nova_msg = ""; self.mitm_answer = None; self.mitm_which = None; self._pa = 0
        self.hint_states = [False, False, False]
        if cfg["mitm"]:
            self.mitm_is_attack = random.random() < 0.65
            if self.mitm_is_attack:
                fs = random.randint(2, p - 2)
                while fs == bs: fs = random.randint(2, p - 2)
                B_shown = dh_public(g, p, fs)
            else: B_shown = B_real
            self.mitm_signed_hash = _dighash(B_real, p)
        else: B_shown = B_real; self.mitm_is_attack = False
        self._cfg, self._g, self._p, self._B, self._Br = cfg, g, p, B_shown, B_real
        # Build steps in the terminal panel area
        tx, fw = 530, 100
        self.steps = [
            _Step("a", tx, 130, fw, lambda v: 2 <= v <= 20, (2, 20)),
            _Step("A", tx, 190, fw, lambda v: v == pow(g, self._ga(), p)),
            _Step("K", tx, 250, fw, lambda v: v == pow(self._B, self._ga(), p)),
        ]
        self.afi = 0
        if self.steps: self.steps[0].active = True
        self.phase = "play"
        self.hud.set_info(scene_name="ESCENA 04 -- SALA DE COMUNICACIONES",
                          layer_text=f"RONDA {self.round_idx + 1}/3")

    def _ga(self):
        for s in self.steps:
            if s.label == "a" and s.locked:
                return int(s.value)
        return self._pa

    # ── Events ──
    def handle_event(self, event):
        if self.dialogue.active: self.dialogue.handle_event(event); return
        if self.phase == "finished":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.back_rect.collidepoint(event.pos):
                    self.manager.change_scene("hub")
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            p = event.pos
            if self.back_rect.collidepoint(p): self.manager.change_scene("hub"); return
            if self.calc.handle_click(p): return
            # Click on step -> transfer calc result
            for i, s in enumerate(self.steps):
                if s.rect.collidepoint(p) and not s.locked:
                    self._setact(i)
                    if self.calc.result is not None: s.value = str(self.calc.result)
                    return
            if self.conf_rect.collidepoint(p): self._cfld(); return
            # Hint buttons
            for i, hr in enumerate(self.hint_rects):
                if hr.collidepoint(p) and self.phase == "play":
                    self._use_hint(i); return
            # MITM buttons
            if self._cfg.get("mitm") and self.phase == "play":
                if self.btn_si.collidepoint(p): self.mitm_answer = "SI"
                elif self.btn_no.collidepoint(p): self.mitm_answer = "NO"
                elif self.btn_a.collidepoint(p): self.mitm_which = "A"
                elif self.btn_b.collidepoint(p): self.mitm_which = "B"
                elif self.btn_mc.collidepoint(p): self._cmitm()
        elif event.type == pygame.KEYDOWN and self.phase == "play":
            if self.afi < 0 or self.afi >= len(self.steps): return
            s = self.steps[self.afi]
            if s.locked: return
            if event.key == pygame.K_RETURN: self._cfld()
            elif event.key == pygame.K_BACKSPACE: s.value = s.value[:-1]
            elif event.key == pygame.K_TAB: self._adv()
            elif event.unicode and event.unicode in "0123456789" and len(s.value) < 8:
                s.value += event.unicode

    def _setact(self, i):
        for j, s in enumerate(self.steps): s.active = (j == i)
        self.afi = i

    def _cfld(self):
        if self.afi < 0 or self.afi >= len(self.steps): return
        s = self.steps[self.afi]
        if s.locked: self._adv(); return
        r = s.confirm()
        if r is True:
            self.score += 15
            if s.label == "a": self._pa = int(s.value)
            self._adv(); self._chk()
        elif r is False:
            self.score = max(0, self.score - 5); self.errors += 1
            if self.timer_max > 0: self.timer = max(0, self.timer - 20)

    def _adv(self):
        for i in range(self.afi + 1, len(self.steps)):
            if not self.steps[i].locked: self._setact(i); return

    def _use_hint(self, idx):
        if self.hint_states[idx]: return
        if self.free_left <= 0:
            self.score = max(0, self.score - 10)
        else:
            self.free_left -= 1
        self.hint_states[idx] = True; self.hints_used += 1
        hints_data = self.manager.dialogues.get("diffie_hellman", {}).get("hints", {})
        hint = hints_data.get(f"hint_{idx + 1}", None)
        if hint:
            self.dialogue.show([{"speaker": hint.get("source", "NOVA"), "text": hint.get("text", "")}])
        else:
            fallback = ["Elige un secreto a entre 2 y 20.",
                        "A = g^a mod p. Usa la calculadora.",
                        "K = B^a mod p. B esta en el canal."]
            self.nova_msg = fallback[idx]; self.nova_timer = 3.0

    def _chk(self):
        if all(s.locked for s in self.steps):
            if self._cfg.get("mitm"): return
            self._fin()

    def _cmitm(self):
        if self.mitm_answer is None: return
        ok = "SI" if self.mitm_is_attack else "NO"
        if self.mitm_answer == ok:
            self.score += 40
            if self.mitm_is_attack and self.mitm_which == "B": self.score += 10
        else: self.score = max(0, self.score - 40)
        self._fin()

    def _fin(self):
        if self.timer_max > 0 and self.timer > 0: self.score += int(self.timer * 0.5)
        self.score += 30; self.round_idx += 1
        if self.round_idx >= len(_ROUNDS):
            self.phase = "finished"
            self.manager.complete_puzzle("diffie_hellman", self.score)
            ms = self.manager.dialogues.get("diffie_hellman", {}).get("success", [])
            if ms: self.dialogue.show(ms)
        else:
            self.dialogue.show(
                [{"speaker": "NOVA", "text": f"Ronda {self.round_idx} completada. "
                  f"Puntuacion: {self.score}. Preparate."}], on_complete=self._intro_round)

    # ── Update ──
    def update(self, dt):
        self.dialogue.update(dt); self.anim_t += dt
        if self.nova_timer > 0: self.nova_timer -= dt
        if self.phase == "play" and self.timer_max > 0:
            self.timer -= dt
            if self.timer <= 0: self.timer = 0; self._fin()

    # ── Draw ──
    def draw(self, surface):
        surface.fill(C_BG); draw_office_floor(surface); draw_wall(surface, 50, 30)
        draw_server_rack(surface, 1180, 100, h=120)
        draw_monitor(surface, 1100, 300, text="DH-KEY", text_color=C_DH)
        self.hud.draw(surface)
        self._dleft(surface); self._dcenter(surface); self._dright(surface)
        self.calc.draw(surface)
        _btn(surface, self.back_rect, "< VOLVER", self.fi, C_ACCENT)
        if self.nova_timer > 0 and self.nova_msg:
            r = pygame.Rect(20, HEIGHT - 80, WIDTH - 40, 36)
            bg = pygame.Surface((r.w, r.h), pygame.SRCALPHA); bg.fill((8, 10, 18, 220))
            surface.blit(bg, r.topleft); pygame.draw.rect(surface, C_NEON, r, 1, border_radius=3)
            pf = self.fl.render("NOVA: ", True, C_NEON); surface.blit(pf, (r.x + 8, r.y + 9))
            surface.blit(self.fi.render(self.nova_msg[:80], True, C_TEXT_PRI),
                         (r.x + 8 + pf.get_width(), r.y + 10))
        if self.phase == "finished": self._debrief(surface)
        self.dialogue.draw(surface)

    def _dleft(self, surface):
        r = pygame.Rect(20, 50, 310, 420); _panel(surface, r, C_DH)
        y = r.y + 8; _ctxt(surface, self.ft, "CANAL INTERCEPTADO", r.x, r.w, y, C_DH)
        y += 28; pygame.draw.line(surface, C_BORDER, (r.x + 10, y), (r.x + r.w - 10, y)); y += 14
        ax, bx = r.x + 40, r.x + r.w - 90
        for nx, nw, lb, c in [(ax,80,"ALICE",C_ACCENT),(bx,80,"BOB",C_GREEN)]:
            nr = pygame.Rect(nx, y, nw, 32)
            pygame.draw.rect(surface, C_BG3, nr, border_radius=4)
            pygame.draw.rect(surface, c, nr, 1, border_radius=4)
            _ctxt(surface, self.fl, lb, nr.x, nr.w, nr.y + 8, c)
        ly = y + 16; lx1, lx2 = ax + 84, bx - 4
        pygame.draw.line(surface, C_BORDER, (lx1, ly), (lx2, ly))
        dot_off = int(self.anim_t * 40) % max(1, lx2 - lx1)
        pygame.draw.circle(surface, C_DH, (lx1 + dot_off, ly), 3)
        y += 44
        if self._cfg.get("mitm"):
            ne = pygame.Rect(r.x + r.w // 2 - 40, y, 80, 28)
            pygame.draw.rect(surface, C_BG3, ne, border_radius=4)
            pygame.draw.rect(surface, C_RED, ne, 2, border_radius=4)
            _ctxt(surface, self.fl, "EVE", ne.x, ne.w, ne.y + 6, C_RED); y += 36
        y += 8
        for lb, val, xo in [("g", self._g, 20), ("p", self._p, 160)]:
            t1 = self.fl.render(f"{lb}:", True, C_TEXT_SEC)
            t2 = self.fv.render(str(val), True, C_TEXT_PRI)
            surface.blit(t1, (r.x + xo, y)); surface.blit(t2, (r.x + xo + t1.get_width() + 4, y))
        y += 28
        t1 = self.fl.render("B:", True, C_TEXT_SEC)
        t2 = self.fv.render(str(self._B), True, C_AMBER)
        surface.blit(t1, (r.x + 20, y)); surface.blit(t2, (r.x + 20 + t1.get_width() + 4, y)); y += 36
        if self._cfg.get("mitm"):
            pygame.draw.line(surface, C_BORDER, (r.x + 10, y), (r.x + r.w - 10, y)); y += 8
            _ctxt(surface, self.fl, "FIRMA CipherBureau", r.x, r.w, y, C_RED); y += 20
            surface.blit(self.fv.render(f"hash(B) = {self.mitm_signed_hash}", True, C_RED),
                         (r.x + 20, y)); y += 22
            surface.blit(self.fi.render("hash = sum_digitos(B) mod p", True, C_TEXT_HINT),
                         (r.x + 20, y))

    def _dcenter(self, surface):
        r = pygame.Rect(350, 50, 560, 420); _panel(surface, r, C_DH)
        y = r.y + 8; rn = min(self.round_idx + 1, 3)
        _ctxt(surface, self.ft, f"TERMINAL DE CALCULO -- RONDA {rn}/3", r.x, r.w, y, C_DH)
        y += 28; pygame.draw.line(surface, C_BORDER, (r.x + 10, y), (r.x + r.w - 10, y))
        if self.phase not in ("play", "round_done"): return
        x0 = r.x + 16; show_aid = self.diff <= DIFFICULTY_MID or self._cfg.get("guided", False)
        sy = r.y + 52; a_val = self._ga()
        prompts = [("> STEP 1: Elige secreto a (2-20)", "a"),
                   ("> STEP 2: Calcula A = g^a mod p", "A"),
                   ("> STEP 3: Calcula K = B^a mod p", "K")]
        aids = None
        if self.diff == DIFFICULTY_DUMMY:
            aids = [f"   [TIP] a entre 2 y 20",
                    f"   [TIP] A = {self._g}^a mod {self._p}" + (f" = {pow(self._g,a_val,self._p)}" if a_val else ""),
                    f"   [TIP] K = {self._B}^a mod {self._p}" + (f" = {pow(self._B,a_val,self._p)}" if a_val else "")]
        elif show_aid:
            aids = [f"   a en [2, 20]", f"   A = {self._g}^a mod {self._p}", f"   K = {self._B}^a mod {self._p}"]
        for i, (prompt, _) in enumerate(prompts):
            step = self.steps[i] if i < len(self.steps) else None
            col = C_GREEN if (step and step.locked) else C_TERM_GREEN
            pfx = "[OK] " if (step and step.locked) else ""
            surface.blit(self.fl.render(pfx + prompt, True, col), (x0, sy)); sy += 18
            if aids and i < len(aids):
                surface.blit(self.fi.render(aids[i], True, C_TEXT_HINT), (x0, sy)); sy += 16
            if step:
                step.rect.topleft = (x0 + 120, sy); step.draw(surface, self.ff)
                if step.active and not step.locked:
                    self.conf_rect.topleft = (step.rect.right + 8, step.rect.y)
                    _btn(surface, self.conf_rect, "CONFIRMAR", self.fi, C_GREEN)
            sy += 36
        if self._cfg.get("mitm") and all(s.locked for s in self.steps):
            surface.blit(self.fl.render("> STEP 4: Ataque MITM?", True, C_TERM_GREEN), (x0, sy))

    def _dright(self, surface):
        r = pygame.Rect(930, 50, 330, 420); _panel(surface, r, C_ACCENT)
        y = r.y + 8; _ctxt(surface, self.ft, "INTEL", r.x, r.w, y, C_ACCENT); y += 28
        if self.timer_max > 0 and self.phase == "play":
            tc = C_RED if self.timer < 15 else C_DH
            _ctxt(surface, self.fb, f"TIEMPO: {int(self.timer)}s", r.x, r.w, y, tc)
            bw = r.w - 40; ratio = max(0, self.timer / self.timer_max)
            pygame.draw.rect(surface, C_BG3, (r.x+20, y+30, bw, 8), border_radius=3)
            bc = C_GREEN if ratio > .4 else (C_AMBER if ratio > .15 else C_RED)
            pygame.draw.rect(surface, bc, (r.x+20, y+30, int(bw*ratio), 8), border_radius=3); y += 50
        t1 = self.fl.render("SCORE:", True, C_TEXT_SEC)
        t2 = self.fv.render(str(self.score), True, C_GREEN)
        surface.blit(t1, (r.x+20, y)); surface.blit(t2, (r.x+20+t1.get_width()+4, y)); y += 30
        if self.diff <= DIFFICULTY_MID:
            for ln in ["Usa la calculadora abajo:","  X^YmodZ y pulsa =","  click campo = transferir"]:
                surface.blit(self.fi.render(ln, True, C_TEXT_HINT), (r.x+15, y)); y += 16
            y += 4
        y = max(y, r.y + 200)
        surface.blit(self.fl.render("PISTAS:", True, C_TEXT_SEC), (r.x+15, y)); y += 22
        for i, hr in enumerate(self.hint_rects):
            hr.topleft = (r.x+15, y)
            if self.hint_states[i]: bc_h, lbl = C_TEXT_HINT, f"Pista {i+1} [usada]"
            elif i < self.free_left: bc_h, lbl = C_GREEN, f"Pista {i+1} [gratis]"
            else: bc_h, lbl = C_AMBER, f"Pista {i+1} [-10pts]"
            _btn(surface, hr, lbl, self.fi, bc_h, self.hint_states[i]); y += 32
        if self._cfg.get("mitm") and self.phase == "play":
            y = max(y, r.y + 320)
            pygame.draw.line(surface, C_BORDER, (r.x+10, y), (r.x+r.w-10, y)); y += 6
            _ctxt(surface, self.fl, "DETECCION MITM", r.x, r.w, y, C_RED); y += 20
            surface.blit(self.fi.render("Ataque MITM?", True, C_TEXT_SEC), (r.x+15, y))
            self.btn_si.topleft = (r.x+150, y-2); self.btn_no.topleft = (r.x+220, y-2)
            _btn(surface, self.btn_si, "SI", self.fl, C_GREEN, self.mitm_answer == "SI")
            _btn(surface, self.btn_no, "NO", self.fl, C_GREEN, self.mitm_answer == "NO"); y += 28
            surface.blit(self.fi.render("Valor manipulado:", True, C_TEXT_SEC), (r.x+15, y))
            self.btn_a.topleft = (r.x+150, y-2); self.btn_b.topleft = (r.x+220, y-2)
            _btn(surface, self.btn_a, "A", self.fl, C_AMBER, self.mitm_which == "A")
            _btn(surface, self.btn_b, "B", self.fl, C_AMBER, self.mitm_which == "B"); y += 28
            self.btn_mc.topleft = (r.x+15, y)
            _btn(surface, self.btn_mc, "CONFIRMAR MITM", self.fl, C_RED)

    # ── Debrief overlay ──
    def _debrief(self, surface):
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); ov.fill((0, 0, 0, 180))
        surface.blit(ov, (0, 0))
        dr = pygame.Rect(WIDTH // 2 - 220, HEIGHT // 2 - 140, 440, 280)
        _panel(surface, dr, C_DH)
        y = dr.y + 20
        _ctxt(surface, self.fb, "PROTOCOLO COMPLETADO", dr.x, dr.w, y, C_GREEN); y += 40
        for lb, val, c in [("Puntuacion final:", str(self.score), C_DH),
                           ("Errores:", str(self.errors), C_RED),
                           ("Pistas usadas:", str(self.hints_used), C_AMBER),
                           ("Dificultad:", ["DUMMY","MID","SENIOR","NOOB"][min(self.diff,3)], C_ACCENT)]:
            surface.blit(self.fl.render(lb, True, C_TEXT_SEC), (dr.x + 40, y))
            surface.blit(self.fv.render(val, True, c), (dr.x + 240, y))
            y += 28
        y += 16
        _ctxt(surface, self.fi, "Click VOLVER para regresar al hub", dr.x, dr.w, y, C_TEXT_HINT)
