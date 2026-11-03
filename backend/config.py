"""
backend/config.py
Unified Configuration & Hardware Profile Loader for J.A.R.V.I.S.
Loads environment variables from .env and determines hardware profile.
"""

import os
from pathlib import Path
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

ROOT_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    HOST: str = "127.0.0.1"
    PORT: int = 8765
    DEBUG: bool = False

    # Directories
    ROOT_DIR: Path = ROOT_DIR
    STORAGE_DIR: Path = Field(default_factory=lambda: ROOT_DIR / "storage")
    MEMORY_DB_PATH: Path = Field(default_factory=lambda: ROOT_DIR / "storage" / "jarvis_memory.db")
    ASSETS_DIR: Path = Field(default_factory=lambda: ROOT_DIR / "backend" / "audio" / "assets")
    SKILLS_DIR: Path = Field(default_factory=lambda: ROOT_DIR / "backend" / "skills")

    # LLM Engine API Keys & Defaults
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
    OPENROUTER_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "llama3"

    # Audio & Voice Settings
    VOICE_NAME: str = "en-GB-RyanNeural"  # British J.A.R.V.I.S accent
    VOICE_RATE: str = "+0%"
    VOICE_PITCH: str = "+0Hz"
    WAKE_WORD: str = "jarvis"
    WAKE_WORDS: List[str] = Field(default_factory=lambda: ["jarvis", "hey jarvis"])
    OMNIVOICE_DEVICE: str = "cuda:0"
    OMNIVOICE_MODEL_ID: str = "k2-fsa/OmniVoice"
    JARVIS_REF_WAV: Path = Field(default_factory=lambda: ROOT_DIR / "backend" / "audio" / "assets" / "jarvis_ref.wav")

    # Hardware Guardian
    POLL_INTERVAL_SECONDS: float = 1.0

    # Security Guardrails
    ENABLE_AGENT_SHIELD: bool = True
    EMERGENCY_KILL_SWITCH: bool = True

    def ensure_directories(self) -> None:
        self.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        self.MEMORY_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        self.SKILLS_DIR.mkdir(parents=True, exist_ok=True)

settings = Settings()
settings.ensure_directories()
