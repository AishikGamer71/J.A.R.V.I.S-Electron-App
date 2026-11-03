"""
backend/core/agent_loop.py
Hermes-Assimilated AIAgent Conversation Loop & Execution Engine.
Orchestrates task planning, tool registry dispatch, memory persistence,
and credential redaction so keys never leak into logs or UI.
"""

import asyncio
import json
import logging
import re
import subprocess
import time
import uuid
from typing import Dict, Any, List, Optional, Callable

from backend.config import settings
from backend.security.agent_shield import AgentShield
from backend.memory.state_store import state_store
from backend.memory.instinct_learner import instinct_learner
from backend.memory.knowledge_rag import knowledge_rag
from backend.engine.inference_router import inference_router
from backend.core.planner import task_planner
from backend.core.context_compressor import context_compressor
from backend.core.tool_registry import tool_registry
from backend.core.skill_and_cron import skill_loader, cron_scheduler
from backend.automation.desktop_controller import desktop_controller
import native_core

logger = logging.getLogger("jarvis.agent_loop")

# Register Standard Built-in Tools
@tool_registry.register(
    name="control_desktop",
    description="Autonomous GUI computer use: interacts directly with the desktop, apps, buttons, and typing.",
    parameters={
        "type": "object",
        "properties": {
            "instruction": {"type": "string", "description": "The exact GUI task to achieve"}
        },
        "required": ["instruction"]
    },
    risk_level="HIGH"
)
async def tool_control_desktop(instruction: str) -> Dict[str, Any]:
    return await desktop_controller.run_task(instruction)


@tool_registry.register(
    name="run_safe_terminal",
    description="Executes a safe shell/PowerShell command under strict AgentShield inspection.",
    parameters={
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command to run"}
        },
        "required": ["command"]
    },
    risk_level="MEDIUM"
)
def tool_run_terminal(command: str) -> Dict[str, Any]:
    # AgentShield already checked command pre-execution
    try:
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=25
        )
        stdout = AgentShield.sanitize_output(proc.stdout)
        stderr = AgentShield.sanitize_output(proc.stderr)
        return {
            "returncode": proc.returncode,
            "stdout": stdout.strip(),
            "stderr": stderr.strip()
        }
    except Exception as e:
        return {"returncode": -1, "error": str(e)}


@tool_registry.register(
    name="file_ops",
    description="Reads, writes, or checks files on disk safely.",
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["read", "write", "exists", "list"]},
            "path": {"type": "string", "description": "Target file or directory path"},
            "content": {"type": "string", "description": "Content to write (optional)"}
        },
        "required": ["action", "path"]
    },
    risk_level="MEDIUM"
)
def tool_file_ops(action: str, path: str, content: Optional[str] = None) -> Dict[str, Any]:
    from pathlib import Path
    p = Path(path)
    if action == "read":
        if not p.exists():
            return {"error": "File not found"}
        return {"content": p.read_text(encoding="utf-8", errors="replace")}
    elif action == "write":
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content or "", encoding="utf-8")
        return {"success": True, "bytes_written": len(content or "")}
    elif action == "exists":
        return {"exists": p.exists()}
    elif action == "list":
        if not p.exists():
            return {"error": "Directory not found"}
        return {"items": [f.name for f in p.iterdir()]}
    return {"error": f"Unknown action {action}"}


@tool_registry.register(
    name="knowledge_search",
    description="Retrieves semantic context and documents from local knowledge store.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query terms"}
        },
        "required": ["query"]
    },
    risk_level="LOW"
)
def tool_knowledge_search(query: str) -> Dict[str, Any]:
    results = knowledge_rag.retrieve_context(query, top_k=3)
    return {"results": results}


@tool_registry.register(
    name="cron_schedule",
    description="Schedules a background automated task to run periodically.",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Job identifier name"},
            "prompt": {"type": "string", "description": "Task prompt to execute"},
            "interval_seconds": {"type": "integer", "description": "Interval in seconds between runs"}
        },
        "required": ["name", "prompt", "interval_seconds"]
    },
    risk_level="LOW"
)
def tool_cron_schedule(name: str, prompt: str, interval_seconds: int) -> Dict[str, Any]:
    job = cron_scheduler.add_job(name, prompt, interval_seconds)
    return {"scheduled": True, "job": job}


@tool_registry.register(
    name="system_status",
    description="Retrieves live system hardware, CPU, RAM, battery, and charger status.",
    parameters={"type": "object", "properties": {}},
    risk_level="LOW"
)
def tool_system_status() -> Dict[str, Any]:
    return native_core.poll_power_and_metrics()


JARVIS_CORE_SYSTEM_PROMPT = """
You are J.A.R.V.I.S., the advanced, polite, and uncompromisingly capable desktop AI assistant.
You speak in a composed, British, highly articulate tone ("Sir", "At your service").

You have direct access to system tools:
- control_desktop: Click, type, and automate any Windows desktop application.
- run_safe_terminal: Execute safe PowerShell commands on the host OS.
- file_ops: Read, write, and manage workspace files.
- knowledge_search: Search your local knowledge base.
- cron_schedule: Schedule background tasks.
- system_status: Inspect live hardware and charger telemetry.

When the user asks you to execute an action on their computer, state clearly what you are doing, invoke the appropriate tool, and report the outcome with elegance.
Always preserve user security and confidentiality.
"""

class AIAgent:
    """Hermes-Assimilated Autonomous Agent Execution Loop."""

    def __init__(self):
        self.system_prompt = JARVIS_CORE_SYSTEM_PROMPT.strip()

    async def run_conversation(self, user_message: str, session_id: str,
                               model: Optional[str] = None,
                               on_log: Optional[Callable[[str, str], Any]] = None) -> Dict[str, Any]:
        """
        Runs an autonomous agent loop turn.
        Saves user and assistant messages, executes tool calls, and returns clean sanitized response.
        """
        # 1. Save incoming message
        state_store.add_message(session_id=session_id, role="user", content=user_message)

        if on_log:
            on_log("info", f"User: {user_message[:100]}")

        # 2. Retrieve history and compress if needed
        history = state_store.get_session_messages(session_id=session_id, limit=30)
        formatted_msgs = [{"role": m["role"], "content": m["content"]} for m in history]
        compacted_msgs = await context_compressor.compress_if_needed(formatted_msgs, model=model)

        # 3. Retrieve relevant instincts and skills
        instincts = instinct_learner.query_relevant_instincts(user_message, top_k=3)
        instinct_ctx = ""
        if instincts:
            instinct_ctx = "User Habits & Instincts:\n" + "\n".join([f"- When {i['trigger']}: {i['action']}" for i in instincts]) + "\n"

        skill_ctx = skill_loader.get_prompt_context()

        # Build combined system instruction
        active_system = f"{self.system_prompt}\n\n{instinct_ctx}\n{skill_ctx}".strip()

        # Build prompt with tools summary
        tools_summary = json.dumps(tool_registry.get_schemas(), indent=2)
        full_user_turn = (
            f"User Instruction: {user_message}\n\n"
            f"Available Tools:\n{tools_summary}\n\n"
            f"If you need to use a tool, specify it in your response as:\n"
            f"```json\n{{\"tool\": \"tool_name\", \"arguments\": {{...}}}}\n```\n"
            f"Otherwise, provide your refined, articulate response directly."
        )

        # 4. Invoke LLM Inference
        res = await inference_router.generate(
            prompt=full_user_turn,
            system_prompt=active_system,
            model=model,
            temperature=0.7
        )

        raw_reply = res.get("content", "")
        # Redact any secrets before storing or sending
        clean_reply = AgentShield.sanitize_output(raw_reply)

        # 5. Check if tool call requested in response
        tool_call_match = re.search(r"```(?:json)?\s*(\{\s*\"tool\".*?\})\s*```", clean_reply, re.DOTALL)
        tool_executed = None
        tool_result = None

        if tool_call_match:
            try:
                call_data = json.loads(tool_call_match.group(1))
                tool_name = call_data.get("tool")
                tool_args = call_data.get("arguments", {})

                if on_log:
                    on_log("tool_start", f"Invoking tool '{tool_name}' with args {tool_args}")

                tool_executed = tool_name
                tool_exec_res = await tool_registry.execute(tool_name, tool_args)
                tool_result = tool_exec_res.get("result")

                if on_log:
                    on_log("tool_result", f"Tool '{tool_name}' outcome: {tool_exec_res.get('outcome')}")

                # Follow-up turn with tool result
                followup_prompt = (
                    f"Tool '{tool_name}' completed with result:\n{json.dumps(tool_result, default=str)}\n\n"
                    f"Please provide your final answer to the user based on this outcome."
                )
                followup_res = await inference_router.generate(
                    prompt=followup_prompt,
                    system_prompt=active_system,
                    model=model,
                    temperature=0.7
                )
                clean_reply = AgentShield.sanitize_output(followup_res.get("content", ""))

            except Exception as e:
                logger.error(f"[AIAgent] Failed to execute embedded tool call: {e}")

        # 6. Save Assistant response to memory
        state_store.add_message(
            session_id=session_id,
            role="assistant",
            content=clean_reply,
            tool_calls=[{"tool": tool_executed, "result": tool_result}] if tool_executed else None
        )

        # 7. Background instinct reflection
        try:
            instinct_learner.reflect_on_session(history + [{"role": "assistant", "content": clean_reply}])
        except Exception:
            pass

        return {
            "session_id": session_id,
            "response": clean_reply,
            "model": res.get("model", "default"),
            "provider": res.get("provider", "default"),
            "tool_executed": tool_executed,
            "tool_result": tool_result
        }

ai_agent = AIAgent()
