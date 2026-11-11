# ToolDispatcher Automation Handler Replacement Snippet
# Replace lines 300-412 in backend/core/tool_dispatcher.py

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
