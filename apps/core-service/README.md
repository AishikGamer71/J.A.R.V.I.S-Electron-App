# J.A.R.V.I.S Core Service

Autonomous hexagonal backend engine for J.A.R.V.I.S AI.

## Features
- **FastAPI / WebSocket Control Plane**: Real-time bidirectional communication with Electron and voice services.
- **Dynamic Heuristic Router**: 3-Tier classification with live hardware telemetry and automatic offline Ollama fallback.
- **SQLite + FTS5 Memory**: Full-text indexed conversation store.
- **Process Supervisor**: Automatic crash recovery with exponential backoff.
