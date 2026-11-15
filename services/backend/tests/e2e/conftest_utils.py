"""Shared test utilities, fixtures, and contract validators for J.A.R.V.I.S. E2E tests.
"""

import os
import re
import sys
import wave
import json
import sqlite3
import hashlib
import unittest
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

_candidate = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = _candidate.parent.parent if (_candidate.parent.parent / "package.json").exists() else _candidate

JARVIS_REF_SHA256 = "81d2718566fa9617cfaace564300488243d93ec0c554c7d4b7194bbed3e02d73"
JARVIS_REF_SIZE = 353708
JARVIS_REF_RATE = 24000
JARVIS_REF_CHANNELS = 1
JARVIS_REF_FRAMES = 176832

TARGET_BACKEND_SUBDIRS = [
    "agents",
    "memory",
    "skills",
    "core",
    "engine",
    "security",
    "voice",
    "automation",
    "senses",
    "hardware",
]

GOVERNANCE_RULES_REQUIRED_PHRASES = [
    "ZERO UI DRIFT",
    "Electron",
    "3-tier",
    "AgentShield",
    "Ctrl+Alt+Backspace",
]

LIGHTING_CONFIG_REQUIRED_KEYS = [
    "primaryColor",
    "outerRingColor",
    "innerCoreColor",
    "dampingFactor",
]


def get_project_root() -> Path:
    return PROJECT_ROOT


def get_backend_path() -> Path:
    shim = PROJECT_ROOT / "services" / "backend" / "backend"
    if shim.exists():
        return shim
    app_path = PROJECT_ROOT / "services" / "backend" / "app"
    if app_path.exists():
        return app_path
    return PROJECT_ROOT / "backend"


BACKEND_DIR = get_backend_path()
DESKTOP_SRC = PROJECT_ROOT / "apps" / "desktop" / "src" if (PROJECT_ROOT / "apps" / "desktop" / "src").exists() else PROJECT_ROOT / "src"
PERSONA_DIR = PROJECT_ROOT / "config" / "persona" if (PROJECT_ROOT / "config" / "persona").exists() else BACKEND_DIR


def locate_voice_ref_wav() -> Optional[Path]:
    for candidate in [
        PROJECT_ROOT / "services" / "backend" / "app" / "voice" / "assets" / "jarvis_ref.wav",
        PROJECT_ROOT / "services" / "backend" / "backend" / "voice" / "assets" / "jarvis_ref.wav",
        PROJECT_ROOT / "backend" / "voice" / "assets" / "jarvis_ref.wav",
        PROJECT_ROOT / "backend" / "audio" / "assets" / "jarvis_ref.wav",
        PROJECT_ROOT / "_safe_assets" / "jarvis_ref.wav",
    ]:
        if candidate.exists():
            return candidate
    return None


def calculate_sha256(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def inspect_wav_file(file_path: Path) -> Dict[str, Any]:
    with wave.open(str(file_path), "rb") as w:
        return {
            "channels": w.getnchannels(),
            "sample_width": w.getsampwidth(),
            "frame_rate": w.getframerate(),
            "n_frames": w.getnframes(),
            "compression_type": w.getcomptype(),
            "duration_sec": w.getnframes() / float(w.getframerate()),
        }


def check_milestone_ready(milestone: str) -> bool:
    milestone = milestone.upper()
    backend_dir = BACKEND_DIR
    desktop_src = DESKTOP_SRC
    persona_dir = PERSONA_DIR
    if milestone == "M1":
        voice_ref = locate_voice_ref_wav() is not None
        arc_reactor = (desktop_src / "components" / "widgets" / "arc-reactor.tsx").exists()
        agents_dir = (backend_dir / "agents").exists() or (persona_dir / "agents").exists()
        return voice_ref and arc_reactor and agents_dir
    elif milestone == "M2":
        agent_shield = backend_dir / "security" / "agent_shield.py"
        hermes = backend_dir / "core" / "hermes_brain.py"
        state_db = backend_dir / "memory" / "state_db.py"
        return agent_shield.exists() and (hermes.exists() or state_db.exists())
    elif milestone == "M3":
        voice_pipe = backend_dir / "voice" / "audio_pipeline.py"
        router = backend_dir / "engine" / "model_router.py"
        return voice_pipe.exists() and router.exists()
    elif milestone == "M4":
        s3 = backend_dir / "automation" / "agent_s3_runner.py"
        omniparser = backend_dir / "automation" / "omniparser_service.py"
        return s3.exists() or omniparser.exists()
    elif milestone == "M5":
        main_py = backend_dir / "main.py"
        camera = backend_dir / "senses" / "camera_hub.py"
        return main_py.exists() and camera.exists()
    elif milestone == "M6":
        return True
    return False


def skip_if_milestone_pending(test_case: unittest.TestCase, milestone: str):
    if not check_milestone_ready(milestone):
        raise unittest.SkipTest(f"Milestone {milestone} implementation is pending. Contract test deferred.")


class MockWebSocketEnvelope:
    @staticmethod
    def create(msg_type: str, payload: Any, correlation_id: Optional[str] = None) -> Dict[str, Any]:
        return {
            "type": msg_type,
            "payload": payload,
            "timestamp": "2026-11-10T08:30:00.000Z",
            "correlation_id": correlation_id or "corr-0001",
        }

    @staticmethod
    def validate(envelope: Dict[str, Any]) -> Tuple[bool, str]:
        if not isinstance(envelope, dict):
            return False, "Envelope must be a JSON object (dict)"
        for field in ["type", "payload", "timestamp"]:
            if field not in envelope:
                return False, f"Missing required envelope field: {field}"
        if not isinstance(envelope["type"], str) or not envelope["type"].strip():
            return False, "Envelope type must be a non-empty string"
        return True, "Valid"
