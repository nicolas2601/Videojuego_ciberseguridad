import pygame, random, math, time, base64
from game.constants import (WIDTH, HEIGHT, C_BG, C_BG2, C_BG3, C_BORDER, C_TEXT_PRI,
    C_TEXT_SEC, C_TEXT_HINT, C_ACCENT, C_GREEN, C_RED, C_NEON, C_WHITE, C_PANEL,
    C_BASE64, C_AMBER, C_TERM_BG, C_TERM_GREEN, HINTS_CONFIG)
from game.ui.draw_assets import (draw_server_rack, draw_office_floor, draw_wall,
    draw_text_box, word_wrap)
from game.ui.dialogue import DialogueBox
from game.ui.hud import HUD

_B64_VALID = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
_B64_CHARS = _B64_VALID[:-1]  # 64 chars without '=' padding (backward compat)
_B64_INVALID = "#@!$%&*?{}[]<>~"
_REF_LINES = [
    "BASE64 -- TABLA DE REFERENCIA", "",
    "A-Z (0-25)  a-z (26-51)", "0-9 (52-61)  + (62)  / (63)",
    "= padding (relleno final)", "",
    *[" ".join(f"{_B64_VALID[r+j]}={r+j:<3}" for j in range(8) if r+j < 64)
      for r in range(0, 64, 8)],
    "", "4 chars Base64 = 3 bytes ASCII", "'=' rellena cuando faltan bytes",
]


def _safe_decode(s):
    try:
        return base64.b64decode(s.encode()).decode("utf-8", errors="replace")
    except Exception:
        out = ""
        for i in range(0, len(s), 4):
            b = s[i:i+4].ljust(4, "=")
            try:
                out += base64.b64decode(b.encode()).decode("utf-8", errors="replace")
            except Exception:
                out += "???"
        return out


def _scanlines(surf, a=10):
    o = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for y in range(0, HEIGHT, 3):
        pygame.draw.line(o, (0, 0, 0, a), (0, y), (WIDTH, y))
    surf.blit(o, (0, 0))


def _vignette(surf, n=30):
    v = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for i in range(n):
        a = int((i / n) * 35)
        pygame.draw.rect(v, (0, 0, 0, a), (i, i, WIDTH-2*i, HEIGHT-2*i), 3)
    surf.blit(v, (0, 0))


def _circuit_rect(surf, r, col, w=1):
    pygame.draw.rect(surf, col, r, w, border_radius=2)
    s = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
    c = (*col[:3], 80)
    for tx in range(6, r.w-6, 14):
        pygame.draw.line(s, c, (tx, 0), (tx+4, 0), 1)
        pygame.draw.line(s, c, (tx+2, r.h-1), (tx+6, r.h-1), 1)
    for ty in range(6, r.h-6, 10):
        pygame.draw.line(s, c, (0, ty), (2, ty), 1)
        pygame.draw.line(s, c, (r.w-1, ty), (r.w-3, ty), 1)
    surf.blit(s, r.topleft)


class Base64Scene:
    CS = 40           # cell size
    GX, GY = 30, 110  # grid origin
    GC = 8            # grid columns

    def __init__(self, manager):
        self.mgr = manager
        self.pz = manager.puzzles["base64"]
        self.dlg_data = manager.dialogues["base64"]
        cfg = HINTS_CONFIG[manager.difficulty]
        self.free_hints, self.visual_aids = cfg["free_hints"], cfg["visual_aids"]
        # Fonts
        self.f_cell = pygame.font.SysFont("monospace", 20, bold=True)
        self.f_lbl  = pygame.font.SysFont("monospace", 13, bold=True)
        self.f_term = pygame.font.SysFont("monospace", 16, bold=True)
        self.f_ts   = pygame.font.SysFont("monospace", 12)
        self.f_ref  = pygame.font.SysFont("monospace", 11)
        self.f_rft  = pygame.font.SysFont("monospace", 12, bold=True)
        self.f_pal  = pygame.font.SysFont("monospace", 18, bold=True)
        self.f_stat = pygame.font.SysFont("monospace", 12, bold=True)
        self.f_btn  = pygame.font.SysFont("monospace", 13, bold=True)
        self.f_dt   = pygame.font.SysFont("monospace", 18, bold=True)
        self.f_db   = pygame.font.SysFont("monospace", 14)
        self.f_dbb  = pygame.font.SysFont("monospace", 15, bold=True)
        # HUD + dialogue
        self.hud = HUD()
        self.hud.set_info("ESCENA 02 -- SALA DE SERVIDORES", "CAPA 2/4 -- BASE64")
        self.dialogue = DialogueBox()
        # State
        self.rnd = 0; self.score = 0; self.errs_fixed = 0; self.erased_n = 0
        self.completed = False; self._t = 0.0
        self.orig = []; self.disp = []; self.err_pos = []
        self.sel = -1; self.cell_r = []; self.flash = {}
        self.pal_chars = list(_B64_VALID[:-1]); self.pal_r = []; self.pal_on = False
        self.erase_tmr = 0.0; self.erased = []
        self.t0 = time.time(); self.t_el = 0.0; self.hints_used = 0
        self.hint_r = [pygame.Rect(440+i*110, HEIGHT-52, 100, 30) for i in range(3)]
        self.hints_rev = [False]*3
        self.btn_vol = pygame.Rect(20, HEIGHT-62, 130, 38)
        self.show_db = False
        self.db_r = pygame.Rect(WIDTH//2-280, HEIGHT//2-180, 560, 360)
        self.db_close = pygame.Rect(0, 0, 180, 40)
        self.db_close.centerx = self.db_r.centerx; self.db_close.y = self.db_r.bottom-60
        self.fade_a = 255; self.fade_t = 0.0; self._dbt = 0.0
        self._bg = None; self._ov = None
        self.phase = "dialogue_enter"
        self.dialogue.show(self.dlg_data["enter"], on_complete=self._enter_done)

    # -- Phase flow --------------------------------------------------------
    def _enter_done(self):
        self._start_round(0)

    def _start_round(self, ri):
        self.rnd = ri; self.sel = -1; self.pal_on = False; self.flash.clear()
        rd = self.pz[f"round_{ri+1}"]; pool = self.pz["message_pool"]
        msg = random.choice(pool); orig = msg["original"]; ne = rd["num_errors"]
        self.orig = list(orig); self.disp = list(orig)
        self.erased = [False]*len(orig); self.erase_tmr = 0.0
        repl = [i for i, c in enumerate(orig) if c != "="]
        ep = random.sample(repl, min(ne, len(repl)))
        self.err_pos = sorted(ep)
        for p in self.err_pos:
            self.disp[p] = random.choice(list(_B64_INVALID))
        self._build_cells()
        ik = f"round_{ri+1}_intro"
        if ik in self.dlg_data:
            self.phase = "dialogue_round"
            self.dialogue.show(self.dlg_data[ik], on_complete=lambda: setattr(self, 'phase', 'playing'))
        else:
            self.phase = "playing"

    def _build_cells(self):
        self.cell_r = []
        for i in range(len(self.disp)):
            c, r = i % self.GC, i // self.GC
            self.cell_r.append(pygame.Rect(
                self.GX + c*(self.CS+4), self.GY + r*(self.CS+4), self.CS, self.CS))

    def _build_pal(self):
        self.pal_r = []; pw, gap = 28, 2
        tw = len(self.pal_chars)*(pw+gap)-gap
        sx = max(20, (WIDTH-tw)//2)
        for i in range(len(self.pal_chars)):
            self.pal_r.append(pygame.Rect(sx+i*(pw+gap), 570, pw, 36))

    def _round_done(self):
        for p in self.err_pos:
            if not self.erased[p] and self.disp[p] != self.orig[p]:
                return False
        return True

    def _advance(self):
        self.score += 20
        if self.rnd + 1 >= 3:
            self.completed = True; self.phase = "dialogue_success"
            self.dialogue.show(self.dlg_data["success"], on_complete=self._suc_done)
        else:
            self._start_round(self.rnd + 1)

    def _suc_done(self):
        self.show_db = True; self.phase = "debrief"

    # -- Events ------------------------------------------------------------
    def handle_event(self, ev):
        if self.dialogue.active:
            self.dialogue.handle_event(ev); return
        if self.show_db:
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if self.db_close.collidepoint(ev.pos):
                    self.mgr.complete_puzzle("base64", max(0, self.score))
                    self.mgr.change_scene("hub")
            return
        if ev.type != pygame.MOUSEBUTTONDOWN or ev.button != 1:
            return
        mx, my = ev.pos
        if self.btn_vol.collidepoint(ev.pos):
            self.mgr.change_scene("hub"); return
        for i, hr in enumerate(self.hint_r):
            if hr.collidepoint(ev.pos) and not self.hints_rev[i]:
                hd = self.dlg_data.get("hints", {}); hk = f"hint_{i+1}"
                if hk in hd:
                    h = hd[hk]; self.hints_rev[i] = True; self.hints_used += 1
                    if "pts" in h.get("cost", ""):
                        self.score -= 30
                    self.dialogue.show([{"speaker": h["source"], "text": h["text"]}])
                return
        if self.phase != "playing":
            return
        if self.pal_on and self.sel >= 0:
            for i, pr in enumerate(self.pal_r):
                if pr.collidepoint(ev.pos):
                    self._replace(self.sel, self.pal_chars[i]); return
        for i, cr in enumerate(self.cell_r):
            if cr.collidepoint(ev.pos) and not self.erased[i]:
                self.sel = i; self.pal_on = True; self._build_pal(); return

    def _replace(self, idx, ch):
        self.disp[idx] = ch
        if ch == self.orig[idx]:
            self.flash[idx] = (0.5, C_GREEN); self.errs_fixed += 1; self.score += 25
            if self._round_done():
                self.sel = -1; self.pal_on = False; self._advance(); return
        elif ch not in _B64_VALID:
            self.flash[idx] = (0.5, C_RED)
        else:
            self.flash[idx] = (0.5, C_AMBER)
        self.sel = -1; self.pal_on = False

    # -- Update ------------------------------------------------------------
    def update(self, dt):
        self._t += dt; self.dialogue.update(dt)
        if self.fade_a > 0:
            self.fade_t += dt; self.fade_a = max(0, 255 - int(self.fade_t * 400))
        exp = [k for k, (t, _) in self.flash.items() if t - dt <= 0]
        for k in exp: del self.flash[k]
        for k in list(self.flash):
            t, c = self.flash[k]; self.flash[k] = (t - dt, c)
        if self.phase == "playing":
            self.t_el = time.time() - self.t0
        if self.phase == "playing" and self.rnd == 2:
            self.erase_tmr += dt
            if self.erase_tmr >= 3.0:
                self.erase_tmr -= 3.0; self._erase_one()
        if self.show_db:
            self._dbt += dt

    def _erase_one(self):
        for i in range(len(self.disp)-1, -1, -1):
            if not self.erased[i]:
                self.erased[i] = True; self.erased_n += 1; self.score -= 15
                if self._round_done():
                    self.sel = -1; self.pal_on = False; self._advance()
                elif all(self.erased):
                    self._advance()
                return

    # -- Draw --------------------------------------------------------------
    def draw(self, surface):
        if not self._bg:
            self._bg = pygame.Surface((WIDTH, HEIGHT))
            draw_office_floor(self._bg); draw_wall(self._bg, 0, wall_h=50)
            for x in (10, 60, 1160, 1210):
                draw_server_rack(self._bg, x, 60, h=360)
        if not self._ov:
            self._ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            _scanlines(self._ov); _vignette(self._ov)
        surface.blit(self._bg, (0, 0))
        t = self._t
        self._draw_grid(surface, t)
        self._draw_decode(surface, t)
        if self.rnd < 2:
            self._draw_ref(surface, t)
        self._draw_bottom(surface, t)
        if self.pal_on:
            self._draw_pal(surface)
        surface.blit(self._ov, (0, 0))
        self.hud.draw(surface); self.dialogue.draw(surface)
        if self.show_db:
            self._draw_debrief(surface)
        if self.fade_a > 0:
            f = pygame.Surface((WIDTH, HEIGHT)); f.fill((0, 0, 0))
            f.set_alpha(self.fade_a); surface.blit(f, (0, 0))

    def _draw_grid(self, s, t):
        nh = max(200, (len(self.disp)//self.GC+2)*(self.CS+4)+20)
        pr = pygame.Rect(self.GX-10, self.GY-30, self.GC*(self.CS+4)+16, nh)
        ps = pygame.Surface((pr.w, pr.h), pygame.SRCALPHA); ps.fill((12,14,22,200))
        s.blit(ps, pr.topleft); _circuit_rect(s, pr, C_BASE64)
        lb = self.f_lbl.render(f"TRANSMISION CORRUPTA  [RONDA {self.rnd+1}/3]", True, C_BASE64)
        s.blit(lb, (self.GX-4, self.GY-24))
        if not self.disp:
            return
        eh = self.pz.get(f"round_{self.rnd+1}", {}).get("errors_highlighted", False)
        mx, my = pygame.mouse.get_pos()
        for i, cr in enumerate(self.cell_r):
            if self.erased[i]:
                es = pygame.Surface((self.CS, self.CS), pygame.SRCALPHA)
                for _ in range(10):
                    es.fill((0,0,0,0))
                    nx, ny = random.randint(2, self.CS-3), random.randint(2, self.CS-3)
                    pygame.draw.rect(es, (100,100,100, random.randint(20,60)), (nx,ny,3,2))
                s.blit(es, cr.topleft)
                pygame.draw.rect(s, (40,40,50), cr, 1, border_radius=2); continue
            ch = self.disp[i]; ie = i in self.err_pos
            sw = ie and ch != self.orig[i]; sel = i == self.sel
            fc = self.flash.get(i, (0, None))[1]
            cs = pygame.Surface((self.CS, self.CS), pygame.SRCALPHA)
            if sel: cs.fill((40,60,100,220))
            elif fc: cs.fill((*fc[:3], 60))
            else: cs.fill((16,20,30,200))
            s.blit(cs, cr.topleft)
            bc = C_WHITE if sel else (fc if fc else (C_RED if eh and sw else (50,60,80)))
            bw = 2 if sel or fc or (eh and sw) else 1
            pygame.draw.rect(s, bc, cr, bw, border_radius=2)
            if cr.collidepoint(mx, my) and not sel:
                hs = pygame.Surface((self.CS, self.CS), pygame.SRCALPHA)
                hs.fill((80,120,200,30)); s.blit(hs, cr.topleft)
            tc = C_RED if eh and sw else (C_GREEN if ie and not sw else C_TEXT_PRI)
            ct = self.f_cell.render(ch, True, tc)
            s.blit(ct, (cr.x+(self.CS-ct.get_width())//2, cr.y+(self.CS-ct.get_height())//2))

    def _draw_decode(self, s, t):
        dr = pygame.Rect(430, 110, 400, 300)
        ps = pygame.Surface((dr.w, dr.h), pygame.SRCALPHA); ps.fill((*C_TERM_BG, 230))
        for sy in range(0, dr.h, 3):
            pygame.draw.line(ps, (0,0,0,8), (0,sy), (dr.w,sy))
        s.blit(ps, dr.topleft); _circuit_rect(s, dr, C_TERM_GREEN)
        tb = pygame.Surface((dr.w, 22), pygame.SRCALPHA); tb.fill((20,30,20,180))
        s.blit(tb, (dr.x, dr.y))
        s.blit(self.f_lbl.render("DECODIFICACION BASE64", True, C_TERM_GREEN), (dr.x+8, dr.y+4))
        if int(t*2)%2 == 0:
            pygame.draw.rect(s, C_TERM_GREEN, (dr.x+dr.w-20, dr.y+6, 8, 12))
        if not self.disp:
            return
        cs = "".join(self.disp); dec = _safe_decode(cs); y = dr.y+30
        s.blit(self.f_ts.render("INPUT:", True, (100,140,100)), (dr.x+10, y)); y += 18
        for ci in range(0, len(cs), 28):
            s.blit(self.f_ts.render(cs[ci:ci+28], True, C_TERM_GREEN), (dr.x+10, y)); y += 16
        y += 10
        pygame.draw.line(s, (40,80,40), (dr.x+10,y), (dr.x+dr.w-10,y)); y += 10
        s.blit(self.f_ts.render("OUTPUT:", True, (100,140,100)), (dr.x+10, y)); y += 20
        for ci in range(0, len(dec), 24):
            cx = dr.x+10
            for c in dec[ci:ci+24]:
                if c in ("\ufffd", "?"):
                    col, c = C_RED, "?"
                else:
                    col = C_TERM_GREEN
                cs2 = self.f_term.render(c, True, col); s.blit(cs2, (cx, y)); cx += cs2.get_width()
            y += 20
        y += 10
        rem = sum(1 for p in self.err_pos if not self.erased[p] and self.disp[p] != self.orig[p])
        sc = C_GREEN if rem == 0 else C_AMBER
        s.blit(self.f_ts.render(f"Errores restantes: {rem}", True, sc), (dr.x+10, y))

    def _draw_ref(self, s, t):
        rr = pygame.Rect(850, 110, 400, 300)
        ps = pygame.Surface((rr.w, rr.h), pygame.SRCALPHA); ps.fill((14,18,28,210))
        s.blit(ps, rr.topleft); _circuit_rect(s, rr, C_ACCENT)
        y = rr.y+8
        for i, ln in enumerate(_REF_LINES):
            if y > rr.y+rr.h-14: break
            f = self.f_rft if i == 0 else self.f_ref
            s.blit(f.render(ln, True, C_ACCENT if i == 0 else C_TEXT_SEC), (rr.x+8, y))
            y += f.get_linesize()+1

    def _draw_bottom(self, s, t):
        st = f"Corregidos: {self.errs_fixed}   Borrados: {self.erased_n}   Puntos: {self.score}"
        s.blit(self.f_stat.render(st, True, C_TEXT_SEC), (180, HEIGHT-30))
        self._nbtn(s, self.btn_vol, "VOLVER", C_ACCENT)
        hd = self.dlg_data.get("hints", {})
        for i, hr in enumerate(self.hint_r):
            hk = f"hint_{i+1}"
            if hk not in hd: continue
            h = hd[hk]; lbl = f"PISTA {i+1}"
            if self.hints_rev[i]: col = C_TEXT_HINT
            elif h.get("cost","") == "free": col = C_GREEN
            else: col = C_AMBER
            self._nbtn(s, hr, lbl, col, dis=self.hints_rev[i])
        if self.phase == "playing" and self.rnd == 2:
            bx, by, bw, bh = self.GX-10, HEIGHT-100, 350, 10
            prog = self.erase_tmr/3.0; dc = C_RED if prog > 0.7 else C_AMBER
            pygame.draw.rect(s, (30,30,40), (bx,by,bw,bh), border_radius=4)
            fw = int(bw*prog)
            if fw > 0:
                pygame.draw.rect(s, dc, (bx,by,fw,bh), border_radius=4)
            s.blit(self.f_stat.render("BORRADO EN CURSO", True, dc), (bx, by-16))

    def _draw_pal(self, s):
        if not self.pal_r: return
        pw = self.pal_r[-1].right - self.pal_r[0].x + 20
        px = self.pal_r[0].x-10
        ps = pygame.Surface((pw, 52), pygame.SRCALPHA); ps.fill((16,20,32,230))
        s.blit(ps, (px, 562))
        pygame.draw.rect(s, C_BASE64, (px, 562, pw, 52), 1, border_radius=3)
        s.blit(self.f_stat.render("Seleccionar reemplazo:", True, C_TEXT_SEC), (px+4, 550))
        mx, my = pygame.mouse.get_pos()
        for i, pr in enumerate(self.pal_r):
            h = pr.collidepoint(mx, my)
            cs = pygame.Surface((pr.w, pr.h), pygame.SRCALPHA)
            cs.fill((60,80,140,180) if h else (20,24,36,180))
            s.blit(cs, pr.topleft)
            pygame.draw.rect(s, C_WHITE if h else (50,60,80), pr, 1, border_radius=2)
            ct = self.f_pal.render(self.pal_chars[i], True, C_WHITE if h else C_BASE64)
            s.blit(ct, (pr.x+(pr.w-ct.get_width())//2, pr.y+(pr.h-ct.get_height())//2))

    def _draw_debrief(self, s):
        dm = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); dm.fill((0,0,0,160))
        s.blit(dm, (0,0))
        dr = self.db_r; ps = pygame.Surface((dr.w, dr.h), pygame.SRCALPHA)
        ps.fill((14,18,28,240)); s.blit(ps, dr.topleft)
        p = int(140+60*math.sin(self._dbt*2))
        pygame.draw.rect(s, (*C_BASE64[:3], p), dr, 2, border_radius=4)
        tt = self.f_dt.render("MISION COMPLETADA", True, C_BASE64)
        s.blit(tt, (dr.centerx-tt.get_width()//2, dr.y+20))
        y = dr.y+60
        for ln in [f"Errores corregidos: {self.errs_fixed}",
                    f"Caracteres borrados: {self.erased_n}",
                    f"Pistas usadas: {self.hints_used}",
                    f"Puntuacion final: {max(0, self.score)}"]:
            s.blit(self.f_db.render(ln, True, C_TEXT_PRI), (dr.x+40, y)); y += 24
        y += 10
        for ln in ["Base64 codifica 3 bytes en 4 chars ASCII.",
                    "NO es cifrado: cualquiera puede decodificarlo.",
                    "Codificacion != Seguridad."]:
            s.blit(self.f_db.render(ln, True, C_TEXT_SEC), (dr.x+40, y)); y += 22
        self._nbtn(s, self.db_close, "VOLVER AL HUB", C_BASE64)

    def _nbtn(self, s, r, txt, col, dis=False):
        mx, my = pygame.mouse.get_pos(); h = r.collidepoint(mx, my) and not dis
        bs = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
        bs.fill((20,22,30,140) if dis else ((*col[:3], 50) if h else (16,20,30,200)))
        s.blit(bs, r.topleft)
        bc = col if not dis else C_TEXT_HINT; bw = 2 if h else 1
        pygame.draw.rect(s, bc, r, bw, border_radius=4)
        tc = C_WHITE if h else bc
        ts = self.f_btn.render(txt, True, tc)
        s.blit(ts, (r.centerx-ts.get_width()//2, r.centery-ts.get_height()//2))
