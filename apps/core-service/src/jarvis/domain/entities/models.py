from enum import Enum
from typing import Any, Literal
import time
import uuid
from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ModelTier(str, Enum):
    TIER1_LOCAL = "tier1_local"
    TIER2_BALANCED = "tier2_balanced"
    TIER3_CLOUD = "tier3_cloud"


class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    role: MessageRole
    content: str
    tier: ModelTier | None = None
    model: str | None = None
    created_at: float = Field(default_factory=time.time)
    tokens: dict[str, int] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = "New Session"
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    metadata: dict[str, Any] = Field(default_factory=dict)


class HardwareTelemetry(BaseModel):
    cpu_percent: float
    ram_percent: float
    ram_used_gb: float
    ram_total_gb: float
    gpu_name: str | None = None
    vram_used_mb: float | None = None
    vram_total_mb: float | None = None
    system_tier: Literal["low", "mid", "high"] = "mid"
    temperature_c: float | None = None
    timestamp: float = Field(default_factory=time.time)


class NetworkStatus(BaseModel):
    is_online: bool
    latency_ms: float | None = None
    checked_at: float = Field(default_factory=time.time)


class RouterDecision(BaseModel):
    tier: ModelTier
    selected_provider: Literal["ollama", "litellm"]
    selected_model: str
    reason: str
    is_fallback: bool = False
