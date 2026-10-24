import asyncio
import base64
import io
import os
import platform
import subprocess
from typing import Any, Callable, Dict, List, Optional
import httpx
from PIL import ImageGrab

from backend.telemetry import get_system_telemetry

DESTRUCTIVE_PATTERNS = [
    "del ", "rmdir", "remove-item", "format", "shutdown", "drop ",
    "truncate", "reg delete", "diskpart", "erase", "taskkill", "kill"
]

class ConfirmationBridge:
    def __init__(self):
        self._pending: Dict[str, asyncio.Future] = {}
        self._broadcasters: List[Callable] = []

    def register_broadcaster(self, cb: Callable):
        if cb not in self._broadcasters:
            self._broadcasters.append(cb)

    def unregister_broadcaster(self, cb: Callable):
        if cb in self._broadcasters:
            self._broadcasters.remove(cb)

    async def request_confirmation(self, tool_name: str, args: dict, risk_level: str = "HIGH", timeout_sec: int = 30) -> bool:
        import uuid
        confirmation_id = str(uuid.uuid4())
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self._pending[confirmation_id] = future

        payload = {
            "type": "confirmation_request",
            "confirmationId": confirmation_id,
            "toolName": tool_name,
            "riskLevel": risk_level,
            "arguments": args,
            "timeoutSeconds": timeout_sec,
            "timestamp": int(asyncio.get_event_loop().time())
        }

        # Broadcast to connected UI clients
        for cb in list(self._broadcasters):
            try:
                res = cb(payload)
                if asyncio.iscoroutine(res):
                    await res
            except Exception:
                pass

        try:
            approved = await asyncio.wait_for(future, timeout=float(timeout_sec))
            return bool(approved)
        except asyncio.TimeoutError:
            return False
        finally:
            self._pending.pop(confirmation_id, None)

    def resolve(self, confirmation_id: str, approved: bool, reason: str = "") -> bool:
        future = self._pending.get(confirmation_id)
        if future and not future.done():
            future.set_result(approved)
            return True
        return False

confirmation_bridge = ConfirmationBridge()

# Common application aliases on Windows
APP_COMMANDS = {
    "chrome": "start chrome",
    "google chrome": "start chrome",
    "edge": "start msedge",
    "firefox": "start firefox",
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "code": "code",
    "vs code": "code",
    "vscode": "code",
    "terminal": "start wt",
    "cmd": "start cmd",
    "powershell": "start powershell",
    "explorer": "explorer.exe",
    "files": "explorer.exe",
    "settings": "start ms-settings:",
    "spotify": "start spotify:",
    "discord": "start discord:"
}

async def tool_system_telemetry() -> Dict[str, Any]:
    """Retrieve real-time hardware telemetry: CPU, RAM, disk, battery, and network rates."""
    return get_system_telemetry()

async def tool_launch_application(name: str) -> Dict[str, Any]:
    """Launch an installed desktop application by name (e.g., 'notepad', 'chrome', 'calculator', 'code')."""
    lower = name.lower().strip()
    cmd = APP_COMMANDS.get(lower)

    if not cmd:
        # Fallback to direct Windows start or shell search
        if platform.system() == "Windows":
            cmd = f'start "" "{name}"'
        else:
            cmd = name

    try:
        subprocess.Popen(cmd, shell=True)
        return {"success": True, "message": f"Successfully launched {name}"}
    except Exception as e:
        return {"success": False, "error": f"Failed to launch {name}: {str(e)}"}

async def tool_run_shell_command(command: str) -> Dict[str, Any]:
    """Execute a shell or PowerShell command on the host. Potentially destructive commands require explicit user approval."""
    # Check if destructive
    is_destructive = any(pattern in command.lower() for pattern in DESTRUCTIVE_PATTERNS)
    risk_level = "CRITICAL" if is_destructive else "HIGH"

    approved = await confirmation_bridge.request_confirmation(
        tool_name="run_shell_command",
        args={"command": command},
        risk_level=risk_level,
        timeout_sec=30
    )

    if not approved:
        return {"success": False, "error": "Operation aborted: user denied permission or confirmation timed out."}

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
        out_text = stdout.decode("utf-8", errors="replace").strip()
        err_text = stderr.decode("utf-8", errors="replace").strip()

        return {
            "success": proc.returncode == 0,
            "returncode": proc.returncode,
            "output": out_text or err_text or "[Command executed with no output]"
        }
    except asyncio.TimeoutError:
        return {"success": False, "error": "Command execution timed out after 30 seconds."}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def tool_take_screenshot() -> Dict[str, Any]:
    """Capture a screenshot of the primary display. Returns a base64 encoded image."""
    try:
        img = ImageGrab.grab()
        # Scale to max 1280 wide to keep payload efficient
        if img.width > 1280:
            scale = 1280 / img.width
            img = img.resize((1280, int(img.height * scale)))
        
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=80)
        b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return {
            "success": True,
            "mime_type": "image/jpeg",
            "image_base64": b64,
            "width": img.width,
            "height": img.height
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to capture screenshot: {str(e)}"}

async def tool_get_active_window() -> Dict[str, Any]:
    """Retrieve the title and process of the currently active desktop window."""
    if platform.system() == "Windows":
        try:
            import win32gui
            import win32process
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd)
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            return {"success": True, "title": title or "Desktop", "pid": pid}
        except Exception:
            pass
    return {"success": True, "title": "J.A.R.V.I.S Desktop", "pid": os.getpid()}

async def tool_web_search(query: str) -> Dict[str, Any]:
    """Search the web for up-to-date facts, news, documentation, or technical information."""
    try:
        url = "https://html.duckduckgo.com/html/"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.post(url, data={"q": query}, headers=headers)
            if resp.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, "html.parser")
                results = []
                for result in soup.select(".result__body")[:5]:
                    title_elem = result.select_one(".result__title")
                    snippet_elem = result.select_one(".result__snippet")
                    if title_elem and snippet_elem:
                        results.append({
                            "title": title_elem.get_text(strip=True),
                            "snippet": snippet_elem.get_text(strip=True)
                        })
                if results:
                    return {"success": True, "query": query, "results": results}
    except Exception:
        pass
    
    # Simple fallback using wikipedia API
    try:
        wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{query.replace(' ', '_')}"
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(wiki_url)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "success": True,
                    "query": query,
                    "results": [{"title": data.get("title"), "snippet": data.get("extract")}]
                }
    except Exception as e:
        return {"success": False, "error": f"Search failed: {str(e)}"}

    return {"success": True, "query": query, "results": [{"title": query, "snippet": "No direct search matches found."}]}

# Unified Tool Manifest for Gemini Function Calling
TOOL_DEFINITIONS = [
    {
        "name": "system_telemetry",
        "description": "Fetch real-time CPU, RAM, disk, battery, and network telemetry for the PC.",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        },
        "handler": tool_system_telemetry
    },
    {
        "name": "launch_application",
        "description": "Open or launch a desktop application (e.g. 'notepad', 'chrome', 'calculator', 'vscode').",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "name": {"type": "STRING", "description": "The name of the application to launch."}
            },
            "required": ["name"]
        },
        "handler": tool_launch_application
    },
    {
        "name": "run_shell_command",
        "description": "Execute a safe shell/PowerShell command to query system state or run scripts. Destructive commands trigger a confirmation gate.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "command": {"type": "STRING", "description": "The exact shell command line string to execute."}
            },
            "required": ["command"]
        },
        "handler": tool_run_shell_command
    },
    {
        "name": "take_screenshot",
        "description": "Capture the user's primary display screen to see what is currently open or examine visual errors.",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        },
        "handler": tool_take_screenshot
    },
    {
        "name": "get_active_window",
        "description": "Get the window title and process ID of the application the user is currently working on.",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        },
        "handler": tool_get_active_window
    },
    {
        "name": "web_search",
        "description": "Perform an external web search to retrieve current real-world information, documentation, or news.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Search query terms."}
            },
            "required": ["query"]
        },
        "handler": tool_web_search
    }
]

TOOL_HANDLERS: Dict[str, Callable] = {
    t["name"]: t["handler"] for t in TOOL_DEFINITIONS
}
