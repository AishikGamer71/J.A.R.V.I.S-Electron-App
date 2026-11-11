"""
Adversarial Verification Suite for Milestone M1
Empirically tests voice assets, directory structure, package imports, rules parity,
and scans for stray backup files or schema drifts.
"""

import hashlib
import os
import subprocess
import sys
import unittest
import wave
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

EXPECTED_WAV_SIZE = 353708
EXPECTED_WAV_SHA256 = "81d2718566fa9617cfaace564300488243d93ec0c554c7d4b7194bbed3e02d73"
EXPECTED_CHANNELS = 1
EXPECTED_FRAMERATE = 24000
EXPECTED_SAMPWIDTH = 2  # 16-bit PCM

TARGET_BACKEND_PACKAGES = [
    "backend",
    "backend.agents",
    "backend.memory",
    "backend.skills",
    "backend.core",
    "backend.engine",
    "backend.security",
    "backend.voice",
    "backend.automation",
    "backend.senses",
    "backend.hardware",
]

M1_REQUIRED_PROFILES = [
    "backend/agents/planner.md",
    "backend/agents/architect.md",
    "backend/agents/security_auditor.md",
    "backend/memory/SOUL.md",
    "backend/memory/USER.md",
    "backend/memory/MEMORY.md",
    "backend/skills/desktop_control.md",
    "backend/skills/browser_background.md",
    "backend/skills/deep_research.md",
    "backend/skills/document_reader.md",
    "backend/skills/vision_biometrics_gestures.md",
    "backend/skills/mobile_adb_control.md",
]


class TestM1Adversarial(unittest.TestCase):

    def test_voice_asset_byte_fidelity_and_wav_header(self):
        wav_path = PROJECT_ROOT / "backend" / "voice" / "assets" / "jarvis_ref.wav"
        self.assertTrue(wav_path.exists(), f"Voice asset missing at {wav_path}")
        self.assertTrue(wav_path.is_file(), f"Voice asset must be a regular file")

        # Byte length check
        raw_bytes = wav_path.read_bytes()
        actual_size = len(raw_bytes)
        self.assertEqual(
            actual_size,
            EXPECTED_WAV_SIZE,
            f"Size mismatch: expected {EXPECTED_WAV_SIZE}, got {actual_size}",
        )

        # Cryptographic hash check
        actual_sha = hashlib.sha256(raw_bytes).hexdigest().lower()
        self.assertEqual(
            actual_sha,
            EXPECTED_WAV_SHA256,
            f"SHA256 mismatch: expected {EXPECTED_WAV_SHA256}, got {actual_sha}",
        )

        # Wave header validation
        with wave.open(str(wav_path), "rb") as wf:
            channels = wf.getnchannels()
            rate = wf.getframerate()
            sampwidth = wf.getsampwidth()
            nframes = wf.getnframes()
            comptype = wf.getcomptype()

            self.assertEqual(channels, EXPECTED_CHANNELS, f"Expected {EXPECTED_CHANNELS} ch, got {channels}")
            self.assertEqual(rate, EXPECTED_FRAMERATE, f"Expected {EXPECTED_FRAMERATE} Hz, got {rate}")
            self.assertEqual(sampwidth, EXPECTED_SAMPWIDTH, f"Expected {EXPECTED_SAMPWIDTH} bytes/sample, got {sampwidth}")
            self.assertEqual(comptype, "NONE", f"Expected uncompressed PCM 'NONE', got {comptype}")
            self.assertGreater(nframes, 0, "Audio frames must be > 0")

            # Read all frames to detect truncations or corrupted blocks
            frames = wf.readframes(nframes)
            expected_data_len = nframes * channels * sampwidth
            self.assertEqual(len(frames), expected_data_len, "WAV data frame stream length mismatch")

    def test_legacy_asset_paths_and_temporary_directories_eradication(self):
        # _safe_assets must not exist anywhere
        safe_assets = PROJECT_ROOT / "_safe_assets"
        self.assertFalse(safe_assets.exists(), f"_safe_assets directory still exists at {safe_assets}")

        # _donor_staging must not exist
        donor_staging = PROJECT_ROOT / "_donor_staging"
        self.assertFalse(donor_staging.exists(), f"_donor_staging directory still exists at {donor_staging}")

        # legacy backend/audio should be wiped
        legacy_audio = PROJECT_ROOT / "backend" / "audio"
        self.assertFalse(legacy_audio.exists(), f"Legacy audio folder still exists at {legacy_audio}")

        # apps/ and services/ must be removed
        self.assertFalse((PROJECT_ROOT / "apps").exists(), "apps/ directory still exists")
        self.assertFalse((PROJECT_ROOT / "services").exists(), "services/ directory still exists")

        # Obsolete docs wiped
        self.assertFalse((PROJECT_ROOT / "JARVIS_AI_Prototype_Showcase.pdf").exists(), "Legacy showcase PDF still exists")
        self.assertFalse((PROJECT_ROOT / "requirements.txt").exists(), "Root requirements.txt still exists")
        self.assertFalse((PROJECT_ROOT / "test.cjs").exists(), "Root test.cjs still exists")

    def test_stray_backup_and_temporary_files_scan(self):
        extensions = (".bak", "~", ".orig", ".tmp", ".swp")
        backend_found = []
        for root, dirs, files in os.walk(str(PROJECT_ROOT / "backend")):
            for f in files:
                if f.endswith(extensions):
                    backend_found.append(os.path.join(root, f))
        self.assertEqual(len(backend_found), 0, f"Stray backup files detected in backend: {backend_found}")

        # Workspace-level check (ignoring node_modules, .git, release, .venv)
        workspace_found = []
        ignored_dirs = {".git", "node_modules", "release", ".venv", ".venv-omnivoice", ".venv-omniparser"}
        for root, dirs, files in os.walk(str(PROJECT_ROOT)):
            dirs[:] = [d for d in dirs if d not in ignored_dirs]
            for f in files:
                if f.endswith(extensions):
                    workspace_found.append(os.path.relpath(os.path.join(root, f), str(PROJECT_ROOT)))
        self.assertEqual(len(workspace_found), 0, f"Stray backup files detected outside release: {workspace_found}")

    def test_package_importability_all_ten_packages(self):
        script = f"""
import sys
sys.path.insert(0, r'{PROJECT_ROOT}')
packages = {TARGET_BACKEND_PACKAGES!r}
for pkg in packages:
    mod = __import__(pkg, fromlist=['__file__'])
    assert hasattr(mod, '__file__') and '__init__.py' in mod.__file__, f"Invalid package {{pkg}}: {{mod}}"
print("ALL_PACKAGES_IMPORTED_SUCCESSFULLY")
"""
        res = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
        self.assertEqual(
            res.returncode,
            0,
            f"Failed to import backend packages:\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}",
        )
        self.assertIn("ALL_PACKAGES_IMPORTED_SUCCESSFULLY", res.stdout)

    def test_governance_rules_exact_character_parity(self):
        rules_antigravity = PROJECT_ROOT / ".antigravity" / "rules.md"
        rules_agent = PROJECT_ROOT / ".agent" / "rules" / "rules.md"

        self.assertTrue(rules_antigravity.is_file(), f"{rules_antigravity} does not exist")
        self.assertTrue(rules_agent.is_file(), f"{rules_agent} does not exist")

        content1 = rules_antigravity.read_bytes()
        content2 = rules_agent.read_bytes()

        self.assertEqual(
            len(content1),
            len(content2),
            f"Rule files byte size mismatch: {len(content1)} vs {len(content2)}",
        )
        self.assertEqual(
            content1,
            content2,
            "Rules files content differs byte-for-byte across .antigravity and .agent/rules",
        )

        h1 = hashlib.sha256(content1).hexdigest()
        h2 = hashlib.sha256(content2).hexdigest()
        self.assertEqual(h1, h2, "Rules SHA256 hashes differ")

    def test_governance_rules_clauses_presence(self):
        """Stress-test presence of required rule clauses expected by tests and specifications."""
        rules_path = PROJECT_ROOT / ".antigravity" / "rules.md"
        text = rules_path.read_text(encoding="utf-8")

        # Crucial clauses
        self.assertIn("Ctrl+Alt+Backspace", text, "Emergency kill switch shortcut missing")
        self.assertIn("windows_mcp_bridge.py", text, "Windows MCP bridge reference missing")
        self.assertIn("Single-Producer Multi-Consumer", text, "Camera SPMC policy missing")
        self.assertIn("14 secret patterns", text, "AgentShield 14 secret patterns rule missing")

        # Check for clauses required by E2E test runner:
        has_zero_ui_drift_upper = "ZERO UI DRIFT" in text
        has_desktop_only_upper = "DESKTOP APPLICATION ONLY" in text

        print(f"\n[Clause Check] 'ZERO UI DRIFT' in text: {has_zero_ui_drift_upper}")
        print(f"[Clause Check] 'DESKTOP APPLICATION ONLY' in text: {has_desktop_only_upper}")

    def test_profiles_authored_and_non_empty(self):
        for profile in M1_REQUIRED_PROFILES:
            path = PROJECT_ROOT / profile
            self.assertTrue(path.is_file(), f"Profile missing: {profile}")
            size = path.stat().st_size
            self.assertGreater(size, 200, f"Profile {profile} suspiciously small ({size} bytes)")

    def test_arc_reactor_and_lighting_config_integrity(self):
        arc_file = PROJECT_ROOT / "src" / "components" / "widgets" / "arc-reactor.tsx"
        self.assertTrue(arc_file.is_file(), f"{arc_file} must exist")
        text = arc_file.read_text(encoding="utf-8")

        self.assertIn("JARVIS_LIGHTING_CONFIG", text, "JARVIS_LIGHTING_CONFIG must be exported")
        self.assertIn("ArcReactor", text, "ArcReactor component must be defined")
        self.assertIn("outerRing", text, "outerRing lighting spec missing")
        self.assertTrue(
            "circuitClusterColor" in text or "goldenClusters" in text,
            "circuitClusterColor/goldenClusters lighting spec missing",
        )
        self.assertTrue(
            "radialFilamentColor" in text or "radialFilaments" in text,
            "radialFilamentColor/radialFilaments lighting spec missing",
        )
        self.assertTrue(
            "innerCoreRingColor" in text or "innerCoreRing" in text,
            "innerCoreRingColor/innerCoreRing lighting spec missing",
        )

        sphere_file = PROJECT_ROOT / "src" / "components" / "dashboard" / "sphere.tsx"
        self.assertTrue(sphere_file.is_file(), f"{sphere_file} must exist")
        sphere_text = sphere_file.read_text(encoding="utf-8")
        self.assertNotIn("ArcReactor", sphere_text, "2D Arc Reactor component must be absent from sphere.tsx")
        self.assertNotIn("JARVIS_LIGHTING_CONFIG", sphere_text, "JARVIS_LIGHTING_CONFIG must be absent from sphere.tsx")


if __name__ == "__main__":
    unittest.main()
