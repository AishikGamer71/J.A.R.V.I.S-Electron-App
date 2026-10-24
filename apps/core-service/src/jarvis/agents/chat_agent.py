import logging
from typing import Any
from jarvis.agents.base_agent import BaseAgent, AgentResult
from jarvis.domain.entities.models import ChatMessage, MessageRole
from jarvis.router.heuristic_router import HeuristicRouter
from jarvis.skills.catalog import skill_catalog

logger = logging.getLogger("jarvis.agents.chat")


class ChatAgent(BaseAgent):
    def __init__(self, router: HeuristicRouter | None = None):
        super().__init__(
            name="chat_agent",
            description="Default conversational assistant for direct reasoning, Q&A, and quick dialogue",
            system_prompt=(
                "You are J.A.R.V.I.S, an advanced autonomous operating intelligence. "
                "Provide precise, thoughtful, and highly capable assistance."
            ),
            allowed_tools=[]
        )
        self.router = router or HeuristicRouter()

    async def run(
        self,
        task: str,
        context: dict[str, Any] | None = None,
        task_id: str | None = None
    ) -> AgentResult:
        session_id = context.get("session_id", "default") if context else "default"
        messages = [ChatMessage(session_id=session_id, role=MessageRole.USER, content=task)]
        skill_context = skill_catalog.build_prompt_context(task, agent_name=self.name)
        if skill_context:
            messages.insert(0, ChatMessage(session_id=session_id, role=MessageRole.SYSTEM, content=skill_context))
        provider, decision = await self.router.route(messages)
        resp = await provider.generate(messages=messages, model=decision.selected_model)

        return AgentResult(
            agent_name=self.name,
            task_id=task_id,
            success=True,
            summary=resp.content,
            output_data={"tier": decision.tier.value, "model": decision.selected_model}
        )


chat_agent = ChatAgent()
