"""
tests/test_adversarial_m5_vision_mobile.py
===========================================
Milestone M5 Adversarial Stress & Vulnerability Test Suite.
Authored by challenger_m5_1 (Empirical Challenger).

Subsystems Covered:
1. CameraHub (SPMC non-blocking queue dropping, FPS mismatch, rapid start/stop cycles, synthetic fallback)
2. MediaPipeGestures (corrupted/null frames, landmark damping against oscillations, scale-invariant pinch click)
3. DeepFaceSentry (null frame, stranger streaks & sentry alerts, anti-spoofing rejection, mock mode discrepancies)
4. MobileRunService (shell injection defenses, command validation, mock device fallbacks, negative coords)
5. Crawl4AIService & GPTResearcherService (invalid schemes, malformed HTML, empty URLs, citation parsing, report layout)
"""

import math
import queue
import time
import unittest
from unittest.mock import MagicMock, patch
import numpy as np

from backend.senses.camera_hub import CameraHub
from backend.senses.mediapipe_gestures import MediaPipeGestures
import backend.senses.deepface_sentry as dfs_module
from backend.senses.deepface_sentry import DeepFaceSentry
from backend.senses.mobilerun_service import MobileRunService
from backend.senses.crawl4ai_service import Crawl4AIService, CrawlResult
from backend.senses.gpt_researcher_service import GPTResearcherService, ResearchReport


class TestCameraHubAdversarial(unittest.TestCase):
    """Adversarial and stress verification for CameraHub SPMC engine."""

    def test_01_exclusive_single_ownership(self):
        """Verify exclusive single ownership contract flag."""
        hub = CameraHub(device_index=999, use_mock_if_unavailable=True)
        self.assertTrue(hub.is_exclusive_owner, "CameraHub must maintain exclusive camera hardware ownership")
        self.assertFalse(hub.is_running())
        self.assertEqual(hub.status, "stopped")

    def test_02_mismatched_fps_consumers(self):
        """Verify multiple consumers with mismatched FPS rates (e.g. 60 FPS and 2 Hz)."""
        hub = CameraHub(device_index=999, target_fps=60, use_mock_if_unavailable=True)
        q_fast = hub.subscribe(name="fast_consumer_60fps", fps=60, max_queue_size=20)
        q_slow = hub.subscribe(name="slow_consumer_2hz", fps=2.0, max_queue_size=10)

        hub.start()
        time.sleep(0.55)  # Allow ~30 frames produced
        hub.stop()

        fast_count = q_fast.qsize()
        slow_count = q_slow.qsize()

        self.assertGreater(fast_count, slow_count, "Fast 60 FPS queue must receive significantly more frames than 2 Hz queue")
        self.assertLessEqual(slow_count, 3, "2 Hz subscriber must receive <= 3 frames in ~0.55s interval")

    def test_03_non_blocking_producer_on_unresponsive_consumer(self):
        """Verify unread subscriber queue does NOT block producer and drops oldest frame."""
        hub = CameraHub(device_index=999, target_fps=100, use_mock_if_unavailable=True)
        # Small queue size = 3
        q_unread = hub.subscribe(name="unresponsive_subscriber", fps=100, max_queue_size=3)

        hub.start()
        time.sleep(0.15)  # Produce ~15 frames
        hub.stop()

        # Producer must have completed without blocking
        self.assertEqual(q_unread.qsize(), 3, "Queue size must remain clamped to max_queue_size")
        self.assertGreaterEqual(hub._frame_seq, 5, "Producer must have advanced frame sequence beyond queue capacity")

    def test_04_fifo_oldest_frame_drop_semantics(self):
        """Verify that when the queue overflows, the oldest frame is dropped first."""
        hub = CameraHub(device_index=999, target_fps=60, use_mock_if_unavailable=True)
        q = hub.subscribe(name="overflow_test", fps=None, max_queue_size=2)

        # Manually invoke producer loop logic for 3 synthetic frames
        f1 = np.full((10, 10, 3), 1, dtype=np.uint8)
        f2 = np.full((10, 10, 3), 2, dtype=np.uint8)
        f3 = np.full((10, 10, 3), 3, dtype=np.uint8)

        # Put f1 and f2 to fill queue
        q.put_nowait(f1)
        q.put_nowait(f2)
        self.assertTrue(q.full())

        # Simulate CameraHub drop-and-put logic
        with hub._lock:
            for sub in hub._subscribers:
                if sub.queue.full():
                    try:
                        sub.queue.get_nowait()
                    except queue.Empty:
                        pass
                sub.queue.put_nowait(f3)

        # First frame retrieved should be f2 (f1 was dropped)
        popped_1 = q.get_nowait()
        popped_2 = q.get_nowait()
        self.assertEqual(int(popped_1[0, 0, 0]), 2, "Oldest frame f1 must have been dropped, leaving f2")
        self.assertEqual(int(popped_2[0, 0, 0]), 3, "Newest frame f3 must be in queue")

    def test_05_rapid_start_stop_thread_safety(self):
        """Stress test rapid start() and stop() cycles for race conditions and deadlocks."""
        hub = CameraHub(device_index=999, target_fps=60, use_mock_if_unavailable=True)
        for cycle in range(12):
            hub.start()
            self.assertTrue(hub.is_running())
            time.sleep(0.005)
            hub.stop()
            self.assertFalse(hub.is_running())
        self.assertEqual(hub.status, "stopped")

    def test_06_synthetic_fallback_frame_generation(self):
        """Verify synthetic optical frame generation when cv2 hardware camera 0 is unavailable."""
        hub = CameraHub(device_index=999, target_fps=30, width=320, height=240, use_mock_if_unavailable=True)
        self.assertFalse(hub.has_hardware())
        frame = hub.get_frame_sync()
        self.assertIsInstance(frame, np.ndarray)
        self.assertEqual(frame.shape, (240, 320, 3))
        self.assertEqual(frame.dtype, np.uint8)
        self.assertGreater(np.mean(frame), 0, "Synthetic frame must contain non-zero pixel values")

    def test_07_dynamic_subscriber_unsubscription(self):
        """Verify dynamic subscriber unsubscription while running does not throw exceptions."""
        hub = CameraHub(device_index=999, target_fps=60, use_mock_if_unavailable=True)
        q1 = hub.subscribe("sub1")
        q2 = hub.subscribe("sub2")
        self.assertEqual(len(hub._subscribers), 2)

        hub.start()
        time.sleep(0.05)
        removed = hub.unsubscribe(q1)
        self.assertTrue(removed)
        self.assertEqual(len(hub._subscribers), 1)
        time.sleep(0.05)
        hub.stop()


class TestMediaPipeGesturesAdversarial(unittest.TestCase):
    """Adversarial and boundary verification for MediaPipeGestures."""

    def setUp(self):
        self.gestures = MediaPipeGestures()

    def test_01_null_and_corrupted_frame_inputs(self):
        """Verify detect() gracefully handles None, 0x0, 1D, and NaN corrupted frames."""
        self.assertIsNone(self.gestures.detect(None))
        # 0x0 empty frame
        empty_frame = np.zeros((0, 0, 3), dtype=np.uint8)
        self.assertIsNone(self.gestures.detect(empty_frame))
        # NaN frame
        nan_frame = np.full((100, 100, 3), np.nan)
        self.assertIsNone(self.gestures.detect(nan_frame))
        # Random high-frequency noise frame
        noise_frame = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
        self.assertIsNone(self.gestures.detect(noise_frame))

    def test_02_landmark_exponential_smoothing_dampens_oscillations(self):
        """Verify exponential damping dampens rapid landmark coordinate oscillations."""
        # Oscillate between x=0.1 and x=0.9
        raw_x_values = [0.1, 0.9] * 10
        smoothed_x_values = []

        # dt = 16ms (60 FPS)
        dt = 0.016
        for x in raw_x_values:
            lm = [{"x": x, "y": 0.5, "z": 0.0}]
            res = self.gestures.smooth_landmarks(lm, dt=dt)
            smoothed_x_values.append(res[0]["x"])

        # Compare amplitude of oscillations
        raw_variance = np.var(raw_x_values)
        smoothed_variance = np.var(smoothed_x_values)
        self.assertLess(smoothed_variance, raw_variance * 0.40,
                        f"Landmark smoothing must reduce variance by >= 60% (raw: {raw_variance:.3f}, smoothed: {smoothed_variance:.3f})")

    def test_03_scale_invariant_pinch_click(self):
        """Verify pinch-click recognition is scale invariant across user distance from sensor."""
        # Hand NEAR sensor: palm_dist = 0.40, pinch_dist = 0.06 -> ratio = 0.15 (< 0.28)
        landmarks_near = [
            {"x": 0.5, "y": 0.8, "z": 0.0} if i == 0 else
            {"x": 0.56, "y": 0.3, "z": 0.0} if i == 4 else
            {"x": 0.50, "y": 0.3, "z": 0.0} if i == 8 else
            {"x": 0.5, "y": 0.4, "z": 0.0} if i == 9 else
            {"x": 0.5, "y": 0.5, "z": 0.0} for i in range(21)
        ]
        self.gestures._analyze_hand(landmarks_near, canned="None", now_ts=1.0)
        self.assertEqual(self.gestures.get_current_gesture(), "pinch_click")
        self.assertTrue(self.gestures._is_pinched)

        # Hand FAR from sensor (4x distance): palm_dist = 0.10, pinch_dist = 0.015 -> ratio = 0.15 (< 0.28)
        self.gestures._is_pinched = False
        landmarks_far = [
            {"x": 0.5, "y": 0.575, "z": 0.0} if i == 0 else
            {"x": 0.515, "y": 0.45, "z": 0.0} if i == 4 else
            {"x": 0.500, "y": 0.45, "z": 0.0} if i == 8 else
            {"x": 0.5, "y": 0.475, "z": 0.0} if i == 9 else
            {"x": 0.5, "y": 0.5, "z": 0.0} for i in range(21)
        ]
        self.gestures._analyze_hand(landmarks_far, canned="None", now_ts=2.0)
        self.assertEqual(self.gestures.get_current_gesture(), "pinch_click")
        self.assertTrue(self.gestures._is_pinched)

    def test_04_pinch_release_hysteresis(self):
        """Verify pinch release hysteresis requiring pinch_ratio > 0.38 to unpinch."""
        # 1. Trigger pinch
        lms_pinch = [
            {"x": 0.5, "y": 0.8, "z": 0.0} if i == 0 else
            {"x": 0.55, "y": 0.3, "z": 0.0} if i == 4 else
            {"x": 0.50, "y": 0.3, "z": 0.0} if i == 8 else
            {"x": 0.5, "y": 0.4, "z": 0.0} if i == 9 else
            {"x": 0.5, "y": 0.5, "z": 0.0} for i in range(21)
        ]
        self.gestures._analyze_hand(lms_pinch, canned="None", now_ts=1.0)
        self.assertTrue(self.gestures._is_pinched)

        # 2. Intermediate distance: pinch_ratio = 0.32 (deadband: between 0.28 and 0.38)
        lms_deadband = [
            {"x": 0.5, "y": 0.8, "z": 0.0} if i == 0 else
            {"x": 0.628, "y": 0.3, "z": 0.0} if i == 4 else
            {"x": 0.50, "y": 0.3, "z": 0.0} if i == 8 else
            {"x": 0.5, "y": 0.4, "z": 0.0} if i == 9 else
            {"x": 0.5, "y": 0.5, "z": 0.0} for i in range(21)
        ]
        self.gestures._analyze_hand(lms_deadband, canned="None", now_ts=1.1)
        self.assertTrue(self.gestures._is_pinched, "Pinch state must remain held in hysteresis deadband")

        # 3. Released distance: pinch_ratio = 0.45 (> 0.38)
        lms_release = [
            {"x": 0.5, "y": 0.8, "z": 0.0} if i == 0 else
            {"x": 0.68, "y": 0.3, "z": 0.0} if i == 4 else
            {"x": 0.50, "y": 0.3, "z": 0.0} if i == 8 else
            {"x": 0.5, "y": 0.4, "z": 0.0} if i == 9 else
            {"x": 0.5, "y": 0.5, "z": 0.0} for i in range(21)
        ]
        self.gestures._analyze_hand(lms_release, canned="None", now_ts=1.2)
        self.assertFalse(self.gestures._is_pinched, "Pinch state must release when pinch_ratio > 0.38")

    def test_05_swipe_velocity_detection(self):
        """Verify swipe left and right detection from rapid palm displacement."""
        # Swipe Left: rapid movement from x=0.8 to x=0.2 in 0.1s (vx = -6.0 < -0.65)
        self.gestures._palm_history.clear()
        for idx, (t, x) in enumerate([(0.0, 0.8), (0.03, 0.6), (0.07, 0.4), (0.10, 0.2)]):
            lms = [
                {"x": x, "y": 0.8, "z": 0.0} if i == 0 else
                {"x": x, "y": 0.4, "z": 0.0} if i == 9 else
                {"x": x + 0.3, "y": 0.3, "z": 0.0} if i == 4 else
                {"x": x, "y": 0.3, "z": 0.0} if i == 8 else
                {"x": x, "y": 0.5, "z": 0.0} for i in range(21)
            ]
            self.gestures._analyze_hand(lms, canned="None", now_ts=t)

        self.assertEqual(self.gestures.get_current_gesture(), "swipe_left")

    def test_06_callback_resilience_to_errors(self):
        """Verify throwing an exception inside gesture callback does not crash recognizer."""
        def faulty_callback(evt):
            raise RuntimeError("Faulty callback exception")

        self.gestures.on_gesture(faulty_callback)
        # Should not raise exception
        res = self.gestures.trigger_mock_gesture("victory", confidence=0.98)
        self.assertEqual(res["gesture"], "victory")


class TestDeepFaceSentryAdversarial(unittest.TestCase):
    """Adversarial and edge-case verification for DeepFaceSentry."""

    def setUp(self):
        self.sentry = DeepFaceSentry(anti_spoofing_enabled=True)

    def test_01_null_frame_authentication(self):
        """Verify authenticate_frame(None) returns unauthenticated result."""
        res = self.sentry.authenticate_frame(None)
        self.assertFalse(res["authenticated"])
        self.assertIsNone(res["user"])
        self.assertFalse(res["liveness_passed"])
        self.assertEqual(res["distance"], 1.0)

    def test_02_black_frame_no_face_detection(self):
        """Verify all-black / dark frame returns NO_FACE in mock mode."""
        black_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        res = self.sentry.authenticate_frame(black_frame)
        self.assertFalse(res["authenticated"])
        self.assertEqual(res["status"], "NO_FACE")

    def test_03_stranger_streak_and_sentry_alert_deepface_engine(self):
        """Verify stranger streak increments to 3 and triggers STRANGER_SENTRY_ALERT."""
        # Simulate DeepFace engine active
        mock_df = MagicMock()
        dfs_module.DeepFace = mock_df
        dfs_module.HAS_DEEPFACE = True

        try:
            # DeepFace detects face, but returns embedding completely orthogonal to registered owner
            self.sentry._owner_embeddings = [np.array([1.0] + [0.0] * 511, dtype=np.float32)]
            # Stranger embedding (orthogonal)
            mock_df.represent.return_value = [{
                "is_real": True,
                "antispoof_score": 0.99,
                "embedding": [0.0] * 511 + [1.0],
            }]
            frame = np.ones((100, 100, 3), dtype=np.uint8) * 50

            # Attempt 1
            r1 = self.sentry.authenticate_frame(frame)
            self.assertEqual(r1["status"], "STRANGER")
            self.assertEqual(self.sentry._stranger_streak, 1)

            # Attempt 2
            r2 = self.sentry.authenticate_frame(frame)
            self.assertEqual(r2["status"], "STRANGER")
            self.assertEqual(self.sentry._stranger_streak, 2)

            # Attempt 3 -> Must trigger sentry alert!
            r3 = self.sentry.authenticate_frame(frame)
            self.assertEqual(r3["status"], "STRANGER_SENTRY_ALERT")
            self.assertEqual(self.sentry._stranger_streak, 3)

            # Verification of owner face resets stranger streak
            mock_df.represent.return_value = [{
                "is_real": True,
                "antispoof_score": 0.99,
                "embedding": [1.0] + [0.0] * 511,
            }]
            r_owner = self.sentry.authenticate_frame(frame)
            self.assertTrue(r_owner["authenticated"])
            self.assertEqual(r_owner["status"], "OWNER_VERIFIED")
            self.assertEqual(self.sentry._stranger_streak, 0, "Stranger streak must reset to 0 upon owner authentication")

        finally:
            dfs_module.HAS_DEEPFACE = False
            if hasattr(dfs_module, "DeepFace"):
                delattr(dfs_module, "DeepFace")

    def test_04_anti_spoofing_physical_liveness_rejection(self):
        """Verify anti-spoofing rejection when is_real is False or spoof score is low."""
        mock_df = MagicMock()
        dfs_module.DeepFace = mock_df
        dfs_module.HAS_DEEPFACE = True

        try:
            # Frame has spoof flag (e.g. photo on phone screen)
            mock_df.represent.return_value = [{
                "is_real": False,
                "antispoof_score": 0.12,
                "embedding": [0.5] * 512,
            }]
            frame = np.ones((100, 100, 3), dtype=np.uint8) * 50

            res = self.sentry.authenticate_frame(frame)
            self.assertFalse(res["authenticated"])
            self.assertEqual(res["status"], "SPOOF_ALERT")
            self.assertFalse(res["liveness_passed"])
            self.assertFalse(res["anti_spoofing"]["passed"])
            self.assertEqual(res["anti_spoofing"]["score"], 0.12)
        finally:
            dfs_module.HAS_DEEPFACE = False
            if hasattr(dfs_module, "DeepFace"):
                delattr(dfs_module, "DeepFace")

    def test_05_presence_detection(self):
        """Verify presence detection for blank and illuminated frames."""
        self.assertFalse(self.sentry.detect_presence(None)["presence"])
        black_frame = np.zeros((50, 50, 3), dtype=np.uint8)
        self.assertFalse(self.sentry.detect_presence(black_frame)["presence"])
        lit_frame = np.ones((50, 50, 3), dtype=np.uint8) * 128
        self.assertTrue(self.sentry.detect_presence(lit_frame)["presence"])

    def test_06_mock_mode_stranger_streak_and_alert(self):
        """Verify mock mode stranger streak increments to 3, triggers STRANGER_SENTRY_ALERT, and owner resets streak."""
        was_has_df = dfs_module.HAS_DEEPFACE
        dfs_module.HAS_DEEPFACE = False
        try:
            mock_sentry = DeepFaceSentry(anti_spoofing_enabled=True)
            owner_emb = np.zeros(512, dtype=np.float32)
            owner_emb[0] = 1.0
            mock_sentry._owner_embeddings = [owner_emb]

            # Create stranger frame whose synthetic embedding is orthogonal/distant from owner_emb
            stranger_frame = np.ones((50, 50, 3), dtype=np.uint8) * 128
            stranger_emb = mock_sentry._generate_synthetic_embedding(stranger_frame)
            self.assertGreater(mock_sentry._cosine_distance(stranger_emb, owner_emb), mock_sentry.distance_threshold)

            # Attempt 1
            r1 = mock_sentry.authenticate_frame(stranger_frame)
            self.assertFalse(r1["authenticated"])
            self.assertEqual(r1["status"], "STRANGER")
            self.assertEqual(mock_sentry._stranger_streak, 1)

            # Attempt 2
            r2 = mock_sentry.authenticate_frame(stranger_frame)
            self.assertFalse(r2["authenticated"])
            self.assertEqual(r2["status"], "STRANGER")
            self.assertEqual(mock_sentry._stranger_streak, 2)

            # Attempt 3 -> Alert trigger
            r3 = mock_sentry.authenticate_frame(stranger_frame)
            self.assertFalse(r3["authenticated"])
            self.assertEqual(r3["status"], "STRANGER_SENTRY_ALERT")
            self.assertEqual(mock_sentry._stranger_streak, 3)

            # Attempt 4 with registered owner frame -> resets streak to 0
            mock_sentry._owner_embeddings = [stranger_emb]
            r_owner = mock_sentry.authenticate_frame(stranger_frame)
            self.assertTrue(r_owner["authenticated"])
            self.assertEqual(r_owner["status"], "OWNER_VERIFIED")
            self.assertEqual(mock_sentry._stranger_streak, 0, "Stranger streak must reset to 0 upon owner authentication")
        finally:
            dfs_module.HAS_DEEPFACE = was_has_df


class TestMobileRunServiceAdversarial(unittest.TestCase):
    """Adversarial and shell-injection verification for MobileRunService."""

    def setUp(self):
        self.service = MobileRunService()

    def test_01_destructive_shell_command_injections_blocked(self):
        """Verify that all dangerous and destructive commands are rejected."""
        destructive_commands = [
            "rm -rf /system",
            "rm -rf /",
            "rm -rf /data",
            "rm -rf /boot",
            "rm -rf /sdcard",
            "rm -r /system",
            "rm -r -f /system",
            "rm -f -r /data",
            "rm -r -f /boot",
            "rm -r -f /sdcard",
            "rm --recursive --force /system",
            "rm -r -f /",
            "rm -f -r /",
            "mkfs.ext4 /dev/block/bootdevice",
            "dd if=/dev/zero of=/dev/block/bootdevice",
            "reboot bootloader",
            "reboot recovery",
            "reboot fastboot",
            "su -c 'rm -rf /'",
            "su 0",
            "chmod 777 /system",
            "format /data",
            "wipe data",
            "fastboot flash boot boot.img",
        ]
        for cmd in destructive_commands:
            is_valid = self.service.validate_adb_command(cmd)
            self.assertFalse(is_valid, f"Command '{cmd}' must be BLOCKED by safety filter")

    def test_02_benign_adb_commands_allowed(self):
        """Verify that standard safe ADB shell commands pass validation."""
        benign_commands = [
            "rm myfile.txt",
            "input tap 100 200",
            "input swipe 100 200 100 800 300",
            "input text hello%sworld",
            "input keyevent 3",
            "dumpsys window windows",
            "am start -n com.android.settings/.Settings",
            "screencap -p /sdcard/screenshot.png",
        ]
        for cmd in benign_commands:
            is_valid = self.service.validate_adb_command(cmd)
            self.assertTrue(is_valid, f"Command '{cmd}' should be ALLOWED")

    def test_03_malformed_and_empty_command_validation(self):
        """Verify non-string and empty commands are safely rejected."""
        self.assertFalse(self.service.validate_adb_command(""))
        self.assertFalse(self.service.validate_adb_command(None))  # type: ignore
        self.assertFalse(self.service.validate_adb_command(12345))  # type: ignore
        self.assertFalse(self.service.validate_adb_command({"cmd": "ls"}))  # type: ignore
        # Whitespace commands must all be strictly rejected
        whitespace_cmds = [" ", "  ", "\t", "\n", "\r\n", "   \t\r\n   "]
        for ws in whitespace_cmds:
            self.assertFalse(self.service.validate_adb_command(ws), f"Whitespace command {repr(ws)} must be rejected")

    def test_04_negative_coordinates_rejected_for_touch_actions(self):
        """Verify negative coordinates are rejected for tap and swipe operations."""
        self.assertFalse(self.service.tap(-10, 50))
        self.assertFalse(self.service.tap(50, -10))
        self.assertFalse(self.service.swipe(-10, 10, 100, 100))
        self.assertFalse(self.service.swipe(10, 10, -50, 100))

    def test_05_mock_device_listing_and_action_resilience(self):
        """Verify mock devices and touch execution succeed gracefully without physical ADB."""
        devices = self.service.list_devices()
        self.assertIsInstance(devices, list)
        self.assertGreaterEqual(len(devices), 1)
        self.assertEqual(devices[0]["model"], "Pixel_8_Pro_Virtual")

        # Mock actions should return True without crashing
        self.assertTrue(self.service.tap(100, 200))
        self.assertTrue(self.service.swipe(100, 200, 300, 400))
        self.assertTrue(self.service.input_text("Test J.A.R.V.I.S."))
        self.assertTrue(self.service.send_key(3))  # KEYCODE_HOME

        task_res = self.service.execute_task("tap 150, 250")
        self.assertEqual(task_res["status"], "success")


class TestCrawl4AIAndGPTResearcherAdversarial(unittest.TestCase):
    """Adversarial and boundary verification for Crawl4AI and GPTResearcher."""

    def setUp(self):
        self.crawler = Crawl4AIService(timeout_sec=5)
        self.researcher = GPTResearcherService(crawler=self.crawler)

    def test_01_url_validation_boundaries(self):
        """Verify URL validation rejects unsupported protocols and malformed URLs."""
        invalid_urls = [
            "",
            "   ",
            "ftp://files.server.org/report.pdf",
            "javascript:alert('xss')",
            "data:text/html,<h1>test</h1>",
            "gopher://gopher.floodgap.com",
            "file_without_scheme.html",
            "http://",
            "https://",
        ]
        for url in invalid_urls:
            self.assertFalse(self.crawler.is_valid_url(url), f"URL '{url}' must be rejected")

        valid_urls = [
            "http://example.com",
            "https://example.com/research",
            "https://sub.domain.org/path?param=value#anchor",
        ]
        for url in valid_urls:
            self.assertTrue(self.crawler.is_valid_url(url), f"URL '{url}' should be valid")

    def test_02_crawl_invalid_schemes_returns_structured_error(self):
        """Verify crawling invalid scheme returns structured CrawlResult with 400 error."""
        res_ftp = self.crawler.crawl("ftp://ftp.test.org/archive.tar.gz")
        self.assertEqual(res_ftp.status, "error")
        self.assertEqual(res_ftp.status_code, 400)
        self.assertIn("Unsupported or malformed URL", res_ftp.error or "")

        res_empty = self.crawler.crawl("")
        self.assertEqual(res_empty.status, "error")
        self.assertEqual(res_empty.status_code, 400)

    def test_03_crawl_about_blank_synthetic_page(self):
        """Verify about:blank returns fast synthetic empty result."""
        res = self.crawler.crawl("about:blank")
        self.assertEqual(res.status, "success")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.title, "Blank Page")
        self.assertEqual(res.markdown, "")

    def test_04_html_to_markdown_malformed_and_unclosed_tags(self):
        """Verify HTML to Markdown parser survives malformed unclosed tags and scripts."""
        malformed_html = """
        <html>
            <head><script>alert('malicious')</script><style>body { color: red; }</style></head>
            <body>
                <div class="cookie-banner-popup">Please accept cookies!</div>
                <nav><a href="/home">Home</a></nav>
                <h1>Autonomous Systems Heading
                <p>Paragraph without closing tag
                <b>Bold text without close
                <i>Italic text
                <div>Nested unclosed div
                <table border="1">
                    <tr><th>Metric</th><th>Score</th></tr>
                    <tr><td>Throughput</td><td>99.9%</td></tr>
                <footer>Page footer</footer>
            </body>
        </html>
        """
        md = self.crawler.html_to_markdown(malformed_html)
        self.assertNotIn("alert('malicious')", md, "Script tags must be removed")
        self.assertNotIn("Please accept cookies!", md, "Cookie banner elements must be removed")
        self.assertNotIn("Page footer", md, "Footer elements must be removed")
        self.assertIn("# Autonomous Systems Heading", md, "Heading must be converted to Markdown")
        self.assertIn("Throughput", md, "Table contents must be preserved")

    def test_05_subquery_formulation_boundaries(self):
        """Verify subquery generator handles empty, None, and varied count requests."""
        self.assertEqual(self.researcher.generate_subqueries(""), ["general background overview"])
        self.assertEqual(self.researcher.generate_subqueries(None), ["general background overview"])  # type: ignore

        sq_1 = self.researcher.generate_subqueries("Deep Learning", count=1)
        self.assertEqual(len(sq_1), 1)

        sq_5 = self.researcher.generate_subqueries("Deep Learning", count=5)
        self.assertEqual(len(sq_5), 5)

    def test_06_inline_citation_extraction(self):
        """Verify inline citation parser extracts and deduplicates citation tokens."""
        text = "Transformer models [1] exhibit high throughput [2], as further verified by [1] and [3]."
        citations = self.researcher.extract_citations(text)
        self.assertEqual(citations, ["[1]", "[2]", ["[3]"][0]])

    def test_07_research_report_formatting_with_empty_inputs(self):
        """Verify format_report handles empty findings and empty sources without crashing."""
        rep = self.researcher.format_report(
            title="Empty Test",
            findings=[],
            sources=[],
            executive_summary="",
        )
        self.assertIn("# Research Report: Empty Test", rep)
        self.assertIn("## Table of Contents", rep)
        self.assertIn("## Executive Summary", rep)
        self.assertIn("No empirical findings identified.", rep)
        self.assertIn("*No external bibliographic references catalogued.*", rep)

    def test_08_autonomous_research_pipeline_offline(self):
        """Verify complete conduct_research execution in offline/mock environment."""
        with patch("backend.senses.gpt_researcher_service._HAS_DDG", False):
            report = self.researcher.conduct_research(
                query="Edge AI Sensor Fusion",
                report_type="technical_brief",
                index_to_memory=False,
            )
            self.assertIsInstance(report, ResearchReport)
            self.assertEqual(report.query, "Edge AI Sensor Fusion")
            self.assertGreaterEqual(len(report.subqueries), 1)
            self.assertGreaterEqual(len(report.detailed_findings), 1)
            self.assertIn("## Table of Contents", report.markdown)

    def test_09_pure_regex_fallback_noise_and_unclosed_tags(self):
        """Verify Crawl4AIService pure-regex fallback strips noise classes and handles unclosed tags when bs4 is disabled."""
        was_has_bs4 = self.crawler._has_bs4
        try:
            self.crawler._has_bs4 = False
            malformed_html = (
                "<html>\n"
                "<head><script>alert('bad');</script><style>.hidden { display: none; }</style></head>\n"
                "<body>\n"
                "  <div class=\"cookie-banner-modal\">Please accept our tracking cookies! <button>Accept</button></div>\n"
                "  <div class=\"popup-advertisement\">Special Discount! Buy Now!</div>\n"
                "  <div class=\"newsletter-signup\">Sign up for daily spam</div>\n"
                "  <nav><a href=\"#\">Navigation link</a></nav>\n"
                "  <header><h1>Header title</h1></header>\n"
                "  <h1>Autonomous Systems Heading\n"
                "  <p>Paragraph without closing tag\n"
                "  <h2>Sub-heading 2\n"
                "  <p>Second paragraph with details.\n"
                "  <ul>\n"
                "    <li>First bullet item\n"
                "    <li>Second bullet item without closing li\n"
                "  </ul>\n"
                "  <footer>Footer copyright 2026</footer>\n"
                "</body>\n"
                "</html>"
            )

            # Test both html_to_markdown (with _has_bs4=False) and direct _regex_html_to_markdown
            md_via_fallback = self.crawler.html_to_markdown(malformed_html)
            md_direct = self.crawler._regex_html_to_markdown(malformed_html)

            for md in (md_via_fallback, md_direct):
                self.assertNotIn("Please accept our tracking cookies!", md, "Cookie banner leaked into markdown")
                self.assertNotIn("Special Discount! Buy Now!", md, "Popup advertisement leaked into markdown")
                self.assertNotIn("Sign up for daily spam", md, "Newsletter signup leaked into markdown")
                self.assertNotIn("alert('bad');", md, "Script tag leaked into markdown")
                self.assertIn("# Autonomous Systems Heading", md, "Heading 1 not converted properly")
                self.assertIn("Paragraph without closing tag", md, "Paragraph text missing")
                self.assertIn("## Sub-heading 2", md, "Heading 2 not converted properly")
                self.assertIn("- First bullet item", md, "List item 1 not converted properly")
                self.assertIn("- Second bullet item without closing li", md, "List item 2 not converted properly")
        finally:
            self.crawler._has_bs4 = was_has_bs4


if __name__ == "__main__":
    unittest.main()
