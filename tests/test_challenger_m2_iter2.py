"""
tests/test_challenger_m2_iter2.py
=================================
Empirical Adversarial Challenge Suite for Milestone M2 Iteration 2:
  1. Empirical Verification of Remediations V1..V7
  2. Fresh GNU Long Flags and Compound Syntax Evasions
  3. Deep Heterogeneous Credential Nesting Stress (All 14 Secret Types)
  4. Path Traversal & System32 Subpath Write Evasions
  5. 20-Thread High-Concurrency Telemetry Stress (500 records)
  6. Multi-tool Instinct Contradiction Counting and Fault-Tolerance Stress

Authored by: challenger_m2_iter2_1 (teamwork_challenger)
"""

import json
import os
import shutil
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.security.agent_shield import AgentShield
from backend.security.ecc_hooks import ECCHookDispatcher
from backend.memory.instinct_engine import InstinctEngine
from backend.memory.state_db import SessionDB


class TestM2Iter2EmpiricalVerifications(unittest.TestCase):
    """Empirical verification that all 7 findings (V1..V7) are definitively remediated."""

    def setUp(self):
        self.shield = AgentShield()

    def test_v1_quoted_and_spaced_azure_keys_blocked_and_redacted(self):
        """V1 Verification: Quoted and spaced Azure AccountKey must be blocked and redacted."""
        raw_key = ("A" * 86) + "=="
        test_cases = [
            f'AccountKey="{raw_key}"',
            f"AccountKey='{raw_key}'",
            f'AccountKey = "{raw_key}"',
            f"AccountKey = '{raw_key}'",
            f'AccountKey="{raw_key}";EndpointSuffix=core.windows.net',
            f'accountkey="{raw_key}"',
            f'AccountKey={raw_key}',
            f'SharedAccessSignature="sv=2020-08-04&ss=b&srt=sco&sp=rwdlacupx&se=2026-11-10T18:00:00Z&sig=1234567890123456789012345678901234567890"',
        ]

        for tc in test_cases:
            with self.subTest(azure_key_variant=tc):
                res = self.shield.scan_input(f"Connecting with {tc}")
                self.assertFalse(res.passed, f"Quoted/spaced Azure key bypassed scan_input: {tc}")
                self.assertEqual(res.violation_type, "secret_leak")

                # Verify redaction
                redacted = self.shield.sanitize_output(f"Prefix {tc} Suffix")
                self.assertNotIn(raw_key, redacted, f"Raw key leaked in sanitized output: {tc}")

    def test_v2_destructive_commands_split_and_reordered_flags_blocked(self):
        """V2 Verification: Split flags, reordered flags, and GNU long flags must all be blocked."""
        reordered_and_gnu_commands = [
            "rm -f -r /",
            "rm -r -f /",
            "rm --recursive --force /",
            "rm --force --recursive /",
            "rm -r --force /",
            "rm --force -r /",
            "rm -f --recursive /",
            "rm --recursive -f /",
            "rm -R -f /",
            "rm -f -R /",
            "rm -rf /",
            "rm -fr /",
            "del /q /s /f C:\\*",
            "del /s /f /q C:\\*",
            "del /f /q /s C:\\*",
            "del /q /f /s C:\\*",
            "del /s /q C:\\*",
            "del /q /s C:\\*",
            "rmdir /q /s C:\\Users",
            "rmdir /s /q C:\\Users",
            "rd /q /s C:\\temp",
            "rd /s /q C:\\temp",
            "format C:",
            "format-volume -DriveLetter C",
            "diskpart /s wipe.txt",
            "mkfs.ext4 /dev/sda1",
            "dd if=/dev/zero of=/dev/sda",
            ":(){ :|:& };:",
            "reg delete HKLM\\Software\\Jarvis /f",
            "regedit /s evil.reg",
            "shutdown /s /t 0",
            "shutdown /r /t 0",
        ]

        allowed_destructive = []
        for cmd in reordered_and_gnu_commands:
            if self.shield.validate_command(cmd):
                allowed_destructive.append(cmd)

        self.assertEqual(
            allowed_destructive,
            [],
            f"V2 Failed: The following destructive commands bypassed validation: {allowed_destructive}",
        )

    def test_v3_null_byte_command_splitting_blocked(self):
        """V3 Verification: Null byte insertions in command or flags must not bypass validation."""
        null_byte_commands = [
            "r\x00m -rf /",
            "rm\x00 -rf /",
            "r\x00m -r -f /",
            "rm -\x00r\x00f /",
            "del\x00 /s /q C:\\*",
            "rm\x00dir /s /q C:\\Users",
        ]

        for cmd in null_byte_commands:
            with self.subTest(null_command=repr(cmd)):
                allowed = self.shield.validate_command(cmd)
                self.assertFalse(allowed, f"V3 Failed: Null byte command was permitted: {repr(cmd)}")

    def test_v4_system32_subpaths_blocked_for_write(self):
        """V4 Verification: Writing to any subpath inside System32 must be blocked."""
        system32_paths = [
            "C:\\Windows\\System32\\cmd.exe",
            "C:\\Windows\\System32\\drivers\\etc\\hosts",
            "system32/evil.bat",
            "system32\\malware.exe",
            "C:/Windows/system32/sub/file.dll",
            "C:\\Windows\\System32",
            "C:/Windows/System32/",
            "System32/cmd.exe",
        ]

        allowed_writes = []
        for p in system32_paths:
            allowed, reason = self.shield.verify_file_path(p, write_mode=True)
            if allowed:
                allowed_writes.append(p)

        self.assertEqual(
            allowed_writes,
            [],
            f"V4 Failed: System32 subpaths allowed for write: {allowed_writes}",
        )

    def test_v5_nested_secrets_in_tool_calls_blocked(self):
        """V5 Verification: Secrets deeply nested in dicts, lists, sets, and tuples must be blocked."""
        nested_tool_calls = [
            # Level 2 Dict
            ("tool1", {"payload": {"token": "sk-proj-123456789012345678901234"}}),
            # Level 3 Dict
            ("tool2", {"config": {"headers": {"Authorization": "Bearer a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0"}}}),
            # List of dicts
            ("tool3", {"items": [{"auth": "ghp_" + "123456789012345678901234567890123456"}]}),
            # Tuple inside dict
            ("tool4", {"creds": ("aws_secret_key", "aws_secret_access_key='wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'")}),
            # Set inside dict
            ("tool5", {"db": {"postgres://jarvis_user:super_secret_pw123@db.prod.internal:5432/jarvis_state"}}),
            # 5-level deep hybrid structure
            ("tool6", {"l1": [{"l2": {"l3": [{"l4": {"l5": "AIzaSyD-1234567890123456789012345678901"}}]}}]}),
        ]

        for tool_name, args in nested_tool_calls:
            with self.subTest(tool=tool_name):
                allowed, reason = self.shield.validate_tool_call(tool_name, args)
                self.assertFalse(allowed, f"V5 Failed: Nested secret was allowed for {tool_name}: {reason}")
                self.assertIn("prohibited pattern", reason)

    def test_v6_ecc_concurrent_telemetry_no_data_loss(self):
        """V6 Verification: 10 threads logging concurrently must have 0% loss."""
        td = tempfile.mkdtemp(prefix="jarvis_v6_test_")
        tp = Path(td) / "obs.jsonl"
        disp = ECCHookDispatcher(log_path=tp)

        num_threads = 10
        ops_per_thread = 15
        expected_total = num_threads * ops_per_thread
        barrier = threading.Barrier(num_threads)

        def worker(tid):
            barrier.wait(timeout=10.0)
            for i in range(ops_per_thread):
                disp.post_tool_use(f"tool_{tid}", {"iteration": i}, f"result_{i}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15.0)

        with open(tp, "r", encoding="utf-8") as f:
            lines = [l for l in f if l.strip()]

        shutil.rmtree(td, ignore_errors=True)

        self.assertEqual(len(lines), expected_total, f"V6 Failed: Expected {expected_total} lines, got {len(lines)}")
        # Check all lines are valid JSON
        for line in lines:
            data = json.loads(line)
            self.assertIn("tool_name", data)
            self.assertIn("status", data)

    def test_v7_instinct_contradiction_loss_remediated(self):
        """V7 Verification: parse_observations must record both confirmations and contradictions."""
        td = tempfile.mkdtemp(prefix="jarvis_v7_test_")
        tp = Path(td) / "obs.jsonl"
        inst_dir = Path(td) / "instincts"
        eng = InstinctEngine(instincts_dir=inst_dir, observations_path=tp)

        with open(tp, "w", encoding="utf-8") as f:
            for _ in range(3):
                f.write(json.dumps({"tool_name": "git", "status": "success"}) + "\n")
            for _ in range(2):
                f.write(json.dumps({"tool_name": "git", "status": "error"}) + "\n")

        inferred = eng.parse_observations()
        shutil.rmtree(td, ignore_errors=True)

        self.assertEqual(len(inferred), 1)
        inst = inferred[0]
        self.assertEqual(inst.confirmations, 3, f"Expected 3 confirmations, got {inst.confirmations}")
        self.assertEqual(inst.contradictions, 2, f"Expected 2 contradictions, got {inst.contradictions}")
        # Expected score: 0.50 + 0.05*3 - 0.10*2 = 0.50 + 0.15 - 0.20 = 0.45
        self.assertAlmostEqual(inst.confidence, 0.45, places=3)


class TestM2Iter2FreshAdversarialEvasions(unittest.TestCase):
    """Fresh, creative adversarial evasions challenging the remediations."""

    def setUp(self):
        self.shield = AgentShield()

    def test_fresh_gnu_long_flags_and_subshell_chaining(self):
        """Adversarial stress: GNU long flags, mixed flags, and shell subshell/chaining evasions."""
        evasive_destructive_payloads = [
            "rm --recursive --force /",
            "rm --force --recursive /",
            "rm --recursive -f /",
            "rm -f --recursive /",
            "rm --force -r /",
            "rm -r --force /",
            "rm --recursive --force ~",
            "rm --recursive --force *",
            "rm --recursive --force .",
            "rm -rf *",
            "rm -r -f *",
            "rm -f -r ~",
            "echo 'benign' ; rm --recursive --force /",
            "ls -la && rm --force --recursive /",
            "true || rm -r -f /",
            "powershell -Command \"rm -rf /\"",
            "cmd.exe /c \"del /s /f /q C:\\*\"",
            "RM --RECURSIVE --FORCE /",
            "Rm -F -R /",
            "Del /S /F /Q C:\\*",
            "Rmdir /Q /S C:\\Users",
        ]

        for cmd in evasive_destructive_payloads:
            with self.subTest(evasive_cmd=cmd):
                self.assertFalse(
                    self.shield.validate_command(cmd),
                    f"Evasive destructive command bypassed AgentShield: {cmd}",
                )

    def test_fresh_deep_heterogeneous_credentials_all_14_patterns(self):
        """Adversarial stress: Placing all 14 secret patterns deep inside 10-level nested structures."""
        all_14_secrets = [
            ("openai", "sk-proj-abcde12345678901234567890abcdef"),
            ("anthropic", "sk-ant-api03-abcdef12345678901234567890"),
            ("aws_key", "AKIAIOSFODNN7EXAMPLE"),
            ("aws_sec", "aws_secret_access_key='wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'"),
            ("github", "ghp_" + "123456789012345678901234567890123456"),
            ("google", "AIzaSyD-1234567890123456789012345678901"),
            ("rsa_key", "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0\n-----END RSA PRIVATE KEY-----"),
            ("jwt", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"),
            ("bearer", "Bearer a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0"),
            ("db_url", "postgres://jarvis_user:super_secret_pw123@db.prod.internal:5432/jarvis_state"),
            ("slack", "xoxb-" + "1234567890-123456789012-abcdef123456"),
            ("discord", "https://discord.com/api/webhooks/123456789012345678/abcdefg1234567-hijklmnop"),
            ("azure", 'AccountKey="' + ("A" * 86) + '=="'),
            ("stripe", "sk_live_" + "1234567890abcdefghijklmn"),
        ]

        for name, secret in all_14_secrets:
            # Construct a 10-level deep nested structure containing mixed types
            deep_payload: Dict[str, Any] = {
                "metadata": {"depth": 10},
                "nested_array": [
                    None,
                    42,
                    False,
                    {
                        "level3": [
                            (
                                "tuple_elem",
                                {
                                    "level5": {
                                        "set_holder": {
                                            "level7": [
                                                {"target_secret": secret}
                                            ]
                                        }
                                    }
                                },
                            )
                        ]
                    },
                ],
            }

            with self.subTest(secret_name=name):
                allowed, reason = self.shield.validate_tool_call("test_tool", deep_payload)
                self.assertFalse(
                    allowed,
                    f"10-level nested secret '{name}' bypassed validate_tool_call!",
                )

    def test_fresh_high_concurrency_20_threads_telemetry_stress(self):
        """
        Adversarial Concurrency Stress:
        20 simultaneous threads hammering ECCHookDispatcher with 25 records each = 500 records.
        Verifies 100% written, 0 lost, 0 line tearing, and valid JSON lines.
        """
        td = tempfile.mkdtemp(prefix="jarvis_stress_20t_")
        tp = Path(td) / "obs_concurrent.jsonl"
        disp = ECCHookDispatcher(log_path=tp)

        num_threads = 20
        ops_per_thread = 25
        expected_total = num_threads * ops_per_thread  # 500 records
        barrier = threading.Barrier(num_threads)
        errors: List[Exception] = []

        def stress_writer(tid: int):
            try:
                barrier.wait(timeout=10.0)
                for i in range(ops_per_thread):
                    res = disp.post_tool_use(
                        tool_name=f"thread_tool_{tid}",
                        args={"tid": tid, "seq": i, "payload": f"worker_{tid}_iter_{i}"},
                        result={"status": "completed", "output": f"ok_{tid}_{i}"},
                        status="success" if i % 4 != 0 else "error",
                        duration_ms=12.5 + i,
                        session_id=f"session-{tid}",
                    )
                    if not res.recorded:
                        errors.append(RuntimeError(f"Record failed: {res.error}"))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=stress_writer, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30.0)

        self.assertEqual(len(errors), 0, f"Thread errors during 20-thread stress: {errors}")

        with open(tp, "r", encoding="utf-8") as f:
            raw_lines = f.readlines()

        shutil.rmtree(td, ignore_errors=True)

        # 1. Total count check
        self.assertEqual(
            len(raw_lines),
            expected_total,
            f"Concurrency Data Loss: Expected {expected_total} lines, but found {len(raw_lines)}. Lost: {expected_total - len(raw_lines)}",
        )

        # 2. Integrity and parsing check: every line must be valid JSON with expected fields
        parsed_records = []
        for idx, line in enumerate(raw_lines):
            try:
                rec = json.loads(line.strip())
                parsed_records.append(rec)
            except Exception as e:
                self.fail(f"Corrupted/torn line at index {idx}: '{line[:100]}...' Error: {e}")

        self.assertEqual(len(parsed_records), expected_total)

    def test_fresh_multi_tool_instinct_learning_and_fault_tolerance(self):
        """
        Adversarial Stress on InstinctEngine:
        1. Multi-tool simultaneous contradiction and confirmation tracking.
        2. Resilience against corrupt/empty/partial lines in observations.jsonl.
        3. Confidence formula precision and threshold enforcement.
        """
        td = tempfile.mkdtemp(prefix="jarvis_multi_instinct_")
        tp = Path(td) / "obs_mixed.jsonl"
        inst_dir = Path(td) / "instincts"
        eng = InstinctEngine(instincts_dir=inst_dir, observations_path=tp)

        # Write mixed data: valid, corrupt, empty lines, and multiple tools
        lines = [
            "",  # empty line
            "   ",  # whitespace line
            "{malformed json line",  # corrupt line
            json.dumps({"invalid_record": True}),  # missing tool_name
            # Tool A: 5 successes, 2 errors (total 7) -> conf = 0.50 + 0.25 - 0.20 = 0.55
            json.dumps({"tool_name": "tool_A", "status": "success", "args": {"a": 1}}),
            json.dumps({"tool_name": "tool_A", "status": "success", "args": {"a": 2}}),
            json.dumps({"tool_name": "tool_A", "status": "error", "args": {"a": 3}}),
            json.dumps({"tool_name": "tool_A", "status": "success", "args": {"a": 4}}),
            json.dumps({"tool_name": "tool_A", "status": "error", "args": {"a": 5}}),
            json.dumps({"tool_name": "tool_A", "status": "success", "args": {"a": 6}}),
            json.dumps({"tool_name": "tool_A", "status": "success", "args": {"a": 7}}),
            "NOT_JSON_AT_ALL",  # invalid line
            # Tool B: 4 successes, 0 errors -> conf = 0.50 + 0.20 = 0.70
            json.dumps({"tool_name": "tool_B", "status": "success"}),
            json.dumps({"tool_name": "tool_B", "status": "success"}),
            json.dumps({"tool_name": "tool_B", "status": "success"}),
            json.dumps({"tool_name": "tool_B", "status": "success"}),
            # Tool C: 2 successes, 4 errors -> below min success threshold of 3, should NOT be inferred
            json.dumps({"tool_name": "tool_C", "status": "success"}),
            json.dumps({"tool_name": "tool_C", "status": "success"}),
            json.dumps({"tool_name": "tool_C", "status": "error"}),
            json.dumps({"tool_name": "tool_C", "status": "error"}),
            json.dumps({"tool_name": "tool_C", "status": "error"}),
            json.dumps({"tool_name": "tool_C", "status": "error"}),
        ]

        with open(tp, "w", encoding="utf-8") as f:
            for l in lines:
                f.write(l + "\n")

        inferred = eng.parse_observations()
        shutil.rmtree(td, ignore_errors=True)

        tool_map = {inst.id: inst for inst in inferred}

        # tool_A must be present with exactly 5 confirmations and 2 contradictions
        self.assertIn("obs-tool_A", tool_map)
        inst_a = tool_map["obs-tool_A"]
        self.assertEqual(inst_a.confirmations, 5)
        self.assertEqual(inst_a.contradictions, 2)
        self.assertAlmostEqual(inst_a.confidence, 0.55, places=3)

        # tool_B must be present with exactly 4 confirmations and 0 contradictions
        self.assertIn("obs-tool_B", tool_map)
        inst_b = tool_map["obs-tool_B"]
        self.assertEqual(inst_b.confirmations, 4)
        self.assertEqual(inst_b.contradictions, 0)
        self.assertAlmostEqual(inst_b.confidence, 0.70, places=3)

        # tool_C has only 2 successes (< 3), so it must not be present
        self.assertNotIn("obs-tool_C", tool_map)


def run_challenger_m2_iter2_suite():
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTests(loader.loadTestsFromTestCase(TestM2Iter2EmpiricalVerifications))
    suite.addTests(loader.loadTestsFromTestCase(TestM2Iter2FreshAdversarialEvasions))

    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)


if __name__ == "__main__":
    result = run_challenger_m2_iter2_suite()
    sys.exit(0 if result.wasSuccessful() else 1)
