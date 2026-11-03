import logging
from typing import Any
from jarvis.agents.base_agent import BaseAgent, AgentResult
from jarvis.agents.inbox import agent_inbox, InboxTaskStatus

logger = logging.getLogger("jarvis.agents.file")


class FileAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="file_agent",
            description="Specialist subagent for sandboxed file management, reading, and writing",
            system_prompt=(
                "You are the JARVIS File Specialist. Your responsibility is to inspect, read, "
                "and safely write files strictly within the sandboxed filesystem root."
            ),
            allowed_tools=["read_file", "write_file"]
        )

    async def run(
        self,
        task: str,
        context: dict[str, Any] | None = None,
        task_id: str | None = None
    ) -> AgentResult:
        logger.info(f"[{self.name}] Starting file operation on task: '{task}'")
        
        if task_id:
            await agent_inbox.update_status(task_id, InboxTaskStatus.RUNNING)

        ctx = context or {}
        action = ctx.get("action", "read")
        path = ctx.get("path", "")
        content = ctx.get("content", "")

        if action == "write":
            res = await self.invoke_tool(
                tool_name="write_file",
                args={"path": path, "content": content, "append": ctx.get("append", False)}
            )
            if not res.success:
                err = res.error or "File write failed"
                if task_id:
                    await agent_inbox.update_status(task_id, InboxTaskStatus.FAILED, {"error": err})
                return AgentResult(
                    agent_name=self.name,
                    task_id=task_id,
                    success=False,
                    summary=f"Write failed: {err}",
                    error=err
                )
            
            summary = f"Successfully wrote {res.data.get('bytes_written', 0)} bytes to '{path}'."
            artifacts = [{"type": "file", "path": path, "action": "written"}]

        else: # read
            res = await self.invoke_tool(
                tool_name="read_file",
                args={"path": path, "offset": ctx.get("offset", 0), "limit": ctx.get("limit", 100000)}
            )
            if not res.success:
                err = res.error or "File read failed"
                if task_id:
                    await agent_inbox.update_status(task_id, InboxTaskStatus.FAILED, {"error": err})
                return AgentResult(
                    agent_name=self.name,
                    task_id=task_id,
                    success=False,
                    summary=f"Read failed: {err}",
                    error=err
                )

            read_content = str(res.data)
            summary = f"Successfully read {len(read_content)} characters from '{path}'."
            artifacts = [{"type": "file", "path": path, "content_snippet": read_content[:200]}]

        output_payload = {
            "action": action,
            "path": path,
            "data": res.data
        }

        if task_id:
            await agent_inbox.update_status(
                task_id=task_id,
                status=InboxTaskStatus.COMPLETED,
                output_payload=output_payload,
                artifacts=artifacts
            )

        logger.info(f"[{self.name}] File task completed for '{path}'.")
        return AgentResult(
            agent_name=self.name,
            task_id=task_id,
            success=True,
            summary=summary,
            output_data=output_payload,
            artifacts=artifacts
        )


file_agent = FileAgent()
