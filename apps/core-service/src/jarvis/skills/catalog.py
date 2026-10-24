"""Safe discovery of local ``SKILL.md`` bundles.

This module implements the user-owned, local portion of the skill systems used
by Hermes Agent and OpenClaw. It intentionally does not execute a skill file:
instructions only become model context, and model tool calls remain governed by
J.A.R.V.I.S's existing registry and approvals.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import re
from typing import Iterable

import yaml
from pydantic import ValidationError

from jarvis.config.settings import settings
from jarvis.skills.models import Skill, SkillManifest


logger = logging.getLogger("jarvis.skills.catalog")

_FRONT_MATTER_PATTERN = re.compile(r"\A---\s*\r?\n(.*?)\r?\n---\s*(?:\r?\n|\Z)", re.DOTALL)
_TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]{1,}")
_MAX_SKILLS_IN_CONTEXT = 3
_MAX_SKILL_INSTRUCTION_CHARS = 6_000
_MAX_CONTEXT_CHARS = 12_000


class SkillCatalog:
    """Loads local skill bundles from one or more trusted directories."""

    def __init__(self, roots: Iterable[Path | str] | None = None):
        self.roots = [Path(root) for root in roots] if roots is not None else [settings.SKILLS_DIR]
        self._skills: dict[str, Skill] = {}
        self._errors: list[str] = []

    def reload(self) -> dict[str, object]:
        """Rescan configured roots without executing user-provided files."""
        discovered: dict[str, Skill] = {}
        errors: list[str] = []

        for root in self.roots:
            if not root.exists():
                continue
            if not root.is_dir():
                errors.append(f"Skill root is not a directory: {root}")
                continue

            for skill_file in sorted(root.rglob("SKILL.md")):
                try:
                    skill = self._load_skill_markdown(skill_file)
                except (OSError, ValidationError, ValueError, yaml.YAMLError) as error:
                    errors.append(f"{skill_file}: {error}")
                    continue

                if skill.manifest.name in discovered:
                    errors.append(
                        f"{skill_file}: duplicate skill name '{skill.manifest.name}' "
                        f"(already loaded from {discovered[skill.manifest.name].source_path})"
                    )
                    continue
                discovered[skill.manifest.name] = skill

            # The legacy J.A.R.V.I.S authoring guide supports these manifests.
            # They are only considered when the directory has no canonical SKILL.md.
            for manifest_file in sorted((*root.rglob("manifest.yaml"), *root.rglob("manifest.yml"), *root.rglob("skill.json"))):
                if manifest_file.with_name("SKILL.md").exists():
                    continue
                try:
                    skill = self._load_manifest_file(manifest_file)
                except (OSError, ValidationError, ValueError, json.JSONDecodeError, yaml.YAMLError) as error:
                    errors.append(f"{manifest_file}: {error}")
                    continue

                if skill.manifest.name in discovered:
                    errors.append(
                        f"{manifest_file}: duplicate skill name '{skill.manifest.name}' "
                        f"(already loaded from {discovered[skill.manifest.name].source_path})"
                    )
                    continue
                discovered[skill.manifest.name] = skill

        self._skills = discovered
        self._errors = errors
        for error in errors:
            logger.warning("Rejected local skill: %s", error)
        logger.info("Loaded %d local skills from %d roots", len(discovered), len(self.roots))
        return {"loaded": len(discovered), "errors": list(errors)}

    def list_skills(self) -> list[Skill]:
        return [self._skills[name] for name in sorted(self._skills)]

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name.strip().lower())

    def errors(self) -> list[str]:
        return list(self._errors)

    def select_for_task(self, task: str, agent_name: str | None = None) -> list[Skill]:
        """Pick only clearly relevant skills to avoid wasting context on all skills."""
        task_tokens = set(_TOKEN_PATTERN.findall(task.lower()))
        explicit_names = set(re.findall(r"/(?P<name>[a-z0-9][a-z0-9-]{0,63})\b", task.lower()))
        scored: list[tuple[int, str, Skill]] = []

        for skill in self._skills.values():
            if agent_name and skill.manifest.agents and agent_name not in skill.manifest.agents:
                continue

            skill_tokens = set(
                _TOKEN_PATTERN.findall(
                    f"{skill.manifest.name} {skill.manifest.description} {' '.join(skill.manifest.tags)}".lower()
                )
            )
            score = len(task_tokens & skill_tokens)
            if skill.manifest.name in explicit_names:
                score += 100
            if score:
                scored.append((score, skill.manifest.name, skill))

        scored.sort(key=lambda item: (-item[0], item[1]))
        return [skill for _, _, skill in scored[:_MAX_SKILLS_IN_CONTEXT]]

    def build_prompt_context(self, task: str, agent_name: str | None = None) -> str:
        """Return bounded model context for skills that match the request."""
        selected = self.select_for_task(task, agent_name)
        if not selected:
            return ""

        sections: list[str] = [
            "Use the following approved local J.A.R.V.I.S skills when relevant. "
            "A skill never grants permissions: every external action must still use the approved tool registry and its confirmation flow."
        ]
        remaining = _MAX_CONTEXT_CHARS - len(sections[0])
        for skill in selected:
            instructions = skill.instructions.strip()[:_MAX_SKILL_INSTRUCTION_CHARS]
            section = f"\n\n<skill name=\"{skill.manifest.name}\">\n{instructions}\n</skill>"
            if len(section) > remaining:
                break
            sections.append(section)
            remaining -= len(section)

        return "".join(sections)

    @staticmethod
    def _load_skill_markdown(path: Path) -> Skill:
        content = path.read_text(encoding="utf-8-sig")
        match = _FRONT_MATTER_PATTERN.match(content)
        if not match:
            raise ValueError("SKILL.md must begin with YAML front matter enclosed by ---")

        raw_manifest = yaml.safe_load(match.group(1))
        if not isinstance(raw_manifest, dict):
            raise ValueError("SKILL.md front matter must be a YAML mapping")
        manifest = SkillManifest.model_validate(SkillCatalog._normalize_manifest(raw_manifest))
        instructions = content[match.end():].strip()
        if not instructions:
            raise ValueError("SKILL.md must include instructions after its front matter")
        return Skill(manifest=manifest, instructions=instructions, source_path=path)

    @staticmethod
    def _load_manifest_file(path: Path) -> Skill:
        content = path.read_text(encoding="utf-8-sig")
        raw_manifest = json.loads(content) if path.suffix == ".json" else yaml.safe_load(content)
        if not isinstance(raw_manifest, dict):
            raise ValueError("manifest must be a mapping")
        normalized = SkillCatalog._normalize_manifest(raw_manifest)
        manifest = SkillManifest.model_validate(normalized)
        instructions = str(raw_manifest.get("instructions", "")).strip() or manifest.description
        return Skill(manifest=manifest, instructions=instructions, source_path=path)

    @staticmethod
    def _normalize_manifest(raw_manifest: dict[str, object]) -> dict[str, object]:
        normalized = dict(raw_manifest)
        if "allowed_tools" not in normalized:
            normalized["allowed_tools"] = normalized.get("allowed-tools", normalized.get("tools", []))
        if isinstance(normalized.get("allowed_tools"), list):
            normalized["allowed_tools"] = [
                item.get("name", "") if isinstance(item, dict) else item
                for item in normalized["allowed_tools"]
            ]
        return normalized


skill_catalog = SkillCatalog()
