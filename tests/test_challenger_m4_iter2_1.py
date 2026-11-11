"""
tests/test_challenger_m4_iter2_1.py
===================================
Milestone M4 Iteration 2 Adversarial Stress Test Suite for BrowserUseRunner.
Authored by challenger_m4_iter2_1 (Empirical Challenger).

Empirical verification dimensions:
1. Live Playwright Execution:
   - Navigate to about:blank -> real page, status 200, url 'about:blank'
   - JavaScript evaluation:
     * Arrow function '() => { window.test_val = 42; return window.test_val; }' -> 42
     * Statement script 'window.test_val = 42; return window.test_val;' -> MUST evaluate to 42 in live page
   - Screenshot capture: valid PNG byte stream, length > 1000 bytes (NOT 67-byte 1x1 mock)
   - Real DOM extraction: returns actual HTML from Chromium, NOT the 12-line mock template
   - Dynamic DOM/State mutation: verifying mutations in Chromium persist and reflect in queries
   - Live text extraction: verify empty page does NOT return mock session banner
2. Adversarial URL Validation:
   - 'about:blank' allowed across case and whitespace variations
   - 'javascript:alert(1)', 'file:///C:/Windows/win.ini', 'data:text/html,...' rejected
   - Dangerous schemes ('vbscript:', 'chrome:', 'about:config') and malformed inputs rejected
   - Runner.navigate gracefully blocks unsafe schemes without exceptions
3. Network Failure & Resilience:
   - Unresolvable hostnames ('https://nonexistent-domain-404-jarvis.test') handled cleanly
   - Connection refused ('http://127.0.0.1:59999') handled cleanly
   - Runner recovery after network failure
   - Emergency abort and reset lifecycle
4. Fallback & MockCDPSession:
   - Complete action gauntlet under _is_mock=True runs cleanly without crashes
   - Mock screenshot returns MOCK_1X1_PNG (67 bytes)
   - Mock DOM returns simulated template
5. Lifecycle & Leak Prevention:
   - Context manager deterministically frees Playwright and browser resources
   - Multiple sequential runners start and close cleanly without process leaks
   - close() is idempotent
"""

import time
import unittest
from backend.automation.browser_use_runner import (
    BrowserUseRunner,
    MockCDPSession,
    MOCK_1X1_PNG,
)


class TestLivePlaywrightExecution(unittest.TestCase):
    """Empirical verification of live Playwright Chromium automation."""

    PNG_MAGIC_HEADER = b"\x89PNG\r\n\x1a\n"

    def setUp(self):
        self.runner = BrowserUseRunner(headless=True)
        self.start_time = time.perf_counter()

    def tearDown(self):
        self.runner.close()

    def test_01_navigate_about_blank(self):
        """Verify live navigation to about:blank succeeds and reports status 200."""
        nav = self.runner.navigate("about:blank")
        self.assertTrue(nav["success"], f"Navigation failed: {nav.get('error')}")
        self.assertEqual(nav["url"], "about:blank")
        self.assertEqual(self.runner.current_url, "about:blank")
        self.assertIn(nav["result"]["status"], (200, None))
        self.assertFalse(self.runner._is_mock, "Expected live Playwright mode, but _is_mock is True")

    def test_02_javascript_evaluation_arrow_function(self):
        """Verify executing JavaScript via arrow function evaluates and sets state in real Chromium."""
        self.runner.navigate("about:blank")
        script = "() => { window.test_val = 42; return window.test_val; }"
        res = self.runner.evaluate_js(script)
        self.assertEqual(res, 42, f"Expected 42 from arrow function execution, got {res!r}")

        # Verify state persisted in live page
        val = self.runner.evaluate_js("() => window.test_val")
        self.assertEqual(val, 42, f"window.test_val did not persist in live page: {val!r}")

    def test_03_javascript_evaluation_naked_return_stress(self):
        """
        Adversarial test: verify executing JavaScript with top-level return:
        'window.test_val = 42; return window.test_val;'
        Tests whether evaluate_js supports statement scripts with return or falls back to mock.
        """
        self.runner.navigate("about:blank")
        script = "window.test_val = 42; return window.test_val;"
        res = self.runner.evaluate_js(script)
        # In live Playwright, naked 'return' outside a function raises SyntaxError.
        # BrowserUseRunner should either auto-wrap it into an IIFE and return 42,
        # or we detect that it failed and fell back to mock.
        self.assertEqual(
            res,
            42,
            f"Adversarial failure: evaluate_js failed on naked return statement and returned {res!r}",
        )
        # Verify window.test_val in live page
        val = self.runner.evaluate_js("() => window.test_val")
        self.assertEqual(val, 42, f"window.test_val was not set in live page: {val!r}")

    def test_04_screenshot_byte_stream_size_and_format(self):
        """Verify screenshot is valid PNG byte stream with length > 1000 bytes (NOT 67-byte mock)."""
        self.runner.navigate("about:blank")
        screenshot = self.runner.screenshot()
        self.assertIsInstance(screenshot, bytes)
        self.assertTrue(
            screenshot.startswith(self.PNG_MAGIC_HEADER),
            f"Screenshot missing PNG magic header. Got: {screenshot[:16]!r}",
        )
        self.assertGreater(
            len(screenshot),
            1000,
            f"Screenshot length ({len(screenshot)} bytes) too small. Expected > 1000 bytes for real Chromium render.",
        )
        self.assertNotEqual(
            screenshot,
            MOCK_1X1_PNG,
            "Screenshot returned static MOCK_1X1_PNG instead of live Chromium render.",
        )
        # Verify IHDR chunk presence
        self.assertIn(b"IHDR", screenshot[:24], "Screenshot missing valid IHDR chunk")

    def test_05_dom_extraction_live_chromium(self):
        """Verify DOM extraction from about:blank contains real HTML structure rather than mock template."""
        self.runner.navigate("about:blank")
        dom = self.runner.extract_dom()
        self.assertIsInstance(dom, str)
        self.assertTrue(
            "<html" in dom.lower() and "</html>" in dom.lower(),
            f"DOM extraction missing html tags: {dom!r}",
        )
        # Verify absence of hardcoded mock template elements
        self.assertNotIn("search-btn", dom, "Extracted DOM contains mock 'search-btn' artifact")
        self.assertNotIn("submit-btn", dom, "Extracted DOM contains mock 'submit-btn' artifact")
        self.assertNotIn("Simulated DOM for:", dom, "Extracted DOM contains mock simulated banner")

    def test_06_dynamic_dom_mutation_persistence(self):
        """Verify that JavaScript mutations in live Chromium are reflected in subsequent queries."""
        self.runner.navigate("about:blank")
        self.runner.evaluate_js("() => { document.title = 'Live JARVIS Dynamic Page'; }")
        title = self.runner.evaluate_js("() => document.title")
        self.assertEqual(title, "Live JARVIS Dynamic Page")

    def test_07_extract_text_empty_page_bug_check(self):
        """
        Adversarial test: verify extract_text() on an empty page returns empty string,
        NOT the fallback MockCDPSession banner.
        In current implementation: 'if text:' treats '' as falsy and falls back to mock text.
        """
        self.runner.navigate("about:blank")
        txt = self.runner.extract_text()
        self.assertNotIn(
            "J.A.R.V.I.S. Background Browser (Mock)",
            txt,
            "extract_text() fell back to MockCDPSession text on live about:blank due to 'if text:' falsy check",
        )


class TestAdversarialURLValidation(unittest.TestCase):
    """Stress tests for BrowserUseRunner.validate_url and malicious navigation handling."""

    def setUp(self):
        self.runner = BrowserUseRunner(headless=True)

    def tearDown(self):
        self.runner.close()

    def test_01_about_blank_allowed(self):
        """Verify about:blank is permitted across casing and whitespace variations."""
        valid_blank_cases = [
            "about:blank",
            "ABOUT:BLANK",
            "About:Blank",
            "  about:blank  ",
            "\tabout:blank\n",
        ]
        for url in valid_blank_cases:
            with self.subTest(url=url):
                self.assertTrue(
                    self.runner.validate_url(url),
                    f"about:blank variation should be allowed: {url!r}",
                )

    def test_02_malicious_schemes_rejected(self):
        """Verify hazardous schemes (javascript, file, data, vbscript, chrome) are strictly rejected."""
        malicious_urls = [
            "javascript:alert(1)",
            "javascript:void(0)",
            "JAVASCRIPT:alert('xss')",
            "  javascript:alert(1)  ",
            "file:///C:/Windows/win.ini",
            "FILE:///C:/Windows/win.ini",
            "file:///etc/passwd",
            "data:text/html,<h1>XSS</h1>",
            "DATA:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA",
            "vbscript:msgbox(1)",
            "VBSCRIPT:alert(1)",
            "chrome://settings",
            "about:config",
            "about:about",
            "about:blank?exploit=1",
        ]
        for url in malicious_urls:
            with self.subTest(url=url):
                self.assertFalse(
                    self.runner.validate_url(url),
                    f"Hazardous URL should be rejected: {url!r}",
                )

    def test_03_malformed_and_boundary_cases_rejected(self):
        """Verify malformed inputs, relative paths, and non-string types are rejected."""
        malformed = [
            "",
            "   ",
            "\n\r\t",
            None,
            12345,
            0.5,
            {"url": "https://example.com"},
            ["https://example.com"],
            True,
            False,
            "http://",
            "https://",
            "ftp://files.example.com",
            "ssh://root@10.0.0.1",
            "//example.com/relative",
            "http:///no-host",
        ]
        for case in malformed:
            with self.subTest(case=case):
                self.assertFalse(
                    self.runner.validate_url(case),
                    f"Malformed case should be rejected: {case!r}",
                )

    def test_04_legitimate_urls_accepted(self):
        """Verify standard legitimate HTTP and HTTPS URLs are accepted."""
        legitimate = [
            "https://example.com",
            "http://localhost:8765",
            "http://127.0.0.1:8765/api/health",
            "https://sub.domain.co.uk/path/to/page?q=test&limit=10#section",
            "https://github.com/simular-ai/Agent-S",
        ]
        for url in legitimate:
            with self.subTest(url=url):
                self.assertTrue(
                    self.runner.validate_url(url),
                    f"Legitimate URL should be accepted: {url!r}",
                )

    def test_05_navigate_blocks_malicious_urls_gracefully(self):
        """Verify navigate() cleanly blocks malicious URLs and returns structured error without exception."""
        res = self.runner.navigate("javascript:alert(1)")
        self.assertFalse(res["success"])
        self.assertIn("Blocked", res.get("error", ""))
        self.assertGreaterEqual(res.get("duration_ms", 0), 0)


class TestNetworkFailureResilience(unittest.TestCase):
    """Stress tests for network failures, unresolvable domains, and connection errors."""

    def setUp(self):
        self.runner = BrowserUseRunner(headless=True)

    def tearDown(self):
        self.runner.close()

    def test_01_unresolvable_hostname_resilience(self):
        """Verify runner catches DNS resolution error cleanly and returns structured failure."""
        unresolvable_url = "https://nonexistent-domain-404-jarvis.test"
        res = self.runner.navigate(unresolvable_url)

        self.assertIsInstance(res, dict)
        self.assertEqual(res["action"], "navigate")
        self.assertFalse(res["success"], "Unresolvable domain navigation must report success=False")
        self.assertIsNotNone(res["error"], "Error field must contain diagnostic failure message")
        self.assertGreater(res["duration_ms"], 0)

        # Allow Chromium internal error page transition to settle (300ms)
        time.sleep(0.3)
        recovery_nav = self.runner.navigate("about:blank")
        self.assertTrue(recovery_nav["success"], "Runner failed to recover after network error")

    def test_02_connection_refused_resilience(self):
        """Verify runner handles closed/non-listening local ports without crashing."""
        closed_port_url = "http://127.0.0.1:59999"
        res = self.runner.navigate(closed_port_url)

        self.assertIsInstance(res, dict)
        self.assertFalse(res["success"])
        self.assertIsNotNone(res["error"])

    def test_03_emergency_abort_lifecycle(self):
        """Verify emergency abort stops navigation and reset allows normal operations."""
        self.runner.trigger_emergency_abort()
        self.assertTrue(self.runner.is_aborted)

        abort_res = self.runner.navigate("about:blank")
        self.assertFalse(abort_res["success"])
        self.assertIn("aborted", abort_res.get("error", "").lower())

        self.runner.reset_abort()
        self.assertFalse(self.runner.is_aborted)

        ok_res = self.runner.navigate("about:blank")
        self.assertTrue(ok_res["success"])


class TestMockCDPSessionFallback(unittest.TestCase):
    """Stress tests for fallback mode when Playwright is unavailable or _is_mock=True."""

    def setUp(self):
        self.runner = BrowserUseRunner(headless=True)
        self.runner._is_mock = True

    def tearDown(self):
        self.runner.close()

    def test_01_mock_action_gauntlet(self):
        """Verify all actions operate cleanly in fallback mock mode without throwing exceptions."""
        # 1. navigate
        nav = self.runner.navigate("https://example.com/fallback")
        self.assertTrue(nav["success"])
        self.assertEqual(nav["url"], "https://example.com/fallback")

        # 2. click
        click = self.runner.click("#btn-test")
        self.assertTrue(click["success"])

        # 3. type
        typ = self.runner.type("#input-test", "fallback_text")
        self.assertTrue(typ["success"])

        # 4. screenshot (mock returns 67-byte 1x1 PNG)
        ss = self.runner.screenshot()
        self.assertEqual(ss, MOCK_1X1_PNG)
        self.assertEqual(len(ss), len(MOCK_1X1_PNG))

        # 5. extract_dom
        dom = self.runner.extract_dom()
        self.assertIn("<!DOCTYPE html>", dom)
        self.assertIn("fallback_text", dom)

        # 6. extract_text
        txt = self.runner.extract_text()
        self.assertIn("State: Ready", txt)

        # 7. evaluate_js
        title = self.runner.evaluate_js("document.title")
        self.assertIn("Mock Page", title)
        href = self.runner.evaluate_js("window.location.href")
        self.assertEqual(href, "https://example.com/fallback")


class TestProcessLifecycleAndLeakPrevention(unittest.TestCase):
    """Stress tests for deterministic lifecycle, context managers, and resource leak prevention."""

    def test_01_context_manager_cleanup(self):
        """Verify context manager deterministically frees all Playwright resources."""
        with BrowserUseRunner(headless=True) as runner:
            nav = runner.navigate("about:blank")
            self.assertTrue(nav["success"])
            self.assertIsNotNone(runner._page)
            self.assertIsNotNone(runner._browser)

        # Post-exit: resources must be None
        self.assertIsNone(runner._page)
        self.assertIsNone(runner._context)
        self.assertIsNone(runner._browser)
        self.assertIsNone(runner._pw)

    def test_02_multiple_sequential_runners(self):
        """Verify multiple sequential runner instances launch and terminate without conflicts."""
        for i in range(3):
            with BrowserUseRunner(headless=True) as runner:
                nav = runner.navigate("about:blank")
                self.assertTrue(nav["success"], f"Iteration {i} failed to navigate")
                eval_val = runner.evaluate_js(f"() => {i} * 2")
                self.assertEqual(eval_val, i * 2)

    def test_03_idempotent_close(self):
        """Verify close() can be called multiple times without raising exceptions."""
        runner = BrowserUseRunner(headless=True)
        runner.start()
        runner.close()
        # Second and third close should be safe no-ops
        try:
            runner.close()
            runner.close()
        except Exception as e:
            self.fail(f"Subsequent close() raised unexpected exception: {e}")


if __name__ == "__main__":
    unittest.main()
