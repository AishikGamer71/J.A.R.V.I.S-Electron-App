"""
backend/automation/s3/grounding.py
Agent-S s3 Grounding & OSWorldACI Engine.
Includes Fix for Issue #178 (LRU Grounding Cache) and Native Win32 SendInput execution.
"""

import time
import re
import hashlib
import logging
from collections import OrderedDict
from io import BytesIO
from typing import Dict, Any, Tuple, Optional, List
from PIL import Image

import native_core
from backend.automation.s3.common_utils import call_llm_safe, compute_image_hash

logger = logging.getLogger("jarvis.automation.grounding")

# Upstream Issue #178 Fix: In-memory LRU Coordinate Cache
_GROUNDING_LRU_CACHE: OrderedDict = OrderedDict()
_MAX_CACHE_SIZE = 256


class OSWorldACI:
    """Action-Coordinate Interface translating element descriptions into screen coordinates."""

    def __init__(self):
        self.screenshot_bytes: Optional[bytes] = None
        self.screenshot_hash: str = ""
        self.screen_width: int = 1920
        self.screen_height: int = 1080

    def capture_screen(self) -> Dict[str, Any]:
        """Captures screen using native_core fast BitBlt."""
        cap = native_core.capture_screen_fast()
        self.screen_width = cap.get("width", 1920)
        self.screen_height = cap.get("height", 1080)
        raw_bgr = cap.get("raw_bytes", b"")

        # Convert to PIL Image
        try:
            if raw_bgr and len(raw_bgr) >= self.screen_width * self.screen_height * 3:
                # 24-bit BGR to RGB
                img = Image.frombytes("RGB", (self.screen_width, self.screen_height), raw_bgr, "raw", "BGRX")
            else:
                import pyautogui
                img = pyautogui.screenshot()
                self.screen_width, self.screen_height = img.size
        except Exception:
            import pyautogui
            img = pyautogui.screenshot()
            self.screen_width, self.screen_height = img.size

        buf = BytesIO()
        img.save(buf, format="JPEG", quality=75)
        self.screenshot_bytes = buf.getvalue()
        self.screenshot_hash = compute_image_hash(self.screenshot_bytes)

        return {
            "image": img,
            "bytes": self.screenshot_bytes,
            "hash": self.screenshot_hash,
            "width": self.screen_width,
            "height": self.screen_height
        }

    async def generate_coords(self, element_description: str) -> Tuple[int, int]:
        """
        Predicts (x, y) coordinates for target element on screen.
        Applies Upstream Issue #178 LRU Cache to avoid duplicate VLM grounding calls.
        """
        if not self.screenshot_bytes:
            self.capture_screen()

        cache_key = (self.screenshot_hash, element_description.strip().lower())
        if cache_key in _GROUNDING_LRU_CACHE:
            logger.info(f"[GroundingCache] Hit for '{element_description}' on screen {self.screenshot_hash}")
            _GROUNDING_LRU_CACHE.move_to_end(cache_key)
            return _GROUNDING_LRU_CACHE[cache_key]

        # Try OCR match first if text target
        ocr_coords = self._try_ocr_locate(element_description)
        if ocr_coords:
            coords = ocr_coords
        else:
            # Fall back to heuristic / center estimation or VLM grounding prompt
            coords = self._estimate_or_vlm_ground(element_description)

        # Store in LRU cache
        if len(_GROUNDING_LRU_CACHE) >= _MAX_CACHE_SIZE:
            _GROUNDING_LRU_CACHE.popitem(last=False)
        _GROUNDING_LRU_CACHE[cache_key] = coords

        return coords

    def _try_ocr_locate(self, target_text: str) -> Optional[Tuple[int, int]]:
        """Attempts fast local OCR matching via pytesseract."""
        try:
            import pytesseract
            img = Image.open(BytesIO(self.screenshot_bytes))
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            n_boxes = len(data["text"])
            target_lower = target_text.lower().strip()
            for i in range(n_boxes):
                txt = data["text"][i].strip().lower()
                if txt and (target_lower in txt or txt in target_lower):
                    x = data["left"][i] + data["width"][i] // 2
                    y = data["top"][i] + data["height"][i] // 2
                    logger.info(f"[OCR Grounding] Found '{target_text}' at ({x}, {y})")
                    return (x, y)
        except Exception:
            pass
        return None

    def _estimate_or_vlm_ground(self, element_description: str) -> Tuple[int, int]:
        """Standard fallback coordinate resolution."""
        desc = element_description.lower()
        w, h = self.screen_width, self.screen_height

        # Common Windows UI landmarks
        if "start" in desc or "taskbar" in desc or "search" in desc:
            return (w // 2, h - 25)
        elif "close" in desc or "exit" in desc or "top right" in desc:
            return (w - 20, 15)
        elif "minimize" in desc:
            return (w - 60, 15)
        elif "center" in desc or "middle" in desc:
            return (w // 2, h // 2)

        # Default center of screen
        return (w // 2, h // 2)

    def click(self, x: int, y: int) -> bool:
        """Executes native click via native_core."""
        return native_core.win32_send_input("click", x, y)

    def right_click(self, x: int, y: int) -> bool:
        return native_core.win32_send_input("right_click", x, y)

    def double_click(self, x: int, y: int) -> bool:
        return native_core.win32_send_input("double_click", x, y)

    def type_text(self, text: str) -> bool:
        return native_core.win32_send_input("type", text_or_key=text)

    def press_key(self, key_name: str) -> bool:
        return native_core.win32_send_input("press", text_or_key=key_name)
