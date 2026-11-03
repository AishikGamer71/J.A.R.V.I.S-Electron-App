"""
backend/automation/s3/common_utils.py
Agent-S s3 common utilities, image helpers, and safe LLM invocation.
"""

import time
import hashlib
import logging
from io import BytesIO
from typing import Optional, Dict, Any, Tuple
from PIL import Image
from backend.engine.inference_router import inference_router

logger = logging.getLogger("jarvis.automation.utils")


async def call_llm_safe(prompt: str, system_prompt: str = "", model: Optional[str] = None,
                        temperature: float = 0.0, max_retries: int = 3) -> str:
    """
    Invokes LLM with retry loop and error handling.
    """
    attempt = 0
    while attempt < max_retries:
        try:
            res = await inference_router.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                model=model,
                temperature=temperature
            )
            content = res.get("content", "")
            if content:
                return content
        except Exception as e:
            attempt += 1
            logger.warning(f"[call_llm_safe] Attempt {attempt} failed: {e}")
            if attempt >= max_retries:
                logger.error(f"[call_llm_safe] Reached max retries ({max_retries}).")
                break
            time.sleep(1.0)

    return ""


def compute_image_hash(img_bytes: bytes) -> str:
    """Computes SHA256 hash of screenshot for caching coordinate lookups."""
    return hashlib.sha256(img_bytes).hexdigest()[:16]
