"""
backend/memory/instinct_learner.py
ECC Continuous-Learning-v2 Assimilation.
Autonomous habit extraction, confidence scoring, and instinct storage.
"""

import sqlite3
import time
import json
import uuid
import re
import logging
from typing import List, Dict, Any, Optional
from backend.config import settings

logger = logging.getLogger("jarvis.memory.instinct")

class InstinctLearner:
    """ECC-style continuous learner extracting habits, shortcuts, and persistent instincts."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(settings.MEMORY_DB_PATH)
        self._init_table()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_table(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS instincts (
                    id TEXT PRIMARY KEY,
                    trigger TEXT NOT NULL,
                    action TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    domain TEXT NOT NULL,
                    evidence TEXT,
                    occurrences INTEGER DEFAULT 1,
                    updated_at REAL NOT NULL
                );
            """)

    def record_instinct(self, trigger: str, action: str, domain: str = "general",
                        evidence: str = "", confidence_boost: float = 0.2) -> Dict[str, Any]:
        """Adds or reinforces an observed instinct."""
        now = time.time()
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT id, confidence, occurrences FROM instincts WHERE trigger = ? AND domain = ?",
                (trigger.strip().lower(), domain)
            ).fetchone()

            if row:
                instinct_id = row["id"]
                new_conf = min(1.0, row["confidence"] + confidence_boost)
                new_occ = row["occurrences"] + 1
                conn.execute(
                    "UPDATE instincts SET action = ?, confidence = ?, occurrences = ?, evidence = ?, updated_at = ? "
                    "WHERE id = ?",
                    (action, new_conf, new_occ, evidence, now, instinct_id)
                )
            else:
                instinct_id = str(uuid.uuid4())
                new_conf = max(0.1, min(1.0, confidence_boost))
                new_occ = 1
                conn.execute(
                    "INSERT INTO instincts (id, trigger, action, confidence, domain, evidence, occurrences, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (instinct_id, trigger.strip().lower(), action, new_conf, domain, evidence, new_occ, now)
                )

        return {
            "id": instinct_id,
            "trigger": trigger,
            "action": action,
            "confidence": new_conf,
            "domain": domain,
            "occurrences": new_occ
        }

    def get_instincts(self, domain: Optional[str] = None, min_confidence: float = 0.3) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            if domain:
                rows = conn.execute(
                    "SELECT * FROM instincts WHERE domain = ? AND confidence >= ? ORDER BY confidence DESC",
                    (domain, min_confidence)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM instincts WHERE confidence >= ? ORDER BY confidence DESC",
                    (min_confidence,)
                ).fetchall()

        return [dict(r) for r in rows]

    def query_relevant_instincts(self, context_str: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Matches context words against stored instinct triggers."""
        tokens = set(re.findall(r'\b[a-zA-Z0-9_-]{3,}\b', context_str.lower()))
        if not tokens:
            return []

        all_instincts = self.get_instincts(min_confidence=0.2)
        matched = []
        for inst in all_instincts:
            trig_words = set(re.findall(r'\b[a-zA-Z0-9_-]{3,}\b', inst["trigger"].lower()))
            overlap = len(tokens.intersection(trig_words))
            if overlap > 0:
                score = inst["confidence"] * (overlap / max(1, len(trig_words)))
                matched.append((score, inst))

        matched.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in matched[:top_k]]

    def get_all_instincts(self) -> List[Dict[str, Any]]:
        return self.get_instincts(min_confidence=0.0)

    def learn_from_feedback(self, fact: str, was_success: bool = True) -> Dict[str, Any]:
        return self.record_instinct(
            trigger=fact[:40],
            action=fact,
            domain="core_memory",
            confidence_boost=0.5 if was_success else -0.2
        )

    def reflect_on_session(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyzes session messages for user corrections or repeated commands
        to extract automatic instincts.
        """
        new_instincts = []
        for i in range(1, len(messages)):
            prev = messages[i-1]
            curr = messages[i]
            # Detect user correction e.g. "no, do X instead" or "always use Y"
            if curr.get("role") == "user":
                text = curr.get("content", "")
                m = re.search(r"(?:always|prefer|use)\s+([a-zA-Z0-9_\-\.\s]+?)(?:\s+for|\s+instead|\.|$)", text, re.IGNORECASE)
                if m:
                    pref = m.group(1).strip()
                    inst = self.record_instinct(
                        trigger=f"preference:{pref[:30]}",
                        action=f"Default to {pref}",
                        domain="preference",
                        evidence=text[:100],
                        confidence_boost=0.3
                    )
                    new_instincts.append(inst)

        return new_instincts

instinct_learner = InstinctLearner()
