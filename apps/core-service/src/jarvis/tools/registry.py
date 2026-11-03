import asyncio
import inspect
import logging
import time
from typing import Any, Callable, Coroutine
from pydantic import BaseModel

from jarvis.security.audit_log import audit_log
from jarvis.security.confirmation_bridge import confirmation_bridge
from jarvis.security.permission_store import permission_store
from jarvis.security.risk_classifier import RiskLevel, risk_classifier
from jarvis.security.sandbox_runner import sandbox_runner
from jarvis.tools.file_tools import read_file_tool, write_file_tool
from jarvis.tools.browser_tools import (
    BrowserClickInput,
    BrowserOpenInput,
    BrowserScreenshotInput,
    BrowserTypeInput,
    browser_click_tool,
    browser_open_tool,
    browser_screenshot_tool,
    browser_type_tool,
)
from jarvis.tools.computer_tools import (
    DesktopScreenshotInput,
    ListWindowsInput,
    OpenApplicationInput,
    list_open_windows_tool,
    open_application_tool,
    take_desktop_screenshot_tool,
)
from jarvis.tools.schema import (
    ReadFileInput,
    ToolDefinition,
    ToolResult,
    WebSearchInput,
    WriteFileInput,
)
from jarvis.tools.web_tools import web_search_tool

logger = logging.getLogger("jarvis.tools.registry")


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}
        self._handlers: dict[str, Callable] = {}
        self._input_schemas: dict[str, type[BaseModel]] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        self.register(
            name="read_file",
            description="Read text content from a file inside the sandbox root",
            risk_level=RiskLevel.LOW,
            input_schema=ReadFileInput,
            handler=read_file_tool
        )
        self.register(
            name="write_file",
            description="Write or append text content to a file inside the sandbox root",
            risk_level=RiskLevel.MEDIUM,
            input_schema=WriteFileInput,
            handler=write_file_tool
        )
        self.register(
            name="web_search",
            description="Perform a structured search query on the public web",
            risk_level=RiskLevel.LOW,
            input_schema=WebSearchInput,
            handler=web_search_tool
        )
        # Browser Tools (OpenClaw)
        self.register(
            name="browser_open",
            description="Navigate to a URL and inspect DOM text & visual preview",
            risk_level=RiskLevel.MEDIUM,
            input_schema=BrowserOpenInput,
            handler=browser_open_tool
        )
        self.register(
            name="browser_click",
            description="Click an element matching CSS selector or text descriptor",
            risk_level=RiskLevel.HIGH,
            input_schema=BrowserClickInput,
            handler=browser_click_tool
        )
        self.register(
            name="browser_type",
            description="Type text into an input field matching CSS selector",
            risk_level=RiskLevel.HIGH,
            input_schema=BrowserTypeInput,
            handler=browser_type_tool
        )
        self.register(
            name="browser_screenshot",
            description="Capture current active browser viewport preview",
            risk_level=RiskLevel.LOW,
            input_schema=BrowserScreenshotInput,
            handler=browser_screenshot_tool
        )
        # Computer & OS Tools (OpenClaw)
        self.register(
            name="take_desktop_screenshot",
            description="Capture host desktop screen display",
            risk_level=RiskLevel.LOW,
            input_schema=DesktopScreenshotInput,
            handler=take_desktop_screenshot_tool
        )
        self.register(
            name="list_open_windows",
            description="List active processes and open GUI windows on host",
            risk_level=RiskLevel.LOW,
            input_schema=ListWindowsInput,
            handler=list_open_windows_tool
        )
        self.register(
            name="open_application",
            description="Launch an allowed desktop application executable",
            risk_level=RiskLevel.MEDIUM,
            input_schema=OpenApplicationInput,
            handler=open_application_tool
        )

    def register(
        self,
        name: str,
        description: str,
        risk_level: RiskLevel,
        input_schema: type[BaseModel],
        handler: Callable
    ) -> None:
        self._tools[name] = ToolDefinition(
            name=name,
            description=description,
            risk_level=risk_level,
            parameters_schema=input_schema.model_json_schema()
        )
        self._handlers[name] = handler
        self._input_schemas[name] = input_schema
        risk_classifier.register_tool_risk(name, risk_level)
        logger.info(f"Registered tool '{name}' [Risk: {risk_level.value}]")

    def get_tool(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def list_tools(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    async def invoke(
        self,
        name: str,
        args: dict[str, Any],
        scope: str = "*",
        session_id: str | None = None
    ) -> ToolResult:
        start_time = time.perf_counter()

        if name not in self._tools:
            err_msg = f"Unknown tool: '{name}'"
            await audit_log.record(name, args, RiskLevel.HIGH.value, "BLOCKED_UNKNOWN_TOOL")
            return ToolResult(
                tool=name,
                success=False,
                error=err_msg,
                risk_level=RiskLevel.HIGH
            )

        tool_def = self._tools[name]
        handler = self._handlers[name]
        schema_cls = self._input_schemas[name]

        # Stage 1: Validate Schema
        try:
            validated_input = schema_cls(**args)
        except Exception as e:
            err_msg = f"Input validation failed for '{name}': {e}"
            await audit_log.record(name, args, tool_def.risk_level.value, "BLOCKED_INVALID_SCHEMA")
            return ToolResult(
                tool=name,
                success=False,
                error=err_msg,
                risk_level=tool_def.risk_level
            )

        # Stage 2: Risk Classification (Static + Dynamic inspection)
        risk = risk_classifier.classify(name, args)

        # Stage 3: Permission Check (Default-Deny)
        is_granted = await permission_store.check(name, scope)

        # Stage 4: Confirmation Bridge (if MEDIUM+ and not pre-granted)
        if not is_granted and risk in [RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]:
            approved = await confirmation_bridge.request_confirmation(
                tool_name=name,
                args=args,
                risk_level=risk.value
            )
            if not approved:
                audit_id = await audit_log.record(
                    name, args, risk.value, "BLOCKED_CONFIRMATION_DENIED"
                )
                return ToolResult(
                    tool=name,
                    success=False,
                    error=f"Execution of '{name}' denied by user confirmation bridge.",
                    risk_level=risk,
                    audit_id=audit_id
                )

        # Stage 5: Execution (Sandbox Runner for HIGH+ or Direct Handler)
        is_sandboxed = False
        try:
            if inspect.iscoroutinefunction(handler):
                result_data = await handler(validated_input)
            else:
                result_data = handler(validated_input)

            duration = round((time.perf_counter() - start_time) * 1000, 2)
            audit_id = await audit_log.record(
                name, args, risk.value, "SUCCESS", details={"duration_ms": duration}
            )

            return ToolResult(
                tool=name,
                success=True,
                data=result_data,
                risk_level=risk,
                sandboxed=is_sandboxed,
                execution_time_ms=duration,
                audit_id=audit_id
            )

        except Exception as e:
            duration = round((time.perf_counter() - start_time) * 1000, 2)
            audit_id = await audit_log.record(
                name, args, risk.value, "FAILED", details={"error": str(e)}
            )
            return ToolResult(
                tool=name,
                success=False,
                error=str(e),
                risk_level=risk,
                sandboxed=is_sandboxed,
                execution_time_ms=duration,
                audit_id=audit_id
            )


tool_registry = ToolRegistry()
