"""
tests/test_deep_adversarial.py
==============================
Exhaustive Adversarial Challenge & Stress Verification for Milestone M2 Iteration 2.
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
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.security.agent_shield import AgentShield
from backend.security.ecc_hooks import ECCHookDispatcher
from backend.memory.state_db import SessionDB
from backend.memory.instinct_engine import InstinctEngine


class TestDeepAdversarialAgentShield(unittest.TestCase):
    def setUp(self):
        self.shield = AgentShield()

    def test_secrets_comprehensive(self):
        raw_azure_key = "A" * 86 + "=="
        test_cases = [
            # 1. OpenAI
            ("openai_standard", "sk-proj-abcdef12345678901234567890abcdef"),
            ("openai_legacy", "sk-abcdef12345678901234567890abcdef"),
            # 2. Anthropic
            ("anthropic_std", "sk-ant-api03-abcdef12345678901234567890"),
            ("anthropic_short", "sk-ant-abcdef12345678901234567890"),
            # 3. AWS
            ("aws_key", "AKIAIOSFODNN7EXAMPLE"),
            ("aws_secret_sq", "aws_secret_access_key='wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'"),
            ("aws_secret_dq", 'aws_secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"'),
            ("aws_secret_colon", "aws_secret_access_key: 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'"),
            # 4. GitHub
            ("github_ghp", "ghp_" + "123456789012345678901234567890123456"),
            ("github_pat", "github_pat_11AAAAAAA0123456789012_abcdef"),
            # 5. Google
            ("google_gemini", "AIzaSyD-1234567890123456789012345678901"),
            # 6. Private keys
            ("rsa_private", "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0\n-----END RSA PRIVATE KEY-----"),
            ("openssh_private", "-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXktdjEAAAA\n-----END OPENSSH PRIVATE KEY-----"),
            # 7. JWT & Bearer
            ("jwt", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"),
            ("bearer_std", "Bearer a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0"),
            ("bearer_lower", "bearer a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0"),
            ("bearer_multispace", "Bearer   a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0"),
            ("bearer_tab", "Bearer\ta1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0"),
            # 8. Database URLs
            ("db_postgres", "postgres://user:password123@localhost:5432/jarvis"),
            ("db_mysql", "mysql://root:supersecret@127.0.0.1:3306/db"),
            ("db_mongodb", "mongodb+srv://admin:pass456@cluster0.mongodb.net/test"),
            # 9. Slack
            ("slack_token", "xoxb-" + "1234567890-123456789012-abcdef123456"),
            ("slack_webhook", "https://hooks.slack." + "com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"),
            # 10. Discord
            ("discord_webhook", "https://discord.com/api/webhooks/123456789012345678/abcdefg1234567-hijklmnop"),
            # 11. Telegram
            ("telegram_token", "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ123456789"),
            # 12. Azure Storage
            ("azure_unquoted", f"AccountKey={raw_azure_key}"),
            ("azure_dq", f'AccountKey="{raw_azure_key}"'),
            ("azure_sq", f"AccountKey='{raw_azure_key}'"),
            ("azure_spaces", f'AccountKey = "{raw_azure_key}"'),
            ("azure_conn_str_dq", f'DefaultEndpointsProtocol=https;AccountName=test;AccountKey="{raw_azure_key}";EndpointSuffix=core.windows.net'),
            ("azure_conn_str_unquoted", f"DefaultEndpointsProtocol=https;AccountName=test;AccountKey={raw_azure_key};EndpointSuffix=core.windows.net"),
            # 13. Stripe
            ("stripe_live", "sk_live_" + "1234567890abcdefghijklmn"),
            # 14. Password / Credentials
            ("password_sq", "password: 'superSecretPassword123'"),
            ("password_dq", 'password: "superSecretPassword123"'),
            ("apikey_sq", "api_key: 'my_secret_token_12345'"),
        ]

        for name, secret in test_cases:
            with self.subTest(secret_name=name):
                res = self.shield.scan_input(f"Preamble text: {secret} postamble text")
                self.assertFalse(res.passed, f"Failed to detect secret: {name}")
                self.assertEqual(res.violation_type, "secret_leak")

                # Verify sanitization / redaction
                redacted = self.shield.sanitize_output(f"Output with {secret}")
                self.assertNotIn(secret, redacted, f"Failed to redact secret: {name}")

    def test_destructive_commands_and_split_flags(self):
        destructive = [
            "rm -rf /",
            "rm -f -r /",
            "rm -r -f /",
            "rm --recursive --force /",
            "rm --force --recursive /",
            "rm -rf *",
            "rm -rf ~",
            "rm -rf .",
            "del /s /q C:\\*",
            "del /q /s C:\\*",
            "del /f /s /q C:\\*",
            "del /q /s /f C:\\*",
            "del /s/q C:\\*",
            "del /q/s C:\\*",
            "del /s /f /q C:\\Users",
            "rmdir /s /q C:\\Users",
            "rmdir /q /s C:\\temp",
            "rd /s /q D:\\",
            "rd /q /s D:\\",
            "r\x00m -rf /",
            "r\x00\x00m -r\x00f /",
            "d\x00el /s /q C:\\*",
            "format C:",
            "format-volume -DriveLetter C",
            "diskpart /s x.txt",
            "mkfs.ext4 /dev/sda1",
            "dd if=/dev/zero of=/dev/sda",
            ":(){ :|:& };:",
            "reg delete HKLM\\Software\\Jarvis /f",
            "regedit /s evil.reg",
            "shutdown /s /t 0",
            "shutdown /r /t 0",
            # Chained
            "echo safe && rm -rf /",
            "echo safe; del /s /q C:\\*",
            "dir || rmdir /s /q C:\\temp",
            "type test.txt | rm -rf /",
        ]
        for cmd in destructive:
            with self.subTest(cmd=cmd):
                self.assertFalse(self.shield.validate_command(cmd), f"Destructive command allowed: {cmd}")

    def test_system32_and_protected_paths(self):
        paths_to_block_write = [
            "C:\\Windows\\System32\\cmd.exe",
            "C:\\Windows\\System32\\drivers\\etc\\hosts",
            "system32/evil.bat",
            "c:/windows/system32/cmd.exe",
            "src/layouts/jarvis-layout.tsx",
            "src/components/widgets/arc-reactor.tsx",
            "package.json",
            "tsconfig.json",
            "vite.config.ts",
            ".env",
            ".env.production",
            ".env.local",
            "credentials.json",
            "/etc/passwd",
            "/etc/shadow",
            "../../.env",
            "folder/../../package.json",
            "file\x00.env",
        ]
        for p in paths_to_block_write:
            with self.subTest(path=p):
                allowed, _ = self.shield.verify_file_path(p, write_mode=True)
                self.assertFalse(allowed, f"Write allowed to protected path: {p}")

    def test_nested_tool_arguments_comprehensive(self):
        # Nested secrets
        secret_args = {
            "outer": {
                "inner": {
                    "token": "sk-proj-123456789012345678901234"
                }
            }
        }
        allowed, reason = self.shield.validate_tool_call("any_tool", secret_args)
        self.assertFalse(allowed)

        # Destructive command in tool arguments
        cmd_args = {"command": "rm -f -r /"}
        allowed, reason = self.shield.validate_tool_call("bash_executor", cmd_args)
        self.assertFalse(allowed)

        cmd_args2 = {"cmd": "del /s /q /f C:\\*"}
        allowed, reason = self.shield.validate_tool_call("cmd_runner", cmd_args2)
        self.assertFalse(allowed)

        script_args = {"script": "rmdir /q /s C:\\"}
        allowed, reason = self.shield.validate_tool_call("powershell_exec", script_args)
        self.assertFalse(allowed)


class TestDeepAdversarialECCHooks(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="ecc_deep_")
        self.obs_path = Path(self.temp_dir) / "observations.jsonl"
        self.dispatcher = ECCHookDispatcher(log_path=self.obs_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_concurrent_writes_zero_data_loss(self):
        num_threads = 20
        ops_per_thread = 25
        expected = num_threads * ops_per_thread
        barrier = threading.Barrier(num_threads)
        errors = []

        def worker(tid):
            try:
                barrier.wait(timeout=10.0)
                for i in range(ops_per_thread):
                    r = self.dispatcher.post_tool_use(
                        tool_name=f"tool_{tid}",
                        args={"thread": tid, "i": i},
                        result=f"res_{tid}_{i}",
                        duration_ms=10.0,
                        session_id=f"sess_{tid}",
                    )
                    if not r.recorded:
                        errors.append(f"Not recorded: {r.error}")
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
        for t in threads: t.start()
        for t in threads: t.join(timeout=30.0)

        self.assertEqual(len(errors), 0, f"Errors: {errors}")
        with open(self.obs_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]

        self.assertEqual(len(lines), expected, f"Data loss! {len(lines)} vs {expected}")
        for idx, line in enumerate(lines):
            try:
                json.loads(line)
            except Exception as e:
                self.fail(f"Corrupt line at {idx}: {e}")

    def test_pre_tool_and_post_tool_security(self):
        # Pre tool blocks destructive
        pre = self.dispatcher.pre_tool_use("bash_executor", {"command": "rm -rf /"})
        self.assertFalse(pre.allowed)

        # Post tool redacts secrets from result
        post = self.dispatcher.post_tool_use(
            tool_name="web_fetch",
            args={"url": "https://api.com"},
            result="Secret: sk-proj-123456789012345678901234 here",
        )
        self.assertTrue(post.recorded)
        self.assertNotIn("sk-proj-123456789012345678901234", post.observation["result_summary"])


class TestDeepAdversarialSessionDB(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="db_deep_")
        self.db_path = Path(self.temp_dir) / "state.db"
        self.db = SessionDB(db_path=self.db_path)

    def tearDown(self):
        try:
            self.db.close()
        except Exception:
            pass
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_schema_and_wal(self):
        self.assertEqual(self.db.get_schema_version(), 12)
        conn = sqlite3.connect(str(self.db_path))
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode;")
        self.assertEqual(cur.fetchone()[0].lower(), "wal")
        conn.close()

    def test_foreign_key_cascade_full(self):
        # Create session
        sid = self.db.create_session(title="Cascade Full Test")
        # Add messages and tool calls
        for i in range(10):
            mid = self.db.add_message(
                session_id=sid,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Cascade message item {i} with identifier cascade_tok_{i}",
            )
            self.db.record_tool_call(
                session_id=sid,
                tool_name="tool_cascade",
                arguments={"index": i},
                result={"status": "cascade_ok"},
                message_id=mid,
            )

        # Confirm data in DB
        msgs = self.db.get_messages(sid, active_only=False)
        self.assertEqual(len(msgs), 10)
        fts_hits = self.db.search_fts("cascade_tok_3")
        self.assertGreaterEqual(len(fts_hits), 1)

        # Delete session
        deleted = self.db.delete_session(sid)
        self.assertTrue(deleted)

        # Verify cascades using raw connection with FK ON
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA foreign_keys = ON;")
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM messages WHERE session_id = ?", (sid,))
        self.assertEqual(cur.fetchone()[0], 0, "Messages not deleted by cascade")

        cur.execute("SELECT COUNT(*) FROM tool_calls WHERE session_id = ?", (sid,))
        self.assertEqual(cur.fetchone()[0], 0, "Tool calls not deleted by cascade")

        cur.execute("SELECT COUNT(*) FROM fts_messages")
        self.assertEqual(cur.fetchone()[0], 0, "FTS5 index not cleaned up by trigger")
        conn.close()

    def test_parent_session_set_null(self):
        parent_id = self.db.create_session(title="Parent")
        child_id = self.db.create_session(title="Child", parent_session_id=parent_id)

        child = self.db.get_session(child_id)
        self.assertEqual(child["parent_session_id"], parent_id)

        # Delete parent
        self.db.delete_session(parent_id)

        child_after = self.db.get_session(child_id)
        self.assertIsNotNone(child_after)
        self.assertIsNone(child_after["parent_session_id"])

    def test_concurrency_15_threads(self):
        num_threads = 15
        ops_per_thread = 20
        barrier = threading.Barrier(num_threads)
        errors = []

        def worker(tid):
            try:
                barrier.wait(timeout=10.0)
                sid = f"conc_sess_{tid}"
                self.db.create_session(session_id=sid, title=f"Thread {tid}")
                for i in range(ops_per_thread):
                    mid = self.db.add_message(
                        session_id=sid,
                        role="user",
                        content=f"Thread {tid} content iteration {i} unique_kw_{tid}_{i}",
                    )
                    self.db.record_tool_call(
                        session_id=sid,
                        tool_name="worker_tool",
                        arguments={"thread": tid, "i": i},
                        result="success",
                        message_id=mid,
                    )
                    self.db.search_fts(f"unique_kw_{tid}_{i}")
                    if i % 3 == 0 and mid > 0:
                        self.db.soft_compact_messages(sid, [mid])
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
        for t in threads: t.start()
        for t in threads: t.join(timeout=35.0)

        self.assertEqual(len(errors), 0, f"Concurrency errors: {errors}")
        conn = sqlite3.connect(str(self.db_path))
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM messages")
        self.assertEqual(cur.fetchone()[0], num_threads * ops_per_thread)
        conn.close()

    def test_malformed_fts_queries(self):
        sid = self.db.create_session(title="FTS Resilience")
        self.db.add_message(sid, "user", "The quick brown fox jumps over the lazy dog")
        malformed = [
            "", "   ", '"', '"""', '"unclosed quote', 'unclosed"', 'foo:bar', ':::***',
            '*', '***', 'AND', 'OR', 'NOT', 'NEAR', 'AND OR NOT NEAR', 'AND "hello"',
            'hello AND', 'hello OR', 'hello NOT', '(unbalanced', 'unbalanced)', '(((())))',
            '{column: value}', '[bracket: test]', '+ - ^ ~ < > =', 'content: quick',
            'null\x00byte', "a" * 1500, ":)*!@#$%^&*()_+=-`~[]{}\\|;':\",./<>?"
        ]
        for q in malformed:
            with self.subTest(query=q):
                try:
                    res = self.db.search_fts(q)
                    self.assertIsInstance(res, list)
                except Exception as e:
                    self.fail(f"search_fts crashed on query '{q}': {e}")


if __name__ == "__main__":
    unittest.main()
