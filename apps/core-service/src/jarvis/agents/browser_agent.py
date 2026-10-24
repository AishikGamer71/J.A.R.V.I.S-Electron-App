import logging
from typing import Any
from jarvis.agents.base_agent import BaseAgent, AgentResult
from jarvis.agents.inbox import agent_inbox, InboxTaskStatus

logger = logging.getLogger("jarvis.agents.browser")


class BrowserAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="browser_agent",
            description="Specialist subagent for web browser navigation, DOM inspection, and web page automation",
            system_prompt=(
                "You are the JARVIS Autonomous Browser Agent. Your responsibility is to navigate URLs, "
                "interact with elements, extract information from web pages, and capture visual previews."
            ),
            allowed_tools=[
                "browser_open",
                "browser_click",
                "browser_type",
                "browser_screenshot"
            ]
        )

    async def run(
        self,
        task: str,
        context: dict[str, Any] | None = None,
        task_id: str | None = None
    ) -> AgentResult:
        logger.info(f"[{self.name}] Starting browser automation for task: '{task}'")

        if task_id:
            await agent_inbox.update_status(task_id, InboxTaskStatus.RUNNING)

        ctx = context or {}
        action = ctx.get("action", "open")
        url = ctx.get("url") or task

        artifacts = []

        if action == "click":
            selector = ctx.get("selector", "")
            res = await self.invoke_tool("browser_click", {"selector": selector})
            if not res.success:
                err = res.error or "Click failed"
                if task_id:
                    await agent_inbox.update_status(task_id, InboxTaskStatus.FAILED, {"error": err})
                return AgentResult(agent_name=self.name, task_id=task_id, success=False, summary=err, error=err)
            summary = f"Clicked element matching '{selector}'."

        elif action == "type":
            selector = ctx.get("selector", "")
            text = ctx.get("text", "")
            res = await self.invoke_tool("browser_type", {"selector": selector, "text": text})
            if not res.success:
                err = res.error or "Type failed"
                if task_id:
                    await agent_inbox.update_status(task_id, InboxTaskStatus.FAILED, {"error": err})
                return AgentResult(agent_name=self.name, task_id=task_id, success=False, summary=err, error=err)
            summary = f"Typed '{text}' into '{selector}'."

        else: # Default: open / navigate
            res = await self.invoke_tool("browser_open", {"url": url})
            if not res.success:
                err = res.error or "Navigation failed"
                if task_id:
                    await agent_inbox.update_status(task_id, InboxTaskStatus.FAILED, {"error": err})
                return AgentResult(agent_name=self.name, task_id=task_id, success=False, summary=err, error=err)

            page_data = res.data or {}
            title = page_data.get("title", url)
            summary = f"Navigated to '{page_data.get('url', url)}' ({title}).\n{page_data.get('dom_summary', '')[:500]}"
            if page_data.get("screenshot_base64"):
                artifacts.append({
                    "type": "browser_screenshot",
                    "url": page_data.get("url"),
                    "title": title,
                    "screenshot_base64": page_data.get("screenshot_base64")
                })

        output_payload = {
            "action": action,
            "url": url,
            "data": res.data if 'res' in locals() else {}
        }

        if task_id:
            await agent_inbox.update_status(
                task_id=task_id,
                status=InboxTaskStatus.COMPLETED,
                output_payload=output_payload,
                artifacts=artifacts
            )

        logger.info(f"[{self.name}] Browser action '{action}' completed successfully.")
        return AgentResult(
            agent_name=self.name,
            task_id=task_id,
            success=True,
            summary=summary,
            output_data=output_payload,
            artifacts=artifacts
        )


browser_agent = BrowserAgent()
