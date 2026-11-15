"""
backend/senses/mediapipe_gestures.py
====================================
MediaPipeGestures: Real-time hand landmark tracking and air-gesture recognition.
Recognizes air gestures (swipe left, swipe right, fist, open palm, pointing, pinch, victory)
with frame-rate independent exponential damping and palm-scale-invariant pinch detection.
Provides robust synthetic fallback when mediapipe is not installed or camera is offline.
"""

import logging
import math
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    HAS_MEDIAPIPE = True
except ImportError:
    HAS_MEDIAPIPE = False

logger = logging.getLogger("jarvis.senses.mediapipe_gestures")

KNOWN_GESTURES: List[str] = [
    "swipe_left",
    "swipe_right",
    "open_palm",
    "closed_fist",
    "thumb_up",
    "thumb_down",
    "pointing_up",
    "victory",
    "pinch",
    "pinch_click",
    "scroll_up",
    "scroll_down",
]


@dataclass
class GestureEvent:
    gesture: str
    confidence: float
    pinch_ratio: float
    timestamp: float
    action: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class MediaPipeGestures:
    """
    Air-gesture recognizer integrating hand landmark detection with
    frame-rate independent smoothing and synthetic fallback.
    """
    def __init__(
        self,
        min_confidence: float = 0.5,
        gesture_task_path: Optional[str] = None,
        damping_factor: float = 12.0,
    ):
        self.min_confidence = min_confidence
        self.gesture_task_path = gesture_task_path
        self.damping_factor = damping_factor
        self.known_gestures: List[str] = list(KNOWN_GESTURES)

        self._callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self._current_gesture: Optional[str] = None
        self._palm_history: deque = deque(maxlen=15)
        self._smoothed_landmarks: Optional[List[Dict[str, float]]] = None
        self._last_process_time: float = time.time()
        self._is_pinched: bool = False

        self._recognizer = None
        if HAS_MEDIAPIPE and gesture_task_path:
            self._init_mediapipe(gesture_task_path)

    def _init_mediapipe(self, task_path: str) -> None:
        try:
            base_opts = python.BaseOptions(model_asset_path=task_path)
            options = vision.GestureRecognizerOptions(
                base_options=base_opts,
                running_mode=vision.RunningMode.LIVE_STREAM,
                num_hands=2,
                min_hand_detection_confidence=self.min_confidence,
                min_tracking_confidence=self.min_confidence,
                result_callback=self._mediapipe_async_callback,
            )
            self._recognizer = vision.GestureRecognizer.create_from_options(options)
            logger.info("MediaPipe GestureRecognizer initialized in LIVE_STREAM mode")
        except Exception as e:
            logger.warning("Could not initialize MediaPipe recognizer: %s; using fallback", e)
            self._recognizer = None

    def _mediapipe_async_callback(self, result: Any, output_image: Any, timestamp_ms: int) -> None:
        if not result or not result.hand_landmarks:
            return
        hand = result.hand_landmarks[0]
        canned = result.gestures[0][0].category_name if result.gestures and result.gestures[0] else "None"
        raw_landmarks = [{"x": p.x, "y": p.y, "z": p.z} for p in hand]
        dt = (timestamp_ms / 1000.0) - self._last_process_time
        self._last_process_time = timestamp_ms / 1000.0
        smoothed = self.smooth_landmarks(raw_landmarks, dt=max(0.001, dt))
        self._analyze_hand(smoothed, canned, timestamp_ms / 1000.0)

    def smooth_landmarks(
        self,
        current_landmarks: List[Dict[str, float]],
        dt: Optional[float] = None,
    ) -> List[Dict[str, float]]:
        """
        Frame-rate independent landmark smoothing using exponential damping:
        S_t = S_{t-1} + (X_t - S_{t-1}) * (1 - exp(-damping_factor * dt))
        """
        if not current_landmarks:
            return []

        if self._smoothed_landmarks is None or len(self._smoothed_landmarks) != len(current_landmarks):
            self._smoothed_landmarks = [dict(lm) for lm in current_landmarks]
            return self._smoothed_landmarks

        now = time.time()
        delta_t = dt if dt is not None else max(0.001, min(0.1, now - self._last_process_time))
        smoothing_weight = 1.0 - math.exp(-self.damping_factor * delta_t)

        smoothed: List[Dict[str, float]] = []
        for prev, curr in zip(self._smoothed_landmarks, current_landmarks):
            sm_point = {
                "x": prev["x"] + (curr["x"] - prev["x"]) * smoothing_weight,
                "y": prev["y"] + (curr["y"] - prev["y"]) * smoothing_weight,
                "z": prev["z"] + (curr["z"] - prev["z"]) * smoothing_weight,
            }
            smoothed.append(sm_point)

        self._smoothed_landmarks = smoothed
        return smoothed

    def detect(self, frame: Optional[np.ndarray]) -> Optional[Dict[str, Any]]:
        if frame is None:
            return None

        if self._recognizer is not None and HAS_MEDIAPIPE and HAS_CV2:
            try:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                ts_ms = int(time.time() * 1000)
                self._recognizer.recognize_async(mp_image, ts_ms)
                return self._build_gesture_dict(self._current_gesture or "none", 0.9)
            except Exception as e:
                logger.debug("Error in recognize_async: %s", e)

        return self._detect_synthetic(frame)

    def _detect_synthetic(self, frame: np.ndarray) -> Optional[Dict[str, Any]]:
        if self._current_gesture:
            return self._build_gesture_dict(self._current_gesture, 0.95)
        return None

    def process_frame(self, frame: Optional[np.ndarray]) -> Optional[Dict[str, Any]]:
        res = self.detect(frame)
        if res and res.get("gesture") and res["gesture"] != "none":
            for cb in self._callbacks:
                try:
                    cb(res)
                except Exception as e:
                    logger.warning("Error invoking gesture callback: %s", e)
        return res

    def get_current_gesture(self) -> Optional[str]:
        return self._current_gesture

    def on_gesture(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        self._callbacks.append(callback)

    def trigger_mock_gesture(self, gesture_name: str, confidence: float = 0.95) -> Dict[str, Any]:
        canonical = gesture_name.lower().replace(" ", "_")
        self._current_gesture = canonical
        res = self._build_gesture_dict(canonical, confidence)
        for cb in self._callbacks:
            try:
                cb(res)
            except Exception as e:
                logger.warning("Error invoking gesture callback: %s", e)
        return res

    def _analyze_hand(self, landmarks: List[Dict[str, float]], canned: str, now_ts: float) -> None:
        if len(landmarks) < 21:
            return

        l0 = landmarks[0]
        l4 = landmarks[4]
        l8 = landmarks[8]
        l9 = landmarks[9]

        palm_scale = math.hypot(l0["x"] - l9["x"], l0["y"] - l9["y"]) + 1e-6
        pinch_dist = math.hypot(l4["x"] - l8["x"], l4["y"] - l8["y"])
        pinch_ratio = pinch_dist / palm_scale

        self._palm_history.append((now_ts, l9["x"], l9["y"]))

        detected_gesture = None
        if pinch_ratio < 0.28:
            self._is_pinched = True
            detected_gesture = "pinch_click"
        elif pinch_ratio > 0.38 and self._is_pinched:
            self._is_pinched = False

        if not detected_gesture and len(self._palm_history) >= 4:
            t_old, x_old, _ = self._palm_history[0]
            t_new, x_new, _ = self._palm_history[-1]
            dt = t_new - t_old
            if dt > 0.05:
                vx = (x_new - x_old) / dt
                if vx < -0.65:
                    detected_gesture = "swipe_left"
                    self._palm_history.clear()
                elif vx > 0.65:
                    detected_gesture = "swipe_right"
                    self._palm_history.clear()

        if not detected_gesture:
            canned_map = {
                "Open_Palm": "open_palm",
                "Closed_Fist": "closed_fist",
                "Thumb_Up": "thumb_up",
                "Thumb_Down": "thumb_down",
                "Pointing_Up": "pointing_up",
                "Victory": "victory",
            }
            detected_gesture = canned_map.get(canned)

        if detected_gesture:
            self._current_gesture = detected_gesture
            event_dict = self._build_gesture_dict(detected_gesture, 0.9, pinch_ratio)
            for cb in self._callbacks:
                try:
                    cb(event_dict)
                except Exception as e:
                    logger.warning("Error in on_gesture callback: %s", e)

    def _build_gesture_dict(self, gesture: str, confidence: float, pinch_ratio: float = 1.0) -> Dict[str, Any]:
        return {
            "gesture": gesture,
            "confidence": confidence,
            "pinch_ratio": round(pinch_ratio, 3),
            "timestamp": time.time(),
            "action": gesture.upper(),
        }
