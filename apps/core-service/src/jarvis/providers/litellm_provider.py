import logging
from typing import AsyncGenerator
import litellm
from jarvis.config.settings import settings
from jarvis.domain.entities.models import ChatMessage, MessageRole
from jarvis.providers.base import ModelProvider

logger = logging.getLogger("jarvis.providers.litellm")

# Silence noisy litellm logs
litellm.suppress_debug_info = True


class LiteLLMProvider(ModelProvider):
    def __init__(self):
        # Configure API Keys from settings if present
        if settings.GEMINI_API_KEY:
            litellm.gemini_key = settings.GEMINI_API_KEY
        if settings.OPENAI_API_KEY:
            litellm.openai_key = settings.OPENAI_API_KEY
        if settings.ANTHROPIC_API_KEY:
            litellm.anthropic_key = settings.ANTHROPIC_API_KEY
        if settings.GROQ_API_KEY:
            litellm.groq_key = settings.GROQ_API_KEY

    async def health_check(self) -> bool:
        # Check if at least one API key is provided
        return bool(
            settings.GEMINI_API_KEY or
            settings.OPENAI_API_KEY or
            settings.ANTHROPIC_API_KEY or
            settings.GROQ_API_KEY
        )

    async def list_models(self) -> list[str]:
        return [
            "gemini/gemini-1.5-flash",
            "gemini/gemini-1.5-pro",
            "gemini/gemini-2.0-flash",
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "anthropic/claude-3-5-sonnet-latest",
            "groq/llama-3.3-70b-versatile"
        ]

    async def generate(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None
    ) -> ChatMessage:
        formatted_messages = [
            {"role": m.role.value, "content": m.content}
            for m in messages
        ]

        kwargs: dict = {
            "model": model,
            "messages": formatted_messages,
            "temperature": temperature,
        }
        if max_tokens:
            kwargs["max_tokens"] = max_tokens

        response = await litellm.acompletion(**kwargs)
        reply_content = response.choices[0].message.content or ""
        usage = getattr(response, "usage", None)

        tokens = None
        if usage:
            tokens = {
                "prompt": getattr(usage, "prompt_tokens", 0),
                "completion": getattr(usage, "completion_tokens", 0),
                "total": getattr(usage, "total_tokens", 0),
            }

        return ChatMessage(
            session_id=messages[-1].session_id if messages else "",
            role=MessageRole.ASSISTANT,
            content=reply_content,
            model=model,
            tokens=tokens
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None
    ) -> AsyncGenerator[str, None]:
        formatted_messages = [
            {"role": m.role.value, "content": m.content}
            for m in messages
        ]

        kwargs: dict = {
            "model": model,
            "messages": formatted_messages,
            "temperature": temperature,
            "stream": True,
        }
        if max_tokens:
            kwargs["max_tokens"] = max_tokens

        response = await litellm.acompletion(**kwargs)
        async for chunk in response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
