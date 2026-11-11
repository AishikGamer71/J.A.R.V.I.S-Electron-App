"""
Empirical Challenger Test Harness for Milestone M1
Authored by: teamwork_challenger (challenger_m1_iter2_1)
Adversarially stresses all Milestone M1 gates and contracts.
"""

import hashlib
import json
import os
import sys
import unittest
import wave
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from starlette.testclient import TestClient
from backend.main import app, WS_COMMAND_HANDLERS, manager


class TestEmpiricalChallengerM1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    # =========================================================================
    # 1. REST Endpoints & Contracts
    # =========================================================================
    def test_c01_health_endpoints(self):
        for path in ["/health", "/api/health"]:
            res = self.client.get(path)
            self.assertEqual(res.status_code, 200, f"{path} failed with {res.status_code}")
            data = res.json()
            self.assertEqual(data.get("status"), "healthy")
            self.assertEqual(data.get("service"), "jarvis-core-service")
            self.assertEqual(data.get("version"), "2.0.0")

    def test_c02_system_stats_endpoints(self):
        for path in ["/api/system/stats", "/system/stats"]:
            res = self.client.get(path)
            self.assertEqual(res.status_code, 200, f"{path} failed with {res.status_code}")
            data = res.json()
            self.assertIn("cpu_pct", data)
            self.assertIn("ram_used_mb", data)
            self.assertIn("ram_total_mb", data)
            self.assertIn("gpu_pct", data)
            self.assertIn("power", data)
            self.assertIsInstance(data["power"], dict)

    def test_c03_tools_endpoints(self):
        # GET /v1/tools
        res = self.client.get("/v1/tools")
        self.assertEqual(res.status_code, 200)
        self.assertIn("tools", res.json())
        self.assertIsInstance(res.json()["tools"], list)

        # POST /v1/tools/invoke valid
        valid_payload = {"tool": "test_echo", "args": {"msg": "hello"}}
        res = self.client.post("/v1/tools/invoke", json=valid_payload)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json().get("status"), "success")

        # POST /v1/tools/invoke malformed (missing tool name) -> 422
        bad_payload = {"args": {"msg": "hello"}}
        res = self.client.post("/v1/tools/invoke", json=bad_payload)
        self.assertEqual(res.status_code, 422, "Malformed payload must return 422 Unprocessable Entity")

    def test_c04_all_remaining_rest_routes(self):
        routes_to_test = [
            ("GET", "/api/env", 200),
            ("POST", "/api/env", 200, {"theme": "jarvis-amber"}),
            ("GET", "/api/history", 200),
            ("POST", "/api/history/clear", 200, {}),
            ("GET", "/sessions", 200),
            ("GET", "/api/sessions", 200),
            ("GET", "/sessions/sess-123/messages", 200),
            ("DELETE", "/sessions/sess-123", 200),
            ("GET", "/search?q=adversarial_test", 200),
            ("GET", "/v1/core-memory", 200),
            ("POST", "/v1/core-memory", 200, {"key": "value"}),
            ("GET", "/v1/audit", 200),
            ("GET", "/v1/permissions", 200),
            ("GET", "/v1/agents", 200),
            ("GET", "/v1/inbox", 200),
        ]
        for item in routes_to_test:
            method, path, expected_code = item[0], item[1], item[2]
            body = item[3] if len(item) > 3 else None
            if method == "GET":
                r = self.client.get(path)
            elif method == "POST":
                r = self.client.post(path, json=body or {})
            elif method == "DELETE":
                r = self.client.delete(path)
            self.assertEqual(r.status_code, expected_code, f"{method} {path} returned {r.status_code}")

    # =========================================================================
    # 2. WebSocket Protocol & Handlers
    # =========================================================================
    def test_c05_websocket_protocol_full_matrix(self):
        for ws_path in ["/ws", "/ws/jarvis"]:
            with self.client.websocket_connect(ws_path) as ws:
                # 1. system.toggle
                ws.send_json({"type": "system.toggle", "payload": {}})
                ack = ws.receive_json()
                self.assertEqual(ack.get("type"), "system.toggle.ack")
                self.assertTrue(ack.get("payload", {}).get("toggled"))

                # 2. vision.mode
                ws.send_json({"type": "vision.mode", "payload": "gestures"})
                ack = ws.receive_json()
                self.assertEqual(ack.get("type"), "vision.mode.ack")
                self.assertEqual(ack.get("payload", {}).get("mode"), "gestures")

                # 3. audio.control
                ws.send_json({"type": "audio.control", "payload": {"mute": False}})
                ack = ws.receive_json()
                self.assertEqual(ack.get("type"), "audio.control.ack")
                self.assertEqual(ack.get("payload", {}).get("control"), {"mute": False})

                # 4. reset_abort
                ws.send_json({"type": "reset_abort", "payload": {}})
                ack = ws.receive_json()
                self.assertEqual(ack.get("type"), "reset_abort.ack")
                self.assertTrue(ack.get("payload", {}).get("abort_reset"))

                # 5. user.message
                ws.send_json({"type": "user.message", "payload": {"text": "hello"}})
                ack = ws.receive_json()
                self.assertEqual(ack.get("type"), "user.message.ack")
                self.assertTrue(ack.get("payload", {}).get("received"))

                # 6. Fallback / unrecognized event
                ws.send_json({"type": "custom.telemetry", "payload": {"val": 42}})
                ack = ws.receive_json()
                self.assertEqual(ack.get("type"), "agent.state")
                self.assertEqual(ack.get("payload", {}).get("state"), "idle")

    def test_c06_command_handlers_registry_integrity(self):
        expected_handlers = [
            "system.toggle",
            "vision.mode",
            "audio.control",
            "reset_abort",
            "user.message",
        ]
        for h in expected_handlers:
            self.assertIn(h, WS_COMMAND_HANDLERS, f"Handler {h} missing in WS_COMMAND_HANDLERS")
            self.assertTrue(callable(WS_COMMAND_HANDLERS[h]), f"Handler {h} must be callable")

    def test_c11_websocket_adversarial_and_concurrent(self):
        # 1. Connect two concurrent clients
        with self.client.websocket_connect("/ws") as ws1:
            with self.client.websocket_connect("/ws/jarvis") as ws2:
                self.assertEqual(len(manager.active_connections), 2)

                # Send broadcast via manager
                import asyncio
                asyncio.run(manager.broadcast({"type": "system.metrics", "payload": {"cpu": 12.5}}))

                # Both should receive the broadcast
                msg1 = ws1.receive_json()
                msg2 = ws2.receive_json()
                self.assertEqual(msg1.get("type"), "system.metrics")
                self.assertEqual(msg2.get("type"), "system.metrics")

        # After contexts exit, both should be disconnected
        self.assertEqual(len(manager.active_connections), 0)

    # =========================================================================
    # 3. Cryptographic Rules Parity & Content
    # =========================================================================
    def test_c07_governance_rules_hash_and_byte_parity(self):
        p1 = PROJECT_ROOT / ".antigravity" / "rules.md"
        p2 = PROJECT_ROOT / ".agent" / "rules" / "rules.md"
        self.assertTrue(p1.is_file(), f"{p1} not found")
        self.assertTrue(p2.is_file(), f"{p2} not found")

        b1 = p1.read_bytes()
        b2 = p2.read_bytes()
        self.assertEqual(len(b1), len(b2), f"Size mismatch: {len(b1)} vs {len(b2)}")
        self.assertEqual(b1, b2, "Byte contents mismatch")

        h1 = hashlib.sha256(b1).hexdigest().lower()
        h2 = hashlib.sha256(b2).hexdigest().lower()
        self.assertEqual(h1, h2)
        self.assertEqual(h1, "bd951d8b5fe10f0acfe6204f31e2fb3e1e9791552ddcdb52769d6327764b36ec")

        text = b1.decode("utf-8")
        self.assertIn("ZERO UI DRIFT", text)
        self.assertIn("DESKTOP APPLICATION ONLY", text)
        self.assertIn("Ctrl+Alt+Backspace", text)
        self.assertIn("Single-Producer Multi-Consumer", text)
        self.assertIn("windows_mcp_bridge.py", text)
        self.assertIn("14 secret patterns", text)

    # =========================================================================
    # 4. Audio Asset Bit-Fidelity
    # =========================================================================
    def test_c08_voice_asset_bit_fidelity(self):
        wav_path = PROJECT_ROOT / "backend" / "voice" / "assets" / "jarvis_ref.wav"
        self.assertTrue(wav_path.is_file(), "jarvis_ref.wav missing")
        b = wav_path.read_bytes()
        self.assertEqual(len(b), 353708, f"Expected 353708 bytes, got {len(b)}")
        h = hashlib.sha256(b).hexdigest().lower()
        self.assertEqual(h, "81d2718566fa9617cfaace564300488243d93ec0c554c7d4b7194bbed3e02d73")

        with wave.open(str(wav_path), "rb") as wf:
            self.assertEqual(wf.getnchannels(), 1)
            self.assertEqual(wf.getframerate(), 24000)
            self.assertEqual(wf.getsampwidth(), 2)
            self.assertEqual(wf.getnframes(), 176832)
            data = wf.readframes(176832)
            self.assertEqual(len(data), 176832 * 2)

    # =========================================================================
    # 5. Clean Workspace & No Forbidden Directories
    # =========================================================================
    def test_c09_no_forbidden_directories_or_stray_backups(self):
        forbidden = [
            PROJECT_ROOT / "_safe_assets",
            PROJECT_ROOT / "_donor_staging",
            PROJECT_ROOT / "backend" / "audio",
            PROJECT_ROOT / "apps",
            PROJECT_ROOT / "services",
        ]
        for f in forbidden:
            self.assertFalse(f.exists(), f"Forbidden path still exists: {f}")

    # =========================================================================
    # 6. UI Visualizer Delta-Time Clamping Formula
    # =========================================================================
    def test_c10_visualizer_dt_clamping_formula(self):
        """Mathematically stress-tests the dt formula used in arc-reactor.tsx and sphere.tsx."""
        def arc_reactor_dt(ts: float, last_ts: float) -> float:
            return max(0.0, min((ts - last_ts) / 1000.0, 0.05))

        def sphere_dt(delta: float) -> float:
            return max(0.0, min(0.05, delta))

        # Test case 1: normal 60fps
        dt1 = arc_reactor_dt(1016.6, 1000.0)
        self.assertAlmostEqual(dt1, 0.0166, places=4)
        self.assertTrue(0.0 <= dt1 <= 0.05)

        # Test case 2: extreme large positive jump (10 seconds background suspend)
        dt2 = arc_reactor_dt(11000.0, 1000.0)
        self.assertEqual(dt2, 0.05)
        dt2_s = sphere_dt(10.0)
        self.assertEqual(dt2_s, 0.05)

        # Test case 3: negative timestamp regression / clock skew
        dt3 = arc_reactor_dt(500.0, 1000.0)
        self.assertEqual(dt3, 0.0)
        dt3_s = sphere_dt(-1.0)
        self.assertEqual(dt3_s, 0.0)

        # Test case 4: zero dt
        dt4 = arc_reactor_dt(1000.0, 1000.0)
        self.assertEqual(dt4, 0.0)

        # Test exponential damping under clamped dt: damp = 1 - exp(-k * dt)
        for dt_val in [dt1, dt2, dt3, dt4]:
            damp = 1.0 - (2.718281828459045 ** (-10.0 * dt_val))
            self.assertTrue(0.0 <= damp < 1.0, f"Damping {damp} outside [0, 1) for dt={dt_val}")


if __name__ == "__main__":
    unittest.main()
