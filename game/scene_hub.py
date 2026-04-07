import pygame
import random
import math
from game.constants import (WIDTH, HEIGHT, C_BG, C_BG2, C_BG3, C_BORDER, C_TEXT_PRI,
    C_TEXT_SEC, C_ACCENT, C_GREEN, C_NEON, C_WHITE, C_PANEL, C_AMBER,
    PLAYER_SPEED, PLAYER_SIZE, PUZZLE_SCENES)
from game.ui.draw_assets import (draw_player, draw_desk, draw_monitor, draw_chair,
    draw_plant, draw_filing_cabinet, draw_server_rack, draw_door, draw_whiteboard,
    draw_office_floor, draw_wall, draw_interact_prompt, draw_text_box)
from game.ui.dialogue import DialogueBox
from game.ui.hud import HUD


# ── Safe wrappers for optional draw functions ────────────────────
def _safe_call(fn_name, *args, **kwargs):
    """Call a draw_assets function if it exists, otherwise skip."""
    from game.ui import draw_assets
    fn = getattr(draw_assets, fn_name, None)
    if fn:
        fn(*args, **kwargs)


# ── Door definitions ─────────────────────────────────────────────
_DOORS = [
    {"key": "caesar",         "x": 60,   "y": 80,  "color": PUZZLE_SCENES["caesar"]["color"],
     "label": "CESAR"},
    {"key": "base64",         "x": 1172, "y": 80,  "color": PUZZLE_SCENES["base64"]["color"],
     "label": "BASE64"},
    {"key": "hash",           "x": 60,   "y": 580, "color": PUZZLE_SCENES["hash"]["color"],
     "label": "HASH"},
    {"key": "diffie_hellman", "x": 1172, "y": 580, "color": PUZZLE_SCENES["diffie_hellman"]["color"],
     "label": "D-H"},
]

_EXIT_DOOR = {"x": 616, "y": 48, "color": C_GREEN, "label": "SALIDA — INFORME FINAL"}

_DOOR_W = 48
_DOOR_H = 64
_INTERACT_DIST = 60
_WALL_Y = 0
_WALL_H = 44


# ── Particle class ───────────────────────────────────────────────
class _Particle:
    __slots__ = ("x", "y", "vx", "vy", "alpha", "size", "life", "max_life")

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = random.uniform(-6, 6)
        self.vy = random.uniform(-12, -3)
        self.size = random.uniform(1.0, 2.5)
        self.max_life = random.uniform(3.0, 7.0)
        self.life = self.max_life
        self.alpha = random.randint(40, 100)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        self.alpha = max(0, int((self.life / self.max_life) * 80))

    @property
    def alive(self):
        return self.life > 0


# ── Light pool positions ─────────────────────────────────────────
_LIGHT_POOLS = [
    (320, 260, 90),   # workstation 1
    (910, 260, 90),   # workstation 2
    (320, 500, 90),   # workstation 3
    (910, 500, 90),   # workstation 4
    (640, 360, 110),  # center of room
    (620, 180, 70),   # near servers
]


class HubScene:
    def __init__(self, manager):
        self.manager = manager

        # Player state -- center of room
        self.px = float(WIDTH // 2 - PLAYER_SIZE // 2)
        self.py = float(HEIGHT // 2 - PLAYER_SIZE // 2)
        self.direction = "down"

        # Movement keys held
        self.keys_held = {pygame.K_w: False, pygame.K_a: False,
                          pygame.K_s: False, pygame.K_d: False}

        # HUD
        self.hud = HUD()
        self._update_hud()

        # Dialogue
        self.dialogue = DialogueBox()
        self._show_initial_dialogue()

        # Timers for ambient effects
        self.time = 0.0
        self.glitch_timer = 0.0
        self.glitch_active = False
        self.glitch_y = 0
        self.next_glitch = random.uniform(3.0, 8.0)

        # Monitor flicker state (per workstation)
        self.monitor_flicker = [0.0, 0.0, 0.0, 0.0]
        self.monitor_flicker_next = [random.uniform(2, 6) for _ in range(4)]

        # Server LED blink timers
        self.led_timer = 0.0

        # Particles (dust / data motes)
        self.particles = []
        for _ in range(30):
            p = _Particle(random.uniform(40, WIDTH - 40),
                          random.uniform(60, HEIGHT - 40))
            p.life = random.uniform(0, p.max_life)
            self.particles.append(p)
        self.particle_spawn_timer = 0.0

        # Pre-render static floor surface
        self.floor_surf = pygame.Surface((WIDTH, HEIGHT))
        self._render_floor()

        # Pre-render scanlines overlay
        self.scanline_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self._render_scanlines()

        # Pre-render vignette overlay
        self.vignette_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self._render_vignette()

        # Build collision rects for furniture and walls
        self.furniture = self._build_furniture()
        self.wall_rects = self._build_walls()
        self.collision_rects = self.wall_rects + [r for r, _ in self.furniture]

        # Build door rects for collision and interaction
        self.door_rects = []
        for d in _DOORS:
            dr = pygame.Rect(d["x"] - 2, d["y"] - 2, _DOOR_W + 4, _DOOR_H + 4)
            self.door_rects.append((dr, d["key"]))
            self.collision_rects.append(dr)

        # Exit door rect
        self.exit_rect = pygame.Rect(
            _EXIT_DOOR["x"] - 2, _EXIT_DOOR["y"] - 2,
            _DOOR_W + 4, _DOOR_H + 4
        )

        # Nearby door for interaction prompt
        self.nearby_door = None

    # ── Static surface rendering ─────────────────────────────────

    def _render_floor(self):
        """Dark industrial floor with metallic tile grid."""
        self.floor_surf.fill(C_BG)
        tile = 48
        for tx in range(0, WIDTH, tile):
            for ty in range(0, HEIGHT, tile):
                # Alternating metallic tiles
                checker = (tx // tile + ty // tile) % 2
                if checker == 0:
                    c = (35, 40, 50)
                else:
                    c = (28, 32, 42)
                pygame.draw.rect(self.floor_surf, c, (tx, ty, tile, tile))
                # Subtle grid lines
                pygame.draw.rect(self.floor_surf, (45, 50, 62), (tx, ty, tile, tile), 1)
                # Tiny corner rivets
                rivet = (28, 32, 44)
                for cx, cy in [(tx + 2, ty + 2), (tx + tile - 3, ty + 2),
                               (tx + 2, ty + tile - 3), (tx + tile - 3, ty + tile - 3)]:
                    pygame.draw.rect(self.floor_surf, rivet, (cx, cy, 2, 2))

    def _render_scanlines(self):
        """CRT scanlines overlay -- subtle horizontal lines."""
        for y in range(0, HEIGHT, 2):
            pygame.draw.line(self.scanline_surf, (0, 0, 0, 10), (0, y), (WIDTH, y))

    def _render_vignette(self):
        """Dark vignette on screen edges."""
        # Draw radial gradient approximation with concentric rectangles
        cx, cy = WIDTH // 2, HEIGHT // 2
        max_dist = math.hypot(cx, cy)
        # Light vignette - only very edges
        for i in range(20):
            t = i / 20.0
            alpha = int(30 * (1.0 - t) ** 2)
            if alpha <= 0:
                continue
            margin = int(t * min(cx, cy) * 0.6)
            rect = pygame.Rect(margin, margin, WIDTH - margin * 2, HEIGHT - margin * 2)
            if rect.w > 0 and rect.h > 0:
                border_surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
                pygame.draw.rect(border_surf, (0, 0, 0, alpha), (0, 0, rect.w, rect.h), max(2, 6 - i))
                self.vignette_surf.blit(border_surf, (rect.x, rect.y))

    # ── Furniture layout ─────────────────────────────────────────

    def _build_furniture(self):
        """Return list of (pygame.Rect, tag_string) for all furniture."""
        items = []

        # -- 4 Workstations (desk + monitor + chair each) --
        # Top-left workstation
        items.append((pygame.Rect(270, 200, 96, 50), "desk_0"))
        items.append((pygame.Rect(292, 194, 40, 42), "monitor_0"))
        items.append((pygame.Rect(284, 258, 28, 30), "chair_0"))

        # Top-right workstation
        items.append((pygame.Rect(880, 200, 96, 50), "desk_1"))
        items.append((pygame.Rect(902, 194, 40, 42), "monitor_1"))
        items.append((pygame.Rect(894, 258, 28, 30), "chair_1"))

        # Bottom-left workstation
        items.append((pygame.Rect(270, 440, 96, 50), "desk_2"))
        items.append((pygame.Rect(292, 434, 40, 42), "monitor_2"))
        items.append((pygame.Rect(284, 498, 28, 30), "chair_2"))

        # Bottom-right workstation
        items.append((pygame.Rect(880, 440, 96, 50), "desk_3"))
        items.append((pygame.Rect(902, 434, 40, 42), "monitor_3"))
        items.append((pygame.Rect(894, 498, 28, 30), "chair_3"))

        # -- Filing cabinets along walls --
        items.append((pygame.Rect(200, 58, 32, 56), "cabinet_0"))
        items.append((pygame.Rect(1050, 58, 32, 56), "cabinet_1"))
        items.append((pygame.Rect(200, 620, 32, 56), "cabinet_2"))
        items.append((pygame.Rect(1050, 620, 32, 56), "cabinet_3"))
        items.append((pygame.Rect(500, 620, 32, 56), "cabinet_4"))
        items.append((pygame.Rect(750, 620, 32, 56), "cabinet_5"))

        # -- Plants in corners --
        items.append((pygame.Rect(30, 130, 28, 30), "plant_0"))
        items.append((pygame.Rect(1222, 130, 28, 30), "plant_1"))
        items.append((pygame.Rect(30, 570, 28, 30), "plant_2"))
        items.append((pygame.Rect(1222, 570, 28, 30), "plant_3"))

        # -- Server racks near doors --
        items.append((pygame.Rect(570, 120, 32, 80), "server_0"))
        items.append((pygame.Rect(610, 120, 32, 80), "server_1"))
        items.append((pygame.Rect(650, 120, 32, 80), "server_2"))

        # -- Whiteboards on wall --
        items.append((pygame.Rect(380, 50, 70, 38), "wb_0"))
        items.append((pygame.Rect(830, 50, 70, 38), "wb_1"))

        return items

    def _build_walls(self):
        """Boundary walls the player cannot cross."""
        t = 10
        return [
            pygame.Rect(0, 0, WIDTH, _WALL_H + t),
            pygame.Rect(0, 0, t, HEIGHT),
            pygame.Rect(WIDTH - t, 0, t, HEIGHT),
            pygame.Rect(0, HEIGHT - t, WIDTH, t),
        ]

    # ── Dialogue ─────────────────────────────────────────────────

    def _show_initial_dialogue(self):
        count = len(self.manager.completed_scenes
                     & {"caesar", "base64", "hash", "diffie_hellman"})
        hub_dialogues = self.manager.dialogues.get("hub", {})
        if count == 0:
            key = "enter"
        elif count < 4:
            key = f"progress_{count}"
        else:
            key = "all_done"
        msgs = hub_dialogues.get(key, hub_dialogues.get("enter", []))
        if msgs:
            self.dialogue.show(msgs)

    # ── HUD ──────────────────────────────────────────────────────

    def _update_hud(self):
        completed = len(self.manager.completed_scenes
                        & {"caesar", "base64", "hash", "diffie_hellman"})
        self.hud.set_info(
            scene_name="SEDE PRINCIPAL",
            layer_text=f"SALAS: {completed}/4"
        )

    # ── Events ───────────────────────────────────────────────────

    def handle_event(self, event):
        if self.dialogue.active:
            self.dialogue.handle_event(event)
            return

        if event.type == pygame.KEYDOWN:
            if event.key in self.keys_held:
                self.keys_held[event.key] = True
            if event.key == pygame.K_e and self.nearby_door is not None:
                self.manager.change_scene(self.nearby_door)

        elif event.type == pygame.KEYUP:
            if event.key in self.keys_held:
                self.keys_held[event.key] = False

    # ── Update ───────────────────────────────────────────────────

    def update(self, dt):
        self.time += dt
        self.dialogue.update(dt)
        self._update_hud()

        # -- Ambient timers --
        self._update_particles(dt)
        self._update_glitch(dt)
        self._update_monitor_flicker(dt)
        self.led_timer += dt

        if self.dialogue.active:
            return

        # -- Player movement --
        dx, dy = 0.0, 0.0
        if self.keys_held[pygame.K_w]:
            dy -= PLAYER_SPEED * dt
        if self.keys_held[pygame.K_s]:
            dy += PLAYER_SPEED * dt
        if self.keys_held[pygame.K_a]:
            dx -= PLAYER_SPEED * dt
        if self.keys_held[pygame.K_d]:
            dx += PLAYER_SPEED * dt

        # Normalize diagonal movement
        if dx != 0 and dy != 0:
            inv_sqrt2 = 0.7071
            dx *= inv_sqrt2
            dy *= inv_sqrt2

        # Update facing direction
        if abs(dy) > abs(dx):
            self.direction = "up" if dy < 0 else "down"
        elif dx != 0:
            self.direction = "left" if dx < 0 else "right"

        # Apply movement with per-axis collision
        player_rect = pygame.Rect(int(self.px), int(self.py), PLAYER_SIZE, PLAYER_SIZE)

        if dx != 0:
            new_rect = player_rect.move(int(dx), 0)
            if not self._collides(new_rect):
                self.px += dx
                player_rect.x = int(self.px)

        if dy != 0:
            new_rect = player_rect.move(0, int(dy))
            if not self._collides(new_rect):
                self.py += dy
                player_rect.y = int(self.py)

        # Clamp to room boundaries
        self.px = max(12, min(WIDTH - PLAYER_SIZE - 12, self.px))
        self.py = max(_WALL_H + 12, min(HEIGHT - PLAYER_SIZE - 12, self.py))

        # -- Check nearby doors --
        self.nearby_door = None
        pcx = self.px + PLAYER_SIZE / 2
        pcy = self.py + PLAYER_SIZE / 2

        for d in _DOORS:
            dcx = d["x"] + _DOOR_W / 2
            dcy = d["y"] + _DOOR_H / 2
            dist = math.hypot(pcx - dcx, pcy - dcy)
            if dist < _INTERACT_DIST:
                self.nearby_door = d["key"]
                break

        if self.nearby_door is None and self.manager.all_puzzles_complete():
            dcx = _EXIT_DOOR["x"] + _DOOR_W / 2
            dcy = _EXIT_DOOR["y"] + _DOOR_H / 2
            dist = math.hypot(pcx - dcx, pcy - dcy)
            if dist < _INTERACT_DIST:
                self.nearby_door = "ending"

    def _update_particles(self, dt):
        """Update floating dust/data motes."""
        self.particle_spawn_timer += dt
        # Spawn new particles near light pools
        if self.particle_spawn_timer > 0.15:
            self.particle_spawn_timer = 0.0
            if len(self.particles) < 50:
                pool = random.choice(_LIGHT_POOLS)
                px = pool[0] + random.uniform(-pool[2], pool[2])
                py = pool[1] + random.uniform(-pool[2] * 0.5, pool[2] * 0.5)
                self.particles.append(_Particle(px, py))

        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.alive]

    def _update_glitch(self, dt):
        """Occasional horizontal glitch line across screen."""
        self.glitch_timer += dt
        if not self.glitch_active and self.glitch_timer > self.next_glitch:
            self.glitch_active = True
            self.glitch_timer = 0.0
            self.glitch_y = random.randint(50, HEIGHT - 50)
        if self.glitch_active and self.glitch_timer > 0.08:
            self.glitch_active = False
            self.glitch_timer = 0.0
            self.next_glitch = random.uniform(4.0, 10.0)

    def _update_monitor_flicker(self, dt):
        """Track per-monitor flicker cooldowns."""
        for i in range(4):
            if self.monitor_flicker[i] > 0:
                self.monitor_flicker[i] -= dt
            else:
                self.monitor_flicker_next[i] -= dt
                if self.monitor_flicker_next[i] <= 0:
                    self.monitor_flicker[i] = random.uniform(0.04, 0.12)
                    self.monitor_flicker_next[i] = random.uniform(2.0, 7.0)

    def _collides(self, rect):
        for cr in self.collision_rects:
            if rect.colliderect(cr):
                return True
        return False

    # ── Draw ─────────────────────────────────────────────────────

    def draw(self, surface):
        # 1. Floor
        surface.blit(self.floor_surf, (0, 0))

        # 2. Light pools on floor (atmospheric overhead lights)
        self._draw_light_pools(surface)

        # 3. Wall with conduit details
        self._draw_wall(surface)

        # 4. Furniture shadows
        self._draw_furniture_shadows(surface)

        # 5. Furniture
        self._draw_furniture(surface)

        # 6. Doors with glow effects
        self._draw_doors(surface)

        # 7. Exit door
        if self.manager.all_puzzles_complete():
            self._draw_exit_door(surface)

        # 8. Particles (dust motes in light)
        self._draw_particles(surface)

        # 9. Player
        draw_player(surface, int(self.px), int(self.py), self.direction)

        # 10. Interaction prompt with bouncing [E]
        if self.nearby_door is not None:
            self._draw_interaction(surface)

        # 11. Glitch line
        if self.glitch_active:
            self._draw_glitch(surface)

        # 12. CRT scanlines overlay
        surface.blit(self.scanline_surf, (0, 0))

        # 13. Vignette
        surface.blit(self.vignette_surf, (0, 0))

        # 14. HUD
        self.hud.draw(surface)

        # 15. Dialogue on top of everything
        self.dialogue.draw(surface)

    # ── Draw sub-methods ─────────────────────────────────────────

    def _draw_light_pools(self, surface):
        """Bright elliptical pools of light from overhead fixtures."""
        light_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for lx, ly, lr in _LIGHT_POOLS:
            # Outer glow
            for ring in range(5, 0, -1):
                r = lr + ring * 12
                alpha = max(2, 8 - ring * 1)
                color = (45, 50, 60, alpha)
                pygame.draw.ellipse(light_surf, color,
                                    (lx - r, ly - r // 2, r * 2, r))
            # Inner bright spot
            pygame.draw.ellipse(light_surf, (50, 55, 65, 12),
                                (lx - lr // 2, ly - lr // 4, lr, lr // 2))
        surface.blit(light_surf, (0, 0))

    def _draw_wall(self, surface):
        """Top wall with conduit details."""
        wall_h = _WALL_H
        # Main wall
        wall_color = (18, 20, 28)
        pygame.draw.rect(surface, wall_color, (0, 0, WIDTH, wall_h))

        # Conduit pipes running horizontally
        pipe_color = (30, 34, 46)
        pipe_highlight = (38, 42, 56)
        for py_offset in [12, 26]:
            pygame.draw.line(surface, pipe_color, (0, py_offset), (WIDTH, py_offset), 3)
            pygame.draw.line(surface, pipe_highlight, (0, py_offset - 1), (WIDTH, py_offset - 1), 1)

        # Vertical conduit segments
        for vx in range(80, WIDTH, 160):
            pygame.draw.line(surface, pipe_color, (vx, 10), (vx, wall_h - 4), 2)

        # Baseboard
        pygame.draw.rect(surface, (30, 34, 44), (0, wall_h - 5, WIDTH, 5))
        pygame.draw.line(surface, (40, 46, 60), (0, wall_h - 1), (WIDTH, wall_h - 1), 1)

        # Small overhead light fixtures (circles on wall)
        for lx, _, _ in _LIGHT_POOLS:
            pygame.draw.rect(surface, (55, 60, 70), (lx - 8, wall_h - 8, 16, 6))
            pygame.draw.rect(surface, (80, 90, 100), (lx - 6, wall_h - 7, 12, 3))
            # Tiny glow under fixture
            glow = pygame.Surface((20, 6), pygame.SRCALPHA)
            glow.fill((100, 110, 130, 30))
            surface.blit(glow, (lx - 10, wall_h - 2))

    def _draw_furniture_shadows(self, surface):
        """Dark ellipses under each furniture piece."""
        shadow_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for rect, tag in self.furniture:
            if tag.startswith("chair") or tag.startswith("plant"):
                sw, sh = rect.w + 6, 8
            elif tag.startswith("server"):
                sw, sh = rect.w + 4, 10
            elif tag.startswith("desk"):
                sw, sh = rect.w + 8, 10
            elif tag.startswith("cabinet"):
                sw, sh = rect.w + 4, 8
            else:
                continue
            sx = rect.x + rect.w // 2 - sw // 2
            sy = rect.y + rect.h - 2
            pygame.draw.ellipse(shadow_surf, (0, 0, 0, 18), (sx, sy, sw, sh))
        surface.blit(shadow_surf, (0, 0))

    def _draw_furniture(self, surface):
        """Draw all furniture using draw_assets functions."""
        for rect, tag in self.furniture:
            prefix = tag.split("_")[0]
            idx = int(tag.split("_")[1])

            if prefix == "desk":
                draw_desk(surface, rect.x, rect.y, rect.w, rect.h - 10)

            elif prefix == "monitor":
                # Flicker effect: occasionally go dark
                flickering = self.monitor_flicker[idx] > 0
                if flickering:
                    # Draw dark monitor
                    pygame.draw.rect(surface, (40, 42, 48), (rect.x, rect.y, 40, 32))
                    pygame.draw.rect(surface, (20, 20, 24), (rect.x + 3, rect.y + 3, 34, 26))
                    pygame.draw.rect(surface, (50, 50, 55), (rect.x + 14, rect.y + 32, 12, 8))
                    pygame.draw.rect(surface, (60, 60, 65), (rect.x + 8, rect.y + 38, 24, 4))
                else:
                    draw_monitor(surface, rect.x, rect.y)
                    # Animated screen content: scrolling lines
                    screen_surf = pygame.Surface((34, 26), pygame.SRCALPHA)
                    t = self.time + idx * 1.7
                    for row in range(4):
                        ly = int((t * 8 + row * 7) % 26)
                        lw = 8 + int((row * 11 + idx * 5) % 18)
                        green = 40 + int(20 * math.sin(t * 2 + row))
                        pygame.draw.rect(screen_surf, (0, green, 0, 120),
                                         (2, ly, min(lw, 30), 2))
                    surface.blit(screen_surf, (rect.x + 3, rect.y + 3))

            elif prefix == "chair":
                draw_chair(surface, rect.x, rect.y)

            elif prefix == "cabinet":
                draw_filing_cabinet(surface, rect.x, rect.y)

            elif prefix == "plant":
                draw_plant(surface, rect.x, rect.y)

            elif prefix == "server":
                draw_server_rack(surface, rect.x, rect.y, rect.h)
                # Animated LED blinks
                led_surf = pygame.Surface((32, rect.h), pygame.SRCALPHA)
                for i in range(rect.h // 16):
                    uy = 4 + i * 16
                    # Blink pattern based on time
                    blink = math.sin(self.led_timer * (3 + i * 0.7) + idx * 2 + i) > 0.2
                    if blink:
                        led_c = C_NEON if (i + idx) % 3 == 0 else C_AMBER
                        pygame.draw.rect(led_surf, (*led_c, 200), (5, uy + 4, 3, 3))
                        # Tiny LED glow
                        pygame.draw.rect(led_surf, (*led_c, 40), (3, uy + 2, 7, 7))
                surface.blit(led_surf, (rect.x, rect.y))

            elif prefix == "wb":
                draw_whiteboard(surface, rect.x, rect.y, rect.w, rect.h)

    def _draw_doors(self, surface):
        """Draw 4 puzzle doors with glow effects."""
        completed = self.manager.completed_scenes
        glow_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

        for d in _DOORS:
            is_done = d["key"] in completed
            dx, dy = d["x"], d["y"]
            color = d["color"]

            # Door glow halo
            glow_r = 40 + int(6 * math.sin(self.time * 2))
            if is_done:
                # Green glow for completed
                glow_color = (*C_GREEN, 25)
            else:
                # Theme color glow
                glow_color = (*color, 20)

            cx = dx + _DOOR_W // 2
            cy = dy + _DOOR_H // 2
            pygame.draw.ellipse(glow_surf, glow_color,
                                (cx - glow_r, cy - glow_r, glow_r * 2, glow_r * 2))

            # Pulse ring when player is nearby
            if self.nearby_door == d["key"]:
                pulse_t = (self.time * 3) % 1.0
                pulse_r = int(30 + pulse_t * 25)
                pulse_alpha = int(80 * (1.0 - pulse_t))
                ring_color = (*C_NEON, pulse_alpha) if not is_done else (*C_GREEN, pulse_alpha)
                pygame.draw.circle(glow_surf, ring_color, (cx, cy), pulse_r, 2)

        surface.blit(glow_surf, (0, 0))

        # Draw actual door sprites
        for d in _DOORS:
            is_done = d["key"] in completed
            draw_door(surface, d["x"], d["y"],
                      color=d["color"], label=d["label"],
                      locked=False, completed=is_done)

    def _draw_exit_door(self, surface):
        """Exit door with golden/amber glow effect."""
        dx, dy = _EXIT_DOOR["x"], _EXIT_DOOR["y"]
        cx = dx + _DOOR_W // 2
        cy = dy + _DOOR_H // 2

        # Golden glow
        glow_surf = pygame.Surface((120, 100), pygame.SRCALPHA)
        for ring in range(6, 0, -1):
            r = 20 + ring * 8
            alpha = max(5, 30 - ring * 4)
            pygame.draw.ellipse(glow_surf, (180, 150, 40, alpha),
                                (60 - r, 50 - r // 2, r * 2, r))
        surface.blit(glow_surf, (cx - 60, cy - 50))

        # Pulse ring
        pulse_t = (self.time * 2) % 1.0
        pulse_r = int(25 + pulse_t * 20)
        pulse_alpha = int(60 * (1.0 - pulse_t))
        pulse_surf = pygame.Surface((pulse_r * 2 + 4, pulse_r * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(pulse_surf, (200, 170, 50, pulse_alpha),
                           (pulse_r + 2, pulse_r + 2), pulse_r, 2)
        surface.blit(pulse_surf, (cx - pulse_r - 2, cy - pulse_r - 2))

        draw_door(surface, dx, dy,
                  color=C_AMBER, label=_EXIT_DOOR["label"],
                  locked=False, completed=True)

    def _draw_particles(self, surface):
        """Render floating dust/data motes."""
        p_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for p in self.particles:
            if p.alpha <= 0:
                continue
            size = max(1, int(p.size))
            # Slightly tinted green for data-mote feel
            green_tint = 40 + int(20 * math.sin(p.life * 2))
            color = (30, green_tint, 30, p.alpha)
            pygame.draw.circle(p_surf, color, (int(p.x), int(p.y)), size)
            # Tiny bright core
            if size >= 2:
                pygame.draw.circle(p_surf, (60, 80, 60, min(p.alpha + 20, 120)),
                                   (int(p.x), int(p.y)), 1)
        surface.blit(p_surf, (0, 0))

    def _draw_interaction(self, surface):
        """Draw bouncing [E] prompt near the door the player is close to."""
        if self.nearby_door == "ending":
            px = _EXIT_DOOR["x"] + _DOOR_W // 2
            py = _EXIT_DOOR["y"] - 6
        else:
            for d in _DOORS:
                if d["key"] == self.nearby_door:
                    px = d["x"] + _DOOR_W // 2
                    py = d["y"] - 6
                    break
            else:
                return

        # Bouncing offset
        bounce = int(4 * math.sin(self.time * 5))
        draw_interact_prompt(surface, px, py + bounce, "E")

    def _draw_glitch(self, surface):
        """Horizontal glitch line distortion."""
        glitch_h = random.randint(1, 4)
        gy = self.glitch_y
        # Capture and shift a horizontal strip
        strip = surface.subsurface(pygame.Rect(0, max(0, gy), WIDTH, min(glitch_h, HEIGHT - gy))).copy()
        offset = random.randint(-15, 15)
        surface.blit(strip, (offset, gy))
        # Add colored noise line
        noise_color = random.choice([(0, 255, 0, 60), (255, 0, 0, 40), (0, 200, 255, 50)])
        noise_surf = pygame.Surface((WIDTH, 1), pygame.SRCALPHA)
        noise_surf.fill(noise_color)
        surface.blit(noise_surf, (0, gy))
