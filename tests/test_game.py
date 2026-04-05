"""
Comprehensive headless tests for DEADLOCK game.
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
        for cls in [IntroScene, HubScene, CaesarScene, Base64Scene, HashScene, DHScene, EndingScene]:
            assert callable(cls)

    def test_import_ui(self):
        from game.ui.dialogue import DialogueBox
        from game.ui.hud import HUD
        assert callable(DialogueBox)
        assert callable(HUD)


# ===================================================================
# 2. SCENE INSTANTIATION
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
# 3. SCENE SIMULATION (update, draw, events)
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

        dt = 1.0 / 60.0  # ~60fps

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
# 4. CAESAR PUZZLE LOGIC
# ===================================================================

class TestCaesarLogic:
    def test_decrypt_correct_shift(self):
        """Verify decrypt_caesar(cipher_text, correct_shift) == plain_text."""
        from crypto.caesar import decrypt_caesar
        with open(os.path.join(PROJECT_ROOT, "data", "puzzles.json"), "r") as f:
            puzzles = json.load(f)
        caesar = puzzles["caesar"]
        result = decrypt_caesar(caesar["cipher_text"], caesar["correct_shift"])
        assert result.upper() == caesar["plain_text"].upper()

    def test_all_26_shifts_produce_valid_output(self):
        """Test that all 26 shifts produce valid string output."""
        from crypto.caesar import decrypt_caesar
        cipher = "PHHW PH"
        for shift in range(26):
            result = decrypt_caesar(cipher, shift)
            assert isinstance(result, str)
            assert len(result) == len(cipher)

    def test_encrypt_then_decrypt_roundtrip(self):
        """Encrypt then decrypt should return original text."""
        from crypto.caesar import encrypt_caesar, decrypt_caesar
        original = "Hello World"
        for shift in range(26):
            encrypted = encrypt_caesar(original, shift)
            decrypted = decrypt_caesar(encrypted, shift)
            assert decrypted == original

    def test_non_alpha_preserved(self):
        """Non-alphabetic characters should be preserved."""
        from crypto.caesar import encrypt_caesar
        result = encrypt_caesar("AB 12!?", 3)
        assert result[2] == " "
        assert result[3] == "1"
        assert result[4] == "2"
        assert result[5] == "!"

    def test_shift_zero_identity(self):
        """Shift of 0 should return the same text."""
        from crypto.caesar import decrypt_caesar
        text = "PHHW PH"
        assert decrypt_caesar(text, 0) == text

    def test_shift_26_identity(self):
        """Shift of 26 should return the same text (full cycle)."""
        from crypto.caesar import decrypt_caesar
        text = "PHHW PH"
        assert decrypt_caesar(text, 26) == text


# ===================================================================
# 5. BASE64 PUZZLE LOGIC
# ===================================================================

class TestBase64Logic:
    def test_blocks_correct_order_decodes(self):
        """Blocks in correct order should decode to 'Hello World!'."""
        from crypto.b64_utils import decode_b64
        with open(os.path.join(PROJECT_ROOT, "data", "puzzles.json"), "r") as f:
            puzzles = json.load(f)
        b64 = puzzles["base64"]
        full_encoded = "".join(b64["blocks"])
        result = decode_b64(full_encoded)
        assert result == b64["decoded"], f"Expected '{b64['decoded']}', got '{result}'"

    def test_full_encoded_matches(self):
        """Concatenated blocks should match the 'encoded' field."""
        with open(os.path.join(PROJECT_ROOT, "data", "puzzles.json"), "r") as f:
            puzzles = json.load(f)
        b64 = puzzles["base64"]
        assert "".join(b64["blocks"]) == b64["encoded"]

    def test_decode_partial_all_slots(self):
        """decode_partial with all slots filled should decode correctly."""
        from crypto.b64_utils import decode_partial
        slots = ["SGVs", "bG8g", "V29y", "bGQh"]
        result = decode_partial(slots)
        assert result == "Hello World!"

    def test_decode_partial_none_slots(self):
        """decode_partial with None slots should handle gracefully."""
        from crypto.b64_utils import decode_partial
        result = decode_partial([None, None, None, None])
        # Should not crash; result is whatever decoding spaces produces
        assert isinstance(result, str)

    def test_decode_partial_mixed_slots(self):
        """decode_partial with some None slots should not crash."""
        from crypto.b64_utils import decode_partial
        result = decode_partial(["SGVs", None, "V29y", None])
        assert isinstance(result, str)

    def test_encode_decode_roundtrip(self):
        """Encoding then decoding should return original."""
        from crypto.b64_utils import encode_b64, decode_b64
        original = "Hello World!"
        assert decode_b64(encode_b64(original)) == original


# ===================================================================
# 6. HASH PUZZLE LOGIC
# ===================================================================

class TestHashLogic:
    CANDIDATES = ["password", "123456", "qwerty", "letmein", "deadlock"]

    def test_sha256_short_consistent(self):
        """sha256_short should produce consistent hashes for all candidates."""
        from crypto.hash_utils import sha256_short
        for word in self.CANDIDATES:
            h1 = sha256_short(word)
            h2 = sha256_short(word)
            assert h1 == h2, f"Inconsistent hash for '{word}'"
            assert len(h1) == 16, f"Expected 16 chars, got {len(h1)}"
            assert all(c in "0123456789abcdef" for c in h1)

    def test_sha256_short_matches_hashlib(self):
        """sha256_short should match hashlib.sha256 first 16 chars."""
        from crypto.hash_utils import sha256_short
        for word in self.CANDIDATES:
            expected = hashlib.sha256(word.encode()).hexdigest()[:16]
            assert sha256_short(word) == expected

    def test_build_rainbow_table(self):
        """build_rainbow_table should return dict with all candidates."""
        from crypto.hash_utils import build_rainbow_table
        table = build_rainbow_table(self.CANDIDATES)
        assert isinstance(table, dict)
        assert len(table) == len(self.CANDIDATES)
        for word in self.CANDIDATES:
            assert word in table
            assert isinstance(table[word], str)
            assert len(table[word]) == 16

    def test_all_hashes_unique(self):
        """All candidate hashes should be unique."""
        from crypto.hash_utils import build_rainbow_table
        table = build_rainbow_table(self.CANDIDATES)
        hashes = list(table.values())
        assert len(set(hashes)) == len(hashes), "Duplicate hashes found"

    def test_sha256_full(self):
        """sha256_full should return 64-char hex string."""
        from crypto.hash_utils import sha256_full
        result = sha256_full("test")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)


# ===================================================================
# 7. DIFFIE-HELLMAN PUZZLE LOGIC
# ===================================================================

class TestDiffieHellmanLogic:
    def test_dh_public_basic(self):
        """dh_public should compute g^secret mod p."""
        from crypto.dh_utils import dh_public
        # 5^7 mod 23 = 17
        assert dh_public(5, 23, 7) == pow(5, 7, 23)

    def test_dh_shared_key_matching(self):
        """Both sides should compute the same shared key for any 'a' value 1-20."""
        from crypto.dh_utils import dh_public, dh_shared_key
        g, p = 5, 23
        b_secret = 15
        b_public = dh_public(g, p, b_secret)

        for a in range(1, 21):
            a_public = dh_public(g, p, a)
            # Player computes: B^a mod p
            key_player = dh_shared_key(b_public, p, a)
            # Other side computes: A^b mod p
            key_other = dh_shared_key(a_public, p, b_secret)
            assert key_player == key_other, (
                f"Keys don't match for a={a}: player={key_player}, other={key_other}"
            )

    def test_dh_public_range(self):
        """Public values should be in range [0, p-1]."""
        from crypto.dh_utils import dh_public
        g, p = 5, 23
        for secret in range(1, 21):
            pub = dh_public(g, p, secret)
            assert 0 <= pub < p, f"Public value {pub} out of range for secret={secret}"

    def test_dh_different_secrets_same_key(self):
        """DH always produces matching shared keys regardless of a."""
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
        # Not all keys are the same (different 'a' values produce different shared keys)
        assert len(keys_set) > 1, "All secrets produce the same shared key, which is unexpected"


# ===================================================================
# 8. SCENE TRANSITION TEST
# ===================================================================

class TestSceneTransition:
    def _get_manager(self):
        from game.scene_manager import SceneManager
        return SceneManager(screen)

    def test_change_scene_triggers_transition(self):
        """change_scene should start a transition."""
        manager = self._get_manager()
        manager.load_scene("intro")
        manager.change_scene("hub")
        assert manager.transitioning is True
        assert manager.transition_phase == "out"
        assert manager.next_scene_name == "hub"

    def test_transition_completes_after_updates(self):
        """Running enough update frames should complete the transition."""
        manager = self._get_manager()
        manager.load_scene("intro")
        manager.change_scene("hub")

        dt = 1.0 / 60.0
        # Run enough frames to complete fade-out and fade-in
        for _ in range(120):
            manager.update(dt)
            manager.draw()

        assert manager.transitioning is False
        from game.scene_hub import HubScene
        assert isinstance(manager.current_scene, HubScene)

    def test_transition_blocks_events(self):
        """Events should be blocked during transition."""
        manager = self._get_manager()
        manager.load_scene("intro")
        manager.change_scene("hub")

        # Transition is active - events should be ignored
        click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(640, 360), button=1)
        manager.handle_event(click)
        # Should not crash and transition should still be active
        assert manager.transitioning is True

    def test_double_change_scene_blocked(self):
        """Calling change_scene during transition should be blocked."""
        manager = self._get_manager()
        manager.load_scene("intro")
        manager.change_scene("hub")
        # Try to change again
        manager.change_scene("caesar")
        # next_scene_name should still be "hub"
        assert manager.next_scene_name == "hub"


# ===================================================================
# 9. SCORE SYSTEM TEST
# ===================================================================

class TestScoreSystem:
    def _get_manager(self):
        from game.scene_manager import SceneManager
        return SceneManager(screen)

    def test_complete_puzzle_tracked(self):
        """complete_puzzle should track the score."""
        manager = self._get_manager()
        manager.complete_puzzle("caesar", 85)
        assert manager.scores["caesar"] == 85
        assert "caesar" in manager.completed_scenes

    def test_all_puzzles_complete_false(self):
        """all_puzzles_complete should be False with only some puzzles done."""
        manager = self._get_manager()
        manager.complete_puzzle("caesar", 85)
        manager.complete_puzzle("base64", 70)
        assert manager.all_puzzles_complete() is False

    def test_all_puzzles_complete_true(self):
        """all_puzzles_complete should be True after all 4 puzzles."""
        manager = self._get_manager()
        manager.complete_puzzle("caesar", 85)
        manager.complete_puzzle("base64", 70)
        manager.complete_puzzle("hash", 60)
        manager.complete_puzzle("diffie_hellman", 90)
        assert manager.all_puzzles_complete() is True

    def test_total_score(self):
        """total_score should sum all puzzle scores."""
        manager = self._get_manager()
        manager.complete_puzzle("caesar", 85)
        manager.complete_puzzle("base64", 70)
        manager.complete_puzzle("hash", 60)
        manager.complete_puzzle("diffie_hellman", 90)
        assert manager.total_score() == 305

    def test_total_score_empty(self):
        """total_score should be 0 with no puzzles completed."""
        manager = self._get_manager()
        assert manager.total_score() == 0

    def test_overwrite_score(self):
        """Completing the same puzzle again should overwrite the score."""
        manager = self._get_manager()
        manager.complete_puzzle("caesar", 85)
        manager.complete_puzzle("caesar", 95)
        assert manager.scores["caesar"] == 95
        assert manager.total_score() == 95


# ===================================================================
# 10. DIALOGUE BOX TEST
# ===================================================================

class TestDialogueBox:
    def test_initial_state(self):
        """DialogueBox should start inactive."""
        from game.ui.dialogue import DialogueBox
        db = DialogueBox()
        assert db.active is False
        assert db.finished is False

    def test_show_activates(self):
        """show() should activate the dialogue."""
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
        """update() should advance char_index over time."""
        from game.ui.dialogue import DialogueBox
        db = DialogueBox()
        msgs = [{"speaker": "TEST", "text": "Hello World"}]
        db.show(msgs)

        # Run several updates
        for _ in range(50):
            db.update(0.05)

        # char_index should have advanced
        assert db.char_index > 0

    def test_advance_completes_text(self):
        """First advance() should complete the current message text."""
        from game.ui.dialogue import DialogueBox
        db = DialogueBox()
        msgs = [{"speaker": "TEST", "text": "Hello World"}]
        db.show(msgs)
        db.advance()
        # Should have completed the text
        assert db.char_index == len("Hello World")
        # Still active (need second advance to finish)
        assert db.active is True

    def test_advance_next_message(self):
        """Second advance() should move to next message or finish."""
        from game.ui.dialogue import DialogueBox
        db = DialogueBox()
        msgs = [
            {"speaker": "TEST", "text": "First"},
            {"speaker": "TEST", "text": "Second"},
        ]
        db.show(msgs)
        db.advance()  # complete text of first
        db.advance()  # move to second
        assert db.current_index == 1
        assert db.active is True

    def test_advance_through_all(self):
        """Advancing through all messages should deactivate dialogue."""
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
        """on_complete should be called when all messages are done."""
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
        """draw() should not crash in active or inactive states."""
        from game.ui.dialogue import DialogueBox
        db = DialogueBox()
        # Inactive draw
        db.draw(screen)

        # Active draw
        msgs = [{"speaker": "TEST", "text": "Hello"}]
        db.show(msgs)
        db.update(0.1)
        db.draw(screen)

    def test_handle_event_click_advances(self):
        """Clicking should advance the dialogue."""
        from game.ui.dialogue import DialogueBox
        db = DialogueBox()
        msgs = [{"speaker": "TEST", "text": "Click me"}]
        db.show(msgs)

        click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(100, 100), button=1)
        result = db.handle_event(click)
        assert result is True
        # Text should be completed
        assert db.char_index == len("Click me")


# ===================================================================
# ADDITIONAL: HUD test
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
        for scene in ["intro", "hub", "caesar", "base64", "hash", "diffie_hellman", "ending"]:
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
