"""
backend/engine/inference_router.py
OpenJarvis-Assimilated Multi-Provider Inference Router with Hardware VRAM Detection.
Intelligently routes between Gemini, OpenAI, and Local Ollama with automatic failover.
"""

import os
import time
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, AsyncGenerator
import aiohttp
from backend.config import settings
from backend.security.agent_shield import AgentShield

logger = logging.getLogger("jarvis.engine")


def detect_hardware_tier() -> Dict[str, Any]:
    """Detects available GPU/VRAM and system capacity."""
    tier = "low"
    vram_mb = 0
    gpu_name = "Integrated / CPU"

    try:
        import torch
        if torch.cuda.is_available():
            vram_mb = int(torch.cuda.get_device_properties(0).total_memory / (1024 * 1024))
            gpu_name = torch.cuda.get_device_name(0)
            if vram_mb >= 16000:
                tier = "high"
            elif vram_mb >= 8000:
                tier = "mid"
            else:
                tier = "low"
    except Exception:
        pass

    return {
        "tier": tier,
        "vram_mb": vram_mb,
        "gpu_name": gpu_name,
    }


class BaseEngine(ABC):
    """Abstract Base Class for LLM Inference Engines."""

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str = "", model: Optional[str] = None,
                       temperature: float = 0.7, tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def stream(self, prompt: str, system_prompt: str = "", model: Optional[str] = None,
                     temperature: float = 0.7) -> AsyncGenerator[str, None]:
        pass

    @abstractmethod
    async def health(self) -> bool:
        pass


class GeminiEngine(BaseEngine):
    """Google Gemini Engine using official google-genai SDK or direct REST fallback."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")

    async def health(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    async def generate(self, prompt: str, system_prompt: str = "", model: Optional[str] = None,
                       temperature: float = 0.7, tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        target_model = model or settings.GEMINI_MODEL
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured")

        # Try google-genai SDK first
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=self.api_key)
            config = types.GenerateContentConfig(
                temperature=temperature,
                system_instruction=system_prompt if system_prompt else None
            )
            response = client.models.generate_content(
                model=target_model,
                contents=prompt,
                config=config
            )
            text = response.text or ""
            return {"content": text, "model": target_model, "provider": "gemini", "tool_calls": None}
        except Exception as e:
            logger.debug(f"[Gemini SDK] falling back to REST: {e}")

        # REST API fallback
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={self.api_key}"
        payload: Dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature}
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=30) as resp:
                if resp.status != 200:
                    err_txt = await resp.text()
                    raise RuntimeError(f"Gemini API returned status {resp.status}: {err_txt}")
                data = await resp.json()
                try:
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                except (KeyError, IndexError):
                    text = ""
                return {"content": text, "model": target_model, "provider": "gemini", "tool_calls": None}

    async def stream(self, prompt: str, system_prompt: str = "", model: Optional[str] = None,
                     temperature: float = 0.7) -> AsyncGenerator[str, None]:
        res = await self.generate(prompt, system_prompt, model, temperature)
        yield res.get("content", "")


class OpenAIEngine(BaseEngine):
    """OpenAI / OpenRouter Engine."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = base_url

    async def health(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    async def generate(self, prompt: str, system_prompt: str = "", model: Optional[str] = None,
                       temperature: float = 0.7, tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        target_model = model or settings.OPENAI_MODEL
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await client.chat.completions.create(
            model=target_model,
            messages=messages,
            temperature=temperature
        )
        choice = response.choices[0]
        text = choice.message.content or ""
        return {"content": text, "model": target_model, "provider": "openai", "tool_calls": None}

    async def stream(self, prompt: str, system_prompt: str = "", model: Optional[str] = None,
                     temperature: float = 0.7) -> AsyncGenerator[str, None]:
        target_model = model or settings.OPENAI_MODEL
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        stream = await client.chat.completions.stream(
            model=target_model,
            messages=messages,
            temperature=temperature
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                yield delta


class OllamaEngine(BaseEngine):
    """Local Ollama Engine for privacy-first on-device execution."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")

    async def health(self) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/version", timeout=1.5) as resp:
                    return resp.status == 200
        except Exception:
            return False

    async def generate(self, prompt: str, system_prompt: str = "", model: Optional[str] = None,
                       temperature: float = 0.7, tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        target_model = model or settings.OLLAMA_MODEL
        url = f"{self.base_url}/api/chat"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": target_model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature}
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=60) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Ollama returned {resp.status}")
                data = await resp.json()
                content = data.get("message", {}).get("content", "")
                return {"content": content, "model": target_model, "provider": "ollama", "tool_calls": None}

    async def stream(self, prompt: str, system_prompt: str = "", model: Optional[str] = None,
                     temperature: float = 0.7) -> AsyncGenerator[str, None]:
        res = await self.generate(prompt, system_prompt, model, temperature)
        yield res.get("content", "")


class InferenceRouter:
    """Master Multi-Engine Dispatcher with Automatic Resilience Fallback."""

    def __init__(self):
        self.gemini = GeminiEngine()
        self.openai = OpenAIEngine()
        self.ollama = OllamaEngine()
        self.hardware = detect_hardware_tier()

    def update_keys(self, gemini_key: Optional[str] = None, openai_key: Optional[str] = None) -> None:
        if gemini_key:
            self.gemini.api_key = gemini_key
        if openai_key:
            self.openai.api_key = openai_key

    async def generate(self, prompt: str, system_prompt: str = "", model: Optional[str] = None,
                       temperature: float = 0.7, tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        chosen_model = model or settings.GEMINI_MODEL
        target_engine: BaseEngine = self.gemini

        if "gpt" in chosen_model.lower() or "o1" in chosen_model.lower() or "o3" in chosen_model.lower():
            target_engine = self.openai
        elif "ollama" in chosen_model.lower() or "llama" in chosen_model.lower():
            target_engine = self.ollama

        # Attempt primary engine
        try:
            if await target_engine.health():
                return await target_engine.generate(prompt, system_prompt, chosen_model, temperature, tools)
        except Exception as e:
            logger.warning(f"[InferenceRouter] Primary engine {target_engine.__class__.__name__} failed: {e}. Trying fallback...")

        # Fallback cascade: Gemini -> OpenAI -> Ollama -> Safe Local Response
        if target_engine != self.gemini and await self.gemini.health():
            try:
                return await self.gemini.generate(prompt, system_prompt, settings.GEMINI_MODEL, temperature, tools)
            except Exception:
                pass

        if target_engine != self.openai and await self.openai.health():
            try:
                return await self.openai.generate(prompt, system_prompt, settings.OPENAI_MODEL, temperature, tools)
            except Exception:
                pass

        if await self.ollama.health():
            try:
                return await self.ollama.generate(prompt, system_prompt, settings.OLLAMA_MODEL, temperature, tools)
            except Exception:
                pass

        # If all offline, provide a graceful offline intelligence reply
        return {
            "content": (
                "Sir, all external neural backends are currently unreachable or missing API credentials. "
                "Local hardware telemetry, security guardrails, and desktop automation remain fully functional. "
                "Please configure a valid GEMINI_API_KEY in the Command Center Vault."
            ),
            "model": "offline-fallback",
            "provider": "offline",
            "tool_calls": None
        }

inference_router = InferenceRouter()
