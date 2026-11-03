from abc import ABC, abstractmethod
from typing import AsyncGenerator
from jarvis.domain.entities.models import ChatMessage
from jarvis.domain.ports.model_port import ModelPort


class ModelProvider(ModelPort, ABC):
    """Base abstract interface for all Model Providers."""
    
    @abstractmethod
    async def list_models(self) -> list[str]:
        """List available models from this provider."""
        pass
