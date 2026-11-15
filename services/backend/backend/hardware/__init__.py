
import sys
from pathlib import Path

# Forward module namespace to app.hardware
try:
    import app.hardware as _target
    for _k, _v in _target.__dict__.items():
        if not _k.startswith('__'):
            globals()[_k] = _v
except Exception:
    pass
