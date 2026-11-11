"""
backend/memory/instinct_engine.py
=================================
InstinctEngine: Continuous epistemic calibration and behavior learning for J.A.R.V.I.S.
Parses observations from ~/.jarvis/homunculus/observations.jsonl, scores confidence,
stores atomic YAML instincts in ~/.jarvis/homunculus/instincts/personal/, and generates
dynamic system prompt injection blocks.
"""

import json
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger("jarvis.instinct_engine")


@dataclass
class Instinct:
    id: str
    trigger: str
    action: str
    confidence: float
    domain: str = "general"       # "security", "desktop", "terminal", "preference"
    source: str = "observation"   # "observation", "user_correction", "ecc_rule"
    scope: str = "personal"       # "personal", "global"
    confirmations: int = 1
    contradictions: int = 0
    occurrences: int = 1
    evidence: str = ""
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Default core instincts initialized if personal instincts directory is empty
DEFAULT_SEED_INSTINCTS: List[Dict[str, Any]] = [
    {
        "id": "instinct-sec-01",
        "trigger": "never format drive",
        "action": "do not execute destructive disk or filesystem format commands",
        "confidence": 1.0,
        "domain": "security",
        "source": "ecc_rule",
        "scope": "personal",
        "confirmations": 10,
        "contradictions": 0,
        "occurrences": 10,
        "evidence": "Enforced by AgentShield governance rule",
    },
    {
        "id": "instinct-pref-01",
        "trigger": "responding to user greetings",
        "action": "address the user respectfully as Sir with polished British efficiency",
        "confidence": 0.85,
        "domain": "preference",
        "source": "observation",
        "scope": "personal",
        "confirmations": 7,
        "contradictions": 0,
        "occurrences": 7,
        "evidence": "Aligned with SOUL persona specification",
    },
    {
        "id": "instinct-term-01",
        "trigger": "running powershell scripts",
        "action": "use non-interactive execution flags and check exit codes",
        "confidence": 0.75,
        "domain": "terminal",
        "source": "observation",
        "scope": "personal",
        "confirmations": 5,
        "contradictions": 0,
        "occurrences": 5,
        "evidence": "Observed terminal command best practices",
    },
]


class InstinctEngine:
    """Manages observation ingestion, confidence scoring, and dynamic instinct injection."""

    def __init__(
        self,
        instincts_dir: Optional[Path] = None,
        observations_path: Optional[Path] = None,
    ):
        self.instincts_dir = instincts_dir or (
            Path.home() / ".jarvis" / "homunculus" / "instincts" / "personal"
        )
        self.observations_path = observations_path or (
            Path.home() / ".jarvis" / "homunculus" / "observations.jsonl"
        )

        self.instincts_dir.mkdir(parents=True, exist_ok=True)
        self.observations_path.parent.mkdir(parents=True, exist_ok=True)

        self._ensure_seed_instincts()

    def _ensure_seed_instincts(self) -> None:
        """Seeds default baseline instincts if the instincts directory is currently empty."""
        try:
            existing = list(self.instincts_dir.glob("*.yaml")) + list(self.instincts_dir.glob("*.yml"))
            if not existing:
                for seed in DEFAULT_SEED_INSTINCTS:
                    slug = re.sub(r"[^a-zA-Z0-9_\-]", "_", seed["id"])
                    target = self.instincts_dir / f"{slug}.yaml"
                    with open(target, "w", encoding="utf-8") as f:
                        yaml.safe_dump(seed, f, sort_keys=False)
        except Exception as e:
            logger.warning("Could not initialize seed instincts: %s", e)

    def score_instinct(self, trigger: str, confirmations: int, contradictions: int) -> float:
        """
        Calculates confidence score based on the verified formula:
        Score = min(1.0, max(0.0, 0.50 + 0.05 * confirmations - 0.10 * contradictions))
        """
        raw = 0.50 + (0.05 * confirmations) - (0.10 * contradictions)
        return min(1.0, max(0.0, round(raw, 4)))

    def record_instinct(
        self,
        trigger: str,
        action: str,
        domain: str = "general",
        evidence: str = "",
        confirmations: int = 1,
        contradictions: int = 0,
        source: str = "observation",
        scope: str = "personal",
    ) -> Dict[str, Any]:
        """Creates or updates an atomic YAML instinct file."""
        slug = re.sub(r"[^a-zA-Z0-9_\-]", "_", trigger[:30].strip().lower())
        instinct_id = f"instinct-{domain[:3]}-{slug}"
        confidence = self.score_instinct(trigger, confirmations, contradictions)

        instinct = Instinct(
            id=instinct_id,
            trigger=trigger,
            action=action,
            confidence=confidence,
            domain=domain,
            source=source,
            scope=scope,
            confirmations=confirmations,
            contradictions=contradictions,
            occurrences=confirmations + contradictions,
            evidence=evidence,
            updated_at=time.time(),
        )

        file_path = self.instincts_dir / f"{instinct_id}.yaml"
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(instinct.to_dict(), f, sort_keys=False)

        return instinct.to_dict()

    def parse_observations(self) -> List[Instinct]:
        """
        Parses observations.jsonl to infer candidate behavioral patterns.
        Resilient against malformed or partial JSON lines.
        """
        if not self.observations_path.exists():
            return []

        counts: Dict[str, Dict[str, Any]] = {}
        with open(self.observations_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    tool = record.get("tool_name", "")
                    if not tool:
                        continue
                    status = record.get("status", "success")

                    if tool not in counts:
                        counts[tool] = {
                            "tool": tool,
                            "success_count": 0,
                            "fail_count": 0,
                            "samples": [],
                        }

                    if status == "success":
                        counts[tool]["success_count"] += 1
                        if len(counts[tool]["samples"]) < 3 and record.get("args") is not None:
                            counts[tool]["samples"].append(record.get("args", {}))
                    else:
                        counts[tool]["fail_count"] += 1
                except Exception:
                    # Gracefully skip malformed line
                    continue

        results: List[Instinct] = []
        for tool, data in counts.items():
            if data["success_count"] >= 3:
                trigger = f"executing {data['tool']}"
                action = "prefer standard parameters that succeeded in observations"
                conf = self.score_instinct(trigger, data["success_count"], data["fail_count"])
                inst = Instinct(
                    id=f"obs-{data['tool']}",
                    trigger=trigger,
                    action=action,
                    confidence=conf,
                    domain="tool_execution",
                    source="observation",
                    confirmations=data["success_count"],
                    contradictions=data["fail_count"],
                    occurrences=data["success_count"] + data["fail_count"],
                    evidence=f"Observed {data['success_count']} successful runs",
                )
                results.append(inst)

        return results

    def get_active_instincts(self, min_confidence: float = 0.70) -> List[Dict[str, Any]]:
        """
        Retrieves active instincts with confidence >= min_confidence from personal YAML files.
        """
        active: List[Dict[str, Any]] = []

        # Read YAML files from instincts_dir
        if self.instincts_dir.exists():
            for file_path in list(self.instincts_dir.glob("*.yaml")) + list(self.instincts_dir.glob("*.yml")):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                    if isinstance(data, dict):
                        conf = float(data.get("confidence", 0.0))
                        if conf >= min_confidence:
                            active.append(data)
                except Exception as e:
                    logger.debug("Failed to read instinct file %s: %s", file_path, e)

        # Sort descending by confidence
        active.sort(key=lambda x: x.get("confidence", 0.0), reverse=True)
        return active

    def render_prompt_injection(self, min_confidence: float = 0.70) -> str:
        """
        Formats high-confidence instincts into an authoritative Markdown prompt section.
        """
        active = self.get_active_instincts(min_confidence=min_confidence)
        if not active:
            return ""

        lines = [
            f"## Active Behavioral Instincts (Confidence >= {min_confidence:.2f})",
            "The following learned behavioral patterns have been verified and MUST be respected:",
        ]
        for inst in active:
            domain = inst.get("domain", "general")
            trigger = inst.get("trigger", "")
            action = inst.get("action", "")
            confidence = inst.get("confidence", 0.0)
            lines.append(f"- [{domain}] When {trigger}: {action} (confidence: {confidence:.2f})")

        return "\n".join(lines) + "\n"

    def prune_instincts(self, min_confidence: float = 0.50) -> int:
        """
        Prunes or deletes instincts with confidence below min_confidence.
        Returns count of pruned instinct files.
        """
        pruned_count = 0
        if not self.instincts_dir.exists():
            return 0

        for file_path in list(self.instincts_dir.glob("*.yaml")) + list(self.instincts_dir.glob("*.yml")):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if isinstance(data, dict):
                    conf = float(data.get("confidence", 0.0))
                    if conf < min_confidence:
                        file_path.unlink()
                        pruned_count += 1
            except Exception as e:
                logger.debug("Error while inspecting instinct for prune %s: %s", file_path, e)

        return pruned_count
