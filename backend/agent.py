import asyncio
import json
import logging
import os
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional
from google import genai
from google.genai import types

from backend.config import settings
from backend.memory import memory_store
from backend.tools import (
    tool_system_telemetry,
    tool_launch_application,
    tool_run_shell_command,
    tool_take_screenshot,
    tool_get_active_window,
    tool_web_search
)

logger = logging.getLogger("jarvis.agent")

JARVIS_SYSTEM_INSTRUCTION = """You are J.A.R.V.I.S. (Just A Rather Very Intelligent System), an advanced autonomous desktop assistant.
Your persona is inspired by refined British sophistication: courteous, technically sharp, concise, perceptive, and unfailingly reliable.
Keep verbal and text responses concise, clear, and direct. You are integrated directly into the user's desktop operating system.
You have direct access to desktop tools:
- system_telemetry: check CPU, RAM, disk, battery, and network speeds.
- launch_application: launch desktop applications like Chrome, Notepad, Calculator, VS Code.
- run_shell_command: execute safe command-line instructions.
- take_screenshot: view the primary monitor when analyzing visual items.
- get_active_window: check which window the user is currently focused on.
- web_search: retrieve up-to-date facts, documentation, or news.

When a user asks to perform an action or check status, use your available tools immediately. Always prioritize safety and precision."""

# Asynchronous tool definitions matching Google GenAI schema extraction
async def get_hardware_telemetry() -> str:
    """Fetch current real-time hardware telemetry: CPU load, RAM usage, disk space, battery status, and network counters."""
    data = await tool_system_telemetry()
    return json.dumps(data)

async def launch_app(application_name: str) -> str:
    """Launch an application on the host machine by name (e.g. 'notepad', 'chrome', 'calculator', 'code')."""
    res = await tool_launch_application(application_name)
    return json.dumps(res)

async def execute_shell(command: str) -> str:
    """Execute a safe shell command on the host. Potentially destructive operations trigger user confirmation."""
    res = await tool_run_shell_command(command)
    return json.dumps(res)

async def capture_screen() -> str:
    """Capture a screenshot of the primary desktop monitor to analyze current visual content."""
    res = await tool_take_screenshot()
    if res.get("success"):
        return json.dumps({"success": True, "message": "Screenshot captured successfully", "dimensions": f"{res.get('width')}x{res.get('height')}"})
    return json.dumps(res)

async def active_window() -> str:
    """Retrieve the title and process of the currently active desktop window."""
    res = await tool_get_active_window()
    return json.dumps(res)

async def search_web_info(query: str) -> str:
    """Search the web for up-to-date facts, current news, technical documentation, or knowledge."""
    res = await tool_web_search(query)
    return json.dumps(res)

AVAILABLE_TOOLS = [
    get_hardware_telemetry,
    launch_app,
    execute_shell,
    capture_screen,
    active_window,
    search_web_info
]

class JarvisAgent:
    def __init__(self):
        self._client: Optional[genai.Client] = None
        self._api_key: Optional[str] = None
        self._init_client()

    def _init_client(self):
        api_key = os.environ.get("GEMINI_API_KEY") or settings.GEMINI_API_KEY
        if api_key and api_key.strip():
            self._api_key = api_key.strip()
            try:
                self._client = genai.Client(api_key=self._api_key)
                logger.info("[JarvisAgent] Google GenAI client initialized successfully.")
            except Exception as e:
                logger.error(f"[JarvisAgent] Error initializing GenAI client: {e}")
                self._client = None
        else:
            self._client = None
            self._api_key = None

    def update_api_key(self, api_key: str):
        if api_key and api_key.strip():
            os.environ["GEMINI_API_KEY"] = api_key.strip()
            self._init_client()

    def is_configured(self) -> bool:
        return self._client is not None

    async def generate_response(self, prompt: str) -> Dict[str, Any]:
        session_id = f"task_{int(asyncio.get_event_loop().time()*1000)}"
        text = await self.chat_stream(session_id=session_id, user_prompt=prompt)
        return {"text": text, "session_id": session_id}

    async def chat_stream(
        self,
        session_id: str,
        user_prompt: str,
        on_state: Optional[Callable[[str], Any]] = None,
        on_chunk: Optional[Callable[[str], Any]] = None,
        on_tool_start: Optional[Callable[[str, dict], Any]] = None,
        on_tool_result: Optional[Callable[[str, Any], Any]] = None
    ) -> str:
        """
        Process a user prompt using Google Gemini with multi-turn memory, streaming, and tool execution.
        """
        await memory_store.get_or_create_session(session_id)
        await memory_store.save_message(session_id, "user", user_prompt)

        # Handle unconfigured key gracefully
        if not self._client:
            msg = (
                "Good day, sir. My neural engine is operational, but requires a valid `GEMINI_API_KEY` "
                "to establish an autonomous link. Please open the **Settings** tab and enter your key in the Command Center Vault."
            )
            if on_state:
                on_state("speaking")
            if on_chunk:
                on_chunk(msg)
            await memory_store.save_message(session_id, "assistant", msg)
            if on_state:
                on_state("idle")
            return msg

        if on_state:
            on_state("thinking")

        # Load recent conversation history
        history_msgs = await memory_store.get_messages(session_id, limit=16)
        contents = []
        for m in history_msgs:
            role = "user" if m["role"] == "user" else "model"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=m["content"])]
                )
            )

        config = types.GenerateContentConfig(
            system_instruction=JARVIS_SYSTEM_INSTRUCTION,
            temperature=0.7,
            tools=AVAILABLE_TOOLS
        )

        model_name = settings.GEMINI_MODEL
        full_response = ""

        try:
            # First turn generation
            response = await asyncio.to_thread(
                self._client.models.generate_content,
                model=model_name,
                contents=contents,
                config=config
            )

            # Check for function calls
            has_tool_call = False
            if response.function_calls:
                has_tool_call = True
                if on_state:
                    on_state("executing_tool")

                tool_results_parts = []
                for call in response.function_calls:
                    call_name = call.name
                    call_args = dict(call.args) if call.args else {}

                    logger.info(f"[JarvisAgent] Executing tool: {call_name}({call_args})")
                    if on_tool_start:
                        on_tool_start(call_name, call_args)

                    # Find tool and run
                    handler = next((t for t in AVAILABLE_TOOLS if t.__name__ == call_name), None)
                    if handler:
                        try:
                            if asyncio.iscoroutinefunction(handler):
                                result_data = await handler(**call_args)
                            else:
                                result_data = handler(**call_args)
                        except Exception as e:
                            result_data = json.dumps({"error": str(e)})
                    else:
                        result_data = json.dumps({"error": f"Tool '{call_name}' not found"})

                    # Record in persistent audit log for the HUD activity feed
                    try:
                        risk_level = "HIGH" if call_name in ["execute_shell", "run_shell_command"] else "LOW"
                        outcome = "ERROR" if "error" in str(result_data).lower() else "SUCCESS"
                        await memory_store.log_audit(
                            tool=call_name,
                            args_summary=call_args,
                            risk_level=risk_level,
                            outcome=outcome,
                            details={"result": str(result_data)[:300]}
                        )
                    except Exception as audit_err:
                        logger.debug(f"[Audit] error logging: {audit_err}")

                    if on_tool_result:
                        on_tool_result(call_name, result_data)

                    tool_results_parts.append(
                        types.Part.from_function_response(
                            name=call_name,
                            response={"result": result_data}
                        )
                    )

                # Send tool execution output back to model for synthesis
                contents.append(response.candidates[0].content)
                contents.append(types.Content(role="user", parts=tool_results_parts))

                if on_state:
                    on_state("thinking")

                # Second turn: synthesize final response with tool results
                synth_stream = await asyncio.to_thread(
                    self._client.models.generate_content_stream,
                    model=model_name,
                    contents=contents,
                    config=config
                )

                if on_state:
                    on_state("speaking")

                for chunk in synth_stream:
                    text_piece = chunk.text or ""
                    if text_piece:
                        full_response += text_piece
                        if on_chunk:
                            on_chunk(text_piece)

            else:
                # Direct response
                text_content = response.text or ""
                full_response = text_content
                if on_state:
                    on_state("speaking")
                if on_chunk:
                    on_chunk(text_content)

        except Exception as e:
            logger.error(f"[JarvisAgent] Generation error: {e}", exc_info=True)
            full_response = f"I encountered an error communicating with my neural core: {str(e)}"
            if on_chunk:
                on_chunk(full_response)

        await memory_store.save_message(session_id, "assistant", full_response)
        if on_state:
            on_state("idle")

        return full_response

jarvis_agent = JarvisAgent()
