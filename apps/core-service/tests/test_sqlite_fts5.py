import pytest
import os
import tempfile
from pathlib import Path
from jarvis.domain.entities.models import ChatMessage, MessageRole, ModelTier
from jarvis.memory.sqlite_store import SQLiteMemoryStore


@pytest.mark.asyncio
async def test_sqlite_session_and_fts5_search(tmp_path: Path):
    db_path = tmp_path / "test_jarvis.db"
    store = SQLiteMemoryStore(db_path=db_path)
    await store.init_db()

    # 1. Create a session
    session = await store.create_session(title="Quantum Computing Research")
    assert session.id is not None
    assert session.title == "Quantum Computing Research"

    # 2. Add messages
    msg1 = ChatMessage(
        session_id=session.id,
        role=MessageRole.USER,
        content="Can you explain Shor's algorithm for quantum factorization?"
    )
    await store.save_message(msg1)

    msg2 = ChatMessage(
        session_id=session.id,
        role=MessageRole.ASSISTANT,
        content="Shor's algorithm is a quantum computer algorithm for finding prime factors in polynomial time.",
        tier=ModelTier.TIER2_BALANCED,
        model="gemini/gemini-1.5-flash"
    )
    await store.save_message(msg2)

    # 3. Retrieve messages
    messages = await store.get_messages(session_id=session.id)
    assert len(messages) == 2
    assert messages[0].content == msg1.content
    assert messages[1].content == msg2.content

    # 4. Full Text Search (FTS5) test
    search_results = await store.search_messages("factorization")
    assert len(search_results) >= 1
    assert search_results[0].session_id == session.id

    search_shor = await store.search_messages("quantum")
    assert len(search_shor) == 2

    # 5. List sessions
    sessions = await store.list_sessions()
    assert len(sessions) == 1
    assert sessions[0].id == session.id
