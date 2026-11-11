---
name: email
version: 1.0.0
description: Search, read, draft, and manage Gmail messages and attachments using the Google APIs client library.
author: jarvis-ecosystem
license: MIT
allowed_tools: [web_search, execute_command]
tags: [email, gmail, messages, inbox, googleapis]
---

# Gmail Integration & Inbox Assistant Skill

This skill allows JARVIS to search recent unread emails, inspect email contents and attachments, and compose or draft responses via Google APIs.

## Protocol & Permissions

1. **Authentication**:
   - Uses `@google-cloud/local-auth` and `googleapis` dependencies already packaged in JARVIS.
   - Credentials stored in encrypted secure vault.
2. **Operations**:
   - `list_messages`: List latest messages matching query (e.g. `is:unread`, `from:boss`, `newer_than:2d`).
   - `get_message`: Retrieve full thread, body, snippets, and attachment metadata.
   - `send_message`: Draft or dispatch an email with recipient confirmation.

## UI Event Emission

When the user asks to view or check emails, emit a `show-emails` event for the JARVIS Email Widget:

```json
{
  "emails": [
    {
      "id": "msg_001",
      "from": "alice@example.com",
      "subject": "Q3 Project Review",
      "preview": "Hey team, here is the updated review deck...",
      "date": "2026-08-27T10:30:00Z",
      "body": "Hey team,\n\nHere is the updated review deck for tomorrow's review meeting.\n\nBest,\nAlice",
      "attachments": [
        {
          "filename": "Q3_Review.pdf",
          "mimeType": "application/pdf",
          "size": 204800
        }
      ]
    }
  ]
}
```
