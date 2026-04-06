"""Diffie-Hellman manual calculator puzzle -- 3 rounds of increasing difficulty.
Round 1: guided worksheet, Round 2: timed no-guide, Round 3: MITM detection."""
import pygame, random, math, time
from game.constants import (WIDTH, HEIGHT, C_BG, C_BG2, C_BG3, C_BORDER, C_TEXT_PRI,
    C_TEXT_SEC, C_TEXT_HINT, C_ACCENT, C_GREEN, C_RED, C_NEON, C_WHITE, C_PANEL,
    C_DH, C_AMBER, C_TERM_BG, C_TERM_GREEN, HINTS_CONFIG)
from game.ui.draw_assets import (draw_server_rack, draw_monitor,
    draw_office_floor, draw_wall, draw_text_box, word_wrap)
from game.ui.dialogue import DialogueBox
from game.ui.hud import HUD
from crypto.dh_utils import dh_public, dh_shared_key

# Legacy exports for test compatibility
import colorsys as _colorsys
_G, _P, _B_SECRET = 5, 23, 15
_B_PUBLIC = dh_public(_G, _P, _B_SECRET)
_BASE_COLOR = (230, 210, 50)

def _number_to_color(n, p):
    h = n / p; r, g, b = _colorsys.hsv_to_rgb(h, 0.85, 0.95)
    return (int(r*255), int(g*255), int(b*255))

def _blend_colors(c1, c2, ratio=0.5):
    return tuple(int(c1[i]*ratio + c2[i]*(1-ratio)) for i in range(3))

_ROUNDS = [
    {"g": 5, "p": 23, "b_secret": 15, "timer": 0, "guided": True, "mitm": False},
    {"g": 7, "p": 41, "b_secret": 12, "timer": 90, "guided": False, "mitm": False},
    {"g": 3, "p": 29, "b_secret": 9, "timer": 45, "guided": False, "mitm": True},
]

def _dighash(val, p):
    return sum(int(d) for d in str(abs(val))) % p

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
    surface.blit(t, (rect.x + (rect.w - t.get_width()) // 2, rect.y + 5))


class _Calculator:
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)
        self.display = ""; self.result = None
        self.fd = pygame.font.SysFont("monospace", 18, bold=True)
        self.fb = pygame.font.SysFont("monospace", 16, bold=True)
        self._keys = [["7","8","9","^"],["4","5","6","mod"],
                      ["1","2","3","DEL"],["0","C",".","="]]
        pad, dh, cols, rows = 4, 34, 4, 4
        bw = (w - pad*(cols+1))//cols; bh = (h - dh - pad*(rows+2))//rows
        self.dr = pygame.Rect(x+pad, y+pad, w-pad*2, dh)
        self.br = {}
        top = y + dh + pad*2
        for r, row in enumerate(self._keys):
            for c, lb in enumerate(row):
                self.br[lb] = pygame.Rect(x+pad+c*(bw+pad), top+r*(bh+pad), bw, bh)

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
            else: self.result = int(e)
        except Exception: self.result = None; return
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
        surface.blit(t, (self.dr.x+6, self.dr.y+(self.dr.h-t.get_height())//2))
        for lb, r in self.br.items():
            hov = r.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(surface, C_ACCENT if hov else C_BG3, r, border_radius=3)
            pygame.draw.rect(surface, C_BORDER, r, 1, border_radius=3)
            tc = C_DH if lb in ("^","mod","=") else C_TEXT_PRI
            ts = self.fb.render(lb, True, tc)
            surface.blit(ts, (r.x+(r.w-ts.get_width())//2, r.y+(r.h-ts.get_height())//2))


class _Field:
    def __init__(self, label, x, y, w, fn, rng=None):
        self.label, self.rect, self.fn, self.rng = label, pygame.Rect(x,y,w,26), fn, rng
        self.value, self.locked, self.correct, self.active, self.blink = "", False, None, False, 0.

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

    def draw(self, surface, font, t):
        bc = C_GREEN if (self.locked and self.correct) else (
             C_RED if self.correct is False else (C_DH if self.active else C_BORDER))
        pygame.draw.rect(surface, C_TERM_BG, self.rect, border_radius=2)
        pygame.draw.rect(surface, bc, self.rect, 2 if self.active else 1, border_radius=2)
        ts = font.render(self.value, True, C_TEXT_PRI)
        surface.blit(ts, (self.rect.x+4, self.rect.y+4))
        if self.active and not self.locked:
            self.blink += 0.06
            if math.sin(self.blink*4) > 0:
                cx = self.rect.x + 4 + ts.get_width() + 1
                pygame.draw.line(surface, C_DH, (cx, self.rect.y+4), (cx, self.rect.y+22))


class DHScene:
    def __init__(self, manager):
        self.manager = manager
        self.ft = pygame.font.SysFont("monospace", 15, bold=True)
        self.fl = pygame.font.SysFont("monospace", 13, bold=True)
        self.fv = pygame.font.SysFont("monospace", 14)
        self.ff = pygame.font.SysFont("monospace", 14, bold=True)
        self.fi = pygame.font.SysFont("monospace", 12)
        self.fb = pygame.font.SysFont("monospace", 20, bold=True)
        self.hud = HUD()
        self.hud.set_info(scene_name="ESCENA 04 -- SALA DE COMUNICACIONES",
                          layer_text="RONDA 1/3")
        self.dialogue = DialogueBox()
        self.calc = _Calculator(WIDTH//2 - 170, 490, 340, 200)
        self.round_idx = 0; self.score = 0; self.phase = "dialogue"
        self.timer = 0.; self.timer_max = 0.; self.fields = []; self.afi = -1
        self.nova_msg = ""; self.nova_timer = 0.
        self.mitm_answer = None; self.mitm_which = None
        self.mitm_is_attack = False; self.mitm_signed_hash = 0; self._pa = 0
        self._cfg = _ROUNDS[0]; self._g = 5; self._p = 23; self._B = 0; self._Br = 0
        self.back_rect = pygame.Rect(20, HEIGHT-40, 120, 30)
        self.conf_rect = pygame.Rect(0, 0, 90, 24)
        self.btn_si = pygame.Rect(970,400,60,28); self.btn_no = pygame.Rect(1040,400,60,28)
        self.btn_a = pygame.Rect(970,440,60,28); self.btn_b = pygame.Rect(1040,440,60,28)
        self.btn_mc = pygame.Rect(970,480,130,28)
        msgs = manager.dialogues.get("diffie_hellman", {}).get("enter", [])
        if msgs: self.dialogue.show(msgs, on_complete=self._start_round)
        else: self._start_round()

    def _start_round(self):
        cfg = _ROUNDS[self.round_idx]
        g, p, bs = cfg["g"], cfg["p"], cfg["b_secret"]
        B_real = dh_public(g, p, bs)
        self.timer_max = cfg["timer"]; self.timer = float(self.timer_max)
        self.nova_msg = ""; self.mitm_answer = None; self.mitm_which = None; self._pa = 0
        if cfg["mitm"]:
            self.mitm_is_attack = random.random() < 0.65
            if self.mitm_is_attack:
                fs = random.randint(2, p-2)
                while fs == bs: fs = random.randint(2, p-2)
                B_shown = dh_public(g, p, fs)
            else: B_shown = B_real
            self.mitm_signed_hash = _dighash(B_real, p)
        else: B_shown = B_real; self.mitm_is_attack = False
        self._cfg, self._g, self._p, self._B, self._Br = cfg, g, p, B_shown, B_real
        self.fields = []; cx, fw = 380, 80
        if cfg["guided"]:
            y0 = 90
            self.fields += [
                _Field("a", cx+200, y0+60, fw, lambda v: 2<=v<=20, (2,20)),
                _Field("g_fill", cx+80, y0+100, 50, lambda v,_g=g: v==_g),
                _Field("a_fill", cx+140, y0+100, 50, lambda v: v==self._ga()),
                _Field("p_fill", cx+220, y0+100, 50, lambda v,_p=p: v==_p),
                _Field("A", cx+200, y0+140, fw, lambda v: v==pow(g,self._ga(),p)),
                _Field("B_fill", cx+80, y0+220, 50, lambda v: v==self._B),
                _Field("a_fill2", cx+140, y0+220, 50, lambda v: v==self._ga()),
                _Field("p_fill2", cx+220, y0+220, 50, lambda v,_p=p: v==_p),
                _Field("K", cx+200, y0+260, fw, lambda v: v==pow(self._B,self._ga(),p)),
            ]
        else:
            y0 = 120
            self.fields += [
                _Field("a", cx+200, y0, fw, lambda v: 2<=v<=20, (2,20)),
                _Field("A", cx+200, y0+50, fw, lambda v: v==pow(g,self._ga(),p)),
                _Field("K", cx+200, y0+100, fw, lambda v: v==pow(self._B,self._ga(),p)),
            ]
        self.afi = 0
        if self.fields: self.fields[0].active = True
        self.phase = "play"
        self.hud.set_info(scene_name="ESCENA 04 -- SALA DE COMUNICACIONES",
                          layer_text=f"RONDA {self.round_idx+1}/3")

    def _ga(self):
        for f in self.fields:
            if f.label == "a" and f.locked: return int(f.value)
        return self._pa

    def handle_event(self, event):
        if self.dialogue.active: self.dialogue.handle_event(event); return
        if self.phase == "finished":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.back_rect.collidepoint(event.pos): self.manager.change_scene("hub")
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            p = event.pos
            if self.back_rect.collidepoint(p): self.manager.change_scene("hub"); return
            if self.calc.handle_click(p): return
            for i, f in enumerate(self.fields):
                if f.rect.collidepoint(p) and not f.locked:
                    self._setact(i)
                    if self.calc.result is not None: f.value = str(self.calc.result)
                    return
            if self.conf_rect.collidepoint(p): self._cfld(); return
            if hasattr(self, "_cfg") and self._cfg.get("mitm"):
                if self.btn_si.collidepoint(p): self.mitm_answer = "SI"
                elif self.btn_no.collidepoint(p): self.mitm_answer = "NO"
                elif self.btn_a.collidepoint(p): self.mitm_which = "A"
                elif self.btn_b.collidepoint(p): self.mitm_which = "B"
                elif self.btn_mc.collidepoint(p): self._cmitm()
        elif event.type == pygame.KEYDOWN and self.phase == "play":
            if self.afi < 0 or self.afi >= len(self.fields): return
            f = self.fields[self.afi]
            if f.locked: return
            if event.key == pygame.K_RETURN: self._cfld()
            elif event.key == pygame.K_BACKSPACE: f.value = f.value[:-1]
            elif event.key == pygame.K_TAB: self._adv()
            elif event.unicode and event.unicode in "0123456789" and len(f.value) < 8:
                f.value += event.unicode

    def _setact(self, i):
        for j, f in enumerate(self.fields): f.active = (j == i)
        self.afi = i

    def _cfld(self):
        if self.afi < 0: return
        f = self.fields[self.afi]
        if f.locked: self._adv(); return
        r = f.confirm()
        if r is True:
            self.score += 15
            if f.label == "a": self._pa = int(f.value)
            self._adv(); self._chk()
        elif r is False:
            self.score = max(0, self.score - 5)
            if self.timer_max > 0: self.timer = max(0, self.timer - 20)
            self._hint(f.label)

    def _adv(self):
        for i in range(self.afi+1, len(self.fields)):
            if not self.fields[i].locked: self._setact(i); return

    def _hint(self, label):
        _h = {"a": "Elige un numero secreto entre 2 y 20.",
              "g_fill": "El generador g esta en los parametros publicos.",
              "a_fill": "Usa tu secreto 'a' que elegiste arriba.",
              "a_fill2": "Tu secreto 'a' es el mismo de antes.",
              "p_fill": "El primo p esta en los parametros publicos.",
              "p_fill2": "El primo p no cambia, revisalo a la izquierda.",
              "B_fill": "B es el valor publico que interceptaste.",
              "A": "A = g^a mod p. Calculadora: g ^ a mod p =",
              "K": "K = B^a mod p. Calculadora: B ^ a mod p ="}
        dlg = self.manager.dialogues.get("diffie_hellman", {}).get("hints", [])
        self.nova_msg = dlg[0].get("text", _h.get(label, "Revisa.")) if dlg else _h.get(label, "Revisa.")
        self.nova_timer = 3.0

    def _chk(self):
        if all(f.locked for f in self.fields):
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
        self.score += 30
        self.round_idx += 1
        if self.round_idx >= len(_ROUNDS):
            self.phase = "finished"
            self.manager.complete_puzzle("diffie_hellman", self.score)
            ms = self.manager.dialogues.get("diffie_hellman", {}).get("success", [])
            if ms: self.dialogue.show(ms)
        else:
            self.phase = "round_done"
            self.dialogue.show(
                [{"speaker": "NOVA", "text": f"Ronda {self.round_idx} completada. "
                  f"Puntuacion: {self.score}. Preparate."}], on_complete=self._start_round)

    def update(self, dt):
        self.dialogue.update(dt)
        if self.nova_timer > 0: self.nova_timer -= dt
        if self.phase == "play" and self.timer_max > 0:
            self.timer -= dt
            if self.timer <= 0: self.timer = 0; self._fin()

    def draw(self, surface):
        surface.fill(C_BG); draw_office_floor(surface); draw_wall(surface, 50, 30)
        draw_server_rack(surface, 1180, 100, h=120)
        draw_monitor(surface, 1100, 300, text="DH-KEY", text_color=C_DH)
        self.hud.draw(surface)
        self._dleft(surface); self._dcenter(surface); self._dright(surface)
        self.calc.draw(surface)
        # Back button
        _btn(surface, self.back_rect, "< VOLVER", self.fi, C_ACCENT)
        # Nova hint bar
        if self.nova_timer > 0 and self.nova_msg:
            r = pygame.Rect(20, HEIGHT-80, WIDTH-40, 36)
            bg = pygame.Surface((r.w, r.h), pygame.SRCALPHA); bg.fill((8,10,18,220))
            surface.blit(bg, r.topleft); pygame.draw.rect(surface, C_NEON, r, 1, border_radius=3)
            pf = self.fl.render("NOVA: ", True, C_NEON); surface.blit(pf, (r.x+8, r.y+9))
            surface.blit(self.fi.render(self.nova_msg[:80], True, C_TEXT_PRI),
                         (r.x+8+pf.get_width(), r.y+10))
        self.dialogue.draw(surface)

    def _dleft(self, surface):
        r = pygame.Rect(20, 60, 300, 410); _panel(surface, r, C_DH)
        y = r.y + 8; _ctxt(surface, self.ft, "CANAL INTERCEPTADO", r.x, r.w, y, C_DH)
        y += 28; pygame.draw.line(surface, C_BORDER, (r.x+10,y), (r.x+r.w-10,y)); y += 12
        self.fl.render("g:", True, C_TEXT_SEC)
        for lb, val, xo in [("g", self._g, 20), ("p", self._p, 160)]:
            t1 = self.fl.render(f"{lb}:", True, C_TEXT_SEC)
            t2 = self.fv.render(str(val), True, C_TEXT_PRI)
            surface.blit(t1, (r.x+xo, y)); surface.blit(t2, (r.x+xo+t1.get_width()+4, y))
        y += 30
        t1 = self.fl.render("B:", True, C_TEXT_SEC)
        t2 = self.fv.render(str(self._B), True, C_AMBER)
        surface.blit(t1, (r.x+20, y)); surface.blit(t2, (r.x+20+t1.get_width()+4, y))
        y += 40
        if hasattr(self, "_cfg") and self._cfg["mitm"]:
            pygame.draw.line(surface, C_BORDER, (r.x+10,y), (r.x+r.w-10,y)); y += 10
            _ctxt(surface, self.fl, "FIRMA CipherBureau", r.x, r.w, y, C_RED); y += 22
            surface.blit(self.fv.render(f"hash(B) = {self.mitm_signed_hash}", True, C_RED),
                         (r.x+20, y)); y += 24
            surface.blit(self.fi.render("hash = sum_digitos(B) mod p", True, C_TEXT_HINT),
                         (r.x+20, y))

    def _dcenter(self, surface):
        r = pygame.Rect(340, 60, 600, 410); _panel(surface, r, C_DH)
        y = r.y+8; rn = self.round_idx+1 if self.phase != "finished" else 3
        _ctxt(surface, self.ft, f"HOJA DE CALCULO -- RONDA {rn}/3", r.x, r.w, y, C_DH)
        y += 28; pygame.draw.line(surface, C_BORDER, (r.x+10,y), (r.x+r.w-10,y))
        if self.phase in ("play", "round_done"):
            x0, y0 = r.x+20, r.y+50
            if self._cfg["guided"]:
                for yy, tx in [(y0,"Parametros publicos:"),
                    (y0+20,f"  g = {self._g}        p = {self._p}"),
                    (y0+50,"Tu secreto:"), (y0+68,"  a = "),
                    (y0+100,"Calcula tu valor publico:"), (y0+118,"  A =    ^    mod"),
                    (y0+148,"  A = "), (y0+180,f"B interceptado: B = {self._B}"),
                    (y0+210,"Calcula clave compartida:"), (y0+228,"  K =    ^    mod"),
                    (y0+268,"  K = ")]:
                    surface.blit(self.fv.render(tx, True, C_TEXT_SEC), (x0, yy))
            else:
                y1 = r.y+80
                surface.blit(self.fl.render(f"g={self._g}  p={self._p}  B={self._B}",
                             True, C_AMBER), (x0, y1))
                for tx, dy in [("a = ",40),("A = ",90),("K = ",140)]:
                    surface.blit(self.fv.render(tx, True, C_TEXT_SEC), (x0, y1+dy))
            if 0 <= self.afi < len(self.fields):
                af = self.fields[self.afi]
                if not af.locked:
                    self.conf_rect.topleft = (af.rect.right+8, af.rect.y)
                    _btn(surface, self.conf_rect, "CONFIRMAR", self.fi, C_GREEN)
        elif self.phase == "finished":
            _ctxt(surface, self.fb, "PROTOCOLO COMPLETADO", r.x, r.w, r.y+60, C_GREEN)
            _ctxt(surface, self.ft, f"Puntuacion: {self.score}", r.x, r.w, r.y+100, C_DH)
        t = pygame.time.get_ticks()
        for f in self.fields: f.draw(surface, self.ff, t)

    def _dright(self, surface):
        r = pygame.Rect(960, 60, 300, 410); _panel(surface, r, C_ACCENT)
        y = r.y+8; _ctxt(surface, self.ft, "INFORMACION", r.x, r.w, y, C_ACCENT); y += 28
        if self.timer_max > 0 and self.phase == "play":
            tc = C_RED if self.timer < 15 else C_DH
            _ctxt(surface, self.fb, f"TIEMPO: {int(self.timer)}s", r.x, r.w, y, tc)
            bw = r.w-40; ratio = max(0, self.timer/self.timer_max)
            pygame.draw.rect(surface, C_BG3, (r.x+20,y+30,bw,8), border_radius=3)
            bc = C_GREEN if ratio > .4 else (C_AMBER if ratio > .15 else C_RED)
            pygame.draw.rect(surface, bc, (r.x+20,y+30,int(bw*ratio),8), border_radius=3)
            y += 50
        t1 = self.fl.render("SCORE:", True, C_TEXT_SEC)
        t2 = self.fv.render(str(self.score), True, C_GREEN)
        surface.blit(t1, (r.x+20,y)); surface.blit(t2, (r.x+20+t1.get_width()+4,y)); y += 40
        if hasattr(self, "_cfg") and self._cfg.get("guided"):
            for ln in ["1. Elige tu secreto 'a'","2. Calcula A = g^a mod p",
                "3. Con B interceptado,","   calcula K = B^a mod p","",
                "Usa la calculadora:","  escribe X^YmodZ  ="]:
                surface.blit(self.fi.render(ln, True, C_TEXT_HINT), (r.x+15,y)); y += 16
        if hasattr(self, "_cfg") and self._cfg.get("mitm") and self.phase == "play":
            y = max(y, r.y+260)
            pygame.draw.line(surface, C_BORDER, (r.x+10,y), (r.x+r.w-10,y)); y += 8
            _ctxt(surface, self.fl, "DETECCION MITM", r.x, r.w, y, C_RED); y += 22
            surface.blit(self.fi.render("Ataque MITM?", True, C_TEXT_SEC), (r.x+15,y))
            for b, lb in [(self.btn_si,"SI"),(self.btn_no,"NO")]:
                _btn(surface, b, lb, self.fl, C_GREEN, self.mitm_answer == lb)
            surface.blit(self.fi.render("Valor manipulado:", True, C_TEXT_SEC),
                         (r.x+15, self.btn_a.y-16))
            for b, lb in [(self.btn_a,"A"),(self.btn_b,"B")]:
                _btn(surface, b, lb, self.fl, C_AMBER, self.mitm_which == lb)
            _btn(surface, self.btn_mc, "CONFIRMAR MITM", self.fl, C_RED)
