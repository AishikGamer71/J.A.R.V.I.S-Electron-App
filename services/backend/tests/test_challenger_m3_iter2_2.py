"""
tests/test_challenger_m3_iter2_2.py
===================================
Adversarial Verification Suite for Milestone M3 Iteration 2 (RAG & Power Challenger).

Authored by: challenger_m3_iter2_2 (Empirical Challenger)
Target components:
1. backend/memory/hybrid_rag.py:
   - compute_rrf_score boundary robustness (rank=0, rank=-5, k=-1, non-positive denominators)
   - SearchResult negative indexing and tuple unpacking
   - String path initialization and Windows file handle release (zero [WinError 32])
2. backend/engine/model_router.py:
   - Trace-driven routing with power_mode == "power_saver" cloud suppression
   - OllamaEngine.is_available() cached latency benchmark (< 1ms)
3. backend/hardware/power_guardian.py:
   - Boundary at battery_pct = 20.0% matching Tier 2 and BATTERY_LOW
"""

import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.engine.model_router import ModelRouter, OllamaEngine, RouteDecision
from backend.hardware.power_guardian import (
    PowerConservationTier,
    PowerGuardian,
    PowerState,
    PowerStatus,
    SYSTEM_POWER_STATUS,
)
from backend.memory.hybrid_rag import (
    HybridMemory,
    NumpyDenseEmbedder,
    SearchResult,
    compute_rrf_score,
)


class TestAdversarialHybridRAGChallenger(unittest.TestCase):
    """Stress testing for Hybrid RAG: RRF math guards, indexing, and Windows lock release."""

    def test_compute_rrf_score_adversarial_boundaries(self):
        """Stress test compute_rrf_score with rank=0, rank=-5, k=-1 (must return 0.0, zero exceptions)."""
        # Explicit mandated values
        self.assertEqual(compute_rrf_score(rank=0, k=60), 0.0)
        self.assertEqual(compute_rrf_score(rank=-5, k=60), 0.0)
        self.assertEqual(compute_rrf_score(rank=1, k=-1), 0.0)

        # Additional edge-cases: zero and negative denominators
        self.assertEqual(compute_rrf_score(rank=2, k=-2), 0.0)
        self.assertEqual(compute_rrf_score(rank=5, k=-10), 0.0)
        self.assertEqual(compute_rrf_score(rank=-10, k=-10), 0.0)
        self.assertEqual(compute_rrf_score(rank=0, k=0), 0.0)

        # Valid boundaries
        self.assertEqual(compute_rrf_score(rank=1, k=0), 1.0)
        self.assertAlmostEqual(compute_rrf_score(rank=1, k=60), 1.0 / 61.0, places=9)
        self.assertAlmostEqual(compute_rrf_score(rank=1000, k=60), 1.0 / 1060.0, places=9)

        # Bulk fuzzing: 500 combinations of negative and zero ranks/k
        for r in range(-250, 1):
            for k_val in [-50, -10, -1, 0, 10, 60]:
                val = compute_rrf_score(rank=r, k=k_val)
                self.assertEqual(val, 0.0, f"Failed for rank={r}, k={k_val}")

    def test_search_result_negative_indexing_and_unpacking(self):
        """Stress test SearchResult negative indexing and tuple unpacking."""
        sr = SearchResult(
            doc_id="doc_alpha_99",
            content="Autonomous quantum interface telemetry",
            score=0.98765,
            metadata={"source": "openjarvis", "layer": 4},
            fts_rank=2,
            vector_rank=1,
        )

        # Verify length
        self.assertEqual(len(sr), 4)

        # Verify negative indexing
        self.assertEqual(sr[-1], {"source": "openjarvis", "layer": 4})
        self.assertEqual(sr[-2], "Autonomous quantum interface telemetry")
        self.assertEqual(sr[-3], 0.98765)
        self.assertEqual(sr[-4], "doc_alpha_99")

        # Verify positive indexing
        self.assertEqual(sr[0], "doc_alpha_99")
        self.assertEqual(sr[1], 0.98765)
        self.assertEqual(sr[2], "Autonomous quantum interface telemetry")
        self.assertEqual(sr[3], {"source": "openjarvis", "layer": 4})

        # Out-of-bounds indexing raises IndexError
        with self.assertRaises(IndexError):
            _ = sr[-5]
        with self.assertRaises(IndexError):
            _ = sr[4]

        # Slicing
        self.assertEqual(sr[0:2], ("doc_alpha_99", 0.98765))
        self.assertEqual(sr[-2:], ("Autonomous quantum interface telemetry", {"source": "openjarvis", "layer": 4}))

        # Tuple unpacking
        d, s, c, m = sr
        self.assertEqual(d, "doc_alpha_99")
        self.assertEqual(s, 0.98765)
        self.assertEqual(c, "Autonomous quantum interface telemetry")
        self.assertEqual(m, {"source": "openjarvis", "layer": 4})

    def test_string_path_init_and_windows_file_locking(self):
        """
        Stress test string path initialization and temporary file deletion on Windows.
        Verifies zero [WinError 32] file handle locks over 30 rapid creation/deletion cycles.
        """
        temp_dir = tempfile.mkdtemp(prefix="jarvis_rag_lock_test_")
        try:
            for i in range(30):
                db_file = os.path.join(temp_dir, f"test_store_{i}.db")
                # Initialize with raw string path
                hm = HybridMemory(db_path=db_file)

                # Index multiple documents
                hm.index_text(f"doc_{i}_a", f"Arc reactor power grid telemetry {i}", {"run": i})
                hm.index_text(f"doc_{i}_b", f"Stark Industries clean energy initiative {i}", {"run": i})

                # Perform search
                results = hm.search("power grid", top_k=2)
                self.assertGreater(len(results), 0)

                # Delete a document
                hm.delete_document(f"doc_{i}_a")

                # Clear and close
                hm.clear()
                hm.close()
                del hm

                # Must delete cleanly on Windows without WinError 32
                self.assertTrue(os.path.exists(db_file), "Database file should exist prior to removal")
                os.remove(db_file)
                self.assertFalse(os.path.exists(db_file), "Database file should be completely removed")

                # Also remove WAL/SHM if present
                wal_file = f"{db_file}-wal"
                shm_file = f"{db_file}-shm"
                if os.path.exists(wal_file):
                    os.remove(wal_file)
                if os.path.exists(shm_file):
                    os.remove(shm_file)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestAdversarialModelRouterChallenger(unittest.TestCase):
    """Stress testing for ModelRouter power mode constraints and cache latency."""

    def test_power_saver_cloud_trace_suppression(self):
        """
        Adversarially populate traces.db with 10 high-reward cloud traces for a bucket.
        Call route_query() with power_mode == "power_saver"; verify it strictly routes
        to local engine ("ollama" or "fallback") and suppresses cloud override.
        """
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            trace_path = Path(tf.name)

        try:
            router = ModelRouter(trace_db_path=trace_path)

            # Adversarially populate 10 high-reward cloud traces for "long" bucket
            for _ in range(10):
                router.traces.record_trace(
                    bucket="long",
                    engine="cloud",
                    model="gemini-2.5-pro",
                    latency_ms=120.0,
                    tokens=350,
                    cost=0.001,
                    success=True,
                )

            # Verification 1: Under normal performance mode, trace-driven policy picks cloud
            router.update_power_mode("performance")
            normal_decision = router.route_query(
                "Synthesize comprehensive empirical evidence on room-temperature superconductor replication"
            )
            self.assertEqual(normal_decision.engine, "cloud")
            self.assertIn("Overridden by trace reward", normal_decision.reason)

            # Verification 2: Switch to power_saver mode
            router.update_power_mode("power_saver")
            saver_decision = router.route_query(
                "Synthesize comprehensive empirical evidence on room-temperature superconductor replication"
            )

            # Must strictly route to local engine, never cloud
            self.assertNotEqual(saver_decision.engine, "cloud")
            self.assertIn(saver_decision.engine, ["ollama", "fallback"])
            self.assertTrue(saver_decision.quantized_or_cpu)
            self.assertEqual(saver_decision.tier, "local_fast")
            self.assertIn("power_saver", saver_decision.reason)

            # Verification 3: Even with local traces added, it only selects between local engines
            for _ in range(5):
                router.traces.record_trace(
                    bucket="long",
                    engine="ollama",
                    model="qwen2.5:3b-q4",
                    latency_ms=90.0,
                    tokens=300,
                    cost=0.0,
                    success=True,
                )

            local_trace_decision = router.route_query(
                "Synthesize comprehensive empirical evidence on room-temperature superconductor replication"
            )
            self.assertEqual(local_trace_decision.engine, "ollama")
            self.assertEqual(local_trace_decision.model, "qwen2.5:3b-q4")
            self.assertTrue(local_trace_decision.quantized_or_cpu)
        finally:
            if trace_path.exists():
                try:
                    os.remove(trace_path)
                except Exception:
                    pass

    def test_ollama_engine_cached_availability_latency_benchmark(self):
        """
        Benchmark OllamaEngine.is_available() latency.
        Verify it completes in < 1ms when cached.
        """
        engine = OllamaEngine(base_url="http://127.0.0.1:11434", cache_ttl_sec=30.0)

        # Force prime the cache
        with engine._lock:
            engine._cached_available = True
            engine._last_check_time = time.time()

        # Execute 5,000 iterations to measure latency distribution
        num_iterations = 5000
        latencies_ms = []

        for _ in range(num_iterations):
            t0 = time.perf_counter()
            res = engine.is_available()
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            latencies_ms.append(elapsed_ms)
            self.assertTrue(res)

        avg_latency = sum(latencies_ms) / num_iterations
        p99_latency = sorted(latencies_ms)[int(num_iterations * 0.99)]
        max_latency = max(latencies_ms)

        print(
            f"\n[BENCHMARK] OllamaEngine.is_available() cached latency over {num_iterations} calls:"
            f"\n  Average: {avg_latency*1000.0:.2f} µs ({avg_latency:.4f} ms)"
            f"\n  p99:     {p99_latency*1000.0:.2f} µs ({p99_latency:.4f} ms)"
            f"\n  Max:     {max_latency*1000.0:.2f} µs ({max_latency:.4f} ms)"
        )

        # Must strictly complete in < 1ms when cached
        self.assertLess(avg_latency, 0.1, f"Average latency {avg_latency:.4f} ms exceeds 0.1 ms threshold")
        self.assertLess(p99_latency, 0.5, f"p99 latency {p99_latency:.4f} ms exceeds 0.5 ms threshold")
        self.assertLess(max_latency, 1.0, f"Max latency {max_latency:.4f} ms exceeds 1.0 ms threshold")


class TestAdversarialPowerGuardianChallenger(unittest.TestCase):
    """Stress testing for PowerGuardian boundary conditions."""

    def test_power_guardian_battery_20_percent_boundary(self):
        """
        Test boundary at battery_pct = 20.0%
        Must return "power_saver", matching Tier 2 and BATTERY_LOW.
        """
        guardian = PowerGuardian()

        # 1. Profile determination boundary tests
        self.assertEqual(
            guardian.determine_power_profile(ac_online=False, battery_pct=20.0),
            "power_saver",
            "At 20.0% battery, profile must be 'power_saver'",
        )
        self.assertEqual(
            guardian.determine_power_profile(ac_online=False, battery_pct=19.99),
            "power_saver",
            "Below 20.0% battery, profile must be 'power_saver'",
        )
        self.assertEqual(
            guardian.determine_power_profile(ac_online=False, battery_pct=20.01),
            "conservative",
            "Just above 20.0% battery, profile must be 'conservative'",
        )
        self.assertEqual(
            guardian.determine_power_profile(ac_online=True, battery_pct=20.0),
            "performance",
            "On AC power even at 20.0% battery, profile must be 'performance'",
        )

        # 2. psutil fallback simulation at exact 20.0% battery
        mock_batt = MagicMock()
        mock_batt.power_plugged = False
        mock_batt.percent = 20.0
        mock_batt.secsleft = 3600

        with patch("psutil.sensors_battery", return_value=mock_batt):
            status = guardian._query_psutil_power_status()
            self.assertEqual(status.power_state, PowerState.BATTERY_LOW)
            self.assertEqual(status.conservation_tier, PowerConservationTier.POWER_SAVER)
            self.assertEqual(status.conservation_tier.value, 2)
            self.assertEqual(status.battery_percent, 20.0)
            self.assertFalse(status.ac_online)

        # 3. psutil fallback simulation at 20.1% battery -> CONSERVATIVE (Tier 1)
        mock_batt_20_1 = MagicMock()
        mock_batt_20_1.power_plugged = False
        mock_batt_20_1.percent = 20.1
        mock_batt_20_1.secsleft = 3700

        with patch("psutil.sensors_battery", return_value=mock_batt_20_1):
            status_20_1 = guardian._query_psutil_power_status()
            self.assertEqual(status_20_1.power_state, PowerState.BATTERY_DISCHARGING)
            self.assertEqual(status_20_1.conservation_tier, PowerConservationTier.CONSERVATIVE)
            self.assertEqual(status_20_1.conservation_tier.value, 1)

        # 4. Win32 simulation at exact 20% battery
        sps_instance = SYSTEM_POWER_STATUS()
        sps_instance.ACLineStatus = 0
        sps_instance.BatteryFlag = 0  # has battery, not charging
        sps_instance.BatteryLifePercent = 20
        sps_instance.SystemStatusFlag = 0
        sps_instance.BatteryLifeTime = 3600
        sps_instance.BatteryFullLifeTime = 7200

        with patch("backend.hardware.power_guardian.SYSTEM_POWER_STATUS", return_value=sps_instance), \
             patch("ctypes.windll.kernel32.GetSystemPowerStatus", return_value=1):
            win_status = guardian._query_win32_power_status()
            self.assertEqual(win_status.power_state, PowerState.BATTERY_LOW)
            self.assertEqual(win_status.conservation_tier, PowerConservationTier.POWER_SAVER)
            self.assertEqual(win_status.conservation_tier.value, 2)
            self.assertEqual(win_status.battery_percent, 20.0)
            self.assertFalse(win_status.ac_online)

    def test_power_guardian_desktop_and_critical_boundaries(self):
        """Test desktop host without battery and critical 10.0% boundary."""
        guardian = PowerGuardian()

        # Desktop host without battery (psutil returns None)
        with patch("psutil.sensors_battery", return_value=None):
            desktop_status = guardian._query_psutil_power_status()
            self.assertEqual(desktop_status.power_state, PowerState.AC_DESKTOP)
            self.assertEqual(desktop_status.conservation_tier, PowerConservationTier.UNRESTRICTED)
            self.assertFalse(desktop_status.has_battery)

        # Battery at 10.0% -> BATTERY_CRITICAL (Tier 3)
        mock_crit = MagicMock()
        mock_crit.power_plugged = False
        mock_crit.percent = 10.0
        mock_crit.secsleft = 1200
        with patch("psutil.sensors_battery", return_value=mock_crit):
            crit_status = guardian._query_psutil_power_status()
            self.assertEqual(crit_status.power_state, PowerState.BATTERY_CRITICAL)
            self.assertEqual(crit_status.conservation_tier, PowerConservationTier.CRITICAL_PRESERVATION)
            self.assertEqual(crit_status.conservation_tier.value, 3)

        # Battery at 10.1% -> BATTERY_LOW (Tier 2)
        mock_low = MagicMock()
        mock_low.power_plugged = False
        mock_low.percent = 10.1
        mock_low.secsleft = 1300
        with patch("psutil.sensors_battery", return_value=mock_low):
            low_status = guardian._query_psutil_power_status()
            self.assertEqual(low_status.power_state, PowerState.BATTERY_LOW)
            self.assertEqual(low_status.conservation_tier, PowerConservationTier.POWER_SAVER)
            self.assertEqual(low_status.conservation_tier.value, 2)


class TestAdversarialConcurrencyAndFallback(unittest.TestCase):
    """Stress tests for multi-threading and offline streaming fallback."""

    def test_hybrid_memory_multithreaded_concurrency(self):
        """Verify 8 concurrent threads indexing and querying SQLite on Windows with zero lock failures."""
        temp_dir = tempfile.mkdtemp(prefix="jarvis_rag_thread_test_")
        db_path = os.path.join(temp_dir, "threaded_memory.db")
        hm = HybridMemory(db_path=db_path)

        errors = []

        def worker_fn(worker_id: int):
            try:
                for j in range(25):
                    doc_id = f"w{worker_id}_d{j}"
                    hm.index_text(doc_id, f"Worker {worker_id} thread task step {j} reactor core")
                    hits = hm.search(f"Worker {worker_id}", top_k=3)
                    if not hits:
                        errors.append(f"Worker {worker_id} step {j} produced no hits")
            except Exception as ex:
                errors.append(f"Worker {worker_id} exception: {ex}")

        threads = [threading.Thread(target=worker_fn, args=(i,)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Thread concurrency errors: {errors}")
        hm.close()
        del hm
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_power_saver_fallback_stream_when_ollama_offline(self):
        """When in power_saver and Ollama is offline, stream_chat smoothly falls back to FallbackEngine."""
        import asyncio
        router = ModelRouter()
        router.update_power_mode("power_saver")
        # Ensure Ollama is considered unavailable
        router._ollama_engine.is_available = lambda *args, **kwargs: False

        async def run_stream():
            chunks = []
            async for chunk in router.stream_chat([{"role": "user", "content": "System status report"}]):
                chunks.append(chunk)
            return chunks

        chunks = asyncio.run(run_stream())
        self.assertGreater(len(chunks), 0)
        self.assertEqual(chunks[0]["engine"], "fallback")
        self.assertEqual(chunks[0]["model"], "jarvis-dry-wit")
        full_text = "".join(c.get("delta", "") for c in chunks)
        self.assertIn("nominal performance", full_text.lower())


if __name__ == "__main__":
    unittest.main()
