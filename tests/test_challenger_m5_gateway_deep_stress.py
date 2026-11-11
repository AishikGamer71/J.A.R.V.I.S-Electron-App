"""
tests/test_challenger_m5_gateway_deep_stress.py
================================================
Empirical Challenger Deep Stress Suite for FastAPI Gateway & WebSockets.
Targeting: Milestone M5 Iteration 2 Gateway resilience, /search, /v1/permissions, and /ws.
Authored by challenger_m5_iter2_2.
"""

import json
import threading
import time
import unittest
from typing import Any, Dict, List

from fastapi.testclient import TestClient
from backend.main import app, hermes_brain, tool_dispatcher, hybrid_memory, state_db


class TestGatewayAdversarialStress(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app, raise_server_exceptions=False)

    def test_search_adversarial_queries(self):
        """Stress test /search endpoint with various query shapes."""
        adversarial_queries = [
            "",  # Empty query
            "   ",  # Whitespace only
            "a" * 5000,  # Extremely long query
            "' OR '1'='1",  # SQL injection syntax
            '"; DROP TABLE sessions; --',  # DDL injection attempt
            ".*+?^${}()|[]\\",  # Regex metacharacters
            "日本語 / ⚡ / \U0001f916 JARVIS",  # Unicode and emojis
            "<script>alert('xss')</script>",  # XSS probe
            "1234567890",  # Numeric string
            "\x00\x01\x02",  # Control characters
        ]

        for q in adversarial_queries:
            with self.subTest(query=q[:30]):
                resp = self.client.get("/search", params={"q": q})
                self.assertEqual(
                    resp.status_code,
                    200,
                    f"Query {q!r} failed with status {resp.status_code}: {resp.text}",
                )
                data = resp.json()
                self.assertIn("query", data)
                self.assertIn("results", data)
                self.assertIn("hybrid_hits", data)
                self.assertIsInstance(data["results"], list)
                self.assertIsInstance(data["hybrid_hits"], list)

    def test_search_with_unexpected_query_params(self):
        """Verify /search ignores extraneous parameters without error."""
        resp = self.client.get("/search", params={"q": "core", "limit": 100, "offset": 10, "foo": "bar"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("results", data)
        self.assertIn("hybrid_hits", data)

    def test_permissions_endpoint_resilience(self):
        """Verify /v1/permissions returns all tools with valid scope and risk_level."""
        resp = self.client.get("/v1/permissions")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("permissions", data)
        perms = data["permissions"]
        self.assertIsInstance(perms, dict)

        tools = tool_dispatcher.get_tool_definitions()
        for t in tools:
            name = t.get("name") or t.get("function", {}).get("name")
            if name:
                self.assertIn(name, perms, f"Tool {name} missing from /v1/permissions")
                p = perms[name]
                self.assertIn("scope", p)
                self.assertIn("granted", p)
                self.assertIn("risk_level", p)
                self.assertIn(p["risk_level"], ("LOW", "MEDIUM", "HIGH", "CRITICAL"))

    def test_permissions_with_unusual_tool_formats(self):
        """Verify get_permissions handles unconventional tool schema dictionaries gracefully."""
        # Temporarily inject irregular tool definition into tool_dispatcher registry
        test_tool_name = "test_adversarial_tool_minimal"
        try:
            tool_dispatcher.register_tool(
                name=test_tool_name,
                handler=lambda args: "ok",
                description="Adversarial minimal tool",
            )
            resp = self.client.get("/v1/permissions")
            self.assertEqual(resp.status_code, 200)
            perms = resp.json().get("permissions", {})
            self.assertIn(test_tool_name, perms)
            self.assertEqual(perms[test_tool_name]["risk_level"], "LOW")
        finally:
            tool_dispatcher._registry.pop(test_tool_name, None)
            tool_dispatcher._tool_descriptions.pop(test_tool_name, None)

    def test_permissions_grant_and_revoke_edge_cases(self):
        """Test grant and revoke endpoints with boundary payloads."""
        # Standard grant
        r1 = self.client.post("/v1/permissions/grant", json={"tool": "echo", "scope": "*"})
        self.assertEqual(r1.status_code, 200)
        self.assertTrue(r1.json().get("success"))

        # Empty tool name
        r2 = self.client.post("/v1/permissions/grant", json={"tool": "", "scope": "read"})
        self.assertEqual(r2.status_code, 200)

        # Standard revoke
        r3 = self.client.post("/v1/permissions/revoke", json={"tool": "echo", "scope": "*"})
        self.assertEqual(r3.status_code, 200)
        self.assertTrue(r3.json().get("success"))


class TestWebSocketDualPathDeepStress(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_dual_websocket_burst_traffic(self):
        """Send a burst of rapid sequential messages across both /ws and /ws/jarvis."""
        for endpoint in ("/ws", "/ws/jarvis"):
            with self.subTest(endpoint=endpoint):
                with self.client.websocket_connect(endpoint) as ws:
                    for i in range(25):
                        req_id = f"burst-{endpoint.replace('/', '')}-{i}"
                        ws.send_json({
                            "type": "system.toggle",
                            "request_id": req_id,
                            "payload": {"index": i},
                        })
                        resp = ws.receive_json()
                        self.assertEqual(resp.get("type"), "system.toggle.ack")
                        self.assertEqual(resp.get("request_id"), req_id)

    def test_websocket_barge_in_and_voice_stop(self):
        """Verify barge_in, voice:stop, and audio.control cancel_speech abort hermes_brain."""
        for abort_cmd in [
            {"type": "reset_abort"},
            {"type": "voice:stop"},
            {"type": "barge_in"},
            {"type": "audio.control", "payload": {"action": "cancel_speech"}},
        ]:
            with self.subTest(cmd=abort_cmd["type"]):
                with self.client.websocket_connect("/ws") as ws:
                    hermes_brain.reset_interrupt()
                    self.assertFalse(hermes_brain.is_interrupted)

                    ws.send_json(abort_cmd)
                    resp = ws.receive_json()
                    self.assertEqual(resp.get("type"), "audio.control.ack")
                    self.assertEqual(resp.get("payload", {}).get("status"), "interrupted")
                    self.assertTrue(hermes_brain.is_interrupted)
                    hermes_brain.reset_interrupt()

    def test_websocket_user_message_payload_variants(self):
        """Verify user.message handles string, dict, or top-level message formats."""
        variants = [
            {"type": "user.message", "payload": {"content": "Ping test 1", "session_id": "test-s1"}},
            {"type": "user.message", "payload": "Ping test 2", "session_id": "test-s2"},
            {"type": "user.message", "content": "Ping test 3", "session_id": "test-s3"},
            {"type": "chat:send", "payload": {"text": "Ping test 4", "sessionId": "test-s4"}},
        ]

        with self.client.websocket_connect("/ws") as ws:
            for payload in variants:
                ws.send_json(payload)
                # Consume until agent_response
                got_response = False
                for _ in range(100):
                    frame = ws.receive_json()
                    if frame.get("type") == "agent_response":
                        got_response = True
                        break
                self.assertTrue(got_response, f"Failed to get agent_response for variant {payload}")

    def test_websocket_unknown_commands_fallback_echo(self):
        """Unknown message types must not crash the connection; returns fallback agent.state."""
        with self.client.websocket_connect("/ws") as ws:
            ws.send_json({
                "type": "custom.unknown.action",
                "request_id": "unknown-1",
                "payload": {"arbitrary": 123},
            })
            resp = ws.receive_json()
            self.assertEqual(resp.get("type"), "agent.state")
            self.assertEqual(resp.get("payload", {}).get("state"), "idle")
            self.assertEqual(resp.get("request_id"), "unknown-1")

    def test_websocket_large_payload(self):
        """Verify handling of large text payloads without socket death."""
        large_text = "JARVIS " * 10000  # ~70KB
        with self.client.websocket_connect("/ws") as ws:
            ws.send_json({
                "type": "system.toggle",
                "request_id": "large-1",
                "payload": {"data": large_text},
            })
            resp = ws.receive_json()
            self.assertEqual(resp.get("type"), "system.toggle.ack")
            self.assertEqual(resp.get("request_id"), "large-1")

    def test_websocket_ten_concurrent_clients(self):
        """Stress-test 10 parallel WebSocket client connections concurrently."""
        results: List[Dict[str, Any]] = []
        errors: List[str] = []

        def worker(client_id: int):
            endpoint = "/ws" if client_id % 2 == 0 else "/ws/jarvis"
            try:
                with self.client.websocket_connect(endpoint) as ws:
                    for i in range(5):
                        req_id = f"c{client_id}-step{i}"
                        ws.send_json({"type": "system.toggle", "payload": {"cid": client_id, "step": i}, "request_id": req_id})
                        data = ws.receive_json()
                        self.assertEqual(data.get("request_id"), req_id)
                        results.append(data)
            except Exception as e:
                errors.append(f"Client {client_id} error: {e}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Concurrent WS errors encountered: {errors}")
        self.assertEqual(len(results), 50)


if __name__ == "__main__":
    unittest.main()
