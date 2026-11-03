"""
backend/core/tool_registry.py
Hermes-Assimilated Self-Registering Tool Dispatcher & Schema Collector.
Pre-screens every tool call through AgentShield before execution.
"""

import inspect
import time
import json
import logging
from typing import Callable, Dict, Any, List, Optional
from backend.security.agent_shield import AgentShield

logger = logging.getLogger("jarvis.tools")


class ToolRegistry:
    """Central registry and execution dispatcher for agent tools."""

    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._schemas: Dict[str, Dict[str, Any]] = {}
        self._risk_levels: Dict[str, str] = {}

    def register(self, name: str, description: str, parameters: Dict[str, Any], risk_level: str = "LOW"):
        """Decorator to register a function as an LLM tool."""
        def decorator(func: Callable):
            self._tools[name] = func
            self._schemas[name] = {
                "name": name,
                "description": description,
                "parameters": parameters
            }
            self._risk_levels[name] = risk_level.upper()
            return func
        return decorator

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Returns OpenAPI/JSON schemas for all registered tools."""
        return list(self._schemas.values())

    def get_tool(self, name: str) -> Optional[Callable]:
        return self._tools.get(name)

    async def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a registered tool with pre-tool security validation.
        """
        start_time = time.time()
        func = self._tools.get(tool_name)
        if not func:
            return {
                "tool": tool_name,
                "outcome": "ERROR",
                "result": f"Unknown tool: '{tool_name}'",
                "duration_ms": 0
            }

        # Pre-Tool Security Guardrail Check (ECC AgentShield)
        is_safe, reason = AgentShield.validate_tool_use(tool_name, arguments)
        if not is_safe:
            return {
                "tool": tool_name,
                "outcome": "DENIED",
                "result": f"SECURITY SHIELD INTERVENTION: {reason}",
                "duration_ms": round((time.time() - start_time) * 1000, 2)
            }

        try:
            # Handle both async and sync tools
            if inspect.iscoroutinefunction(func):
                result = await func(**arguments)
            else:
                result = func(**arguments)

            duration_ms = round((time.time() - start_time) * 1000, 2)
            # Redact secrets from output
            if isinstance(result, str):
                result = AgentShield.sanitize_output(result)
            elif isinstance(result, dict):
                result = {k: (AgentShield.sanitize_output(v) if isinstance(v, str) else v) for k, v in result.items()}

            return {
                "tool": tool_name,
                "outcome": "SUCCESS",
                "result": result,
                "duration_ms": duration_ms
            }

        except Exception as e:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            logger.error(f"[ToolRegistry] Error running {tool_name}: {e}")
            return {
                "tool": tool_name,
                "outcome": "ERROR",
                "result": f"Execution error: {str(e)}",
                "duration_ms": duration_ms
            }

tool_registry = ToolRegistry()
