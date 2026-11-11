"""
backend/core/prompt_builder.py
==============================
PromptBuilder: Dynamic system prompt assembler for J.A.R.V.I.S.
Loads persona from SOUL.md, user details from USER.md, long-term memory from MEMORY.md,
runtime skills from backend/skills/*.md, and active instincts from InstinctEngine.
Ensures prompt injection sanitization and UTF-8 BOM stripping.
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

from backend.memory.instinct_engine import InstinctEngine
from backend.security.agent_shield import AgentShield

logger = logging.getLogger("jarvis.prompt_builder")


class PromptBuilder:
    """Assembles authoritative system prompts and LLM message payloads."""

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        instinct_engine: Optional[InstinctEngine] = None,
        shield: Optional[AgentShield] = None,
    ):
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent
        self.memory_dir = self.base_dir / "memory"
        self.skills_dir = self.base_dir / "skills"
        self.agents_dir = self.base_dir / "agents"
        self.instinct_engine = instinct_engine or InstinctEngine()
        self.shield = shield or AgentShield()

    def _read_file_safe(self, path: Path) -> str:
        """Reads text file safely, stripping UTF-8 BOM."""
        if not path.exists():
            return ""
        try:
            content = path.read_text(encoding="utf-8")
            # Strip BOM if present
            if content.startswith("\ufeff"):
                content = content[1:]
            return content.strip()
        except Exception as e:
            logger.warning("Error reading file %s: %s", path, e)
            return ""

    def load_soul_md(self) -> str:
        soul_path = self.memory_dir / "SOUL.md"
        content = self._read_file_safe(soul_path)
        if not content:
            return "You are J.A.R.V.I.S., an advanced autonomous AI assistant."
        return content

    def load_user_md(self) -> str:
        user_path = self.memory_dir / "USER.md"
        return self._read_file_safe(user_path)

    def load_memory_md(self) -> str:
        mem_path = self.memory_dir / "MEMORY.md"
        return self._read_file_safe(mem_path)

    def load_active_instincts(self, min_confidence: float = 0.70) -> str:
        if self.instinct_engine:
            return self.instinct_engine.render_prompt_injection(min_confidence=min_confidence)
        return ""

    def load_skills_catalog(self) -> List[Dict[str, Any]]:
        """Parses YAML frontmatter from markdown files in backend/skills/."""
        catalog: List[Dict[str, Any]] = []
        if not self.skills_dir.exists():
            return catalog

        for md_file in self.skills_dir.glob("*.md"):
            try:
                text = self._read_file_safe(md_file)
                match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
                if match:
                    header_yaml = match.group(1)
                    meta = yaml.safe_load(header_yaml) or {}
                    if isinstance(meta, dict):
                        meta["file"] = md_file.name
                        catalog.append(meta)
                else:
                    catalog.append({"name": md_file.stem, "file": md_file.name})
            except Exception as e:
                logger.debug("Failed to parse skill frontmatter in %s: %s", md_file, e)

        return catalog

    def build_skills_system_prompt(self) -> str:
        skills = self.load_skills_catalog()
        if not skills:
            return ""

        lines = ["## Available Skills & Tools"]
        for s in skills:
            name = s.get("name", "skill")
            desc = s.get("description", "")
            tools = s.get("tools", [])
            tools_str = f" (Tools: {', '.join(tools)})" if tools else ""
            lines.append(f"- **{name}**{tools_str}: {desc}")

        return "\n".join(lines)

    def build_system_prompt(
        self,
        extra_context: str = "",
        tools: Optional[List[Dict[str, Any]]] = None,
        instincts: Optional[List[Union[str, Dict[str, Any]]]] = None,
        user_profile: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Builds the unified system prompt adhering to priority ordering:
        SOUL -> User Profile -> Memory -> Learned Instincts -> Skills / Tools -> Hardware / Extra
        """
        sections: List[str] = []

        # 1. SOUL
        soul = self.load_soul_md()
        sections.append(soul)

        # 2. User Profile
        if user_profile:
            user_sec = ["## User Profile"]
            for k, v in user_profile.items():
                user_sec.append(f"- **{k.capitalize()}**: {v}")
            sections.append("\n".join(user_sec))
        else:
            user_md = self.load_user_md()
            if user_md:
                sections.append(user_md)

        # 3. Core Memory
        memory_md = self.load_memory_md()
        if memory_md:
            sections.append(memory_md)

        # 4. Instincts
        if instincts:
            inst_lines = ["## Active Behavioral Instincts"]
            for inst in instincts:
                if isinstance(inst, str):
                    inst_lines.append(f"- {inst}")
                elif isinstance(inst, dict):
                    trigger = inst.get("trigger", "")
                    action = inst.get("action", "")
                    conf = inst.get("confidence", 1.0)
                    inst_lines.append(f"- When {trigger}: {action} (confidence: {conf})")
            sections.append("\n".join(inst_lines))
        else:
            active_inst = self.load_active_instincts()
            if active_inst:
                sections.append(active_inst.strip())

        # 5. Tools Catalog
        if tools:
            tool_lines = ["## Registered Tools"]
            for t in tools:
                name = t.get("name") or t.get("tool") or str(t)
                desc = t.get("description", "")
                tool_lines.append(f"- **{name}**: {desc}")
            sections.append("\n".join(tool_lines))
        else:
            skills_prompt = self.build_skills_system_prompt()
            if skills_prompt:
                sections.append(skills_prompt)

        # 6. Extra context
        if extra_context:
            sections.append(f"## Additional Context\n{extra_context}")

        assembled = "\n\n".join(sections)
        return assembled

    def assemble_messages(
        self,
        system_prompt: str,
        history: List[Dict[str, Any]],
        current_user_message: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Formats system prompt, cleaned history, and user input into provider-ready messages payload.
        """
        messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]

        for h in history:
            role = h.get("role", "user")
            content = h.get("content") or ""
            msg_dict: Dict[str, Any] = {"role": role, "content": content}
            if h.get("tool_calls"):
                msg_dict["tool_calls"] = h["tool_calls"]
            if h.get("tool_call_id"):
                msg_dict["tool_call_id"] = h["tool_call_id"]
            if h.get("tool_name"):
                msg_dict["name"] = h["tool_name"]
            messages.append(msg_dict)

        if current_user_message:
            # Avoid duplicate if last message in history is identical
            if not history or history[-1].get("content") != current_user_message:
                messages.append({"role": "user", "content": current_user_message})

        return messages

    def build_subagent_prompt(self, role: str, parent_goal: str) -> str:
        """
        Loads specialized persona and limits from backend/agents/{role}.md.
        """
        agent_file = self.agents_dir / f"{role}.md"
        base_prompt = self._read_file_safe(agent_file)
        if not base_prompt:
            base_prompt = f"You are a specialized {role} subagent supporting J.A.R.V.I.S."

        constraints = f"\n\n## Subagent Mission Constraint\nParent Goal: {parent_goal}\nExecute with strict read-only tool limits."
        return base_prompt + constraints
