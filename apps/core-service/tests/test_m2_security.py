import asyncio
from pathlib import Path
import pytest
from unittest.mock import AsyncMock

from jarvis.config.settings import settings
from jarvis.security.audit_log import AuditLog
from jarvis.security.confirmation_bridge import ConfirmationBridge
from jarvis.security.permission_store import PermissionStore
from jarvis.security.risk_classifier import RiskLevel, RiskClassifier
from jarvis.tools.file_tools import read_file_tool, write_file_tool
from jarvis.tools.registry import ToolRegistry
from jarvis.tools.schema import ReadFileInput, WriteFileInput, WebSearchInput
from jarvis.tools.web_tools import web_search_tool


@pytest.fixture
def temp_env(tmp_path: Path):
    db_path = tmp_path / "security_test.db"
    sandbox_dir = tmp_path / "sandbox"
    sandbox_dir.mkdir(parents=True, exist_ok=True)
    
    orig_db = settings.DATABASE_PATH
    orig_sandbox = settings.SANDBOX_ROOT
    settings.DATABASE_PATH = db_path
    settings.SANDBOX_ROOT = sandbox_dir

    yield {
        "db_path": db_path,
        "sandbox_dir": sandbox_dir
    }

    settings.DATABASE_PATH = orig_db
    settings.SANDBOX_ROOT = orig_sandbox


def test_risk_classifier():
    classifier = RiskClassifier()
    assert classifier.classify("read_file") == RiskLevel.LOW
    assert classifier.classify("write_file") == RiskLevel.MEDIUM
    assert classifier.classify("web_search") == RiskLevel.LOW
    assert classifier.classify("execute_command") == RiskLevel.HIGH

    # Path traversal escalation to CRITICAL
    assert classifier.classify("read_file", {"path": "../../etc/passwd"}) == RiskLevel.CRITICAL
    assert classifier.classify("write_file", {"path": "../.env"}) == RiskLevel.CRITICAL

    # Destructive command escalation
    assert classifier.classify("execute_command", {"command": "rm -rf /"}) == RiskLevel.CRITICAL


@pytest.mark.asyncio
async def test_permission_store(temp_env):
    store = PermissionStore(db_path=temp_env["db_path"])
    await store.init_db()

    # 1. Default-deny
    assert await store.check("write_file", "global") is False
    assert await store.check("read_file") is False

    # 2. Grant permission for specific scope
    await store.grant("write_file", "global")
    assert await store.check("write_file", "global") is True
    assert await store.check("write_file", "other_scope") is False

    # 3. Grant wildcard permission
    await store.grant("write_file", "*")
    assert await store.check("write_file", "other_scope") is True

    # 4. Revoke permission
    await store.revoke("write_file", "*")
    await store.revoke("write_file", "global")
    assert await store.check("write_file", "global") is False


@pytest.mark.asyncio
async def test_audit_log(temp_env):
    log = AuditLog(db_path=temp_env["db_path"])
    await log.init_db()

    log_id1 = await log.record(
        tool="write_file",
        args={"path": "test.txt", "content": "Hello"},
        risk_level="MEDIUM",
        outcome="SUCCESS",
        details={"bytes": 5}
    )
    assert log_id1 is not None

    log_id2 = await log.record(
        tool="execute_command",
        args={"cmd": "rm -rf /"},
        risk_level="CRITICAL",
        outcome="BLOCKED_SECURITY_VIOLATION"
    )

    logs = await log.list_logs()
    assert len(logs) == 2
    assert logs[0]["id"] == log_id2
    assert logs[0]["outcome"] == "BLOCKED_SECURITY_VIOLATION"
    assert logs[1]["id"] == log_id1
    assert logs[1]["risk_level"] == "MEDIUM"


@pytest.mark.asyncio
async def test_confirmation_bridge_timeout():
    bridge = ConfirmationBridge()
    # Test auto-deny on short timeout
    approved = await bridge.request_confirmation(
        tool_name="write_file",
        args={"path": "critical.txt"},
        risk_level="MEDIUM",
        timeout_seconds=1
    )
    assert approved is False


@pytest.mark.asyncio
async def test_confirmation_bridge_approval():
    bridge = ConfirmationBridge()
    
    async def simulate_user_approval(cid: str):
        await asyncio.sleep(0.1)
        bridge.resolve_confirmation(cid, approved=True)

    # Listen for broadcast
    async def on_broadcast(frame: dict):
        cid = frame["confirmationId"]
        asyncio.create_task(simulate_user_approval(cid))

    bridge.register_broadcaster(on_broadcast)

    approved = await bridge.request_confirmation(
        tool_name="write_file",
        args={"path": "doc.txt"},
        risk_level="MEDIUM",
        timeout_seconds=5
    )
    assert approved is True


@pytest.mark.asyncio
async def test_sandboxed_file_tools(temp_env):
    # 1. Write file inside sandbox
    write_res = await write_file_tool({"path": "hello.txt", "content": "JARVIS Autonomous Layer"})
    assert write_res["bytes_written"] > 0

    # 2. Read file from sandbox
    content = await read_file_tool({"path": "hello.txt"})
    assert content == "JARVIS Autonomous Layer"

    # 3. Attempt path traversal -> must raise PermissionError
    with pytest.raises(PermissionError):
        await write_file_tool({"path": "../outside.txt", "content": "Malicious"})

    with pytest.raises(PermissionError):
        await read_file_tool({"path": "../../Windows/win.ini"})


@pytest.mark.asyncio
async def test_web_search_tool():
    results = await web_search_tool({"query": "quantum computing", "max_results": 3})
    assert len(results) >= 1
    assert "title" in results[0]
    assert "url" in results[0]


@pytest.mark.asyncio
async def test_tool_registry_pipeline_end_to_end(temp_env):
    from jarvis.security.permission_store import permission_store
    from jarvis.security.audit_log import audit_log
    from jarvis.tools.registry import tool_registry

    await permission_store.init_db()
    await audit_log.init_db()

    # Pre-grant write_file for this test
    await permission_store.grant("write_file")

    # 1. Successful invoke through registry
    res = await tool_registry.invoke(
        name="write_file",
        args={"path": "notes.md", "content": "# Architecture v4"}
    )
    assert res.success is True
    assert res.risk_level == RiskLevel.MEDIUM
    assert res.audit_id is not None

    # 2. Read file back through registry
    read_res = await tool_registry.invoke(
        name="read_file",
        args={"path": "notes.md"}
    )
    assert read_res.success is True
    assert read_res.data == "# Architecture v4"

    # 3. Path traversal attack through registry
    attack_res = await tool_registry.invoke(
        name="write_file",
        args={"path": "../../../system.exe", "content": "bad"}
    )
    # Blocked by risk classifier / confirmation / permission containment
    assert attack_res.success is False
