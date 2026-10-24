"""
J.A.R.V.I.S Voice Service HTTP & WebSocket Microservice.
Provides real-time STT, TTS streaming, and wake word notifications.
"""
import io
import json
import logging
from typing import Optional
from fastapi import FastAPI, File, Form, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel

try:
    from .stt import SpeechToText
    from .tts import TextToSpeech
    from .wake_word import WakeWordDetector
    from .echo_gate import EchoGate
except ImportError:
    from stt import SpeechToText
    from tts import TextToSpeech
    from wake_word import WakeWordDetector
    from echo_gate import EchoGate

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("jarvis.voice.server")

app = FastAPI(title="JARVIS Voice Service", version="4.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

stt_engine = SpeechToText()
tts_engine = TextToSpeech()
wake_detector = WakeWordDetector()
echo_gate = EchoGate()


class SynthesizeRequest(BaseModel):
    text: str
    voice: Optional[str] = None


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "jarvis-voice-service",
        "version": "4.0.0",
        "echo_gate_muted": echo_gate.is_mic_muted
    }


@app.post("/v1/voice/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Transcribe audio upload (WAV, MP3, OGG, WebM) into text.
    """
    try:
        content = await file.read()
        text = stt_engine.transcribe(content)
        return {"text": text, "filename": file.filename}
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/v1/voice/synthesize")
async def synthesize_speech(req: SynthesizeRequest):
    """
    Synthesize text into WAV speech audio.
    """
    try:
        echo_gate.on_tts_start()
        wav_bytes = tts_engine.synthesize_bytes(req.text)
        echo_gate.on_tts_end()
        return Response(content=wav_bytes, media_type="audio/wav")
    except Exception as e:
        echo_gate.on_tts_end()
        logger.error(f"Synthesis error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.websocket("/v1/voice/stream")
async def voice_stream_ws(websocket: WebSocket):
    """
    Real-time bidirectional voice stream from Electron client:
    - Receives binary PCM audio chunks (from Chromium getUserMedia with AEC).
    - Detects wake words on incoming frames.
    - Emits wake_word_detected, speech_transcribed, and audio playback events.
    """
    await websocket.accept()
    logger.info("Client connected to voice stream WebSocket")

    try:
        while True:
            message = await websocket.receive()
            if "bytes" in message and message["bytes"]:
                raw_pcm = message["bytes"]
                
                # If echo gate is muted (JARVIS is speaking), ignore incoming mic audio
                if echo_gate.is_mic_muted:
                    continue

                # Check wake word
                wake_result = wake_detector.process_frame(raw_pcm)
                if wake_result:
                    wake_name, score = wake_result
                    await websocket.send_json({
                        "event": "wake_word_detected",
                        "wake_word": wake_name,
                        "score": score
                    })

            elif "text" in message and message["text"]:
                data = json.loads(message["text"])
                msg_type = data.get("type")

                if msg_type == "ping":
                    await websocket.send_json({"type": "pong"})

                elif msg_type == "transcribe_buffer":
                    pcm_hex = data.get("pcm_hex", "")
                    if pcm_hex:
                        pcm_bytes = bytes.fromhex(pcm_hex)
                        transcription = stt_engine.transcribe_pcm(pcm_bytes)
                        await websocket.send_json({
                            "event": "transcription_complete",
                            "text": transcription
                        })

                elif msg_type == "tts_speak":
                    text = data.get("text", "")
                    if text:
                        echo_gate.on_tts_start()
                        audio_data = tts_engine.synthesize_bytes(text)
                        echo_gate.on_tts_end()
                        await websocket.send_bytes(audio_data)

    except WebSocketDisconnect:
        logger.info("Voice stream WebSocket disconnected")
    except Exception as e:
        logger.error(f"Voice stream exception: {e}")
