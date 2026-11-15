"""
backend/core/context_compressor.py
==================================
ContextCompressor: Context window compaction and token budget management for J.A.R.V.I.S.
Maintains system prompt integrity (head), recent conversational state (tail),
prunes/summarizes intermediate turns, cleans orphaned tool pairs, and soft-compacts
messages in SessionDB.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("jarvis.context_compressor")

SUMMARY_PREFIX = (
    "[CONTEXT COMPACTION — REFERENCE ONLY] Earlier turns were compacted "
    "into the summary below. Treat this as background reference:\n\n"
)

SUMMARY_END_MARKER = (
    "\n--- END OF CONTEXT SUMMARY ---"
)


class ContextCompressor:
    """Manages conversational context budget and semantic compaction."""

    def __init__(
        self,
        max_tokens: int = 8192,
        threshold_ratio: float = 0.50,
        state_db: Optional[Any] = None,
    ):
        self.max_tokens = max_tokens
        self.threshold_ratio = threshold_ratio
        self.state_db = state_db
        self._consecutive_small_savings = 0

    def estimate_tokens(self, content_or_messages: Union[str, List[Dict[str, Any]]]) -> int:
        """
        Estimates token count for either a text string or a list of messages.
        Uses standard ~4 chars per token heuristic + message envelope overhead.
        """
        if isinstance(content_or_messages, str):
            if not content_or_messages:
                return 0
            return max(1, len(content_or_messages) // 4)

        if isinstance(content_or_messages, list):
            total = 0
            for msg in content_or_messages:
                if isinstance(msg, dict):
                    toks = msg.get("tokens")
                    if toks is not None and isinstance(toks, int) and toks > 0:
                        total += toks
                    else:
                        c = msg.get("content") or ""
                        total += self.estimate_tokens(str(c)) + 4
                        if msg.get("tool_calls"):
                            total += self.estimate_tokens(json.dumps(msg["tool_calls"]))
            return total

        return 0

    def should_compress(
        self,
        messages: List[Dict[str, Any]],
        current_tokens: Optional[int] = None,
    ) -> bool:
        """
        Determines whether the conversation exceeds threshold_ratio of max_tokens.
        """
        tokens = current_tokens if current_tokens is not None else self.estimate_tokens(messages)
        threshold = int(self.max_tokens * self.threshold_ratio)
        if tokens >= threshold and self._consecutive_small_savings < 3:
            return True
        return False

    def compress(
        self,
        messages: List[Dict[str, Any]],
        current_tokens: Optional[int] = None,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Compacts the messages list so total tokens do not exceed max_tokens.
        Preserves leading system messages and recent turns.
        """
        if not messages:
            return []

        tokens = current_tokens if current_tokens is not None else self.estimate_tokens(messages)
        if tokens <= self.max_tokens:
            return list(messages)

        # 1. Identify and protect leading system messages (Head)
        head: List[Dict[str, Any]] = []
        rest: List[Dict[str, Any]] = []
        for i, m in enumerate(messages):
            if m.get("role") == "system" and len(rest) == 0:
                head.append(m)
            else:
                rest.append(m)

        if not rest:
            return head

        # 2. Partition into Middle and Tail
        # Keep at least the latest user/assistant turn if possible
        tail_count = min(len(rest), max(1, 2))
        middle = rest[:-tail_count]
        tail = rest[-tail_count:]

        # 3. Create a concise summary of middle turns
        middle_ids = [m["id"] for m in middle if isinstance(m.get("id"), int)]
        summary_text_parts = []
        for m in middle:
            role = m.get("role", "unknown")
            content = str(m.get("content", ""))
            preview = content[:100].replace("\n", " ")
            summary_text_parts.append(f"{role}: {preview}")

        summary_body = "; ".join(summary_text_parts)
        if len(summary_body) > 300:
            summary_body = summary_body[:300] + "..."

        summary_content = f"{SUMMARY_PREFIX}{summary_body}{SUMMARY_END_MARKER}"
        summary_tokens = self.estimate_tokens(summary_content)

        summary_msg = {
            "role": "user",
            "content": summary_content,
            "tokens": summary_tokens,
            "_compressed_summary": True,
        }

        # 4. Clean orphaned tool calls in tail
        cleaned_tail = self._clean_orphaned_tools(tail)

        # 5. Assemble compacted messages
        if middle:
            compacted = head + [summary_msg] + cleaned_tail
        else:
            compacted = head + cleaned_tail

        # 6. If still exceeding budget, aggressively trim oldest non-system turns
        while self.estimate_tokens(compacted) > self.max_tokens and len(compacted) > len(head) + 1:
            # Remove earliest non-head turn
            compacted.pop(len(head))

        # 7. Soft-compact in database if available
        if self.state_db and session_id and middle_ids:
            try:
                self.state_db.soft_compact_messages(session_id, middle_ids)
            except Exception as e:
                logger.debug("Failed to soft-compact in state_db: %s", e)

        return compacted

    async def compress_async(
        self,
        messages: List[Dict[str, Any]],
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Asynchronous wrapper for compress."""
        return self.compress(messages, session_id=session_id)

    def _clean_orphaned_tools(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Removes dangling tool results whose matching tool_call_id is missing from assistant turns.
        Prunes all tool messages if no matching assistant tool_calls exist in the window.
        """
        if not messages:
            return []

        call_ids = set()
        for m in messages:
            if m.get("role") == "assistant" and m.get("tool_calls"):
                for tc in m["tool_calls"]:
                    if isinstance(tc, dict) and tc.get("id"):
                        call_ids.add(tc["id"])
                    elif hasattr(tc, "id") and getattr(tc, "id"):
                        call_ids.add(getattr(tc, "id"))

        cleaned = []
        for m in messages:
            if m.get("role") == "tool":
                tcid = m.get("tool_call_id")
                # Prune if tool_call_id is missing or has no antecedent assistant tool_call
                if not tcid or tcid not in call_ids:
                    continue
            cleaned.append(m)

        return cleaned
