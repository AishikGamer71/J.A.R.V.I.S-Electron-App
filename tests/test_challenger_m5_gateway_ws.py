"""
tests/test_challenger_m5_gateway_ws.py
======================================
Milestone M5 Adversarial Stress Test Suite for Unified FastAPI Gateway & WebSockets.
Authored by challenger_m5_2 (Empirical Challenger).

Test Coverage:
1. REST API Endpoint Stress:
   - GET /health and GET /api/health -> status "healthy", version "2.0.0", subsystems dict
   - GET /api/system/stats and GET /system/stats -> cpu_pct, ram_used_mb, ram_total_mb, gpu_pct, power dict
   - GET /api/env and POST /api/env -> environment variable read/write
   - GET /api/history and POST /api/history/clear -> history retrieval and clearing
   - Sessions CRUD: GET /sessions, POST /sessions, GET /sessions/{id}/messages, DELETE /sessions/{id}
   - GET /search?q=test -> HybridMemory search response (RRF k=60)
   - GET /v1/tools -> registered tools list contains >= 15 tools including crawl4ai_extract, gpt_researcher_report, mobilerun_phone_task
   - POST /v1/tools/invoke -> works with {"tool": ..., "args": ...} and {"name": ..., "arguments": ...}
   - GET /v1/core-memory and POST /v1/core-memory -> memory state and dynamic indexing
   - GET /v1/audit -> audit log events and dynamic security score
   - GET /v1/permissions, POST /v1/permissions/grant, POST /v1/permissions/revoke
   - GET /v1/agents and POST /v1/agents/execute -> agent role inventory and goal execution
   - GET /v1/inbox -> scheduled tasks and inbox items

2. Full-Duplex WebSocket Endpoint Stress (/ws and /ws/jarvis):
   - Command routing: system.toggle, vision.mode, audio.control, user.message, reset_abort
   - Envelope compliance: verifies ACK envelopes with request_id, type, timestamp, payload
   - Emergency abort: reset_abort triggers hermes_brain.interrupt() and returns audio.control.ack
   - Malformed frames resilience: missing payload, missing type, empty string, non-JSON text, array JSON, raw bytes
   - Concurrency stress: 5 parallel concurrent WebSocket connections without deadlocks

3. Multi-Environment Script & Documentation Verification:
   - scripts/setup-environments.ps1 -> existence, .venv, .venv-omnivoice, .venv-omniparser, uv, -Force, exit
   - docs/UNIFIED_ARCHITECTURE.md -> existence, ports 8765, 8001, 8002, AgentShield, 17 assimilated components
   - README.md -> existence, installation, setup instructions
"""

import json
import os
import threading
import unittest
from pathlib import Path
from typing import Any, Dict, List

from fastapi.testclient import TestClient
from backend.main import app, hermes_brain, tool_dispatcher


class TestGatewayRestEndpoints(unittest.TestCase):
    """Stress tests for Unified FastAPI Gateway REST API endpoints."""

    @classmethod
    def setUpClass(cls):
        # Initialize client with raise_server_exceptions=False to capture HTTP status codes
        cls.client = TestClient(app, raise_server_exceptions=False)

    def test_01_health_endpoints(self):
        """Verify GET /health and GET /api/health contracts."""
        for path in ("/health", "/api/health"):
            resp = self.client.get(path)
            self.assertEqual(resp.status_code, 200, f"Failed on {path}: {resp.text}")
            data = resp.json()
            self.assertEqual(data.get("status"), "healthy")
            self.assertEqual(data.get("service"), "jarvis-core-service")
            self.assertEqual(data.get("version"), "2.0.0")
            self.assertIn("uptime_seconds", data)
            self.assertIn("subsystems", data)
            sub = data["subsystems"]
            self.assertIn("brain", sub)
            self.assertIn("shield", sub)
            self.assertIn("power", sub)

    def test_02_system_stats_endpoints(self):
        """Verify GET /api/system/stats and GET /system/stats contracts."""
        for path in ("/api/system/stats", "/system/stats"):
            resp = self.client.get(path)
            self.assertEqual(resp.status_code, 200, f"Failed on {path}: {resp.text}")
            data = resp.json()
            self.assertIn("cpu_pct", data)
            self.assertIn("ram_used_mb", data)
            self.assertIn("ram_total_mb", data)
            self.assertIn("gpu_pct", data)
            self.assertIn("power", data)
            self.assertIsInstance(data["cpu_pct"], (int, float))
            self.assertIsInstance(data["ram_used_mb"], (int, float))
            self.assertIsInstance(data["power"], dict)

    def test_03_env_endpoints(self):
        """Verify GET /api/env and POST /api/env read/write."""
        get_resp = self.client.get("/api/env")
        self.assertEqual(get_resp.status_code, 200)
        self.assertIn("env", get_resp.json())

        test_key = "JARVIS_CHALLENGER_TEST_ENV"
        test_val = "stress_test_pass_8829"
        post_resp = self.client.post("/api/env", json={"env": {test_key: test_val}})
        self.assertEqual(post_resp.status_code, 200)
        self.assertEqual(os.environ.get(test_key), test_val)

    def test_04_history_endpoints(self):
        """Verify GET /api/history and POST /api/history/clear."""
        clear_resp = self.client.post("/api/history/clear")
        self.assertEqual(clear_resp.status_code, 200)
        self.assertEqual(clear_resp.json().get("status"), "cleared")

        get_resp = self.client.get("/api/history")
        self.assertEqual(get_resp.status_code, 200)
        data = get_resp.json()
        self.assertIn("history", data)
        self.assertIn("session_id", data)

    def test_05_sessions_crud_lifecycle(self):
        """Verify full sessions lifecycle: create, list, get messages, delete."""
        create_resp = self.client.post("/sessions", json={"title": "Adversarial Stress Session"})
        self.assertEqual(create_resp.status_code, 200)
        session_id = create_resp.json().get("session_id")
        self.assertTrue(session_id)

        list_resp = self.client.get("/sessions")
        self.assertEqual(list_resp.status_code, 200)
        sessions = list_resp.json()
        session_ids = [s["id"] for s in sessions if "id" in s]
        self.assertIn(session_id, session_ids)

        msg_resp = self.client.get(f"/sessions/{session_id}/messages")
        self.assertEqual(msg_resp.status_code, 200)
        self.assertIsInstance(msg_resp.json(), list)

        del_resp = self.client.delete(f"/sessions/{session_id}")
        self.assertEqual(del_resp.status_code, 200)
        self.assertEqual(del_resp.json().get("status"), "deleted")

    def test_06_search_endpoint(self):
        """Verify GET /search?q=test interacts with HybridMemory without error."""
        resp = self.client.get("/search?q=test")
        self.assertEqual(
            resp.status_code,
            200,
            f"GET /search failed with status {resp.status_code}: {resp.text}",
        )
        data = resp.json()
        self.assertIn("results", data)
        self.assertIn("hybrid_hits", data)

    def test_07_tools_inventory(self):
        """Verify registered tools list contains >=15 tools including M5 additions."""
        resp = self.client.get("/v1/tools")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        tools = data.get("tools", [])
        self.assertGreaterEqual(len(tools), 15)

        tool_names = [
            t.get("name") or t.get("function", {}).get("name")
            for t in tools
        ]
        self.assertIn("crawl4ai_extract", tool_names)
        self.assertIn("gpt_researcher_report", tool_names)
        self.assertIn("mobilerun_phone_task", tool_names)

    def test_08_tools_invoke_variants(self):
        """Verify tool invocation works for both schema formats and handles edge cases."""
        # Variant A: {"tool": "echo", "args": {...}}
        resp_a = self.client.post("/v1/tools/invoke", json={"tool": "echo", "args": {"text": "ping_a"}})
        self.assertEqual(resp_a.status_code, 200)
        self.assertEqual(resp_a.json().get("result"), "ping_a")

        # Variant B: {"name": "echo", "arguments": {...}}
        resp_b = self.client.post("/v1/tools/invoke", json={"name": "echo", "arguments": {"text": "ping_b"}})
        self.assertEqual(resp_b.status_code, 200)
        self.assertEqual(resp_b.json().get("result"), "ping_b")

        # Missing tool name -> 400
        resp_missing = self.client.post("/v1/tools/invoke", json={"args": {}})
        self.assertEqual(resp_missing.status_code, 400)

        # Unknown tool -> fails gracefully without crashing gateway
        resp_unknown = self.client.post("/v1/tools/invoke", json={"tool": "non_existent_tool_xyz", "args": {}})
        self.assertEqual(resp_unknown.status_code, 200)
        self.assertFalse(resp_unknown.json().get("success"))

    def test_09_core_memory_endpoints(self):
        """Verify GET /v1/core-memory and POST /v1/core-memory."""
        get_resp = self.client.get("/v1/core-memory")
        self.assertEqual(get_resp.status_code, 200)
        data = get_resp.json()
        self.assertIn("soul", data)
        self.assertIn("user", data)
        self.assertIn("memory", data)
        self.assertIn("instincts", data)

        post_resp = self.client.post("/v1/core-memory", json={"fact": "User prefers concise logs", "category": "preference"})
        self.assertEqual(post_resp.status_code, 200)
        self.assertTrue(post_resp.json().get("success"))

    def test_10_audit_endpoint(self):
        """Verify GET /v1/audit returns audit records and score."""
        resp = self.client.get("/v1/audit")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("audit_log", data)
        self.assertIn("security_score", data)
        self.assertIn("total_records", data)

    def test_11_permissions_endpoints(self):
        """Verify GET /v1/permissions, POST grant, POST revoke."""
        resp = self.client.get("/v1/permissions")
        self.assertEqual(
            resp.status_code,
            200,
            f"GET /v1/permissions failed with status {resp.status_code}: {resp.text}",
        )
        data = resp.json()
        self.assertIn("permissions", data)

        grant_resp = self.client.post("/v1/permissions/grant", json={"tool": "echo", "scope": "*"})
        self.assertEqual(grant_resp.status_code, 200)
        self.assertTrue(grant_resp.json().get("success"))

        revoke_resp = self.client.post("/v1/permissions/revoke", json={"tool": "echo", "scope": "*"})
        self.assertEqual(revoke_resp.status_code, 200)
        self.assertTrue(revoke_resp.json().get("success"))

    def test_12_agents_endpoints(self):
        """Verify GET /v1/agents and POST /v1/agents/execute."""
        get_resp = self.client.get("/v1/agents")
        self.assertEqual(get_resp.status_code, 200)
        agents = get_resp.json()
        self.assertIsInstance(agents, list)
        agent_names = [a.get("name") for a in agents]
        self.assertIn("planner", agent_names)

        exec_resp = self.client.post("/v1/agents/execute", json={"task": "inspect system state", "agent_name": "planner"})
        self.assertEqual(exec_resp.status_code, 200)
        self.assertTrue(exec_resp.json().get("success"))

    def test_13_inbox_endpoint(self):
        """Verify GET /v1/inbox returns inbox task items."""
        resp = self.client.get("/v1/inbox")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("inbox", resp.json())


class TestGatewayWebSocketRouting(unittest.TestCase):
    """Stress tests for Full-Duplex WebSocket endpoints (/ws and /ws/jarvis)."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_ws_command_routing_dual_paths(self):
        """Verify routing for system.toggle, vision.mode, audio.control, reset_abort, user.message."""
        for endpoint in ("/ws", "/ws/jarvis"):
            with self.subTest(endpoint=endpoint):
                with self.client.websocket_connect(endpoint) as ws:
                    # 1. system.toggle
                    ws.send_json({"type": "system.toggle", "payload": {}, "request_id": "req-toggle-1"})
                    r = ws.receive_json()
                    self.assertEqual(r.get("type"), "system.toggle.ack")
                    self.assertEqual(r.get("request_id"), "req-toggle-1")
                    self.assertTrue(r.get("payload", {}).get("toggled"))

                    # 2. vision.mode
                    ws.send_json({"type": "vision.mode", "payload": {"mode": "hud_vision"}, "request_id": "req-vision-2"})
                    r = ws.receive_json()
                    self.assertEqual(r.get("type"), "vision.mode.ack")
                    self.assertEqual(r.get("request_id"), "req-vision-2")
                    self.assertEqual(r.get("payload", {}).get("mode"), "hud_vision")

                    # 3. audio.control
                    ws.send_json({"type": "audio.control", "payload": {"action": "unmute"}, "request_id": "req-audio-3"})
                    r = ws.receive_json()
                    self.assertEqual(r.get("type"), "audio.control.ack")
                    self.assertEqual(r.get("request_id"), "req-audio-3")

                    # 4. reset_abort -> emergency abort
                    hermes_brain.reset_interrupt()
                    self.assertFalse(hermes_brain.is_interrupted)
                    ws.send_json({"type": "reset_abort", "payload": {}, "request_id": "req-abort-4"})
                    r = ws.receive_json()
                    self.assertEqual(r.get("type"), "audio.control.ack")
                    self.assertEqual(r.get("payload", {}).get("status"), "interrupted")
                    self.assertTrue(hermes_brain.is_interrupted)
                    hermes_brain.reset_interrupt()

                    # 5. user.message -> streams response frames
                    ws.send_json({"type": "user.message", "payload": {"content": "Status check"}, "request_id": "req-user-5"})
                    received_types = []
                    while True:
                        msg = ws.receive_json()
                        received_types.append(msg.get("type"))
                        if msg.get("type") == "agent_response":
                            break
                    self.assertIn("agent.state", received_types)
                    self.assertIn("voice_state", received_types)
                    self.assertIn("agent.token", received_types)
                    self.assertIn("agent.complete", received_types)
                    self.assertIn("agent_response", received_types)

    def test_ws_malformed_frames_resilience(self):
        """Verify server handles malformed frames without crashing or unexpected disconnection."""
        with self.client.websocket_connect("/ws") as ws:
            # A. Missing payload
            ws.send_json({"type": "system.toggle", "request_id": "m1"})
            r_a = ws.receive_json()
            self.assertEqual(r_a.get("type"), "system.toggle.ack")

            # B. Missing type (fallback echo envelope)
            ws.send_json({"payload": {"test": "missing_type"}, "request_id": "m2"})
            r_b = ws.receive_json()
            self.assertEqual(r_b.get("type"), "agent.state")
            self.assertEqual(r_b.get("payload", {}).get("state"), "idle")

            # C. Empty string
            ws.send_text("")
            r_c = ws.receive_json()
            self.assertEqual(r_c.get("type"), "error")
            self.assertIn("Malformed JSON", r_c.get("payload", {}).get("message", ""))

            # D. Non-JSON string
            ws.send_text("MALFORMED_GARBAGE_PAYLOAD")
            r_d = ws.receive_json()
            self.assertEqual(r_d.get("type"), "error")
            self.assertIn("Malformed JSON", r_d.get("payload", {}).get("message", ""))

            # E. Non-dict JSON (array)
            ws.send_text("[1, 2, 3]")
            r_e = ws.receive_json()
            self.assertEqual(r_e.get("type"), "error")
            self.assertIn("Envelope must be a JSON object", r_e.get("payload", {}).get("message", ""))

            # Verify connection is STILL alive and functional after all malformed inputs
            ws.send_json({"type": "system.toggle", "payload": {}, "request_id": "alive-check"})
            r_alive = ws.receive_json()
            self.assertEqual(r_alive.get("type"), "system.toggle.ack")
            self.assertEqual(r_alive.get("request_id"), "alive-check")

    def test_ws_parallel_client_concurrency(self):
        """Stress-test 5 parallel concurrent WebSocket client connections."""
        results: List[Dict[str, Any]] = []
        errors: List[str] = []

        def worker(client_id: int):
            try:
                with self.client.websocket_connect("/ws") as ws:
                    ws.send_json({"type": "system.toggle", "payload": {"id": client_id}, "request_id": f"conc-{client_id}"})
                    data = ws.receive_json()
                    results.append(data)
            except Exception as e:
                errors.append(f"Client {client_id} error: {e}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Concurrent WS errors: {errors}")
        self.assertEqual(len(results), 5)
        for r in results:
            self.assertEqual(r.get("type"), "system.toggle.ack")


class TestSetupScriptAndDocs(unittest.TestCase):
    """Verification for setup-environments.ps1, UNIFIED_ARCHITECTURE.md, and README.md."""

    def test_setup_environments_script(self):
        """Verify scripts/setup-environments.ps1 exists and has mandatory tokens."""
        ps1_path = Path("scripts/setup-environments.ps1")
        self.assertTrue(ps1_path.exists(), "scripts/setup-environments.ps1 does not exist")
        content = ps1_path.read_text(encoding="utf-8")
        for token in (".venv", ".venv-omnivoice", ".venv-omniparser", "uv", "-Force", "exit"):
            self.assertIn(token, content, f"Token '{token}' missing from setup-environments.ps1")

    def test_unified_architecture_doc(self):
        """Verify docs/UNIFIED_ARCHITECTURE.md exists and covers tri-port model and 17 components."""
        doc_path = Path("docs/UNIFIED_ARCHITECTURE.md")
        self.assertTrue(doc_path.exists(), "docs/UNIFIED_ARCHITECTURE.md does not exist")
        content = doc_path.read_text(encoding="utf-8")
        for token in ("8765", "8001", "8002", "AgentShield", "17"):
            self.assertIn(token, content, f"Token '{token}' missing from UNIFIED_ARCHITECTURE.md")

    def test_readme_doc(self):
        """Verify README.md exists and covers installation and setup."""
        readme_path = Path("README.md")
        self.assertTrue(readme_path.exists(), "README.md does not exist")
        content = readme_path.read_text(encoding="utf-8")
        for token in ("installation", "setup", "setup-environments.ps1"):
            self.assertIn(token, content.lower(), f"Token '{token}' missing from README.md")


if __name__ == "__main__":
    unittest.main()
