"""
tests/benchmark_m3_forensics.py
===============================
Adversarial Forensics and Benchmark Probes for Milestone M3.
Authored by: challenger_m3_2 (teamwork_challenger)
"""

import io
import math
import os
import subprocess
import sys
import time
import wave
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def run_probes():
    print("======================================================================")
    print(" MILESTONE M3 EMPIRICAL AUDIT & FORENSIC PROBE REPORT")
    print("======================================================================")

    # 1. BARGE-IN LATENCY BENCHMARK
    print("\n--- 1. AUDIO PIPELINE BARGE-IN LATENCY BENCHMARK ---")
    # Probe cold-start latency in isolated sub-process
    probe_code = (
        "import time; "
        "from backend.voice.audio_pipeline import AudioPipeline; "
        "p = AudioPipeline(); "
        "lat = p.trigger_barge_in(); "
        "print(lat)"
    )
    res = subprocess.run([sys.executable, "-c", probe_code], capture_output=True, text=True)
    cold_lat = float(res.stdout.strip()) if res.stdout.strip() else -1.0
    print(f"Cold Start Barge-in Latency (Iteration 0 without warm-up): {cold_lat:.4f} ms")
    if cold_lat > 32.0:
        print(f"  [!] VULNERABILITY DETECTED: Cold-start barge-in ({cold_lat:.2f}ms) EXCEEDS 32ms bound!")
        print("      Root Cause: 'import sounddevice as sd' inside trigger_barge_in() lazily loads PortAudio DLL on first call.")
    else:
        print(f"  [*] Cold-start within 32ms bound.")

    # 50-iteration warm benchmark
    import sounddevice
    from backend.voice.audio_pipeline import AudioPipeline
    pipe = AudioPipeline(max_barge_in_latency_ms=32)
    warm_lats = []
    for _ in range(50):
        pipe.on_speaking()
        warm_lats.append(pipe.trigger_barge_in())

    print(f"Warm 50-Iteration Benchmark:")
    print(f"  * Min Latency : {min(warm_lats):.4f} ms")
    print(f"  * Max Latency : {max(warm_lats):.4f} ms")
    print(f"  * Mean Latency: {np.mean(warm_lats):.4f} ms")
    print(f"  * P95 Latency : {np.percentile(warm_lats, 95):.4f} ms")
    print(f"  * P99 Latency : {np.percentile(warm_lats, 99):.4f} ms")
    print(f"  * All 50 iterations <= 32ms: {all(l <= 32.0 for l in warm_lats)}")

    # 2. NUMPY DENSE EMBEDDER 10K BENCHMARK
    print("\n--- 2. NUMPY DENSE EMBEDDER 10,000-DOC BENCHMARK ---")
    from backend.memory.hybrid_rag import NumpyDenseEmbedder, compute_rrf_score, HybridMemory
    embedder = NumpyDenseEmbedder(dim=384)
    docs = [
        f"Document {i}: System telemetry diagnostics for Mark {i % 85} autonomous suit reactor"
        for i in range(10000)
    ]
    t0 = time.perf_counter()
    matrix = np.array([embedder.embed(d) for d in docs], dtype=np.float32)
    embed_time = time.perf_counter() - t0
    print(f"10,000 Embeddings Generation Time: {embed_time:.3f} s ({embed_time / 10000.0 * 1000.0:.3f} ms/doc)")

    q_vec = embedder.embed("Mark reactor autonomous diagnostics")
    t0 = time.perf_counter()
    sims = np.dot(matrix, q_vec)
    top10 = np.argsort(-sims)[:10]
    search_time = (time.perf_counter() - t0) * 1000.0
    print(f"10,000-doc Cosine Similarity Search Time: {search_time:.3f} ms")

    # 3. WAKEWORD NOISE BENCHMARK
    print("\n--- 3. WAKEWORD SILENCE & GAUSSIAN NOISE BENCHMARK ---")
    from backend.voice.wakeword_engine import WakewordEngine
    ww = WakewordEngine(threshold=0.5)
    silence = bytes(1280)
    print(f"Pure Silence Score: {ww.score_frame(silence):.4f} (must be < 0.5)")
    for std in [100, 500, 2000, 10000, 25000]:
        noise = np.random.normal(0, std, 640).astype(np.int16).tobytes()
        score = ww.score_frame(noise)
        print(f"Gaussian Noise (std={std:5d}): Score = {score:.4f} (passed: {score < 0.5})")

    # 4. REALTIME STT ENDPOINT BENCHMARK
    print("\n--- 4. REALTIME STT ENDPOINT DETECTION BENCHMARK ---")
    from backend.voice.realtime_stt import RealtimeSTT
    stt = RealtimeSTT(post_speech_silence_duration=0.6)
    for ms in [590.0, 599.0, 599.9, 600.0, 600.1, 700.0]:
        print(f"Endpoint at {ms:5.1f} ms: {stt.detect_endpoint(ms)}")

    # 5. OMNIVOICE SERVICE BENCHMARK
    print("\n--- 5. OMNIVOICE SYNTHESIS & OFFLINE RIFF FALLBACK ---")
    from backend.voice.omnivoice_service import OmniVoiceService, generate_synthetic_wav_24k
    svc = OmniVoiceService()
    prev = svc.synthesize_preview("Preview test for J.A.R.V.I.S.")
    print(f"Preview Output Header: {prev[:4]} | Length: {len(prev)} bytes")
    with wave.open(io.BytesIO(prev), "rb") as wf:
        print(f"Preview WAV Params: {wf.getnchannels()} ch, {wf.getframerate()} Hz, {wf.getsampwidth()*8} bit, {wf.getnframes()/wf.getframerate():.2f}s")

    offline = generate_synthetic_wav_24k("Offline fallback speech synthesis test", sample_rate=24000)
    print(f"Offline Output Header: {offline[:4]} | Length: {len(offline)} bytes")
    with wave.open(io.BytesIO(offline), "rb") as wf:
        print(f"Offline WAV Params: {wf.getnchannels()} ch, {wf.getframerate()} Hz, {wf.getsampwidth()*8} bit, {wf.getnframes()/wf.getframerate():.2f}s")

    print("\n======================================================================")
    print(" EMPIRICAL AUDIT COMPLETE")
    print("======================================================================")


if __name__ == "__main__":
    run_probes()
