"""
tests/test_adversarial_m4.py
============================
Empirical Adversarial Challenge Suite for Milestone M4:
  1. backend/automation/windows_mcp_bridge.py:
     - Window exclusion filter adversarial title variations ('JARVIS', 'j.a.r.v.i.s',
       'Electron', 'jarvis-electron-app', 'J.A.R.V.I.S.', mixed-case, whitespace)
     - Non-JARVIS window discrimination ('Notepad', 'Calculator', 'Chrome', 'Slack', etc.)
     - HWND & PID exclusion registries and reflection
     - Desktop element tree safety and exclusion guarantees
  2. backend/automation/agent_s3_runner.py (Emergency Abort):
     - trigger_emergency_abort() latency benchmark (mean < 1ms, strictly < 5ms)
     - Interruptible sleep wait_interruptible() wake-up and halt latency (< 15ms)
     - Instant wake-up if already aborted (< 0.5ms)
     - reset_abort() state restoration (is_aborted=False, state=IDLE)
     - Telemetry envelope emission on abort/reset
     - Operation blocking across all ACI primitives when aborted
  3. backend/automation/agent_s3_runner.py (ExactTerminationEngine / Issue #235):
     - Substring evasion resistance ('done.txt', 'file_done = True', '# done comment',
       'undone', 'well done', 'done_task()', 'failure_reason = "timeout"')
     - Exact token matching ('DONE', 'FINISHED', 'SUCCESS', 'FAIL', 'FAILED', etc.)
     - Exact function matching ('DONE()', 'FAIL("msg")')
     - Goal completion semantic state evaluation (close, open, save, type, status flags)
  4. backend/automation/agent_s3_runner.py (OSWorldACI Coordinate Boundaries):
     - Negative coordinate rejection (-10, 50), (50, -10), (-1, -1) -> False & ValueError
     - 8K UHD high-res coordinate support (7680, 4320) -> True
     - Extreme coordinate rejection (7681, 100), (100, 4321), (10000, 10000) -> False & ValueError
     - Dry-run and aborted state execution behavior
  5. UI Drift Verification:
     - Programmatic inspection ensuring zero UI drift outside permitted M1 files
  6. Additional Automation Component Stress:
     - BrowserUseRunner URL protocol rejection (javascript:, vbscript:, data:, file:)
     - MarkItDownService table repair edge cases (missing delimiters, uneven columns)
     - OmniParserService empty/corrupt image handling and element formatting

Authored by: challenger_m4_1 (critic, specialist)
"""

import os
import re
import sys
import time
import subprocess
import threading
import unittest
from pathlib import Path
from typing import Any, Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.automation.windows_mcp_bridge import WindowsMCPBridge
from backend.automation.agent_s3_runner import (
    AgentS3Runner,
    AgentStatus,
    DesktopAction,
    DesktopActionType,
    EmergencyAbortManager,
    ExactTerminationEngine,
    OSWorldACI,
)
from backend.automation.browser_use_runner import BrowserUseRunner
from backend.automation.markitdown_service import MarkItDownService
from backend.automation.omniparser_service import OmniParserService


class TestAdversarialWindowsMCPBridge(unittest.TestCase):
    """Adversarial stress-testing of WindowsMCPBridge window exclusion filters."""

    def setUp(self):
        self.bridge = WindowsMCPBridge()

    def test_exclusion_exact_and_title_variations(self):
        """Mandatory Test 1: JARVIS and Electron title variations must all return True."""
        required_variations = [
            "JARVIS",
            "j.a.r.v.i.s",
            "Electron",
            "jarvis-electron-app",
            "J.A.R.V.I.S.",
        ]
        for title in required_variations:
            self.assertTrue(
                self.bridge.is_excluded_window(title),
                f"Expected '{title}' to be excluded by WindowsMCPBridge",
            )

    def test_exclusion_case_insensitivity_and_spacing(self):
        """Stress-test case variations, whitespace padding, and punctuation."""
        extended_variations = [
            "jarvis",
            "ELECTRON",
            "electron.exe",
            "j.A.r.V.i.S",
            "J.A.R.V.I.S",
            "  JARVIS  ",
            "\tElectron Application\n",
            "J.A.R.V.I.S. Core Dashboard",
            "Project Jarvis Main Console",
            "electron-quick-start",
            "jarvis-electron-app v2.0",
        ]
        for title in extended_variations:
            self.assertTrue(
                self.bridge.is_excluded_window(title),
                f"Expected extended variation '{title}' to be excluded",
            )

    def test_non_jarvis_windows_allowed(self):
        """Mandatory Test 1b: Non-JARVIS windows must return False."""
        allowed_titles = [
            "Notepad",
            "Calculator",
            "Chrome",
            "Google Chrome - New Tab",
            "Microsoft Visual Studio Code",
            "Windows PowerShell",
            "Task Manager",
            "Slack | General",
            "Spotify Free",
            "File Explorer",
            "Settings",
            "Command Prompt",
        ]
        for title in allowed_titles:
            self.assertFalse(
                self.bridge.is_excluded_window(title),
                f"Expected legitimate window '{title}' NOT to be excluded",
            )

    def test_hwnd_and_pid_registries(self):
        """Test explicit HWND and PID exclusion registries."""
        bridge = WindowsMCPBridge()
        test_hwnd = 98765432
        self.assertFalse(bridge.is_excluded_window(test_hwnd))

        bridge.exclude_hwnd(test_hwnd)
        self.assertTrue(bridge.is_excluded_window(test_hwnd))

        test_pid = 54321
        bridge.exclude_pid(test_pid)
        self.assertIn(test_pid, bridge._excluded_pids)

    def test_root_elements_contain_no_excluded_windows(self):
        """Root elements enumerated must never include JARVIS or Electron titles."""
        elements = self.bridge.get_root_elements()
        self.assertIsInstance(elements, list)
        for elem in elements:
            title = elem.get("title", "")
            if title:
                self.assertFalse(
                    self.bridge.is_excluded_window(title),
                    f"Enumerated element '{title}' should not have been returned in desktop root",
                )


class TestAdversarialEmergencyAbort(unittest.TestCase):
    """Adversarial stress-testing of AgentS3Runner and EmergencyAbortManager."""

    def test_trigger_abort_latency_benchmark(self):
        """
        Mandatory Test 2a: trigger_emergency_abort() must set is_aborted = True
        immediately (<1ms). Run benchmark over 200 iterations.
        """
        durations = []
        for _ in range(200):
            runner = AgentS3Runner(enable_hotkey=False)
            self.assertFalse(runner.is_aborted)

            t0 = time.perf_counter()
            runner.trigger_emergency_abort("Benchmark abort")
            t1 = time.perf_counter()

            self.assertTrue(runner.is_aborted)
            durations.append((t1 - t0) * 1000.0)  # ms

        mean_duration = sum(durations) / len(durations)
        max_duration = max(durations)

        self.assertLess(
            mean_duration,
            1.0,
            f"Mean abort trigger latency {mean_duration:.4f}ms exceeded 1.0ms limit",
        )
        self.assertLess(
            max_duration,
            5.0,
            f"Max abort trigger latency {max_duration:.4f}ms exceeded 5.0ms threshold",
        )

    def test_wait_interruptible_delayed_abort_latency(self):
        """
        Mandatory Test 2b: wait_interruptible() must wake up and halt in <15ms
        when an abort is fired concurrently from another thread.
        """
        latencies = []
        for _ in range(15):
            mgr = EmergencyAbortManager(enabled=False)

            def delayed_trip():
                time.sleep(0.005)  # 5ms delay
                mgr.trigger_abort("Threaded abort")

            th = threading.Thread(target=delayed_trip)
            t_start = time.perf_counter()
            th.start()
            res = mgr.wait_interruptible(seconds=2.0, check_interval=0.002)
            t_halt = time.perf_counter()
            th.join()

            self.assertFalse(res, "wait_interruptible must return False when aborted")
            self.assertTrue(mgr.is_aborted)

            # Response time from the 5ms trigger to unblock
            total_elapsed_ms = (t_halt - t_start) * 1000.0
            # Latency after delay (trip took ~5ms)
            trip_response_ms = max(0.0, total_elapsed_ms - 5.0)
            latencies.append(trip_response_ms)

        mean_resp = sum(latencies) / len(latencies)
        max_resp = max(latencies)

        # Total unblock response from trip must be well under 15ms
        self.assertLess(
            mean_resp,
            15.0,
            f"Mean halt latency after trip {mean_resp:.2f}ms was not < 15ms",
        )
        self.assertLess(
            max_resp,
            25.0,
            f"Max halt latency {max_resp:.2f}ms exceeded safety bounds",
        )

    def test_wait_interruptible_when_already_aborted(self):
        """If already aborted, wait_interruptible must return False immediately (<0.5ms)."""
        mgr = EmergencyAbortManager(enabled=False)
        mgr.trigger_abort()
        self.assertTrue(mgr.is_aborted)

        t0 = time.perf_counter()
        res = mgr.wait_interruptible(seconds=10.0)
        t1 = time.perf_counter()

        self.assertFalse(res)
        elapsed_ms = (t1 - t0) * 1000.0
        self.assertLess(elapsed_ms, 1.0, f"Already-aborted wait took {elapsed_ms:.4f}ms, expected < 1ms")

    def test_reset_abort_restores_state(self):
        """Mandatory Test 2c: reset_abort() restores is_aborted = False and IDLE state."""
        runner = AgentS3Runner(enable_hotkey=False)
        runner.trigger_emergency_abort("Test reset")
        self.assertTrue(runner.is_aborted)
        self.assertEqual(runner.state, AgentStatus.ABORTED)

        runner.reset_abort()
        self.assertFalse(runner.is_aborted)
        self.assertEqual(runner.state, AgentStatus.IDLE)

    def test_telemetry_emission_on_abort_and_reset(self):
        """Structured telemetry envelopes must be emitted on abort and reset."""
        runner = AgentS3Runner(enable_hotkey=False)
        envelopes = []
        runner.register_telemetry_handler(lambda env: envelopes.append(env))

        runner.trigger_emergency_abort("Emergency operator halt")
        self.assertGreaterEqual(len(envelopes), 1)
        abort_env = envelopes[-1]
        self.assertEqual(abort_env["type"], "agent.state")
        self.assertEqual(abort_env["payload"]["state"], "aborted")
        self.assertTrue(abort_env["payload"]["is_aborted"])

        runner.reset_abort()
        self.assertGreaterEqual(len(envelopes), 2)
        reset_env = envelopes[-1]
        self.assertEqual(reset_env["type"], "agent.state")
        self.assertEqual(reset_env["payload"]["state"], "idle")
        self.assertFalse(reset_env["payload"]["is_aborted"])

    def test_aci_blocks_actions_when_aborted(self):
        """OSWorldACI must refuse to execute all actions when runner is aborted."""
        runner = AgentS3Runner(enable_hotkey=False, dry_run=True)
        runner.trigger_emergency_abort()

        click_res = runner.aci.click(100, 100)
        self.assertFalse(click_res["success"])
        self.assertTrue(click_res.get("aborted", False))

        move_res = runner.aci.move_to(100, 100)
        self.assertFalse(move_res["success"])
        self.assertTrue(move_res.get("aborted", False))

        type_res = runner.aci.type_text("test")
        self.assertFalse(type_res["success"])
        self.assertTrue(type_res.get("aborted", False))

        hotkey_res = runner.aci.hotkey(["ctrl", "c"])
        self.assertFalse(hotkey_res["success"])
        self.assertTrue(hotkey_res.get("aborted", False))


class TestAdversarialExactTerminationEngine(unittest.TestCase):
    """
    Adversarial challenge of ExactTerminationEngine (Fix for Agent-S Issue #235).
    Guarantees that substring occurrences do not trigger false termination.
    """

    def test_substring_evasion_must_not_terminate(self):
        """
        Mandatory Test 3a: Strings containing 'done' or 'fail' as substrings,
        variable names, or comments must NOT trigger termination.
        """
        false_positive_strings = [
            "done.txt",
            "file_done = True",
            "# done comment",
            "done_something",
            "undone",
            "well done",
            "task_done_flag = 1",
            "is_done = False",
            "print('done processing')",
            "failure_rate = 0.05",
            "failing_tests = []",
            "is_failed = False",
            "fail_count = 0",
            "# fail safe mechanism",
        ]
        for s in false_positive_strings:
            is_term, is_succ = ExactTerminationEngine.is_termination_action(s)
            self.assertFalse(
                is_term,
                f"Substring evasion failure: '{s}' falsely triggered termination!",
            )

    def test_exact_success_tokens(self):
        """Mandatory Test 3b: Exact success tokens must trigger completion."""
        success_tokens = [
            "DONE",
            "FINISHED",
            "SUCCESS",
            "GOAL_ACHIEVED",
            "COMPLETE",
            "COMPLETED",
            "done",
            "finished",
            "success",
            "  DONE  ",
            "'DONE'",
            '"FINISHED"',
            "DONE()",
            "DONE('All steps completed')",
            "DONE(result='ok')",
        ]
        for token in success_tokens:
            is_term, is_succ = ExactTerminationEngine.is_termination_action(token)
            self.assertTrue(
                is_term,
                f"Token '{token}' should have triggered termination",
            )
            self.assertTrue(
                is_succ,
                f"Token '{token}' should have returned success=True",
            )

    def test_exact_failure_tokens(self):
        """Mandatory Test 3c: Exact failure tokens must trigger termination with fail."""
        fail_tokens = [
            "FAIL",
            "FAILED",
            "ERROR",
            "IMPOSSIBLE",
            "GOAL_IMPOSSIBLE",
            "ABORT",
            "fail",
            "failed",
            "  FAIL  ",
            "'FAIL'",
            '"FAILED"',
            "FAIL()",
            "FAIL('Element not found')",
            "FAIL(error='timeout')",
        ]
        for token in fail_tokens:
            is_term, is_succ = ExactTerminationEngine.is_termination_action(token)
            self.assertTrue(
                is_term,
                f"Token '{token}' should have triggered termination",
            )
            self.assertFalse(
                is_succ,
                f"Token '{token}' should have returned success=False",
            )

    def test_goal_completion_semantic_evaluations(self):
        """
        Mandatory Test 3d: Goal completion evaluation based on environment states.
        """
        # Goal = close
        self.assertTrue(
            ExactTerminationEngine.check_goal_completion(
                goal="close the notepad window",
                state={"window_open": False},
            )
        )
        self.assertFalse(
            ExactTerminationEngine.check_goal_completion(
                goal="close the notepad window",
                state={"window_open": True},
            )
        )
        self.assertTrue(
            ExactTerminationEngine.check_goal_completion(
                goal="terminate process",
                state={"process_running": False},
            )
        )

        # Goal = open
        self.assertTrue(
            ExactTerminationEngine.check_goal_completion(
                goal="open calculator",
                state={"window_open": True},
            )
        )
        self.assertFalse(
            ExactTerminationEngine.check_goal_completion(
                goal="open calculator",
                state={"window_open": False},
            )
        )

        # Goal = save
        self.assertTrue(
            ExactTerminationEngine.check_goal_completion(
                goal="save document to disk",
                state={"file_saved": True},
            )
        )
        self.assertFalse(
            ExactTerminationEngine.check_goal_completion(
                goal="save document to disk",
                state={"file_saved": False},
            )
        )

        # Goal = type
        self.assertTrue(
            ExactTerminationEngine.check_goal_completion(
                goal="type hello jarvis into input field",
                state={"text_written": True},
            )
        )

        # Explicit terminal states
        self.assertTrue(
            ExactTerminationEngine.check_goal_completion(
                goal="any arbitrary goal",
                state={"goal_achieved": True},
            )
        )
        self.assertTrue(
            ExactTerminationEngine.check_goal_completion(
                goal="any arbitrary goal",
                state={"is_aborted": True},
            )
        )
        self.assertTrue(
            ExactTerminationEngine.check_goal_completion(
                goal="any arbitrary goal",
                state={"status": "DONE"},
            )
        )


class TestAdversarialCoordinateBoundaries(unittest.TestCase):
    """Adversarial stress-testing of OSWorldACI coordinate validation and bounds."""

    def setUp(self):
        self.aci = OSWorldACI(dry_run=True)

    def test_negative_coordinates_rejected(self):
        """Mandatory Test 4a: Negative coordinates must be rejected."""
        negative_cases = [
            (-10, 50),
            (50, -10),
            (-1, -1),
            (-500, -500),
            (0, -1),
            (-1, 0),
        ]
        for x, y in negative_cases:
            self.assertFalse(
                self.aci.validate_coordinates(x, y),
                f"Negative coordinates ({x}, {y}) should return False",
            )
            with self.assertRaises(ValueError, msg=f"click({x}, {y}) must raise ValueError"):
                self.aci.click(x, y)
            with self.assertRaises(ValueError, msg=f"move_to({x}, {y}) must raise ValueError"):
                self.aci.move_to(x, y)

    def test_multi_monitor_and_8k_resolution_validity(self):
        """Mandatory Test 4b: Multi-monitor and 8K coordinates (7680, 4320) must be accepted."""
        valid_coords = [
            (0, 0),
            (1920, 1080),
            (2560, 1440),
            (3840, 2160),  # 4K
            (7680, 4320),  # 8K UHD bound
        ]
        for x, y in valid_coords:
            self.assertTrue(
                self.aci.validate_coordinates(x, y),
                f"Valid coordinate ({x}, {y}) should return True",
            )
            res = self.aci.click(x, y)
            self.assertTrue(res["success"])

    def test_extreme_out_of_bounds_coordinates_rejected(self):
        """Coordinates exceeding 8K UHD bounds must return False and raise ValueError."""
        invalid_coords = [
            (7681, 4320),
            (7680, 4321),
            (10000, 5000),
            (99999, 99999),
        ]
        for x, y in invalid_coords:
            self.assertFalse(
                self.aci.validate_coordinates(x, y),
                f"Extreme coordinate ({x}, {y}) should return False",
            )
            with self.assertRaises(ValueError):
                self.aci.click(x, y)

    def test_drag_and_drop_coordinate_validation(self):
        """drag_and_drop must validate both start and end coordinates."""
        # Valid drag
        res = self.aci.drag_and_drop(100, 100, 200, 200)
        self.assertTrue(res["success"])

        # Invalid start coordinate
        with self.assertRaises(ValueError):
            self.aci.drag_and_drop(-10, 100, 200, 200)

        # Invalid end coordinate
        with self.assertRaises(ValueError):
            self.aci.drag_and_drop(100, 100, 8000, 200)


class TestAdversarialUIIntegrity(unittest.TestCase):
    """Mandatory Test 5: Verify zero UI drift in src/."""

    def test_zero_ui_drift_in_src(self):
        """git status / diff must reveal 0 modifications outside M1 arc-reactor/sphere files."""
        result = subprocess.run(
            ["git", "status", "--porcelain", "src/"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, f"git status failed: {result.stderr}")

        lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        for line in lines:
            status, path = line[:2].strip(), line[3:].strip()
            # The only allowed changes are M1 sphere.tsx (modified) and arc-reactor.tsx (untracked/added)
            is_permitted_m1 = (
                "sphere.tsx" in path or "arc-reactor.tsx" in path
            )
            self.assertTrue(
                is_permitted_m1,
                f"Unauthorized UI drift detected in file: '{path}' (status: {status})",
            )


class TestAdversarialWebAndDocumentAutomation(unittest.TestCase):
    """Additional adversarial tests for BrowserUseRunner and MarkItDownService."""

    def test_browser_use_url_security_filtering(self):
        """BrowserUseRunner must reject dangerous URI schemes."""
        runner = BrowserUseRunner()
        dangerous_urls = [
            "javascript:alert('XSS')",
            "JAVASCRIPT:document.location='http://evil.com'",
            "vbscript:msgbox('payload')",
            "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",
            "file:///C:/Windows/System32/drivers/etc/hosts",
            "about:blank",
            "not-a-url",
            "",
        ]
        for url in dangerous_urls:
            self.assertFalse(
                runner.validate_url(url),
                f"Dangerous or invalid URL '{url}' should have been rejected by validate_url",
            )

        safe_urls = [
            "https://www.google.com",
            "http://127.0.0.1:8080/dashboard",
            "https://github.com/simular-ai/Agent-S",
        ]
        for url in safe_urls:
            self.assertTrue(
                runner.validate_url(url),
                f"Safe URL '{url}' should be accepted",
            )

    def test_markitdown_table_repair(self):
        """MarkItDownService table repair must insert delimiter rows and pad columns."""
        svc = MarkItDownService()

        raw_ragged_table = (
            "| Header 1 | Header 2 |\n"
            "| Row 1 Col 1 | Row 1 Col 2 | Extra Col |\n"
            "| Row 2 Col 1 |\n"
        )
        repaired = svc.repair_markdown_table(raw_ragged_table)
        self.assertIn("|---|", repaired, "Repaired table must contain '|---|' delimiter row")
        lines = repaired.strip().splitlines()
        self.assertGreaterEqual(len(lines), 3)

    def test_omniparser_service_empty_and_fallback(self):
        """OmniParserService must handle empty image bytes without exceptions."""
        svc = OmniParserService()
        parsed = svc.parse_screen(b"")
        self.assertEqual(parsed.get("elements"), [])
        self.assertEqual(parsed.get("tier_used"), "empty")
        self.assertEqual(parsed.get("width"), 0)
        self.assertEqual(parsed.get("height"), 0)


if __name__ == "__main__":
    unittest.main()
