import re
from jarvis.domain.entities.models import ModelTier

# Keywords triggering Tier 1 (Fast / Command / Conversational)
TIER1_PATTERNS = [
    r"^(hi|hello|hey|good morning|good evening|who are you|jarvis|what is your name)\b",
    r"^(what time|what date|what day|current time|today's date)",
    r"^(open|close|launch|switch to|maximize|minimize|mute|unmute)\s+[a-zA-Z0-9_-]+",
    r"^(system status|hardware status|cpu usage|ram usage|telemetry|ping)",
    r"^(clear|reset|clean|exit|quit|stop)$",
]

# Keywords triggering Tier 3 (Deep Reasoning / Complex Orchestration / Refactor)
TIER3_PATTERNS = [
    r"\b(refactor|architect|architecture|formal verification|deep dive|proof|benchmark)\b",
    r"\b(design system|multi-agent|distributed system|compiler|kernel|security audit)\b",
    r"\b(write a comprehensive|full implementation|end-to-end plan|in-depth analysis)\b"
]


def classify_tier(text: str) -> ModelTier:
    stripped = text.strip().lower()
    
    # 1. Quick length and pattern match for Tier 1
    if len(stripped) < 40:
        for pat in TIER1_PATTERNS:
            if re.search(pat, stripped, re.IGNORECASE):
                return ModelTier.TIER1_LOCAL

    # 2. Check for Tier 3 keywords or long complex instructions
    if len(stripped) > 400:
        return ModelTier.TIER3_CLOUD
        
    for pat in TIER3_PATTERNS:
        if re.search(pat, stripped, re.IGNORECASE):
            return ModelTier.TIER3_CLOUD

    # 3. Default to Tier 2 (Balanced Reasoning)
    return ModelTier.TIER2_BALANCED
