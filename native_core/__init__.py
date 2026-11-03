"""
native_core/__init__.py
Exposes the Win32 high-performance hardware, power, screen capture,
input automation, kill switch, and ECC security shield functions.
Falls back to jarvis_native_fallback seamlessly on any system.
"""

try:
    import jarvis_native_core as _core
except ImportError:
    try:
        from native_core import jarvis_native_core as _core
    except ImportError:
        from native_core import jarvis_native_fallback as _core

poll_power_and_metrics = _core.poll_power_and_metrics
capture_screen_fast = _core.capture_screen_fast
win32_send_input = _core.win32_send_input
check_emergency_abort = _core.check_emergency_abort
reset_emergency_abort = _core.reset_emergency_abort
verify_command_safety = _core.verify_command_safety

__all__ = [
    "poll_power_and_metrics",
    "capture_screen_fast",
    "win32_send_input",
    "check_emergency_abort",
    "reset_emergency_abort",
    "verify_command_safety",
]
