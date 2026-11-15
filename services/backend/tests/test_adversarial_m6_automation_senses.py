"""
tests/test_adversarial_m6_automation_senses.py
==============================================
Tier 5 White-Box Adversarial Coverage Hardening Test Suite
Covering Automation, Senses, and Gateway Subsystems.

Subsystems:
1. WindowsMCPBridge (backend/automation/windows_mcp_bridge.py)
2. OmniParserService & OmniParserClient (backend/automation/omniparser_service.py)
3. AgentS3Runner & ExactTerminationEngine (backend/automation/agent_s3_runner.py)
4. BrowserUseRunner & MockCDPSession (backend/automation/browser_use_runner.py)
5. MarkItDownService & Table Repair (backend/automation/markitdown_service.py)
6. CameraHub SPMC Engine (backend/senses/camera_hub.py)
7. MediaPipeGestures & Landmark Smoothing (backend/senses/mediapipe_gestures.py)
8. DeepFaceSentry & Liveness (backend/senses/deepface_sentry.py)
9. Crawl4AIService & HTML Cleaner (backend/senses/crawl4ai_service.py)
10. GPTResearcherService & Synthesis (backend/senses/gpt_researcher_service.py)
11. MobileRunService & ADB Safety Guard (backend/senses/mobilerun_service.py)
12. Unified Gateway REST & WebSockets (backend/main.py)

Authored by: challenger_m6_2 (critic, specialist)
"""

import asyncio
import io
import json
import math
import os
import queue
import re
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Automation subsystems
from backend.automation.windows_mcp_bridge import WindowsMCPBridge
from backend.automation.omniparser_service import OmniParserService, OmniParserClient
from backend.automation.agent_s3_runner import (
    AgentS3Runner,
    AgentStatus,
    DesktopAction,
    DesktopActionType,
    EmergencyAbortManager,
    ExactTerminationEngine,
    OSWorldACI,
)
from backend.automation.browser_use_runner import BrowserUseRunner, MockCDPSession
from backend.automation.markitdown_service import MarkItDownService

# Senses subsystems
from backend.senses.camera_hub import CameraHub
from backend.senses.mediapipe_gestures import MediaPipeGestures
from backend.senses.deepface_sentry import DeepFaceSentry
from backend.senses.crawl4ai_service import Crawl4AIService, CrawlResult
from backend.senses.gpt_researcher_service import GPTResearcherService, ResearchReport
from backend.senses.mobilerun_service import MobileRunService

# Gateway
from fastapi.testclient import TestClient
from backend.main import app, hermes_brain, tool_dispatcher, state_db, hybrid_memory


# ==============================================================================
# 1. WindowsMCPBridge Adversarial Tests
# ==============================================================================
class TestWindowsMCPBridgeAdversarial(unittest.TestCase):
    """Stress tests for Windows native automation bridge and exclusion filters."""

    def setUp(self):
        self.bridge = WindowsMCPBridge(enable_com=False)

    def test_01_exclusion_filter_variations(self):
        """Verify strict exclusion of all J.A.R.V.I.S. Electron application window signatures."""
        jarvis_variants = [
            "JARVIS",
            "jarvis",
            "j.a.r.v.i.s",
            "J.A.R.V.I.S.",
            "Electron",
            "electron",
            "jarvis-electron-app",
            "  JARVIS Console  ",
            "J.A.R.V.I.S. Electron App - Main Window",
        ]
        for variant in jarvis_variants:
            self.assertTrue(
                self.bridge.is_excluded_window(variant),
                f"Variant '{variant}' should be identified as an excluded window.",
            )

    def test_02_non_excluded_windows_allowed(self):
        """Verify standard desktop applications are not falsely excluded."""
        allowed_windows = [
            "Notepad - Untitled",
            "Calculator",
            "Google Chrome",
            "Visual Studio Code",
            "File Explorer",
            "Slack",
            "Spotify Free",
        ]
        for win in allowed_windows:
            self.assertFalse(
                self.bridge.is_excluded_window(win),
                f"Application '{win}' should NOT be excluded.",
            )

    def test_03_malformed_and_edge_inputs(self):
        """Verify robustness against empty, None, and non-standard inputs."""
        self.assertFalse(self.bridge.is_excluded_window(""))
        self.assertFalse(self.bridge.is_excluded_window("   "))
        self.assertFalse(self.bridge.is_excluded_window(0))
        self.assertFalse(self.bridge.is_excluded_window(-1))
        self.assertFalse(self.bridge.is_excluded_window(None))  # type: ignore

    def test_04_explicit_pid_and_hwnd_exclusion(self):
        """Verify programmatic registration of PIDs and HWNDs."""
        test_pid = 98765
        test_hwnd = 123456
        self.bridge.exclude_pid(test_pid)
        self.bridge.exclude_hwnd(test_hwnd)

        self.assertTrue(self.bridge.is_excluded_window(test_hwnd))
        self.assertIn(test_pid, self.bridge._excluded_pids)
        self.assertIn(test_hwnd, self.bridge._excluded_hwnds)

    def test_05_element_lookups_and_snapshots(self):
        """Verify element searches and snapshot generation."""
        snapshot = self.bridge.windows_mcp_snapshot()
        self.assertEqual(snapshot["status"], "success")
        self.assertIn("controls", snapshot)
        self.assertIsInstance(snapshot["controls"], list)
        self.assertGreater(snapshot["count"], 0)

        # Search by non-existent name
        empty_hits = self.bridge.find_elements_by_name("NonExistentWindow_XYZ_999", exact=True)
        self.assertEqual(empty_hits, [])

        # Empty search string
        self.assertEqual(self.bridge.find_elements_by_name(""), [])

        # Search by control type
        panes = self.bridge.find_elements_by_control_type("Pane")
        self.assertIsInstance(panes, list)

    def test_06_simulated_input_dry_run(self):
        """Verify synthetic mouse and keyboard execution in dry-run mode."""
        click_res = self.bridge.simulate_click(500, 300, button="left", clicks=2, dry_run=True)
        self.assertTrue(click_res["success"])
        self.assertTrue(click_res["dry_run"])
        self.assertEqual(click_res["clicks"], 2)

        type_res = self.bridge.simulate_type("Hello Jarvis", dry_run=True)
        self.assertTrue(type_res["success"])
        self.assertEqual(type_res["text_length"], len("Hello Jarvis"))

        shortcut_res = self.bridge.simulate_shortcut(["ctrl", "c"], dry_run=True)
        self.assertTrue(shortcut_res["success"])
        self.assertEqual(shortcut_res["keys"], ["ctrl", "c"])

    def test_07_app_action_dispatch(self):
        """Verify windows_mcp_app action responses."""
        unsupported = self.bridge.windows_mcp_app(action="dance", name="app")
        self.assertEqual(unsupported["status"], "unsupported_action")

        focus_missing = self.bridge.windows_mcp_app(action="focus", name="PhantomAppXYZ")
        self.assertEqual(focus_missing["status"], "not_found")


# ==============================================================================
# 2. OmniParserService & OmniParserClient Adversarial Tests
# ==============================================================================
class TestOmniParserAdversarial(unittest.TestCase):
    """Stress tests for OmniParser V2 screen parsing and client fallbacks."""

    def setUp(self):
        self.service = OmniParserService(force_tier=3)
        self.client = OmniParserClient(base_url="http://127.0.0.1:9999", enable_in_process_fallback=True)

    def test_01_empty_and_corrupt_image_bytes(self):
        """Empty or corrupt images must return gracefully without raising unhandled exceptions."""
        empty_res = self.service.parse_screen(b"")
        self.assertEqual(empty_res["tier_used"], "empty")
        self.assertEqual(empty_res["count"], 0)
        self.assertEqual(empty_res["elements"], [])

        corrupt_res = self.service.parse_screen(b"invalid_non_image_garbage_bytes")
        self.assertIn("tier3", corrupt_res["tier_used"])
        self.assertGreater(corrupt_res["count"], 0)

    def test_02_element_formatting_schema(self):
        """Verify strict adherence to the OmniParser element contract."""
        elem = self.service.format_element(
            box=[10, 20, 100, 80],
            label="button",
            caption="Submit Form",
            confidence=0.98765,
            elem_type="button",
            id=42,
        )
        self.assertEqual(elem["id"], 42)
        self.assertEqual(elem["box"], [10, 20, 100, 80])
        self.assertEqual(elem["label"], "button")
        self.assertEqual(elem["caption"], "Submit Form")
        self.assertEqual(elem["confidence"], 0.988)
        self.assertEqual(elem["type"], "button")

    def test_03_som_image_annotation_resilience(self):
        """Verify Set-of-Mark (SoM) bounding box label drawing."""
        # Empty image returns None
        self.assertIsNone(self.service.get_som_labeled_img(b"", []))

        # Synthetic 100x100 PNG
        from PIL import Image
        img = Image.new("RGB", (100, 100), color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        png_bytes = buf.getvalue()

        elements = [
            self.service.format_element([10, 10, 50, 50], label="icon", caption="Test", id=1),
        ]
        labeled_bytes = self.service.get_som_labeled_img(png_bytes, elements)
        self.assertIsNotNone(labeled_bytes)
        self.assertGreater(len(labeled_bytes), 0)

    def test_04_client_in_process_fallback(self):
        """OmniParserClient transparently falls back to in-process execution when microservice offline."""
        client_res = self.client.parse_screen(b"fake_image_bytes")
        self.assertEqual(client_res["source"], "in_process_fallback")
        self.assertIn("elements", client_res)
        self.assertGreater(client_res["count"], 0)

        # Health check fallback
        health = self.client.health()
        self.assertEqual(health["status"], "in_process_fallback")
        self.assertEqual(health["port"], 8002)

    def test_05_client_disabled_fallback_raises(self):
        """When in-process fallback is disabled and service offline, client raises ConnectionError."""
        strict_client = OmniParserClient(
            base_url="http://127.0.0.1:9999",
            enable_in_process_fallback=False,
            timeout=0.2,
        )
        with self.assertRaises(ConnectionError):
            strict_client.parse_screen(b"test_bytes")


# ==============================================================================
# 3. AgentS3Runner & ExactTerminationEngine Adversarial Tests
# ==============================================================================
class TestAgentS3RunnerAdversarial(unittest.TestCase):
    """Stress tests for Agent-S3 autonomous execution, Issue #235, and emergency abort."""

    def setUp(self):
        self.runner = AgentS3Runner(max_steps=5, dry_run=True, enable_hotkey=False)

    def tearDown(self):
        self.runner.close()

    def test_01_exact_termination_engine_issue_235(self):
        """Fix Agent-S Issue #235: Reject substring occurrences of 'done' and 'fail'."""
        false_positives = [
            "done.txt",
            "file_done = True",
            "# done comment",
            "undone",
            "condone",
            "abandoned_process",
            "well done task",
            "failure_reason = 'timeout'",
            "redone",
        ]
        for s in false_positives:
            is_term, is_succ = ExactTerminationEngine.is_termination_action(s)
            self.assertFalse(
                is_term,
                f"String '{s}' must NOT be treated as a termination action (Issue #235).",
            )

        true_positives = [
            ("DONE", True),
            ("FINISHED", True),
            ("SUCCESS", True),
            ("GOAL_ACHIEVED", True),
            ("COMPLETE", True),
            ("COMPLETED", True),
            ("DONE()", True),
            ("DONE(code=0)", True),
            ("FAIL", False),
            ("FAILED", False),
            ("ERROR", False),
            ("IMPOSSIBLE", False),
            ("FAIL('missing window')", False),
        ]
        for token, expected_success in true_positives:
            is_term, is_succ = ExactTerminationEngine.is_termination_action(token)
            self.assertTrue(is_term, f"Token '{token}' must terminate.")
            self.assertEqual(is_succ, expected_success)

    def test_02_goal_completion_semantics(self):
        """Verify goal semantic evaluation on environmental state."""
        self.assertTrue(ExactTerminationEngine.check_goal_completion("Close Notepad", {"window_open": False}))
        self.assertTrue(ExactTerminationEngine.check_goal_completion("Open Chrome", {"window_open": True}))
        self.assertTrue(ExactTerminationEngine.check_goal_completion("Save document", {"file_saved": True}))
        self.assertTrue(ExactTerminationEngine.check_goal_completion("Type user query", {"text_written": True}))
        self.assertTrue(ExactTerminationEngine.check_goal_completion("Task", {"status": "DONE"}))
        self.assertFalse(ExactTerminationEngine.check_goal_completion("Close Notepad", {"window_open": True}))

    def test_03_emergency_abort_sub_15ms_latency(self):
        """Verify sub-15ms halt on emergency abort trigger."""
        abort_mgr = EmergencyAbortManager(enabled=False)
        self.assertFalse(abort_mgr.is_aborted)

        # Trigger abort in a background thread after 20ms
        def _trigger():
            time.sleep(0.02)
            abort_mgr.trigger_abort("Test trigger")

        t = threading.Thread(target=_trigger)
        t.start()

        t_start = time.perf_counter()
        completed = abort_mgr.wait_interruptible(seconds=2.0)
        latency = (time.perf_counter() - t_start) * 1000.0

        t.join()
        self.assertFalse(completed, "Sleep must be aborted.")
        self.assertTrue(abort_mgr.is_aborted)
        # Total latency should be around ~20-35ms, demonstrating instantaneous reaction
        self.assertLess(latency, 150.0, f"Halt latency was {latency:.2f}ms, expected fast interrupt.")

        # Reset abort
        abort_mgr.reset()
        self.assertFalse(abort_mgr.is_aborted)

    def test_04_repetitive_action_streak_guard(self):
        """Runner must halt when agent repeats the exact same action 3 times."""
        action = DesktopAction(
            action_type=DesktopActionType.CLICK,
            x=150,
            y=250,
            reasoning="Clicking button",
        )
        res1 = self.runner.execute_action(action)
        self.assertTrue(res1.success)

        res2 = self.runner.execute_action(action)
        self.assertTrue(res2.success)

        res3 = self.runner.execute_action(action)
        self.assertFalse(res3.success)
        self.assertTrue(res3.is_terminal)
        self.assertEqual(res3.terminal_state, "LOOP_DETECTED")
        self.assertIn("Repetitive action loop detected", res3.error or "")

    def test_05_max_steps_limit_exceeded(self):
        """Runner halts with MAX_STEPS_EXCEEDED if goal remains unfulfilled."""
        short_runner = AgentS3Runner(max_steps=2, dry_run=True, enable_hotkey=False)
        # Mock _plan_next_step to return alternating clicks
        short_runner._plan_next_step = lambda goal, state: DesktopAction(
            action_type=DesktopActionType.CLICK,
            x=100 + short_runner.current_step * 10,
            y=100,
        )
        result = short_runner.execute_goal("Unachievable goal", context={"window_open": True})
        self.assertFalse(result.success)
        self.assertEqual(result.status, "MAX_STEPS_EXCEEDED")
        self.assertEqual(result.total_steps, 2)
        short_runner.close()

    def test_06_confirmation_hook_rejection(self):
        """User confirmation hook can reject dangerous actions."""
        self.runner.register_confirmation_hook(lambda act: False)  # Reject all
        action = DesktopAction(action_type=DesktopActionType.CLICK, x=50, y=50)
        res = self.runner.execute_action(action)
        self.assertFalse(res.success)
        self.assertIn("rejected", res.error or "")

    def test_07_coordinate_boundaries_in_aci(self):
        """OSWorldACI must reject negative coordinates and out-of-bound values."""
        aci = OSWorldACI(dry_run=True)
        self.assertFalse(aci.validate_coordinates(-1, 50))
        self.assertFalse(aci.validate_coordinates(50, -5))
        self.assertTrue(aci.validate_coordinates(7680, 4320))  # 8K UHD
        self.assertFalse(aci.validate_coordinates(99999, 100))

        with self.assertRaises(ValueError):
            aci.click(-10, 50)


# ==============================================================================
# 4. BrowserUseRunner & MockCDPSession Adversarial Tests
# ==============================================================================
class TestBrowserUseAdversarial(unittest.TestCase):
    """Stress tests for headless CDP browser automation and URL validation."""

    def setUp(self):
        self.runner = BrowserUseRunner(headless=True, auto_start=False)

    def tearDown(self):
        self.runner.close()

    def test_01_url_validation_security(self):
        """Block dangerous schemes (javascript:, vbscript:, data:, file:), allow valid http/https and about:blank."""
        valid_urls = [
            "https://www.google.com",
            "http://localhost:8080/dashboard",
            "https://api.github.com/v1",
            "about:blank",
            "  https://example.com/test  ",
        ]
        for url in valid_urls:
            self.assertTrue(self.runner.validate_url(url), f"URL '{url}' should be valid.")

        dangerous_urls = [
            "javascript:alert('XSS')",
            "data:text/html,<h1>Injected</h1>",
            "file:///C:/Windows/System32/cmd.exe",
            "vbscript:msgbox",
            "about:config",
            "",
            "   ",
            None,  # type: ignore
            "ftp://ftp.is.co.za",
        ]
        for url in dangerous_urls:
            self.assertFalse(self.runner.validate_url(url), f"URL '{url}' should be blocked.")

    def test_02_mock_cdp_session_primitives(self):
        """Verify complete virtual CDP execution in MockCDPSession."""
        mock = MockCDPSession()
        nav = mock.navigate("https://example.com")
        self.assertTrue(nav["success"])
        self.assertEqual(mock.current_url, "https://example.com")

        click = mock.click("#submit-btn")
        self.assertTrue(click["success"])

        t1 = mock.type_text("#username", "jarvis_admin", clear_existing=True)
        self.assertEqual(t1["current_value"], "jarvis_admin")

        t2 = mock.type_text("#username", "_v2", clear_existing=False)
        self.assertEqual(t2["current_value"], "jarvis_admin_v2")

        dom = mock.extract_dom()
        self.assertIn("<!DOCTYPE html>", dom)
        self.assertIn("jarvis_admin_v2", dom)

        text = mock.extract_text()
        self.assertIn("example.com", text)

        screenshot = mock.capture_screenshot()
        self.assertEqual(screenshot[:8], b"\x89PNG\r\n\x1a\n")

        title = mock.evaluate_js("document.title")
        self.assertIn("example.com", title)

    def test_03_navigation_with_blocked_url(self):
        """Runner returns error on blocked URLs without crashing."""
        res = self.runner.navigate("javascript:void(0)")
        self.assertFalse(res["success"])
        self.assertIn("Blocked", res["error"])

    def test_04_emergency_abort_in_browser(self):
        """Emergency abort stops browser task."""
        self.runner.trigger_emergency_abort()
        self.assertTrue(self.runner.is_aborted)
        res = self.runner.navigate("https://example.com")
        self.assertFalse(res["success"])
        self.assertIn("aborted", res["error"])

        self.runner.reset_abort()
        self.assertFalse(self.runner.is_aborted)

    def test_05_idempotent_close(self):
        """Closing runner repeatedly does not raise errors."""
        self.runner.close()
        self.runner.close()


# ==============================================================================
# 5. MarkItDownService & Table Repair Adversarial Tests
# ==============================================================================
class TestMarkItDownAdversarial(unittest.TestCase):
    """Stress tests for universal document conversion and intelligent table repair."""

    def setUp(self):
        self.service = MarkItDownService(ocr_enabled=False)

    def test_01_table_repair_missing_delimiter(self):
        """Inject clean delimiter row into Markdown table missing delimiter."""
        raw_table = (
            "| Column 1 | Column 2 | Column 3 |\n"
            "| Val 1    | Val 2    | Val 3    |\n"
            "| Val 4    | Val 5    | Val 6    |"
        )
        repaired = self.service.repair_markdown_table(raw_table)
        lines = repaired.splitlines()
        self.assertEqual(len(lines), 4)
        self.assertIn("---", lines[1])
        self.assertIn("| Column 1 | Column 2 | Column 3 |", lines[0])

    def test_02_table_repair_ragged_columns(self):
        """Pad uneven row columns across table."""
        ragged_table = (
            "| Head 1 | Head 2 |\n"
            "|---|---|\n"
            "| Val 1 | Val 2 | Extra 3 | Extra 4 |\n"
            "| Single |"
        )
        repaired = self.service.repair_markdown_table(ragged_table)
        lines = repaired.splitlines()
        for line in lines:
            # 4 columns means 5 pipes
            self.assertEqual(line.count("|"), 5, f"Line does not have normalized 4 columns: '{line}'")

    def test_03_text_normalization(self):
        """Normalize carriage returns and collapse excessive blank lines."""
        raw = "Line 1\r\n\r\n\r\n\r\n\r\nLine 2\rLine 3   \nLine 4"
        clean = self.service.convert_text(raw)
        self.assertNotIn("\r", clean)
        self.assertNotIn("\n\n\n\n", clean)
        self.assertIn("Line 2\nLine 3\nLine 4", clean)

    def test_04_csv_conversion(self):
        """Convert CSV bytes to clean Markdown table."""
        csv_data = b"Name,Role,Clearance\nJarvis,AI,TopSecret\nTony,Creator,Admin\n"
        md, meta = self.service._convert_csv(csv_data, "team.csv")
        self.assertEqual(meta.format, "csv")
        self.assertEqual(meta.table_count, 1)
        self.assertIn("| Name | Role | Clearance |", md)
        self.assertIn("| Jarvis | AI | TopSecret |", md)

    def test_05_xlsx_xml_repair_showzeroes(self):
        """Microsoft MarkItDown repair: showZeroes='0' replaced with showZeroes='false'."""
        import zipfile
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            corrupt_xml = b'<?xml version="1.0"?><sheetView showZeroes="0" tabSelected="1"/>'
            zf.writestr("xl/worksheets/sheet1.xml", corrupt_xml)

        repaired_bytes = self.service._repair_xlsx_xml(buf.getvalue())
        with zipfile.ZipFile(io.BytesIO(repaired_bytes), "r") as zf:
            fixed_xml = zf.read("xl/worksheets/sheet1.xml")
            self.assertIn(b'showZeroes="false"', fixed_xml)
            self.assertNotIn(b'showZeroes="0"', fixed_xml)

    def test_06_nonexistent_file_handling(self):
        """Converting a non-existent file path returns structured failure envelope."""
        res = self.service.convert_local("non_existent_doc_12345.pdf")
        self.assertEqual(res.status, "failed")
        self.assertIn("File not found", res.error or "")


# ==============================================================================
# 6. CameraHub SPMC Engine Adversarial Tests
# ==============================================================================
class TestCameraHubAdversarial(unittest.TestCase):
    """Stress tests for CameraHub single-producer multi-consumer frame distribution."""

    def test_01_exclusive_ownership_and_lifecycle(self):
        """Verify exclusive camera ownership and clean start/stop idempotency."""
        hub = CameraHub(device_index=999, use_mock_if_unavailable=True)
        self.assertTrue(hub.is_exclusive_owner)
        self.assertFalse(hub.is_running())

        hub.start()
        self.assertTrue(hub.is_running())
        hub.start()  # Idempotent
        self.assertTrue(hub.is_running())

        hub.stop()
        self.assertFalse(hub.is_running())
        hub.stop()  # Idempotent
        self.assertFalse(hub.is_running())

    def test_02_mismatched_fps_consumers(self):
        """Distribute frames correctly between 60 FPS (MediaPipe) and 2 Hz (DeepFace) consumers."""
        hub = CameraHub(device_index=999, target_fps=60, use_mock_if_unavailable=True)
        q_fast = hub.subscribe("fast_60fps", fps=60, max_queue_size=30)
        q_slow = hub.subscribe("slow_2hz", fps=2.0, max_queue_size=10)

        hub.start()
        time.sleep(0.55)
        hub.stop()

        fast_count = q_fast.qsize()
        slow_count = q_slow.qsize()
        self.assertGreater(fast_count, slow_count)
        self.assertLessEqual(slow_count, 3)

    def test_03_queue_overflow_drops_oldest(self):
        """When consumer queue fills up, producer drops the oldest frame without blocking."""
        hub = CameraHub(device_index=999, target_fps=60, use_mock_if_unavailable=True)
        q = hub.subscribe("overflow_tester", fps=None, max_queue_size=2)

        f1 = np.full((10, 10, 3), 1, dtype=np.uint8)
        f2 = np.full((10, 10, 3), 2, dtype=np.uint8)
        f3 = np.full((10, 10, 3), 3, dtype=np.uint8)

        q.put_nowait(f1)
        q.put_nowait(f2)
        self.assertTrue(q.full())

        with hub._lock:
            for sub in hub._subscribers:
                if sub.queue.full():
                    try:
                        sub.queue.get_nowait()
                    except queue.Empty:
                        pass
                sub.queue.put_nowait(f3)

        p1 = q.get_nowait()
        p2 = q.get_nowait()
        self.assertEqual(int(p1[0, 0, 0]), 2, "f1 should have been dropped")
        self.assertEqual(int(p2[0, 0, 0]), 3, "f3 should be present")

    def test_04_synthetic_frame_generation(self):
        """Generate valid synthetic frame when physical camera unavailable."""
        hub = CameraHub(width=320, height=240, use_mock_if_unavailable=True)
        frame = hub.get_frame_sync()
        self.assertIsInstance(frame, np.ndarray)
        self.assertEqual(frame.shape, (240, 320, 3))
        self.assertEqual(frame.dtype, np.uint8)


# ==============================================================================
# 7. MediaPipeGestures Adversarial Tests
# ==============================================================================
class TestMediaPipeGesturesAdversarial(unittest.TestCase):
    """Stress tests for hand landmark tracking, smoothing, and gesture triggers."""

    def setUp(self):
        self.gestures = MediaPipeGestures(damping_factor=12.0)

    def test_01_exponential_damping_smoothing(self):
        """Landmarks are smoothed using exponential damping formula."""
        p0 = [{"x": 0.0, "y": 0.0, "z": 0.0}]
        p1 = [{"x": 1.0, "y": 1.0, "z": 1.0}]

        # Initial seeding
        s0 = self.gestures.smooth_landmarks(p0, dt=0.01)
        self.assertEqual(s0[0]["x"], 0.0)

        # Step with dt = 0.05
        # smoothing_weight = 1 - exp(-12 * 0.05) = 1 - exp(-0.6) = 1 - 0.5488 = 0.4512
        s1 = self.gestures.smooth_landmarks(p1, dt=0.05)
        expected_x = 0.0 + (1.0 - 0.0) * (1.0 - math.exp(-12.0 * 0.05))
        self.assertAlmostEqual(s1[0]["x"], expected_x, places=4)

    def test_02_scale_invariant_pinch_click(self):
        """Pinch click triggers when pinch_dist / palm_scale < 0.28."""
        events = []
        self.gestures.on_gesture(lambda e: events.append(e))

        # 21 synthetic landmarks: wrist at (0.5, 0.8), middle mcp (l9) at (0.5, 0.5) -> palm_scale = 0.3
        landmarks = [{"x": 0.5, "y": 0.5, "z": 0.0} for _ in range(21)]
        landmarks[0] = {"x": 0.5, "y": 0.8, "z": 0.0}  # wrist
        landmarks[9] = {"x": 0.5, "y": 0.5, "z": 0.0}  # middle_mcp
        # Thumb tip (4) and Index tip (8) very close -> pinch_dist = 0.03 -> pinch_ratio = 0.03 / 0.3 = 0.10 (< 0.28)
        landmarks[4] = {"x": 0.5, "y": 0.4, "z": 0.0}
        landmarks[8] = {"x": 0.5, "y": 0.43, "z": 0.0}

        self.gestures._analyze_hand(landmarks, canned="None", now_ts=time.time())
        self.assertTrue(self.gestures._is_pinched)
        self.assertEqual(self.gestures.get_current_gesture(), "pinch_click")
        self.assertTrue(any(e["gesture"] == "pinch_click" for e in events))

    def test_03_swipe_velocity_detection(self):
        """Swipe gestures detect high horizontal palm velocity vx > 0.65 or vx < -0.65."""
        self.gestures._palm_history.clear()
        for t, x in [(0.0, 0.8), (0.03, 0.6), (0.07, 0.4), (0.10, 0.2)]:
            lms = [
                {"x": x, "y": 0.8, "z": 0.0} if i == 0 else
                {"x": x, "y": 0.4, "z": 0.0} if i == 9 else
                {"x": x + 0.3, "y": 0.3, "z": 0.0} if i == 4 else
                {"x": x, "y": 0.3, "z": 0.0} if i == 8 else
                {"x": x, "y": 0.5, "z": 0.0} for i in range(21)
            ]
            self.gestures._analyze_hand(lms, canned="None", now_ts=t)

        self.assertEqual(self.gestures.get_current_gesture(), "swipe_left")

    def test_04_trigger_mock_gesture(self):
        """trigger_mock_gesture dispatches callback immediately."""
        dispatched = []
        self.gestures.on_gesture(lambda e: dispatched.append(e))
        res = self.gestures.trigger_mock_gesture("victory", confidence=0.99)
        self.assertEqual(res["gesture"], "victory")
        self.assertEqual(res["action"], "VICTORY")
        self.assertEqual(len(dispatched), 1)


# ==============================================================================
# 8. DeepFaceSentry Adversarial Tests
# ==============================================================================
class TestDeepFaceSentryAdversarial(unittest.TestCase):
    """Stress tests for biometric sentry, stranger streaks, and anti-spoofing."""

    def setUp(self):
        self.sentry = DeepFaceSentry(anti_spoofing_enabled=True)

    def test_01_null_and_black_frame(self):
        """Null frame and pure black frame are handled cleanly."""
        res_none = self.sentry.authenticate_frame(None)
        self.assertFalse(res_none["authenticated"])
        self.assertIn("No frame provided", res_none["error"])

        black_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        res_black = self.sentry.authenticate_frame(black_frame)
        self.assertFalse(res_black["authenticated"])
        self.assertEqual(res_black["status"], "NO_FACE")

    def test_02_stranger_streak_escalation(self):
        """Stranger detections increment streak; streak >= 3 escalates to STRANGER_SENTRY_ALERT."""
        # Set registered owner embedding orthogonal to frame
        self.sentry._owner_embeddings = [np.array([1.0] + [0.0] * 511, dtype=np.float32)]
        self.sentry._stranger_streak = 0
        frame = np.full((100, 100, 3), 50, dtype=np.uint8)

        r1 = self.sentry.authenticate_frame(frame)
        self.assertFalse(r1["authenticated"])
        self.assertEqual(r1["status"], "STRANGER")
        self.assertEqual(self.sentry._stranger_streak, 1)

        r2 = self.sentry.authenticate_frame(frame)
        self.assertEqual(r2["status"], "STRANGER")
        self.assertEqual(self.sentry._stranger_streak, 2)

        r3 = self.sentry.authenticate_frame(frame)
        self.assertEqual(r3["status"], "STRANGER_SENTRY_ALERT")
        self.assertEqual(self.sentry._stranger_streak, 3)

    def test_03_cosine_distance_edge_cases(self):
        """Cosine distance handles identical, orthogonal, and zero vectors without divide-by-zero."""
        v1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        v2 = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        v_zero = np.zeros(3, dtype=np.float32)

        # Identical
        self.assertAlmostEqual(self.sentry._cosine_distance(v1, v1), 0.0, places=5)
        # Orthogonal
        self.assertAlmostEqual(self.sentry._cosine_distance(v1, v2), 1.0, places=5)
        # Zero vector fallback
        self.assertEqual(self.sentry._cosine_distance(v1, v_zero), 1.0)

    def test_04_owner_face_registration(self):
        """Registering owner face stores reference embedding."""
        frame = np.full((100, 100, 3), 128, dtype=np.uint8)
        success = self.sentry.register_face("owner", frame)
        self.assertTrue(success)
        self.assertGreater(len(self.sentry._owner_embeddings), 0)


# ==============================================================================
# 9. Crawl4AIService Adversarial Tests
# ==============================================================================
class TestCrawl4AIAdversarial(unittest.TestCase):
    """Stress tests for web scraping, HTML cleaning, and protocol validation."""

    def setUp(self):
        self.service = Crawl4AIService(filter_noise=True)

    def test_01_url_validation(self):
        """Validate web protocols and reject invalid schemes."""
        self.assertTrue(self.service.is_valid_url("https://news.ycombinator.com"))
        self.assertTrue(self.service.is_valid_url("http://127.0.0.1:8000"))
        self.assertFalse(self.service.is_valid_url("ftp://files.example.com"))
        self.assertFalse(self.service.is_valid_url("javascript:void(0)"))
        self.assertFalse(self.service.is_valid_url(""))
        self.assertFalse(self.service.is_valid_url("not a url"))

    def test_02_html_boilerplate_and_cookie_stripping(self):
        """HTML cleaner strips scripts, styles, cookie banners, and noise."""
        raw_html = (
            "<!DOCTYPE html><html><head><title>Test</title><style>body {color: red;}</style></head>"
            "<body>"
            "<script>var x = 1;</script>"
            "<nav><a href='/home'>Home</a></nav>"
            "<div class='cookie-banner-popup'>Please accept cookies!</div>"
            "<h1>Main Article Title</h1>"
            "<p>This is the essential article paragraph.</p>"
            "<footer>Copyright 2026</footer>"
            "</body></html>"
        )
        md = self.service.html_to_markdown(raw_html)
        self.assertNotIn("Please accept cookies", md)
        self.assertNotIn("var x = 1", md)
        self.assertNotIn("body {color: red;}", md)
        self.assertNotIn("Copyright 2026", md)
        self.assertIn("# Main Article Title", md)
        self.assertIn("This is the essential article paragraph.", md)

    def test_03_table_conversion(self):
        """Convert HTML tables to clean Markdown syntax."""
        html_table = (
            "<table>"
            "<tr><th>Metric</th><th>Score</th></tr>"
            "<tr><td>Latency</td><td>12ms</td></tr>"
            "</table>"
        )
        md = self.service.html_to_markdown(html_table)
        self.assertIn("| Metric | Score |", md)
        self.assertIn("| Latency | 12ms |", md)

    def test_04_about_blank_and_local_file_crawl(self):
        """about:blank returns empty markdown with status 200."""
        res = self.service.crawl("about:blank")
        self.assertEqual(res.status, "success")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.markdown, "")


# ==============================================================================
# 10. GPTResearcherService Adversarial Tests
# ==============================================================================
class TestGPTResearcherAdversarial(unittest.TestCase):
    """Stress tests for autonomous research, subquery formulation, and citations."""

    def setUp(self):
        self.researcher = GPTResearcherService(max_sources=3)

    def test_01_subquery_decomposition(self):
        """Decompose topic into specified count of subqueries."""
        subqueries = self.researcher.generate_subqueries("Autonomous Quantum AI", count=3)
        self.assertEqual(len(subqueries), 3)
        for sq in subqueries:
            self.assertIn("Autonomous Quantum AI", sq)

        # Boundary count
        single = self.researcher.generate_subqueries("Topic", count=1)
        self.assertEqual(len(single), 1)

    def test_02_citation_extraction(self):
        """Extract inline citations deterministically without duplicate references."""
        text = "Finding A demonstrates efficiency [1]. Finding B corroborates [2]. Additional review [1] and [3]."
        citations = self.researcher.extract_citations(text)
        self.assertEqual(citations, ["[1]", "[2]", "[3]"])

    def test_03_report_formatting_structure(self):
        """Report contains Table of Contents, Executive Summary, Findings, and Sources."""
        findings = [
            "Quantum error correction achieved 99.9% fidelity.",
            "Distributed state consensus demonstrated sub-5ms sync.",
        ]
        sources = [
            "IEEE Quantum Transactions (https://ieee.org/paper1)",
            "Nature Physics Review (https://nature.com/paper2)",
        ]
        report = self.researcher.format_report(
            title="Quantum Consensus",
            findings=findings,
            sources=sources,
            executive_summary="Summary of quantum breakthrough.",
        )
        self.assertIn("# Research Report: Quantum Consensus", report)
        self.assertIn("## Table of Contents", report)
        self.assertIn("## Executive Summary", report)
        self.assertIn("Summary of quantum breakthrough.", report)
        self.assertIn("## Key Findings", report)
        self.assertIn("[1] IEEE Quantum Transactions", report)
        self.assertIn("[2] Nature Physics Review", report)

    def test_04_bm25_lexical_filtering(self):
        """BM25 filter ranks relevant passages matching query tokens at top."""
        query = "distributed neural memory"
        texts = [
            "The weather in Tokyo is sunny today.",
            "Autonomous driving systems require lidar calibration.",
            "Distributed neural memory architectures utilize reciprocal rank fusion for indexing.",
        ]
        filtered = self.researcher._filter_context_bm25(query, texts, top_k=1)
        self.assertEqual(len(filtered), 1)
        self.assertIn("Distributed neural memory", filtered[0])


# ==============================================================================
# 11. MobileRunService Adversarial Tests
# ==============================================================================
class TestMobileRunAdversarial(unittest.TestCase):
    """Stress tests for ADB command safety guarding and injection defenses."""

    def setUp(self):
        self.service = MobileRunService()

    def test_01_dangerous_command_blocking(self):
        """Block destructive commands targeting system partitions."""
        dangerous_commands = [
            "rm -rf /",
            "rm -rf /system",
            "rm -r -f /system",
            "rm -rf /data",
            "rm /boot/boot.img",
            "format /sdcard",
            "dd if=/dev/zero of=/dev/block/bootdevice",
            "reboot bootloader",
            "reboot recovery",
            "chmod 777 /system",
            "su",
            "mkfs.ext4 /dev/block/sda",
            "wipe data",
        ]
        for cmd in dangerous_commands:
            self.assertFalse(
                self.service.validate_adb_command(cmd),
                f"Command '{cmd}' must be blocked by MobileRun safety guard.",
            )

    def test_02_safe_commands_allowed(self):
        """Allow legitimate automation commands."""
        safe_commands = [
            "input tap 400 800",
            "input swipe 100 200 100 600 250",
            "input text Hello%sJarvis",
            "input keyevent 3",  # HOME
            "input keyevent 4",  # BACK
            "dumpsys battery",
            "pm list packages -3",
        ]
        for cmd in safe_commands:
            self.assertTrue(
                self.service.validate_adb_command(cmd),
                f"Command '{cmd}' should be allowed.",
            )

    def test_03_empty_and_whitespace_commands_rejected(self):
        """Reject empty or whitespace-only inputs."""
        self.assertFalse(self.service.validate_adb_command(""))
        self.assertFalse(self.service.validate_adb_command("   "))
        self.assertFalse(self.service.validate_adb_command(None))  # type: ignore

    def test_04_negative_coordinates_rejected(self):
        """Reject negative coordinates in tap and swipe."""
        self.assertFalse(self.service.tap(-10, 50))
        self.assertFalse(self.service.swipe(100, -20, 100, 500))

    def test_05_mock_device_enumeration(self):
        """List devices returns mock device when adb binary absent or offline."""
        devices = self.service.list_devices()
        self.assertIsInstance(devices, list)
        self.assertGreater(len(devices), 0)
        self.assertIn("id", devices[0])


# ==============================================================================
# 12. Unified Gateway REST & WebSockets Adversarial Tests
# ==============================================================================
class TestGatewayAdversarial(unittest.TestCase):
    """Stress tests for FastAPI Gateway endpoints, WebSockets, and envelope formatting."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app, raise_server_exceptions=False)

    def test_01_rest_health_and_subsystems(self):
        """GET /health and GET /api/health return 200 OK with subsystems dict."""
        for path in ("/health", "/api/health"):
            resp = self.client.get(path)
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["status"], "healthy")
            self.assertEqual(data["service"], "jarvis-core-service")
            self.assertIn("subsystems", data)

    def test_02_system_stats(self):
        """GET /api/system/stats returns hardware telemetry metrics."""
        resp = self.client.get("/api/system/stats")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("cpu_pct", data)
        self.assertIn("ram_used_mb", data)
        self.assertIn("power", data)

    def test_03_environment_api_roundtrip(self):
        """GET /api/env and POST /api/env read and write safe environment variables."""
        test_val = f"test_val_{int(time.time())}"
        post_resp = self.client.post("/api/env", json={"env": {"MODEL_ROUTING_POLICY": test_val}})
        self.assertEqual(post_resp.status_code, 200)

        get_resp = self.client.get("/api/env")
        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(get_resp.json()["env"]["MODEL_ROUTING_POLICY"], test_val)

    def test_04_sessions_crud(self):
        """Sessions CRUD lifecycle: create, get messages, delete."""
        # Create
        c_resp = self.client.post("/sessions", json={"title": "Adversarial Test Session"})
        self.assertEqual(c_resp.status_code, 200)
        sid = c_resp.json()["session_id"]

        # Add message via direct state_db
        state_db.add_message(sid, "user", "Test message")

        # Get messages
        m_resp = self.client.get(f"/sessions/{sid}/messages")
        self.assertEqual(m_resp.status_code, 200)
        msgs = m_resp.json()
        self.assertGreater(len(msgs), 0)

        # Delete
        d_resp = self.client.delete(f"/sessions/{sid}")
        self.assertEqual(d_resp.status_code, 200)
        self.assertEqual(d_resp.json()["status"], "deleted")

    def test_05_search_endpoint_hybrid_rrf(self):
        """GET /search returns both FTS and Hybrid RAG hits."""
        resp = self.client.get("/search", params={"q": "system"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("results", data)
        self.assertIn("hybrid_hits", data)

    def test_06_tools_invoke_error_handling(self):
        """POST /v1/tools/invoke handles missing tool name gracefully."""
        resp = self.client.post("/v1/tools/invoke", json={})
        self.assertEqual(resp.status_code, 400)

    def test_07_core_memory_roundtrip(self):
        """GET /v1/core-memory and POST /v1/core-memory."""
        get_resp = self.client.get("/v1/core-memory")
        self.assertEqual(get_resp.status_code, 200)
        data = get_resp.json()
        self.assertIn("soul", data)
        self.assertIn("instincts", data)

        post_resp = self.client.post("/v1/core-memory", json={"fact": "User prefers concise answers", "category": "user"})
        self.assertEqual(post_resp.status_code, 200)
        self.assertTrue(post_resp.json()["success"])

    def test_08_permissions_and_agents_api(self):
        """GET /v1/permissions and GET /v1/agents return valid catalogs."""
        p_resp = self.client.get("/v1/permissions")
        self.assertEqual(p_resp.status_code, 200)
        self.assertIn("permissions", p_resp.json())

        a_resp = self.client.get("/v1/agents")
        self.assertEqual(a_resp.status_code, 200)
        agents = a_resp.json()
        self.assertGreater(len(agents), 0)

    def test_09_websocket_command_routing_and_envelopes(self):
        """WebSocket /ws accepts client commands and replies with standard ACK envelopes."""
        with self.client.websocket_connect("/ws") as ws:
            # 1. system.toggle
            ws.send_json({"type": "system.toggle", "request_id": "req-001", "payload": {}})
            msg1 = ws.receive_json()
            self.assertEqual(msg1["type"], "system.toggle.ack")
            self.assertEqual(msg1["request_id"], "req-001")
            self.assertTrue(msg1["payload"]["toggled"])

            # 2. vision.mode
            ws.send_json({"type": "vision.mode", "request_id": "req-002", "payload": {"mode": "biometric"}})
            msg2 = ws.receive_json()
            self.assertEqual(msg2["type"], "vision.mode.ack")
            self.assertEqual(msg2["payload"]["mode"], "biometric")

            # 3. reset_abort
            ws.send_json({"type": "reset_abort", "request_id": "req-003"})
            msg3 = ws.receive_json()
            self.assertEqual(msg3["type"], "audio.control.ack")
            self.assertEqual(msg3["payload"]["status"], "interrupted")

    def test_10_websocket_malformed_frame_resilience(self):
        """WebSocket handles malformed frames, non-JSON strings, and array payloads gracefully."""
        with self.client.websocket_connect("/ws") as ws:
            # Malformed JSON
            ws.send_text("NOT_VALID_JSON{{{")
            err1 = ws.receive_json()
            self.assertEqual(err1["type"], "error")
            self.assertIn("Malformed JSON", err1["payload"]["message"])

            # Non-dict JSON (array)
            ws.send_text("[1, 2, 3]")
            err2 = ws.receive_json()
            self.assertEqual(err2["type"], "error")
            self.assertIn("JSON object", err2["payload"]["message"])

            # Unknown type falls back to agent.state echo without disconnect
            ws.send_json({"type": "unknown.custom.cmd", "payload": {"key": "val"}})
            echo = ws.receive_json()
            self.assertEqual(echo["type"], "agent.state")

    def test_11_concurrent_websocket_connections(self):
        """Multiple concurrent WebSocket connections can connect without deadlocks."""
        conns = []
        try:
            for _ in range(5):
                ws = self.client.websocket_connect("/ws")
                conns.append(ws.__enter__())

            # Send ping on each
            for idx, ws in enumerate(conns):
                ws.send_json({"type": "system.toggle", "request_id": f"conn-{idx}"})
                reply = ws.receive_json()
                self.assertEqual(reply["request_id"], f"conn-{idx}")
        finally:
            for ws in conns:
                try:
                    ws.__exit__(None, None, None)
                except Exception:
                    pass


if __name__ == "__main__":
    unittest.main()
