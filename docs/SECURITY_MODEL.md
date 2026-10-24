# Security Model: J.A.R.V.I.S Security & Isolation Layer

## 1. Overview
J.A.R.V.I.S operates with an explicit, defense-in-depth security model to ensure autonomous tools and background subagents cannot compromise the host operating system.

## 2. Risk Classification Matrix

Every tool registered in `tools/registry.py` must declare a static risk level:

| Risk Level | Description | Execution Path | Example Tools |
|---|---|---|---|
| **LOW** | Read-only operations with no persistent side effects | Direct Execution | `read_file` (scoped), `get_system_time`, `calculate` |
| **MEDIUM** | Network access, non-destructive system queries, screenshot capture | Permission Check + Audit Log | `web_search`, `take_screenshot`, `browser_open_url` |
| **HIGH** | File writes/deletions, process termination, external CLI commands | **User Confirmation Bridge** + Docker Sandbox | `write_file`, `kill_process`, `gh_cli_action`, `git_push` |
| **CRITICAL** | System-wide configuration changes, credential manipulation, arbitrary bash/powershell | **Mandatory Explicit Confirmation** + Full Isolation | `execute_shell_command`, `modify_registry`, `update_env_secrets` |

## 3. Confirmation Bridge Flow
```
Agent -> Tool Execution Request
            |
      Risk Classifier (Risk >= MEDIUM)
            |
      Permission Store (Is auto-approved for this session?)
       /           \
     YES           NO
      |             \
      |          Confirmation Bridge -> Electron UI Modal
      |                 \
      |            User approves / denies (30s timeout auto-deny)
      v                 /
Audit Log Recording <--+
      |
Sandbox Runner (if HIGH/CRITICAL: runs in Docker container with read-only root)
```

## 4. Secret Management
- Secrets and API keys must never be hardcoded in repository files or stored in unencrypted local state.
- In production, secrets are managed through Infisical or encrypted OS Keyrings (`keytar` / Windows DPAPI).
