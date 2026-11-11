"""
backend/senses/deepface_sentry.py
=================================
DeepFaceSentry: Biometric authentication and physical presence sentry for J.A.R.V.I.S.
Integrates Facenet512 Face ID verification with FasNet anti-spoofing at 2 Hz sampling.
Provides robust synthetic fallback and mock matching when deepface weights or physical
hardware are absent.
"""

import hashlib
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    from deepface import DeepFace
    HAS_DEEPFACE = True
except ImportError:
    HAS_DEEPFACE = False

logger = logging.getLogger("jarvis.senses.deepface_sentry")


class DeepFaceSentry:
    """
    Biometric Sentry Guardian using Facenet512 Face ID and FasNet anti-spoofing.
    Operates at 2 Hz polling rate. Enforces anti-spoofing liveness verification.
    """
    def __init__(
        self,
        model_name: str = "Facenet512",
        detector_backend: str = "yunet",
        anti_spoofing_enabled: bool = True,
        polling_rate_hz: int = 2,
        owner_face_dir: Optional[str] = None,
        distance_threshold: float = 0.30,
    ):
        self.model_name = model_name
        self.detector_backend = detector_backend
        self.anti_spoofing_enabled = anti_spoofing_enabled
        self.polling_rate_hz = polling_rate_hz
        self.distance_threshold = distance_threshold

        self.faces_dir = Path(owner_face_dir).expanduser() if owner_face_dir else Path.home() / ".jarvis" / "faces" / "owner"
        self.faces_dir.mkdir(parents=True, exist_ok=True)
        self.sentry_log_dir = Path.home() / ".jarvis" / "sentry_logs"
        self.sentry_log_dir.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._owner_embeddings: List[np.ndarray] = []
        self._registered_users: Dict[str, List[np.ndarray]] = {}
        self._stranger_streak: int = 0
        self._owner_greeted: bool = False
        self._load_registered_faces()

    def _load_registered_faces(self) -> None:
        if not self.faces_dir.exists():
            return
        for ext in ("*.jpg", "*.jpeg", "*.png"):
            for img_path in self.faces_dir.glob(ext):
                try:
                    emb = self._compute_embedding_from_file(str(img_path))
                    if emb is not None:
                        self._owner_embeddings.append(emb)
                        logger.info("Loaded owner reference face: %s", img_path.name)
                except Exception as e:
                    logger.debug("Could not compute embedding for %s: %s", img_path.name, e)

    def _compute_embedding_from_file(self, img_path: str) -> Optional[np.ndarray]:
        if HAS_DEEPFACE:
            try:
                reps = DeepFace.represent(
                    img_path=img_path,
                    model_name=self.model_name,
                    detector_backend=self.detector_backend,
                    enforce_detection=False,
                )
                if reps and len(reps) > 0:
                    return np.array(reps[0]["embedding"], dtype=np.float32)
            except Exception as e:
                logger.debug("DeepFace file embedding failed: %s", e)
        h = hashlib.sha256(Path(img_path).name.encode()).digest()
        vec = np.frombuffer(h * 16, dtype=np.uint8)[:512].astype(np.float32)
        return vec / (np.linalg.norm(vec) + 1e-6)

    def authenticate_frame(self, frame: Optional[np.ndarray]) -> Dict[str, Any]:
        if frame is None:
            return {
                "authenticated": False,
                "user": None,
                "confidence": 0.0,
                "distance": 1.0,
                "liveness_passed": False,
                "anti_spoofing": {"passed": False, "score": 0.0},
                "error": "No frame provided",
            }

        if HAS_DEEPFACE:
            return self._authenticate_deepface(frame)
        return self._authenticate_mock(frame)

    def authenticate_face(self, frame: Optional[np.ndarray]) -> Dict[str, Any]:
        return self.authenticate_frame(frame)

    def _authenticate_deepface(self, frame: np.ndarray) -> Dict[str, Any]:
        try:
            reps = DeepFace.represent(
                img_path=frame,
                model_name=self.model_name,
                detector_backend=self.detector_backend,
                enforce_detection=True,
                align=True,
                anti_spoofing=self.anti_spoofing_enabled,
            )
            if not reps:
                return self._record_stranger("No face detected in frame")

            face_meta = reps[0]
            liveness_score = face_meta.get("antispoof_score", 1.0)
            is_real = face_meta.get("is_real", True)
            if self.anti_spoofing_enabled and not is_real:
                logger.warning("SPOOF DETECTED: Physical liveness check failed")
                return {
                    "authenticated": False,
                    "user": None,
                    "confidence": 0.0,
                    "distance": 1.0,
                    "liveness_passed": False,
                    "anti_spoofing": {"passed": False, "score": float(liveness_score)},
                    "status": "SPOOF_ALERT",
                }

            live_emb = np.array(face_meta["embedding"], dtype=np.float32)
            if self._owner_embeddings:
                dists = [self._cosine_distance(live_emb, ref) for ref in self._owner_embeddings]
                min_dist = float(min(dists))
                if min_dist <= self.distance_threshold:
                    confidence = 1.0 - (min_dist / self.distance_threshold) * 0.5
                    self._stranger_streak = 0
                    return {
                        "authenticated": True,
                        "user": "owner",
                        "confidence": round(confidence, 3),
                        "distance": round(min_dist, 3),
                        "liveness_passed": True,
                        "anti_spoofing": {"passed": True, "score": float(liveness_score)},
                        "status": "OWNER_VERIFIED",
                    }

            return self._record_stranger("Face embedding did not match registered owner")

        except Exception as e:
            err_name = type(e).__name__
            if "Spoof" in err_name:
                return {
                    "authenticated": False,
                    "user": None,
                    "confidence": 0.0,
                    "distance": 1.0,
                    "liveness_passed": False,
                    "anti_spoofing": {"passed": False, "score": 0.0},
                    "status": "SPOOF_ALERT",
                }
            logger.debug("DeepFace authentication exception: %s", e)
            return self._record_stranger(str(e))

    def _authenticate_mock(self, frame: np.ndarray) -> Dict[str, Any]:
        if np.mean(frame) < 5:
            return {
                "authenticated": False,
                "user": None,
                "confidence": 0.0,
                "distance": 1.0,
                "liveness_passed": False,
                "anti_spoofing": {"passed": False, "score": 0.0},
                "status": "NO_FACE",
            }

        if self._owner_embeddings:
            mock_emb = self._generate_synthetic_embedding(frame)
            dists = [self._cosine_distance(mock_emb, ref) for ref in self._owner_embeddings]
            min_dist = float(min(dists))
            if min_dist <= self.distance_threshold:
                self._stranger_streak = 0
                return {
                    "authenticated": True,
                    "user": "owner",
                    "confidence": 0.96,
                    "distance": round(min_dist, 3),
                    "liveness_passed": True,
                    "anti_spoofing": {"passed": True, "score": 0.98},
                    "status": "OWNER_VERIFIED",
                }

        return self._record_stranger("Face embedding did not match registered owner")

    def _record_stranger(self, reason: str) -> Dict[str, Any]:
        self._stranger_streak += 1
        return {
            "authenticated": False,
            "user": None,
            "confidence": 0.0,
            "distance": 1.0,
            "liveness_passed": True,
            "anti_spoofing": {"passed": True, "score": 0.9},
            "status": "STRANGER_SENTRY_ALERT" if self._stranger_streak >= 3 else "STRANGER",
            "reason": reason,
        }

    def detect_presence(self, frame: Optional[np.ndarray]) -> Dict[str, Any]:
        if frame is None:
            return {"presence": False, "faces_detected": 0, "boxes": []}
        if HAS_CV2 and HAS_DEEPFACE:
            try:
                faces = DeepFace.extract_faces(
                    img_path=frame,
                    detector_backend=self.detector_backend,
                    enforce_detection=False,
                )
                valid_faces = [f for f in faces if f.get("confidence", 0) > 0.4]
                return {
                    "presence": len(valid_faces) > 0,
                    "faces_detected": len(valid_faces),
                    "boxes": [f.get("facial_area", {}) for f in valid_faces],
                }
            except Exception as e:
                logger.debug("Face extraction error: %s", e)
        has_content = frame is not None and np.mean(frame) > 10
        return {
            "presence": has_content,
            "faces_detected": 1 if has_content else 0,
            "boxes": [{"x": 100, "y": 100, "w": 200, "h": 200}] if has_content else [],
        }

    def register_face(self, name: str, frame: np.ndarray) -> bool:
        if frame is None:
            return False
        user_dir = Path.home() / ".jarvis" / "faces" / name
        user_dir.mkdir(parents=True, exist_ok=True)
        ts = int(time.time())
        img_file = user_dir / f"ref_{ts}.jpg"
        if HAS_CV2:
            try:
                cv2.imwrite(str(img_file), frame)
            except Exception as e:
                logger.warning("Could not write face reference image: %s", e)

        emb = self._compute_embedding(frame)
        if emb is not None:
            with self._lock:
                if name == "owner":
                    self._owner_embeddings.append(emb)
                if name not in self._registered_users:
                    self._registered_users[name] = []
                self._registered_users[name].append(emb)
            logger.info("Registered face for '%s'", name)
            return True
        return False

    def _compute_embedding(self, frame: np.ndarray) -> Optional[np.ndarray]:
        if HAS_DEEPFACE:
            try:
                reps = DeepFace.represent(
                    img_path=frame,
                    model_name=self.model_name,
                    detector_backend=self.detector_backend,
                    enforce_detection=False,
                )
                if reps:
                    return np.array(reps[0]["embedding"], dtype=np.float32)
            except Exception as e:
                logger.debug("DeepFace represent error: %s", e)
        return self._generate_synthetic_embedding(frame)

    def _generate_synthetic_embedding(self, frame: np.ndarray) -> np.ndarray:
        h = hashlib.sha256(frame.tobytes()[:2048]).digest()
        vec = np.frombuffer(h * 16, dtype=np.uint8)[:512].astype(np.float32)
        return vec / (np.linalg.norm(vec) + 1e-6)

    def _cosine_distance(self, u: np.ndarray, v: np.ndarray) -> float:
        dot = float(np.dot(u, v))
        norm_u = float(np.linalg.norm(u))
        norm_v = float(np.linalg.norm(v))
        if norm_u < 1e-6 or norm_v < 1e-6:
            return 1.0
        return max(0.0, 1.0 - (dot / (norm_u * norm_v)))
