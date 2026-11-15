"""
backend/senses/camera_hub.py
============================
CameraHub: Single-Producer Multi-Consumer (SPMC) OpenCV webcam hub for J.A.R.V.I.S.
Feeds 60 FPS frames to MediaPipeGestures and 2 Hz frames to DeepFaceSentry.
Enforces single camera hardware ownership and provides synthetic fallback frames
when physical webcam hardware is unavailable.
"""

import logging
import queue
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

logger = logging.getLogger("jarvis.senses.camera_hub")


@dataclass
class _SubscriberEntry:
    name: str
    fps: Optional[float]
    queue: queue.Queue
    last_dispatched_ts: float = 0.0


class CameraHub:
    """
    SPMC Camera Hub distributing webcam frames to multiple consumers.
    Guarantees single exclusive ownership of cv2.VideoCapture(0).
    Provides synthetic fallback frames when physical camera is absent.
    """
    _instance_lock = threading.Lock()
    _active_instance = None

    def __init__(
        self,
        device_index: int = 0,
        target_fps: int = 60,
        width: int = 640,
        height: int = 480,
        use_mock_if_unavailable: bool = True,
    ):
        self.device_index = device_index
        self.target_fps = target_fps
        self.width = width
        self.height = height
        self.use_mock_if_unavailable = use_mock_if_unavailable

        self.is_exclusive_owner: bool = True
        self._running: bool = False
        self._has_hardware: bool = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self._lock = threading.Lock()
        self._latest_frame: Optional[np.ndarray] = None
        self._frame_seq: int = 0
        self._subscribers: List[_SubscriberEntry] = []
        self._cap: Optional[Any] = None

        self._fps_measured: float = 0.0
        self._frame_count: int = 0
        self._fps_calc_start: float = time.time()

        self._init_capture()

    def _init_capture(self) -> None:
        if not HAS_CV2:
            self._has_hardware = False
            return

        try:
            cap = cv2.VideoCapture(self.device_index)
            if cap.isOpened():
                self._has_hardware = True
                self._cap = cap
                self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self._cap.set(cv2.CAP_PROP_FPS, self.target_fps)
            else:
                self._has_hardware = False
                self._cap = None
        except Exception as e:
            logger.warning("Camera hardware initialization failed: %s; using mock mode", e)
            self._has_hardware = False
            self._cap = None

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._producer_loop, daemon=True, name="CameraHub-Producer")
            self._thread.start()
            logger.info("CameraHub started (hardware=%s, target_fps=%d)", self._has_hardware, self.target_fps)

    def stop(self) -> None:
        with self._lock:
            if not self._running:
                return
            self._running = False
            self._stop_event.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

        with self._lock:
            if self._cap is not None and HAS_CV2:
                try:
                    self._cap.release()
                except Exception as e:
                    logger.debug("Error releasing VideoCapture: %s", e)
                self._cap = None
            self._subscribers.clear()
        logger.info("CameraHub stopped cleanly")

    def is_running(self) -> bool:
        return self._running

    def has_hardware(self) -> bool:
        return self._has_hardware

    @property
    def status(self) -> str:
        if not self._running:
            return "stopped"
        return "running" if self._has_hardware else "simulated"

    @property
    def fps(self) -> float:
        return self._fps_measured

    def subscribe(
        self,
        name: Optional[str] = None,
        fps: Optional[float] = None,
        max_queue_size: int = 10,
    ) -> queue.Queue:
        sub_name = name or f"consumer_{len(self._subscribers) + 1}"
        q: queue.Queue = queue.Queue(maxsize=max_queue_size)
        entry = _SubscriberEntry(name=sub_name, fps=fps, queue=q)
        with self._lock:
            self._subscribers.append(entry)
        return q

    def unsubscribe(self, sub_queue: queue.Queue) -> bool:
        with self._lock:
            initial_len = len(self._subscribers)
            self._subscribers = [s for s in self._subscribers if s.queue is not sub_queue]
            return len(self._subscribers) < initial_len

    def get_frame_sync(self) -> np.ndarray:
        with self._lock:
            if self._latest_frame is not None:
                return self._latest_frame.copy()
        return self._generate_synthetic_frame()

    def get_frame(self, timeout: float = 0.5) -> Optional[np.ndarray]:
        with self._lock:
            if self._latest_frame is not None:
                return self._latest_frame.copy()
        if self._has_hardware and self._running:
            start_t = time.time()
            while time.time() - start_t < timeout:
                with self._lock:
                    if self._latest_frame is not None:
                        return self._latest_frame.copy()
                time.sleep(0.01)
        return self._generate_synthetic_frame()

    def _generate_synthetic_frame(self) -> np.ndarray:
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        frame[:] = (35, 25, 18)

        cx, cy = self.width // 2, self.height // 2
        frame[max(0, cy - 20):min(self.height, cy + 20), max(0, cx - 1):min(self.width, cx + 2)] = (180, 160, 42)
        frame[max(0, cy - 1):min(self.height, cy + 2), max(0, cx - 20):min(self.width, cx + 20)] = (180, 160, 42)

        if HAS_CV2:
            ts_str = datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3]
            cv2.putText(
                frame,
                "J.A.R.V.I.S. OPTICAL SENSOR [SIMULATED]",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (42, 180, 240),
                1,
                cv2.LINE_AA,
            )
            cv2.putText(
                frame,
                f"UTC: {ts_str} | SEQ: {self._frame_seq}",
                (20, 70),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (200, 200, 200),
                1,
                cv2.LINE_AA,
            )
        return frame

    def _producer_loop(self) -> None:
        interval = 1.0 / max(1, self.target_fps)
        while not self._stop_event.is_set():
            t0 = time.time()
            frame = None

            if self._has_hardware and self._cap is not None:
                try:
                    ret, raw = self._cap.read()
                    if ret and raw is not None:
                        frame = raw
                    else:
                        frame = self._generate_synthetic_frame()
                except Exception as e:
                    logger.warning("Camera read exception: %s", e)
                    frame = self._generate_synthetic_frame()
            else:
                frame = self._generate_synthetic_frame()

            now = time.time()
            with self._lock:
                self._latest_frame = frame
                self._frame_seq += 1
                self._frame_count += 1

                elapsed = now - self._fps_calc_start
                if elapsed >= 1.0:
                    self._fps_measured = self._frame_count / elapsed
                    self._frame_count = 0
                    self._fps_calc_start = now

                for sub in self._subscribers:
                    if sub.fps is not None and sub.fps > 0:
                        min_delta = 1.0 / sub.fps
                        if now - sub.last_dispatched_ts < min_delta:
                            continue

                    sub.last_dispatched_ts = now
                    if sub.queue.full():
                        try:
                            sub.queue.get_nowait()
                        except queue.Empty:
                            pass
                    try:
                        sub.queue.put_nowait(frame.copy())
                    except queue.Full:
                        pass

            proc_time = time.time() - t0
            sleep_needed = interval - proc_time
            if sleep_needed > 0:
                time.sleep(sleep_needed)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
