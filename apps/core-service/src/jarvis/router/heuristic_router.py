import logging
from jarvis.config.settings import settings
from jarvis.domain.entities.models import ChatMessage, ModelTier, RouterDecision
from jarvis.providers.base import ModelProvider
from jarvis.providers.litellm_provider import LiteLLMProvider
from jarvis.providers.ollama_provider import OllamaProvider
from jarvis.router.tiers import classify_tier
from jarvis.telemetry.hardware import get_hardware_telemetry
from jarvis.telemetry.network_monitor import network_monitor

logger = logging.getLogger("jarvis.router.heuristic")


class HeuristicRouter:
    def __init__(
        self,
        ollama_provider: OllamaProvider | None = None,
        litellm_provider: LiteLLMProvider | None = None
    ):
        self.ollama_provider = ollama_provider or OllamaProvider()
        self.litellm_provider = litellm_provider or LiteLLMProvider()

    async def route(self, messages: list[ChatMessage]) -> tuple[ModelProvider, RouterDecision]:
        if not messages:
            last_text = ""
        else:
            last_text = messages[-1].content

        tier = classify_tier(last_text)
        net_status = await network_monitor.check_connectivity()
        hw_telemetry = get_hardware_telemetry()
        has_cloud_keys = await self.litellm_provider.health_check()

        # 1. Offline Mode -> Force Local Ollama
        if not net_status.is_online:
            decision = RouterDecision(
                tier=ModelTier.TIER1_LOCAL,
                selected_provider="ollama",
                selected_model=settings.TIER1_MODEL,
                reason="Network offline: falling back to local Ollama",
                is_fallback=True
            )
            return self.ollama_provider, decision

        # 2. No Cloud API Keys -> Fallback to Ollama
        if not has_cloud_keys:
            decision = RouterDecision(
                tier=tier,
                selected_provider="ollama",
                selected_model=settings.TIER1_MODEL,
                reason="No Cloud API keys configured: routing to local Ollama",
                is_fallback=True
            )
            return self.ollama_provider, decision

        # 3. Normal Tier Routing
        if tier == ModelTier.TIER1_LOCAL:
            # If Ollama is available, prefer local for Tier 1 to save latency/tokens
            is_ollama_alive = await self.ollama_provider.health_check()
            if is_ollama_alive:
                decision = RouterDecision(
                    tier=ModelTier.TIER1_LOCAL,
                    selected_provider="ollama",
                    selected_model=settings.TIER1_MODEL,
                    reason="Tier 1 quick command routed to local Ollama",
                    is_fallback=False
                )
                return self.ollama_provider, decision
            else:
                # Fast cloud fallback for Tier 1
                decision = RouterDecision(
                    tier=ModelTier.TIER1_LOCAL,
                    selected_provider="litellm",
                    selected_model=settings.TIER2_MODEL,
                    reason="Tier 1 routed to fast cloud model (Ollama inactive)",
                    is_fallback=False
                )
                return self.litellm_provider, decision

        elif tier == ModelTier.TIER3_CLOUD:
            decision = RouterDecision(
                tier=ModelTier.TIER3_CLOUD,
                selected_provider="litellm",
                selected_model=settings.TIER3_MODEL,
                reason="Tier 3 complex reasoning routed to advanced cloud model",
                is_fallback=False
            )
            return self.litellm_provider, decision

        else: # TIER2_BALANCED
            decision = RouterDecision(
                tier=ModelTier.TIER2_BALANCED,
                selected_provider="litellm",
                selected_model=settings.TIER2_MODEL,
                reason="Tier 2 balanced reasoning routed to standard cloud model",
                is_fallback=False
            )
            return self.litellm_provider, decision
