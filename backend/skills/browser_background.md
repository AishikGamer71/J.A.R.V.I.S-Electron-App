---
name: browser_background
description: Headless background browser automation via Chrome DevTools Protocol (CDP).
trigger: search web, browse website, fill form online, interact with web page, navigate web
tools:
  - browser_use_background
---

# Browser Background Skill

## Purpose & Overview
Executes complex web-based workflows, form fills, navigation, interactive web sessions, and online tasks in the background without hijacking the user's physical mouse cursor or desktop display.

## Operational Instructions
1. **Background CDP Execution**:
   - All browser operations run through `browser_use_background(task, headless=True)` using Chrome DevTools Protocol.
   - Connects to existing Chrome/Edge sessions if `CHROME_CDP_URL` is set, or launches an isolated headless browser instance.
2. **Interactive Tasks**:
   - Use for multi-step web flows: logging into services, submitting web forms, querying portals, scraping dynamic single-page applications.
3. **Cursor Isolation**:
   - Never move, click, or lock the user's physical mouse cursor for web tasks. The user must be free to continue typing or coding while background browsing executes.
4. **Data Handling & Security**:
   - Sensitive inputs (passwords, payment details) must never be emitted into public WebSocket envelopes or terminal logs.
