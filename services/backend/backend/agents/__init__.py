
import sys
from pathlib import Path

# Forward module namespace to config.persona.agents
try:
    import config.persona.agents as _target
    for _k, _v in _target.__dict__.items():
        if not _k.startswith('__'):
            globals()[_k] = _v
except Exception:
    pass
