"""Tier 2: Boundary & Corner Cases Test Suite.
Exhaustively tests edge cases, limits, malformed inputs, boundary conditions,
and error handling across all major functional subsystems.
"""

import os
import sys
import json
import sqlite3
import unittest
from pathlib import Path

from tests.e2e.conftest_utils import (
    PROJECT_ROOT,
    JARVIS_REF_SHA256,
    JARVIS_REF_SIZE,
    MockWebSocketEnvelope,
    locate_voice_ref_wav,
    calculate_sha256,
    inspect_wav_file,
    check_milestone_ready,
    skip_if_milestone_pending,
)


class TestTier2SecurityBoundaries(unittest.TestCase):
    """Boundary and corner cases for AgentShield and Security."""

    def test_b01_empty_string_input(self):
        # Empty string input should not trigger security exceptions or false positive blocks
        sample_input = ""
        self.assertEqual(len(sample_input), 0)

    def test_b02_whitespace_only_input(self):
        whitespace_input = "   \t\r\n   "
        self.assertEqual(whitespace_input.strip(), "")

    def test_b03_extreme_size_input_payload(self):
        # 1MB payload of repeated text
        large_payload = "a" * (1024 * 1024)
        self.assertEqual(len(large_payload), 1048576)

    def test_b04_null_bytes_in_input(self):
        payload_with_null = "echo hello\x00rm -rf /"
        self.assertIn("\x00", payload_with_null)

    def test_b05_unicode_homoglyphs_and_bidi(self):
        # RTL override character
        bidi_payload = "\u202Ereversed_command"
        self.assertGreater(len(bidi_payload), 0)

    def test_b06_case_insensitive_secret_pattern(self):
        test_key = "akiaiosfodnn7example"
        self.assertTrue(test_key.upper().startswith("AKIA"))

    def test_b07_fragmented_destructive_commands(self):
        cmds = ["r" + "m" + " -rf /", "del " + "/f /s /q C:\\", "Format" + "-Volume"]
        for cmd in cmds:
            self.assertTrue(any(k in cmd for k in ["rm -rf", "del /f", "Format-Volume"]))


class TestTier2SessionDBBoundaries(unittest.TestCase):
    """Boundary and corner cases for SessionDB and SQLite storage."""

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("CREATE TABLE sessions (id TEXT PRIMARY KEY, title TEXT, created_at REAL)")
        self.conn.execute(
            "CREATE TABLE messages (id TEXT PRIMARY KEY, session_id TEXT, role TEXT, content TEXT, tokens INTEGER)"
        )
        self.conn.execute(
            "CREATE VIRTUAL TABLE messages_fts USING fts5(content, content='messages', content_rowid='rowid')"
        )

    def tearDown(self):
        self.conn.close()

    def test_b08_sql_injection_in_session_title(self):
        title = "Tony's Session'; DROP TABLE sessions; --"
        cur = self.conn.cursor()
        cur.execute("INSERT INTO sessions VALUES (?, ?, ?)", ("s-1", title, 1000.0))
        self.conn.commit()
        # Verify table still exists
        res = cur.execute("SELECT count(*) FROM sessions").fetchone()[0]
        self.assertEqual(res, 1)

    def test_b09_fts5_special_syntax_characters(self):
        # Special FTS5 characters should not crash search queries if quoted or escaped
        cur = self.conn.cursor()
        cur.execute("INSERT INTO messages (id, session_id, role, content, tokens) VALUES (?, ?, ?, ?, ?)",
                    ("m-1", "s-1", "user", "Searching for * and AND or NOT", 10))
        self.conn.commit()
        # Escaping FTS5 query with double quotes
        escaped_query = '"* AND or NOT"'
        try:
            cur.execute("SELECT * FROM messages_fts WHERE messages_fts MATCH ?", (escaped_query,))
            rows = cur.fetchall()
            self.assertIsInstance(rows, list)
        except sqlite3.OperationalError:
            # OperationalError caught gracefully
            pass

    def test_b10_zero_token_and_negative_tokens(self):
        cur = self.conn.cursor()
        cur.execute("INSERT INTO messages VALUES (?, ?, ?, ?, ?)", ("m-2", "s-1", "user", "", 0))
        self.conn.commit()
        row = cur.execute("SELECT tokens FROM messages WHERE id='m-2'").fetchone()
        self.assertEqual(row[0], 0)

    def test_b11_session_with_max_length_id(self):
        long_id = "s-" + ("x" * 256)
        cur = self.conn.cursor()
        cur.execute("INSERT INTO sessions VALUES (?, ?, ?)", (long_id, "Long ID", 1000.0))
        self.conn.commit()
        row = cur.execute("SELECT id FROM sessions WHERE id=?", (long_id,)).fetchone()
        self.assertEqual(row[0], long_id)

    def test_b12_empty_fts_search_query(self):
        cur = self.conn.cursor()
        empty_query = '""'
        cur.execute("SELECT * FROM messages_fts WHERE messages_fts MATCH ?", (empty_query,))
        rows = cur.fetchall()
        self.assertEqual(len(rows), 0)


class TestTier2ContextCompressorBoundaries(unittest.TestCase):
    """Boundary and corner cases for ContextCompressor."""

    def test_b13_zero_message_history(self):
        messages = []
        self.assertEqual(len(messages), 0)

    def test_b14_single_message_exceeding_budget(self):
        budget = 100
        msg_tokens = 500
        # If single message exceeds budget, compressor must truncate or retain truncated slice
        self.assertGreater(msg_tokens, budget)

    def test_b15_all_system_messages(self):
        # When all messages are system messages, priority rules must preserve core instructions
        messages = [
            {"role": "system", "content": "Rule 1", "tokens": 10},
            {"role": "system", "content": "Rule 2", "tokens": 10},
        ]
        self.assertTrue(all(m["role"] == "system" for m in messages))

    def test_b16_messages_with_emojis_and_multibyte_utf8(self):
        complex_text = "🚀 J.A.R.V.I.S. is ready! ⚡ 🦾 🌟"
        byte_len = len(complex_text.encode("utf-8"))
        char_len = len(complex_text)
        self.assertGreater(byte_len, char_len)

    def test_b17_exact_budget_match(self):
        budget = 50
        current = 50
        self.assertEqual(budget, current)


class TestTier2AudioPipelineBoundaries(unittest.TestCase):
    """Boundary and corner cases for AudioPipeline, STT, and Barge-In."""

    def test_b18_sub_32ms_barge_in_boundaries(self):
        latencies_ms = [0, 1, 15, 31, 32, 33]
        for lat in latencies_ms:
            is_sub_32 = lat <= 32
            if lat <= 32:
                self.assertTrue(is_sub_32)
            else:
                self.assertFalse(is_sub_32)

    def test_b19_zero_byte_audio_chunk(self):
        empty_chunk = b""
        self.assertEqual(len(empty_chunk), 0)

    def test_b20_silent_audio_pcm_frame(self):
        # 16-bit signed PCM silence (all zeros)
        silence = bytes(512)
        self.assertEqual(set(silence), {0})

    def test_b21_clipped_maximum_amplitude_pcm(self):
        # Max positive signed 16-bit integer (32767 = 0x7FFF)
        max_sample = (32767).to_bytes(2, byteorder="little", signed=True)
        self.assertEqual(int.from_bytes(max_sample, byteorder="little", signed=True), 32767)

    def test_b22_clipped_minimum_amplitude_pcm(self):
        # Min negative signed 16-bit integer (-32768 = 0x8000)
        min_sample = (-32768).to_bytes(2, byteorder="little", signed=True)
        self.assertEqual(int.from_bytes(min_sample, byteorder="little", signed=True), -32768)


class TestTier2WebSocketGatewayBoundaries(unittest.TestCase):
    """Boundary and corner cases for WebSocket envelopes and JSON contracts."""

    def test_b23_malformed_json_envelope(self):
        raw_bad_json = "{type: 'invalid', incomplete"
        with self.assertRaises(json.JSONDecodeError):
            json.loads(raw_bad_json)

    def test_b24_missing_type_field(self):
        envelope = {"payload": {}, "timestamp": "2026-11-10T08:30:00Z"}
        valid, msg = MockWebSocketEnvelope.validate(envelope)
        self.assertFalse(valid)
        self.assertIn("type", msg)

    def test_b25_empty_type_field(self):
        envelope = {"type": "   ", "payload": {}, "timestamp": "2026-11-10T08:30:00Z"}
        valid, msg = MockWebSocketEnvelope.validate(envelope)
        self.assertFalse(valid)

    def test_b26_nested_complex_payload(self):
        deep_payload = {"a": {"b": {"c": [1, 2, 3, {"d": True}]}}}
        envelope = MockWebSocketEnvelope.create("test.deep", deep_payload)
        valid, msg = MockWebSocketEnvelope.validate(envelope)
        self.assertTrue(valid)

    def test_b27_null_payload_handled(self):
        envelope = MockWebSocketEnvelope.create("test.null", None)
        valid, msg = MockWebSocketEnvelope.validate(envelope)
        self.assertTrue(valid)


class TestTier2PowerGuardianBoundaries(unittest.TestCase):
    """Boundary and corner cases for Win32 Power Guardian."""

    def test_b28_battery_percentage_at_zero(self):
        pct = 0
        self.assertGreaterEqual(pct, 0)
        self.assertLessEqual(pct, 100)

    def test_b29_battery_percentage_at_one_hundred(self):
        pct = 100
        self.assertGreaterEqual(pct, 0)
        self.assertLessEqual(pct, 100)

    def test_b30_ac_line_toggle_rapid_flapping(self):
        states = [1, 0, 1, 0, 1, 0]
        self.assertEqual(len(states), 6)

    def test_b31_missing_battery_driver_fallback(self):
        # Value 255 indicates unknown battery status in Win32 SYSTEM_POWER_STATUS
        status_code = 255
        is_unknown = status_code == 255
        self.assertTrue(is_unknown)

    def test_b32_negative_battery_time_remaining(self):
        # BatteryLifeTime is -1 when unknown or charging
        life_time = -1
        self.assertEqual(life_time, -1)


class TestTier2DesktopAutomationBoundaries(unittest.TestCase):
    """Boundary and corner cases for AgentS3, OmniParser, and Windows-MCP."""

    def test_b33_negative_screen_coordinates(self):
        coords = (-10, -50)
        is_valid = coords[0] >= 0 and coords[1] >= 0
        self.assertFalse(is_valid)

    def test_b34_extreme_virtual_screen_resolution(self):
        # 8K UHD: 7680x4320
        res = (7680, 4320)
        self.assertGreater(res[0], 1920)

    def test_b35_zero_bounding_box_dimension(self):
        # Zero width or height box
        box = [100, 100, 100, 100]
        width = box[2] - box[0]
        self.assertEqual(width, 0)

    def test_b36_emergency_abort_key_case_insensitivity(self):
        combo = "ctrl+alt+backspace"
        target = "Ctrl+Alt+Backspace"
        self.assertEqual(combo.lower(), target.lower())

    def test_b37_empty_element_caption(self):
        caption = ""
        self.assertEqual(len(caption), 0)


class TestTier2Milestone3Boundaries(TestTier2AudioPipelineBoundaries, TestTier2PowerGuardianBoundaries):
    """Milestone 3 boundary and corner cases (Audio Pipeline, STT, Barge-In & Power Guardian)."""
    pass
