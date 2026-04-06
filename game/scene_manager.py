import json
import math
import os
import random

import pygame
from game.constants import BASE_DIR, WIDTH, HEIGHT


# Neon palette for glitch effects
_NEON_CYAN = (0, 255, 255)
_NEON_GREEN = (0, 255, 70)
_NEON_WHITE = (220, 255, 220)
_NEON_COLORS = (_NEON_CYAN, _NEON_GREEN, _NEON_WHITE)

# Loading messages cycled during fade-out
_LOADING_MESSAGES = [
    "RE-ESTABLISHING SECURE LINK...",
    "LOADING",
    "DECRYPTING CHANNEL...",
    "SYNCING NODES...",
]


class SceneManager:
    def __init__(self, screen):
        self.screen = screen
        self.current_scene = None
        self.transition_alpha = 0
        self.transitioning = False
        self.transition_phase = None  # 'out' or 'in'
        self.next_scene_name = None
        self.transition_speed = 500  # alpha per second (slower for visible glitch)
        self.transition_surface = pygame.Surface((WIDTH, HEIGHT))
        self.transition_surface.fill((0, 0, 0))

        # Score tracking
        self.scores = {}
        self.completed_scenes = set()

        # Difficulty (set from intro)
        from game.constants import DIFFICULTY_MID
        self.difficulty = DIFFICULTY_MID

        # Hub visit count (for progressive dialogues)
        self.hub_visits = 0

        # Load data
        with open(os.path.join(BASE_DIR, "data", "puzzles.json"), "r", encoding="utf-8") as f:
            self.puzzles = json.load(f)
        with open(os.path.join(BASE_DIR, "data", "dialogues.json"), "r", encoding="utf-8") as f:
            self.dialogues = json.load(f)

        # -- Cinematic transition state --
        self._glitch_timer = 0.0
        self._glitch_lines = []  # list of (y, height, color, x_offset)
        self._cursor_visible = True
        self._cursor_timer = 0.0
        self._loading_msg = random.choice(_LOADING_MESSAGES)
        self._progress = 0.0
        self._scanline_y = -4  # vertical position of the scan line during fade-in
        self._signal_flash_timer = 0.0
        self._transition_time = 0.0  # total elapsed time in current transition

        # Cache a monospace font for HUD text (small size)
        self._mono_font = None  # lazy-init to avoid pygame.font issues at import

    # ------------------------------------------------------------------ #
    #  Core scene management (unchanged logic)
    # ------------------------------------------------------------------ #

    def load_scene(self, name):
        from game.intro import IntroScene
        from game.scene_hub import HubScene
        from game.scene_caesar import CaesarScene
        from game.scene_base64 import Base64Scene
        from game.scene_hash import HashScene
        from game.scene_dh import DHScene
        from game.scene_ending import EndingScene

        scene_map = {
            "intro": IntroScene,
            "hub": HubScene,
            "caesar": CaesarScene,
            "base64": Base64Scene,
            "hash": HashScene,
            "diffie_hellman": DHScene,
            "ending": EndingScene,
        }
        cls = scene_map.get(name)
        if cls:
            self.current_scene = cls(self)

    def change_scene(self, name):
        if self.transitioning:
            return
        self.next_scene_name = name
        self.transitioning = True
        self.transition_phase = "out"
        self.transition_alpha = 0
        # Reset cinematic state for new transition
        self._glitch_timer = 0.0
        self._glitch_lines = []
        self._cursor_visible = True
        self._cursor_timer = 0.0
        self._loading_msg = random.choice(_LOADING_MESSAGES)
        self._progress = 0.0
        self._scanline_y = -4
        self._signal_flash_timer = 0.0
        self._transition_time = 0.0

    def complete_puzzle(self, scene_name, score):
        self.scores[scene_name] = score
        self.completed_scenes.add(scene_name)

    def all_puzzles_complete(self):
        required = {"caesar", "base64", "hash", "diffie_hellman"}
        return required.issubset(self.completed_scenes)

    def total_score(self):
        return sum(self.scores.values())

    def handle_event(self, event):
        if self.transitioning:
            return
        if self.current_scene:
            self.current_scene.handle_event(event)

    # ------------------------------------------------------------------ #
    #  Update
    # ------------------------------------------------------------------ #

    def update(self, dt):
        if self.transitioning:
            self._transition_time += dt

            if self.transition_phase == "out":
                self.transition_alpha = min(255, self.transition_alpha + self.transition_speed * dt)
                # Update cinematic sub-systems
                self._update_glitch(dt)
                self._update_cursor(dt)
                self._update_progress(dt)
                if self.transition_alpha >= 255:
                    self.transition_alpha = 255
                    self.load_scene(self.next_scene_name)
                    self.transition_phase = "in"
                    self._scanline_y = -4
                    self._signal_flash_timer = 0.6  # show "SIGNAL LOCKED" for 0.6s

            elif self.transition_phase == "in":
                self.transition_alpha = max(0, self.transition_alpha - self.transition_speed * dt)
                self._signal_flash_timer = max(0.0, self._signal_flash_timer - dt)
                # Advance scanline from top to bottom
                if self._scanline_y < HEIGHT + 4:
                    self._scanline_y += 900 * dt  # pixels per second
                if self.transition_alpha <= 0:
                    self.transition_alpha = 0
                    self.transitioning = False
                    self.transition_phase = None

        if self.current_scene:
            self.current_scene.update(dt)

    # ------------------------------------------------------------------ #
    #  Draw
    # ------------------------------------------------------------------ #

    def draw(self):
        if self.current_scene:
            self.current_scene.draw(self.screen)

        if not self.transitioning or self.transition_alpha <= 0:
            return

        # Main dark overlay
        self.transition_surface.set_alpha(int(self.transition_alpha))
        self.screen.blit(self.transition_surface, (0, 0))

        if self.transition_phase == "out":
            # Glitch effects once overlay is semi-opaque
            if self.transition_alpha > 100:
                self._draw_glitch_effects()
            # Loading HUD once overlay is mostly opaque
            if self.transition_alpha > 150:
                self._draw_loading_text()

        elif self.transition_phase == "in":
            # "SIGNAL LOCKED" flash
            if self._signal_flash_timer > 0:
                self._draw_signal_locked()
            # Horizontal scan line sweep
            if 0 <= self._scanline_y <= HEIGHT:
                self._draw_scanline()

    # ------------------------------------------------------------------ #
    #  Cinematic helpers -- fade-out
    # ------------------------------------------------------------------ #

    def _ensure_font(self):
        if self._mono_font is None:
            self._mono_font = pygame.font.SysFont("couriernew,courier,monospace", 16)

    def _update_glitch(self, dt):
        """Regenerate glitch lines at random intervals."""
        self._glitch_timer -= dt
        if self._glitch_timer <= 0:
            self._glitch_timer = random.uniform(0.04, 0.12)
            count = random.randint(2, 6)
            self._glitch_lines = []
            for _ in range(count):
                y = random.randint(0, HEIGHT - 1)
                h = random.randint(1, 4)
                color = random.choice(_NEON_COLORS)
                x_off = random.randint(-10, 10)
                self._glitch_lines.append((y, h, color, x_off))

    def _update_cursor(self, dt):
        self._cursor_timer += dt
        if self._cursor_timer >= 0.35:
            self._cursor_timer = 0.0
            self._cursor_visible = not self._cursor_visible

    def _update_progress(self, dt):
        """Advance fake progress bar toward 1.0."""
        target = min(self.transition_alpha / 255.0, 1.0)
        self._progress += (target - self._progress) * dt * 3.0

    def _draw_glitch_effects(self):
        """Draw neon glitch lines and pixel-strip displacement."""
        for y, h, color, x_off in self._glitch_lines:
            # Neon horizontal strip
            strip_w = random.randint(WIDTH // 4, WIDTH)
            strip_x = random.randint(0, WIDTH - strip_w)
            glitch_surf = pygame.Surface((strip_w, h))
            glitch_surf.fill(color)
            glitch_surf.set_alpha(random.randint(60, 160))
            self.screen.blit(glitch_surf, (strip_x + x_off, y))

        # Pixel-strip displacement: grab a thin horizontal band and redraw offset
        if random.random() < 0.5:
            band_y = random.randint(0, HEIGHT - 8)
            band_h = random.randint(2, 8)
            shift = random.randint(-10, 10)
            try:
                band = self.screen.subsurface((0, band_y, WIDTH, band_h)).copy()
                self.screen.blit(band, (shift, band_y))
            except ValueError:
                pass  # subsurface out of bounds safety

    def _draw_loading_text(self):
        """Draw loading message, blinking cursor, and mini progress bar."""
        self._ensure_font()

        # Position: bottom-right corner
        margin = 24
        base_x = WIDTH - margin
        base_y = HEIGHT - margin - 20

        # Bracket + loading message
        cursor_char = "_" if self._cursor_visible else " "
        text = f"[>] {self._loading_msg}{cursor_char}"
        text_surf = self._mono_font.render(text, True, _NEON_GREEN)
        text_rect = text_surf.get_rect(bottomright=(base_x, base_y))
        self.screen.blit(text_surf, text_rect)

        # Mini progress bar below the text
        bar_w = 160
        bar_h = 4
        bar_x = base_x - bar_w
        bar_y = base_y + 6
        # Background
        pygame.draw.rect(self.screen, (30, 60, 30), (bar_x, bar_y, bar_w, bar_h))
        # Fill
        fill_w = int(bar_w * self._progress)
        if fill_w > 0:
            pygame.draw.rect(self.screen, _NEON_GREEN, (bar_x, bar_y, fill_w, bar_h))
        # Border
        pygame.draw.rect(self.screen, _NEON_GREEN, (bar_x, bar_y, bar_w, bar_h), 1)

        # Spinning indicator next to progress bar
        spin_chars = ["|", "/", "-", "\\"]
        idx = int(self._transition_time * 8) % len(spin_chars)
        spin_surf = self._mono_font.render(spin_chars[idx], True, _NEON_GREEN)
        self.screen.blit(spin_surf, (bar_x - 18, bar_y - 6))

    # ------------------------------------------------------------------ #
    #  Cinematic helpers -- fade-in
    # ------------------------------------------------------------------ #

    def _draw_signal_locked(self):
        """Flash 'SIGNAL LOCKED' confirmation during fade-in."""
        self._ensure_font()
        # Pulsing alpha based on remaining timer
        pulse = int(200 * min(self._signal_flash_timer / 0.3, 1.0))
        text_surf = self._mono_font.render("[SIGNAL LOCKED]", True, _NEON_CYAN)
        text_surf.set_alpha(pulse)
        cx = WIDTH // 2 - text_surf.get_width() // 2
        cy = HEIGHT // 2 - text_surf.get_height() // 2
        self.screen.blit(text_surf, (cx, cy))

    def _draw_scanline(self):
        """Draw a bright horizontal scan line sweeping top to bottom."""
        y = int(self._scanline_y)
        # Main bright line
        line_surf = pygame.Surface((WIDTH, 2))
        line_surf.fill(_NEON_CYAN)
        line_surf.set_alpha(180)
        self.screen.blit(line_surf, (0, y))
        # Softer glow above and below
        glow_surf = pygame.Surface((WIDTH, 6))
        glow_surf.fill(_NEON_CYAN)
        glow_surf.set_alpha(40)
        self.screen.blit(glow_surf, (0, y - 3))
