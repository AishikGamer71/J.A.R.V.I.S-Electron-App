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

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

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
    return PROJECT_ROOT / "backend"


def locate_voice_ref_wav() -> Optional[Path]:
    target_voice_path = PROJECT_ROOT / "backend" / "voice" / "assets" / "jarvis_ref.wav"
    if target_voice_path.exists():
        return target_voice_path
    
    legacy_audio_path = PROJECT_ROOT / "backend" / "audio" / "assets" / "jarvis_ref.wav"
    if legacy_audio_path.exists():
        return legacy_audio_path

    safe_backup_path = PROJECT_ROOT / "_safe_assets" / "jarvis_ref.wav"
    if safe_backup_path.exists():
        return safe_backup_path

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
    if milestone == "M1":
        voice_ref = (PROJECT_ROOT / "backend" / "voice" / "assets" / "jarvis_ref.wav").exists()
        arc_reactor = (PROJECT_ROOT / "src" / "components" / "widgets" / "arc-reactor.tsx").exists()
        agents_dir = (PROJECT_ROOT / "backend" / "agents").exists()
        return voice_ref and arc_reactor and agents_dir
    elif milestone == "M2":

        agent_shield = PROJECT_ROOT / "backend" / "security" / "agent_shield.py"
        hermes = PROJECT_ROOT / "backend" / "core" / "hermes_brain.py"
        state_db = PROJECT_ROOT / "backend" / "memory" / "state_db.py"
        return agent_shield.exists() and (hermes.exists() or state_db.exists())
    elif milestone == "M3":
        voice_pipe = PROJECT_ROOT / "backend" / "voice" / "audio_pipeline.py"
        router = PROJECT_ROOT / "backend" / "engine" / "model_router.py"
        return voice_pipe.exists() and router.exists()
    elif milestone == "M4":
        s3 = PROJECT_ROOT / "backend" / "automation" / "agent_s3_runner.py"
        omniparser = PROJECT_ROOT / "backend" / "automation" / "omniparser_service.py"
        return s3.exists() or omniparser.exists()
    elif milestone == "M5":
        main_py = PROJECT_ROOT / "backend" / "main.py"
        camera = PROJECT_ROOT / "backend" / "senses" / "camera_hub.py"
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
