import asyncio
import logging
import time
import uuid
from typing import Any, Callable, Coroutine

from jarvis.config.settings import settings

logger = logging.getLogger("jarvis.security.confirmation_bridge")


class ConfirmationBridge:
    def __init__(self):
        self._pending_requests: dict[str, asyncio.Future[bool]] = {}
        self._request_metadata: dict[str, dict[str, Any]] = {}
        self._broadcasters: list[Callable[[dict[str, Any]], Coroutine[Any, Any, None]]] = []

    def register_broadcaster(
        self, callback: Callable[[dict[str, Any]], Coroutine[Any, Any, None]]
    ) -> None:
        self._broadcasters.append(callback)

    def unregister_broadcaster(
        self, callback: Callable[[dict[str, Any]], Coroutine[Any, Any, None]]
    ) -> None:
        if callback in self._broadcasters:
            self._broadcasters.remove(callback)

    async def _broadcast(self, message: dict[str, Any]) -> None:
        for broadcaster in list(self._broadcasters):
            try:
                await broadcaster(message)
            except Exception as e:
                logger.warning(f"Error broadcasting confirmation request: {e}")

    async def request_confirmation(
        self,
        tool_name: str,
        args: dict[str, Any],
        risk_level: str,
        timeout_seconds: int | None = None
    ) -> bool:
        timeout = timeout_seconds or settings.CONFIRMATION_TIMEOUT_SECONDS
        confirmation_id = str(uuid.uuid4())
        loop = asyncio.get_running_loop()
        future: asyncio.Future[bool] = loop.create_future()

        self._pending_requests[confirmation_id] = future
        self._request_metadata[confirmation_id] = {
            "confirmation_id": confirmation_id,
            "tool": tool_name,
            "args": args,
            "risk_level": risk_level,
            "requested_at": time.time(),
            "timeout_seconds": timeout
        }

        # Broadcast confirmation request to all connected UI clients
        request_frame = {
            "type": "confirmation_request",
            "confirmationId": confirmation_id,
            "toolName": tool_name,
            "riskLevel": risk_level,
            "arguments": args,
            "timeoutSeconds": timeout,
            "timestamp": time.time()
        }
        await self._broadcast(request_frame)

        logger.info(
            f"[CONFIRMATION] Requesting approval for {tool_name} (Risk: {risk_level}, ID: {confirmation_id})"
        )

        try:
            approved = await asyncio.wait_for(future, timeout=float(timeout))
            logger.info(
                f"[CONFIRMATION] Request {confirmation_id} resolved: {'APPROVED' if approved else 'DENIED'}"
            )
            return approved
        except asyncio.TimeoutError:
            logger.warning(
                f"[CONFIRMATION] Request {confirmation_id} timed out after {timeout}s -> AUTO-DENIED"
            )
            return False
        finally:
            self._pending_requests.pop(confirmation_id, None)
            self._request_metadata.pop(confirmation_id, None)

    def resolve_confirmation(self, confirmation_id: str, approved: bool, reason: str = "") -> bool:
        future = self._pending_requests.get(confirmation_id)
        if future and not future.done():
            future.set_result(approved)
            return True
        return False

    def list_pending(self) -> list[dict[str, Any]]:
        return list(self._request_metadata.values())


confirmation_bridge = ConfirmationBridge()
