import pygame
from game.constants import (WIDTH, HEIGHT, C_BG, C_BG2, C_BG3, C_BORDER, C_TEXT_PRI,
    C_TEXT_SEC, C_ACCENT, C_GREEN, C_NEON, C_WHITE, C_PANEL,
    PLAYER_SPEED, PLAYER_SIZE, PUZZLE_SCENES)
from game.ui.draw_assets import (draw_player, draw_desk, draw_monitor, draw_chair,
    draw_plant, draw_filing_cabinet, draw_server_rack, draw_door, draw_whiteboard,
    draw_office_floor, draw_wall, draw_interact_prompt, draw_text_box)
from game.ui.dialogue import DialogueBox
from game.ui.hud import HUD


# ── Door definitions ─────────────────────────────────────────────
# Each door: scene_key, x, y, color, label
_DOORS = [
    {"key": "caesar",         "x": 100,  "y": 80,  "color": PUZZLE_SCENES["caesar"]["color"],
     "label": "CESAR"},
    {"key": "base64",         "x": 1130, "y": 80,  "color": PUZZLE_SCENES["base64"]["color"],
     "label": "BASE64"},
    {"key": "hash",           "x": 100,  "y": 560, "color": PUZZLE_SCENES["hash"]["color"],
     "label": "HASH"},
    {"key": "diffie_hellman", "x": 1130, "y": 560, "color": PUZZLE_SCENES["diffie_hellman"]["color"],
     "label": "D-H"},
]

_EXIT_DOOR = {"x": 616, "y": 48, "color": C_GREEN, "label": "SALIDA"}

# Door dimensions (from draw_door: w=48, h=64)
_DOOR_W = 48
_DOOR_H = 64

# Interaction radius
_INTERACT_DIST = 50

# Wall height
_WALL_Y = 0
_WALL_H = 40


class HubScene:
    def __init__(self, manager):
        self.manager = manager

        # Player state — center of office
        self.px = WIDTH // 2 - PLAYER_SIZE // 2
        self.py = HEIGHT // 2 - PLAYER_SIZE // 2
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

        # Pre-render floor surface
        self.floor_surf = pygame.Surface((WIDTH, HEIGHT))
        draw_office_floor(self.floor_surf)

        # Build collision rects for furniture and walls
        self.furniture = self._build_furniture()
        self.wall_rects = self._build_walls()
        self.collision_rects = self.wall_rects + [r for r, _ in self.furniture]

        # Build door rects for collision and interaction
        self.door_rects = []
        for d in _DOORS:
            self.door_rects.append((
                pygame.Rect(d["x"] - 2, d["y"] - 2, _DOOR_W + 4, _DOOR_H + 4),
                d["key"]
            ))

        # Exit door rect
        self.exit_rect = pygame.Rect(
            _EXIT_DOOR["x"] - 2, _EXIT_DOOR["y"] - 2,
            _DOOR_W + 4, _DOOR_H + 4
        )

        # Nearby door for interaction prompt
        self.nearby_door = None  # (key, x, y) or None

    # ── Furniture layout ─────────────────────────────────────────

    def _build_furniture(self):
        """Return list of (pygame.Rect, draw_func) for all furniture."""
        items = []

        # -- Desks with monitors and chairs (4 workstations) --
        # Center-left workstation
        items.append((pygame.Rect(320, 200, 96, 60), "desk1"))
        items.append((pygame.Rect(340, 195, 40, 42), "monitor1"))
        items.append((pygame.Rect(330, 268, 28, 30), "chair1"))

        # Center-right workstation
        items.append((pygame.Rect(860, 200, 96, 60), "desk2"))
        items.append((pygame.Rect(880, 195, 40, 42), "monitor2"))
        items.append((pygame.Rect(870, 268, 28, 30), "chair2"))

        # Lower-center-left workstation
        items.append((pygame.Rect(320, 440, 96, 60), "desk3"))
        items.append((pygame.Rect(340, 435, 40, 42), "monitor3"))
        items.append((pygame.Rect(330, 508, 28, 30), "chair3"))

        # Lower-center-right workstation
        items.append((pygame.Rect(860, 440, 96, 60), "desk4"))
        items.append((pygame.Rect(880, 435, 40, 42), "monitor4"))
        items.append((pygame.Rect(870, 508, 28, 30), "chair4"))

        # -- Filing cabinets along walls --
        items.append((pygame.Rect(240, 70, 32, 56), "cabinet1"))
        items.append((pygame.Rect(1010, 70, 32, 56), "cabinet2"))
        items.append((pygame.Rect(240, 600, 32, 56), "cabinet3"))
        items.append((pygame.Rect(1010, 600, 32, 56), "cabinet4"))

        # -- Plants in corners --
        items.append((pygame.Rect(50, 160, 28, 30), "plant1"))
        items.append((pygame.Rect(1200, 160, 28, 30), "plant2"))
        items.append((pygame.Rect(50, 530, 28, 30), "plant3"))
        items.append((pygame.Rect(1200, 530, 28, 30), "plant4"))

        # -- Server racks --
        items.append((pygame.Rect(580, 140, 32, 80), "server1"))
        items.append((pygame.Rect(668, 140, 32, 80), "server2"))

        # -- Whiteboards on top wall --
        items.append((pygame.Rect(440, 48, 64, 40), "wb1"))
        items.append((pygame.Rect(776, 48, 64, 40), "wb2"))

        return items

    def _build_walls(self):
        """Boundary walls the player cannot cross."""
        t = 8  # wall thickness
        return [
            pygame.Rect(0, 0, WIDTH, _WALL_H + t),          # top wall
            pygame.Rect(0, 0, t, HEIGHT),                     # left wall
            pygame.Rect(WIDTH - t, 0, t, HEIGHT),             # right wall
            pygame.Rect(0, HEIGHT - t, WIDTH, t),             # bottom wall
        ]

    # ── Dialogue ─────────────────────────────────────────────────

    def _show_initial_dialogue(self):
        count = len(self.manager.completed_scenes
                     & {"caesar", "base64", "hash", "diffie_hellman"})
        hub_dialogues = self.manager.dialogues.get("hub", {})
        if count == 0:
            msgs = hub_dialogues.get("enter", [])
        elif count == 1:
            msgs = hub_dialogues.get("progress_1", [])
        elif count == 2:
            msgs = hub_dialogues.get("progress_2", [])
        elif count == 3:
            msgs = hub_dialogues.get("progress_3", [])
        else:
            msgs = hub_dialogues.get("all_done", [])
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
        # Dialogue takes priority
        if self.dialogue.active:
            self.dialogue.handle_event(event)
            return

        if event.type == pygame.KEYDOWN:
            if event.key in self.keys_held:
                self.keys_held[event.key] = True

            # Interact with nearby door
            if event.key == pygame.K_e and self.nearby_door is not None:
                self.manager.change_scene(self.nearby_door)

        elif event.type == pygame.KEYUP:
            if event.key in self.keys_held:
                self.keys_held[event.key] = False

    # ── Update ───────────────────────────────────────────────────

    def update(self, dt):
        self.dialogue.update(dt)
        self._update_hud()

        if self.dialogue.active:
            return

        # --- Player movement ---
        dx, dy = 0.0, 0.0
        if self.keys_held[pygame.K_w]:
            dy -= PLAYER_SPEED * dt
        if self.keys_held[pygame.K_s]:
            dy += PLAYER_SPEED * dt
        if self.keys_held[pygame.K_a]:
            dx -= PLAYER_SPEED * dt
        if self.keys_held[pygame.K_d]:
            dx += PLAYER_SPEED * dt

        # Update direction
        if dy < 0:
            self.direction = "up"
        elif dy > 0:
            self.direction = "down"
        if dx < 0:
            self.direction = "left"
        elif dx > 0:
            self.direction = "right"

        # Apply movement with collision per axis
        player_rect = pygame.Rect(self.px, self.py, PLAYER_SIZE, PLAYER_SIZE)

        # X axis
        if dx != 0:
            new_rect = player_rect.move(dx, 0)
            if not self._collides(new_rect):
                self.px = new_rect.x
                player_rect.x = new_rect.x

        # Y axis
        if dy != 0:
            new_rect = player_rect.move(0, dy)
            if not self._collides(new_rect):
                self.py = new_rect.y
                player_rect.y = new_rect.y

        # Clamp to screen
        self.px = max(8, min(WIDTH - PLAYER_SIZE - 8, self.px))
        self.py = max(_WALL_H + 8, min(HEIGHT - PLAYER_SIZE - 8, self.py))

        # --- Check nearby doors ---
        self.nearby_door = None
        pcx = self.px + PLAYER_SIZE // 2
        pcy = self.py + PLAYER_SIZE // 2

        for d in _DOORS:
            dcx = d["x"] + _DOOR_W // 2
            dcy = d["y"] + _DOOR_H // 2
            dist = ((pcx - dcx) ** 2 + (pcy - dcy) ** 2) ** 0.5
            if dist < _INTERACT_DIST:
                self.nearby_door = d["key"]
                break

        # Check exit door
        if self.nearby_door is None and self.manager.all_puzzles_complete():
            dcx = _EXIT_DOOR["x"] + _DOOR_W // 2
            dcy = _EXIT_DOOR["y"] + _DOOR_H // 2
            dist = ((pcx - dcx) ** 2 + (pcy - dcy) ** 2) ** 0.5
            if dist < _INTERACT_DIST:
                self.nearby_door = "ending"

    def _collides(self, rect):
        """Check if rect overlaps any collision object."""
        for cr in self.collision_rects:
            if rect.colliderect(cr):
                return True
        return False

    # ── Draw ─────────────────────────────────────────────────────

    def draw(self, surface):
        # Floor
        surface.blit(self.floor_surf, (0, 0))

        # Wall
        draw_wall(surface, _WALL_Y, _WALL_H)

        # Furniture
        self._draw_furniture(surface)

        # Doors
        self._draw_doors(surface)

        # Exit door (only when all puzzles complete)
        if self.manager.all_puzzles_complete():
            self._draw_exit_door(surface)

        # Player
        draw_player(surface, int(self.px), int(self.py), self.direction)

        # Interaction prompt
        if self.nearby_door is not None:
            if self.nearby_door == "ending":
                px = _EXIT_DOOR["x"] + _DOOR_W // 2
                py = _EXIT_DOOR["y"] - 6
            else:
                for d in _DOORS:
                    if d["key"] == self.nearby_door:
                        px = d["x"] + _DOOR_W // 2
                        py = d["y"] - 6
                        break
            draw_interact_prompt(surface, px, py, "E")

        # HUD
        self.hud.draw(surface)

        # Dialogue on top
        self.dialogue.draw(surface)

    def _draw_furniture(self, surface):
        """Draw all furniture items using draw_assets functions."""
        for rect, tag in self.furniture:
            if tag.startswith("desk"):
                draw_desk(surface, rect.x, rect.y, rect.w, rect.h - 12)
            elif tag.startswith("monitor"):
                draw_monitor(surface, rect.x, rect.y)
            elif tag.startswith("chair"):
                draw_chair(surface, rect.x, rect.y)
            elif tag.startswith("cabinet"):
                draw_filing_cabinet(surface, rect.x, rect.y)
            elif tag.startswith("plant"):
                draw_plant(surface, rect.x, rect.y)
            elif tag.startswith("server"):
                draw_server_rack(surface, rect.x, rect.y, rect.h)
            elif tag.startswith("wb"):
                draw_whiteboard(surface, rect.x, rect.y, rect.w, rect.h)

    def _draw_doors(self, surface):
        """Draw the 4 puzzle doors."""
        completed = self.manager.completed_scenes
        for d in _DOORS:
            is_done = d["key"] in completed
            draw_door(surface, d["x"], d["y"],
                      color=d["color"], label=d["label"],
                      locked=False, completed=is_done)

    def _draw_exit_door(self, surface):
        """Draw the exit door at center-top."""
        draw_door(surface, _EXIT_DOOR["x"], _EXIT_DOOR["y"],
                  color=C_GREEN, label=_EXIT_DOOR["label"],
                  locked=False, completed=True)
