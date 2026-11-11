"""
tests/test_m2_adversarial_deep.py
=================================
Deep adversarial stress testing harness for M2 Iteration 2 components:
1. InstinctEngine contradiction tracking, confidence formula boundaries, and observation parsing resilience.
2. ContextCompressor orphaned tool call pruning (empty call_ids, populated call_ids, middle-compressed tool calls, head/tail preservation).
3. ToolDispatcher high-concurrency loop guard stress, test_echo, and read-only vs mutating batching.
4. HermesBrain multi-sample interrupt latency benchmarking (mid-stream streaming interrupt vs pre-token prompt assembly interrupt).
"""

import asyncio
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.core.hermes_brain import HermesBrain, BrainEvent
from backend.core.tool_dispatcher import (
    ToolDispatcher,
    ToolLoopHaltException,
    READ_ONLY_TOOLS,
)
from backend.core.context_compressor import ContextCompressor, SUMMARY_PREFIX, SUMMARY_END_MARKER
from backend.memory.instinct_engine import InstinctEngine, Instinct
from backend.memory.state_db import SessionDB


class AdversarialInstinctEngineTests(unittest.TestCase):
    """Stress tests for InstinctEngine contradiction tracking and confidence scoring."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="instinct_adv_"))
        self.instincts_dir = self.temp_dir / "instincts"
        self.obs_file = self.temp_dir / "observations.jsonl"
        self.engine = InstinctEngine(
            instincts_dir=self.instincts_dir,
            observations_path=self.obs_file,
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_contradiction_tracking_with_interleaved_observations(self):
        """Test interleaved successes and failures across multiple tools."""
        lines = [
            {"tool_name": "bash", "status": "success", "args": {"cmd": "ls"}},
            {"tool_name": "python", "status": "failed", "args": {"code": "1/0"}},
            {"tool_name": "bash", "status": "failed", "args": {"cmd": "invalid"}},
            {"tool_name": "bash", "status": "success", "args": {"cmd": "pwd"}},
            {"tool_name": "python", "status": "success", "args": {"code": "x=1"}},
            {"tool_name": "bash", "status": "success", "args": {"cmd": "whoami"}},
            {"tool_name": "bash", "status": "failed", "args": {"cmd": "bad"}},
            {"tool_name": "python", "status": "error", "args": {"code": "syntax error"}},
            {"tool_name": "git", "status": "success", "args": {"sub": "status"}},  # Only 1 success
        ]

        with open(self.obs_file, "w", encoding="utf-8") as f:
            for l in lines:
                f.write(json.dumps(l) + "\n")

        instincts = self.engine.parse_observations()
        instinct_map = {inst.id: inst for inst in instincts}

        # git has only 1 success (<3) -> should not produce an instinct
        self.assertNotIn("obs-git", instinct_map)

        # bash has 3 successes and 2 failures -> should produce an instinct with exact confirmations and contradictions
        self.assertIn("obs-bash", instinct_map)
        bash_inst = instinct_map["obs-bash"]
        self.assertEqual(bash_inst.confirmations, 3)
        self.assertEqual(bash_inst.contradictions, 2)
        self.assertEqual(bash_inst.occurrences, 5)

        # Score calculation: 0.50 + 0.05*3 - 0.10*2 = 0.50 + 0.15 - 0.20 = 0.45
        self.assertEqual(bash_inst.confidence, 0.45)

        # python has 1 success and 2 failures -> not >=3 successes, so not produced
        self.assertNotIn("obs-python", instinct_map)

    def test_malformed_and_adversarial_json_lines_in_observations(self):
        """Verify resilience against malformed lines, huge tokens, missing keys."""
        raw_content = (
            "\n"
            "   \n"
            "NOT_JSON_AT_ALL\n"
            '{"incomplete": true\n'
            '{"tool_name": "", "status": "success"}\n'
            '{"status": "success"}\n'
            '{"tool_name": "valid_tool", "status": "success", "args": {"valid": true}}\n'
            '{"tool_name": "valid_tool", "status": "success"}\n'
            '{"tool_name": "valid_tool", "status": "success"}\n'
            '{"tool_name": "valid_tool", "status": "unknown_status_counts_as_fail"}\n'
            '{"tool_name": "valid_tool", "status": "error"}\n'
            "\x00\x01\x02\n"
        )
        self.obs_file.write_text(raw_content, encoding="utf-8")

        instincts = self.engine.parse_observations()
        self.assertEqual(len(instincts), 1)
        inst = instincts[0]
        self.assertEqual(inst.id, "obs-valid_tool")
        self.assertEqual(inst.confirmations, 3)
        self.assertEqual(inst.contradictions, 2)  # unknown_status and error count as contradictions
        self.assertEqual(inst.confidence, 0.45)

    def test_confidence_formula_mathematical_boundaries(self):
        """Stress-test the score_instinct formula at extreme boundaries."""
        # Baseline (0, 0) -> 0.50
        self.assertEqual(self.engine.score_instinct("t", 0, 0), 0.50)

        # Confirmations boundary: 10 confirmations -> 0.50 + 0.50 = 1.0
        self.assertEqual(self.engine.score_instinct("t", 10, 0), 1.0)
        # Overflow confirmation: 1000 confirmations -> clamped to 1.0
        self.assertEqual(self.engine.score_instinct("t", 1000, 0), 1.0)

        # Contradictions boundary: 5 contradictions -> 0.50 - 0.50 = 0.0
        self.assertEqual(self.engine.score_instinct("t", 0, 5), 0.0)
        # Overflow contradiction: 1000 contradictions -> clamped to 0.0
        self.assertEqual(self.engine.score_instinct("t", 0, 1000), 0.0)

        # Balance: 4 confirmations, 2 contradictions -> 0.50 + 0.20 - 0.20 = 0.50
        self.assertEqual(self.engine.score_instinct("t", 4, 2), 0.50)

        # Pruning boundary test
        self.engine.record_instinct("high_rule", "do something good", confirmations=10, contradictions=0)
        self.engine.record_instinct("low_rule", "do something bad", confirmations=0, contradictions=3)

        active = self.engine.get_active_instincts(min_confidence=0.70)
        active_triggers = [a["trigger"] for a in active]
        self.assertIn("high_rule", active_triggers)
        self.assertNotIn("low_rule", active_triggers)

        # Prune with min_confidence=0.50
        pruned_count = self.engine.prune_instincts(min_confidence=0.50)
        self.assertGreaterEqual(pruned_count, 1)


class AdversarialContextCompressorTests(unittest.TestCase):
    """Stress tests for ContextCompressor edge cases and orphaned tool pruning."""

    def setUp(self):
        self.compressor = ContextCompressor(max_tokens=200, threshold_ratio=0.50)

    def test_orphaned_tools_pruning_with_empty_call_ids(self):
        """Verify that when call_ids is empty set, orphaned tools are pruned cleanly."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "tool", "tool_call_id": "call_123", "content": "some tool output"},
            {"role": "tool", "tool_call_id": None, "content": "no id"},
            {"role": "tool", "content": "missing tool_call_id field"},
            {"role": "assistant", "content": "I am here."},
        ]

        cleaned = self.compressor._clean_orphaned_tools(messages)
        # All tool messages should be pruned because call_ids is empty
        tool_msgs = [m for m in cleaned if m.get("role") == "tool"]
        self.assertEqual(len(tool_msgs), 0)
        # Non-tool messages should be preserved
        self.assertEqual(len(cleaned), 2)
        self.assertEqual(cleaned[0]["role"], "user")
        self.assertEqual(cleaned[1]["role"], "assistant")

    def test_orphaned_tools_pruning_with_non_empty_call_ids(self):
        """Verify that when call_ids contains valid IDs, only matching tools survive."""
        messages = [
            {
                "role": "assistant",
                "content": "Calling tools",
                "tool_calls": [
                    {"id": "call_legit_1", "function": {"name": "echo"}},
                    {"id": "call_legit_2", "function": {"name": "add"}},
                ],
            },
            {"role": "tool", "tool_call_id": "call_legit_1", "content": "echo result"},
            {"role": "tool", "tool_call_id": "call_ghost", "content": "ghost result"},
            {"role": "tool", "tool_call_id": "call_legit_2", "content": "add result"},
            {"role": "tool", "tool_call_id": "", "content": "empty string id"},
        ]

        cleaned = self.compressor._clean_orphaned_tools(messages)
        surviving_ids = [m.get("tool_call_id") for m in cleaned if m.get("role") == "tool"]
        self.assertEqual(surviving_ids, ["call_legit_1", "call_legit_2"])
        self.assertNotIn("call_ghost", surviving_ids)
        self.assertNotIn("", surviving_ids)

    def test_middle_turn_tool_call_compression_orphans_tail_tool_result(self):
        """
        When assistant tool_call is in the middle (compacted to summary),
        a corresponding tool result in the tail must be cleanly pruned by _clean_orphaned_tools.
        """
        # Create a conversation with >200 tokens (max_tokens=200) to trigger compression
        messages = [
            {"role": "system", "content": "You are JARVIS"},
            {
                "role": "assistant",
                "content": "Tool call in middle " + ("data " * 100),
                "tool_calls": [{"id": "call_in_middle", "function": {"name": "test"}}],
            },
            {"role": "user", "content": "User response " + ("data " * 100)},
            # Tail starts here (last 2 turns)
            {"role": "tool", "tool_call_id": "call_in_middle", "content": "tool result in tail"},
            {"role": "user", "content": "Now what?"},
        ]

        # Total tokens ~301 > 200 max_tokens -> triggers compression
        total_tokens = self.compressor.estimate_tokens(messages)
        self.assertGreater(total_tokens, 200)

        compacted = self.compressor.compress(messages)
        # The tool result in tail should have been pruned because its matching assistant call
        # was compacted into the middle summary!
        tail_tool_msgs = [m for m in compacted if m.get("role") == "tool"]
        self.assertEqual(len(tail_tool_msgs), 0)

        # Head system prompt must be preserved
        self.assertEqual(compacted[0]["role"], "system")
        self.assertEqual(compacted[0]["content"], "You are JARVIS")

        # Tail user message must be preserved
        self.assertEqual(compacted[-1]["role"], "user")
        self.assertEqual(compacted[-1]["content"], "Now what?")

    def test_head_and_tail_preservation_under_extreme_token_flooding(self):
        """Verify system prompt and tail are preserved even with massive token floods."""
        messages = [{"role": "system", "content": "CRITICAL_SYSTEM_DIRECTIVE"}]
        for i in range(50):
            messages.append({"role": "user", "content": f"Turn {i}: " + ("huge flood " * 50)})
            messages.append({"role": "assistant", "content": f"Response {i}: " + ("huge response " * 50)})
        messages.append({"role": "user", "content": "FINAL_USER_QUESTION"})

        compacted = self.compressor.compress(messages)
        self.assertEqual(compacted[0]["role"], "system")
        self.assertEqual(compacted[0]["content"], "CRITICAL_SYSTEM_DIRECTIVE")
        self.assertEqual(compacted[-1]["role"], "user")
        self.assertEqual(compacted[-1]["content"], "FINAL_USER_QUESTION")


class AdversarialToolDispatcherTests(unittest.TestCase):
    """Stress tests for ToolDispatcher concurrency and loop guard locking."""

    def test_multithreaded_high_frequency_loop_guard_locking(self):
        """Stress-test _check_loop_guard under high-frequency multithreaded contention."""
        td = ToolDispatcher(max_consecutive_calls=1000)
        call_count = 500
        threads = 10

        # Run 500 identical calls across 10 concurrent threads
        def worker():
            for _ in range(call_count // threads):
                td._check_loop_guard("test_tool", {"arg": "constant"})

        thread_list = [threading.Thread(target=worker) for _ in range(threads)]
        for t in thread_list:
            t.start()
        for t in thread_list:
            t.join()

        # Due to thread safety under _loop_lock, total consecutive count must equal exact calls
        self.assertEqual(td._consecutive_call_count, call_count)

    def test_test_echo_and_read_only_tool_dispatch(self):
        """Verify test_echo and echo are registered, read-only, and callable concurrently."""
        td = ToolDispatcher()
        self.assertIn("test_echo", READ_ONLY_TOOLS)
        self.assertIn("echo", READ_ONLY_TOOLS)

        # Single dispatch
        res1 = td.dispatch("test_echo", {"msg": "Hello M2"})
        self.assertEqual(res1, "Hello M2")

        res2 = td.dispatch("test_echo", {"text": "Alternative key"})
        self.assertEqual(res2, "Alternative key")

        # Concurrent batch dispatch
        calls = [
            {"id": f"call_{i}", "name": "test_echo", "args": {"msg": f"msg_{i}"}}
            for i in range(16)
        ]
        results = td.dispatch_tool_calls(calls)
        self.assertEqual(len(results), 16)
        for i, r in enumerate(results):
            self.assertEqual(r["status"], "success")
            self.assertIn("msg_", r["result"])


class AdversarialHermesBrainInterruptLatencyTests(unittest.TestCase):
    """Multi-sample benchmark for HermesBrain interrupt latency (<32ms)."""

    def test_mid_stream_interrupt_latency_sub_32ms(self):
        """Benchmark 50 mid-stream interrupts during active token generation (<32ms SLA)."""
        async def _run_benchmark():
            latencies = []
            brain = HermesBrain()

            for i in range(50):
                brain.reset_interrupt()
                gen = brain.run_turn(f"bench-session-{i}", "Tell me an extensive story about AI")

                # Consume initial state
                await gen.__anext__()
                # Consume initial tokens
                await gen.__anext__()
                await gen.__anext__()

                t0 = time.perf_counter()
                brain.interrupt(f"Benchmark abort {i}")
                events = []
                async for ev in gen:
                    events.append(ev)
                t1 = time.perf_counter()

                lat_ms = (t1 - t0) * 1000.0
                latencies.append(lat_ms)

            latencies.sort()
            p50 = latencies[25]
            p95 = latencies[47]
            p99 = latencies[49]
            max_lat = max(latencies)

            print(f"\n--- HERMESBRAIN MID-STREAM INTERRUPT LATENCY (50 runs) ---")
            print(f"Min: {min(latencies):.3f} ms")
            print(f"p50: {p50:.3f} ms")
            print(f"p95: {p95:.3f} ms")
            print(f"p99: {p99:.3f} ms")
            print(f"Max: {max_lat:.3f} ms")

            self.assertLess(max_lat, 32.0, f"Max interrupt latency {max_lat:.3f}ms exceeded 32.0ms!")
            self.assertLess(p95, 25.0, f"p95 latency {p95:.3f}ms exceeded 25.0ms!")

        asyncio.run(_run_benchmark())

    def test_pre_token_interrupt_state_and_event_handling(self):
        """Verify that when interrupted immediately after turn start, interrupted event is yielded."""
        async def _run_pre_token():
            brain = HermesBrain()
            gen = brain.run_turn("pre-token-session", "Quick command")

            # Consume state event
            ev1 = await gen.__anext__()
            self.assertEqual(ev1.event_type, "agent.state")

            # Trigger interrupt immediately
            t0 = time.perf_counter()
            brain.interrupt("Immediate abort")
            events = []
            async for ev in gen:
                events.append(ev)
            t1 = time.perf_counter()

            lat_ms = (t1 - t0) * 1000.0
            event_types = [e.event_type for e in events]
            self.assertIn("interrupted", event_types)
            self.assertNotIn("agent.complete", event_types)
            self.assertEqual(brain.get_state(), "idle")
            print(f"[PASS] Pre-token interrupt completed in {lat_ms:.3f} ms with event 'interrupted'")

        asyncio.run(_run_pre_token())


if __name__ == "__main__":
    unittest.main(verbosity=2)
