"""
Comprehensive headless tests for DEADLOCK game (rewritten version).
Covers: imports, draw_assets, word_wrap, scene loading, scene simulation,
difficulty system, hub WASD/E interaction, Caesar logic, Base64 logic,
hash terminal, DH color metaphor, DialogueBox word wrap, progressive
dialogues, score system, and scene transitions.

Run with:
    cd /home/nicolas/Documentos/ciberseguridad/Juego && \
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 -m pytest tests/test_game.py -v
"""
import os
import sys
import json
import hashlib

# Ensure project root is on path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Set dummy drivers before importing pygame
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
pygame.init()
screen = pygame.display.set_mode((1280, 720))


# ===================================================================
# 1. IMPORT TESTS
# ===================================================================

class TestImports:
    def test_import_crypto_caesar(self):
        from crypto.caesar import encrypt_caesar, decrypt_caesar
        assert callable(encrypt_caesar)
        assert callable(decrypt_caesar)

    def test_import_crypto_b64(self):
        from crypto.b64_utils import encode_b64, decode_b64, decode_partial
        assert callable(encode_b64)
        assert callable(decode_b64)
        assert callable(decode_partial)

    def test_import_crypto_hash(self):
        from crypto.hash_utils import sha256_short, sha256_full, build_rainbow_table
        assert callable(sha256_short)
        assert callable(sha256_full)
        assert callable(build_rainbow_table)

    def test_import_crypto_dh(self):
        from crypto.dh_utils import dh_public, dh_shared_key
        assert callable(dh_public)
        assert callable(dh_shared_key)

    def test_import_game_constants(self):
        from game.constants import WIDTH, HEIGHT, FPS, TITLE, SCENE_ORDER, PUZZLE_SCENES
        assert WIDTH == 1280
        assert HEIGHT == 720
        assert FPS == 60
        assert len(SCENE_ORDER) == 7
        assert len(PUZZLE_SCENES) == 4

    def test_import_scene_manager(self):
        from game.scene_manager import SceneManager
        assert callable(SceneManager)

    def test_import_all_scenes(self):
        from game.intro import IntroScene
        from game.scene_hub import HubScene
        from game.scene_caesar import CaesarScene
        from game.scene_base64 import Base64Scene
        from game.scene_hash import HashScene
        from game.scene_dh import DHScene
        from game.scene_ending import EndingScene
        for cls in [IntroScene, HubScene, CaesarScene, Base64Scene,
                    HashScene, DHScene, EndingScene]:
            assert callable(cls)

    def test_import_ui(self):
        from game.ui.dialogue import DialogueBox
        from game.ui.hud import HUD
        assert callable(DialogueBox)
        assert callable(HUD)

    def test_import_draw_assets(self):
        """Verify all draw_assets functions are importable."""
        from game.ui.draw_assets import (
            draw_player, draw_desk, draw_monitor, draw_server_rack,
            draw_filing_cabinet, draw_chair, draw_plant, draw_whiteboard,
            draw_door, draw_office_floor, draw_wall, draw_interact_prompt,
            draw_text_box, word_wrap,
        )
        for fn in [draw_player, draw_desk, draw_monitor, draw_server_rack,
                   draw_filing_cabinet, draw_chair, draw_plant, draw_whiteboard,
                   draw_door, draw_office_floor, draw_wall, draw_interact_prompt,
                   draw_text_box, word_wrap]:
            assert callable(fn)

    def test_import_difficulty_constants(self):
        from game.constants import (DIFFICULTY_DUMMY, DIFFICULTY_MID,
                                    DIFFICULTY_SENIOR, DIFFICULTY_NOOB,
                                    HINTS_CONFIG, DIFFICULTY_NAMES)
        assert DIFFICULTY_DUMMY == 0
        assert DIFFICULTY_MID == 1
        assert DIFFICULTY_SENIOR == 2
        assert DIFFICULTY_NOOB == 3
        assert len(HINTS_CONFIG) == 4
        assert len(DIFFICULTY_NAMES) == 4


# ===================================================================
# 2. DRAW_ASSETS TESTS -- each draw function runs without crash
# ===================================================================

class TestDrawAssets:
    """Verify each draw function renders without raising exceptions."""

    def test_draw_player_all_directions(self):
        from game.ui.draw_assets import draw_player
        surf = pygame.Surface((200, 200))
        for direction in ("up", "down", "left", "right"):
            draw_player(surf, 50, 50, direction)

    def test_draw_desk(self):
        from game.ui.draw_assets import draw_desk
        surf = pygame.Surface((200, 200))
        draw_desk(surf, 10, 10, 96, 48)

    def test_draw_monitor_with_text(self):
        from game.ui.draw_assets import draw_monitor
        surf = pygame.Surface((200, 200))
        draw_monitor(surf, 10, 10, text="HELLO")

    def test_draw_monitor_no_text(self):
        from game.ui.draw_assets import draw_monitor
        surf = pygame.Surface((200, 200))
        draw_monitor(surf, 10, 10)

    def test_draw_server_rack(self):
        from game.ui.draw_assets import draw_server_rack
        surf = pygame.Surface((200, 200))
        draw_server_rack(surf, 10, 10, h=80)

    def test_draw_filing_cabinet(self):
        from game.ui.draw_assets import draw_filing_cabinet
        surf = pygame.Surface((200, 200))
        draw_filing_cabinet(surf, 10, 10)

    def test_draw_chair(self):
        from game.ui.draw_assets import draw_chair
        surf = pygame.Surface((200, 200))
        draw_chair(surf, 10, 10)

    def test_draw_plant(self):
        from game.ui.draw_assets import draw_plant
        surf = pygame.Surface((200, 200))
        draw_plant(surf, 10, 10)

    def test_draw_whiteboard(self):
        from game.ui.draw_assets import draw_whiteboard
        surf = pygame.Surface((200, 200))
        draw_whiteboard(surf, 10, 10, 64, 40)

    def test_draw_door_variants(self):
        from game.ui.draw_assets import draw_door
        surf = pygame.Surface((200, 200))
        # Normal door
        draw_door(surf, 10, 10, color=(74, 106, 138), label="TEST")
        # Locked door
        draw_door(surf, 10, 10, locked=True, label="LOCKED")
        # Completed door
        draw_door(surf, 10, 10, completed=True, label="DONE")

    def test_draw_office_floor(self):
        from game.ui.draw_assets import draw_office_floor
        surf = pygame.Surface((200, 200))
        draw_office_floor(surf)

    def test_draw_office_floor_with_rect(self):
        from game.ui.draw_assets import draw_office_floor
        surf = pygame.Surface((200, 200))
        draw_office_floor(surf, pygame.Rect(10, 10, 100, 100))

    def test_draw_wall(self):
        from game.ui.draw_assets import draw_wall
        surf = pygame.Surface((200, 200))
        draw_wall(surf, 0, wall_h=40)

    def test_draw_interact_prompt(self):
        from game.ui.draw_assets import draw_interact_prompt
        surf = pygame.Surface((200, 200))
        draw_interact_prompt(surf, 100, 100, key="E")

    def test_draw_text_box_no_wrap(self):
        from game.ui.draw_assets import draw_text_box
        surf = pygame.Surface((400, 200))
        font = pygame.font.SysFont("monospace", 14)
        w, h = draw_text_box(surf, "Hello World", 10, 10, font)
        assert w > 0
        assert h > 0

    def test_draw_text_box_with_wrap(self):
        from game.ui.draw_assets import draw_text_box
        surf = pygame.Surface((400, 200))
        font = pygame.font.SysFont("monospace", 14)
        long_text = "This is a much longer text that should be word wrapped to fit within the given maximum width constraint."
        w, h = draw_text_box(surf, long_text, 10, 10, font, max_width=200)
        assert w > 0
        assert h > 0


# ===================================================================
# 3. WORD_WRAP TESTS
# ===================================================================

class TestWordWrap:
    """Test the word_wrap function from draw_assets."""

    def test_short_text_single_line(self):
        from game.ui.draw_assets import word_wrap
        font = pygame.font.SysFont("monospace", 14)
        result = word_wrap("Hello", font, 500)
        assert len(result) == 1
        assert result[0] == "Hello"

    def test_long_text_wraps(self):
        from game.ui.draw_assets import word_wrap
        font = pygame.font.SysFont("monospace", 14)
        long_text = "This is a very long text that should definitely be wrapped into multiple lines"
        result = word_wrap(long_text, font, 150)
        assert len(result) > 1
        # All words should still be present
        recombined = " ".join(result)
        assert recombined == long_text

    def test_zero_max_width_returns_single_line(self):
        from game.ui.draw_assets import word_wrap
        font = pygame.font.SysFont("monospace", 14)
        result = word_wrap("Some text", font, 0)
        assert len(result) == 1
        assert result[0] == "Some text"

    def test_negative_max_width_returns_single_line(self):
        from game.ui.draw_assets import word_wrap
        font = pygame.font.SysFont("monospace", 14)
        result = word_wrap("Some text", font, -100)
        assert len(result) == 1

    def test_empty_string(self):
        from game.ui.draw_assets import word_wrap
        font = pygame.font.SysFont("monospace", 14)
        result = word_wrap("", font, 200)
        assert isinstance(result, list)
        assert len(result) >= 1  # At least the original (empty) text

    def test_single_very_long_word(self):
        from game.ui.draw_assets import word_wrap
        font = pygame.font.SysFont("monospace", 14)
        result = word_wrap("Superlongwordwithoutspaces", font, 50)
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_dialogue_word_wrap(self):
        """Test the word_wrap function from dialogue module."""
        from game.ui.dialogue import _word_wrap
        font = pygame.font.SysFont("monospace", 15)
        long_text = "This is a dialogue message that should wrap properly into multiple lines for the dialogue box."
        result = _word_wrap(long_text, font, 200)
        assert len(result) > 1
        recombined = " ".join(result)
        assert recombined == long_text


# ===================================================================
# 4. SCENE INSTANTIATION (all 7 scenes load)
# ===================================================================

class TestSceneInstantiation:
    def _get_manager(self):
        from game.scene_manager import SceneManager
        return SceneManager(screen)

    def test_scene_manager_creation(self):
        manager = self._get_manager()
        assert manager.current_scene is None
        assert manager.scores == {}
        assert manager.completed_scenes == set()

    def test_load_intro(self):
        manager = self._get_manager()
        manager.load_scene("intro")
        from game.intro import IntroScene
        assert isinstance(manager.current_scene, IntroScene)

    def test_load_hub(self):
        manager = self._get_manager()
        manager.load_scene("hub")
        from game.scene_hub import HubScene
        assert isinstance(manager.current_scene, HubScene)

    def test_load_caesar(self):
        manager = self._get_manager()
        manager.load_scene("caesar")
        from game.scene_caesar import CaesarScene
        assert isinstance(manager.current_scene, CaesarScene)

    def test_load_base64(self):
        manager = self._get_manager()
        manager.load_scene("base64")
        from game.scene_base64 import Base64Scene
        assert isinstance(manager.current_scene, Base64Scene)

    def test_load_hash(self):
        manager = self._get_manager()
        manager.load_scene("hash")
        from game.scene_hash import HashScene
        assert isinstance(manager.current_scene, HashScene)

    def test_load_diffie_hellman(self):
        manager = self._get_manager()
        manager.load_scene("diffie_hellman")
        from game.scene_dh import DHScene
        assert isinstance(manager.current_scene, DHScene)

    def test_load_ending(self):
        manager = self._get_manager()
        manager.load_scene("ending")
        from game.scene_ending import EndingScene
        assert isinstance(manager.current_scene, EndingScene)

    def test_load_invalid_scene(self):
        manager = self._get_manager()
        manager.load_scene("nonexistent")
        assert manager.current_scene is None


# ===================================================================
# 5. SCENE UPDATE + DRAW (each scene can run update and draw)
# ===================================================================

class TestSceneSimulation:
    def _get_manager(self):
        from game.scene_manager import SceneManager
        return SceneManager(screen)

    def _simulate_scene(self, scene_name, num_frames=30):
        """Load scene, run update/draw loop, simulate mouse events."""
        manager = self._get_manager()
        manager.load_scene(scene_name)
        assert manager.current_scene is not None, f"Failed to load scene: {scene_name}"

        dt = 1.0 / 60.0

        # Run update/draw loop
        for _ in range(num_frames):
            manager.update(dt)
            manager.draw()

        # Simulate mouse events
        motion_event = pygame.event.Event(
            pygame.MOUSEMOTION, pos=(640, 360), rel=(1, 0), buttons=(0, 0, 0)
        )
        manager.handle_event(motion_event)

        click_down = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, pos=(640, 360), button=1
        )
        manager.handle_event(click_down)

        click_up = pygame.event.Event(
            pygame.MOUSEBUTTONUP, pos=(640, 360), button=1
        )
        manager.handle_event(click_up)

        # Additional frames after events
        for _ in range(10):
            manager.update(dt)
            manager.draw()

        return manager

    def test_simulate_intro(self):
        manager = self._simulate_scene("intro")
        assert manager.current_scene is not None

    def test_simulate_hub(self):
        manager = self._simulate_scene("hub")
        assert manager.current_scene is not None

    def test_simulate_caesar(self):
        manager = self._simulate_scene("caesar")
        assert manager.current_scene is not None

    def test_simulate_base64(self):
        manager = self._simulate_scene("base64")
        assert manager.current_scene is not None

    def test_simulate_hash(self):
        manager = self._simulate_scene("hash")
        assert manager.current_scene is not None

    def test_simulate_diffie_hellman(self):
        manager = self._simulate_scene("diffie_hellman")
        assert manager.current_scene is not None

    def test_simulate_ending(self):
        manager = self._simulate_scene("ending")
        assert manager.current_scene is not None


# ===================================================================
# 6. DIFFICULTY SYSTEM
# ===================================================================

class TestDifficultySystem:
    def _get_manager(self):
        from game.scene_manager import SceneManager
        return SceneManager(screen)

    def test_default_difficulty_is_mid(self):
        from game.constants import DIFFICULTY_MID
        manager = self._get_manager()
        assert manager.difficulty == DIFFICULTY_MID

    def test_set_difficulty_dummy(self):
        from game.constants import DIFFICULTY_DUMMY, HINTS_CONFIG
        manager = self._get_manager()
        manager.difficulty = DIFFICULTY_DUMMY
        config = HINTS_CONFIG[manager.difficulty]
        assert config["free_hints"] == 3
        assert config["visual_aids"] is True

    def test_set_difficulty_mid(self):
        from game.constants import DIFFICULTY_MID, HINTS_CONFIG
        manager = self._get_manager()
        manager.difficulty = DIFFICULTY_MID
        config = HINTS_CONFIG[manager.difficulty]
        assert config["free_hints"] == 1
        assert config["visual_aids"] is False

    def test_set_difficulty_senior(self):
        from game.constants import DIFFICULTY_SENIOR, HINTS_CONFIG
        manager = self._get_manager()
        manager.difficulty = DIFFICULTY_SENIOR
        config = HINTS_CONFIG[manager.difficulty]
        assert config["free_hints"] == 1
        assert config["visual_aids"] is False

    def test_set_difficulty_noob(self):
        from game.constants import DIFFICULTY_NOOB, HINTS_CONFIG
        manager = self._get_manager()
        manager.difficulty = DIFFICULTY_NOOB
        config = HINTS_CONFIG[manager.difficulty]
        assert config["free_hints"] == 0
        assert config["visual_aids"] is False

    def test_difficulty_affects_caesar_scene(self):
        """Caesar scene should read difficulty from manager."""
        from game.constants import DIFFICULTY_DUMMY, HINTS_CONFIG
        manager = self._get_manager()
        manager.difficulty = DIFFICULTY_DUMMY
        manager.load_scene("caesar")
        scene = manager.current_scene
        assert scene.free_hints == HINTS_CONFIG[DIFFICULTY_DUMMY]["free_hints"]
        assert scene.visual_aids == HINTS_CONFIG[DIFFICULTY_DUMMY]["visual_aids"]

    def test_difficulty_affects_base64_scene(self):
        """Base64 scene should read difficulty from manager."""
        from game.constants import DIFFICULTY_NOOB, HINTS_CONFIG
        manager = self._get_manager()
        manager.difficulty = DIFFICULTY_NOOB
        manager.load_scene("base64")
        scene = manager.current_scene
        assert scene.free_hints == HINTS_CONFIG[DIFFICULTY_NOOB]["free_hints"]
        assert scene.visual_aids == HINTS_CONFIG[DIFFICULTY_NOOB]["visual_aids"]


# ===================================================================
# 7. HUB WASD MOVEMENT SIMULATION
# ===================================================================

class TestHubWASD:
    def _get_hub(self):
        from game.scene_manager import SceneManager
        manager = SceneManager(screen)
        manager.load_scene("hub")
        scene = manager.current_scene
        # Dismiss dialogue so movement works
        while scene.dialogue.active:
            scene.dialogue.advance()
        return manager, scene

    def test_initial_player_position_is_center(self):
        from game.constants import WIDTH, HEIGHT, PLAYER_SIZE
        _, scene = self._get_hub()
        expected_x = WIDTH // 2 - PLAYER_SIZE // 2
        expected_y = HEIGHT // 2 - PLAYER_SIZE // 2
        assert scene.px == expected_x
        assert scene.py == expected_y

    def test_move_down_with_s(self):
        manager, scene = self._get_hub()
        initial_y = scene.py

        # Press S
        key_down = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_s)
        scene.handle_event(key_down)

        # Update several frames
        for _ in range(10):
            scene.update(1.0 / 60.0)

        assert scene.py > initial_y, "Player should have moved down"
        assert scene.direction == "down"

        # Release S
        key_up = pygame.event.Event(pygame.KEYUP, key=pygame.K_s)
        scene.handle_event(key_up)

    def test_move_up_with_w(self):
        manager, scene = self._get_hub()
        initial_y = scene.py

        key_down = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_w)
        scene.handle_event(key_down)

        for _ in range(10):
            scene.update(1.0 / 60.0)

        assert scene.py < initial_y, "Player should have moved up"
        assert scene.direction == "up"

        key_up = pygame.event.Event(pygame.KEYUP, key=pygame.K_w)
        scene.handle_event(key_up)

    def test_move_left_with_a(self):
        manager, scene = self._get_hub()
        initial_x = scene.px

        key_down = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a)
        scene.handle_event(key_down)

        for _ in range(10):
            scene.update(1.0 / 60.0)

        assert scene.px < initial_x, "Player should have moved left"
        assert scene.direction == "left"

        key_up = pygame.event.Event(pygame.KEYUP, key=pygame.K_a)
        scene.handle_event(key_up)

    def test_move_right_with_d(self):
        manager, scene = self._get_hub()
        initial_x = scene.px

        key_down = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d)
        scene.handle_event(key_down)

        for _ in range(10):
            scene.update(1.0 / 60.0)

        assert scene.px > initial_x, "Player should have moved right"
        assert scene.direction == "right"

        key_up = pygame.event.Event(pygame.KEYUP, key=pygame.K_d)
        scene.handle_event(key_up)

    def test_diagonal_movement(self):
        """Pressing W+D should move player up-right."""
        manager, scene = self._get_hub()
        initial_x = scene.px
        initial_y = scene.py

        # Press W and D simultaneously
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_w))
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d))

        for _ in range(10):
            scene.update(1.0 / 60.0)

        assert scene.px > initial_x, "Player should have moved right"
        assert scene.py < initial_y, "Player should have moved up"

        scene.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_w))
        scene.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_d))

    def test_movement_stops_on_key_release(self):
        manager, scene = self._get_hub()

        # Press and release D
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d))
        for _ in range(5):
            scene.update(1.0 / 60.0)
        scene.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_d))

        pos_after_release = scene.px
        for _ in range(10):
            scene.update(1.0 / 60.0)
        assert scene.px == pos_after_release, "Player should stop after key release"


# ===================================================================
# 8. HUB E INTERACTION (pressing E near a door)
# ===================================================================

class TestHubInteraction:
    def _get_hub(self):
        from game.scene_manager import SceneManager
        manager = SceneManager(screen)
        manager.load_scene("hub")
        scene = manager.current_scene
        # Dismiss dialogue
        while scene.dialogue.active:
            scene.dialogue.advance()
        return manager, scene

    def test_e_near_caesar_door(self):
        """Moving player near the Caesar door and pressing E should trigger transition."""
        manager, scene = self._get_hub()

        # Caesar door is at x=100, y=80 (from _DOORS)
        # Place player near it (door center + some offset)
        scene.px = 110.0
        scene.py = 100.0
        scene.update(1.0 / 60.0)  # Update to detect nearby door

        assert scene.nearby_door == "caesar", (
            f"Expected nearby_door='caesar', got '{scene.nearby_door}'"
        )

        # Press E
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))

        # Manager should now be transitioning to caesar
        assert manager.transitioning is True
        assert manager.next_scene_name == "caesar"

    def test_e_far_from_doors_does_nothing(self):
        """Pressing E far from any door should do nothing."""
        manager, scene = self._get_hub()

        # Player at center is far from all doors
        scene.update(1.0 / 60.0)
        assert scene.nearby_door is None

        # Press E -- should not crash or transition
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
        assert manager.transitioning is False

    def test_exit_door_hidden_when_incomplete(self):
        """Exit door should not be interactable when puzzles are incomplete."""
        manager, scene = self._get_hub()

        # Place player near exit door position (616, 48)
        scene.px = 620.0
        scene.py = 70.0
        scene.update(1.0 / 60.0)

        # Exit door should not show (all_puzzles_complete is False)
        assert scene.nearby_door != "ending"

    def test_exit_door_available_when_all_complete(self):
        """Exit door should be interactable when all puzzles are complete."""
        manager, scene = self._get_hub()

        # Complete all puzzles
        manager.complete_puzzle("caesar", 80)
        manager.complete_puzzle("base64", 80)
        manager.complete_puzzle("hash", 80)
        manager.complete_puzzle("diffie_hellman", 80)

        # Place player near exit door (616, 48)
        scene.px = 620.0
        scene.py = 70.0
        scene.update(1.0 / 60.0)

        assert scene.nearby_door == "ending", (
            f"Expected nearby_door='ending', got '{scene.nearby_door}'"
        )


# ===================================================================
# 9. CAESAR PUZZLE LOGIC
# ===================================================================

class TestCaesarLogic:
    def test_decrypt_correct_shift(self):
        """decrypt_caesar('PHHW PH', 3) == 'MEET ME'."""
        from crypto.caesar import decrypt_caesar
        result = decrypt_caesar("PHHW PH", 3)
        assert result.upper() == "MEET ME"

    def test_decrypt_from_puzzle_data(self):
        """Verify using data from puzzles.json."""
        from crypto.caesar import decrypt_caesar
        with open(os.path.join(PROJECT_ROOT, "data", "puzzles.json"), "r") as f:
            puzzles = json.load(f)
        caesar = puzzles["caesar"]
        result = decrypt_caesar(caesar["cipher_text"], caesar["correct_shift"])
        assert result.upper() == caesar["plain_text"].upper()

    def test_all_26_shifts_produce_valid_output(self):
        from crypto.caesar import decrypt_caesar
        cipher = "PHHW PH"
        for shift in range(26):
            result = decrypt_caesar(cipher, shift)
            assert isinstance(result, str)
            assert len(result) == len(cipher)

    def test_encrypt_then_decrypt_roundtrip(self):
        from crypto.caesar import encrypt_caesar, decrypt_caesar
        original = "Hello World"
        for shift in range(26):
            encrypted = encrypt_caesar(original, shift)
            decrypted = decrypt_caesar(encrypted, shift)
            assert decrypted == original

    def test_non_alpha_preserved(self):
        from crypto.caesar import encrypt_caesar
        result = encrypt_caesar("AB 12!?", 3)
        assert result[2] == " "
        assert result[3] == "1"
        assert result[4] == "2"
        assert result[5] == "!"

    def test_shift_zero_identity(self):
        from crypto.caesar import decrypt_caesar
        text = "PHHW PH"
        assert decrypt_caesar(text, 0) == text

    def test_shift_26_identity(self):
        from crypto.caesar import decrypt_caesar
        text = "PHHW PH"
        assert decrypt_caesar(text, 26) == text


# ===================================================================
# 10. BASE64 PUZZLE LOGIC
# ===================================================================

class TestBase64Logic:
    def test_blocks_correct_order_decodes(self):
        """Blocks in correct order should decode to the expected decoded string."""
        from crypto.b64_utils import decode_b64
        with open(os.path.join(PROJECT_ROOT, "data", "puzzles.json"), "r") as f:
            puzzles = json.load(f)
        b64 = puzzles["base64"]
        full_encoded = "".join(b64["blocks"])
        result = decode_b64(full_encoded)
        assert result == b64["decoded"], f"Expected '{b64['decoded']}', got '{result}'"

    def test_full_encoded_matches(self):
        with open(os.path.join(PROJECT_ROOT, "data", "puzzles.json"), "r") as f:
            puzzles = json.load(f)
        b64 = puzzles["base64"]
        assert "".join(b64["blocks"]) == b64["encoded"]

    def test_decode_partial_all_slots(self):
        from crypto.b64_utils import decode_partial
        slots = ["SGVs", "bG8g", "V29y", "bGQh"]
        result = decode_partial(slots)
        assert result == "Hello World!"

    def test_decode_partial_none_slots(self):
        from crypto.b64_utils import decode_partial
        result = decode_partial([None, None, None, None])
        assert isinstance(result, str)

    def test_decode_partial_mixed_slots(self):
        from crypto.b64_utils import decode_partial
        result = decode_partial(["SGVs", None, "V29y", None])
        assert isinstance(result, str)

    def test_encode_decode_roundtrip(self):
        from crypto.b64_utils import encode_b64, decode_b64
        original = "Hello World!"
        assert decode_b64(encode_b64(original)) == original

    def test_base64_lookup_table_exists(self):
        """The base64 reference table data should be available in scene_base64."""
        from game.scene_base64 import _REF_LINES, _B64_CHARS
        assert len(_B64_CHARS) == 64
        assert len(_REF_LINES) > 5
        assert "BASE64" in _REF_LINES[0]


# ===================================================================
# 11. HASH TERMINAL LOGIC
# ===================================================================

class TestHashLogic:
    CANDIDATES = ["password", "123456", "qwerty", "letmein", "deadlock"]

    def test_sha256_short_consistent(self):
        from crypto.hash_utils import sha256_short
        for word in self.CANDIDATES:
            h1 = sha256_short(word)
            h2 = sha256_short(word)
            assert h1 == h2, f"Inconsistent hash for '{word}'"
            assert len(h1) == 16, f"Expected 16 chars, got {len(h1)}"
            assert all(c in "0123456789abcdef" for c in h1)

    def test_sha256_short_matches_hashlib(self):
        from crypto.hash_utils import sha256_short
        for word in self.CANDIDATES:
            expected = hashlib.sha256(word.encode()).hexdigest()[:16]
            assert sha256_short(word) == expected

    def test_build_rainbow_table(self):
        from crypto.hash_utils import build_rainbow_table
        table = build_rainbow_table(self.CANDIDATES)
        assert isinstance(table, dict)
        assert len(table) == len(self.CANDIDATES)
        for word in self.CANDIDATES:
            assert word in table
            assert isinstance(table[word], str)
            assert len(table[word]) == 16

    def test_all_hashes_unique(self):
        from crypto.hash_utils import build_rainbow_table
        table = build_rainbow_table(self.CANDIDATES)
        hashes = list(table.values())
        assert len(set(hashes)) == len(hashes), "Duplicate hashes found"

    def test_sha256_full(self):
        from crypto.hash_utils import sha256_full
        result = sha256_full("test")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_hash_scene_rounds_use_puzzle_data(self):
        """Hash scene builds rounds from puzzle JSON data."""
        from game.scene_hash import _build_rounds
        with open(os.path.join(PROJECT_ROOT, "data", "puzzles.json"), "r") as f:
            puzzles = json.load(f)
        rounds = _build_rounds(puzzles["hash"])
        assert len(rounds) == 3
        assert rounds[0]["hlen"] == 64
        assert rounds[1]["hlen"] == 8
        assert rounds[2]["hlen"] == 16


# ===================================================================
# 12. DIFFIE-HELLMAN COLOR METAPHOR
# ===================================================================

class TestDiffieHellmanLogic:
    def test_dh_public_basic(self):
        from crypto.dh_utils import dh_public
        assert dh_public(5, 23, 7) == pow(5, 7, 23)

    def test_dh_shared_key_matching(self):
        """Both sides should compute the same shared key for any a in 1-20."""
        from crypto.dh_utils import dh_public, dh_shared_key
        g, p = 5, 23
        b_secret = 15
        b_public = dh_public(g, p, b_secret)

        for a in range(1, 21):
            a_public = dh_public(g, p, a)
            key_player = dh_shared_key(b_public, p, a)
            key_other = dh_shared_key(a_public, p, b_secret)
            assert key_player == key_other, (
                f"Keys don't match for a={a}: player={key_player}, other={key_other}"
            )

    def test_dh_public_range(self):
        from crypto.dh_utils import dh_public
        g, p = 5, 23
        for secret in range(1, 21):
            pub = dh_public(g, p, secret)
            assert 0 <= pub < p, f"Public value {pub} out of range for secret={secret}"

    def test_dh_different_secrets_same_key(self):
        from crypto.dh_utils import dh_public, dh_shared_key
        g, p, b = 5, 23, 15
        B = dh_public(g, p, b)
        keys_set = set()
        for a in range(1, 21):
            A = dh_public(g, p, a)
            k1 = dh_shared_key(B, p, a)
            k2 = dh_shared_key(A, p, b)
            assert k1 == k2
            keys_set.add(k1)
        assert len(keys_set) > 1, "All secrets produce the same shared key"

    def test_dh_color_metaphor_in_scene(self):
        """DH scene should have color mapping function that works."""
        from game.scene_dh import _number_to_color, _blend_colors, _BASE_COLOR
        # number_to_color should return valid RGB for all values in range
        for n in range(23):
            color = _number_to_color(n, 23)
            assert len(color) == 3
            assert all(0 <= c <= 255 for c in color)

        # blend_colors should produce valid output
        c1 = (255, 0, 0)
        c2 = (0, 0, 255)
        blended = _blend_colors(c1, c2, 0.5)
        assert len(blended) == 3
        assert all(0 <= c <= 255 for c in blended)

    def test_dh_scene_uses_puzzle_params(self):
        """DH scene should use g=5, p=23 from puzzle data."""
        from game.scene_dh import _G, _P, _B_SECRET, _B_PUBLIC
        from crypto.dh_utils import dh_public
        assert _G == 5
        assert _P == 23
        assert _B_SECRET == 15
        assert _B_PUBLIC == dh_public(5, 23, 15)


# ===================================================================
# 13. DIALOGUE BOX WORD WRAP
# ===================================================================

class TestDialogueBox:
    def test_initial_state(self):
        from game.ui.dialogue import DialogueBox
        db = DialogueBox()
        assert db.active is False
        assert db.finished is False

    def test_show_activates(self):
        from game.ui.dialogue import DialogueBox
        db = DialogueBox()
        msgs = [
            {"speaker": "TEST", "text": "Hello"},
            {"speaker": "TEST", "text": "World"},
        ]
        db.show(msgs)
        assert db.active is True
        assert db.current_index == 0
        assert db.char_index == 0

    def test_update_typewriter(self):
        from game.ui.dialogue import DialogueBox
        db = DialogueBox()
        msgs = [{"speaker": "TEST", "text": "Hello World"}]
        db.show(msgs)
        for _ in range(50):
            db.update(0.05)
        assert db.char_index > 0

    def test_advance_completes_text(self):
        from game.ui.dialogue import DialogueBox
        db = DialogueBox()
        msgs = [{"speaker": "TEST", "text": "Hello World"}]
        db.show(msgs)
        db.advance()
        assert db.char_index == len("Hello World")
        assert db.active is True

    def test_advance_next_message(self):
        from game.ui.dialogue import DialogueBox
        db = DialogueBox()
        msgs = [
            {"speaker": "TEST", "text": "First"},
            {"speaker": "TEST", "text": "Second"},
        ]
        db.show(msgs)
        db.advance()  # complete first
        db.advance()  # move to second
        assert db.current_index == 1
        assert db.active is True

    def test_advance_through_all(self):
        from game.ui.dialogue import DialogueBox
        db = DialogueBox()
        msgs = [
            {"speaker": "TEST", "text": "A"},
            {"speaker": "TEST", "text": "B"},
        ]
        db.show(msgs)
        db.advance()  # complete A
        db.advance()  # move to B
        db.advance()  # complete B
        db.advance()  # finish
        assert db.active is False
        assert db.finished is True

    def test_on_complete_callback(self):
        from game.ui.dialogue import DialogueBox
        db = DialogueBox()
        called = [False]
        def callback():
            called[0] = True
        msgs = [{"speaker": "TEST", "text": "Done"}]
        db.show(msgs, on_complete=callback)
        db.advance()  # complete text
        db.advance()  # finish
        assert called[0] is True

    def test_draw_does_not_crash(self):
        from game.ui.dialogue import DialogueBox
        db = DialogueBox()
        db.draw(screen)
        msgs = [{"speaker": "TEST", "text": "Hello"}]
        db.show(msgs)
        db.update(0.1)
        db.draw(screen)

    def test_handle_event_click_advances(self):
        from game.ui.dialogue import DialogueBox
        db = DialogueBox()
        msgs = [{"speaker": "TEST", "text": "Click me"}]
        db.show(msgs)
        click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(100, 100), button=1)
        result = db.handle_event(click)
        assert result is True
        assert db.char_index == len("Click me")

    def test_handle_event_space_advances(self):
        """Space bar should also advance dialogue."""
        from game.ui.dialogue import DialogueBox
        db = DialogueBox()
        msgs = [{"speaker": "TEST", "text": "Press space"}]
        db.show(msgs)
        space = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)
        result = db.handle_event(space)
        assert result is True
        assert db.char_index == len("Press space")

    def test_long_text_wraps_in_draw(self):
        """A very long dialogue text should render without crash (word wrap in draw)."""
        from game.ui.dialogue import DialogueBox
        db = DialogueBox()
        long_text = ("Este es un texto muy largo que deberia envolverse "
                     "automaticamente en multiples lineas dentro del cuadro "
                     "de dialogo para mantener la legibilidad del juego.")
        msgs = [{"speaker": "CONTROL", "text": long_text}]
        db.show(msgs)
        # Complete the text so draw renders all characters
        db.advance()
        db.draw(screen)
        # Should not crash


# ===================================================================
# 14. PROGRESSIVE HUB DIALOGUES
# ===================================================================

class TestProgressiveDialogues:
    def test_dialogue_keys_exist(self):
        """dialogues.json hub section should have progressive keys."""
        with open(os.path.join(PROJECT_ROOT, "data", "dialogues.json"), "r") as f:
            data = json.load(f)
        hub = data["hub"]
        assert "enter" in hub
        assert "progress_1" in hub
        assert "progress_2" in hub
        assert "progress_3" in hub
        assert "all_done" in hub

    def test_progress_1_after_one_puzzle(self):
        """Hub should show progress_1 dialogue after completing 1 puzzle."""
        from game.scene_manager import SceneManager
        manager = SceneManager(screen)
        manager.complete_puzzle("caesar", 80)
        manager.load_scene("hub")
        scene = manager.current_scene
        # Dialogue should be active with progress_1 text
        assert scene.dialogue.active is True
        expected_msgs = manager.dialogues["hub"]["progress_1"]
        assert scene.dialogue.messages == expected_msgs

    def test_progress_2_after_two_puzzles(self):
        from game.scene_manager import SceneManager
        manager = SceneManager(screen)
        manager.complete_puzzle("caesar", 80)
        manager.complete_puzzle("base64", 70)
        manager.load_scene("hub")
        scene = manager.current_scene
        assert scene.dialogue.active is True
        expected_msgs = manager.dialogues["hub"]["progress_2"]
        assert scene.dialogue.messages == expected_msgs

    def test_progress_3_after_three_puzzles(self):
        from game.scene_manager import SceneManager
        manager = SceneManager(screen)
        manager.complete_puzzle("caesar", 80)
        manager.complete_puzzle("base64", 70)
        manager.complete_puzzle("hash", 60)
        manager.load_scene("hub")
        scene = manager.current_scene
        assert scene.dialogue.active is True
        expected_msgs = manager.dialogues["hub"]["progress_3"]
        assert scene.dialogue.messages == expected_msgs

    def test_all_done_after_four_puzzles(self):
        from game.scene_manager import SceneManager
        manager = SceneManager(screen)
        manager.complete_puzzle("caesar", 80)
        manager.complete_puzzle("base64", 70)
        manager.complete_puzzle("hash", 60)
        manager.complete_puzzle("diffie_hellman", 90)
        manager.load_scene("hub")
        scene = manager.current_scene
        assert scene.dialogue.active is True
        expected_msgs = manager.dialogues["hub"]["all_done"]
        assert scene.dialogue.messages == expected_msgs

    def test_enter_dialogue_with_zero_puzzles(self):
        from game.scene_manager import SceneManager
        manager = SceneManager(screen)
        manager.load_scene("hub")
        scene = manager.current_scene
        assert scene.dialogue.active is True
        expected_msgs = manager.dialogues["hub"]["enter"]
        assert scene.dialogue.messages == expected_msgs


# ===================================================================
# 15. SCORE SYSTEM
# ===================================================================

class TestScoreSystem:
    def _get_manager(self):
        from game.scene_manager import SceneManager
        return SceneManager(screen)

    def test_complete_puzzle_tracked(self):
        manager = self._get_manager()
        manager.complete_puzzle("caesar", 85)
        assert manager.scores["caesar"] == 85
        assert "caesar" in manager.completed_scenes

    def test_all_puzzles_complete_false(self):
        manager = self._get_manager()
        manager.complete_puzzle("caesar", 85)
        manager.complete_puzzle("base64", 70)
        assert manager.all_puzzles_complete() is False

    def test_all_puzzles_complete_true(self):
        manager = self._get_manager()
        manager.complete_puzzle("caesar", 85)
        manager.complete_puzzle("base64", 70)
        manager.complete_puzzle("hash", 60)
        manager.complete_puzzle("diffie_hellman", 90)
        assert manager.all_puzzles_complete() is True

    def test_total_score(self):
        manager = self._get_manager()
        manager.complete_puzzle("caesar", 85)
        manager.complete_puzzle("base64", 70)
        manager.complete_puzzle("hash", 60)
        manager.complete_puzzle("diffie_hellman", 90)
        assert manager.total_score() == 305

    def test_total_score_empty(self):
        manager = self._get_manager()
        assert manager.total_score() == 0

    def test_overwrite_score(self):
        manager = self._get_manager()
        manager.complete_puzzle("caesar", 85)
        manager.complete_puzzle("caesar", 95)
        assert manager.scores["caesar"] == 95
        assert manager.total_score() == 95

    def test_completed_scenes_set_semantics(self):
        """Completing same puzzle twice should not duplicate in set."""
        manager = self._get_manager()
        manager.complete_puzzle("caesar", 80)
        manager.complete_puzzle("caesar", 90)
        assert len(manager.completed_scenes) == 1


# ===================================================================
# 16. SCENE TRANSITIONS
# ===================================================================

class TestSceneTransition:
    def _get_manager(self):
        from game.scene_manager import SceneManager
        return SceneManager(screen)

    def test_change_scene_triggers_transition(self):
        manager = self._get_manager()
        manager.load_scene("intro")
        manager.change_scene("hub")
        assert manager.transitioning is True
        assert manager.transition_phase == "out"
        assert manager.next_scene_name == "hub"

    def test_transition_completes_after_updates(self):
        manager = self._get_manager()
        manager.load_scene("intro")
        manager.change_scene("hub")

        dt = 1.0 / 60.0
        for _ in range(120):
            manager.update(dt)
            manager.draw()

        assert manager.transitioning is False
        from game.scene_hub import HubScene
        assert isinstance(manager.current_scene, HubScene)

    def test_transition_blocks_events(self):
        manager = self._get_manager()
        manager.load_scene("intro")
        manager.change_scene("hub")

        click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(640, 360), button=1)
        manager.handle_event(click)
        assert manager.transitioning is True

    def test_double_change_scene_blocked(self):
        manager = self._get_manager()
        manager.load_scene("intro")
        manager.change_scene("hub")
        manager.change_scene("caesar")
        assert manager.next_scene_name == "hub"

    def test_transition_alpha_starts_at_zero(self):
        manager = self._get_manager()
        manager.load_scene("intro")
        manager.change_scene("hub")
        assert manager.transition_alpha == 0

    def test_transition_phase_out_then_in(self):
        """Transition goes through 'out' phase, then 'in' phase."""
        manager = self._get_manager()
        manager.load_scene("intro")
        manager.change_scene("hub")

        dt = 1.0 / 60.0
        # Run until fade-out completes (alpha reaches 255)
        seen_in_phase = False
        for _ in range(200):
            manager.update(dt)
            manager.draw()
            if manager.transition_phase == "in":
                seen_in_phase = True
                break

        assert seen_in_phase, "Never reached 'in' phase of transition"


# ===================================================================
# ADDITIONAL: HUD tests
# ===================================================================

class TestHUD:
    def test_hud_creation(self):
        from game.ui.hud import HUD
        hud = HUD()
        assert hud.height == 40

    def test_hud_set_info(self):
        from game.ui.hud import HUD
        hud = HUD()
        hud.set_info(scene_name="TEST", layer_text="L1")
        assert hud.scene_name == "TEST"
        assert hud.layer_text == "L1"

    def test_hud_draw_no_crash(self):
        from game.ui.hud import HUD
        hud = HUD()
        hud.set_info(scene_name="TEST", layer_text="LAYER")
        hud.draw(screen)


# ===================================================================
# ADDITIONAL: Data files integrity
# ===================================================================

class TestDataFiles:
    def test_puzzles_json_loads(self):
        with open(os.path.join(PROJECT_ROOT, "data", "puzzles.json"), "r") as f:
            data = json.load(f)
        assert "caesar" in data
        assert "base64" in data
        assert "hash" in data
        assert "diffie_hellman" in data

    def test_dialogues_json_loads(self):
        with open(os.path.join(PROJECT_ROOT, "data", "dialogues.json"), "r") as f:
            data = json.load(f)
        for scene in ["intro", "hub", "caesar", "base64", "hash",
                      "diffie_hellman", "ending"]:
            assert scene in data, f"Missing dialogue for scene: {scene}"

    def test_puzzle_caesar_structure(self):
        with open(os.path.join(PROJECT_ROOT, "data", "puzzles.json"), "r") as f:
            data = json.load(f)
        c = data["caesar"]
        assert "cipher_text" in c
        assert "correct_shift" in c
        assert "plain_text" in c
        assert "hints" in c
        assert len(c["hints"]) == 3

    def test_puzzle_base64_structure(self):
        with open(os.path.join(PROJECT_ROOT, "data", "puzzles.json"), "r") as f:
            data = json.load(f)
        b = data["base64"]
        assert "blocks" in b
        assert len(b["blocks"]) == 4
        assert "decoded" in b

    def test_puzzle_dh_structure(self):
        with open(os.path.join(PROJECT_ROOT, "data", "puzzles.json"), "r") as f:
            data = json.load(f)
        d = data["diffie_hellman"]
        assert "g" in d
        assert "p" in d
        assert "b_secret" in d

    def test_puzzle_hash_structure(self):
        with open(os.path.join(PROJECT_ROOT, "data", "puzzles.json"), "r") as f:
            data = json.load(f)
        h = data["hash"]
        assert "round_1" in h
        assert "round_2" in h
        assert "round_3" in h
        assert "candidates" in h["round_1"]
        assert len(h["round_1"]["candidates"]) == 5

    def test_all_dialogue_scenes_have_enter(self):
        """Every puzzle scene dialogue should have an 'enter' key."""
        with open(os.path.join(PROJECT_ROOT, "data", "dialogues.json"), "r") as f:
            data = json.load(f)
        for scene in ["caesar", "base64", "hash", "diffie_hellman"]:
            assert "enter" in data[scene], f"Missing 'enter' dialogue for {scene}"
            assert len(data[scene]["enter"]) > 0

    def test_all_dialogue_scenes_have_success(self):
        """Every puzzle scene dialogue should have a 'success' key."""
        with open(os.path.join(PROJECT_ROOT, "data", "dialogues.json"), "r") as f:
            data = json.load(f)
        for scene in ["caesar", "base64", "hash", "diffie_hellman"]:
            assert "success" in data[scene], f"Missing 'success' dialogue for {scene}"
