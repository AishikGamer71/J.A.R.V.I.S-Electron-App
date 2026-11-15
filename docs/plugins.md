# Antigravity Plugins Configuration & Audit

**Repository:** J.A.R.V.I.S. Desktop Assistant  
**Notice:** Do not edit plugin files directly. Plugin enable/disable state must be adjusted via the Antigravity Plugins UI.

---

## 1. Plugin Keep / Disable Recommendations

The following table reviews the installed plugins for Antigravity and provides recommendations based on relevance to the J.A.R.V.I.S. Windows 11 Electron HUD + Python FastAPI desktop system:

| Plugin Name | Category | Status Recommendation | Justification / Notes |
|---|---|---|---|
| **ponytail** | Dev Mode / Minimalism | **KEEP** (Active) | Senior engineer minimalism: keeps changes small, avoids over-engineering, enforces YAGNI and clean diffs. |
| **modern-web-guidance** | Frontend Guidance | **KEEP** (Active) | Essential modern HTML/CSS/Tailwind/React 19 best practices; keeps UI code grounded in current web standards. |
| **agent-skills** | Core Engineering | **KEEP** (Active) | Core engineering workflows: test-driven development, code reviews, debugging, security, and verification loops. |
| **chrome-devtools-plugin** | Inspection & QA | **KEEP** (Active) | Required for Chrome DevTools MCP inspection of the Electron renderer HUD during runtime and smoke checks. |
| **coderabbit** | Code Quality | **KEEP** (Active) | Multi-axis code reviews, security reviews, and verification of diffs before checkpoint commits. |
| **gemini-api** | LLM / Model Dev | **KEEP** (Active) | Reference documentation and SDK usage patterns for Gemini API multimodal integrations in J.A.R.V.I.S. |
| **science** | Scientific Domain | **DISABLE** | Domain-specific biological, chemical, and genomic tools (AlphaFold, ChEMBL, PDB, NCBI). Irrelevant to desktop assistant system. |
| **android-cli-plugin** | Mobile Development | **DISABLE** | Android CLI and AVD emulator management. J.A.R.V.I.S. is strictly a Windows 11 desktop assistant. |
| **gcalendar** | Workspace Productivity| **OPTIONAL / DISABLE** | Google Calendar integration. Not needed for core desktop build/restructure work unless testing calendar tools. |

---

## 2. Managing Plugins

To adjust active plugins:
1. Open the **Plugins Manager** in the Antigravity UI.
2. Toggle off the plugins marked **DISABLE** above to reduce prompt context overhead and speed up inference.
3. Keep **ponytail**, **modern-web-guidance**, **agent-skills**, and **chrome-devtools-plugin** enabled.
