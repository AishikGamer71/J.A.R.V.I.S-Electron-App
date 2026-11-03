"""
backend/core/context_compressor.py
Hermes-Assimilated Middle-Turn Context Compactor.
Summarizes older turns into structured Resolved/Pending task blocks while
preserving recent interactions verbatim.
"""

import logging
from typing import List, Dict, Any, Optional
from backend.engine.inference_router import inference_router

logger = logging.getLogger("jarvis.context")

COMPRESSION_PROMPT = """
You are the context compaction engine for J.A.R.V.I.S.
Summarize the following intermediate conversation turns into two concise categories:
1. Resolved Tasks & Decisions: What has been established, inspected, or executed.
2. Pending Directives: What remains to be completed or addressed.

Preserve all file paths, function names, error codes, and user instructions verbatim.
Keep output under 300 words.
"""

class ContextCompressor:
    """Summarizes middle conversation turns to keep LLM context tightly optimized."""

    def __init__(self, threshold: int = 14, keep_recent: int = 6):
        self.threshold = threshold
        self.keep_recent = keep_recent

    async def compress_if_needed(self, messages: List[Dict[str, Any]], model: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Compresses middle turns if total messages exceed threshold.
        """
        if len(messages) <= self.threshold:
            return messages

        # Preserve the initial system / anchor message if present
        start_idx = 1 if messages[0].get("role") == "system" else 0
        anchor_msgs = messages[:start_idx]

        # Preserve the last keep_recent messages
        recent_msgs = messages[-self.keep_recent:]

        # Middle slice to compress
        middle_msgs = messages[start_idx : -self.keep_recent]
        if not middle_msgs:
            return messages

        middle_text = ""
        for m in middle_msgs:
            role = m.get("role", "unknown").upper()
            content = m.get("content", "")
            middle_text += f"{role}: {content}\n---\n"

        try:
            res = await inference_router.generate(
                prompt=f"Please compress these intermediate turns:\n\n{middle_text}",
                system_prompt=COMPRESSION_PROMPT.strip(),
                model=model,
                temperature=0.2
            )
            summary_content = res.get("content", "")
            compressed_msg = {
                "role": "system",
                "content": f"[CONVERSATION COMPRESSION SUMMARY]\n{summary_content}"
            }
            logger.info(f"[ContextCompressor] Compacted {len(middle_msgs)} middle turns into 1 summary block.")
            return anchor_msgs + [compressed_msg] + recent_msgs

        except Exception as e:
            logger.warning(f"[ContextCompressor] Compression failed: {e}. Falling back to sliding window.")
            # Graceful fallback: sliding window
            return anchor_msgs + recent_msgs

context_compressor = ContextCompressor()
