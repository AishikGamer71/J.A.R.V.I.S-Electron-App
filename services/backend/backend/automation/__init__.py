
import sys
from pathlib import Path

# Forward module namespace to app.os_control
try:
    import app.os_control as _target
    for _k, _v in _target.__dict__.items():
        if not _k.startswith('__'):
            globals()[_k] = _v
except Exception:
    pass
