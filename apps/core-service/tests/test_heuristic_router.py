import pytest
from unittest.mock import AsyncMock
from jarvis.domain.entities.models import ChatMessage, MessageRole, ModelTier, NetworkStatus
from jarvis.router.heuristic_router import HeuristicRouter
from jarvis.router.tiers import classify_tier


def test_tier_classification():
    assert classify_tier("Hello JARVIS") == ModelTier.TIER1_LOCAL
    assert classify_tier("open chrome") == ModelTier.TIER1_LOCAL
    assert classify_tier("system status") == ModelTier.TIER1_LOCAL
    assert classify_tier("How does a binary search tree work in Python?") == ModelTier.TIER2_BALANCED
    assert classify_tier("Perform an in-depth security audit and architecture refactor of our microservices") == ModelTier.TIER3_CLOUD


@pytest.mark.asyncio
async def test_router_offline_fallback(monkeypatch):
    router = HeuristicRouter()

    # Mock network monitor to return offline
    async def mock_offline():
        return NetworkStatus(is_online=False)
    monkeypatch.setattr(router.ollama_provider, "health_check", AsyncMock(return_value=True))

    from jarvis.telemetry import network_monitor
    monkeypatch.setattr(network_monitor.network_monitor, "check_connectivity", mock_offline)

    msg = ChatMessage(session_id="s1", role=MessageRole.USER, content="Explain quantum entanglement")
    provider, decision = await router.route([msg])

    assert decision.selected_provider == "ollama"
    assert decision.is_fallback is True
    assert "offline" in decision.reason.lower()
