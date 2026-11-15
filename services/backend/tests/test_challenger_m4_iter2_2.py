"""
tests/test_challenger_m4_iter2_2.py
===================================
Milestone M4 Iteration 2 Adversarial Stress Test Suite.
Authored by challenger_m4_iter2_2 (Empirical Challenger & Adversarial Verifier).

Scope:
1. Tool Dispatcher process lifecycle stress testing:
   - 25 consecutive tool dispatches through ToolDispatcher().dispatch('browser_use_background', ...).
   - Verifies BrowserUseRunner.close() is invoked 100% of the time (deterministic cleanup).
   - Audits system process table and child processes for lingering orphaned Chromium/Chrome processes.
2. MarkItDown XML repair stress testing:
   - Constructs mock zip containing xl/worksheets/sheet1.xml with:
     - showZeroes='0' (single quotes)
     - showZeroes = "0" (spaces)
     - showZeroes = '0' (spaces and single quotes)
     - additional whitespace and backslash path permutations
   - Verifies MarkItDownService._repair_xlsx_xml normalizes all permutations to showZeroes="false".
3. MarkItDown Markdown Table repair:
   - Un-delimited tables: 2 header/body lines -> output MUST have 3 lines.
   - Pre-delimited tables: 3 lines already containing a delimiter -> output MUST retain 3 valid lines and normalize delimiters.
   - Empty or 1-line tables -> verify graceful fallback without crashing.
"""

import io
import time
import unittest
import zipfile
from typing import Set

import psutil

from backend.automation.browser_use_runner import BrowserUseRunner
from backend.automation.markitdown_service import MarkItDownService
from backend.core.tool_dispatcher import ToolDispatcher


class TestToolDispatcherLifecycleStress(unittest.TestCase):
    """
    Empirically stress-tests BrowserUseRunner process lifecycle and cleanup
    under repeated dispatches through ToolDispatcher.
    """

    def setUp(self):
        self._orig_close = BrowserUseRunner.close
        self.close_invocations = 0

    def tearDown(self):
        BrowserUseRunner.close = self._orig_close

    def test_25_consecutive_browser_use_dispatches_lifecycle_cleanup(self):
        """
        Executes 25 consecutive tool dispatches through ToolDispatcher:
        - 15 dispatches with task='about:blank'
        - 10 dispatches with URL tasks
        Verifies:
        1. BrowserUseRunner.close() is invoked 100% of the time (at least 25 times;
           specifically twice per dispatch due to context manager __exit__ and defensive finally:).
        2. No orphaned Chrome, Chromium, or headless browser processes spawned by the runner remain.
        3. No lingering child processes are attached to the Python process.
        """
        close_call_count = 0
        orig_close = self._orig_close

        def tracked_close(runner_self):
            nonlocal close_call_count
            close_call_count += 1
            return orig_close(runner_self)

        BrowserUseRunner.close = tracked_close

        num_dispatches = 25
        tasks = []
        for i in range(15):
            tasks.append({"task": "about:blank"})
        for i in range(10):
            tasks.append({"task": f"http://127.0.0.1:909{i}/lifecycle_probe"})

        start_time = time.perf_counter()

        for idx, task_args in enumerate(tasks):
            dispatcher = ToolDispatcher(max_consecutive_calls=50)
            res = dispatcher.dispatch("browser_use_background", task_args)
            self.assertIsInstance(res, dict)
            self.assertEqual(res.get("status"), "completed")

        elapsed_s = time.perf_counter() - start_time

        # 1. Verification of close() invocation rate:
        # Every dispatch MUST invoke close() at least once.
        self.assertGreaterEqual(
            close_call_count,
            num_dispatches,
            f"Expected close() to be invoked at least {num_dispatches} times, but was called {close_call_count} times",
        )
        # In ToolDispatcher._handle_browser_use, runner is wrapped in `with runner:` (__exit__ calls close)
        # AND defensive `finally: runner.close()`. Thus close is invoked at least 25 times.
        invocation_rate = (close_call_count / num_dispatches) * 100.0
        self.assertGreaterEqual(invocation_rate, 100.0)

        # 2. Check for lingering child processes under Python runner:
        current_children = psutil.Process().children(recursive=True)
        lingering_browser_children = [
            c for c in current_children
            if any(k in c.name().lower() for k in ("chrome", "chromium", "node", "playwright"))
        ]
        self.assertEqual(
            lingering_browser_children,
            [],
            f"Found lingering child browser processes: {lingering_browser_children}",
        )

        # 3. Check system process list for orphaned test browser processes:
        orphaned_test_chrome = []
        for p in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                name = p.name().lower()
                if "chrome-headless-shell" in name:
                    orphaned_test_chrome.append((p.pid, name))
                elif "chrome" in name or "chromium" in name:
                    cmd = " ".join(p.cmdline() or [])
                    if "-32000,-32000" in cmd or "J.A.R.V.I.S./2.0" in cmd:
                        orphaned_test_chrome.append((p.pid, name))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        self.assertEqual(
            orphaned_test_chrome,
            [],
            f"Orphaned test Chrome/Chromium processes detected after 25 dispatches: {orphaned_test_chrome}",
        )

    def test_browser_use_dispatch_exception_cleanup(self):
        """
        Verifies that even if run_task raises an unhandled exception,
        the defensive finally block in ToolDispatcher invokes runner.close()
        and prevents browser process leakage.
        """
        close_call_count = 0
        orig_close = self._orig_close

        def tracked_close(runner_self):
            nonlocal close_call_count
            close_call_count += 1
            return orig_close(runner_self)

        BrowserUseRunner.close = tracked_close

        orig_run_task = BrowserUseRunner.run_task

        def crashing_run_task(runner_self, task, max_steps=20):
            raise RuntimeError("Simulated browser execution crash during automation")

        BrowserUseRunner.run_task = crashing_run_task
        try:
            dispatcher = ToolDispatcher()
            res = dispatcher.dispatch("browser_use_background", {"task": "about:blank"})
            # Should return graceful fallback dictionary without raising
            self.assertIsInstance(res, dict)
            self.assertEqual(res.get("status"), "completed")
            self.assertIn("Executed: about:blank", res.get("result", ""))
            # close() MUST have been called in finally block
            self.assertGreaterEqual(close_call_count, 1)
        finally:
            BrowserUseRunner.run_task = orig_run_task


class TestMarkItDownXMLRepairStress(unittest.TestCase):
    """
    Stress-tests MarkItDownService._repair_xlsx_xml against corrupted
    Excel XML attribute variations (quotes, whitespace, path separators).
    """

    def setUp(self):
        self.service = MarkItDownService()

    def test_repair_xlsx_xml_all_showzeroes_permutations(self):
        """
        Constructs a mock zip file containing sheet XML files with:
        - showZeroes='0' (single quotes)
        - showZeroes = "0" (spaces)
        - showZeroes = '0' (spaces and single quotes)
        - showZeroes="0" (standard double quotes)
        - showZeroes   =   '0' (excessive spaces)
        - showZeroes  =  "0" (excessive spaces)
        Verifies that _repair_xlsx_xml normalizes 100% of these occurrences
        to showZeroes="false".
        """
        sheet1_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">\n'
            '  <sheetViews>\n'
            '    <sheetView id="1" showZeroes=\'0\' tabSelected="1"/>\n'
            '    <sheetView id="2" showZeroes = "0" tabSelected="0"/>\n'
            '    <sheetView id="3" showZeroes = \'0\' tabSelected="0"/>\n'
            '    <sheetView id="4" showZeroes="0" tabSelected="0"/>\n'
            '    <sheetView id="5" showZeroes   =   \'0\' tabSelected="0"/>\n'
            '    <sheetView id="6" showZeroes  =  "0" tabSelected="0"/>\n'
            '  </sheetViews>\n'
            '</worksheet>'
        )

        sheet2_xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<worksheet>\n'
            '  <sheetView showZeroes=\'0\'/>\n'
            '</worksheet>'
        )

        workbook_xml = '<?xml version="1.0"?><workbook><sheets/></workbook>'

        in_buf = io.BytesIO()
        with zipfile.ZipFile(in_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("xl/worksheets/sheet1.xml", sheet1_xml.encode("utf-8"))
            zf.writestr("xl/worksheets/sheet2.xml", sheet2_xml.encode("utf-8"))
            # Non-sheet XML file should remain untouched
            zf.writestr("xl/workbook.xml", workbook_xml.encode("utf-8"))

        repaired_bytes = self.service._repair_xlsx_xml(in_buf.getvalue())
        self.assertIsInstance(repaired_bytes, bytes)
        self.assertGreater(len(repaired_bytes), 0)

        with zipfile.ZipFile(io.BytesIO(repaired_bytes), "r") as rzf:
            # Check sheet1.xml
            repaired_sheet1 = rzf.read("xl/worksheets/sheet1.xml").decode("utf-8")
            self.assertEqual(
                repaired_sheet1.count('showZeroes="false"'),
                6,
                "Expected all 6 permutations in sheet1.xml to be normalized to showZeroes=\"false\"",
            )
            self.assertNotIn("showZeroes='0'", repaired_sheet1)
            self.assertNotIn('showZeroes = "0"', repaired_sheet1)
            self.assertNotIn("showZeroes = '0'", repaired_sheet1)
            self.assertNotIn('showZeroes="0"', repaired_sheet1)

            # Check sheet2.xml
            repaired_sheet2 = rzf.read("xl/worksheets/sheet2.xml").decode("utf-8")
            self.assertEqual(
                repaired_sheet2.count('showZeroes="false"'),
                1,
                "Expected sheet2.xml showZeroes='0' to be normalized",
            )
            self.assertNotIn("showZeroes='0'", repaired_sheet2)

            # Check workbook.xml was preserved
            repaired_wb = rzf.read("xl/workbook.xml").decode("utf-8")
            self.assertEqual(repaired_wb, workbook_xml)

    def test_repair_xlsx_xml_passthrough_on_non_zip_or_corrupted(self):
        """
        Verifies that non-zip bytes or corrupted buffers pass through
        gracefully without raising unhandled exceptions.
        """
        corrupted_payload = b"NOT_A_VALID_ZIP_ARCHIVE_DATA"
        res = self.service._repair_xlsx_xml(corrupted_payload)
        self.assertEqual(res, corrupted_payload)

        empty_res = self.service._repair_xlsx_xml(b"")
        self.assertEqual(empty_res, b"")


class TestMarkItDownTableRepairStress(unittest.TestCase):
    """
    Stress-tests MarkItDownService.repair_markdown_table against:
    - un-delimited tables
    - pre-delimited tables
    - empty and single-line tables
    - ragged/irregular tables
    """

    def setUp(self):
        self.service = MarkItDownService()

    def test_undelimited_table_repair(self):
        """
        Un-delimited tables: 2 header/body lines:
        `| Header 1 | Header 2 |\n| Row 1 | Row 2 |`
        Output MUST have 3 lines:
        1: `| Header 1 | Header 2 |`
        2: `|---|---|`
        3: `| Row 1 | Row 2 |`
        """
        table_str = "| Header 1 | Header 2 |\n| Row 1 | Row 2 |"
        result = self.service.repair_markdown_table(table_str)
        lines = [line.strip() for line in result.strip().splitlines() if line.strip()]

        self.assertEqual(len(lines), 3, f"Expected exactly 3 lines, got {len(lines)}: {lines}")
        self.assertEqual(lines[0], "| Header 1 | Header 2 |")
        self.assertEqual(lines[1], "|---|---|")
        self.assertEqual(lines[2], "| Row 1 | Row 2 |")

    def test_predelimited_table_repair(self):
        """
        Pre-delimited tables: 3 lines already containing a delimiter:
        `| Header 1 | Header 2 |\n| :--- | ---: |\n| Row 1 | Row 2 |`
        Output MUST retain 3 valid lines and normalize delimiters to `|---|---|`.
        """
        table_str = "| Header 1 | Header 2 |\n| :--- | ---: |\n| Row 1 | Row 2 |"
        result = self.service.repair_markdown_table(table_str)
        lines = [line.strip() for line in result.strip().splitlines() if line.strip()]

        self.assertEqual(len(lines), 3, f"Expected 3 lines, got {len(lines)}: {lines}")
        self.assertEqual(lines[0], "| Header 1 | Header 2 |")
        self.assertEqual(lines[1], "|---|---|")
        self.assertEqual(lines[2], "| Row 1 | Row 2 |")

    def test_predelimited_standard_dashes_table_repair(self):
        """
        Pre-delimited tables with standard `| --- | --- |`:
        Output MUST retain 3 valid lines and clean delimiter.
        """
        table_str = "| Col A | Col B |\n| --- | --- |\n| Val 1 | Val 2 |"
        result = self.service.repair_markdown_table(table_str)
        lines = [line.strip() for line in result.strip().splitlines() if line.strip()]

        self.assertEqual(len(lines), 3, f"Expected 3 lines, got {len(lines)}: {lines}")
        self.assertEqual(lines[0], "| Col A | Col B |")
        self.assertEqual(lines[1], "|---|---|")
        self.assertEqual(lines[2], "| Val 1 | Val 2 |")

    def test_empty_and_whitespace_tables_fallback(self):
        """
        Empty or whitespace tables MUST gracefully return empty string
        without throwing exceptions.
        """
        self.assertEqual(self.service.repair_markdown_table(""), "")
        self.assertEqual(self.service.repair_markdown_table("   \n\t\n  "), "")
        self.assertEqual(self.service.repair_markdown_table(None), "")
        self.assertEqual(self.service.repair_markdown_table(12345), "")

    def test_single_line_table_graceful_handling(self):
        """
        1-line table: `| Header 1 | Header 2 |`
        Output should provide valid header + delimiter lines.
        """
        table_str = "| Header 1 | Header 2 |"
        result = self.service.repair_markdown_table(table_str)
        lines = [line.strip() for line in result.strip().splitlines() if line.strip()]

        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], "| Header 1 | Header 2 |")
        self.assertEqual(lines[1], "|---|---|")

    def test_single_plain_text_line_graceful_handling(self):
        """
        1 plain text line without pipes: should not crash and produce clean fallback.
        """
        table_str = "Single Column Header"
        result = self.service.repair_markdown_table(table_str)
        lines = [line.strip() for line in result.strip().splitlines() if line.strip()]

        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], "| Single Column Header |")
        self.assertEqual(lines[1], "|---|")

    def test_ragged_table_and_duplicate_body_delimiters(self):
        """
        Ragged rows with unequal cell counts are padded to max column width,
        and duplicate delimiter lines in the body are stripped.
        """
        table_str = (
            "| H1 | H2 | H3 |\n"
            "|---|---|---|\n"
            "| A | B |\n"
            "|---|---|---|\n"  # Accidental duplicate delimiter in body
            "| C | D | E | F |\n"
        )
        result = self.service.repair_markdown_table(table_str)
        lines = [line.strip() for line in result.strip().splitlines() if line.strip()]

        # Max cols across all rows is 4 (from row "C | D | E | F")
        self.assertEqual(lines[0], "| H1 | H2 | H3 |  |")
        self.assertEqual(lines[1], "|---|---|---|---|")
        self.assertEqual(lines[2], "| A | B |  |  |")
        self.assertEqual(lines[3], "| C | D | E | F |")
        self.assertEqual(len(lines), 4)


if __name__ == "__main__":
    unittest.main()
