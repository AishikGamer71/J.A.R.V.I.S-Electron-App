import os
import sys
from pathlib import Path

# Ensure services/backend and project root are on sys.path
backend_dir = Path(__file__).resolve().parent
repo_root = backend_dir.parent.parent

for p in (str(backend_dir), str(repo_root)):
    if p not in sys.path:
        sys.path.insert(0, p)

# Ensure runtime data directory is set
if "JARVIS_DATA_DIR" not in os.environ:
    appdata = os.environ.get("APPDATA")
    if appdata:
        os.environ["JARVIS_DATA_DIR"] = str(Path(appdata) / "JARVIS" / "core")
    else:
        os.environ["JARVIS_DATA_DIR"] = str(repo_root / ".data" / "core")
