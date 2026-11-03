"""
backend/hardware/power_guardian.py
Power Guardian & Instant Charger Interrupt Detector.
Continuously polls Win32 GetSystemPowerStatus via native_core at strictly 1 Hz.
The exact millisecond external power disconnects, immediately triggers OmniVoice alert & telemetry.
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Callable, Optional
import native_core
from backend.audio.omnivoice_tts import omnivoice_tts

logger = logging.getLogger("jarvis.hardware.power")

class PowerGuardian:
    """Hardware watchdog monitoring AC power and battery metrics in real time."""

    def __init__(self, poll_interval: float = 1.0):
        # Strictly 1 Hz telemetry rate to prevent WebSocket flooding
        self.poll_interval = poll_interval
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None
        self._telemetry_listeners: List[Callable[[Dict[str, Any]], Any]] = []
        self._alert_listeners: List[Callable[[str, str], Any]] = []
        self._previous_plugged_in: Optional[bool] = None

    def add_telemetry_listener(self, cb: Callable[[Dict[str, Any]], Any]) -> None:
        self._telemetry_listeners.append(cb)

    def add_alert_listener(self, cb: Callable[[str, str], Any]) -> None:
        self._alert_listeners.append(cb)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("[PowerGuardian] Hardware power watchdog started at 1.0 Hz.")

    def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()

    async def _poll_loop(self) -> None:
        while self._running:
            try:
                metrics = native_core.poll_power_and_metrics()
                current_plugged = metrics.get("ac_plugged_in", True)
                battery_pct = metrics.get("battery_percent", 100)

                # Check for state transition: only trigger alert on actual state change
                if self._previous_plugged_in is not None:
                    # Transition: Plugged -> Unplugged
                    if self._previous_plugged_in and not current_plugged:
                        alert_msg = f"Sir, external power has been disconnected. Running on internal battery at {battery_pct} percent."
                        logger.warning(f"[PowerGuardian] CHARGER DISCONNECTED: {alert_msg}")
                        # 1. Trigger voice announcement
                        asyncio.create_task(omnivoice_tts.speak(alert_msg))
                        # 2. Push priority alert to TerminalLogs
                        for cb in self._alert_listeners:
                            try:
                                cb("CRITICAL", alert_msg)
                            except Exception:
                                pass

                    # Transition: Unplugged -> Plugged
                    elif not self._previous_plugged_in and current_plugged:
                        alert_msg = "External power connection restored, Sir."
                        logger.info(f"[PowerGuardian] CHARGER RESTORED: {alert_msg}")
                        asyncio.create_task(omnivoice_tts.speak(alert_msg))
                        for cb in self._alert_listeners:
                            try:
                                cb("SUCCESS", alert_msg)
                            except Exception:
                                pass

                self._previous_plugged_in = current_plugged

                # Broadcast 1 Hz telemetry frame
                for cb in self._telemetry_listeners:
                    try:
                        cb(metrics)
                    except Exception:
                        pass

                await asyncio.sleep(self.poll_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[PowerGuardian] Polling loop error: {e}")
                await asyncio.sleep(1.0)

power_guardian = PowerGuardian(poll_interval=1.0)
