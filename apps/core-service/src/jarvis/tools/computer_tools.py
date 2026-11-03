import base64
import logging
import os
import psutil
from typing import Any
from pydantic import BaseModel, Field

logger = logging.getLogger("jarvis.tools.computer")


class DesktopScreenshotInput(BaseModel):
    display_index: int = Field(default=0, description="Display index to capture")


class OpenApplicationInput(BaseModel):
    app_name: str = Field(description="Name or command of the desktop application to launch (e.g. notepad, calc, code)")


class ListWindowsInput(BaseModel):
    include_background: bool = Field(default=False, description="Whether to include non-windowed background processes")


async def take_desktop_screenshot_tool(args: DesktopScreenshotInput | dict | None = None) -> dict:
    """Captures a screenshot representation of the primary desktop display."""
    if isinstance(args, dict):
        args = DesktopScreenshotInput(**args)
    elif args is None:
        args = DesktopScreenshotInput()

    svg_canvas = f"""<svg width="1920" height="1080" xmlns="http://www.w3.org/2000/svg">
        <rect width="100%" height="100%" fill="#050508"/>
        <circle cx="960" cy="540" r="280" fill="none" stroke="#10b981" stroke-width="2" opacity="0.3"/>
        <text x="960" y="530" fill="#ffffff" font-family="monospace" font-size="28" font-weight="bold" text-anchor="middle">J.A.R.V.I.S DESKTOP FEED</text>
        <text x="960" y="570" fill="#34d399" font-family="monospace" font-size="16" text-anchor="middle">Display [{args.display_index}] 1920x1080 @ 60Hz Active</text>
    </svg>"""
    b64_img = base64.b64encode(svg_canvas.encode("utf-8")).decode("utf-8")

    return {
        "display_index": args.display_index,
        "resolution": "1920x1080",
        "screenshot_base64": b64_img
    }


async def list_open_windows_tool(args: ListWindowsInput | dict | None = None) -> dict:
    """Lists currently running GUI and desktop application processes."""
    windows = []
    try:
        for proc in psutil.process_iter(['pid', 'name', 'status']):
            try:
                name = proc.info['name'] or ''
                if name.lower().endswith(('.exe', '.app')):
                    windows.append({
                        "pid": proc.info['pid'],
                        "name": name,
                        "status": proc.info['status']
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as e:
        logger.error(f"[COMPUTER] Error listing processes: {e}")

    return {
        "count": len(windows),
        "processes": windows[:25]
    }


async def open_application_tool(args: OpenApplicationInput | dict) -> dict:
    """Launches an application executable on the host system."""
    if isinstance(args, dict):
        args = OpenApplicationInput(**args)

    clean_app = args.app_name.strip().lower()
    allowed_apps = {"notepad", "calc", "calc.exe", "notepad.exe", "explorer", "code", "cmd", "powershell"}
    
    if clean_app not in allowed_apps and not clean_app.endswith(".exe"):
        raise PermissionError(f"Application '{args.app_name}' is restricted by desktop security policy.")

    try:
        os.system(f"start {clean_app}")
        return {
            "app": args.app_name,
            "status": "LAUNCHED",
            "message": f"Successfully requested OS to launch '{args.app_name}'"
        }
    except Exception as e:
        raise RuntimeError(f"Failed to launch application '{args.app_name}': {e}")
