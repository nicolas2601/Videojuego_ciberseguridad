"""Scene 03 -- Oficina del Sysadmin: 3-round SHA-256 dictionary attack."""
import pygame, random, math, time
from game.constants import (WIDTH, HEIGHT, C_BG, C_BG2, C_BG3, C_BORDER,
    C_TEXT_PRI, C_TEXT_SEC, C_TEXT_HINT, C_ACCENT, C_GREEN, C_RED, C_NEON,
    C_WHITE, C_PANEL, C_HASH, C_AMBER, C_TERM_BG, C_TERM_GREEN, HINTS_CONFIG)
from game.ui.draw_assets import (draw_desk, draw_monitor, draw_filing_cabinet,
    draw_office_floor, draw_wall, draw_text_box, word_wrap)
from game.ui.dialogue import DialogueBox
from game.ui.hud import HUD
from crypto.hash_utils import sha256_short, sha256_full

_rr = lambda s, r, c, rad=6, bw=0: pygame.draw.rect(s, c, r, bw, border_radius=rad)
_AVALANCHE = ("password", "passward")


def _build_rounds(puzzle_data):
    """Build round configs from puzzle JSON data, shuffling candidate order."""
    pool = puzzle_data.get("candidate_pool", [])
    rounds = []
    for key, defs in [("round_1", dict(hlen=64, spd=0.06, tmr=0, dint=0)),
                      ("round_2", dict(hlen=8, spd=0.025, tmr=0, dint=0)),
                      ("round_3", dict(hlen=16, spd=0.012, tmr=60, dint=5))]:
        rd = puzzle_data.get(key, {})
        cands = list(rd.get("candidates", pool[:5]))
        random.shuffle(cands)
        rounds.append(dict(
            cands=cands, target=rd.get("target", cands[0]),
            hlen=rd.get("hash_length", defs["hlen"]), spd=defs["spd"],
            tmr=rd.get("timer", defs["tmr"]),
            dint=rd.get("erase_interval", defs["dint"]),
            avalanche=rd.get("show_avalanche", []),
        ))
    return rounds


class HashScene:
    """3-round progressive SHA-256 dictionary attack puzzle."""
    LX, LW = 30, 400          # Left panel
    CX, CW = 450, 380         # Center panel
    RX, RW = 850, 400         # Right panel
    HH = 44                   # HUD height

    def __init__(self, manager):
        self.manager = manager
        self.puzzle_data = manager.puzzles.get("hash", {})
        self.dial_data = manager.dialogues.get("hash", {})
        diff = getattr(manager, "difficulty", 1)
        self.hints_cfg = HINTS_CONFIG.get(diff, HINTS_CONFIG.get(1, {}))

        F = pygame.font.SysFont
        self.f_title, self.f_mono = F("monospace",16,bold=True), F("monospace",11,bold=True)
        self.f_hash, self.f_btn = F("monospace",10), F("monospace",13,bold=True)
        self.f_label, self.f_big = F("monospace",11,bold=True), F("monospace",14,bold=True)
        self.f_small, self.f_dbrf = F("monospace",10), F("monospace",14)
        self.f_dbrt = F("monospace",20,bold=True)

        # Round system
        self.rounds = _build_rounds(self.puzzle_data)
        self.current_round = 0
        self._init_round()

        self.score, self.total_wrong = 0, 0
        self.completed, self.show_debrief = False, False
        self.debrief_text = self.puzzle_data.get("debriefing",
            "SHA-256 transforma datos en huellas de tamano fijo. El efecto "
            "avalancha garantiza que un cambio minimo produce un hash "
            "completamente distinto. Las colisiones parciales demuestran por "
            "que se necesita la longitud completa del hash.")
        self.debrief_btn = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 + 110, 200, 44)

        self.hud = HUD()
        self.hud.set_info("ESCENA 03 -- OFICINA DEL SYSADMIN", "CAPA 3/4 -- SHA-256")
        self.dialogue = DialogueBox()
        enter = self.dial_data.get("enter", [])
        if enter: self.dialogue.show(enter)
        self.back_rect = pygame.Rect(20, HEIGHT - 48, 140, 36)
        self._scanlines = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for y in range(0, HEIGHT, 3):
            pygame.draw.line(self._scanlines, (0, 0, 0, 12), (0, y), (WIDTH, y))
        self._vignette = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for i in range(0, 60, 3):
            a = int((i / 60) * 30)
            pygame.draw.rect(self._vignette, (0, 0, 0, a),
                             (i, i, WIDTH - 2 * i, HEIGHT - 2 * i), 3)
        self.glow_t = 0.0
        self.cursor_t = 0.0

    # -- Round init --------------------------------------------------------
    def _init_round(self):
        rc = self.rounds[self.current_round]
        self.candidates = list(rc["cands"])
        self.target_pw = rc["target"]
        self.hash_len = rc["hlen"]
        self.type_speed = rc["spd"]
        self.round_timer = rc["tmr"]
        self.delete_interval = rc["dint"]
        self.time_left = float(rc["tmr"])
        self.delete_accum = 0.0
        self.target_hash = sha256_full(self.target_pw)[:self.hash_len]
        self.avalanche_pair = rc.get("avalanche", [])
        # State per round
        self.alive = [True] * len(self.candidates)
        self.selected = None
        self.anim_hash = ""
        self.anim_full = ""
        self.anim_shown = 0
        self.anim_timer = 0.0
        self.anim_done = False
        self.anim_result = None
        self.flash_t = 0.0
        self.expanded_hash = None
        self.show_expanded = False
        self.avalanche_clicks = set()
        self.avalanche_bonus = False
        self.round_wrong = 0
        self.round_lost = 0
        self.scroll_y = 0
        self.max_scroll = max(0, len(self.candidates) * 38 - 340)
        self.compare_rect = pygame.Rect(self.LX + 60, 520, 280, 40)
        self.expand_rect = pygame.Rect(self.RX + 20, 0, 360, 36)

    # -- Events ------------------------------------------------------------
    def handle_event(self, event):
        if self.dialogue.active:
            self.dialogue.handle_event(event)
            return
        if self.show_debrief:
            if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and self.debrief_btn.collidepoint(event.pos)):
                self.manager.complete_puzzle("hash", self.score)
                self.manager.change_scene("hub")
            return
        if self.completed:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self.back_rect.collidepoint(pos):
                self.manager.change_scene("hub"); return
            self._click_candidate(pos)
            if (self.anim_done and self.compare_rect.collidepoint(pos)
                    and self.selected is not None and self.anim_result is None):
                self._do_compare(); return
            if (self.current_round == 1 and self.anim_done
                    and self.expand_rect.collidepoint(pos)
                    and self.selected is not None):
                self.show_expanded = True
                self.expanded_hash = sha256_full(self.candidates[self.selected])
                return
        elif event.type == pygame.MOUSEWHEEL:
            self.scroll_y = max(0, min(self.max_scroll, self.scroll_y - event.y * 20))

    def _click_candidate(self, pos):
        bx, bw, bh, gap = self.CX + 10, self.CW - 20, 34, 4
        base_y = self.HH + 70 - self.scroll_y
        for i in range(len(self.candidates)):
            if not self.alive[i]:
                continue
            by = base_y + i * (bh + gap)
            if pygame.Rect(bx, by, bw, bh).collidepoint(pos):
                self._select(i); return

    def _select(self, idx):
        if not self.alive[idx]:
            return
        self.selected = idx
        word = self.candidates[idx]
        self.anim_full = sha256_full(word)[:self.hash_len]
        self.anim_hash = ""
        self.anim_shown = 0
        self.anim_timer = 0.0
        self.anim_done = False
        self.anim_result = None
        self.flash_t = 0.0
        self.show_expanded = False
        self.expanded_hash = None
        if self.current_round == 2 and word in self.avalanche_pair:
            self.avalanche_clicks.add(idx)

    def _do_compare(self):
        if self.anim_full == self.target_hash:
            self.anim_result = "match"; self.flash_t = 0.8
            pts = 30 - self.round_wrong * 10 - self.round_lost * 5
            if self.current_round == 2 and self.time_left > 0:
                pts += int(self.time_left / 3)
            if self.current_round == 2 and len(self.avalanche_clicks) >= 2:
                pts += 15; self.avalanche_bonus = True
            self.score += max(0, pts)
        else:
            self.anim_result = "nomatch"; self.flash_t = 0.6
            self.round_wrong += 1; self.total_wrong += 1
            self.score = max(0, self.score - 10)

    # -- Update ------------------------------------------------------------
    def update(self, dt):
        self.dialogue.update(dt); self.glow_t += dt; self.cursor_t += dt
        if self.completed or self.dialogue.active:
            return
        # Hash typing animation
        if self.selected is not None and not self.anim_done:
            self.anim_timer += dt
            n = min(int(self.anim_timer / self.type_speed), len(self.anim_full))
            if n > self.anim_shown:
                self.anim_shown = n
                self.anim_hash = self.anim_full[:n]
            if n >= len(self.anim_full):
                self.anim_done = True
        # Flash decay -> advance
        if self.flash_t > 0:
            self.flash_t -= dt
            if self.flash_t <= 0:
                self.flash_t = 0
                if self.anim_result == "match":
                    self._advance()
        # R3 timer + deletion
        if self.round_timer > 0 and not self.completed:
            self.time_left -= dt
            if self.time_left <= 0:
                self.time_left = 0; self.score = max(0, self.score - 15)
                self._advance(); return
            if self.delete_interval > 0:
                self.delete_accum += dt
                if self.delete_accum >= self.delete_interval:
                    self.delete_accum -= self.delete_interval
                    self._delete_candidate()

    def _delete_candidate(self):
        removable = [i for i, a in enumerate(self.alive)
                     if a and self.candidates[i] != self.target_pw
                     and i != self.selected]
        if removable:
            idx = random.choice(removable)
            self.alive[idx] = False; self.round_lost += 1

    def _advance(self):
        if self.current_round < 2:
            self.current_round += 1; self._init_round()
            hints = {
                1: "Ronda 2: Hashes truncados a 8 chars. Cuidado con colisiones parciales.",
                2: "Ronda 3: El sysadmin borra logs. Candidatos desaparecen cada 5s.",
            }
            txt = hints.get(self.current_round)
            if txt:
                self.dialogue.show([{"speaker": "NOVA", "text": txt}])
        else:
            self.completed = True
            s = self.dial_data.get("success", [])
            if s:
                self.dialogue.show(s, on_complete=self._show_debrief)
            else:
                self._show_debrief()

    def _show_debrief(self):
        self.show_debrief = True

    # -- Neon text helper --------------------------------------------------
    def _neon(self, surf, text, x, y, font, color=C_NEON):
        for o in (2, 1):
            g = font.render(text, True, color)
            gs = pygame.Surface(g.get_size(), pygame.SRCALPHA)
            gs.blit(g, (0, 0)); gs.set_alpha(35)
            surf.blit(gs, (x - o, y)); surf.blit(gs, (x + o, y))
        surf.blit(font.render(text, True, color), (x, y))

    # -- Draw entry --------------------------------------------------------
    def draw(self, surface):
        self._draw_bg(surface)
        self._draw_left(surface)
        self._draw_center(surface)
        self._draw_right(surface)
        self._draw_back(surface)
        surface.blit(self._scanlines, (0, 0))
        surface.blit(self._vignette, (0, 0))
        self.hud.draw(surface)
        self.dialogue.draw(surface)
        if self.show_debrief:
            self._draw_debrief(surface)

    def _draw_bg(self, s):
        draw_office_floor(s)
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 210)); s.blit(ov, (0, 0))
        lt = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.circle(lt, (5, 20, 5, 12), (640, 360), 300); s.blit(lt, (0, 0))
        draw_wall(s, 0, wall_h=46)
        fn = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        draw_desk(fn, 80, 620, w=120, h=50)
        draw_monitor(fn, 100, 594, text="SHA")
        draw_filing_cabinet(fn, 1220, 580); fn.set_alpha(40); s.blit(fn, (0, 0))

    # -- LEFT: target hash + computed hash + COMPARAR ----------------------
    def _draw_left(self, s):
        px, pw = self.LX, self.LW; py = self.HH + 4; cpl = 44
        bg = pygame.Surface((pw, 560), pygame.SRCALPHA); bg.fill((0, 0, 0, 210))
        s.blit(bg, (px, py)); pygame.draw.rect(s, C_BORDER, (px, py, pw, 560), 1, border_radius=4)
        self._neon(s, f"RONDA {self.current_round+1}/3", px+10, py+8, self.f_title, C_HASH)
        # Target hash
        ty = py + 36
        s.blit(self.f_label.render("HASH OBJETIVO:", True, C_TEXT_HINT), (px+10, ty)); ty += 18
        tr = pygame.Rect(px+8, ty, pw-16, 60)
        pygame.draw.rect(s, C_TERM_BG, tr); pygame.draw.rect(s, C_BORDER, tr, 1)
        for i in range(0, len(self.target_hash), cpl):
            self._neon(s, self.target_hash[i:i+cpl], px+14, ty+6+(i//cpl)*16, self.f_hash, C_TERM_GREEN)
        # Computed hash
        ty = tr.bottom + 14
        s.blit(self.f_label.render("HASH CALCULADO:", True, C_TEXT_HINT), (px+10, ty)); ty += 18
        cr = pygame.Rect(px+8, ty, pw-16, 80)
        pygame.draw.rect(s, C_TERM_BG, cr); pygame.draw.rect(s, C_BORDER, cr, 1)
        if self.selected is not None:
            w = self.candidates[self.selected]
            s.blit(self.f_label.render(f'SHA-256("{w}")', True, C_TEXT_SEC), (px+14, ty+4))
            shown = self.anim_hash
            if not self.anim_done:
                shown += "_" if int(self.cursor_t * 3) % 2 == 0 else " "
            hc = C_GREEN if self.anim_result == "match" else (
                 C_RED if self.anim_result == "nomatch" else C_TERM_GREEN)
            for i in range(0, max(1, len(shown)), cpl):
                self._neon(s, shown[i:i+cpl], px+14, ty+22+(i//cpl)*16, self.f_hash, hc)
            if not self.anim_done:
                frac = self.anim_shown / max(1, len(self.anim_full))
                bw = int((pw - 20) * frac)
                pygame.draw.rect(s, (*C_NEON, 60), (px+10, cr.bottom-6, pw-20, 4))
                pygame.draw.rect(s, C_NEON, (px+10, cr.bottom-6, bw, 4))
        else:
            draw_text_box(s, "Selecciona un candidato.", px+14, ty+20,
                          self.f_label, color=C_TEXT_SEC, bg_alpha=0, max_width=pw-30)
        # Flash overlay
        if self.flash_t > 0 and self.anim_result:
            fc = C_GREEN if self.anim_result == "match" else C_RED
            fs = pygame.Surface((pw-16, 80), pygame.SRCALPHA)
            fs.fill((*fc, int(80 * (self.flash_t / 0.8)))); s.blit(fs, (px+8, cr.y))
        # Result label
        ry = cr.bottom + 14
        if self.anim_result == "match" and self.flash_t > 0:
            self._neon(s, "COINCIDENCIA", px+80, ry, self.f_big, C_GREEN)
        elif self.anim_result == "nomatch" and self.flash_t > 0:
            self._neon(s, "NO COINCIDE", px+100, ry, self.f_big, C_RED)
        # COMPARAR button
        self.compare_rect = pygame.Rect(px+60, 520, 280, 40)
        can = self.anim_done and self.selected is not None and self.anim_result is None
        mp = pygame.mouse.get_pos(); hov = can and self.compare_rect.collidepoint(mp)
        bb = pygame.Surface((280, 40), pygame.SRCALPHA); bb.fill((0, 0, 0, 220))
        s.blit(bb, self.compare_rect.topleft)
        bc = C_NEON if hov else (C_ACCENT if can else C_BORDER)
        _rr(s, self.compare_rect, bc, 4, 2)
        tc = C_NEON if can else C_TEXT_HINT
        t = self.f_btn.render("[ COMPARAR ]", True, tc)
        s.blit(t, (self.compare_rect.centerx - t.get_width()//2,
                    self.compare_rect.centery - t.get_height()//2))
        # Stats
        sy = 562
        s.blit(self.f_label.render(f"PUNTOS: {self.score}", True, C_NEON), (px+10, sy))
        s.blit(self.f_label.render(f"FALLOS: {self.total_wrong}", True, C_RED), (px+10, sy+16))
        if self.round_timer > 0:
            sec = int(self.time_left); col = C_RED if sec < 15 else C_AMBER
            s.blit(self.f_big.render(f"TIEMPO: {sec}s", True, col), (px+10, sy+34))

    # -- CENTER: scrollable candidate list ---------------------------------
    def _draw_center(self, s):
        cx, cw = self.CX, self.CW; py = self.HH + 4; ph = 560
        bg = pygame.Surface((cw, ph), pygame.SRCALPHA); bg.fill((0, 0, 0, 190))
        s.blit(bg, (cx, py)); pygame.draw.rect(s, C_BORDER, (cx, py, cw, ph), 1, border_radius=4)
        s.blit(self.f_label.render("CANDIDATOS (diccionario)", True, C_TEXT_HINT), (cx+10, py+8))
        clip_y, clip_h = py + 26, ph - 32
        old_clip = s.get_clip(); s.set_clip((cx, clip_y, cw, clip_h))
        bx, bw, bh, gap = cx+10, cw-20, 34, 4
        base_y = clip_y + 4 - self.scroll_y; mp = pygame.mouse.get_pos()
        for i, cand in enumerate(self.candidates):
            by = base_y + i * (bh + gap)
            if by + bh < clip_y or by > clip_y + clip_h:
                continue
            alive = self.alive[i]; r = pygame.Rect(bx, by, bw, bh)
            sel = (self.selected == i); hov = alive and not self.completed and r.collidepoint(mp)
            bs = pygame.Surface((bw, bh), pygame.SRCALPHA)
            bs.fill((*C_RED, 30) if not alive else ((*C_NEON, 30) if sel else (0, 0, 0, 200)))
            s.blit(bs, r.topleft)
            if not alive:
                _rr(s, r, (80, 40, 40), 3, 1)
                s.blit(self.f_mono.render(f"[BORRADO] {cand}", True, (100, 50, 50)), (r.x+8, r.y+10))
                pygame.draw.line(s, (100, 50, 50), (r.x+8, r.centery), (r.right-8, r.centery), 1)
            else:
                bc = C_NEON if sel else (C_HASH if hov else C_BORDER)
                _rr(s, r, bc, 3, 2 if (sel or hov) else 1)
                s.blit(self.f_small.render(f"[{i+1:02d}]", True, C_TEXT_HINT), (r.x+6, r.y+11))
                s.blit(self.f_btn.render(cand, True, C_NEON if sel else C_TEXT_PRI), (r.x+42, r.y+9))
        s.set_clip(old_clip)

    # -- RIGHT: info / collision / avalanche -------------------------------
    def _draw_right(self, s):
        rx, rw = self.RX, self.RW; py = self.HH + 4
        bg = pygame.Surface((rw, 560), pygame.SRCALPHA); bg.fill((0, 0, 0, 190))
        s.blit(bg, (rx, py)); pygame.draw.rect(s, C_BORDER, (rx, py, rw, 560), 1, border_radius=4)
        [self._right_r1, self._right_r2, self._right_r3][self.current_round](s, rx, py, rw)

    def _right_r1(self, s, rx, py, rw):
        self._neon(s, "FUNDAMENTOS HASH", rx+10, py+8, self.f_title, C_ACCENT); y = py+36
        for ln in ["SHA-256 siempre produce 64 chars hex","sin importar el tamano de entrada.",
                    "","Funcion determinista:","misma entrada = mismo hash.","",
                    "Selecciona un candidato, observa","el hash y pulsa COMPARAR."]:
            s.blit(self.f_label.render(ln, True, C_TEXT_SEC), (rx+14, y)); y += 16

    def _right_r2(self, s, rx, py, rw):
        self._neon(s, "COLISIONES PARCIALES", rx+10, py+8, self.f_title, C_AMBER); y = py+36
        for ln in ["Hash truncado a 8 chars.","","Algunos candidatos coinciden en",
                    "los primeros chars pero difieren","en el hash completo.","",
                    "Usa VER HASH COMPLETO para verificar."]:
            s.blit(self.f_label.render(ln, True, C_TEXT_SEC), (rx+14, y)); y += 16
        if self.anim_done and self.selected is not None:
            self.expand_rect = pygame.Rect(rx+20, y+10, 360, 36)
            mp = pygame.mouse.get_pos(); hov = self.expand_rect.collidepoint(mp)
            bb = pygame.Surface((360, 36), pygame.SRCALPHA); bb.fill((0, 0, 0, 220))
            s.blit(bb, self.expand_rect.topleft)
            ec = C_AMBER if hov else C_ACCENT; _rr(s, self.expand_rect, ec, 4, 2)
            et = self.f_btn.render("[ VER HASH COMPLETO ]", True, ec)
            s.blit(et, (self.expand_rect.centerx - et.get_width()//2,
                        self.expand_rect.centery - et.get_height()//2))
            y = self.expand_rect.bottom + 10
            if self.show_expanded and self.expanded_hash:
                s.blit(self.f_label.render("Hash completo (64 chars):", True, C_TEXT_HINT), (rx+14, y))
                y += 18
                fr = pygame.Rect(rx+10, y, rw-20, 50)
                pygame.draw.rect(s, C_TERM_BG, fr); pygame.draw.rect(s, C_BORDER, fr, 1)
                h = self.expanded_hash
                for i in range(0, len(h), 44):
                    ch = h[i:i+44]
                    if i == 0:
                        t8 = self.f_hash.render(ch[:8], True, C_AMBER)
                        tr = self.f_hash.render(ch[8:], True, C_TERM_GREEN)
                        s.blit(t8, (rx+16, y+4)); s.blit(tr, (rx+16+t8.get_width(), y+4))
                    else:
                        s.blit(self.f_hash.render(ch, True, C_TERM_GREEN), (rx+16, y+4+(i//44)*14))
                y = fr.bottom + 8
                tf = sha256_full(self.target_pw)
                if h[:8] == tf[:8] and h != tf:
                    s.blit(self.f_big.render("COLISION PARCIAL", True, C_RED), (rx+14, y))
                    y += 18
                    s.blit(self.f_label.render("Primeros 8 chars coinciden pero", True, C_TEXT_SEC), (rx+14, y))
                    s.blit(self.f_label.render("el hash completo es DIFERENTE.", True, C_TEXT_SEC), (rx+14, y+14))

    def _right_r3(self, s, rx, py, rw):
        self._neon(s, "EFECTO AVALANCHA", rx+10, py+8, self.f_title, C_RED); y = py+36
        for ln in ["El sysadmin borra logs.","Candidatos DESAPARECEN cada 5s.",
                    "","Un cambio de 1 letra produce","un hash completamente distinto."]:
            s.blit(self.f_label.render(ln,True,C_RED if "DESAPARECEN" in ln else C_TEXT_SEC),(rx+14,y)); y+=16
        y += 8; self._neon(s, "DEMO:", rx+14, y, self.f_label, C_AMBER); y += 20
        av_a, av_b = _AVALANCHE
        ha, hb = sha256_full(av_a)[:16], sha256_full(av_b)[:16]
        self._neon(s, f'"{av_a}"', rx+14, y, self.f_mono, C_NEON); y += 16
        self._neon(s, ha, rx+14, y, self.f_hash, C_TERM_GREEN); y += 20
        self._neon(s, f'"{av_b}"', rx+14, y, self.f_mono, C_NEON); y += 16
        self._neon(s, hb, rx+14, y, self.f_hash, C_TERM_GREEN); y += 20
        diffs = sum(1 for a, b in zip(ha, hb) if a != b)
        pct = int(diffs / len(ha) * 100)
        pulse = 0.5 + 0.5 * math.sin(self.glow_t * 4)
        bar_w = rw - 40; diff_w = int(bar_w * (pct / 100))
        pygame.draw.rect(s, (*C_BORDER, 100), (rx+14, y, bar_w, 12))
        pygame.draw.rect(s, (int(200*pulse), int(60*pulse), int(60*pulse)), (rx+14, y, diff_w, 12))
        y += 18
        s.blit(self.f_label.render(f"{diffs}/{len(ha)} chars distintos ({pct}%)", True, C_RED), (rx+14, y))
        y += 20
        if self.avalanche_bonus:
            s.blit(self.f_big.render("+15 BONUS AVALANCHA", True, C_GREEN), (rx+14, y))

    # -- VOLVER button -----------------------------------------------------
    def _draw_back(self, s):
        mp = pygame.mouse.get_pos(); hov = self.back_rect.collidepoint(mp)
        bb = pygame.Surface((self.back_rect.w, self.back_rect.h), pygame.SRCALPHA)
        bb.fill((0, 0, 0, 220)); s.blit(bb, self.back_rect.topleft)
        _rr(s, self.back_rect, C_NEON if hov else C_BORDER, 4, 2)
        t = self.f_btn.render("< VOLVER", True, C_NEON if hov else C_TEXT_SEC)
        s.blit(t, (self.back_rect.centerx - t.get_width()//2,
                    self.back_rect.centery - t.get_height()//2))

    # -- Debriefing popup --------------------------------------------------
    def _draw_debrief(self, s):
        dm = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dm.fill((0, 0, 0, 200)); s.blit(dm, (0, 0))
        pw, ph = 700, 360; px = WIDTH//2 - pw//2; py = HEIGHT//2 - ph//2
        pygame.draw.rect(s, (0, 0, 0), (px, py, pw, ph))
        for o in (3, 2, 1):
            bs = pygame.Surface((pw+o*2, ph+o*2), pygame.SRCALPHA)
            pygame.draw.rect(bs, (*C_NEON, 20), bs.get_rect(), 2, border_radius=6)
            s.blit(bs, (px-o, py-o))
        pygame.draw.rect(s, C_NEON, (px, py, pw, ph), 2, border_radius=4)
        self._neon(s, "MISION COMPLETADA",
                   px + pw//2 - self.f_dbrt.size("MISION COMPLETADA")[0]//2,
                   py + 20, self.f_dbrt, C_NEON)
        sl = self.f_big.render(f"PUNTUACION FINAL: {self.score}", True, C_WHITE)
        s.blit(sl, (px + pw//2 - sl.get_width()//2, py + 56))
        pygame.draw.line(s, C_BORDER, (px+30, py+84), (px+pw-30, py+84), 1)
        dy = py + 96
        for ln in word_wrap(self.debrief_text, self.f_dbrf, pw - 60):
            s.blit(self.f_dbrf.render(ln, True, C_TEXT_PRI), (px+30, dy)); dy += 20
        hov = self.debrief_btn.collidepoint(pygame.mouse.get_pos())
        bb = pygame.Surface((self.debrief_btn.w, self.debrief_btn.h), pygame.SRCALPHA)
        bb.fill((0, 0, 0, 240)); s.blit(bb, self.debrief_btn.topleft)
        _rr(s, self.debrief_btn, C_NEON if hov else C_BORDER, 4, 2)
        bt = self.f_big.render("[ CONTINUAR ]", True, C_NEON)
        s.blit(bt, (self.debrief_btn.centerx - bt.get_width()//2,
                     self.debrief_btn.centery - bt.get_height()//2))
