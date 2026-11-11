---
name: desktop_control
description: Native Windows COM UIAutomation and vision-guided OSWorld desktop automation.
trigger: control desktop, click button, open window, type into app, automate GUI, native app
tools:
  - windows_mcp_snapshot
  - windows_mcp_click
  - windows_mcp_type
  - windows_mcp_app
  - windows_mcp_shortcut
  - agent_s3_visual_task
---

# Desktop Control Skill

## Purpose & Overview
Enables J.A.R.V.I.S. to interact seamlessly with native Windows applications, desktop windows, dialog boxes, and controls. Implements a 2-stage execution hierarchy: ultra-fast native COM UIAutomation first, escalating to visual VLM grounding only when necessary.

## Tool Routing Hierarchy

### Stage 1: Native COM UIAutomation (<10ms execution)
Always prefer native UIA tools for standard Windows controls:
1. `windows_mcp_snapshot(use_dom=False)`: Inspect accessibility tree, retrieve control names, bounding boxes, and identifiers.
2. `windows_mcp_click(x, y, button="left", clicks=1)`: Native mouse click on target coordinates.
3. `windows_mcp_type(x, y, text, clear=False, press_enter=False)`: Native text input into focused control.
4. `windows_mcp_app(action, name)`: Launch or focus localized Start Menu applications.
5. `windows_mcp_shortcut(keys)`: Send standard Windows keyboard shortcuts (e.g., `["ctrl", "s"]`, `["win", "d"]`).

### Stage 2: Visual Grounding Escalation (OmniParser V2 + Agent-S3)
Escalate to `agent_s3_visual_task(instruction)` ONLY under the following conditions:
- Target application renders on custom canvas, DirectX, OpenGL, or Electron surfaces without accessible UIA elements.
- Target control is an unlabelled graphic icon or complex toolbar button.
- Process: Captures screenshot, requests Set-of-Mark (`SoM`) detection from OmniParser service on port 8002, maps mark coordinates, and executes `pyautogui` action.

## Safety & Deadlock Guardrails
1. **HWND Deadlock Prevention**: The J.A.R.V.I.S. Electron application window (`electron.exe` or title matching "JARVIS") is permanently excluded from accessibility tree inspection to prevent UI thread deadlocks.
2. **Termination Validation**: Always evaluate `action[0].strip().upper() in ("DONE", "FAIL")` before dispatching.
3. **Emergency Abort**: Global hotkey `Ctrl+Alt+Backspace` instantly terminates all desktop actions in $<1$ ms.
