"""Data models for the local J.A.R.V.I.S skill format.

The format is deliberately compatible with the ``SKILL.md`` convention used by
agent-skill ecosystems. Skills are local instruction bundles; they do not get
shell or filesystem access by themselves. Any action still goes through the
normal J.A.R.V.I.S tool registry, permission store, and confirmation bridge.
"""

from __future__ import annotations

from pathlib import Path
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


SKILL_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


class SkillManifest(BaseModel):
    """Validated metadata from a skill's YAML front matter or manifest file."""

    model_config = ConfigDict(extra="ignore")

    name: str
    description: str
    version: str = "0.1.0"
    author: str | None = None
    license: str | None = None
    allowed_tools: list[str] = Field(default_factory=list)
    agents: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not SKILL_NAME_PATTERN.fullmatch(normalized):
            raise ValueError(
                "must contain 1-64 lowercase letters, numbers, or hyphens and start with a letter or number"
            )
        return normalized

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be empty")
        return normalized

    @field_validator("allowed_tools", "agents", "tags", mode="before")
    @classmethod
    def normalize_string_list(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if not isinstance(value, list):
            raise ValueError("must be a string or a list of strings")
        return [str(item).strip() for item in value if str(item).strip()]


class Skill(BaseModel):
    """A validated local skill and its plain-text operating instructions."""

    manifest: SkillManifest
    instructions: str
    source_path: Path

    def as_public_dict(self, include_instructions: bool = False) -> dict[str, object]:
        result: dict[str, object] = {
            "name": self.manifest.name,
            "description": self.manifest.description,
            "version": self.manifest.version,
            "author": self.manifest.author,
            "license": self.manifest.license,
            "allowed_tools": self.manifest.allowed_tools,
            "agents": self.manifest.agents,
            "tags": self.manifest.tags,
            "source_path": str(self.source_path),
        }
        if include_instructions:
            result["instructions"] = self.instructions
        return result
