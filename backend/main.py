"""
backend/main.py
FastAPI Server & Real-time WebSocket Hub for J.A.R.V.I.S Desktop Application.
Manages WebSocket (ws://127.0.0.1:8765/ws and /ws/jarvis), power guardian,
agent loop, voice state, and REST gateway contracts for the restored UI.
"""

import asyncio
import base64
import json
import logging
import os
import re
import time
import uuid
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Set, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.config import settings
import native_core
from backend.core.agent_loop import ai_agent
from backend.core.tool_registry import tool_registry
from backend.core.skill_and_cron import cron_scheduler, skill_loader
from backend.audio.omnivoice_tts import omnivoice_tts
from backend.audio.voice_ears import voice_ears
from backend.hardware.power_guardian import power_guardian
from backend.memory.state_store import state_store
from backend.memory.instinct_learner import instinct_learner
from backend.security.agent_shield import AgentShield

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("jarvis.server")

START_TIME = time.time()
active_websockets: Set[WebSocket] = set()


def build_telemetry_payload(metrics: Dict[str, Any]) -> Dict[str, Any]:
    hw = {
        "cpu_percent": metrics.get("cpu_percent", 0.0),
        "ram_percent": metrics.get("ram_percent", 0.0),
        "ram_used_gb": metrics.get("ram_used_gb", 0.0),
        "ram_total_gb": metrics.get("ram_total_gb", 16.0),
        "battery_percent": metrics.get("battery_percent", 100),
        "battery_charging": metrics.get("battery_charging", False),
        "ac_plugged_in": metrics.get("ac_plugged_in", True),
        "charger_state_changed": metrics.get("charger_state_changed", False),
        "system_tier": "mid"
    }
    net = {
        "is_online": True,
        "latency_ms": 12,
        "rate": 1.2,
        "tx": 35,
        "rx": 42
    }
    return {
        "hardware": hw,
        "network": net,
        "timestamp": metrics.get("timestamp", time.time()),
        "uptime_seconds": round(time.time() - START_TIME, 1)
    }


# Asynchronous Lifecycle Context
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing J.A.R.V.I.S Backend Systems...")
    settings.ensure_directories()

    # 1. Start Hardware Power Guardian (polls Win32 power status)
    power_guardian.start()

    # Wire Power Guardian telemetry to WebSocket broadcast
    def on_telemetry(metrics: Dict[str, Any]):
        t_data = build_telemetry_payload(metrics)
        # Dual-broadcast for jarvisBridge and gatewayClient
        asyncio.create_task(broadcast_json({
            "type": "telemetry",
            "hardware": t_data["hardware"],
            "network": t_data["network"],
            "timestamp": t_data["timestamp"]
        }))
        asyncio.create_task(broadcast_json({
            "type": "system.metrics",
            "payload": {
                "hardware": t_data["hardware"],
                "network": t_data["network"],
                "uptime_seconds": t_data["uptime_seconds"]
            }
        }))

    def on_power_alert(level: str, msg: str):
        asyncio.create_task(broadcast_json({
            "type": "terminal_log",
            "level": level.lower(),
            "message": msg,
            "timestamp": time.time()
        }))

    power_guardian.add_telemetry_listener(on_telemetry)
    power_guardian.add_alert_listener(on_power_alert)

    # 2. Wire OmniVoice amplitude to ArcReactor / Sphere WebSocket broadcast
    _last_emitted_state = None
    _last_emitted_amp = 0.0

    def on_voice_amplitude(amplitude: float, state: str):
        nonlocal _last_emitted_state, _last_emitted_amp
        # Do not flood WebSocket when idle and amplitude is zero
        if state == "IDLE" and amplitude == 0.0 and _last_emitted_state == "IDLE":
            return
        _last_emitted_state = state
        _last_emitted_amp = amplitude

        asyncio.create_task(broadcast_json({
            "type": "voice_state",
            "state": state,
            "amplitude": round(amplitude, 3),
            "is_speaking": state == "SPEAKING"
        }))
        asyncio.create_task(broadcast_json({
            "type": "agent.state",
            "state": state.lower(),
            "payload": {
                "state": state.lower()
            }
        }))

    omnivoice_tts.add_amplitude_listener(on_voice_amplitude)

    # 3. Wire VoiceEars wake word detection to WebSocket broadcast
    def on_wake_detected():
        asyncio.create_task(broadcast_json({
            "type": "wake_word_detected",
            "event": "wake_word_detected",
            "wake_word": settings.WAKE_WORD,
            "timestamp": time.time()
        }))
        asyncio.create_task(broadcast_json({
            "type": "terminal_log",
            "level": "info",
            "message": f"Wake word '{settings.WAKE_WORD.upper()}' detected.",
            "timestamp": time.time()
        }))

    voice_ears.on_wake(on_wake_detected)

    # 4. Wire Cron Scheduler
    await cron_scheduler.start()

    # 5. Generate reference audio in background if missing
    asyncio.create_task(omnivoice_tts.ensure_reference_audio())

    logger.info("J.A.R.V.I.S Core Online on http://127.0.0.1:8765")
    yield

    logger.info("Shutting down J.A.R.V.I.S Backend Systems...")
    power_guardian.stop()
    await cron_scheduler.stop()
    omnivoice_tts.stop()


app = FastAPI(title="J.A.R.V.I.S Desktop AI Core", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def broadcast_json(message: Dict[str, Any]) -> None:
    """Broadcasts a JSON envelope to all active WebSocket clients."""
    if not active_websockets:
        return
    dead = set()
    for ws in list(active_websockets):
        try:
            await ws.send_json(message)
        except Exception:
            dead.add(ws)
    active_websockets.difference_update(dead)


# REST Endpoints
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "jarvis-core-service",
        "model_status": "online",
        "subsystems": {
            "native_core": "active",
            "power_guardian": "running",
            "agent_loop": "ready"
        },
        "app": "J.A.R.V.I.S Desktop AI",
        "version": "1.0.0",
        "uptime_seconds": round(time.time() - START_TIME, 1)
    }


class EnvUpdateRequest(BaseModel):
    key: str
    value: str


@app.get("/api/env")
async def get_env_status():
    """Returns availability of configured neural backends without leaking keys."""
    return {
        "GEMINI_API_KEY": bool(settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")),
        "OPENAI_API_KEY": bool(settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY")),
        "OLLAMA_AVAILABLE": True,
        "WAKE_WORD": settings.WAKE_WORD
    }


@app.post("/api/env")
async def update_env(req: EnvUpdateRequest):
    """Updates an environment variable dynamically and syncs to .env and inference_router."""
    os.environ[req.key] = req.value
    if req.key == "GEMINI_API_KEY":
        settings.GEMINI_API_KEY = req.value
        from backend.engine.inference_router import inference_router
        inference_router.update_keys(gemini_key=req.value)
    elif req.key == "OPENAI_API_KEY":
        settings.OPENAI_API_KEY = req.value
        from backend.engine.inference_router import inference_router
        inference_router.update_keys(openai_key=req.value)
    elif req.key == "WAKE_WORD":
        settings.WAKE_WORD = req.value
        voice_ears.update_wake_word(req.value)

    # Persist to .env file
    env_file = settings.ROOT_DIR / ".env"
    lines = []
    if env_file.exists():
        lines = env_file.read_text(encoding="utf-8").splitlines()

    key_found = False
    new_lines = []
    for line in lines:
        if line.startswith(f"{req.key}=") or line.startswith(f"#{req.key}="):
            new_lines.append(f"{req.key}={req.value}")
            key_found = True
        else:
            new_lines.append(line)
    if not key_found:
        new_lines.append(f"{req.key}={req.value}")

    env_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return {"success": True, "key": req.key}


@app.get("/api/system/stats")
async def get_system_stats():
    raw = await asyncio.to_thread(native_core.poll_power_and_metrics)
    ram_used = raw.get("ram_used_gb", 0.0)
    ram_total = raw.get("ram_total_gb", 16.0)
    ram_free = max(0.0, ram_total - ram_used)
    return {
        "cpu": f"{raw.get('cpu_percent', 0.0):.1f}%",
        "memory": {
            "total": f"{ram_total:.1f} GB",
            "free": f"{ram_free:.1f} GB",
            "usedPercentage": f"{raw.get('ram_percent', 0.0):.1f}%"
        },
        "temperature": 42.0,
        "os": {
            "type": "Windows_NT",
            "uptime": f"{round(time.time() - START_TIME)}s"
        },
        **raw
    }


@app.get("/api/history")
async def get_chat_history(session_id: str = Query("default"), limit: int = 50):
    return state_store.get_session_messages(session_id=session_id, limit=limit)


@app.post("/api/history/clear")
async def clear_history(session_id: str = Query("default")):
    state_store.clear_session(session_id)
    return {"success": True}


# GatewayClient Compatibility REST Endpoints
@app.get("/sessions")
async def get_sessions():
    return state_store.list_sessions()


@app.get("/sessions/{session_id}/messages")
async def get_session_messages_endpoint(session_id: str, limit: int = 100):
    msgs = state_store.get_session_messages(session_id=session_id, limit=limit)
    return [
        {
            "id": m.get("id", str(uuid.uuid4())),
            "session_id": session_id,
            "role": "assistant" if m.get("role") in ("model", "assistant") else "user",
            "content": m.get("content", ""),
            "created_at": m.get("timestamp", time.time())
        }
        for m in msgs
    ]


@app.delete("/sessions/{session_id}")
async def delete_session_endpoint(session_id: str):
    state_store.clear_session(session_id)
    return {"success": True}


@app.get("/search")
async def search_messages_endpoint(q: str = Query("")):
    results = state_store.search_memories(query=q)
    return [
        {
            "id": r.get("id", str(uuid.uuid4())),
            "session_id": r.get("session_id", "default"),
            "role": "assistant" if r.get("role") in ("model", "assistant") else "user",
            "content": r.get("content", ""),
            "created_at": r.get("timestamp", time.time())
        }
        for r in results
    ]


@app.get("/v1/tools")
async def get_tools_endpoint():
    tools = tool_registry.list_schemas()
    return [
        {
            "name": t.get("name"),
            "description": t.get("description"),
            "risk_level": "LOW",
            "parameters_schema": t.get("parameters", {}),
            "requires_confirmation": False
        }
        for t in tools
    ]


@app.post("/v1/tools/invoke")
async def invoke_tool_endpoint(req: Dict[str, Any]):
    name = req.get("name", "")
    args = req.get("arguments", {})
    res = await tool_registry.execute(name, args)
    return res


@app.get("/v1/core-memory")
async def get_core_memory_endpoint(limit: int = 50):
    instincts = instinct_learner.get_all_instincts()
    return [
        {
            "fact": f"{i.get('trigger')} -> {i.get('action')}",
            "category": i.get("domain", "general"),
            "confidence": i.get("confidence", 1.0)
        }
        for i in instincts[:limit]
    ]


@app.post("/v1/core-memory")
async def save_core_memory_endpoint(req: Dict[str, Any]):
    fact = req.get("fact", "")
    instinct_learner.learn_from_feedback(fact, was_success=True)
    return {"success": True}


@app.get("/v1/audit")
async def get_audit_endpoint(limit: int = 50, offset: int = 0, tool: Optional[str] = None):
    return []


@app.get("/v1/permissions")
async def get_permissions_endpoint():
    return []


@app.get("/v1/agents")
async def get_agents_endpoint():
    return [
        {"name": "SystemSupervisor", "role": "Architect", "status": "active", "description": "Primary task planner and system orchestrator"},
        {"name": "AgentS3", "role": "ComputerUse", "status": "active", "description": "Autonomous Windows GUI automation with OSWorldACI grounding"},
        {"name": "PowerGuardian", "role": "HardwareWatchdog", "status": "active", "description": "1ms charger unplug and battery monitor"}
    ]


@app.get("/v1/inbox")
async def get_inbox_endpoint(limit: int = 50, agent_name: Optional[str] = None):
    return []


# WebSocket Hub supporting both /ws and /ws/jarvis
@app.websocket("/ws")
@app.websocket("/ws/jarvis")
async def websocket_hub(websocket: WebSocket):
    await websocket.accept()
    active_websockets.add(websocket)
    logger.info(f"[WebSocket] Client connected: {websocket.client}")

    # Immediately push initial telemetry frame (both envelopes)
    initial_metrics = await asyncio.to_thread(native_core.poll_power_and_metrics)
    t_data = build_telemetry_payload(initial_metrics)
    await websocket.send_json({
        "type": "telemetry",
        "hardware": t_data["hardware"],
        "network": t_data["network"],
        "timestamp": t_data["timestamp"]
    })
    await websocket.send_json({
        "type": "system.metrics",
        "payload": {
            "hardware": t_data["hardware"],
            "network": t_data["network"],
            "uptime_seconds": t_data["uptime_seconds"]
        }
    })

    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                data = json.loads(raw_text)
            except Exception:
                continue

            msg_type = data.get("type", "") or data.get("action", "")

            # Heartbeat Ping/Pong
            if msg_type in ("ping", "heartbeat"):
                await websocket.send_json({"type": "pong", "timestamp": time.time()})
                continue

            # Telemetry Poll
            elif msg_type in ("telemetry:poll", "poll:telemetry"):
                metrics = await asyncio.to_thread(native_core.poll_power_and_metrics)
                t_poll = build_telemetry_payload(metrics)
                await websocket.send_json({
                    "type": "telemetry",
                    "hardware": t_poll["hardware"],
                    "network": t_poll["network"],
                    "timestamp": t_poll["timestamp"]
                })
                await websocket.send_json({
                    "type": "system.metrics",
                    "payload": {
                        "hardware": t_poll["hardware"],
                        "network": t_poll["network"],
                        "uptime_seconds": t_poll["uptime_seconds"]
                    }
                })
                continue

            # User Chat Message
            elif msg_type in ("user.message", "chat:send", "command", "text"):
                text = (
                    data.get("content")
                    or data.get("text")
                    or data.get("payload", {}).get("content", "")
                )
                session_id = (
                    data.get("session_id")
                    or data.get("sessionId")
                    or data.get("payload", {}).get("session_id", "default")
                )
                model = data.get("model") or settings.GEMINI_MODEL

                if not text or not text.strip():
                    continue

                # Barge-in: interrupt any speaking audio
                voice_ears.trigger_barge_in()

                # Broadcast live terminal log: user query
                await broadcast_json({
                    "type": "terminal_log",
                    "level": "info",
                    "message": f"Query: {text}",
                    "timestamp": time.time()
                })

                # Log forwarder callback for live agent steps
                def on_agent_log(lvl: str, log_msg: str):
                    asyncio.create_task(broadcast_json({
                        "type": "terminal_log",
                        "level": lvl,
                        "message": log_msg,
                        "timestamp": time.time()
                    }))

                # Run autonomous agent turn
                agent_res = await ai_agent.run_conversation(
                    user_message=text,
                    session_id=session_id,
                    model=model,
                    on_log=on_agent_log
                )

                reply_text = agent_res.get("response", "")

                # Broadcast responses in both protocols
                await broadcast_json({
                    "type": "agent_response",
                    "session_id": session_id,
                    "content": reply_text,
                    "model": agent_res.get("model"),
                    "tool_executed": agent_res.get("tool_executed"),
                    "timestamp": time.time()
                })
                await broadcast_json({
                    "type": "agent.complete",
                    "session_id": session_id,
                    "content": reply_text,
                    "payload": {
                        "session_id": session_id,
                        "content": reply_text,
                        "message_id": str(uuid.uuid4()),
                        "role": "assistant",
                        "created_at": time.time()
                    }
                })

                # Speak response via OmniVoice / Edge-TTS
                asyncio.create_task(omnivoice_tts.speak(reply_text))

            # Audio Controls / Barge-In
            elif msg_type in ("audio.control", "voice:stop", "barge_in"):
                omnivoice_tts.stop()
                await broadcast_json({
                    "type": "voice_state",
                    "state": "IDLE",
                    "amplitude": 0.0,
                    "is_speaking": False
                })
                await broadcast_json({
                    "type": "agent.state",
                    "state": "idle",
                    "payload": {"state": "idle"}
                })

            # Voice / Audio Transcript Wake-Word Processing
            elif msg_type in ("audio.transcript", "voice:transcript", "audio:text", "speech"):
                raw_text = (
                    data.get("content")
                    or data.get("text")
                    or data.get("transcript")
                    or data.get("payload", {}).get("text", "")
                )
                if raw_text:
                    voice_ears.process_incoming_audio_text(raw_text)

            # Native Kill Switch Reset
            elif msg_type == "reset_abort":
                native_core.reset_emergency_abort()
                await broadcast_json({
                    "type": "terminal_log",
                    "level": "info",
                    "message": "Emergency abort state reset by user.",
                    "timestamp": time.time()
                })

    except WebSocketDisconnect:
        active_websockets.discard(websocket)
        logger.info(f"[WebSocket] Client disconnected: {websocket.client}")
    except Exception as e:
        active_websockets.discard(websocket)
        logger.error(f"[WebSocket] Socket exception: {e}")
