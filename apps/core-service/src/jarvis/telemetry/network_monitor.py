import asyncio
import time
import httpx
from jarvis.domain.entities.models import NetworkStatus


class NetworkMonitor:
    def __init__(self, check_urls: list[str] | None = None):
        self.check_urls = check_urls or [
            "https://1.1.1.1",
            "https://8.8.8.8",
            "https://www.google.com"
        ]
        self._cached_status = NetworkStatus(is_online=True)
        self._last_check_time = 0.0

    async def check_connectivity(self, force: bool = False) -> NetworkStatus:
        now = time.time()
        # Cache results for 5 seconds to avoid network spam
        if not force and (now - self._last_check_time) < 5.0:
            return self._cached_status

        for url in self.check_urls:
            try:
                start = time.perf_counter()
                async with httpx.AsyncClient(timeout=2.0) as client:
                    res = await client.head(url)
                    latency = round((time.perf_counter() - start) * 1000, 1)
                    if res.status_code < 500:
                        self._cached_status = NetworkStatus(
                            is_online=True,
                            latency_ms=latency,
                            checked_at=now
                        )
                        self._last_check_time = now
                        return self._cached_status
            except Exception:
                continue

        self._cached_status = NetworkStatus(
            is_online=False,
            latency_ms=None,
            checked_at=now
        )
        self._last_check_time = now
        return self._cached_status


network_monitor = NetworkMonitor()
