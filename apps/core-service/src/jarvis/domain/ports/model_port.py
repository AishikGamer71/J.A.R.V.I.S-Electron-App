from abc import ABC, abstractmethod
from typing import AsyncGenerator
from jarvis.domain.entities.models import ChatMessage


class ModelPort(ABC):
    @abstractmethod
    async def generate(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None
    ) -> ChatMessage:
        """Generate a complete completion response."""
        pass

    @abstractmethod
    async def stream(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None
    ) -> AsyncGenerator[str, None]:
        """Stream response delta tokens."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider backend is reachable and ready."""
        pass
