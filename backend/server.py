import asyncio
import base64
from contextlib import asynccontextmanager
import io
import json
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional, Set
from fastapi import FastAPI, File, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from backend.config import settings
from backend.telemetry import get_system_telemetry
from backend.memory import memory_store
from backend.tools import (
    confirmation_bridge,
    tool_system_telemetry,
    tool_launch_application,
    tool_run_shell_command,
    tool_take_screenshot,
    tool_get_active_window,
    tool_web_search
)
from backend.agent import jarvis_agent
from backend.voice import voice_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("jarvis.server")

START_TIME = time.time()
active_websockets: Set[WebSocket] = set()

# Broadcast telemetry every 1 second to active websockets
async def telemetry_broadcaster_task():
    while True:
        try:
            await asyncio.sleep(1.0)
            if active_websockets:
                telem = get_system_telemetry()
                msg = {
                    "type": "telemetry:update",
                    "hardware": telem["hardware"],
                    "network": telem["network"],
                    "uptime_seconds": round(time.time() - START_TIME, 1)
                }
                dead_sockets = set()
                for ws in list(active_websockets):
                    try:
                        await ws.send_json(msg)
                    except Exception:
                        dead_sockets.add(ws)
                active_websockets.difference_update(dead_sockets)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.debug(f"[Broadcaster] error: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting J.A.R.V.I.S Core Backend on {settings.HOST}:{settings.PORT}")
    await memory_store.init_db()
    
    # Broadcast callback for confirmation bridge
    async def bridge_sender(payload: dict):
        dead_sockets = set()
        for ws in list(active_websockets):
            try:
                await ws.send_json(payload)
            except Exception:
                dead_sockets.add(ws)
        active_websockets.difference_update(dead_sockets)

    confirmation_bridge.register_broadcaster(bridge_sender)
    telemetry_task = asyncio.create_task(telemetry_broadcaster_task())
    yield
    telemetry_task.cancel()
    confirmation_bridge.unregister_broadcaster(bridge_sender)

app = FastAPI(
    title="J.A.R.V.I.S Autonomous Core Backend",
    version="4.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "jarvis-core-service",
        "version": "4.0.0",
        "model_status": "ready" if jarvis_agent.is_configured() else "needs_key",
        "subsystems": {
            "telemetry": True,
            "agent": True,
            "voice": True,
            "tools": True
        },
        "uptime_seconds": round(time.time() - START_TIME, 1)
    }

@app.get("/telemetry")
async def telemetry_snapshot():
    telem = get_system_telemetry()
    return {
        "hardware": telem["hardware"],
        "network": telem["network"],
        "uptime_seconds": round(time.time() - START_TIME, 1)
    }

class SessionCreate(BaseModel):
    title: str = "New Session"

@app.get("/sessions")
async def list_sessions(limit: int = 50):
    return await memory_store.list_sessions(limit=limit)

@app.post("/sessions")
async def create_session(req: SessionCreate):
    session_id = f"session_{int(time.time()*1000)}"
    await memory_store.get_or_create_session(session_id, title=req.title)
    return {"id": session_id, "title": req.title}

@app.get("/sessions/{session_id}/messages")
async def get_messages(session_id: str, limit: int = 100):
    return await memory_store.get_messages(session_id=session_id, limit=limit)

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    await memory_store.clear_session(session_id)
    return {"success": True}

@app.get("/search")
async def search_messages(q: str = Query(..., min_length=1), limit: int = 20):
    return await memory_store.search_messages(query=q, limit=limit)

class EnvUpdateRequest(BaseModel):
    key: str
    value: str

@app.post("/api/env")
@app.put("/api/env")
async def update_env(req: EnvUpdateRequest):
    os.environ[req.key] = req.value
    if req.key == "GEMINI_API_KEY":
        jarvis_agent.update_api_key(req.value)
        # Also persist to root .env file
        try:
            env_path = settings.DATA_DIR.parent / ".env"
            lines = []
            if env_path.exists():
                lines = env_path.read_text(encoding="utf-8").splitlines()
            found = False
            new_lines = []
            for line in lines:
                if line.startswith(f"{req.key}="):
                    new_lines.append(f"{req.key}={req.value}")
                    found = True
                else:
                    new_lines.append(line)
            if not found:
                new_lines.append(f"{req.key}={req.value}")
            env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        except Exception as e:
            logger.warning(f"Could not persist key to .env: {e}")

    return {"success": True, "key": req.key}

@app.get("/api/env")
async def get_env_status():
    return {
        "GEMINI_API_KEY_CONFIGURED": jarvis_agent.is_configured(),
        "GEMINI_MODEL": settings.GEMINI_MODEL,
        "VOICE_NAME": settings.VOICE_NAME,
        "PORT": settings.PORT
    }

AVAILABLE_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "system_telemetry",
        "description": "Returns real-time hardware telemetry: CPU load, per-core utilization, RAM usage, storage stats, dynamic thermal metrics, and network rates.",
        "risk_level": "LOW",
        "parameters_schema": {}
    },
    {
        "name": "launch_application",
        "description": "Launches a native application or opens a URL on the host operating system.",
        "risk_level": "MEDIUM",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "The name or path of the application/executable, or URL"}
            },
            "required": ["name"]
        }
    },
    {
        "name": "run_shell_command",
        "description": "Executes a PowerShell or shell command with output capture and explicit security confirmation.",
        "risk_level": "HIGH",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The command line string to execute"}
            },
            "required": ["command"]
        }
    },
    {
        "name": "take_screenshot",
        "description": "Captures the current desktop screen and saves it as a PNG file.",
        "risk_level": "LOW",
        "parameters_schema": {}
    },
    {
        "name": "get_active_window",
        "description": "Retrieves the window title of the currently focused foreground window.",
        "risk_level": "LOW",
        "parameters_schema": {}
    },
    {
        "name": "web_search",
        "description": "Searches the web via DuckDuckGo and returns title, snippet, and link for top results.",
        "risk_level": "LOW",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query string"}
            },
            "required": ["query"]
        }
    }
]

granted_permissions: Set[str] = {"system_telemetry", "take_screenshot", "get_active_window", "web_search"}

@app.get("/v1/tools")
@app.get("/tools")
async def get_tools_route():
    return AVAILABLE_TOOLS

@app.post("/v1/tools/invoke")
@app.post("/tools/invoke")
async def invoke_tool_route(req: Dict[str, Any]):
    name = req.get("name")
    args = req.get("arguments", {})
    res = {}
    if name == "system_telemetry":
        res = await tool_system_telemetry()
    elif name == "launch_application":
        res = await tool_launch_application(args.get("name", ""))
    elif name == "run_shell_command":
        res = await tool_run_shell_command(args.get("command", ""))
    elif name == "take_screenshot":
        res = await tool_take_screenshot()
    elif name == "get_active_window":
        res = await tool_get_active_window()
    elif name == "web_search":
        res = await tool_web_search(args.get("query", ""))
    else:
        res = {"error": f"Unknown tool: {name}"}

    # Record persistent audit log for the HUD activity feed
    try:
        risk_level = "HIGH" if name in ["run_shell_command"] else "LOW"
        outcome = "ERROR" if "error" in str(res).lower() else "SUCCESS"
        await memory_store.log_audit(
            tool=str(name),
            args_summary=args,
            risk_level=risk_level,
            outcome=outcome,
            details={"result": str(res)[:300]}
        )
    except Exception as e:
        logger.debug(f"[Audit] error logging invoke: {e}")

    return res

@app.get("/v1/audit")
@app.get("/audit")
async def get_audit_route(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    tool: Optional[str] = Query(None)
):
    return await memory_store.get_audit_logs(limit=limit, offset=offset, tool=tool)

@app.get("/v1/permissions")
@app.get("/permissions")
async def get_permissions_route():
    return [
        {
            "tool": t["name"],
            "scope": "*",
            "granted": t["name"] in granted_permissions,
            "granted_at": int(START_TIME)
        }
        for t in AVAILABLE_TOOLS
    ]

@app.post("/v1/permissions/grant")
@app.post("/permissions/grant")
async def grant_permission_route(req: Dict[str, Any]):
    tool = req.get("tool")
    if tool:
        granted_permissions.add(tool)
    return {"success": True, "tool": tool, "granted": True}

@app.post("/v1/permissions/revoke")
@app.post("/permissions/revoke")
async def revoke_permission_route(req: Dict[str, Any]):
    tool = req.get("tool")
    if tool and tool in granted_permissions:
        granted_permissions.remove(tool)
    return {"success": True, "tool": tool, "granted": False}

@app.get("/v1/agents")
async def get_agents_route():
    return [
        {
            "name": "jarvis_core",
            "description": "Primary J.A.R.V.I.S. executive AI brain powered by Google Gemini",
            "system_prompt": "You are J.A.R.V.I.S., an advanced AI desktop operating partner.",
            "allowed_tools": [t["name"] for t in AVAILABLE_TOOLS]
        }
    ]

@app.get("/v1/inbox")
async def get_inbox_route():
    return []

@app.post("/v1/agents/execute")
async def execute_agent_goal_route(req: Dict[str, Any]):
    task = req.get("task", "")
    res = await jarvis_agent.generate_response(task)
    return {
        "agent_name": "jarvis_core",
        "success": True,
        "summary": res["text"]
    }

class ChatCompletionRequest(BaseModel):
    session_id: str | None = None
    content: str
    stream: bool = True

@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest):
    session_id = req.session_id or f"session_{int(time.time()*1000)}"
    
    async def sse_gen():
        queue = asyncio.Queue()
        
        def on_chunk(text: str):
            queue.put_nowait({"type": "chunk", "data": text})
            
        def on_tool(name: str, args: dict):
            queue.put_nowait({"type": "tool", "name": name, "args": args})

        async def worker():
            try:
                full_reply = await jarvis_agent.chat_stream(
                    session_id=session_id,
                    user_prompt=req.content,
                    on_chunk=on_chunk,
                    on_tool_start=on_tool
                )
                queue.put_nowait({"type": "done", "reply": full_reply})
            except Exception as e:
                queue.put_nowait({"type": "error", "error": str(e)})

        task = asyncio.create_task(worker())
        while True:
            item = await queue.get()
            if item["type"] == "chunk":
                payload = {"session_id": session_id, "delta": item["data"], "done": False}
                yield f"data: {json.dumps(payload)}\n\n"
            elif item["type"] == "done":
                payload = {"session_id": session_id, "delta": "", "done": True, "content": item["reply"]}
                yield f"data: {json.dumps(payload)}\n\n"
                break
            elif item["type"] == "error":
                yield f"data: {json.dumps({'error': item['error'], 'done': True})}\n\n"
                break
        await task

    return StreamingResponse(sse_gen(), media_type="text/event-stream")

class SpeechRequest(BaseModel):
    input: str
    voice: Optional[str] = None

@app.post("/v1/audio/speech")
async def audio_speech(req: SpeechRequest):
    synth = await voice_pipeline.synthesize(req.input, voice=req.voice)
    if not synth:
        raise HTTPException(status_code=500, detail="Speech synthesis failed")
    raw_audio = base64.b64decode(synth["audio_base64"])
    media_type = synth["mime_type"]
    return StreamingResponse(io.BytesIO(raw_audio), media_type=media_type)

@app.post("/v1/audio/transcriptions")
async def audio_transcriptions(
    file: Optional[UploadFile] = File(None)
):
    if not file:
        raise HTTPException(status_code=400, detail="No audio file provided")
    audio_bytes = await file.read()
    transcription = await voice_pipeline.transcribe_audio(audio_bytes, file.content_type or "audio/wav")
    return {"text": transcription}

# Core Real-Time WebSocket Control Plane
@app.websocket("/ws")
async def websocket_control_plane(ws: WebSocket):
    await ws.accept()
    active_websockets.add(ws)
    logger.info(f"[WS] Client connected. Active clients: {len(active_websockets)}")

    # Initial hello state
    try:
        telem = get_system_telemetry()
        await ws.send_json({
            "type": "telemetry:update",
            "hardware": telem["hardware"],
            "network": telem["network"],
            "uptime_seconds": round(time.time() - START_TIME, 1)
        })
        await ws.send_json({
            "type": "agent_state",
            "state": "idle"
        })
    except Exception:
        pass

    try:
        while True:
            raw_text = await ws.receive_text()
            try:
                frame = json.loads(raw_text)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "error": "Invalid JSON frame"})
                continue

            msg_type = frame.get("type", "")

            if msg_type == "ping":
                await ws.send_json({"type": "pong", "timestamp": time.time()})

            elif msg_type == "telemetry:poll":
                telem = get_system_telemetry()
                await ws.send_json({
                    "type": "telemetry:update",
                    "hardware": telem["hardware"],
                    "network": telem["network"],
                    "uptime_seconds": round(time.time() - START_TIME, 1)
                })

            elif msg_type == "confirmation_response":
                cid = frame.get("confirmationId")
                approved = bool(frame.get("approved"))
                reason = frame.get("reason", "")
                if cid:
                    resolved = confirmation_bridge.resolve(cid, approved, reason)
                    await ws.send_json({
                        "type": "confirmation_ack",
                        "confirmationId": cid,
                        "resolved": resolved
                    })

            elif msg_type == "audio_chunk":
                audio_b64 = frame.get("audioBase64", "")
                mtype = frame.get("mimeType", "audio/wav")
                session_id = frame.get("sessionId") or f"session_{int(time.time()*1000)}"
                if audio_b64:
                    try:
                        raw_bytes = base64.b64decode(audio_b64)
                        transcription = await voice_pipeline.transcribe_audio(raw_bytes, mtype)
                        await ws.send_json({
                            "type": "transcription_complete",
                            "sessionId": session_id,
                            "text": transcription
                        })
                    except Exception as e:
                        await ws.send_json({"type": "error", "error": f"STT failed: {str(e)}"})

            elif msg_type == "cancel_speech":
                voice_pipeline.cancel()
                await ws.send_json({"type": "agent_state", "state": "idle"})

            elif msg_type in ["user_message", "chat:send"]:
                session_id = frame.get("sessionId") or frame.get("session_id") or f"session_{int(time.time()*1000)}"
                content = frame.get("content", "").strip()

                if not content:
                    continue

                # Broadcast state transitions
                async def emit_state(st: str):
                    await ws.send_json({"type": "agent_state", "state": st})

                def on_state_sync(st: str):
                    asyncio.create_task(emit_state(st))

                def on_chunk_sync(chunk: str):
                    async def send_chunk():
                        await ws.send_json({
                            "type": "agent_stream_chunk",
                            "sessionId": session_id,
                            "delta": chunk
                        })
                        # Backwards compatibility event
                        await ws.send_json({
                            "type": "chat:delta",
                            "sessionId": session_id,
                            "delta": chunk
                        })
                    asyncio.create_task(send_chunk())

                def on_tool_start_sync(tool_name: str, args: dict):
                    async def send_tool_start():
                        await ws.send_json({
                            "type": "tool_call_start",
                            "sessionId": session_id,
                            "tool": tool_name,
                            "arguments": args
                        })
                    asyncio.create_task(send_tool_start())

                def on_tool_result_sync(tool_name: str, result: Any):
                    async def send_tool_result():
                        await ws.send_json({
                            "type": "tool_call_result",
                            "sessionId": session_id,
                            "tool": tool_name,
                            "result": result
                        })
                    asyncio.create_task(send_tool_result())

                # Notify client that request is routed
                await ws.send_json({
                    "type": "chat:routed",
                    "sessionId": session_id,
                    "model": settings.GEMINI_MODEL,
                    "provider": "google-genai",
                    "tier": "tier3_cloud" if jarvis_agent.is_configured() else "tier1_local",
                    "isFallback": not jarvis_agent.is_configured()
                })

                full_reply = await jarvis_agent.chat_stream(
                    session_id=session_id,
                    user_prompt=content,
                    on_state=on_state_sync,
                    on_chunk=on_chunk_sync,
                    on_tool_start=on_tool_start_sync,
                    on_tool_result=on_tool_result_sync
                )

                # Send finalized message complete event
                complete_msg = {
                    "id": f"msg_{int(time.time()*1000)}",
                    "session_id": session_id,
                    "role": "assistant",
                    "content": full_reply,
                    "created_at": time.time()
                }

                await ws.send_json({
                    "type": "agent_message_complete",
                    "sessionId": session_id,
                    "message": complete_msg
                })

                # Backwards compatible event
                await ws.send_json({
                    "type": "chat:done",
                    "sessionId": session_id,
                    "message": complete_msg
                })

                # Speech synthesis output
                try:
                    synth = await voice_pipeline.synthesize(full_reply[:250])
                    if synth:
                        await ws.send_json({
                            "type": "tts_playback",
                            "mimeType": synth["mime_type"],
                            "audioBase64": synth["audio_base64"],
                            "text": synth["text"]
                        })
                except Exception as tts_err:
                    logger.debug(f"[TTS] error: {tts_err}")

    except WebSocketDisconnect:
        active_websockets.discard(ws)
        logger.info(f"[WS] Client disconnected. Remaining: {len(active_websockets)}")
    except Exception as e:
        active_websockets.discard(ws)
        logger.error(f"[WS] Session exception: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.server:app", host=settings.HOST, port=settings.PORT, reload=False)
