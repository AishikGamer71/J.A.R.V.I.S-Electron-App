from abc import ABC, abstractmethod
from jarvis.domain.entities.models import ChatMessage, ChatSession


class MemoryPort(ABC):
    @abstractmethod
    async def create_session(self, title: str = "New Session") -> ChatSession:
        pass

    @abstractmethod
    async def get_session(self, session_id: str) -> ChatSession | None:
        pass

    @abstractmethod
    async def list_sessions(self, limit: int = 50) -> list[ChatSession]:
        pass

    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        pass

    @abstractmethod
    async def save_message(self, message: ChatMessage) -> None:
        pass

    @abstractmethod
    async def get_messages(self, session_id: str, limit: int = 100) -> list[ChatMessage]:
        pass

    @abstractmethod
    async def search_messages(self, query: str, limit: int = 20) -> list[ChatMessage]:
        """Full-text search (FTS5) across all stored messages."""
        pass
