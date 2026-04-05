import json
import os
import pygame
from game.constants import BASE_DIR, WIDTH, HEIGHT


class SceneManager:
    def __init__(self, screen):
        self.screen = screen
        self.current_scene = None
        self.transition_alpha = 0
        self.transitioning = False
        self.transition_phase = None  # 'out' or 'in'
        self.next_scene_name = None
        self.transition_speed = 650  # alpha per second
        self.transition_surface = pygame.Surface((WIDTH, HEIGHT))
        self.transition_surface.fill((0, 0, 0))

        # Score tracking
        self.scores = {}
        self.completed_scenes = set()

        # Load data
        with open(os.path.join(BASE_DIR, "data", "puzzles.json"), "r", encoding="utf-8") as f:
            self.puzzles = json.load(f)
        with open(os.path.join(BASE_DIR, "data", "dialogues.json"), "r", encoding="utf-8") as f:
            self.dialogues = json.load(f)

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

    def update(self, dt):
        if self.transitioning:
            if self.transition_phase == "out":
                self.transition_alpha = min(255, self.transition_alpha + self.transition_speed * dt)
                if self.transition_alpha >= 255:
                    self.transition_alpha = 255
                    self.load_scene(self.next_scene_name)
                    self.transition_phase = "in"
            elif self.transition_phase == "in":
                self.transition_alpha = max(0, self.transition_alpha - self.transition_speed * dt)
                if self.transition_alpha <= 0:
                    self.transition_alpha = 0
                    self.transitioning = False
                    self.transition_phase = None
        if self.current_scene:
            self.current_scene.update(dt)

    def draw(self):
        if self.current_scene:
            self.current_scene.draw(self.screen)
        if self.transitioning and self.transition_alpha > 0:
            self.transition_surface.set_alpha(int(self.transition_alpha))
            self.screen.blit(self.transition_surface, (0, 0))
