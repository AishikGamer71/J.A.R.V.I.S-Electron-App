import pytest
from pathlib import Path
from jarvis.config.settings import settings
from jarvis.agents.inbox import AgentInbox, InboxTaskStatus
from jarvis.agents.research_agent import ResearchAgent
from jarvis.agents.file_agent import FileAgent
from jarvis.agents.planning_agent import PlanningAgent
from jarvis.security.permission_store import PermissionStore
from jarvis.security.audit_log import AuditLog
from jarvis.tools.registry import tool_registry


@pytest.fixture
def agent_test_env(tmp_path: Path):
    db_path = tmp_path / "agents_test.db"
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


@pytest.mark.asyncio
async def test_agent_inbox_lifecycle(agent_test_env):
    inbox = AgentInbox(db_path=agent_test_env["db_path"])
    await inbox.init_db()

    # 1. Create task
    task = await inbox.create_task(
        agent_name="research_agent",
        input_payload={"query": "quantum gravity"}
    )
    assert task.task_id is not None
    assert task.status == InboxTaskStatus.PENDING

    # 2. Update status and artifacts
    artifacts = [{"type": "source", "url": "https://arxiv.org/abs/example"}]
    await inbox.update_status(
        task_id=task.task_id,
        status=InboxTaskStatus.COMPLETED,
        output_payload={"summary": "Quantum gravity reconciles QM with GR."},
        artifacts=artifacts
    )

    # 3. Retrieve task
    retrieved = await inbox.get_task(task.task_id)
    assert retrieved is not None
    assert retrieved.status == InboxTaskStatus.COMPLETED
    assert len(retrieved.artifacts) == 1
    assert retrieved.artifacts[0]["url"] == "https://arxiv.org/abs/example"

    # 4. List tasks
    all_tasks = await inbox.list_tasks(agent_name="research_agent")
    assert len(all_tasks) == 1


@pytest.mark.asyncio
async def test_research_agent_execution(agent_test_env):
    from jarvis.agents.inbox import agent_inbox
    from jarvis.security.permission_store import permission_store
    from jarvis.security.audit_log import audit_log

    await agent_inbox.init_db()
    await permission_store.init_db()
    await audit_log.init_db()

    agent = ResearchAgent()
    task_entry = await agent_inbox.create_task(agent_name=agent.name, input_payload={"query": "artificial intelligence"})

    res = await agent.run(task="artificial intelligence", context={"query": "artificial intelligence"}, task_id=task_entry.task_id)
    assert res.success is True
    assert len(res.artifacts) >= 1
    assert "artificial intelligence" in res.summary.lower()

    # Verify updated in inbox
    inbox_task = await agent_inbox.get_task(task_entry.task_id)
    assert inbox_task.status == InboxTaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_file_agent_execution(agent_test_env):
    from jarvis.agents.inbox import agent_inbox
    from jarvis.security.permission_store import permission_store
    from jarvis.security.audit_log import audit_log

    await agent_inbox.init_db()
    await permission_store.init_db()
    await audit_log.init_db()

    # Grant write_file for testing
    await permission_store.grant("write_file", scope="file_agent")

    agent = FileAgent()
    
    # 1. Write file
    write_task = await agent_inbox.create_task(agent_name=agent.name, input_payload={"path": "report.txt"})
    write_res = await agent.run(
        task="write file",
        context={"action": "write", "path": "report.txt", "content": "Autonomous Core Initialized"},
        task_id=write_task.task_id
    )
    assert write_res.success is True

    # 2. Read file
    read_task = await agent_inbox.create_task(agent_name=agent.name, input_payload={"path": "report.txt"})
    read_res = await agent.run(
        task="read file",
        context={"action": "read", "path": "report.txt"},
        task_id=read_task.task_id
    )
    assert read_res.success is True
    assert read_res.output_data["data"] == "Autonomous Core Initialized"
    assert read_res.artifacts[0]["content_snippet"] == "Autonomous Core Initialized"


@pytest.mark.asyncio
async def test_planning_agent_orchestration_and_flat_context(agent_test_env):
    from jarvis.agents.inbox import agent_inbox
    from jarvis.security.permission_store import permission_store
    from jarvis.security.audit_log import audit_log

    await agent_inbox.init_db()
    await permission_store.init_db()
    await audit_log.init_db()

    planner = PlanningAgent()

    # Goal: search the web and summarize
    goal = "Search the web for quantum algorithms"
    plan_res = await planner.run(task=goal)

    assert plan_res.success is True
    assert plan_res.output_data["delegated_agent"] == "research_agent"
    assert plan_res.output_data["inbox_status"] == InboxTaskStatus.COMPLETED
    assert len(plan_res.artifacts) >= 1

    # Verify parent planner output is concise executive summary
    assert len(plan_res.summary) > 0
