import json
import logging
from typing import AsyncGenerator
import httpx
from jarvis.config.settings import settings
from jarvis.domain.entities.models import ChatMessage, MessageRole
from jarvis.providers.base import ModelProvider

logger = logging.getLogger("jarvis.providers.ollama")


class OllamaProvider(ModelProvider):
    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(f"{self.base_url}/api/version")
                return res.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            logger.debug(f"Failed to list Ollama models: {e}")
        return []

    def _clean_model_name(self, model: str) -> str:
        if model.startswith("ollama/"):
            return model.split("ollama/", 1)[1]
        return model

    async def generate(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None
    ) -> ChatMessage:
        raw_model = self._clean_model_name(model)
        payload = {
            "model": raw_model,
            "messages": [{"role": m.role.value, "content": m.content} for m in messages],
            "stream": False,
            "options": {
                "temperature": temperature,
                **({"num_predict": max_tokens} if max_tokens else {})
            }
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(f"{self.base_url}/api/chat", json=payload)
            res.raise_for_status()
            data = res.json()
            reply_text = data.get("message", {}).get("content", "")
            return ChatMessage(
                session_id=messages[-1].session_id if messages else "",
                role=MessageRole.ASSISTANT,
                content=reply_text,
                model=f"ollama/{raw_model}",
                tokens={
                    "prompt": data.get("prompt_eval_count", 0),
                    "completion": data.get("eval_count", 0),
                    "total": data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
                }
            )

    async def stream(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None
    ) -> AsyncGenerator[str, None]:
        raw_model = self._clean_model_name(model)
        payload = {
            "model": raw_model,
            "messages": [{"role": m.role.value, "content": m.content} for m in messages],
            "stream": True,
            "options": {
                "temperature": temperature,
                **({"num_predict": max_tokens} if max_tokens else {})
            }
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue
