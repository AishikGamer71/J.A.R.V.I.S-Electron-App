"""
J.A.R.V.I.S. Core REST & WebSocket Gateway
===========================================
Unified FastAPI entrypoint on 127.0.0.1:8765.
Provides full REST API endpoints, full-duplex WebSockets (/ws and /ws/jarvis),
bidirectional command routing, real-time token streaming from HermesBrain,
dual envelope formatting (WebSocketEnvelope and legacy jarvisBridge events),
background telemetry broadcasting, and graceful lifespan resource management.
"""

import asyncio
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Set, Union

from fastapi import (
    FastAPI,
    HTTPException,
    Query,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

# Core Subsystems
from backend.security.agent_shield import AgentShield
from backend.security.ecc_hooks import ECCHookDispatcher
from backend.memory.state_db import SessionDB
from backend.memory.instinct_engine import InstinctEngine
from backend.core.prompt_builder import PromptBuilder
from backend.core.context_compressor import ContextCompressor
from backend.core.tool_dispatcher import ToolDispatcher
from backend.core.hermes_brain import HermesBrain, BrainEvent
from backend.core.cron_scheduler import CronScheduler
from backend.engine.hardware_profiler import get_hardware_profiler
from backend.engine.telemetry_store import get_telemetry_store
from backend.hardware.power_guardian import get_power_guardian
from backend.engine.model_router import ModelRouter
from backend.memory.hybrid_rag import HybridMemory

# Optional Voice & Vision Imports
try:
    from backend.voice.audio_pipeline import AudioPipeline
except Exception:
    AudioPipeline = None

try:
    from backend.senses.camera_hub import CameraHub
except Exception:
    CameraHub = None

try:
    from backend.senses.mobilerun_service import MobileRunService
except Exception:
    MobileRunService = None

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jarvis.gateway")

SERVER_START_TIME = time.time()

# ------------------------------------------------------------------------------
# Initialize Subsystems
# ------------------------------------------------------------------------------
state_db = SessionDB()
agent_shield = AgentShield()
ecc_dispatcher = ECCHookDispatcher(shield=agent_shield)
tool_dispatcher = ToolDispatcher(shield=agent_shield, ecc_dispatcher=ecc_dispatcher)
context_compressor = ContextCompressor(state_db=state_db)
prompt_builder = PromptBuilder(shield=agent_shield)
instinct_engine = InstinctEngine()

hardware_profiler = get_hardware_profiler()
power_guardian = get_power_guardian()
telemetry_store = get_telemetry_store()
telemetry_store.set_power_guardian(power_guardian)
model_router = ModelRouter()
hybrid_memory = HybridMemory()

hermes_brain = HermesBrain(
    prompt_builder=prompt_builder,
    context_compressor=context_compressor,
    tool_dispatcher=tool_dispatcher,
    state_db=state_db,
    model_router=model_router,
)
cron_scheduler = CronScheduler()

audio_pipeline = AudioPipeline() if AudioPipeline else None
camera_hub = CameraHub() if CameraHub else None
mobilerun_service = MobileRunService() if MobileRunService else None


# ------------------------------------------------------------------------------
# Pydantic Schemas & Contracts
# ------------------------------------------------------------------------------
class HealthResponse(BaseModel):
    status: str = "healthy"
    service: str = "jarvis-core-service"
    version: str = "2.0.0"
    model_status: str = "ready"
    engine: str = "local_heuristic"
    voice: str = "standby"
    vision: str = "ready"
    mobile: str = "ready"
    uptime_seconds: float = 0.0
    subsystems: Dict[str, Any] = Field(default_factory=dict)


class SystemStatsResponse(BaseModel):
    cpu_pct: float = 0.0
    ram_used_mb: float = 0.0
    ram_total_mb: float = 0.0
    gpu_pct: float = 0.0
    power: Dict[str, Any] = Field(default_factory=dict)


class ToolInvokeRequest(BaseModel):
    tool: Optional[str] = None
    name: Optional[str] = None
    args: Optional[Dict[str, Any]] = None
    arguments: Optional[Dict[str, Any]] = None
    scope: Optional[str] = "*"


class ToolInvokeResponse(BaseModel):
    result: Any = None
    status: str = "success"
    success: bool = True
    error: Optional[str] = None


class WebSocketEnvelope(BaseModel):
    type: str
    payload: Any
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    correlation_id: Optional[str] = None
    request_id: Optional[str] = None


class EnvPayload(BaseModel):
    env: Dict[str, Any] = Field(default_factory=dict)


class CoreMemoryPayload(BaseModel):
    fact: Optional[str] = None
    category: Optional[str] = "general"
    content: Optional[str] = None


class PermissionGrantPayload(BaseModel):
    tool: str
    scope: Optional[str] = "*"


class AgentExecutePayload(BaseModel):
    task: str
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    agent_name: Optional[str] = "planner"


# ------------------------------------------------------------------------------
# Connection Manager & Telemetry Broadcaster
# ------------------------------------------------------------------------------
class ConnectionManager:
    """Manages concurrent WebSocket clients with safe broadcasting and prune-on-disconnect."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
        logger.info("WebSocket connected. Total active: %d", len(self.active_connections))

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info("WebSocket disconnected. Total active: %d", len(self.active_connections))

    async def broadcast(self, message: Dict[str, Any]):
        async with self._lock:
            targets = list(self.active_connections)
        for connection in targets:
            try:
                await connection.send_json(message)
            except Exception:
                await self.disconnect(connection)

    async def close_all(self):
        async with self._lock:
            targets = list(self.active_connections)
            self.active_connections.clear()
        for conn in targets:
            try:
                await conn.close(code=1000)
            except Exception:
                pass


manager = ConnectionManager()
telemetry_broadcast_task: Optional[asyncio.Task] = None


async def _telemetry_broadcast_loop():
    """1.0s periodic telemetry broadcast for active UI components."""
    while True:
        try:
            await asyncio.sleep(1.0)
            if manager.active_connections:
                # 1. Unified Contract Envelope
                envelope = telemetry_store.format_system_metrics_envelope()
                await manager.broadcast(envelope)
                # 2. Legacy Bridge Envelope
                legacy = telemetry_store.format_legacy_telemetry()
                await manager.broadcast(legacy)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.debug("Telemetry broadcast error: %s", e)


# ------------------------------------------------------------------------------
# Lifespan Context Manager
# ------------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global telemetry_broadcast_task
    logger.info("Initializing J.A.R.V.I.S. Core Gateway background services...")
    power_guardian.start()
    telemetry_store.start_sampling(interval_sec=1.0)
    cron_scheduler.start()
    telemetry_broadcast_task = asyncio.create_task(_telemetry_broadcast_loop())
    yield
    logger.info("Shutting down J.A.R.V.I.S. Core Gateway background services...")
    if telemetry_broadcast_task and not telemetry_broadcast_task.done():
        telemetry_broadcast_task.cancel()
        try:
            await telemetry_broadcast_task
        except asyncio.CancelledError:
            pass
    cron_scheduler.stop()
    telemetry_store.stop_sampling()
    power_guardian.stop()
    state_db.close()
    hybrid_memory.close()
    await manager.close_all()


# ------------------------------------------------------------------------------
# FastAPI Application & Middleware
# ------------------------------------------------------------------------------
app = FastAPI(
    title="J.A.R.V.I.S. Core Gateway",
    description="Unified REST & WebSocket Gateway for J.A.R.V.I.S. Desktop System",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled gateway error on %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": str(exc), "code": "INTERNAL_GATEWAY_ERROR"},
    )


# ------------------------------------------------------------------------------
# WebSocket Command Handlers
# ------------------------------------------------------------------------------
async def handle_system_toggle(payload: Any) -> Dict[str, Any]:
    return {"status": "ok", "toggled": True, "active": True}


async def handle_vision_mode(payload: Any) -> Dict[str, Any]:
    mode = payload.get("mode") if isinstance(payload, dict) else payload
    return {"status": "ok", "mode": mode or "camera"}


async def handle_audio_control(payload: Any) -> Dict[str, Any]:
    action = payload.get("action") if isinstance(payload, dict) else payload
    if action == "cancel_speech":
        hermes_brain.interrupt("Audio control cancel speech")
        return {"status": "ok", "action": "cancelled"}
    return {"status": "ok", "action": action or "received"}


async def handle_reset_abort(payload: Any) -> Dict[str, Any]:
    hermes_brain.interrupt("Client emergency reset abort")
    hermes_brain.reset_interrupt()
    return {"status": "ok", "abort_reset": True}


async def handle_user_message(payload: Any) -> Dict[str, Any]:
    return {"status": "ok", "received": True}


async def handle_telemetry_poll(payload: Any) -> Dict[str, Any]:
    return telemetry_store.format_system_stats()


WS_COMMAND_HANDLERS: Dict[str, Any] = {
    "system.toggle": handle_system_toggle,
    "vision.mode": handle_vision_mode,
    "audio.control": handle_audio_control,
    "reset_abort": handle_reset_abort,
    "user.message": handle_user_message,
    "telemetry:poll": handle_telemetry_poll,
}


# ------------------------------------------------------------------------------
# REST Endpoints
# ------------------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse)
@app.get("/api/health", response_model=HealthResponse)
async def get_health() -> Dict[str, Any]:
    now = time.time()
    return {
        "status": "healthy",
        "service": "jarvis-core-service",
        "version": "2.0.0",
        "model_status": "ready",
        "engine": getattr(model_router, "active_engine", "local_heuristic"),
        "voice": "active" if audio_pipeline else "standby",
        "vision": "ready" if camera_hub else "mock",
        "mobile": "ready" if mobilerun_service else "mock",
        "uptime_seconds": round(now - SERVER_START_TIME, 2),
        "subsystems": {
            "brain": "online",
            "shield": "active",
            "state_db": "wal_ready",
            "telemetry": "sampling",
            "power": power_guardian.get_power_status().to_dict(),
        },
    }


@app.get("/api/system/stats", response_model=SystemStatsResponse)
@app.get("/system/stats", response_model=SystemStatsResponse)
async def get_system_stats() -> Dict[str, Any]:
    return telemetry_store.format_system_stats()


@app.get("/api/env")
async def get_env() -> Dict[str, Any]:
    safe_keys = ["OLLAMA_BASE_URL", "CHROME_CDP_URL", "ANDROID_DEVICE_IP", "MODEL_ROUTING_POLICY"]
    env_data = {k: os.environ.get(k, "") for k in safe_keys}
    return {"status": "ready", "env": env_data}


@app.post("/api/env")
async def post_env(payload: EnvPayload) -> Dict[str, Any]:
    for k, v in payload.env.items():
        if isinstance(k, str) and isinstance(v, (str, int, float, bool)):
            os.environ[k] = str(v)
    return {"status": "updated", "env": payload.env}


@app.get("/api/history")
async def get_history() -> Dict[str, Any]:
    sessions = state_db.list_sessions(limit=1)
    if sessions:
        session_id = sessions[0]["id"]
        msgs = state_db.get_messages(session_id, limit=100)
        return {"history": msgs, "session_id": session_id}
    return {"history": [], "session_id": "default"}


@app.post("/api/history/clear")
async def clear_history() -> Dict[str, Any]:
    sessions = state_db.list_sessions(limit=50)
    for s in sessions:
        state_db.delete_session(s["id"])
    return {"status": "cleared"}


@app.get("/sessions")
@app.get("/api/sessions")
async def list_sessions() -> List[Dict[str, Any]]:
    return state_db.list_sessions(limit=50)


@app.post("/sessions")
async def create_session(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    title = (payload or {}).get("title", "New Session")
    sid = state_db.create_session(title=title)
    return {"session_id": sid, "title": title}


@app.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    return state_db.get_messages(session_id, limit=limit)


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str) -> Dict[str, str]:
    state_db.delete_session(session_id)
    return {"status": "deleted", "session_id": session_id}


@app.get("/search")
async def search(q: str = Query("")) -> Dict[str, Any]:
    fts_results = state_db.search_fts(q, limit=20)
    hybrid_results = hybrid_memory.search(q, top_k=10)
    return {"query": q, "results": fts_results, "hybrid_hits": hybrid_results}


@app.get("/v1/tools")
async def get_tools() -> Dict[str, List[Any]]:
    return {"tools": tool_dispatcher.get_tool_definitions()}


@app.post("/v1/tools/invoke", response_model=ToolInvokeResponse)
async def invoke_tool(req: ToolInvokeRequest) -> Dict[str, Any]:
    tool_name = req.tool or req.name
    tool_args = req.args if req.args is not None else (req.arguments or {})
    if not tool_name:
        raise HTTPException(status_code=400, detail="Missing tool name")
    try:
        result = tool_dispatcher.dispatch(tool_name, tool_args)
        return {"result": result, "status": "success", "success": True, "error": None}
    except Exception as e:
        logger.warning("Tool invocation failed: %s -> %s", tool_name, e)
        return {"result": None, "status": "failed", "success": False, "error": str(e)}


@app.get("/v1/core-memory")
async def get_core_memory() -> Dict[str, Any]:
    return {
        "soul": prompt_builder.load_soul_md(),
        "user": prompt_builder.load_user_md(),
        "memory": prompt_builder.load_memory_md(),
        "instincts": instinct_engine.get_active_instincts(),
    }


@app.post("/v1/core-memory")
async def update_core_memory(payload: CoreMemoryPayload) -> Dict[str, Any]:
    fact_text = payload.fact or payload.content or ""
    if fact_text:
        doc_id = f"mem-{uuid.uuid4().hex[:8]}"
        hybrid_memory.index_text(doc_id=doc_id, text=fact_text, metadata={"category": payload.category or "general"})
    return {"status": "updated", "success": True}


@app.get("/v1/audit")
async def get_audit(limit: int = 50, offset: int = 0, tool: Optional[str] = None) -> Dict[str, Any]:
    all_logs = agent_shield.audit_logs
    if tool:
        all_logs = [x for x in all_logs if x.get("tool") == tool]
    sliced = all_logs[offset : offset + limit]
    return {
        "audit_log": sliced,
        "security_score": agent_shield.get_security_score(),
        "total_records": len(all_logs),
    }


@app.get("/v1/permissions")
async def get_permissions() -> Dict[str, Any]:
    tools = tool_dispatcher.get_tool_definitions()
    perms: Dict[str, Any] = {}
    for t in tools:
        if not isinstance(t, dict):
            continue
        tool_name = t.get("name") or t.get("function", {}).get("name")
        if tool_name:
            perms[tool_name] = {
                "scope": "*",
                "granted": True,
                "risk_level": t.get("risk_level") or t.get("function", {}).get("risk_level", "LOW"),
            }
    return {"permissions": perms}


@app.post("/v1/permissions/grant")
async def grant_permission(payload: PermissionGrantPayload) -> Dict[str, Any]:
    return {"status": "granted", "tool": payload.tool, "scope": payload.scope, "success": True}


@app.post("/v1/permissions/revoke")
async def revoke_permission(payload: PermissionGrantPayload) -> Dict[str, Any]:
    return {"status": "revoked", "tool": payload.tool, "scope": payload.scope, "success": True}


@app.get("/v1/agents")
async def get_agents() -> List[Dict[str, Any]]:
    return [
        {"name": "planner", "description": "Goal decomposition and architectural execution planning", "status": "idle"},
        {"name": "architect", "description": "System design and invariant boundary auditing", "status": "idle"},
        {"name": "security_auditor", "description": "Threat modeling and AgentShield ECC auditing", "status": "idle"},
        {"name": "gpt_researcher", "description": "Multi-source academic and web research engine", "status": "idle"},
        {"name": "agent_s3", "description": "OSWorld desktop automation and Windows GUI grounding", "status": "idle"},
        {"name": "browser_use", "description": "Headless CDP browser automation runner", "status": "idle"},
        {"name": "mobilerun", "description": "Wireless Android ADB and Portal bridge", "status": "idle"},
    ]


@app.post("/v1/agents/execute")
async def execute_agent_goal(payload: AgentExecutePayload) -> Dict[str, Any]:
    summary = await hermes_brain.delegate_task(goal=payload.task, role=payload.agent_name or "planner")
    return {
        "agent_name": payload.agent_name or "planner",
        "success": True,
        "summary": summary,
        "output_data": {},
        "error": None,
    }


@app.get("/v1/inbox")
async def get_inbox() -> Dict[str, Any]:
    return {"inbox": cron_scheduler.get_inbox_items()}


@app.post("/v1/chat/completions")
async def chat_completions_sse(request: Request):
    body = await request.json()
    session_id = body.get("session_id", "default")
    content = body.get("content", "")

    async def sse_stream():
        async for event in hermes_brain.run_turn(session_id=session_id, user_message=content):
            if event.event_type == "agent.token":
                chunk = json.dumps({"delta": event.payload.get("token", ""), "model": "hermes-brain", "tier": "tier1_local", "done": False})
                yield f"data: {chunk}\n\n"
            elif event.event_type == "agent.complete":
                chunk = json.dumps({"delta": "", "model": "hermes-brain", "tier": "tier1_local", "done": True})
                yield f"data: {chunk}\n\n"

    return StreamingResponse(sse_stream(), media_type="text/event-stream")


# ------------------------------------------------------------------------------
# Full-Duplex WebSocket Endpoint (/ws & /ws/jarvis)
# ------------------------------------------------------------------------------
@app.websocket("/ws")
@app.websocket("/ws/jarvis")
async def websocket_gateway(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                data = json.loads(raw_text)
            except Exception:
                await websocket.send_json({"type": "error", "payload": {"message": "Malformed JSON payload"}, "timestamp": datetime.now(timezone.utc).isoformat()})
                continue

            if not isinstance(data, dict):
                await websocket.send_json({"type": "error", "payload": {"message": "Envelope must be a JSON object"}, "timestamp": datetime.now(timezone.utc).isoformat()})
                continue

            msg_type = data.get("type", "")
            req_id = data.get("request_id") or data.get("correlation_id") or f"req-{uuid.uuid4().hex[:6]}"
            payload = data.get("payload") if "payload" in data else data

            # 1. Emergency Abort & Barge-In
            if msg_type in ("reset_abort", "voice:stop", "barge_in") or (
                msg_type == "audio.control" and isinstance(payload, dict) and payload.get("action") == "cancel_speech"
            ):
                hermes_brain.interrupt("Client requested abort/cancel speech")
                await websocket.send_json({
                    "type": "audio.control.ack",
                    "request_id": req_id,
                    "payload": {"status": "interrupted"},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                continue

            # 2. User Message -> HermesBrain Turn Execution
            if msg_type in ("user.message", "chat:send"):
                user_text = ""
                session_id = "default"
                if isinstance(payload, dict):
                    user_text = payload.get("content") or payload.get("text") or ""
                    session_id = payload.get("session_id") or payload.get("sessionId") or "default"
                elif isinstance(payload, str):
                    user_text = payload

                if not user_text and isinstance(data, dict):
                    user_text = data.get("content", "")
                    session_id = data.get("session_id", "default")

                # Stream HermesBrain response turn
                async for event in hermes_brain.run_turn(session_id=session_id, user_message=user_text):
                    # Unified Envelope
                    await websocket.send_json({
                        "type": event.event_type,
                        "request_id": req_id,
                        "payload": event.payload,
                        "timestamp": event.timestamp,
                    })

                    # Legacy Bridge Broadcasts
                    if event.event_type == "agent.state":
                        st = str(event.payload.get("state", "IDLE")).upper()
                        await websocket.send_json({
                            "type": "voice_state",
                            "state": st,
                            "amplitude": 0.0,
                            "is_speaking": st == "SPEAKING",
                        })
                    elif event.event_type == "agent.complete":
                        await websocket.send_json({
                            "type": "agent_response",
                            "session_id": session_id,
                            "content": event.payload.get("response", ""),
                            "timestamp": int(time.time() * 1000),
                        })
                continue

            # 3. Registered Command Handlers
            handler = WS_COMMAND_HANDLERS.get(msg_type)
            if handler:
                result = await handler(payload)
                await websocket.send_json({
                    "type": f"{msg_type}.ack",
                    "request_id": req_id,
                    "payload": result,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                continue

            # 4. Fallback Acknowledgment
            await websocket.send_json({
                "type": "agent.state",
                "request_id": req_id,
                "payload": {"state": "idle", "echo": data},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        logger.warning("WebSocket exception: %s", e)
        await manager.disconnect(websocket)



# ------------------------------------------------------------------------------
# Server Entrypoint
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8765, reload=True)
