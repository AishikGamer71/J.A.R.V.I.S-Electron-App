import logging
import re
from typing import Any

from jarvis.agents.base_agent import BaseAgent, AgentResult
from jarvis.agents.browser_agent import browser_agent
from jarvis.agents.chat_agent import chat_agent
from jarvis.agents.file_agent import file_agent
from jarvis.agents.inbox import agent_inbox, InboxTaskStatus
from jarvis.agents.research_agent import research_agent

logger = logging.getLogger("jarvis.agents.planning")


class PlanningAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="planning_agent",
            description="Master orchestrator: intent detection, task decomposition, subagent delegation, and result synthesis",
            system_prompt=(
                "You are the J.A.R.V.I.S Master Planning Orchestrator. "
                "Decompose complex goals into subtasks and delegate to specialized subagents."
            ),
            allowed_tools=[]
        )
        self.subagents = {
            "research_agent": research_agent,
            "browser_agent": browser_agent,
            "file_agent": file_agent,
            "chat_agent": chat_agent
        }

    def detect_intent(self, text: str) -> tuple[str, dict[str, Any]]:
        lower = text.lower().strip()

        # 1. Browser navigation intent
        url_match = re.search(r"(?:open|navigate to|browse to|visit)\s+(?:website\s+|page\s+)?(https?://[^\s]+|[a-zA-Z0-9-]+\.[a-zA-Z]{2,}[^\s]*)", text, re.IGNORECASE)
        if url_match:
            return "browser_agent", {
                "action": "open",
                "url": url_match.group(1).strip("'\"")
            }

        # 2. File write intent
        write_match = re.search(r"(?:save|write|create|append to)\s+(?:file\s+)?([^\s]+)\s+(?:with|containing)\s+(.*)", text, re.IGNORECASE)
        if write_match:
            return "file_agent", {
                "action": "write",
                "path": write_match.group(1).strip("'\""),
                "content": write_match.group(2).strip()
            }

        # 3. File read intent
        read_match = re.search(r"(?:read|show|open|view|inspect)\s+(?:file\s+)?([^\s]+\.[a-zA-Z0-9]+)", text, re.IGNORECASE)
        if read_match:
            return "file_agent", {
                "action": "read",
                "path": read_match.group(1).strip("'\"")
            }

        # 4. Web research intent
        if any(w in lower for w in ["search the web", "search for", "look up", "find information", "who is", "what is the latest", "research"]):
            query = re.sub(r"^(?:please\s+)?(?:search the web for|search for|look up|research)\s+", "", text, flags=re.IGNORECASE).strip()
            return "research_agent", {"query": query or text}

        # 5. Default: Chat / Direct Reasoning
        return "chat_agent", {"session_id": "default"}

    async def run(
        self,
        task: str,
        context: dict[str, Any] | None = None,
        task_id: str | None = None
    ) -> AgentResult:
        logger.info(f"[PLANNER] Orchestrating goal: '{task}'")
        
        target_agent_name, agent_ctx = self.detect_intent(task)
        logger.info(f"[PLANNER] Intent detected -> Delegating to '{target_agent_name}'")

        # 1. Create subtask in Hermes Agent Inbox
        subtask_entry = await agent_inbox.create_task(
            agent_name=target_agent_name,
            input_payload={"task": task, **agent_ctx},
            parent_task_id=task_id
        )

        # 2. Delegate execution to specialized subagent
        subagent = self.subagents.get(target_agent_name, chat_agent)
        subagent_res = await subagent.run(
            task=task,
            context=agent_ctx,
            task_id=subtask_entry.task_id
        )

        # 3. Retrieve verified task result from Inbox
        final_inbox_entry = await agent_inbox.get_task(subtask_entry.task_id)

        # 4. Synthesize final response
        synthesis = subagent_res.summary

        logger.info(f"[PLANNER] Goal completed. Delegated subtask: {subtask_entry.task_id}")
        return AgentResult(
            agent_name=self.name,
            task_id=task_id,
            success=subagent_res.success,
            summary=synthesis,
            output_data={
                "delegated_agent": target_agent_name,
                "subtask_id": subtask_entry.task_id,
                "inbox_status": final_inbox_entry.status if final_inbox_entry else "UNKNOWN",
                "subagent_output": subagent_res.output_data
            },
            artifacts=subagent_res.artifacts,
            error=subagent_res.error
        )


planning_agent = PlanningAgent()
