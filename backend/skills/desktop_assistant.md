---
name: desktop_assistant
description: Desktop assistant skill for native Windows automation, GUI control, application management, and OSWorld tasks.
alias_of: desktop_control
trigger: desktop assistant, control desktop, click button, open window, type into app, automate GUI, native app, manage window
tools:
  - windows_mcp_snapshot
  - windows_mcp_click
  - windows_mcp_type
  - windows_mcp_app
  - windows_mcp_shortcut
  - agent_s3_visual_task
---

# Desktop Assistant Skill

## Purpose & Overview
The Desktop Assistant skill provides autonomous desktop interaction, system automation, and native Windows control for J.A.R.V.I.S. It operates in tandem with `desktop_control.md` to offer a 2-stage execution hierarchy: ultra-fast native COM UIAutomation first (<10ms), escalating to visual VLM grounding (OmniParser V2 + Agent-S3) only when necessary.

## Tool Routing Hierarchy

### Stage 1: Native COM UIAutomation (<10ms execution)
Standard Windows controls, dialogs, and accessibility elements route directly to:
1. `windows_mcp_snapshot(use_dom=False)`: Inspect accessibility tree, retrieve control names, bounding boxes, and identifiers.
2. `windows_mcp_click(x, y, button="left", clicks=1)`: Native mouse click on target coordinates.
3. `windows_mcp_type(x, y, text, clear=False, press_enter=False)`: Native text input into focused control.
4. `windows_mcp_app(action, name)`: Launch or focus localized Start Menu applications.
5. `windows_mcp_shortcut(keys)`: Send standard Windows keyboard shortcuts (e.g., `["ctrl", "s"]`, `["win", "d"]`).

### Stage 2: Visual Grounding Escalation (OmniParser V2 + Agent-S3)
Escalate to `agent_s3_visual_task(instruction)` ONLY under the following conditions:
- Target application renders on custom canvas, DirectX, OpenGL, or Electron surfaces without accessible UIA elements.
- Target control is an unlabelled graphic icon or complex toolbar button.
- Execution flow: Captures screenshot, requests Set-of-Mark (`SoM`) detection from OmniParser service on port 8002, maps mark coordinates, and executes `pyautogui` action.

## Safety & Deadlock Guardrails
1. **HWND Deadlock Prevention**: The J.A.R.V.I.S. Electron application window (`electron.exe` or title matching "JARVIS") is permanently excluded from accessibility tree inspection to prevent UI thread deadlocks.
2. **Termination Validation**: Always evaluate `action[0].strip().upper() in ("DONE", "FAIL")` before dispatching desktop tasks.
3. **Emergency Abort**: Global hotkey `Ctrl+Alt+Backspace` instantly terminates all desktop actions in $<1$ ms.
