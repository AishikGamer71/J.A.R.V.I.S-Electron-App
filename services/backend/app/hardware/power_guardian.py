"""
backend/hardware/power_guardian.py
==================================
Power Guardian & Battery Conservation Monitor for J.A.R.V.I.S. Desktop System.
Assimilated from k2-fsa/OmniVoice & Win32 kernel power APIs (Phase 3.5, Law 3.4).

Provides:
- Real-time AC connection status and battery telemetry via Win32 `GetSystemPowerStatus`
  and `psutil.sensors_battery()`.
- Flawless desktop host detection: Gracefully detects absence of battery
  (AC-only desktop) and reports `AC_DESKTOP` without throwing errors or false alarms.
- Battery conservation tiering (Tiers 0 to 3) for dynamic worker and FPS throttling.
- AC line status transition hooks (unplug/plug) and critical threshold alerts (20%, 10%).
- Power scheme detection via Win32 `powrprof.dll` or `powercfg`.
"""

import ctypes
import logging
import platform
import subprocess
import threading
import time
from ctypes import wintypes
from dataclasses import asdict, dataclass, field
from enum import Enum, IntEnum
from typing import Any, Callable, Dict, List, Optional

import psutil

logger = logging.getLogger("jarvis.power_guardian")


class PowerState(str, Enum):
    AC_DESKTOP = "ac_desktop"
    AC_CHARGING = "ac_charging"
    AC_FULL = "ac_full"
    BATTERY_DISCHARGING = "battery_discharging"
    BATTERY_LOW = "battery_low"
    BATTERY_CRITICAL = "battery_critical"
    UNKNOWN = "unknown"


class PowerConservationTier(IntEnum):
    UNRESTRICTED = 0           # AC online OR Battery > 40%: 60 FPS, 8 workers
    CONSERVATIVE = 1           # Battery 21-40%: 30 FPS, 4 workers
    POWER_SAVER = 2            # Battery 11-20%: 15 FPS, 2 workers, pause sentry
    CRITICAL_PRESERVATION = 3  # Battery <= 10%: 10 FPS, 1 worker, emergency save


class SYSTEM_POWER_STATUS(ctypes.Structure):
    """Win32 SYSTEM_POWER_STATUS structure for kernel32.GetSystemPowerStatus."""
    _fields_ = [
        ("ACLineStatus", wintypes.BYTE),
        ("BatteryFlag", wintypes.BYTE),
        ("BatteryLifePercent", wintypes.BYTE),
        ("SystemStatusFlag", wintypes.BYTE),
        ("BatteryLifeTime", wintypes.DWORD),
        ("BatteryFullLifeTime", wintypes.DWORD),
    ]


@dataclass
class PowerStatus:
    ac_line_status: int
    ac_online: bool
    has_battery: bool
    battery_percent: float
    is_charging: bool
    power_state: PowerState
    conservation_tier: PowerConservationTier
    power_plan: str
    secs_remaining: Optional[int] = None
    charger_state_changed: bool = False
    timestamp: float = field(default_factory=time.time)

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key) or (key in self.to_dict())

    def __getitem__(self, key: str) -> Any:
        if hasattr(self, key):
            val = getattr(self, key)
            if isinstance(val, Enum):
                return val.value
            return val
        data = self.to_dict()
        if key in data:
            return data[key]
        raise KeyError(key)

    def keys(self):
        return self.to_dict().keys()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ac_line_status": self.ac_line_status,
            "ac_online": self.ac_online,
            "has_battery": self.has_battery,
            "battery_percent": round(self.battery_percent, 1),
            "is_charging": self.is_charging,
            "power_state": self.power_state.value,
            "conservation_tier": int(self.conservation_tier.value),
            "power_plan": self.power_plan,
            "secs_remaining": self.secs_remaining,
            "charger_state_changed": self.charger_state_changed,
            "timestamp": self.timestamp,
        }

    def to_stats_power_dict(self) -> Dict[str, Any]:
        """Formats for FastAPI `GET /api/system/stats` response."""
        return {
            "ac_online": self.ac_online,
            "battery_pct": int(round(self.battery_percent)),
            "status": self.power_state.value,
            "power_plan": self.power_plan,
            "has_battery": self.has_battery,
            "tier": int(self.conservation_tier.value),
        }


class PowerGuardian:
    """Monitors system power status, active power plans, and enforces conservation tiers."""

    def __init__(
        self,
        polling_interval_ms: int = 50,
        alert_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        voice_speak_callback: Optional[Callable[[str], None]] = None,
    ):
        self.polling_interval_ms = polling_interval_ms
        self.alert_callback = alert_callback
        self.voice_speak_callback = voice_speak_callback

        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._monitoring_thread: Optional[threading.Thread] = None
        self._last_status: Optional[PowerStatus] = None
        self._listeners: List[Callable[[Dict[str, Any]], None]] = []
        self._has_battery = True
        self._low_threshold_fired = False
        self._crit_threshold_fired = False
        self._cached_power_plan: Optional[str] = None
        self._last_plan_check: float = 0.0

        # Perform initial detection
        self._last_status = self.get_power_status()
        self._has_battery = self._last_status.has_battery
        if not self._has_battery:
            logger.info("Host identified as AC-powered Desktop (no battery detected). Power Guardian operating in Tier 0.")

    def register_listener(self, callback: Callable[[Dict[str, Any]], None]):
        """Registers a listener for power state change events."""
        with self._lock:
            if callback not in self._listeners:
                self._listeners.append(callback)

    def notify_change(self, event_data: Dict[str, Any]):
        """Dispatches an event or state dict to all registered listeners."""
        with self._lock:
            listeners = list(self._listeners)
        for cb in listeners:
            try:
                cb(event_data)
            except Exception as e:
                logger.debug("Error invoking power listener: %s", e)

    def determine_power_profile(self, ac_online: bool, battery_pct: float) -> str:
        """
        Determines power profile string ('performance', 'conservative', or 'power_saver').
        - On AC: 'performance'
        - On Battery <= 20%: 'power_saver'
        - On Battery <= 40%: 'conservative'
        - On Battery > 40%: 'performance'
        """
        if ac_online:
            return "performance"
        if battery_pct <= 20.0:
            return "power_saver"
        if battery_pct <= 40:
            return "conservative"
        return "performance"

    def _get_active_power_plan(self) -> str:
        """Retrieves active Windows power scheme name with 10-second caching."""
        now = time.time()
        if self._cached_power_plan and (now - self._last_plan_check < 10.0):
            return self._cached_power_plan

        self._last_plan_check = now
        plan = "Balanced"

        if platform.system() == "Windows":
            # 1. Try Win32 powrprof.dll PowerGetActiveScheme
            try:
                import uuid
                powrprof = ctypes.windll.LoadLibrary("powrprof.dll")
                guid_ptr = ctypes.c_void_p()
                if powrprof.PowerGetActiveScheme(None, ctypes.byref(guid_ptr)) == 0 and guid_ptr.value:
                    guid_bytes = ctypes.string_at(guid_ptr.value, 16)
                    scheme_guid = str(uuid.UUID(bytes_le=guid_bytes)).lower()
                    guid_map = {
                        "381b4222-f694-41f0-9685-ff5bb260df2e": "Balanced",
                        "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c": "High Performance",
                        "a1841308-3541-4fab-bc81-f71556f20b4a": "Power Saver",
                        "7eab3fb8-62c8-461f-a409-d2a98bf1ea62": "Ultimate Performance",
                        "e9a42b02-d5df-448d-aa00-03f14749eb61": "Ultimate Performance",
                    }
                    if scheme_guid in guid_map:
                        self._cached_power_plan = guid_map[scheme_guid]
                        return self._cached_power_plan
            except Exception:
                pass

            # 2. Fallback to powercfg parsing
            try:
                out = subprocess.check_output(["powercfg", "/getactivescheme"], text=True, timeout=1.0)
                import re
                match = re.search(r"\((.*?)\)", out)
                if match:
                    plan = match.group(1).strip()
            except Exception:
                pass

        self._cached_power_plan = plan
        return plan

    def get_power_status(self) -> PowerStatus:
        """Queries current power status and evaluates conservation tier."""
        with self._lock:
            if platform.system() == "Windows":
                status = self._query_win32_power_status()
            else:
                status = self._query_psutil_power_status()

            if self._last_status is not None:
                status.charger_state_changed = (status.ac_online != self._last_status.ac_online)

            return status

    def _query_win32_power_status(self) -> PowerStatus:
        """Queries Win32 GetSystemPowerStatus directly."""
        sps = SYSTEM_POWER_STATUS()
        res = ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(sps))
        plan = self._get_active_power_plan()

        if res == 0:
            return self._query_psutil_power_status()

        # ACLineStatus: 0 = Offline, 1 = Online, 255 = Unknown
        ac_online = (sps.ACLineStatus == 1)
        ac_line_status = 1 if ac_online else 0

        # BatteryFlag: bit 7 (128 / 0x80) indicates NO system battery
        battery_flag = sps.BatteryFlag & 0xFF
        has_battery = not bool(battery_flag & 0x80)
        is_charging = bool(battery_flag & 0x08)

        # BatteryLifePercent: 0..100, or 255 if unknown
        raw_pct = sps.BatteryLifePercent & 0xFF
        if not has_battery or raw_pct == 255:
            battery_pct = 100.0
        else:
            battery_pct = float(raw_pct)

        secs_left = sps.BatteryLifeTime if sps.BatteryLifeTime != 0xFFFFFFFF else None

        # Determine power state and conservation tier
        if not has_battery:
            state = PowerState.AC_DESKTOP
            tier = PowerConservationTier.UNRESTRICTED
        elif ac_online:
            state = PowerState.AC_FULL if battery_pct >= 99.0 else PowerState.AC_CHARGING
            tier = PowerConservationTier.UNRESTRICTED
        else:
            if battery_pct <= 10.0:
                state = PowerState.BATTERY_CRITICAL
                tier = PowerConservationTier.CRITICAL_PRESERVATION
            elif battery_pct <= 20.0:
                state = PowerState.BATTERY_LOW
                tier = PowerConservationTier.POWER_SAVER
            elif battery_pct <= 40.0:
                state = PowerState.BATTERY_DISCHARGING
                tier = PowerConservationTier.CONSERVATIVE
            else:
                state = PowerState.BATTERY_DISCHARGING
                tier = PowerConservationTier.UNRESTRICTED

        return PowerStatus(
            ac_line_status=ac_line_status,
            ac_online=ac_online,
            has_battery=has_battery,
            battery_percent=battery_pct,
            is_charging=is_charging,
            power_state=state,
            conservation_tier=tier,
            power_plan=plan,
            secs_remaining=secs_left,
        )

    def _query_psutil_power_status(self) -> PowerStatus:
        """Cross-platform fallback using psutil.sensors_battery()."""
        plan = self._get_active_power_plan()
        batt = psutil.sensors_battery()

        if batt is None:
            # AC-only Desktop host
            return PowerStatus(
                ac_line_status=1,
                ac_online=True,
                has_battery=False,
                battery_percent=100.0,
                is_charging=False,
                power_state=PowerState.AC_DESKTOP,
                conservation_tier=PowerConservationTier.UNRESTRICTED,
                power_plan=plan,
                secs_remaining=None,
            )

        ac_online = bool(batt.power_plugged)
        ac_line_status = 1 if ac_online else 0
        battery_pct = float(batt.percent)
        is_charging = ac_online and battery_pct < 99.0
        secs_left = int(batt.secsleft) if batt.secsleft > 0 else None

        if ac_online:
            state = PowerState.AC_FULL if battery_pct >= 99.0 else PowerState.AC_CHARGING
            tier = PowerConservationTier.UNRESTRICTED
        else:
            if battery_pct <= 10.0:
                state = PowerState.BATTERY_CRITICAL
                tier = PowerConservationTier.CRITICAL_PRESERVATION
            elif battery_pct <= 20.0:
                state = PowerState.BATTERY_LOW
                tier = PowerConservationTier.POWER_SAVER
            elif battery_pct <= 40.0:
                state = PowerState.BATTERY_DISCHARGING
                tier = PowerConservationTier.CONSERVATIVE
            else:
                state = PowerState.BATTERY_DISCHARGING
                tier = PowerConservationTier.UNRESTRICTED

        return PowerStatus(
            ac_line_status=ac_line_status,
            ac_online=ac_online,
            has_battery=True,
            battery_percent=battery_pct,
            is_charging=is_charging,
            power_state=state,
            conservation_tier=tier,
            power_plan=plan,
            secs_remaining=secs_left,
        )

    # =========================================================================
    # Throttling & Conservation Query Helpers
    # =========================================================================

    def get_target_fps(self) -> int:
        status = self.get_power_status()
        tier = status.conservation_tier
        if tier == PowerConservationTier.UNRESTRICTED:
            return 60
        elif tier == PowerConservationTier.CONSERVATIVE:
            return 30
        elif tier == PowerConservationTier.POWER_SAVER:
            return 15
        else:
            return 10

    def get_max_workers(self) -> int:
        status = self.get_power_status()
        tier = status.conservation_tier
        if tier == PowerConservationTier.UNRESTRICTED:
            return 8
        elif tier == PowerConservationTier.CONSERVATIVE:
            return 4
        elif tier == PowerConservationTier.POWER_SAVER:
            return 2
        else:
            return 1

    def is_throttled(self) -> bool:
        return self.get_power_status().conservation_tier > PowerConservationTier.UNRESTRICTED

    def should_pause_sentry(self) -> bool:
        return self.get_power_status().conservation_tier >= PowerConservationTier.POWER_SAVER

    # =========================================================================
    # Transition Checking & Alerts
    # =========================================================================

    def _check_transitions(self, new_status: PowerStatus):
        if not new_status.has_battery:
            return

        old = self._last_status
        if old is None:
            return

        # 1. AC Line Transition (Unplug / Plug)
        if old.ac_online and not new_status.ac_online:
            logger.warning("AC power disconnected. Switched to battery power.")
            self.notify_change({"ac_line_status": 0, "event": "power.unplugged"})
            if self.alert_callback:
                self.alert_callback("power.unplugged", new_status.to_dict())
            if self.voice_speak_callback:
                self.voice_speak_callback("Primary power disconnected. Auxiliary battery engaged.")

        elif not old.ac_online and new_status.ac_online:
            logger.info("AC power restored. Charging commenced.")
            self._low_threshold_fired = False
            self._crit_threshold_fired = False
            self.notify_change({"ac_line_status": 1, "event": "power.plugged"})
            if self.alert_callback:
                self.alert_callback("power.plugged", new_status.to_dict())
            if self.voice_speak_callback:
                self.voice_speak_callback("Primary power restored. Commencing battery recharge.")

        # 2. Critical Battery Threshold Alerts
        if not new_status.ac_online:
            if new_status.battery_percent <= 20.0 and not self._low_threshold_fired:
                self._low_threshold_fired = True
                logger.warning("Low battery threshold reached: %.1f%%", new_status.battery_percent)
                self.notify_change({"battery_pct": new_status.battery_percent, "event": "power.battery_low"})
                if self.alert_callback:
                    self.alert_callback("power.battery_low", new_status.to_dict())
                if self.voice_speak_callback:
                    self.voice_speak_callback("Warning, sir. Battery reserves have fallen below 20 percent.")

            if new_status.battery_percent <= 10.0 and not self._crit_threshold_fired:
                self._crit_threshold_fired = True
                logger.critical("Critical battery threshold reached: %.1f%%", new_status.battery_percent)
                self.notify_change({"battery_pct": new_status.battery_percent, "event": "power.battery_critical"})
                if self.alert_callback:
                    self.alert_callback("power.battery_critical", new_status.to_dict())
                if self.voice_speak_callback:
                    self.voice_speak_callback("Emergency power threshold reached: 10 percent. Immediate charging required.")

    # =========================================================================
    # Background Monitoring Thread
    # =========================================================================

    def start(self):
        """Starts background power monitoring thread."""
        with self._lock:
            if self._monitoring_thread is not None and self._monitoring_thread.is_alive():
                return
            self._stop_event.clear()
            self._monitoring_thread = threading.Thread(
                target=self._monitoring_worker,
                name="JarvisPowerGuardian",
                daemon=True,
            )
            self._monitoring_thread.start()
            logger.info("Power Guardian monitoring loop started (%d ms interval).", self.polling_interval_ms)

    def stop(self):
        """Stops background power monitoring thread."""
        self._stop_event.set()
        if self._monitoring_thread is not None:
            self._monitoring_thread.join(timeout=2.0)
            self._monitoring_thread = None
            logger.info("Power Guardian monitoring loop stopped.")

    def is_running(self) -> bool:
        return self._monitoring_thread is not None and self._monitoring_thread.is_alive()

    def _monitoring_worker(self):
        interval = self.polling_interval_ms / 1000.0
        while not self._stop_event.is_set():
            try:
                new_status = self.get_power_status()
                self._check_transitions(new_status)
                self._last_status = new_status
            except Exception as e:
                logger.debug("Error in power monitoring tick: %s", e)

            self._stop_event.wait(interval)


# Global singleton instance
_global_power_guardian: Optional[PowerGuardian] = None


def get_power_guardian() -> PowerGuardian:
    global _global_power_guardian
    if _global_power_guardian is None:
        _global_power_guardian = PowerGuardian()
    return _global_power_guardian
