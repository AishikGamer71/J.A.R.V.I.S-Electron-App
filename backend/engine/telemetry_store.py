"""
backend/engine/telemetry_store.py
=================================
Telemetry Store & Ring Buffer for J.A.R.V.I.S. Desktop System.
Assimilated from open-jarvis/OpenJarvis (src/openjarvis/telemetry/store.py).

Provides:
- Thread-safe rolling ring buffer of system performance snapshots and named metric series.
- Background sampling loop (1.0 Hz default).
- Envelope formatting matching:
  * src/shared/protocol.ts (`system.metrics`)
  * src/services/jarvisBridge.ts (`jarvis-telemetry`)
  * backend/main.py SystemStatsResponse (`GET /api/system/stats`)
- Per-turn latency recording (TTFT, tokens/sec, GPU wattage).
"""

import collections
import logging
import sqlite3
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from backend.engine.hardware_profiler import (
    HardwareProfiler,
    SystemMetrics,
    get_hardware_profiler,
)

logger = logging.getLogger("jarvis.telemetry_store")


@dataclass
class MetricSnapshot:
    timestamp: float
    iso_time: str
    metrics: SystemMetrics
    power: Dict[str, Any] = field(default_factory=lambda: {
        "ac_online": True,
        "battery_pct": 100.0,
        "has_battery": False,
        "status": "ac_desktop",
        "power_plan": "High Performance",
        "tier": 0,
    })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "iso_time": self.iso_time,
            "metrics": self.metrics.to_dict(),
            "power": self.power,
        }


class TelemetryStore:
    """Thread-safe time-series ring buffer and WebSocket/REST message formatter."""

    def __init__(
        self,
        max_history: int = 300,
        ring_buffer_size: Optional[int] = None,
        profiler: Optional[HardwareProfiler] = None,
        power_guardian: Optional[Any] = None,
        db_path: Optional[Path] = None,
    ):
        capacity = ring_buffer_size if ring_buffer_size is not None else max_history
        self._capacity = capacity
        self._max_history = capacity
        self._buffer: collections.deque[MetricSnapshot] = collections.deque(maxlen=capacity)
        self._named_metrics: Dict[str, collections.deque] = {}
        self._lock = threading.RLock()
        self._profiler = profiler or get_hardware_profiler()
        self._power_guardian = power_guardian
        self._db_path = db_path or (Path.home() / ".jarvis" / "telemetry.db")

        self._sampling_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._init_db()

    def _init_db(self):
        """Initializes SQLite database for turn-latency analytics."""
        try:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self._db_path, timeout=5.0) as conn:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS turn_telemetry (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        timestamp REAL NOT NULL,
                        ttft_ms REAL NOT NULL,
                        tokens_per_sec REAL NOT NULL,
                        total_tokens INTEGER NOT NULL,
                        gpu_wattage REAL DEFAULT 0.0
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.debug("Telemetry DB init skipped: %s", e)

    def set_power_guardian(self, power_guardian: Any):
        """Binds the PowerGuardian instance for combined telemetry snapshots."""
        with self._lock:
            self._power_guardian = power_guardian

    def record_metric(self, metric_name: str, value: float):
        """Records an individual scalar metric into a rolling buffer."""
        with self._lock:
            if metric_name not in self._named_metrics:
                self._named_metrics[metric_name] = collections.deque(maxlen=self._max_history)
            self._named_metrics[metric_name].append(value)

    def push_snapshot(self, metrics: SystemMetrics, power_dict: Optional[Dict[str, Any]] = None):
        """Pushes a new full metrics snapshot into the ring buffer."""
        now = time.time()
        iso = datetime.now(timezone.utc).isoformat()
        p_dict = power_dict
        if p_dict is None and self._power_guardian is not None:
            try:
                p_dict = self._power_guardian.get_power_status().to_dict()
            except Exception:
                p_dict = None

        if p_dict is None:
            p_dict = {
                "ac_online": True,
                "battery_pct": 100.0,
                "has_battery": False,
                "status": "ac_desktop",
                "power_plan": "High Performance",
                "tier": 0,
            }

        snapshot = MetricSnapshot(
            timestamp=now,
            iso_time=iso,
            metrics=metrics,
            power=p_dict,
        )
        with self._lock:
            self._buffer.append(snapshot)
            # Also record named individual metrics for convenience
            self.record_metric("cpu_pct", metrics.cpu_pct)
            self.record_metric("ram_pct", metrics.ram_pct)
            self.record_metric("gpu_pct", metrics.gpu_pct)

    def get_latest(self, metric_name: Optional[str] = None) -> Any:
        """
        Returns the latest recorded value for metric_name, or the latest
        MetricSnapshot if metric_name is None.
        """
        with self._lock:
            if metric_name is not None:
                series = self._named_metrics.get(metric_name)
                if series:
                    return series[-1]
                # Try finding in snapshot
                if self._buffer:
                    latest_snap = self._buffer[-1]
                    if hasattr(latest_snap.metrics, metric_name):
                        return getattr(latest_snap.metrics, metric_name)
                return None

            if not self._buffer:
                return None
            return self._buffer[-1]

    def get_history(self, metric_or_seconds: Union[str, int, float] = 60) -> Any:
        """
        If metric_or_seconds is str, returns list of recorded values for that metric.
        If metric_or_seconds is int/float, returns snapshots within that many seconds.
        """
        with self._lock:
            if isinstance(metric_or_seconds, str):
                return list(self._named_metrics.get(metric_or_seconds, []))

            cutoff = time.time() - float(metric_or_seconds)
            return [s.to_dict() for s in self._buffer if s.timestamp >= cutoff]

    def get_averages(self, seconds: int = 60) -> Dict[str, float]:
        """Calculates average metric values over the last N seconds."""
        history = self.get_history(seconds)
        if not history:
            return {"cpu_pct": 0.0, "ram_pct": 0.0, "gpu_pct": 0.0}

        count = len(history)
        avg_cpu = sum(h["metrics"]["cpu_pct"] for h in history) / count
        avg_ram = sum(h["metrics"]["ram_pct"] for h in history) / count
        avg_gpu = sum(h["metrics"]["gpu_pct"] for h in history) / count
        return {
            "cpu_pct": round(avg_cpu, 2),
            "ram_pct": round(avg_ram, 2),
            "gpu_pct": round(avg_gpu, 2),
        }

    # =========================================================================
    # Formatter Methods for UI Protocols
    # =========================================================================

    def format_system_metrics_envelope(
        self,
        snapshot: Optional[MetricSnapshot] = None,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Formats metrics into the exact `system.metrics` envelope expected by
        `src/shared/protocol.ts` and `src/lib/gateway-client.ts`.
        Dual-embeds top-level `hardware` and `network` for `jarvisBridge.ts` parity.
        """
        snap = snapshot or self.get_latest()
        if snap is None or not isinstance(snap, MetricSnapshot):
            metrics = self._profiler.get_system_metrics()
            snap = MetricSnapshot(
                timestamp=time.time(),
                iso_time=datetime.now(timezone.utc).isoformat(),
                metrics=metrics,
            )

        m = snap.metrics
        p = snap.power
        req_id = request_id or f"metric_{uuid.uuid4().hex[:12]}"

        hardware_dict = {
            "cpu_percent": m.cpu_pct,
            "cpu_temp": m.cpu_temp,
            "cpu_freq_mhz": m.cpu_freq_mhz,
            "cores": m.cores,
            "ram_percent": m.ram_pct,
            "ram_used_gb": m.ram_used_gb,
            "ram_total_gb": m.ram_total_gb,
            "disk_percent": m.disk_pct,
            "disk_used_gb": m.disk_used_gb,
            "disk_total_gb": m.disk_total_gb,
            "battery_percent": p.get("battery_percent", 100.0),
            "battery_charging": p.get("is_charging", False),
            "ac_plugged_in": p.get("ac_online", True),
            "charger_state_changed": p.get("charger_state_changed", False),
            "gpu_name": m.gpu_name,
            "gpu_pct": m.gpu_pct,
            "vram_used_mb": m.vram_used_mb,
            "vram_total_mb": m.vram_total_mb,
            "system_tier": m.system_tier,
        }

        network_dict = {
            "is_online": m.is_online,
            "bytes_sent_rate": m.bytes_sent_rate,
            "bytes_recv_rate": m.bytes_recv_rate,
            "tx_bytes_sec": m.tx_bytes_sec,
            "rx_bytes_sec": m.rx_bytes_sec,
            "latency_ms": m.latency_ms,
        }

        return {
            "type": "system.metrics",
            "request_id": req_id,
            "timestamp": snap.iso_time,
            "payload": {
                "hardware": hardware_dict,
                "network": network_dict,
                "uptime_seconds": m.uptime_seconds,
            },
            "hardware": hardware_dict,
            "network": network_dict,
        }

    def format_legacy_telemetry(self, snapshot: Optional[MetricSnapshot] = None) -> Dict[str, Any]:
        """
        Formats metrics into the legacy `jarvis-telemetry` envelope expected by
        `src/services/jarvisBridge.ts:27-32`.
        """
        snap = snapshot or self.get_latest()
        if snap is None or not isinstance(snap, MetricSnapshot):
            metrics = self._profiler.get_system_metrics()
            snap = MetricSnapshot(
                timestamp=time.time(),
                iso_time=datetime.now(timezone.utc).isoformat(),
                metrics=metrics,
            )

        m = snap.metrics
        p = snap.power

        return {
            "type": "telemetry",
            "hardware": {
                "cpu_percent": m.cpu_pct,
                "ram_percent": m.ram_pct,
                "ram_used_gb": m.ram_used_gb,
                "ram_total_gb": m.ram_total_gb,
                "battery_percent": p.get("battery_percent", 100.0),
                "battery_charging": p.get("is_charging", False),
                "ac_plugged_in": p.get("ac_online", True),
                "charger_state_changed": p.get("charger_state_changed", False),
            },
            "network": {
                "is_online": m.is_online,
                "latency_ms": m.latency_ms,
                "rate": round(m.rx_bytes_sec / 1024.0, 1),
                "tx": min(100, int(m.tx_bytes_sec / 1024.0)),
                "rx": min(100, int(m.rx_bytes_sec / 1024.0)),
            },
            "timestamp": int(snap.timestamp * 1000),
        }

    def format_system_stats(self, snapshot: Optional[MetricSnapshot] = None) -> Dict[str, Any]:
        """
        Formats metrics for FastAPI REST response `GET /api/system/stats`.
        Matches `SystemStatsResponse` in `backend/main.py:67-73`.
        """
        snap = snapshot or self.get_latest()
        if snap is None or not isinstance(snap, MetricSnapshot):
            metrics = self._profiler.get_system_metrics()
            snap = MetricSnapshot(
                timestamp=time.time(),
                iso_time=datetime.now(timezone.utc).isoformat(),
                metrics=metrics,
            )

        m = snap.metrics
        p = snap.power

        return {
            "cpu_pct": m.cpu_pct,
            "ram_used_mb": m.ram_used_mb,
            "ram_total_mb": m.ram_total_mb,
            "gpu_pct": m.gpu_pct,
            "power": {
                "ac_online": p.get("ac_online", True),
                "battery_pct": int(round(p.get("battery_percent", 100.0))),
                "status": p.get("status", "ac_desktop"),
                "power_plan": p.get("power_plan", "High Performance"),
            },
        }

    def record_turn_latency(
        self,
        session_id: str,
        ttft_ms: float,
        tokens_per_sec: float,
        total_tokens: int,
        gpu_wattage: Optional[float] = None,
    ):
        """Persists turn latency metrics to SQLite for OpenJarvis telemetry."""
        try:
            with sqlite3.connect(self._db_path, timeout=5.0) as conn:
                conn.execute(
                    """
                    INSERT INTO turn_telemetry (session_id, timestamp, ttft_ms, tokens_per_sec, total_tokens, gpu_wattage)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (session_id, time.time(), ttft_ms, tokens_per_sec, total_tokens, gpu_wattage or 0.0),
                )
                conn.commit()
        except Exception as e:
            logger.debug("Failed to record turn telemetry: %s", e)

    # =========================================================================
    # Sampling Loop
    # =========================================================================

    def start_sampling(self, interval_sec: float = 1.0):
        """Starts background sampling daemon thread."""
        with self._lock:
            if self._sampling_thread is not None and self._sampling_thread.is_alive():
                return
            self._stop_event.clear()
            self._sampling_thread = threading.Thread(
                target=self._sampling_worker,
                args=(interval_sec,),
                name="JarvisTelemetrySampler",
                daemon=True,
            )
            self._sampling_thread.start()
            logger.info("Telemetry sampling started at %.1f Hz.", 1.0 / interval_sec)

    def stop_sampling(self):
        """Stops background sampling daemon thread."""
        self._stop_event.set()
        if self._sampling_thread is not None:
            self._sampling_thread.join(timeout=2.0)
            self._sampling_thread = None
            logger.info("Telemetry sampling stopped.")

    def is_sampling(self) -> bool:
        return self._sampling_thread is not None and self._sampling_thread.is_alive()

    def _sampling_worker(self, interval: float):
        while not self._stop_event.is_set():
            t0 = time.time()
            try:
                metrics = self._profiler.get_system_metrics()
                self.push_snapshot(metrics)
            except Exception as e:
                logger.warning("Error in telemetry sampling loop: %s", e)

            elapsed = time.time() - t0
            sleep_time = max(interval - elapsed, 0.05)
            self._stop_event.wait(sleep_time)


# Global singleton instance
_global_telemetry_store: Optional[TelemetryStore] = None


def get_telemetry_store() -> TelemetryStore:
    global _global_telemetry_store
    if _global_telemetry_store is None:
        _global_telemetry_store = TelemetryStore()
    return _global_telemetry_store
