---
name: vision_biometrics_gestures
description: Real-time optical sensing for MediaPipe air gestures and DeepFace biometric security.
trigger: camera vision, face recognition, hand gesture, sentry mode, biometric auth
tools:
  - camera_hub_status
  - deepface_verify
  - mediapipe_gesture_mode
---

# Vision Biometrics & Gestures Skill

## Purpose & Overview
Integrates real-time optical intelligence through an exclusive Single-Producer Multi-Consumer (SPMC) webcam capture architecture, powering contactless air-gesture system control and biometric facial sentry verification.

## Architecture & Hardware Discipline
- **Exclusive Capture**: `backend/senses/camera_hub.py` is the SOLE process allowed to open `cv2.VideoCapture(0)`.
- **SPMC Frame Dispatch**:
  - High-frequency RGB stream (60 FPS) -> `backend/senses/mediapipe_gestures.py` in `RunningMode.LIVE_STREAM`.
  - Low-frequency BGR stream (2 Hz) -> `backend/senses/deepface_sentry.py` for biometric verification.

## Air-Gesture Control Mappings
1. **Pinch Click**: Palm-scale-invariant ratio $\|L_4 - L_8\|_2 / \|L_0 - L_9\|_2 < 0.28$ triggers click; $> 0.38$ triggers release.
2. **Horizontal Swipe**: Palm velocity $v_x = \Delta x_9 / \Delta t$ triggers `SWIPE_LEFT` / `SWIPE_RIGHT` UI tab navigation.
3. **Two-Finger Scroll**: Vertical delta $\Delta y = ((y_{8,t} + y_{12,t}) - (y_{8,t-1} + y_{12,t-1})) / 2$ controls fluid UI scrolling.
4. **Canned Gestures**: `Open_Palm` (pause/idle), `Closed_Fist` (emergency mute), `Thumb_Up` (confirm), `Thumb_Down` (cancel).

## Biometric Sentry States
1. **`OWNER_VERIFIED`**: Facenet512 embedding matches `~/.jarvis/faces/owner/*.jpg` (cosine distance $\le 0.30$) with FasNet liveness check passed. Triggers personalized greeting ("Welcome back, sir.").
2. **`STRANGER_SENTRY_ALERT`**: 3 consecutive unverified face detections trigger audio warning and sentry snapshot logging to `~/.jarvis/sentry_logs/`. Destructive tools are automatically locked.
3. **`SPOOF_ALERT`**: MiniFASNet physical liveness test fails (photo or screen presentation attack detected). Triggers immediate terminal alarm and voice warning.
