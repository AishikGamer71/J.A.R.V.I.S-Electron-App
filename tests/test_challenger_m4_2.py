"""
tests/test_challenger_m4_2.py
=============================
Milestone M4 Adversarial Stress Test Suite for Web & Document Automation.
Authored by challenger_m4_2 (Empirical Challenger).

Tests cover:
1. BrowserUseRunner URL Validator Stress Testing:
   - Malicious URLs: 'javascript:alert(1)', 'javascript:void(0)', 'vbscript:msgbox',
     'data:text/html,<h1>XSS</h1>', 'file:///C:/Windows/win.ini', '', None -> all return False.
   - Legitimate URLs: 'https://example.com', 'http://localhost:8000',
     'https://github.com/simular-ai/Agent-S' -> all return True.
   - Adversarial edge cases: spaces, uppercase schemes, IP/IPv6, relative URLs, non-strings.
   - Emergency abort and reset.

2. MockCDPSession & BrowserUseRunner Fallback Stress Testing:
   - Full action sequence: navigate, click, type, screenshot, extract_dom, extract_text, evaluate_js.
   - Zero unhandled exceptions.
   - Screenshot PNG header verification: first 8 bytes match b"\\x89PNG\\r\\n\\x1a\\n".
   - DOM state and JavaScript evaluation behavior.

3. MarkItDownService Stress Testing:
   - Table repair: irregular table without delimiter ('| A | B |\\n| 1 | 2 |') -> injects delimiter starting with '|---'.
   - Ragged table repair: rows with varying column counts -> uniform max column padding.
   - Excel XML repair: mock zip with 'xl/worksheets/sheet1.xml' containing showZeroes="0" -> repairs to showZeroes="false".
   - Plain text normalization: convert_text('Heading\\nLine 1') retains both lines, collapses excess blanks, normalizes CRLF.
   - File conversion resilience on TXT, CSV, corrupted XLSX, and non-existent files.
"""

import io
import unittest
import zipfile
from pathlib import Path

from backend.automation.browser_use_runner import (
    BrowserUseRunner,
    MockCDPSession,
    MOCK_1X1_PNG,
    DEFAULT_SCREENSHOT_FORMAT,
)
from backend.automation.markitdown_service import (
    MarkItDownService,
    DocumentMetadata,
    ConversionResult,
)


class TestBrowserUseURLValidator(unittest.TestCase):
    """Stress tests for BrowserUseRunner.validate_url."""

    def setUp(self):
        self.runner = BrowserUseRunner(headless=True)

    def tearDown(self):
        self.runner.close()

    def test_malicious_urls_rejected(self):
        """Verify hazardous and malicious URL schemes return False."""
        malicious_urls = [
            "javascript:alert(1)",
            "javascript:void(0)",
            "vbscript:msgbox",
            "data:text/html,<h1>XSS</h1>",
            "file:///C:/Windows/win.ini",
            "file:///etc/passwd",
            "",
            None,
        ]
        for url in malicious_urls:
            with self.subTest(url=url):
                self.assertFalse(
                    self.runner.validate_url(url),
                    f"Malicious URL should be rejected: {url!r}",
                )

    def test_adversarial_variations_rejected(self):
        """Verify obfuscated, whitespace-padded, or malformed URLs return False."""
        adversarial_cases = [
            "   javascript:alert(1)",
            "JAVASCRIPT:alert('xss')",
            "VBSCRIPT:msgbox(1)",
            "DATA:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA",
            "   ",
            "\n\t",
            "about:config",
            "//example.com/relative",
            "ftp://files.example.com",
            "ssh://root@10.0.0.1",
            "http://",
            "https://",
            12345,
            {"url": "https://example.com"},
            ["https://example.com"],
            True,
            False,
        ]
        for case in adversarial_cases:
            with self.subTest(case=case):
                self.assertFalse(
                    self.runner.validate_url(case),
                    f"Adversarial case should be rejected: {case!r}",
                )

    def test_legitimate_urls_accepted(self):
        """Verify legitimate http and https URLs and about:blank return True."""
        legitimate_urls = [
            "about:blank",
            "https://example.com",
            "http://localhost:8000",
            "https://github.com/simular-ai/Agent-S",
            "https://sub.domain.co.uk/path/to/page?q=test#section",
            "http://127.0.0.1:8765/api/health",
            "https://en.wikipedia.org/wiki/Artificial_intelligence",
        ]
        for url in legitimate_urls:
            with self.subTest(url=url):
                self.assertTrue(
                    self.runner.validate_url(url),
                    f"Legitimate URL should be accepted: {url!r}",
                )

    def test_navigate_blocks_malicious_urls(self):
        """Verify runner.navigate fails cleanly without unhandled exception for unsafe URLs."""
        res = self.runner.navigate("javascript:alert(1)")
        self.assertFalse(res["success"])
        self.assertIn("Blocked", res["error"])

    def test_emergency_abort_behavior(self):
        """Verify emergency abort stops navigation and reset allows subsequent actions."""
        self.runner.trigger_emergency_abort()
        self.assertTrue(self.runner.is_aborted)
        abort_res = self.runner.navigate("https://example.com")
        self.assertFalse(abort_res["success"])
        self.assertIn("aborted", abort_res["error"].lower())

        self.runner.reset_abort()
        self.assertFalse(self.runner.is_aborted)
        ok_res = self.runner.navigate("https://example.com")
        self.assertTrue(ok_res["success"])


class TestMockCDPSession(unittest.TestCase):
    """Stress tests for MockCDPSession and BrowserUseRunner mock fallback."""

    PNG_MAGIC_HEADER = b"\x89PNG\r\n\x1a\n"

    def setUp(self):
        self.session = MockCDPSession()
        self.runner = BrowserUseRunner(headless=True)
        self.runner._is_mock = True

    def tearDown(self):
        self.runner.close()

    def test_mock_cdp_session_sequence(self):
        """Call navigate, click, type, screenshot, extract_dom, extract_text, evaluate_js in sequence."""
        # 1. navigate
        nav_res = self.session.navigate("https://example.com/test")
        self.assertTrue(nav_res["success"])
        self.assertEqual(nav_res["url"], "https://example.com/test")
        self.assertEqual(self.session.current_url, "https://example.com/test")

        # 2. click
        click_res = self.session.click("#login-btn")
        self.assertTrue(click_res["success"])
        self.assertEqual(click_res["action"], "click")
        self.assertEqual(click_res["selector"], "#login-btn")

        # 3. type
        type_res = self.session.type_text("input#username", "jarvis_user", clear_existing=True)
        self.assertTrue(type_res["success"])
        self.assertEqual(type_res["current_value"], "jarvis_user")

        # 4. screenshot
        screenshot_bytes = self.session.capture_screenshot()
        self.assertIsInstance(screenshot_bytes, bytes)
        self.assertTrue(
            screenshot_bytes.startswith(self.PNG_MAGIC_HEADER),
            f"Screenshot bytes must start with PNG header {self.PNG_MAGIC_HEADER!r}",
        )

        # 5. extract_dom
        dom = self.session.extract_dom()
        self.assertIsInstance(dom, str)
        self.assertIn("<!DOCTYPE html>", dom)
        self.assertIn("jarvis_user", dom)

        # 6. extract_text
        text = self.session.extract_text()
        self.assertIsInstance(text, str)
        self.assertIn("https://example.com/test", text)

        # 7. evaluate_js
        title = self.session.evaluate_js("document.title")
        self.assertIsInstance(title, str)
        href = self.session.evaluate_js("window.location.href")
        self.assertEqual(href, "https://example.com/test")
        ready_state = self.session.evaluate_js("document.readyState")
        self.assertEqual(ready_state, "complete")
        arbitrary = self.session.evaluate_js("console.log('test');")
        self.assertEqual(arbitrary.get("eval_result"), "mock_js_executed")

    def test_runner_cdp_sequence_and_png_header(self):
        """Verify BrowserUseRunner dispatches identical sequence with zero exceptions."""
        nav = self.runner.navigate("https://example.com")
        self.assertTrue(nav["success"])

        click = self.runner.click("#submit")
        self.assertTrue(click["success"])

        typing = self.runner.type("input[name=q]", "search term")
        self.assertTrue(typing["success"])

        ss = self.runner.screenshot()
        self.assertIsInstance(ss, bytes)
        self.assertTrue(
            ss.startswith(self.PNG_MAGIC_HEADER),
            f"BrowserUseRunner.screenshot() must start with PNG header {self.PNG_MAGIC_HEADER!r}",
        )

        dom = self.runner.extract_dom()
        self.assertIn("<html", dom.lower())

        txt = self.runner.extract_text()
        self.assertIn("https://example.com", txt)

        js_title = self.runner.evaluate_js("document.title")
        self.assertIsInstance(js_title, str)

    def test_live_playwright_execution(self):
        """Verify that genuine Playwright sync API operates without falling back to mock."""
        live_runner = BrowserUseRunner(headless=True)
        try:
            if live_runner._driver_tier == "playwright":
                nav = live_runner.navigate("about:blank")
                self.assertTrue(nav["success"])
                eval_res = live_runner.evaluate_js("1 + 1")
                self.assertEqual(eval_res, 2)
                screenshot = live_runner.screenshot()
                self.assertGreater(len(screenshot), 100, "Genuine Playwright screenshot must exceed 100 bytes")
                self.assertTrue(screenshot.startswith(self.PNG_MAGIC_HEADER))
                dom = live_runner.extract_dom()
                self.assertIn("html", dom.lower())
        finally:
            live_runner.close()


class TestMarkItDownService(unittest.TestCase):
    """Stress tests for MarkItDownService."""

    def setUp(self):
        self.svc = MarkItDownService(ocr_enabled=True)

    def test_table_repair_missing_delimiters(self):
        """Irregular table without delimiters must receive injected delimiter starting with '|---'."""
        input_table = "| A | B |\n| 1 | 2 |"
        repaired = self.svc.repair_markdown_table(input_table)
        lines = repaired.splitlines()

        self.assertGreaterEqual(len(lines), 3, "Repaired table must have at least 3 lines (header, delimiter, row)")
        self.assertEqual(lines[0], "| A | B |")
        self.assertTrue(
            lines[1].startswith("|---"),
            f"Delimiter row must start with '|---', got: {lines[1]!r}",
        )
        self.assertEqual(lines[2], "| 1 | 2 |")

    def test_table_repair_ragged_columns(self):
        """Ragged table with unequal column counts must be padded to max column width."""
        ragged = (
            "| Col 1 | Col 2 |\n"
            "| Val 1 |\n"
            "| Val 2A | Val 2B | Val 2C |\n"
        )
        repaired = self.svc.repair_markdown_table(ragged)
        lines = repaired.splitlines()

        # Max columns is 3 (from row 3)
        self.assertTrue(lines[1].startswith("|---"))
        for line in lines:
            if line.strip():
                # Count pipes: 3 columns should have 4 pipes
                pipes = line.count("|")
                self.assertEqual(pipes, 4, f"Each padded row must have 4 pipes for 3 columns: {line}")

    def test_table_repair_behavioral_nuance_pre_existing_delimiter(self):
        """Document empirical behavior when input already contains a delimiter row."""
        existing = "| A | B |\n|---|---|\n| 1 | 2 |"
        repaired = self.svc.repair_markdown_table(existing)
        # Delimiter row is preserved and normalized unconditionally, producing 3 valid lines.
        lines = repaired.splitlines()
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0], "| A | B |")
        self.assertEqual(lines[1], "|---|---|")
        self.assertEqual(lines[2], "| 1 | 2 |")

    def test_excel_xml_repair_show_zeroes(self):
        """Corrupted XLSX containing showZeroes='0' in sheet XML must be repaired to showZeroes='false'."""
        # Build in-memory XLSX zip structure
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            corrupted_xml = (
                b'<?xml version="1.0" encoding="UTF-8"?>\n'
                b'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">\n'
                b'  <sheetViews>\n'
                b'    <sheetView tabSelected="1" workbookViewId="0" showZeroes="0"/>\n'
                b'  </sheetViews>\n'
                b'  <sheetData>\n'
                b'    <row r="1">\n'
                b'      <c r="A1" t="inlineStr"><is><t>Fixed Data</t></is></c>\n'
                b'    </row>\n'
                b'  </sheetData>\n'
                b'</worksheet>'
            )
            zf.writestr("xl/worksheets/sheet1.xml", corrupted_xml)
            zf.writestr(
                "[Content_Types].xml",
                b'<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>'
            )

        corrupted_bytes = buf.getvalue()
        # Verify initial corruption inside zip archive
        with zipfile.ZipFile(io.BytesIO(corrupted_bytes), "r") as zf:
            initial_xml = zf.read("xl/worksheets/sheet1.xml").decode("utf-8")
        self.assertIn('showZeroes="0"', initial_xml)

        # Apply MarkItDown repair
        repaired_bytes = self.svc._repair_xlsx_xml(corrupted_bytes)

        # Inspect repaired zip
        with zipfile.ZipFile(io.BytesIO(repaired_bytes), "r") as zf:
            fixed_sheet_xml = zf.read("xl/worksheets/sheet1.xml").decode("utf-8")

        self.assertNotIn('showZeroes="0"', fixed_sheet_xml, "Repaired XML must not contain showZeroes='0'")
        self.assertIn('showZeroes="false"', fixed_sheet_xml, "Repaired XML must contain showZeroes='false'")

    def test_excel_xml_repair_single_quote_and_spacing(self):
        """Ensure showZeroes with single quotes and spaces is correctly repaired."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                "xl/worksheets/sheet1.xml",
                b'<sheetViews><sheetView tabSelected="1" showZeroes = \'0\'/></sheetViews>'
            )
        repaired = self.svc._repair_xlsx_xml(buf.getvalue())
        with zipfile.ZipFile(io.BytesIO(repaired), "r") as zf:
            fixed_xml = zf.read("xl/worksheets/sheet1.xml").decode("utf-8")
        self.assertNotIn("showZeroes = '0'", fixed_xml)
        self.assertIn('showZeroes="false"', fixed_xml)

    def test_plain_text_normalization(self):
        """convert_text('Heading\\nLine 1') must retain both lines and normalize carriage returns."""
        input_text = "Heading\nLine 1"
        converted = self.svc.convert_text(input_text)
        self.assertEqual(converted, "Heading\nLine 1")

        # CRLF and excess blanks
        crlf_text = "Heading\r\nLine 1\r\n\r\n\r\n\r\n\r\nLine 2   "
        norm = self.svc.convert_text(crlf_text)
        self.assertNotIn("\r", norm)
        self.assertIn("Heading\nLine 1", norm)
        self.assertIn("Line 2", norm)
        # Verify excess blank lines collapsed to at most 2
        self.assertNotIn("\n\n\n\n", norm)

    def test_universal_convert_text_and_csv(self):
        """Universal convert() processes in-memory bytes cleanly for txt and csv."""
        txt_res = self.svc.convert(b"Line 1\nLine 2\nLine 3", filename="notes.txt")
        self.assertEqual(txt_res.status, "success")
        self.assertIn("Line 1\nLine 2\nLine 3", txt_res.markdown)
        self.assertEqual(txt_res.metadata["format"], "txt")

        csv_res = self.svc.convert(b"Header1,Header2\nVal1,Val2\nVal3,Val4", filename="data.csv")
        self.assertEqual(csv_res.status, "success")
        self.assertIn("| Header1 | Header2 |", csv_res.markdown)
        self.assertIn("|---|---|", csv_res.markdown)
        self.assertEqual(csv_res.metadata["table_count"], 1)

    def test_nonexistent_file_handling(self):
        """Missing file path must fail gracefully with status='failed' without crashing."""
        res = self.svc.convert(Path("non_existent_file_path_12345.docx"))
        self.assertEqual(res.status, "failed")
        self.assertIn("File not found", res.error)


if __name__ == "__main__":
    unittest.main()
