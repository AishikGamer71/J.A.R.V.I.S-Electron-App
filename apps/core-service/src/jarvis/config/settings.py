import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Server & Networking
    HOST: str = "127.0.0.1"
    PORT: int = 8765
    AUTH_TOKEN: str = "jarvis-local-dev-token"
    DEBUG: bool = False

    # Directories
    DATA_DIR: Path = Path.home() / ".jarvis"
    DATABASE_PATH: Path = Field(default_factory=lambda: Path.home() / ".jarvis" / "jarvis.db")
    SANDBOX_ROOT: Path = Field(default_factory=lambda: Path.home() / ".jarvis" / "sandbox")
    SKILLS_DIR: Path = Field(default_factory=lambda: Path.home() / ".jarvis" / "skills")

    # Security & Tool Gating
    CONFIRMATION_TIMEOUT_SECONDS: int = 30
    DOCKER_IMAGE: str = "jarvis-tool-sandbox:latest"
    INFISICAL_PROJECT_ID: str | None = None

    # Local Ollama Settings
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_DEFAULT_MODEL: str = "llama3.2"

    # Model Tier Defaults
    TIER1_MODEL: str = "ollama/llama3.2"
    TIER2_MODEL: str = "gemini/gemini-2.5-flash"
    TIER3_MODEL: str = "gemini/gemini-2.5-pro"

    # API Keys
    GEMINI_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None
    DEEPSEEK_API_KEY: str | None = None

    # Telemetry
    ENABLE_LANGFUSE: bool = False
    LANGFUSE_PUBLIC_KEY: str | None = None
    LANGFUSE_SECRET_KEY: str | None = None
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    def ensure_directories(self) -> None:
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.SANDBOX_ROOT.mkdir(parents=True, exist_ok=True)
        self.SKILLS_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
