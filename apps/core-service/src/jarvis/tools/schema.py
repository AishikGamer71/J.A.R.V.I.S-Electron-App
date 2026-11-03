from typing import Any
from pydantic import BaseModel, Field
from jarvis.security.risk_classifier import RiskLevel


class ToolDefinition(BaseModel):
    name: str
    description: str
    risk_level: RiskLevel
    parameters_schema: dict[str, Any]


class ReadFileInput(BaseModel):
    path: str = Field(..., description="Relative or absolute path inside the sandbox")
    offset: int = Field(default=0, ge=0, description="Byte offset to start reading from")
    limit: int = Field(default=100000, ge=1, description="Max characters/bytes to read")


class WriteFileInput(BaseModel):
    path: str = Field(..., description="Target file path inside the sandbox")
    content: str = Field(..., description="Text content to write")
    append: bool = Field(default=False, description="Whether to append instead of overwriting")


class WebSearchInput(BaseModel):
    query: str = Field(..., min_length=1, description="Search query string")
    max_results: int = Field(default=5, ge=1, le=20, description="Max results to return")


class ToolResult(BaseModel):
    tool: str
    success: bool
    data: Any = None
    error: str | None = None
    risk_level: RiskLevel
    sandboxed: bool = False
    execution_time_ms: float = 0.0
    audit_id: str | None = None
