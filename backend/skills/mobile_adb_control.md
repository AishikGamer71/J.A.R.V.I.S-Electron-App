---
name: mobile_adb_control
description: Wireless Android smartphone automation and live notification bridging.
trigger: phone task, control android, tap phone screen, send text on phone, read phone notifications
tools:
  - mobilerun_phone_task
---

# Mobile ADB Control Skill

## Purpose & Overview
Enables J.A.R.V.I.S. to wirelessly control an Android smartphone and stream live phone events (notifications, SMS, battery alerts) into the desktop HUD and autonomous brain.

## Operational Modes
1. **Wireless ADB Bridge**:
   - Connects over local Wi-Fi via `adb tcpip 5555 && adb connect <ANDROID_DEVICE_IP>:5555`.
   - Executes standard touch, swipe, app launch, and key events.
2. **Portal HTTP & WebSocket Bridge**:
   - Connects to MobileRun Portal app on port `:8080` (HTTP Accessibility state tree) and port `:8081` (WebSocket event stream).
   - Inspects UI hierarchy via `content://com.mobilerun.portal/state`.
   - Types Unicode text seamlessly using `MobilerunKeyboardIME`.
3. **Real-Time Notification Bridge**:
   - Subscribes to `ws://<ANDROID_DEVICE_IP>:8081/?token=<TOKEN>`.
   - Streams incoming `NOTIFICATION_POSTED`, `SMS_RECEIVED`, and `BATTERY_LOW` events directly into J.A.R.V.I.S.'s inbox (`GET /v1/inbox`) and triggers voice announcements.
