import time
from typing import Any


class PromptCache:
    def __init__(self, ttl_seconds: float = 300.0):
        self.ttl = ttl_seconds
        self._cache: dict[str, tuple[str, float]] = {}

    def _normalize(self, text: str) -> str:
        return " ".join(text.strip().lower().split())

    def get(self, text: str) -> str | None:
        key = self._normalize(text)
        if key in self._cache:
            val, timestamp = self._cache[key]
            if (time.time() - timestamp) < self.ttl:
                return val
            else:
                del self._cache[key]
        return None

    def set(self, text: str, response: str) -> None:
        key = self._normalize(text)
        self._cache[key] = (response, time.time())

    def clear(self) -> None:
        self._cache.clear()


prompt_cache = PromptCache()
