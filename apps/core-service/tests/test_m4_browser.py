import pytest
from pathlib import Path
from jarvis.config.settings import settings
from jarvis.agents.inbox import AgentInbox, InboxTaskStatus
from jarvis.agents.browser_agent import BrowserAgent
from jarvis.agents.planning_agent import PlanningAgent
from jarvis.tools.browser_tools import (
    browser_open_tool,
    browser_click_tool,
    browser_type_tool,
    browser_screenshot_tool,
    browser_state
)
from jarvis.tools.computer_tools import (
    take_desktop_screenshot_tool,
    list_open_windows_tool,
    open_application_tool
)
from jarvis.security.permission_store import permission_store
from jarvis.security.audit_log import audit_log
from jarvis.tools.registry import tool_registry


@pytest.fixture
def browser_test_env(tmp_path: Path):
    db_path = tmp_path / "browser_test.db"
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
async def test_browser_tools_direct(browser_test_env):
    # 1. Test browser_screenshot on blank page
    ss_res = await browser_screenshot_tool()
    assert ss_res["screenshot_base64"] != ""

    # 2. Mock state and test click & type
    browser_state.current_url = "https://example.com"
    browser_state.current_html = "<html><body><button id='login-btn'>Log in</button><input name='query' /></body></html>"

    click_res = await browser_click_tool({"selector": "login-btn"})
    assert click_res["clicked"] == "login-btn"
    assert click_res["element_found"] is True

    type_res = await browser_type_tool({"selector": "query", "text": "Jarvis 4.0"})
    assert type_res["selector"] == "query"
    assert type_res["typed_length"] == 10


@pytest.mark.asyncio
async def test_computer_tools(browser_test_env):
    # 1. Desktop screenshot
    desk_res = await take_desktop_screenshot_tool({"display_index": 0})
    assert desk_res["resolution"] == "1920x1080"
    assert len(desk_res["screenshot_base64"]) > 0

    # 2. List windows
    win_res = await list_open_windows_tool()
    assert "processes" in win_res
    assert isinstance(win_res["processes"], list)

    # 3. Restricted application check
    with pytest.raises(PermissionError):
        await open_application_tool({"app_name": "malicious_script.bat"})


@pytest.mark.asyncio
async def test_browser_agent_delegation(browser_test_env):
    from jarvis.agents.inbox import agent_inbox
    await agent_inbox.init_db()
    await permission_store.init_db()
    await audit_log.init_db()

    # Pre-grant browser_open for test
    await permission_store.grant("browser_open", scope="browser_agent")

    agent = BrowserAgent()
    task_entry = await agent_inbox.create_task(
        agent_name=agent.name,
        input_payload={"url": "https://example.com", "action": "open"}
    )

    res = await agent.run(
        task="Navigate to example.com",
        context={"action": "open", "url": "https://example.com"},
        task_id=task_entry.task_id
    )

    assert res.success is True
    assert "example.com" in res.summary.lower()

    # Verify inbox status updated
    inbox_task = await agent_inbox.get_task(task_entry.task_id)
    assert inbox_task.status == InboxTaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_planning_agent_browser_intent(browser_test_env):
    from jarvis.agents.inbox import agent_inbox
    await agent_inbox.init_db()
    await permission_store.init_db()
    await audit_log.init_db()

    await permission_store.grant("browser_open", scope="browser_agent")

    planner = PlanningAgent()
    target_agent, ctx = planner.detect_intent("Please navigate to https://example.com")
    assert target_agent == "browser_agent"
    assert "example.com" in ctx["url"]

    # End-to-end goal orchestration
    plan_res = await planner.run("Visit website https://example.com")
    assert plan_res.success is True
    assert plan_res.output_data["delegated_agent"] == "browser_agent"
    assert plan_res.output_data["inbox_status"] == InboxTaskStatus.COMPLETED
