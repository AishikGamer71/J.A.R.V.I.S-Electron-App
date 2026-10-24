import os
from pathlib import Path
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
    
    # Storage & directories
    DATA_DIR: Path = ROOT_DIR / "storage"
    DATABASE_PATH: Path = Field(default_factory=lambda: ROOT_DIR / "storage" / "jarvis_memory.db")
    
    # Gemini AI Configuration
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    
    # TTS & Voice
    VOICE_NAME: str = "en-GB-RyanNeural"  # Classic British J.A.R.V.I.S accent
    VOICE_RATE: str = "+0%"
    VOICE_PITCH: str = "+0Hz"
    
    # Security
    CONFIRMATION_TIMEOUT_SECONDS: int = 30
    
    def ensure_directories(self) -> None:
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

settings = Settings()
settings.ensure_directories()
