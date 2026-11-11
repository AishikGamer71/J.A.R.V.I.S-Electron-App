import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.security.agent_shield import AgentShield
from backend.security.ecc_hooks import ECCHookDispatcher
from backend.memory.instinct_engine import InstinctEngine
import tempfile
import threading
import json
import shutil

s = AgentShield()

# 1. Quoted Azure Key
raw_key = ("A" * 86) + "=="
v1 = s.scan_input(f'AccountKey="{raw_key}"').passed

# 2. Reordered commands
reordered = [
    "rm -f -r /",
    "rm -r -f /",
    "rm --recursive --force /",
    "del /q /s /f C:\\*",
    "del /s /f /q C:\\*",
    "rmdir /q /s C:\\Users",
]
v2 = [c for c in reordered if s.validate_command(c)]

# 3. Null byte split
v3 = s.validate_command("r\x00m -rf /")

# 4. System32 subpath write
v4 = [
    p
    for p in [
        "C:\\Windows\\System32\\cmd.exe",
        "C:\\Windows\\System32\\drivers\\etc\\hosts",
        "system32/evil.bat",
    ]
    if s.verify_file_path(p, write_mode=True)[0]
]

# 5. Nested secrets
v5 = s.validate_tool_call(
    "test", {"payload": {"token": "sk-proj-123456789012345678901234"}}
)[0]

# 6. ECC concurrency
td = tempfile.mkdtemp()
tp = Path(td) / "obs.jsonl"
disp = ECCHookDispatcher(log_path=tp)
barrier = threading.Barrier(10)


def w(tid):
    barrier.wait()
    for i in range(15):
        disp.post_tool_use(f"t_{tid}", {"i": i}, f"r_{i}")


ths = [threading.Thread(target=w, args=(i,)) for i in range(10)]
for t in ths:
    t.start()
for t in ths:
    t.join()
with open(tp) as f:
    lines = [l for l in f if l.strip()]
v6 = (150, len(lines), 150 - len(lines))

# 7. Instinct contradiction loss
inst_dir = Path(td) / "inst"
eng = InstinctEngine(instincts_dir=inst_dir, observations_path=tp)
with open(tp, "w") as f:
    for _ in range(3):
        f.write(json.dumps({"tool_name": "git", "status": "success"}) + "\n")
    for _ in range(2):
        f.write(json.dumps({"tool_name": "git", "status": "error"}) + "\n")
inferred = eng.parse_observations()
v7 = (inferred[0].confirmations, inferred[0].contradictions)

shutil.rmtree(td, ignore_errors=True)

print("--- EMPIRICAL EVIDENCE SUMMARY ---")
print("V1 (Quoted Azure Key Bypasses Scanner):", v1)
print("V2 (Destructive Commands Allowed):", v2)
print("V3 (Null-byte Command Splitting Allowed):", v3)
print("V4 (System32 Subpaths Allowed For Write):", v4)
print("V5 (Nested Secrets Allowed in Tool Call):", v5)
print(f"V6 (ECC Concurrent Telemetry Loss): Expected={v6[0]}, Written={v6[1]}, Lost={v6[2]} ({(v6[2]/v6[0])*100:.1f}%)")
print(f"V7 (Instinct Observation Contradictions Lost): Expected=2, Recorded={v7[1]}")
