# Investigation & Hardening Report — Milestone M5 Iteration 2: Mobile & Senses Hardening

**Agent**: `explorer_m5_iter2_2`  
**Role**: Teamwork Explorer (Read-Only Investigation & Adversarial Synthesis)  
**Milestone**: M5 Iteration 2 (Mobile & Senses Hardening)  
**Working Directory**: `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m5_iter2_2`  
**Parent Orchestrator ID**: `0fdc9e0b-a0b4-4f46-b4f4-43817ee786b4`  
**Date**: 2026-11-10T16:05:00Z  

---

## 1. Observation

Direct empirical observations, line citations, and reproduction commands across the target subsystems:

### 1.1 MobileRunService (`backend/senses/mobilerun_service.py`)

1. **Whitespace-Only Command Bypasses Filter**:
   - **File & Lines**: `backend/senses/mobilerun_service.py:83–91`
   - **Current Implementation**:
     ```python
     83:    def validate_adb_command(self, cmd: str) -> bool:
     84:        if not cmd or not isinstance(cmd, str):
     85:            return False
     86:        clean = cmd.strip()
     87:        for pattern in DANGEROUS_COMMAND_PATTERNS:
     88:            if re.search(pattern, clean, re.IGNORECASE):
     89:                logger.warning("MobileRun safety guard blocked dangerous command: %s", clean)
     90:                return False
     91:        return True
     ```
   - **Reproduction**:
     ```powershell
     python -c "from backend.senses.mobilerun_service import MobileRunService; s = MobileRunService(); print('Result:', s.validate_adb_command('   '))"
     ```
   - **Verbatim Result**: `Result: True`
   - **Observation**: `"   "` is a truthy string (`bool("   ") == True`). `clean = cmd.strip()` produces `""`. None of the `DANGEROUS_COMMAND_PATTERNS` match an empty string, so `validate_adb_command("   ")` reaches line 91 and returns `True`.

2. **Split-Flag Destructive Command Evasion (`rm -r -f /system`)**:
   - **File & Lines**: `backend/senses/mobilerun_service.py:19–30`
   - **Current Pattern**:
     ```python
     19: DANGEROUS_COMMAND_PATTERNS = [
     20:     r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f?[a-zA-Z]*\s+)?(\/|\/system|\/data|\/boot)",
     21:     r"\bformat\b",
     ...
     ```
   - **Reproduction**:
     ```powershell
     python -c "from backend.senses.mobilerun_service import MobileRunService; s = MobileRunService(); print('rm -rf /system:', s.validate_adb_command('rm -rf /system')); print('rm -r -f /system:', s.validate_adb_command('rm -r -f /system'))"
     ```
   - **Verbatim Result**:
     ```
     MobileRun safety guard blocked dangerous command: rm -rf /system
     rm -rf /system: False
     rm -r -f /system: True
     ```
   - **Observation**: `rm -rf /system` is blocked (`False`), but `rm -r -f /system`, `rm -f -r /data`, `rm -r -f /boot`, and `rm -r -f /` all return `True` (allowed).
   - **Regex Mechanism**: `\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f?[a-zA-Z]*\s+)?` only consumes a *single* flag argument (e.g. `-r `). The remaining tokens `-f /system` fail to match the path branch `(\/|\/system|\/data|\/boot)` because `-f` intervenes.

3. **Critical Regex Finding Regarding Word Boundaries (`\b`) with Slashes**:
   - Testing reviewer_m5_1's suggested regex `r"\brm\b.*?\b(\/|\/system|\/data|\/boot)\b"` revealed a flaw:
     In Python `re`, `/` is a non-word character (`\W`). The word boundary assertion `\b` requires a transition between word (`\w`) and non-word (`\W`) characters. When `/` is preceded by a space (`\W`), `\b\/` **does not match**!
     Consequently, `r"\brm\b.*?\b(\/|\/system...)"` evaluated `rm -rf /system` as `False` (not matched).
     The pattern must omit `\b` immediately adjacent to `/`.

---

### 1.2 DeepFaceSentry (`backend/senses/deepface_sentry.py`)

1. **Mock Stranger Streak & Alarm Discrepancy**:
   - **File & Lines**: `backend/senses/deepface_sentry.py:177–226`
   - **Current Implementation**:
     ```python
     177:    def _authenticate_mock(self, frame: np.ndarray) -> Dict[str, Any]:
     ...
     204:        return {
     205:            "authenticated": False,
     206:            "user": None,
     207:            "confidence": 0.15,
     208:            "distance": 0.85,
     209:            "liveness_passed": True,
     210:            "anti_spoofing": {"passed": True, "score": 0.95},
     211:            "status": "STRANGER",
     212:        }
     213:
     214:    def _record_stranger(self, reason: str) -> Dict[str, Any]:
     215:        self._stranger_streak += 1
     216:        return {
     217:            "authenticated": False,
     218:            "user": None,
     219:            "confidence": 0.0,
     220:            "distance": 1.0,
     221:            "liveness_passed": True,
     222:            "anti_spoofing": {"passed": True, "score": 0.9},
     223:            "status": "STRANGER_SENTRY_ALERT" if self._stranger_streak >= 3 else "STRANGER",
     224:            "reason": reason,
     225:        }
     ```
   - **Reproduction**:
     ```powershell
     python -c "import numpy as np; from backend.senses.deepface_sentry import DeepFaceSentry; s = DeepFaceSentry(); frame = np.ones((50,50,3), dtype=np.uint8)*100; [print(i, s.authenticate_frame(frame)['status'], 'streak:', s._stranger_streak) for i in range(1, 5)]"
     ```
   - **Verbatim Result**:
     ```
     1 STRANGER streak: 0
     2 STRANGER streak: 0
     3 STRANGER streak: 0
     4 STRANGER streak: 0
     ```
   - **Observation**: `_authenticate_mock` bypasses `self._record_stranger(...)`. The streak remains `0` indefinitely and `"STRANGER_SENTRY_ALERT"` is never raised, whereas in `_authenticate_deepface` (line 160), `self._record_stranger(...)` increments `_stranger_streak` and fires `"STRANGER_SENTRY_ALERT"` on attempt 3.
   - **Owner Verification Streak Reset Gap**: In `_authenticate_deepface` line 149, successful authentication performs `self._stranger_streak = 0`. In `_authenticate_mock` lines 193–202, `self._stranger_streak` is not reset when an owner matches.

---

## 2. Logic Chain

### 2.1 MobileRun Command Validation Reasoning
1. **Whitespace Safety**:
   - `validate_adb_command(cmd)` must reject empty or whitespace-only inputs because submitting an empty string to `adb shell ""` causes undefined shell behavior or interactive prompts that hang automated subprocess runners.
   - Adding `or not cmd.strip()` to line 84 guarantees that strings consisting purely of whitespace (`" "`, `"\t"`, `"\n"`) are rejected immediately without executing regex loops.

2. **Split-Flag Destructive Command Defense**:
   - Attackers evade single-token regexes by breaking `-rf` into `-r -f`, `-f -r`, `-R -f`, `--recursive --force`, or inserting multiple space-separated flags before the target directory.
   - In Unix/Android ADB, `rm -r -f /system` and `rm -f -r /data` delete critical OS and user partitions just as effectively as `rm -rf /system`.
   - The regex must support zero or more arbitrary flag tokens: `(?:-[a-zA-Z0-9-]+\s+)*`.
   - Matching optional quotes around paths: `[\"']?`.
   - Sensitive Android directories to protect: `/`, `/system`, `/data`, `/boot`, `/sdcard`.
   - In addition to regex pattern hardening, a defense-in-depth token check in `validate_adb_command` analyzes `clean.split()`: if `parts[0] == "rm"`, any command with recursive/force flags targeting root, sensitive paths, or relative system paths is blocked.

### 2.2 DeepFace Sentry Consistency Reasoning
1. **Mock Fidelity**:
   - Automated tests, CI environments, and systems lacking physical webcams or pre-downloaded 512-dimensional Facenet weights run in mock mode.
   - Sentry security behavior (locking the session or sounding an alert after 3 consecutive stranger sightings) must function identically in mock mode so that integration tests, UI alerts, and telemetry broadcast pipelines can be tested reliably without GPU/hardware dependencies.
2. **Implementation Alignment**:
   - Calling `self._record_stranger("Face did not match owner reference in mock mode")` directly reuses the existing `_record_stranger` method.
   - This increments `self._stranger_streak`, returns `"STRANGER"` on attempts 1 and 2, and automatically transitions to `"STRANGER_SENTRY_ALERT"` on attempt 3.
   - When an owner face matches in mock mode, resetting `self._stranger_streak = 0` mirrors the behavior of `_authenticate_deepface:149`.

---

## 3. Caveats

1. **Read-Only Scope**:
   - `explorer_m5_iter2_2` has not modified any source code in `backend/` or `tests/`.
   - All proposed modifications are provided as exact line-numbered blueprints for the implementer agent (`worker_m5_iter2`).
2. **Benign Command False Positives**:
   - Safe ADB commands such as `rm myfile.txt` (local non-sensitive file), `ls -la /sdcard`, `cat /system/build.prop`, `screencap -p /sdcard/screenshot.png`, `input tap`, and `input text` were empirically verified against the proposed regex and token filter to ensure 0% false positives.
3. **Environment Invariance**:
   - When DeepFace is installed and active, `authenticate_frame()` routes to `_authenticate_deepface()`. When DeepFace is absent or disabled, it routes to `_authenticate_mock()`. Both code paths will now exhibit identical stranger streak and sentry alert semantics.

---

## 4. Conclusion & Concrete Blueprint

### 4.1 Blueprint 1: `backend/senses/mobilerun_service.py`

#### A. Harden `DANGEROUS_COMMAND_PATTERNS` (Line 20)
**Target File**: `backend/senses/mobilerun_service.py`  
**Lines**: 19–21  

**Before**:
```python
DANGEROUS_COMMAND_PATTERNS = [
    r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f?[a-zA-Z]*\s+)?(\/|\/system|\/data|\/boot)",
    r"\bformat\b",
```

**After**:
```python
DANGEROUS_COMMAND_PATTERNS = [
    r"\brm\s+(?:-[a-zA-Z0-9-]+\s+)*[\"']?(?:\/|\/system|\/data|\/boot|\/sdcard)",
    r"\bformat\b",
```

#### B. Reject Whitespace & Add Tokenized Defense in `validate_adb_command` (Lines 83–91)
**Target File**: `backend/senses/mobilerun_service.py`  
**Lines**: 83–91  

**Before**:
```python
    def validate_adb_command(self, cmd: str) -> bool:
        if not cmd or not isinstance(cmd, str):
            return False
        clean = cmd.strip()
        for pattern in DANGEROUS_COMMAND_PATTERNS:
            if re.search(pattern, clean, re.IGNORECASE):
                logger.warning("MobileRun safety guard blocked dangerous command: %s", clean)
                return False
        return True
```

**After**:
```python
    def validate_adb_command(self, cmd: str) -> bool:
        if not cmd or not isinstance(cmd, str) or not cmd.strip():
            return False
        clean = cmd.strip()
        for pattern in DANGEROUS_COMMAND_PATTERNS:
            if re.search(pattern, clean, re.IGNORECASE):
                logger.warning("MobileRun safety guard blocked dangerous command: %s", clean)
                return False

        # Token-based verification for split-flag destructive command evasion
        parts = clean.split()
        if parts and parts[0].lower() == "rm":
            args = [p.lower() for p in parts[1:]]
            flags = {a for a in args if a.startswith("-")}
            targets = [a.strip("\"'`") for a in args if not a.startswith("-")]
            is_recursive = any("r" in f or "--recursive" in f for f in flags)
            is_forced = any("f" in f or "--force" in f for f in flags)
            dangerous_targets = {"/", "/system", "/data", "/boot", "/sdcard", "system", "data", "boot", "sdcard"}
            for t in targets:
                if t in dangerous_targets or t.startswith(("/system", "/data", "/boot", "/sdcard")):
                    logger.warning("MobileRun safety guard blocked rm targeting sensitive path: %s", clean)
                    return False
                if (is_recursive or is_forced) and (t == "/" or t.startswith("/")):
                    logger.warning("MobileRun safety guard blocked destructive rm: %s", clean)
                    return False

        return True
```

---

### 4.2 Blueprint 2: `backend/senses/deepface_sentry.py`

#### A. Synchronize Mock Stranger Streak & Sentry Alert (Lines 193–212)
**Target File**: `backend/senses/deepface_sentry.py`  
**Lines**: 193–212  

**Before**:
```python
            if min_dist <= self.distance_threshold:
                return {
                    "authenticated": True,
                    "user": "owner",
                    "confidence": 0.96,
                    "distance": round(min_dist, 3),
                    "liveness_passed": True,
                    "anti_spoofing": {"passed": True, "score": 0.98},
                    "status": "OWNER_VERIFIED",
                }

        return {
            "authenticated": False,
            "user": None,
            "confidence": 0.15,
            "distance": 0.85,
            "liveness_passed": True,
            "anti_spoofing": {"passed": True, "score": 0.95},
            "status": "STRANGER",
        }
```

**After**:
```python
            if min_dist <= self.distance_threshold:
                self._stranger_streak = 0
                return {
                    "authenticated": True,
                    "user": "owner",
                    "confidence": 0.96,
                    "distance": round(min_dist, 3),
                    "liveness_passed": True,
                    "anti_spoofing": {"passed": True, "score": 0.98},
                    "status": "OWNER_VERIFIED",
                }

        return self._record_stranger("Face did not match owner reference in mock mode")
```

---

## 5. Verification Method

Once `worker_m5_iter2` implements the changes, run the following verification steps:

### 5.1 Verify `validate_adb_command` Hardening
Execute this verification one-liner in PowerShell:
```powershell
python -c "from backend.senses.mobilerun_service import MobileRunService; s = MobileRunService(); assert s.validate_adb_command('   ') is False, 'Whitespace allowed!'; assert s.validate_adb_command('rm -r -f /system') is False, 'Split flag /system allowed!'; assert s.validate_adb_command('rm -f -r /data') is False, 'Split flag /data allowed!'; assert s.validate_adb_command('input tap 100 200') is True, 'Benign command blocked!'; assert s.validate_adb_command('rm myfile.txt') is True, 'Benign rm blocked!'; print('MOBILERUN VALIDATION HARDENING VERIFIED: 100% OK')"
```
- **Expected Output**: `MOBILERUN VALIDATION HARDENING VERIFIED: 100% OK`

### 5.2 Verify `DeepFaceSentry` Mock Stranger Streak & Sentry Alert
Execute this verification one-liner in PowerShell:
```powershell
python -c "import numpy as np; from backend.senses.deepface_sentry import DeepFaceSentry; s = DeepFaceSentry(); f = np.ones((50,50,3), dtype=np.uint8)*100; r1 = s.authenticate_frame(f); assert r1['status'] == 'STRANGER' and s._stranger_streak == 1, 'Attempt 1 failed'; r2 = s.authenticate_frame(f); assert r2['status'] == 'STRANGER' and s._stranger_streak == 2, 'Attempt 2 failed'; r3 = s.authenticate_frame(f); assert r3['status'] == 'STRANGER_SENTRY_ALERT' and s._stranger_streak == 3, 'Attempt 3 alert failed!'; print('DEEPFACE SENTRY MOCK STREAK & ALERT VERIFIED: 100% OK')"
```
- **Expected Output**: `DEEPFACE SENTRY MOCK STREAK & ALERT VERIFIED: 100% OK`

### 5.3 Run Full Adversarial Vision & Mobile Test Suite
```powershell
python -m unittest tests.test_adversarial_m5_vision_mobile
```
- **Expected Output**: All tests pass cleanly (`OK`).

### 5.4 Run Milestone M5 & Full E2E Test Suite
```powershell
python tests/e2e/runner.py --milestone M5
python tests/e2e/runner.py
```
- **Expected Output**: `RESULT: SUCCESS (All active requirements satisfied)` across all 250 tests.
