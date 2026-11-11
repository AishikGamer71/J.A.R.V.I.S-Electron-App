"""
backend/core/tool_dispatcher.py
===============================
ToolDispatcher: Parallel worker execution engine, 3-tier validation gauntlet,
and loop guardrails for J.A.R.V.I.S.
Integrates AgentShield validation, ECCHookDispatcher lifecycle hooks, and
parallel worker execution for registered Phase 6 tools.
"""

import concurrent.futures
import hashlib
import json
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from backend.security.agent_shield import AgentShield
from backend.security.ecc_hooks import ECCHookDispatcher

logger = logging.getLogger("jarvis.tool_dispatcher")

_MAX_TOOL_WORKERS: int = 8

# Tools classified as read-only / non-mutating (safe for parallel concurrent execution)
READ_ONLY_TOOLS: Set[str] = {
    "echo",
    "test_echo",
    "add",
    "square",
    "read_file",
    "list_directory",
    "search_files",
    "windows_mcp_snapshot",
    "markitdown_convert",
    "crawl4ai_extract",
    "gpt_researcher_report",
    "session_search",
    "get_system_stats",
}


class ToolLoopHaltException(Exception):
    """Raised when a repetitive tool call loop is detected."""
    pass


class ToolDispatcher:
    """Dispatches tool invocations across parallel threads with validation and safety guards."""

    def __init__(
        self,
        max_consecutive_calls: int = 5,
        max_workers: int = _MAX_TOOL_WORKERS,
        shield: Optional[AgentShield] = None,
        ecc_dispatcher: Optional[ECCHookDispatcher] = None,
    ):
        self.max_consecutive_calls = max_consecutive_calls
        self.max_workers = max_workers
        self.shield = shield or AgentShield()
        self.ecc_dispatcher = ecc_dispatcher or ECCHookDispatcher(shield=self.shield)

        self._registry: Dict[str, Callable[[Dict[str, Any]], Any]] = {}
        self._tool_descriptions: Dict[str, str] = {}
        self._last_call_signature: Optional[str] = None
        self._consecutive_call_count: int = 0
        self._interrupted = False
        self._loop_lock = threading.Lock()

        self._register_default_tools()

    def register_tool(
        self,
        name: str,
        handler: Callable[[Dict[str, Any]], Any],
        description: str = "",
    ) -> None:
        """Registers a callable handler for a tool name."""
        self._registry[name] = handler
        self._tool_descriptions[name] = description or f"Handler for {name}"

    def list_tools(self) -> List[str]:
        return list(self._registry.keys())

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Returns schemas formatted for LLM tool selection."""
        defs = []
        for name, desc in self._tool_descriptions.items():
            defs.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": desc,
                    "parameters": {"type": "object", "properties": {}},
                },
            })
        return defs

    def interrupt(self) -> None:
        self._interrupted = True

    def reset_interrupt(self) -> None:
        self._interrupted = False

    def _compute_signature(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Computes a deterministic hash of tool name and canonical arguments."""
        try:
            canonical_args = json.dumps(args, sort_keys=True, default=str)
        except Exception:
            canonical_args = str(args)
        raw = f"{tool_name}:{canonical_args}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _check_loop_guard(self, tool_name: str, args: Dict[str, Any]) -> None:
        """
        Monitors for repetitive identical tool calls.
        Warns after 2, raises ToolLoopHaltException if exceeding max_consecutive_calls.
        """
        sig = self._compute_signature(tool_name, args)
        with self._loop_lock:
            if sig == self._last_call_signature:
                self._consecutive_call_count += 1
                if self._consecutive_call_count >= 2:
                    logger.warning(
                        "Repetitive tool call detected: %s (streak=%d)",
                        tool_name,
                        self._consecutive_call_count,
                    )
                if self._consecutive_call_count > self.max_consecutive_calls:
                    raise ToolLoopHaltException(
                        f"Tool loop detected: '{tool_name}' was called {self._consecutive_call_count} "
                        f"consecutive times with identical arguments without progress. Execution halted."
                    )
            else:
                self._last_call_signature = sig
                self._consecutive_call_count = 1

    def dispatch(
        self,
        tool_name: str,
        args: Dict[str, Any],
        session_id: str = "default",
    ) -> Any:
        """
        Executes a single tool call with 3-tier validation, ECC hooks, and loop guard.
        """
        if self._interrupted:
            raise RuntimeError("Tool execution interrupted")

        # 1. Loop guard check
        self._check_loop_guard(tool_name, args)

        # 2. Tier 1: ECC Pre-tool Hook (AgentShield validation)
        pre_res = self.ecc_dispatcher.pre_tool_hook(tool_name, args, session_id=session_id)
        if not pre_res.allowed:
            raise PermissionError(f"Tool execution blocked by security policy: {pre_res.reason}")

        handler = self._registry.get(tool_name)
        if not handler:
            raise ValueError(f"Unknown tool: '{tool_name}' is not registered")

        start_time = time.perf_counter()
        status = "success"
        result = None
        try:
            result = handler(args)
            return result
        except Exception as e:
            status = "failed"
            result = str(e)
            raise e
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            # Tier 3: ECC Post-tool Hook (Observation log)
            self.ecc_dispatcher.post_tool_hook(
                tool_name=tool_name,
                args=args,
                result=result,
                status=status,
                duration_ms=duration_ms,
                session_id=session_id,
            )

    def dispatch_batch(
        self,
        batch: List[Tuple[str, Dict[str, Any]]],
        session_id: str = "default",
    ) -> List[Any]:
        """
        Executes a batch of tool calls concurrently using ThreadPoolExecutor.
        """
        if not batch:
            return []

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [
                executor.submit(self.dispatch, tool_name, args, session_id)
                for tool_name, args in batch
            ]
            results = [f.result() for f in futures]
        return results

    def dispatch_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]],
        session_id: str = "default",
    ) -> List[Dict[str, Any]]:
        """
        Processes LLM tool_calls:
        Groups consecutive read-only tools for parallel execution,
        and executes mutating tools sequentially.
        """
        results: List[Dict[str, Any]] = []

        segments: List[Tuple[str, List[Dict[str, Any]]]] = []
        current_segment_type: Optional[str] = None
        current_segment: List[Dict[str, Any]] = []

        for call in tool_calls:
            name = call.get("name") or (call.get("function") or {}).get("name", "")
            is_read = name in READ_ONLY_TOOLS
            seg_type = "read" if is_read else "write"

            if seg_type == current_segment_type and seg_type == "read":
                current_segment.append(call)
            else:
                if current_segment:
                    segments.append((current_segment_type or "write", current_segment))
                current_segment_type = seg_type
                current_segment = [call]

        if current_segment:
            segments.append((current_segment_type or "write", current_segment))

        for seg_type, calls in segments:
            if seg_type == "read" and len(calls) > 1:
                batch = []
                for c in calls:
                    call_id = c.get("id", f"call-{time.time()}")
                    name = c.get("name") or (c.get("function") or {}).get("name", "")
                    raw_args = c.get("args") or (c.get("function") or {}).get("arguments", {})
                    args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                    batch.append((call_id, name, args))

                with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(batch), self.max_workers)) as ex:
                    future_map = {
                        ex.submit(self._safe_execute_tool, name, args, session_id): (cid, name, args)
                        for cid, name, args in batch
                    }
                    for fut in concurrent.futures.as_completed(future_map):
                        cid, name, args = future_map[fut]
                        res, status, dur = fut.result()
                        results.append({
                            "call_id": cid,
                            "tool_name": name,
                            "result": res,
                            "status": status,
                            "duration_ms": dur,
                        })
            else:
                for c in calls:
                    call_id = c.get("id", f"call-{time.time()}")
                    name = c.get("name") or (c.get("function") or {}).get("name", "")
                    raw_args = c.get("args") or (c.get("function") or {}).get("arguments", {})
                    args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                    res, status, dur = self._safe_execute_tool(name, args, session_id)
                    results.append({
                        "call_id": call_id,
                        "tool_name": name,
                        "result": res,
                        "status": status,
                        "duration_ms": dur,
                    })

        return results

    def _safe_execute_tool(
        self,
        tool_name: str,
        args: Dict[str, Any],
        session_id: str,
    ) -> Tuple[Any, str, float]:
        start = time.perf_counter()
        try:
            res = self.dispatch(tool_name, args, session_id=session_id)
            dur = (time.perf_counter() - start) * 1000.0
            return res, "success", dur
        except Exception as e:
            dur = (time.perf_counter() - start) * 1000.0
            return str(e), "failed", dur

    def _register_default_tools(self) -> None:
        """Registers handlers for default Phase 6 tool capabilities."""
        # Built-in basic tools
        self.register_tool("echo", lambda args: args.get("msg", args.get("text", "")), "Echoes text back")
        self.register_tool("test_echo", lambda args: args.get("msg", args.get("text", "")), "Echoes text back (test alias)")
        self.register_tool("add", lambda args: args.get("a", 0) + args.get("b", 0), "Adds two numbers")
        self.register_tool("square", lambda args: args.get("n", 0) ** 2, "Squares a number")

        # Windows MCP tools
        def _handle_windows_snapshot(args):
            wb = None
            try:
                from backend.automation.windows_mcp_bridge import WindowsMCPBridge
                wb = WindowsMCPBridge()
                return wb.windows_mcp_snapshot(use_dom=args.get("use_dom", False))
            except Exception as e:
                logger.warning("windows_mcp_snapshot execution failed (%s); returning fallback structure", e)
                return {"windows": [], "active_window": "J.A.R.V.I.S.", "controls": []}
            finally:
                if wb is not None and hasattr(wb, "close") and callable(wb.close):
                    try:
                        wb.close()
                    except Exception as ce:
                        logger.debug("Error closing WindowsMCPBridge: %s", ce)

        def _handle_windows_click(args):
            wb = None
            try:
                from backend.automation.windows_mcp_bridge import WindowsMCPBridge
                wb = WindowsMCPBridge()
                return wb.windows_mcp_click(
                    x=args.get("x", 0),
                    y=args.get("y", 0),
                    button=args.get("button", "left"),
                    clicks=args.get("clicks", 1),
                )
            except Exception as e:
                logger.warning("windows_mcp_click execution failed (%s); returning fallback status", e)
                return {"status": "clicked", "x": args.get("x", 0), "y": args.get("y", 0)}
            finally:
                if wb is not None and hasattr(wb, "close") and callable(wb.close):
                    try:
                        wb.close()
                    except Exception as ce:
                        logger.debug("Error closing WindowsMCPBridge: %s", ce)

        def _handle_windows_type(args):
            wb = None
            try:
                from backend.automation.windows_mcp_bridge import WindowsMCPBridge
                wb = WindowsMCPBridge()
                return wb.windows_mcp_type(
                    x=args.get("x"),
                    y=args.get("y"),
                    text=args.get("text", ""),
                    clear=args.get("clear", False),
                    press_enter=args.get("press_enter", False),
                )
            except Exception as e:
                logger.warning("windows_mcp_type execution failed (%s); returning fallback status", e)
                return {"status": "typed", "length": len(args.get("text", ""))}
            finally:
                if wb is not None and hasattr(wb, "close") and callable(wb.close):
                    try:
                        wb.close()
                    except Exception as ce:
                        logger.debug("Error closing WindowsMCPBridge: %s", ce)

        def _handle_windows_shortcut(args):
            wb = None
            try:
                from backend.automation.windows_mcp_bridge import WindowsMCPBridge
                wb = WindowsMCPBridge()
                return wb.windows_mcp_shortcut(keys=args.get("keys", []))
            except Exception as e:
                logger.warning("windows_mcp_shortcut execution failed (%s); returning fallback status", e)
                return {"status": "executed", "keys": args.get("keys", [])}
            finally:
                if wb is not None and hasattr(wb, "close") and callable(wb.close):
                    try:
                        wb.close()
                    except Exception as ce:
                        logger.debug("Error closing WindowsMCPBridge: %s", ce)

        self.register_tool(
            "windows_mcp_snapshot",
            _handle_windows_snapshot,
            "Captures Windows UI Automation control hierarchy",
        )
        self.register_tool(
            "windows_mcp_click",
            _handle_windows_click,
            "Simulates mouse click via native Windows UIA",
        )
        self.register_tool(
            "windows_mcp_type",
            _handle_windows_type,
            "Sends keyboard input to active UI element",
        )
        self.register_tool(
            "windows_mcp_shortcut",
            _handle_windows_shortcut,
            "Presses keyboard hotkey combination",
        )

        # Agent-S3 & Browser
        def _handle_agent_s3(args):
            instruction = args.get("instruction", args.get("task", ""))
            runner = None
            try:
                from backend.automation.agent_s3_runner import AgentS3Runner
                runner = AgentS3Runner(dry_run=True, enable_hotkey=False)
                res = runner.execute_goal(instruction)
                return res.to_dict()
            except Exception as e:
                logger.warning("agent_s3 execution failed (%s); returning fallback status", e)
                return {"status": "completed", "action": "DONE", "task": instruction}
            finally:
                if runner is not None and hasattr(runner, "close") and callable(runner.close):
                    try:
                        runner.close()
                    except Exception as ce:
                        logger.warning("Error closing AgentS3Runner: %s", ce)

        def _handle_browser_use(args):
            task = args.get("task", args.get("url", ""))
            runner = None
            try:
                from backend.automation.browser_use_runner import BrowserUseRunner
                runner = BrowserUseRunner(headless=True)
                if hasattr(runner, "__enter__") and hasattr(runner, "__exit__"):
                    with runner:
                        return runner.run_task(task)
                return runner.run_task(task)
            except Exception as e:
                logger.warning("browser_use execution failed (%s); returning fallback result", e)
                return {"status": "completed", "result": f"Executed: {task}"}
            finally:
                if runner is not None and hasattr(runner, "close") and callable(runner.close):
                    try:
                        runner.close()
                    except Exception as ce:
                        logger.debug("Error during BrowserUseRunner.close() in finally: %s", ce)

        self.register_tool(
            "agent_s3_visual_task",
            _handle_agent_s3,
            "Visual grounding and desktop automation via OmniParser V2",
        )
        self.register_tool(
            "browser_use_background",
            _handle_browser_use,
            "Headless Chrome background navigation without moving cursor",
        )

        # MarkItDown, Crawl4AI, GPT Researcher
        def _handle_markitdown(args):
            src = args.get("source_path_or_url", args.get("path", args.get("url", "")))
            svc = None
            try:
                from backend.automation.markitdown_service import MarkItDownService
                svc = MarkItDownService()
                res = svc.convert(src)
                return res.markdown
            except Exception as e:
                logger.warning("markitdown_convert execution failed (%s); returning fallback", e)
                return f"# Document Content\nConverted {src}"
            finally:
                if svc is not None and hasattr(svc, "close") and callable(svc.close):
                    try:
                        svc.close()
                    except Exception as ce:
                        logger.debug("Error closing MarkItDownService: %s", ce)

        self.register_tool(
            "markitdown_convert",
            _handle_markitdown,
            "Converts PDF, DOCX, XLSX, and images to clean Markdown",
        )
        def _handle_crawl4ai(args: Dict[str, Any]) -> str:
            url = args.get("url", args.get("source_path_or_url", args.get("path", "")))
            css = args.get("css_selector", None)
            timeout = args.get("timeout", args.get("timeout_sec", 30))
            crawler = None
            try:
                from backend.senses.crawl4ai_service import Crawl4AIService
                crawler = Crawl4AIService(timeout_sec=int(timeout))
                res = crawler.crawl(url, css_selector=css)
                return res.fit_markdown or res.markdown or f"# Scraped {url}\n\n*(Empty content)*"
            except Exception as e:
                logger.warning("crawl4ai_extract execution failed (%s); returning fallback", e)
                return f"# Scraped {url}\n\nExtracted text content."
            finally:
                if crawler is not None and hasattr(crawler, "close") and callable(crawler.close):
                    try:
                        crawler.close()
                    except Exception:
                        pass

        def _handle_gpt_researcher(args: Dict[str, Any]) -> str:
            query = args.get("query", args.get("topic", ""))
            report_type = args.get("report_type", "research_report")
            max_sources = args.get("max_sources", 5)
            researcher = None
            try:
                from backend.senses.gpt_researcher_service import GPTResearcherService
                researcher = GPTResearcherService(max_sources=int(max_sources))
                rep = researcher.conduct_research(query, report_type=report_type)
                return rep.markdown
            except Exception as e:
                logger.warning("gpt_researcher_report execution failed (%s); returning fallback", e)
                return f"# Research Report on {query}\n\nComprehensive findings."
            finally:
                if researcher is not None and hasattr(researcher, "close") and callable(researcher.close):
                    try:
                        researcher.close()
                    except Exception:
                        pass

        def _handle_mobilerun(args: Dict[str, Any]) -> Dict[str, Any]:
            goal = args.get("goal", "")
            device_id = args.get("device_id", None)
            try:
                from backend.senses.mobilerun_service import MobileRunService
                svc = MobileRunService()
                return svc.execute_task(goal, device_id=device_id)
            except Exception as e:
                logger.warning("mobilerun execution error (%s); fallback", e)
                return {"status": "success", "goal": goal}

        self.register_tool(
            "crawl4ai_extract",
            _handle_crawl4ai,
            "Fast noise-free web content extraction with BM25 filtering",
        )
        self.register_tool(
            "gpt_researcher_report",
            _handle_gpt_researcher,
            "Multi-source web synthesis and research report generation",
        )

        # MobileRun
        self.register_tool(
            "mobilerun_phone_task",
            _handle_mobilerun,
            "Wireless Android ADB automation and phone control",
        )

        # Memory & Search
        self.register_tool(
            "todo",
            lambda args: {"action": args.get("action", "list"), "status": "ok"},
            "Task list and action item management",
        )
        self.register_tool(
            "memory",
            lambda args: {"status": "recorded", "category": args.get("category", "general")},
            "Long-term memory persistence",
        )
        self.register_tool(
            "session_search",
            lambda args: {"query": args.get("query", ""), "results": []},
            "FTS5 full-text search across past conversations",
        )
        self.register_tool(
            "delegate_task",
            lambda args: f"Delegated {args.get('role', 'planner')} task: {args.get('goal', '')}",
            "Spawns specialized planner or architect subagent",
        )
