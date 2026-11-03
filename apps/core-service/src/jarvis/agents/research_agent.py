import logging
from typing import Any
from jarvis.agents.base_agent import BaseAgent, AgentResult
from jarvis.agents.inbox import agent_inbox, InboxTaskStatus

logger = logging.getLogger("jarvis.agents.research")


class ResearchAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="research_agent",
            description="Specialist subagent for web search, data lookup, and information gathering",
            system_prompt=(
                "You are the JARVIS Research Specialist. Your responsibility is to autonomously query the web, "
                "extract relevant findings, and format structured summaries for the orchestrator."
            ),
            allowed_tools=["web_search", "read_file"]
        )

    async def run(
        self,
        task: str,
        context: dict[str, Any] | None = None,
        task_id: str | None = None
    ) -> AgentResult:
        logger.info(f"[{self.name}] Starting research on task: '{task}'")
        
        if task_id:
            await agent_inbox.update_status(task_id, InboxTaskStatus.RUNNING)

        # 1. Execute web search
        query = (context or {}).get("query") or task
        search_res = await self.invoke_tool(
            tool_name="web_search",
            args={"query": query, "max_results": 5}
        )

        if not search_res.success:
            err = search_res.error or "Web search failed"
            if task_id:
                await agent_inbox.update_status(
                    task_id, InboxTaskStatus.FAILED, output_payload={"error": err}
                )
            return AgentResult(
                agent_name=self.name,
                task_id=task_id,
                success=False,
                summary=f"Research failed: {err}",
                error=err
            )

        results = search_res.data or []
        summary_lines = []
        artifacts = []

        for idx, item in enumerate(results, 1):
            title = item.get("title", f"Source {idx}")
            snippet = item.get("snippet", "")
            url = item.get("url", "")
            summary_lines.append(f"• **{title}**: {snippet}")
            artifacts.append({
                "type": "web_source",
                "title": title,
                "snippet": snippet,
                "url": url
            })

        full_summary = f"Synthesized research for '{query}':\n" + "\n".join(summary_lines)

        output_payload = {
            "query": query,
            "result_count": len(results),
            "sources": results
        }

        # Post to Hermes Inbox
        if task_id:
            await agent_inbox.update_status(
                task_id=task_id,
                status=InboxTaskStatus.COMPLETED,
                output_payload=output_payload,
                artifacts=artifacts
            )

        logger.info(f"[{self.name}] Research completed. Found {len(results)} sources.")
        return AgentResult(
            agent_name=self.name,
            task_id=task_id,
            success=True,
            summary=full_summary,
            output_data=output_payload,
            artifacts=artifacts
        )


research_agent = ResearchAgent()
