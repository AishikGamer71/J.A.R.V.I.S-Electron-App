import asyncio
from contextlib import asynccontextmanager
import json
import logging
import time
import uuid
from typing import Any
from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from jarvis.config.settings import settings
from jarvis.domain.entities.models import (
    ChatMessage,
    ChatSession,
    HardwareTelemetry,
    MessageRole,
    NetworkStatus,
    RouterDecision,
)
from jarvis.gateway.auth import verify_auth_token
from jarvis.memory.sqlite_store import SQLiteMemoryStore
from jarvis.router.heuristic_router import HeuristicRouter
from jarvis.router.prompt_cache import prompt_cache
from jarvis.security.audit_log import audit_log
from jarvis.security.confirmation_bridge import confirmation_bridge
from jarvis.security.permission_store import permission_store
from jarvis.agents.inbox import agent_inbox
from jarvis.agents.planning_agent import planning_agent
from jarvis.agents.research_agent import research_agent
from jarvis.agents.browser_agent import browser_agent
from jarvis.agents.file_agent import file_agent
from jarvis.agents.chat_agent import chat_agent
from jarvis.telemetry.hardware import get_hardware_telemetry
from jarvis.telemetry.network_monitor import network_monitor
from jarvis.tools.registry import tool_registry
from jarvis.skills.catalog import skill_catalog

logger = logging.getLogger("jarvis.gateway.server")

# Global services
memory_store = SQLiteMemoryStore()
router = HeuristicRouter()
START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await memory_store.init_db()
    await permission_store.init_db()
    await audit_log.init_db()
    await agent_inbox.init_db()
    skill_catalog.reload()
    logger.info("J.A.R.V.I.S Gateway, Security & Agent Inbox initialized successfully.")
    yield


app = FastAPI(
    title="J.A.R.V.I.S Autonomous Core Gateway",
    version="4.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def add_skill_context(messages: list[ChatMessage]) -> list[ChatMessage]:
    """Prepend only relevant, local skill instructions to a model request."""
    if not messages:
        return messages
    skill_context = skill_catalog.build_prompt_context(messages[-1].content, agent_name="chat_agent")
    if not skill_context:
        return messages
    return [
        ChatMessage(session_id=messages[-1].session_id, role=MessageRole.SYSTEM, content=skill_context),
        *messages,
    ]


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "jarvis-core-service",
        "version": "4.0.0",
        "uptime_seconds": round(time.time() - START_TIME, 1)
    }


@app.get("/telemetry")
async def get_telemetry():
    hw = get_hardware_telemetry()
    net = await network_monitor.check_connectivity()
    return {
        "hardware": hw.model_dump(),
        "network": net.model_dump(),
        "uptime_seconds": round(time.time() - START_TIME, 1)
    }


# Session Management Endpoints
class CreateSessionRequest(BaseModel):
    title: str = "New Session"


@app.get("/sessions", dependencies=[Depends(verify_auth_token)])
async def list_sessions(limit: int = 50):
    return await memory_store.list_sessions(limit=limit)


@app.post("/sessions", dependencies=[Depends(verify_auth_token)])
async def create_session(req: CreateSessionRequest):
    return await memory_store.create_session(title=req.title)


@app.get("/sessions/{session_id}/messages", dependencies=[Depends(verify_auth_token)])
async def get_session_messages(session_id: str, limit: int = 100):
    return await memory_store.get_messages(session_id=session_id, limit=limit)


@app.delete("/sessions/{session_id}", dependencies=[Depends(verify_auth_token)])
async def delete_session(session_id: str):
    success = await memory_store.delete_session(session_id=session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True}


@app.get("/search", dependencies=[Depends(verify_auth_token)])
async def search_messages(q: str = Query(..., min_length=1), limit: int = 20):
    return await memory_store.search_messages(query=q, limit=limit)


# Tool Subsystem Endpoints
class InvokeToolRequest(BaseModel):
    name: str
    arguments: dict[str, Any] = {}
    scope: str = "*"
    session_id: str | None = None


@app.get("/v1/tools", dependencies=[Depends(verify_auth_token)])
async def list_registered_tools():
    return tool_registry.list_tools()


# Local Agent Skills (Hermes/OpenClaw-compatible SKILL.md bundles)
@app.get("/v1/skills", dependencies=[Depends(verify_auth_token)])
async def list_skills():
    return {
        "skills": [skill.as_public_dict() for skill in skill_catalog.list_skills()],
        "errors": skill_catalog.errors(),
    }


@app.post("/v1/skills/reload", dependencies=[Depends(verify_auth_token)])
async def reload_skills():
    return skill_catalog.reload()


@app.get("/v1/skills/{skill_name}", dependencies=[Depends(verify_auth_token)])
async def get_skill(skill_name: str):
    skill = skill_catalog.get(skill_name)
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill.as_public_dict(include_instructions=True)


@app.post("/v1/tools/invoke", dependencies=[Depends(verify_auth_token)])
async def invoke_tool(req: InvokeToolRequest):
    result = await tool_registry.invoke(
        name=req.name,
        args=req.arguments,
        scope=req.scope,
        session_id=req.session_id
    )
    return result


# Permissions Management Endpoints
class GrantPermissionRequest(BaseModel):
    tool: str
    scope: str = "*"


@app.get("/v1/permissions", dependencies=[Depends(verify_auth_token)])
async def list_permissions():
    return await permission_store.list_permissions()


@app.post("/v1/permissions/grant", dependencies=[Depends(verify_auth_token)])
async def grant_permission(req: GrantPermissionRequest):
    await permission_store.grant(tool=req.tool, scope=req.scope)
    return {"success": True, "tool": req.tool, "scope": req.scope}


@app.post("/v1/permissions/revoke", dependencies=[Depends(verify_auth_token)])
async def revoke_permission(req: GrantPermissionRequest):
    await permission_store.revoke(tool=req.tool, scope=req.scope)
    return {"success": True, "tool": req.tool, "scope": req.scope}


# Audit Log Endpoints
@app.get("/v1/audit", dependencies=[Depends(verify_auth_token)])
async def get_audit_logs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    tool: str | None = None
):
    return await audit_log.list_logs(limit=limit, offset=offset, tool=tool)


# Agent & Inbox Subsystem Endpoints
class AgentExecuteRequest(BaseModel):
    task: str
    context: dict[str, Any] = {}
    task_id: str | None = None


@app.get("/v1/agents", dependencies=[Depends(verify_auth_token)])
async def list_agents():
    return [
        {
            "name": planning_agent.name,
            "description": planning_agent.description,
            "system_prompt": planning_agent.system_prompt,
            "allowed_tools": list(planning_agent.allowed_tools)
        },
        {
            "name": research_agent.name,
            "description": research_agent.description,
            "system_prompt": research_agent.system_prompt,
            "allowed_tools": list(research_agent.allowed_tools)
        },
        {
            "name": browser_agent.name,
            "description": browser_agent.description,
            "system_prompt": browser_agent.system_prompt,
            "allowed_tools": list(browser_agent.allowed_tools)
        },
        {
            "name": file_agent.name,
            "description": file_agent.description,
            "system_prompt": file_agent.system_prompt,
            "allowed_tools": list(file_agent.allowed_tools)
        },
        {
            "name": chat_agent.name,
            "description": chat_agent.description,
            "system_prompt": chat_agent.system_prompt,
            "allowed_tools": list(chat_agent.allowed_tools)
        }
    ]


@app.get("/v1/inbox", dependencies=[Depends(verify_auth_token)])
async def get_inbox_tasks(
    limit: int = Query(default=50, ge=1, le=100),
    agent_name: str | None = None,
    parent_task_id: str | None = None
):
    return await agent_inbox.list_tasks(limit=limit, agent_name=agent_name, parent_task_id=parent_task_id)


@app.post("/v1/agents/execute", dependencies=[Depends(verify_auth_token)])
async def execute_agent_goal(req: AgentExecuteRequest):
    result = await planning_agent.run(task=req.task, context=req.context, task_id=req.task_id)
    return result


# Chat Completions Request Body
class ChatRequest(BaseModel):
    session_id: str | None = None
    content: str
    stream: bool = True
    temperature: float = 0.7


@app.post("/v1/chat/completions", dependencies=[Depends(verify_auth_token)])
async def chat_endpoint(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    
    # Save user message
    user_msg = ChatMessage(
        session_id=session_id,
        role=MessageRole.USER,
        content=req.content
    )
    await memory_store.save_message(user_msg)

    # Load history
    history = await memory_store.get_messages(session_id=session_id, limit=20)

    # Route request
    model_messages = add_skill_context(history)
    provider, decision = await router.route(model_messages)

    # Check cache for Tier-1 command responses
    cached_reply = prompt_cache.get(req.content)
    if cached_reply:
        assistant_msg = ChatMessage(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=cached_reply,
            tier=decision.tier,
            model="cache/instant",
            metadata={"cached": True}
        )
        await memory_store.save_message(assistant_msg)
        return assistant_msg

    if not req.stream:
        assistant_msg = await provider.generate(
            messages=model_messages,
            model=decision.selected_model,
            temperature=req.temperature
        )
        assistant_msg.tier = decision.tier
        await memory_store.save_message(assistant_msg)
        return assistant_msg

    async def sse_generator():
        collected_chunks = []
        try:
            async for chunk in provider.stream(
                messages=model_messages,
                model=decision.selected_model,
                temperature=req.temperature
            ):
                collected_chunks.append(chunk)
                payload = {
                    "session_id": session_id,
                    "delta": chunk,
                    "tier": decision.tier.value,
                    "model": decision.selected_model,
                    "is_fallback": decision.is_fallback,
                    "done": False
                }
                yield f"data: {json.dumps(payload)}\n\n"

            full_reply = "".join(collected_chunks)
            assistant_msg = ChatMessage(
                session_id=session_id,
                role=MessageRole.ASSISTANT,
                content=full_reply,
                tier=decision.tier,
                model=decision.selected_model
            )
            await memory_store.save_message(assistant_msg)
            
            # Cache quick Tier 1 responses
            if decision.tier.value == "tier1_local" and len(req.content) < 50:
                prompt_cache.set(req.content, full_reply)

            yield f"data: {json.dumps({'session_id': session_id, 'delta': '', 'done': True})}\n\n"
        except Exception as e:
            logger.error(f"Error during streaming response: {e}")
            err_payload = {"error": str(e), "done": True}
            yield f"data: {json.dumps(err_payload)}\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


# WebSocket Control Plane
@app.websocket("/ws")
async def websocket_control_plane(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket client connected to JARVIS Control Plane")

    # Register broadcaster for confirmation requests
    async def send_to_client(frame: dict[str, Any]):
        try:
            await websocket.send_json(frame)
        except Exception:
            pass

    confirmation_bridge.register_broadcaster(send_to_client)

    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                msg = json.loads(raw_data)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "error": "Invalid JSON frame"})
                continue

            msg_type = msg.get("type", "")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong", "timestamp": time.time()})

            elif msg_type == "telemetry:poll":
                hw = get_hardware_telemetry()
                net = await network_monitor.check_connectivity()
                await websocket.send_json({
                    "type": "telemetry:update",
                    "hardware": hw.model_dump(),
                    "network": net.model_dump(),
                    "uptime_seconds": round(time.time() - START_TIME, 1),
                    "pendingConfirmations": confirmation_bridge.list_pending()
                })

            elif msg_type == "confirmation_response":
                cid = msg.get("confirmationId")
                approved = bool(msg.get("approved"))
                reason = msg.get("reason", "")
                if cid:
                    resolved = confirmation_bridge.resolve_confirmation(
                        confirmation_id=cid,
                        approved=approved,
                        reason=reason
                    )
                    await websocket.send_json({
                        "type": "confirmation_ack",
                        "confirmationId": cid,
                        "resolved": resolved
                    })

            elif msg_type == "chat:send":
                session_id = msg.get("sessionId") or str(uuid.uuid4())
                content = msg.get("content", "")
                
                user_msg = ChatMessage(
                    session_id=session_id,
                    role=MessageRole.USER,
                    content=content
                )
                await memory_store.save_message(user_msg)

                history = await memory_store.get_messages(session_id=session_id, limit=20)
                model_messages = add_skill_context(history)
                provider, decision = await router.route(model_messages)

                # Send routing event to client
                await websocket.send_json({
                    "type": "chat:routed",
                    "sessionId": session_id,
                    "tier": decision.tier.value,
                    "model": decision.selected_model,
                    "provider": decision.selected_provider,
                    "isFallback": decision.is_fallback,
                    "reason": decision.reason
                })

                # Stream response tokens
                collected_chunks = []
                try:
                    async for chunk in provider.stream(
                        messages=model_messages,
                        model=decision.selected_model
                    ):
                        collected_chunks.append(chunk)
                        await websocket.send_json({
                            "type": "chat:delta",
                            "sessionId": session_id,
                            "delta": chunk
                        })

                    full_reply = "".join(collected_chunks)
                    assistant_msg = ChatMessage(
                        session_id=session_id,
                        role=MessageRole.ASSISTANT,
                        content=full_reply,
                        tier=decision.tier,
                        model=decision.selected_model
                    )
                    await memory_store.save_message(assistant_msg)

                    await websocket.send_json({
                        "type": "chat:done",
                        "sessionId": session_id,
                        "message": assistant_msg.model_dump()
                    })
                except Exception as e:
                    logger.error(f"WS streaming error: {e}")
                    await websocket.send_json({
                        "type": "chat:error",
                        "sessionId": session_id,
                        "error": str(e)
                    })

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket session error: {e}")
    finally:
        confirmation_bridge.unregister_broadcaster(send_to_client)
