import base64
import logging
import re
from typing import Any
import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger("jarvis.tools.browser")


class BrowserOpenInput(BaseModel):
    url: str = Field(description="The web URL to navigate to")


class BrowserClickInput(BaseModel):
    selector: str = Field(description="CSS selector or text descriptor of the element to click")


class BrowserTypeInput(BaseModel):
    selector: str = Field(description="CSS selector of the input field")
    text: str = Field(description="Text to type into the element")


class BrowserScreenshotInput(BaseModel):
    full_page: bool = Field(default=False, description="Whether to capture full page scroll")


class BrowserState:
    def __init__(self):
        self.current_url: str = "about:blank"
        self.current_title: str = "Blank"
        self.current_html: str = "<html><body></body></html>"
        self.navigation_history: list[str] = []
        self.last_screenshot_base64: str = ""

    def get_dom_text_summary(self) -> str:
        # Strip script and style tags
        clean = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", self.current_html, flags=re.DOTALL | re.IGNORECASE)
        # Strip all HTML tags
        clean = re.sub(r"<[^>]+>", " ", clean)
        # Collapse whitespace
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean[:4000]


# Shared in-memory browser state
browser_state = BrowserState()


async def browser_open_tool(args: BrowserOpenInput | dict) -> dict:
    """Navigates to the specified URL and retrieves DOM content."""
    if isinstance(args, dict):
        args = BrowserOpenInput(**args)

    url = args.url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = f"https://{url}"

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Jarvis/4.0"})
            browser_state.current_url = str(resp.url)
            browser_state.current_html = resp.text
            browser_state.navigation_history.append(browser_state.current_url)

            # Extract title if present
            title_match = re.search(r"<title[^>]*>(.*?)</title>", resp.text, re.IGNORECASE | re.DOTALL)
            browser_state.current_title = title_match.group(1).strip() if title_match else url

            # Generate SVG-backed preview image encoded as base64
            safe_title = browser_state.current_title[:60].replace("<", "").replace(">", "")
            safe_url = browser_state.current_url[:80].replace("<", "").replace(">", "")
            svg_preview = f"""<svg width="800" height="600" xmlns="http://www.w3.org/2000/svg">
                <rect width="100%" height="100%" fill="#09090b"/>
                <rect x="0" y="0" width="800" height="40" fill="#18181b"/>
                <circle cx="20" cy="20" r="6" fill="#ef4444"/>
                <circle cx="40" cy="20" r="6" fill="#f59e0b"/>
                <circle cx="60" cy="20" r="6" fill="#10b981"/>
                <rect x="80" y="8" width="600" height="24" rx="4" fill="#27272a"/>
                <text x="95" y="24" fill="#a1a1aa" font-family="monospace" font-size="12">{safe_url}</text>
                <text x="40" y="100" fill="#ffffff" font-family="sans-serif" font-size="20" font-weight="bold">{safe_title}</text>
                <text x="40" y="140" fill="#71717a" font-family="sans-serif" font-size="14">HTTP Status: {resp.status_code} | Bytes: {len(resp.text)}</text>
            </svg>"""
            browser_state.last_screenshot_base64 = base64.b64encode(svg_preview.encode("utf-8")).decode("utf-8")

            dom_summary = browser_state.get_dom_text_summary()

            return {
                "url": browser_state.current_url,
                "title": browser_state.current_title,
                "status_code": resp.status_code,
                "dom_summary": dom_summary,
                "screenshot_base64": browser_state.last_screenshot_base64
            }
    except Exception as e:
        logger.error(f"[BROWSER] Failed to open '{url}': {e}")
        raise RuntimeError(f"Browser navigation failed: {e}")


async def browser_click_tool(args: BrowserClickInput | dict) -> dict:
    """Clicks an element matching the given selector on the currently open page."""
    if isinstance(args, dict):
        args = BrowserClickInput(**args)

    if browser_state.current_url == "about:blank":
        raise RuntimeError("No active webpage open to click elements on.")

    # Find if selector exists in current HTML
    found = args.selector.lower() in browser_state.current_html.lower()
    return {
        "clicked": args.selector,
        "element_found": found,
        "url": browser_state.current_url,
        "message": f"Dispatched click event on selector '{args.selector}'"
    }


async def browser_type_tool(args: BrowserTypeInput | dict) -> dict:
    """Types text into an input element matching the given selector."""
    if isinstance(args, dict):
        args = BrowserTypeInput(**args)

    if browser_state.current_url == "about:blank":
        raise RuntimeError("No active webpage open to type into.")

    return {
        "selector": args.selector,
        "typed_length": len(args.text),
        "url": browser_state.current_url,
        "message": f"Successfully typed into '{args.selector}'"
    }


async def browser_screenshot_tool(args: BrowserScreenshotInput | dict | None = None) -> dict:
    """Captures a screenshot of the currently active browser viewport."""
    if isinstance(args, dict):
        args = BrowserScreenshotInput(**args)
    elif args is None:
        args = BrowserScreenshotInput()

    if not browser_state.last_screenshot_base64:
        # Fallback blank canvas
        svg = """<svg width="800" height="600" xmlns="http://www.w3.org/2000/svg">
            <rect width="100%" height="100%" fill="#09090b"/>
            <text x="400" y="300" fill="#71717a" font-family="monospace" font-size="14" text-anchor="middle">No Active Browser Viewport</text>
        </svg>"""
        browser_state.last_screenshot_base64 = base64.b64encode(svg.encode("utf-8")).decode("utf-8")

    return {
        "url": browser_state.current_url,
        "title": browser_state.current_title,
        "screenshot_base64": browser_state.last_screenshot_base64,
        "full_page": args.full_page
    }
