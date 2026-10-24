from abc import ABC, abstractmethod
import logging
from typing import Any
from pydantic import BaseModel

from jarvis.agents.inbox import agent_inbox, InboxTaskStatus
from jarvis.tools.registry import tool_registry

logger = logging.getLogger("jarvis.agents.base")


class AgentResult(BaseModel):
    agent_name: str
    task_id: str | None = None
    success: bool
    summary: str
    output_data: dict[str, Any] = {}
    artifacts: list[dict[str, Any]] = []
    error: str | None = None


class BaseAgent(ABC):
    def __init__(
        self,
        name: str,
        description: str,
        system_prompt: str,
        allowed_tools: list[str] | None = None
    ):
        self.name = name
        self.description = description
        self.system_prompt = system_prompt
        self.allowed_tools = set(allowed_tools or [])

    def can_use_tool(self, tool_name: str) -> bool:
        if not self.allowed_tools:
            return True
        return tool_name in self.allowed_tools

    async def invoke_tool(self, tool_name: str, args: dict[str, Any], session_id: str | None = None) -> Any:
        if not self.can_use_tool(tool_name):
            raise PermissionError(
                f"Agent '{self.name}' is not authorized to call tool '{tool_name}'. Allowed: {list(self.allowed_tools)}"
            )
        return await tool_registry.invoke(
            name=tool_name,
            args=args,
            scope=self.name,
            session_id=session_id
        )

    @abstractmethod
    async def run(
        self,
        task: str,
        context: dict[str, Any] | None = None,
        task_id: str | None = None
    ) -> AgentResult:
        pass
