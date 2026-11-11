"""
tests/test_adversarial_m3.py
============================
Empirical Adversarial Challenge Suite for Milestone M3:
  1. backend/memory/hybrid_rag.py:
     - compute_rrf_score boundary values (rank=0, rank=1, rank=100000, negative rank, k boundaries)
     - fuse_ranks 4-tier deterministic tie-breaking (score, modality_count, min_rank, lexicographical)
     - NumpyDenseEmbedder stress (empty, repetitive tokens, multi-language unicode/bidi/emojis)
     - 10,000 documents indexing & cosine similarity speed benchmark (< 100ms)
     - query("") and whitespace empty queries
  2. backend/voice/wakeword_engine.py:
     - Silence frames (all zeros, random gaussian noise) -> score strictly < 0.5
     - simulate_wakeword() and buffer reset
     - Corrupted / odd-byte frame resilience
  3. backend/voice/realtime_stt.py:
     - Empty chunk b"" and b"\\x00" -> returns ""
     - Strict endpoint detection at 599ms (False) vs 600ms (True)
     - Speech VAD activation, silence accumulation, and endpoint transition lifecycle
  4. backend/voice/omnivoice_service.py:
     - synthesize_preview() output starts with b"RIFF" and has valid 24kHz mono WAV headers
     - Fallback to pure-Python WAV generation when network / Edge-TTS is offline
     - Duration bounds [0.5s, 3.0s] under extreme input lengths (0 chars, 100k chars)
     - OmniVoiceClient transparent in-process fallback when microservice port is unreachable
  5. backend/voice/audio_pipeline.py:
     - Adversarially benchmark barge-in latency over 50 iterations (strictly <= 32ms bound)
     - Rapid state transitions under rapid interruptions (100 cycles)
     - Multi-threaded concurrent barge-in stress
     - Mute toggle behavior

Authored by: challenger_m3_2 (teamwork_challenger)
"""

import io
import math
import os
import struct
import sys
import tempfile
import threading
import time
import unittest
import wave
from pathlib import Path
from typing import Any, Dict, List, Tuple
from unittest.mock import patch

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.engine.model_router import ModelRouter, OllamaEngine
from backend.hardware.power_guardian import PowerGuardian
from backend.memory.hybrid_rag import (
    HybridMemory,
    NumpyDenseEmbedder,
    SearchResult,
    chunk_text,
    compute_rrf_score,
)
from backend.voice.audio_pipeline import AudioPipeline
from backend.voice.omnivoice_service import (
    DEFAULT_TTS_PORT,
    OmniVoiceClient,
    OmniVoiceService,
    generate_synthetic_wav_24k,
)
from backend.voice.realtime_stt import RealtimeSTT
from backend.voice.wakeword_engine import WakewordEngine, WakewordMode


class TestAdversarialHybridRAG(unittest.TestCase):
    """Adversarial stress testing for Hybrid RAG, RRF fusion, and NumpyDenseEmbedder."""

    def test_rrf_boundary_rank_zero_and_negative(self):
        """rank <= 0 must return score 0.0 without ZeroDivisionError."""
        self.assertEqual(compute_rrf_score(0, k=60), 0.0)
        self.assertEqual(compute_rrf_score(-1, k=60), 0.0)
        self.assertEqual(compute_rrf_score(-99999, k=60), 0.0)

    def test_rrf_boundary_rank_one(self):
        """rank=1 (best rank) must return 1 / (60 + 1) = 1/61."""
        score = compute_rrf_score(1, k=60)
        self.assertAlmostEqual(score, 1.0 / 61.0, places=7)

    def test_rrf_boundary_rank_100000(self):
        """rank=100000 must return 1 / (60 + 100000) without underflow."""
        score = compute_rrf_score(100000, k=60)
        self.assertAlmostEqual(score, 1.0 / 100060.0, places=9)
        self.assertGreater(score, 0.0)

    def test_rrf_k_boundary_values(self):
        """compute_rrf_score with k=0 should return 1.0 for rank=1."""
        score = compute_rrf_score(1, k=0)
        self.assertAlmostEqual(score, 1.0, places=6)

    def test_fuse_ranks_deterministic_tie_breaking_tier1_score(self):
        """Tier 1: Higher RRF score takes precedence."""
        rag = HybridMemory()
        fts_hits = [("doc_high", 1), ("doc_low", 20)]
        vec_hits = [("doc_high", 1), ("doc_low", 20)]
        fused = rag.fuse_ranks(fts_hits, vec_hits, k=60)
        self.assertEqual(fused[0][0], "doc_high")
        self.assertGreater(fused[0][1], fused[1][1])

    def test_fuse_ranks_deterministic_tie_breaking_tier2_modality_count(self):
        """
        Tier 2: Dual modality presence beats single modality when RRF scores collide.
        Mathematical proof of score collision:
        doc_multi: rank 140 in FTS and rank 140 in Vec -> 1/200 + 1/200 = 1/100 = 0.01
        doc_single: rank 40 in FTS only -> 1/(60+40) = 1/100 = 0.01
        doc_multi must rank ahead of doc_single despite lexicographical disadvantage.
        """
        rag = HybridMemory()
        fts_hits = [("z_multi", 140), ("a_single", 40)]
        vec_hits = [("z_multi", 140)]
        fused = rag.fuse_ranks(fts_hits, vec_hits, k=60)

        # Both have exact score 0.01
        self.assertAlmostEqual(fused[0][1], 0.01, places=6)
        self.assertAlmostEqual(fused[1][1], 0.01, places=6)
        # z_multi must beat a_single because modality_count is 2 vs 1
        self.assertEqual(fused[0][0], "z_multi")
        self.assertEqual(fused[1][0], "a_single")

    def test_fuse_ranks_deterministic_tie_breaking_tier3_min_rank(self):
        """
        Tier 3: When RRF score and modality count both collide, lower individual best rank wins.
        Mathematical proof:
        doc1: FTS 60, Vec 240 -> 1/120 + 1/300 = 7/600 (~0.011667), min_rank = 60
        doc2: FTS 90, Vec 140 -> 1/150 + 1/200 = 7/600 (~0.011667), min_rank = 90
        doc1 must rank ahead of doc2 because min_rank 60 < 90.
        """
        rag = HybridMemory()
        fts_hits = [("z_doc1", 60), ("a_doc2", 90)]
        vec_hits = [("z_doc1", 240), ("a_doc2", 140)]
        fused = rag.fuse_ranks(fts_hits, vec_hits, k=60)

        self.assertAlmostEqual(fused[0][1], 7.0 / 600.0, places=6)
        self.assertAlmostEqual(fused[1][1], 7.0 / 600.0, places=6)
        self.assertEqual(fused[0][0], "z_doc1")
        self.assertEqual(fused[1][0], "a_doc2")

    def test_fuse_ranks_deterministic_tie_breaking_tier4_lexicographical(self):
        """
        Tier 4: When score, modality count, and min_rank all collide, lexicographical ordering breaks tie.
        doc_beta: FTS rank 10
        doc_alpha: Vec rank 10
        Both score 1/70, modality 1, min_rank 10. doc_alpha must come before doc_beta.
        """
        rag = HybridMemory()
        fts_hits = [("doc_beta", 10)]
        vec_hits = [("doc_alpha", 10)]
        fused = rag.fuse_ranks(fts_hits, vec_hits, k=60)

        self.assertEqual(fused[0][0], "doc_alpha")
        self.assertEqual(fused[1][0], "doc_beta")

    def test_embedder_empty_and_whitespace(self):
        """NumpyDenseEmbedder must return a 384-dimensional zero vector for empty/whitespace input."""
        embedder = NumpyDenseEmbedder(dim=384)
        for empty_text in ["", "   ", "\t\t\n\n\r\n"]:
            vec = embedder.embed(empty_text)
            self.assertEqual(vec.shape, (384,))
            self.assertEqual(vec.dtype, np.float32)
            self.assertEqual(float(np.linalg.norm(vec)), 0.0)

    def test_embedder_repetitive_words_no_nan_or_inf(self):
        """NumpyDenseEmbedder must handle repetitive tokens without numerical overflow or NaN."""
        embedder = NumpyDenseEmbedder(dim=384)
        long_rep = "stark " * 10000
        vec = embedder.embed(long_rep)
        self.assertEqual(vec.shape, (384,))
        self.assertFalse(np.isnan(vec).any(), "Embedding contained NaN")
        self.assertFalse(np.isinf(vec).any(), "Embedding contained Inf")
        norm = float(np.linalg.norm(vec))
        self.assertAlmostEqual(norm, 1.0, places=5)

    def test_embedder_unicode_and_bidi_heterogeneous(self):
        """NumpyDenseEmbedder must stably embed unicode, bidi, emojis, and null bytes."""
        embedder = NumpyDenseEmbedder(dim=384)
        inputs = [
            "Tony Stark 钢铁侠 토니 스타크 🚀 \u202e \x00",
            "⚡ JARVIS Neural Core v2.0 🌟 🦾",
            "مرحبا بك يا جارفيس في النظام",
            "こんにちは世界！人工知能アシスタント",
        ]
        for inp in inputs:
            vec = embedder.embed(inp)
            self.assertEqual(vec.shape, (384,))
            self.assertFalse(np.isnan(vec).any())
            self.assertAlmostEqual(float(np.linalg.norm(vec)), 1.0, places=5)

    def test_embedder_10000_documents_indexing_and_cosine_speed(self):
        """
        Benchmark: 10,000 document vector embeddings generated and searched with cosine similarity.
        Cosine similarity search across all 10,000 documents must complete in < 100ms on CPU.
        """
        embedder = NumpyDenseEmbedder(dim=384)
        docs = [
            f"Document {i}: System telemetry diagnostics for Mark {i % 85} autonomous suit reactor"
            for i in range(10000)
        ]

        t0 = time.perf_counter()
        matrix = np.array([embedder.embed(doc) for doc in docs], dtype=np.float32)
        embed_elapsed = time.perf_counter() - t0
        self.assertEqual(matrix.shape, (10000, 384))
        # Embedding 10,000 short documents should take under 10 seconds
        self.assertLess(embed_elapsed, 10.0, f"10k embedding generation took {embed_elapsed:.2f}s")

        # Benchmark query cosine similarity
        query_text = "Mark reactor autonomous diagnostics"
        q_vec = embedder.embed(query_text)
        t_search_0 = time.perf_counter()
        sims = np.dot(matrix, q_vec)
        top_indices = np.argsort(-sims)[:10]
        search_elapsed_ms = (time.perf_counter() - t_search_0) * 1000.0

        self.assertLess(
            search_elapsed_ms,
            100.0,
            f"10,000-doc cosine similarity search took {search_elapsed_ms:.2f}ms (threshold 100ms)",
        )
        self.assertEqual(len(top_indices), 10)
        self.assertGreater(sims[top_indices[0]], 0.5)

    def test_hybrid_memory_empty_query(self):
        """HybridMemory.query('') and whitespace-only queries must return an empty list immediately."""
        rag = HybridMemory()
        rag.index_text("d1", "Tony Stark created Jarvis in Malibu")
        self.assertEqual(rag.query(""), [])
        self.assertEqual(rag.query("   \t\n"), [])

    def test_hybrid_memory_fts_syntax_and_special_chars(self):
        """FTS5 syntax characters (*, AND, OR, NOT, punctuation) must not cause query crashes."""
        rag = HybridMemory()
        rag.index_text("d1", "Search and destroy protocol operational")
        results_punct = rag.query("***???///---")
        self.assertIsInstance(results_punct, list)
        results_bool = rag.query("NOT AND OR")
        self.assertIsInstance(results_bool, list)


class TestAdversarialWakewordEngine(unittest.TestCase):
    """Adversarial stress testing for WakewordEngine audio scoring and simulation."""

    def setUp(self):
        self.ww = WakewordEngine(threshold=0.5)

    def test_silence_frame_all_zeros_score_below_half(self):
        """Pure zero PCM frame (16-bit 16kHz mono = 1280 bytes) must score well below 0.5."""
        silence_frame = bytes(1280)
        score = self.ww.score_frame(silence_frame)
        self.assertLess(score, 0.5, f"Silence scored {score}, expected < 0.5")
        self.assertAlmostEqual(score, 0.02, places=2)

    def test_silence_frame_gaussian_noise_scores_below_half(self):
        """
        Adversarial gaussian noise frames across varying amplitudes
        (std dev from 50 to 30,000) must consistently score < 0.5.
        """
        stds = [50, 200, 1000, 5000, 12000, 25000]
        for std in stds:
            with self.subTest(noise_std=std):
                noise = np.random.normal(0, std, 640).astype(np.int16).tobytes()
                score = self.ww.score_frame(noise)
                self.assertLess(
                    score,
                    0.5,
                    f"Gaussian noise with std={std} scored {score} >= 0.5",
                )

    def test_simulate_wakeword_and_one_shot_consumption(self):
        """simulate_wakeword() must trigger on_wakeword callback and yield >=0.5 on next frame, then reset."""
        callback_called = []
        ww = WakewordEngine(threshold=0.5, on_wakeword=lambda: callback_called.append(True))
        silence = bytes(1280)

        # Baseline: silence frame yields < 0.5
        self.assertLess(ww.score_frame(silence), 0.5)

        # Simulate trigger
        ww.simulate_wakeword(score=0.95)
        self.assertTrue(len(callback_called) >= 1)

        # Next score_frame must consume the simulated trigger
        score_1 = ww.score_frame(silence)
        self.assertGreaterEqual(score_1, 0.5)
        self.assertEqual(score_1, 0.95)

        # Subsequent score_frame must drop back to baseline
        score_2 = ww.score_frame(silence)
        self.assertLess(score_2, 0.5)

    def test_wakeword_reset_buffer_and_state(self):
        """reset() must clear the buffer, reset buffer_size to 0, and clear simulated triggers."""
        self.ww.simulate_wakeword()
        self.ww.process_frame(bytes(1280))
        self.assertGreater(self.ww.buffer_size, 0)

        self.ww.reset()
        self.assertEqual(self.ww.buffer_size, 0)
        self.assertFalse(self.ww._simulated_trigger)
        self.assertLess(self.ww.score_frame(bytes(1280)), 0.5)

    def test_wakeword_corrupted_odd_byte_frame_sizes(self):
        """Corrupted audio frames with odd or truncated bytes must not raise unhandled exceptions."""
        odd_frames = [b"", b"\x00", b"\x00\x01\x02", bytes(1279)]
        for f in odd_frames:
            with self.subTest(frame_len=len(f)):
                score = self.ww.score_frame(f)
                self.assertIsInstance(score, float)
                self.assertLess(score, 0.5)


class TestAdversarialRealtimeSTT(unittest.TestCase):
    """Adversarial testing for RealtimeSTT chunk transcription, VAD, and endpoint detection."""

    def setUp(self):
        self.stt = RealtimeSTT(post_speech_silence_duration=0.6)

    def test_transcribe_empty_and_zero_byte_chunk(self):
        """transcribe_chunk with b'' or 1-byte b'\\x00' must return empty string ''."""
        self.assertEqual(self.stt.transcribe_chunk(b""), "")
        self.assertEqual(self.stt.transcribe_chunk(b"\x00"), "")

    def test_detect_endpoint_sub_millisecond_boundaries(self):
        """
        Silence endpoint boundary is strictly 600.0ms:
        - 599.0ms -> False
        - 599.9ms -> False
        - 600.0ms -> True
        - 600.1ms -> True
        """
        self.assertFalse(self.stt.detect_endpoint(silence_duration_ms=599.0))
        self.assertFalse(self.stt.detect_endpoint(silence_duration_ms=599.9))
        self.assertTrue(self.stt.detect_endpoint(silence_duration_ms=600.0))
        self.assertTrue(self.stt.detect_endpoint(silence_duration_ms=600.1))
        self.assertTrue(self.stt.detect_endpoint(silence_duration_ms=1000.0))

    def test_stt_feed_audio_vad_and_endpoint_lifecycle(self):
        """
        Test complete speech -> silence -> endpoint -> stop lifecycle:
        1. Speech frame sets is_recording = True.
        2. 500ms silence does not trigger endpoint.
        3. Reaching 600ms silence triggers on_recording_stop and resets is_recording = False.
        """
        recorded_transcripts = []
        stt = RealtimeSTT(
            post_speech_silence_duration=0.6,
            on_recording_stop=lambda text: recorded_transcripts.append(text),
        )

        # 100ms at 16kHz = 1600 samples (3200 bytes)
        speech_pcm = (np.sin(np.linspace(0, 50, 1600)) * 8000).astype(np.int16).tobytes()
        silence_pcm = bytes(3200)

        # Feed speech
        stt.feed_audio(speech_pcm)
        self.assertTrue(stt.is_recording)
        self.assertEqual(len(recorded_transcripts), 0)

        # Feed 5 chunks of silence (500ms total)
        for _ in range(5):
            stt.feed_audio(silence_pcm)
        self.assertTrue(stt.is_recording, "Should still be recording at 500ms silence")
        self.assertEqual(len(recorded_transcripts), 0)

        # Feed 6th chunk of silence (reaching 600ms endpoint)
        stt.feed_audio(silence_pcm)
        self.assertFalse(stt.is_recording, "Recording should stop at 600ms endpoint")
        self.assertEqual(len(recorded_transcripts), 1)


class TestAdversarialOmniVoiceService(unittest.TestCase):
    """Adversarial testing for OmniVoice synthesis, RIFF WAV headers, and pure-Python fallback."""

    def setUp(self):
        self.svc = OmniVoiceService()

    def test_synthesize_preview_riff_header_and_params(self):
        """synthesize_preview() must produce valid 24kHz RIFF WAV bytes with header b'RIFF'."""
        wav_bytes = self.svc.synthesize_preview("Preview synthesis test for J.A.R.V.I.S.")
        self.assertTrue(
            wav_bytes.startswith(b"RIFF"),
            f"Output did not start with b'RIFF': {wav_bytes[:8]}",
        )
        self.assertGreater(len(wav_bytes), 44)

        # Validate with wave module
        with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
            self.assertEqual(wf.getnchannels(), 1, "Must be mono 1-channel audio")
            self.assertEqual(wf.getframerate(), 24000, "Must be 24000 Hz")
            self.assertEqual(wf.getsampwidth(), 2, "Must be 16-bit PCM")
            self.assertGreater(wf.getnframes(), 0)

    def test_synthesize_offline_fallback_pure_python_wav(self):
        """When Edge-TTS and neural models are unavailable, offline pure-Python fallback succeeds."""
        with patch("edge_tts.Communicate", side_effect=RuntimeError("Network offline")):
            wav_bytes = self.svc.synthesize_wav_bytes("Testing offline voice generation.")
            self.assertTrue(wav_bytes.startswith(b"RIFF"))
            with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
                self.assertEqual(wf.getframerate(), 24000)
                self.assertEqual(wf.getnchannels(), 1)

    def test_generate_synthetic_wav_24k_duration_bounds(self):
        """Duration of pure-Python synthetic WAV must remain bounded in [0.5s, 3.0s]."""
        # Empty text -> minimum 0.5s duration
        wav_empty = generate_synthetic_wav_24k("", sample_rate=24000)
        with wave.open(io.BytesIO(wav_empty), "rb") as wf:
            duration_empty = wf.getnframes() / float(wf.getframerate())
            self.assertAlmostEqual(duration_empty, 0.5, places=1)

        # Extremely long text (100k characters) -> capped at 3.0s duration
        huge_text = "Iron Man Mark 85 armor system " * 3000
        wav_huge = generate_synthetic_wav_24k(huge_text, sample_rate=24000)
        with wave.open(io.BytesIO(wav_huge), "rb") as wf:
            duration_huge = wf.getnframes() / float(wf.getframerate())
            self.assertAlmostEqual(duration_huge, 3.0, places=1)

    def test_omnivoice_client_in_process_fallback(self):
        """OmniVoiceClient must transparently fall back to in-process service when HTTP port is down."""
        # Port 59999 has no listener
        client = OmniVoiceClient(service_url="http://127.0.0.1:59999")
        waveform, audio_b64 = client.synthesize("Client in-process fallback check")
        self.assertIsInstance(waveform, np.ndarray)
        self.assertGreater(len(waveform), 0)
        self.assertGreater(len(audio_b64), 0)


class TestAdversarialAudioPipeline(unittest.TestCase):
    """Adversarial stress testing for AudioPipeline barge-in latency and interruption states."""

    def test_barge_in_latency_benchmark_50_iterations_warm(self):
        """
        Adversarially benchmark 50 iterations of conversational barge-in.
        Every single iteration must strictly measure <= 32ms.
        Pre-warms PortAudio / sounddevice to isolate steady-state conversational execution.
        """
        try:
            import sounddevice as sd
        except Exception:
            pass

        pipe = AudioPipeline(max_barge_in_latency_ms=32)
        latencies: List[float] = []

        for i in range(50):
            pipe.on_speaking()
            lat_ms = pipe.trigger_barge_in()
            latencies.append(lat_ms)

        max_lat = max(latencies)
        mean_lat = sum(latencies) / len(latencies)
        min_lat = min(latencies)

        # Strict SLA assertion: ALL 50 iterations must be <= 32ms
        self.assertLessEqual(
            max_lat,
            32.0,
            f"Barge-in latency exceeded 32ms bound! Max: {max_lat:.4f}ms, Mean: {mean_lat:.4f}ms",
        )
        self.assertLessEqual(mean_lat, 5.0, f"Mean latency unexpectedly high: {mean_lat:.4f}ms")

    def test_rapid_speaking_interrupted_state_transitions(self):
        """Stress test 100 consecutive rapid speaking -> barge-in state transition cycles."""
        pipe = AudioPipeline()
        for i in range(100):
            pipe.on_speaking()
            self.assertEqual(pipe.state, "speaking")

            pipe.trigger_barge_in()
            self.assertEqual(pipe.state, "interrupted")
            self.assertTrue(pipe.tts_stop_event.is_set())

    def test_concurrent_multi_threaded_barge_in(self):
        """Verify thread safety under 10 concurrent threads rapidly triggering barge-in."""
        pipe = AudioPipeline()
        errors: List[str] = []

        def worker(tid: int):
            for i in range(20):
                try:
                    pipe.on_speaking()
                    time.sleep(0.0005)
                    pipe.trigger_barge_in()
                    if pipe.state != "interrupted":
                        errors.append(f"Thread {tid} cycle {i}: state was {pipe.state}")
                except Exception as exc:
                    errors.append(f"Thread {tid} error: {exc}")

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Concurrent barge-in errors: {errors}")

    def test_muted_pipeline_skips_playback(self):
        """When is_muted=True, speak_24khz does not broadcast or transition to speaking."""
        broadcasts = []
        pipe = AudioPipeline(ws_broadcast_fn=lambda event, payload: broadcasts.append((event, payload)))
        pipe.is_muted = True

        pipe.speak_24khz("Muted test message")
        self.assertEqual(pipe.state, "listening")
        self.assertEqual(len(broadcasts), 0)


class TestAdversarialPowerGuardianBoundaries(unittest.TestCase):
    """Adversarial boundary tests for PowerGuardian consistency."""

    def test_battery_20_percent_boundary_consistency(self):
        """At exactly 20.0% battery, determine_power_profile must return 'power_saver'."""
        guardian = PowerGuardian()
        self.assertEqual(guardian.determine_power_profile(ac_online=False, battery_pct=20.0), "power_saver")
        self.assertEqual(guardian.determine_power_profile(ac_online=False, battery_pct=20.1), "conservative")
        self.assertEqual(guardian.determine_power_profile(ac_online=False, battery_pct=40.0), "conservative")
        self.assertEqual(guardian.determine_power_profile(ac_online=False, battery_pct=40.1), "performance")
        self.assertEqual(guardian.determine_power_profile(ac_online=True, battery_pct=20.0), "performance")


class TestAdversarialModelRouterAlignment(unittest.TestCase):
    """Adversarial tests for ModelRouter power constraints and streaming latency."""

    def test_power_saver_hard_constraint_suppresses_cloud_trace_override(self):
        """When power_mode is 'power_saver', cloud traces MUST NOT override engine to cloud."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            trace_path = Path(tf.name)
        router = ModelRouter(trace_db_path=trace_path)

        for _ in range(5):
            router.traces.record_trace("long", "cloud", "gemini-2.5-pro", latency_ms=100.0, tokens=200, cost=0.001, success=True)

        router.update_power_mode("power_saver")
        decision = router.route_query("Synthesize room-temperature superconductor research papers")

        self.assertNotEqual(decision.engine, "cloud")
        self.assertEqual(decision.engine, "ollama")
        self.assertTrue(decision.quantized_or_cpu)
        self.assertIn("power_saver", decision.reason)

    def test_power_saver_permits_local_traces_optimization(self):
        """When power_mode is 'power_saver', local ollama traces CAN still optimize model selection."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            trace_path = Path(tf.name)
        router = ModelRouter(trace_db_path=trace_path)

        for _ in range(5):
            router.traces.record_trace("long", "cloud", "gemini-2.5-pro", latency_ms=100.0, tokens=200, cost=0.001, success=True)
        for _ in range(4):
            router.traces.record_trace("long", "ollama", "qwen2.5:3b-q4", latency_ms=80.0, tokens=200, cost=0.0, success=True)

        router.update_power_mode("power_saver")
        decision = router.route_query("Synthesize room-temperature superconductor research papers")

        self.assertEqual(decision.engine, "ollama")
        self.assertEqual(decision.model, "qwen2.5:3b-q4")

    def test_ollama_engine_cached_availability_latency_bound(self):
        """OllamaEngine.is_available() must return in < 25ms under all conditions."""
        engine = OllamaEngine()
        t0 = time.perf_counter()
        _ = engine.is_available()
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.assertLess(elapsed_ms, 25.0, f"is_available() took {elapsed_ms:.2f}ms (must be < 25ms)")


class TestAdversarialHybridRAGRobustness(unittest.TestCase):
    """Adversarial tests for HybridRAG string paths, indexing, and Windows lock release."""

    def test_string_db_path_and_windows_handle_release(self):
        td = tempfile.mkdtemp()
        str_db = os.path.join(td, "sub", "test.db")
        hm = HybridMemory(db_path=str_db)
        hm.index_text("doc1", "quantum neural interface")
        res = hm.search("quantum", top_k=1)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].doc_id, "doc1")
        hm.clear()
        del hm
        os.remove(str_db)

    def test_search_result_negative_indexing_and_unpacking(self):
        sr = SearchResult("docX", "content text", 0.99, {"author": "stark"})
        self.assertEqual(sr[-1], {"author": "stark"})
        self.assertEqual(sr[-2], "content text")
        self.assertEqual(sr[-3], 0.99)
        self.assertEqual(sr[-4], "docX")
        d, s, c, m = sr
        self.assertEqual((d, s, c, m), ("docX", 0.99, "content text", {"author": "stark"}))

    def test_rrf_division_zero_guard(self):
        self.assertEqual(compute_rrf_score(1, k=-1), 0.0)
        self.assertEqual(compute_rrf_score(2, k=-5), 0.0)


if __name__ == "__main__":
    unittest.main()
