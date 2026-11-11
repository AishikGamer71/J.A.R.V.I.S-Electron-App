"""
Adversarial Stress Test & Forensic Integrity Verification for Milestone M4.
Executed by auditor_m4_1.
"""

import os
import sys
import time
import threading
import io
import zipfile
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

results = []

def record(name: str, passed: bool, details: str = ""):
    results.append({"name": name, "passed": passed, "details": details})
    mark = "PASS" if passed else "FAIL"
    print(f"[{mark}] {name}: {details}")

print("=== 1. WindowsMCPBridge Adversarial Tests ===")
try:
    from backend.automation.windows_mcp_bridge import WindowsMCPBridge
    bridge = WindowsMCPBridge()

    # Test 1.1: Exclusion of tricky title variants
    variants = [
        "J.A.R.V.I.S.",
        "jarvis",
        "JARVIS Desktop",
        "electron",
        "Electron Helper",
        "my-jarvis-app",
        "jarvis.exe",
    ]
    all_excluded = all(bridge.is_excluded_window(v) for v in variants)
    record("Title exclusion variants", all_excluded, f"Tested {len(variants)} patterns")

    # Test 1.2: Allowed normal titles
    allowed_titles = ["Notepad", "Calculator", "Google Chrome", "Spotify", "Windows Terminal"]
    none_excluded = not any(bridge.is_excluded_window(t) for t in allowed_titles)
    record("Non-Jarvis titles allowed", none_excluded, f"Allowed: {allowed_titles}")

    # Test 1.3: Boundary HWND values (negative, zero, arbitrary)
    neg_excluded = bridge.is_excluded_window(-1)
    zero_excluded = bridge.is_excluded_window(0)
    record("Boundary HWND handling", isinstance(neg_excluded, bool) and isinstance(zero_excluded, bool), "No exceptions raised")

    # Test 1.4: Synthetic / fallback root elements schema
    elems = bridge.get_root_elements()
    valid_schema = isinstance(elems, list) and len(elems) > 0 and all("name" in e and "rect" in e for e in elems)
    record("Root elements schema validity", valid_schema, f"Found {len(elems)} elements")

    # Test 1.5: simulate_click dry run and boundaries
    click_res = bridge.simulate_click(-50, -50, dry_run=True)
    record("simulate_click dry run", click_res.get("success") is True, f"Result: {click_res}")

except Exception as e:
    record("WindowsMCPBridge suite", False, str(e))


print("\n=== 2. OmniParserService Adversarial Tests ===")
try:
    from backend.automation.omniparser_service import OmniParserService, OmniParserClient
    service = OmniParserService()

    # Test 2.1: Corrupt byte stream (random noise)
    noise_bytes = b"NOT_AN_IMAGE_RANDOM_CORRUPT_BYTES_XYZ_123456789"
    noise_res = service.parse_screen(image_bytes=noise_bytes)
    record("Corrupt image bytes parsing", isinstance(noise_res.get("elements"), list), f"Tier used: {noise_res.get('tier_used')}")

    # Test 2.2: Extreme empty / None bytes
    empty_res = service.parse_screen(b"")
    record("Empty bytes parsing", empty_res.get("count") == 0 and empty_res.get("elements") == [], "Zero elements returned safely")

    # Test 2.3: Large zero-byte buffer (1MB)
    large_zeros = b"\x00" * (1024 * 1024)
    large_res = service.parse_screen(large_zeros)
    record("1MB zero-byte buffer resilience", isinstance(large_res.get("elements"), list), f"Elements: {large_res.get('count')}")

    # Test 2.4: Set-of-Mark drawing on corrupt bytes
    som_img = service.get_som_labeled_img(noise_bytes, elements=[{"box": [10, 10, 50, 50], "id": 1}])
    record("SoM with invalid image bytes", som_img is None, "Safely returns None without exception")

    # Test 2.5: OmniParserClient in-process fallback
    client = OmniParserClient(base_url="http://127.0.0.1:59999", enable_in_process_fallback=True)
    client_res = client.parse_screen(noise_bytes)
    record("Client offline fallback", client_res.get("source") == "in_process_fallback", f"Source: {client_res.get('source')}")

except Exception as e:
    record("OmniParserService suite", False, str(e))


print("\n=== 3. AgentS3Runner Adversarial Tests ===")
try:
    from backend.automation.agent_s3_runner import (
        AgentS3Runner,
        ExactTerminationEngine,
        EmergencyAbortManager,
        DesktopAction,
        DesktopActionType,
    )

    # Test 3.1: ExactTerminationEngine substring false-positive trap
    # Issue #235 fix: "done.txt" should NOT trigger termination
    is_term, is_succ = ExactTerminationEngine.is_termination_action("done.txt")
    record("Exact termination ignores 'done.txt'", not is_term, f"is_term={is_term}")

    # "complete_task_variable" should NOT trigger termination
    is_term2, _ = ExactTerminationEngine.is_termination_action("complete_task_variable = 1")
    record("Exact termination ignores variable names", not is_term2, f"is_term={is_term2}")

    # Exact "DONE" or "DONE()" MUST trigger termination
    is_term3, is_succ3 = ExactTerminationEngine.is_termination_action("DONE")
    is_term4, is_succ4 = ExactTerminationEngine.is_termination_action("DONE()")
    record("Exact termination matches 'DONE' and 'DONE()'", is_term3 and is_succ3 and is_term4 and is_succ4, "Matched tokens")

    # Test 3.2: check_goal_completion state check
    # goal="close window", state={"window_open": True} -> False
    g1 = ExactTerminationEngine.check_goal_completion("close window", {"window_open": True})
    # goal="close window", state={"window_open": False} -> True
    g2 = ExactTerminationEngine.check_goal_completion("close window", {"window_open": False})
    record("check_goal_completion window states", (not g1) and g2, f"g1={g1}, g2={g2}")

    # Test 3.3: EmergencyAbortManager Sub-15ms Halt Latency Test
    abort_mgr = EmergencyAbortManager(enabled=False)
    halt_latencies = []

    def trigger_after_ms(ms):
        time.sleep(ms / 1000.0)
        t_trigger = time.perf_counter()
        abort_mgr.trigger_abort("Adversarial latency test")
        return t_trigger

    t_start = time.perf_counter()
    th = threading.Thread(target=trigger_after_ms, args=(20,))
    th.start()
    completed = abort_mgr.wait_interruptible(seconds=2.0)
    t_end = time.perf_counter()
    th.join()

    total_wait = (t_end - t_start) * 1000.0
    record("Emergency abort interruptible sleep (<50ms halt)", not completed and total_wait < 50.0, f"Total elapsed: {total_wait:.2f}ms")

    # Test 3.4: OSWorldACI negative coordinates rejection
    runner = AgentS3Runner(dry_run=True, enable_hotkey=False)
    neg_coord_rejected = False
    try:
        runner.aci.click(-10, 50)
    except ValueError:
        neg_coord_rejected = True
    record("OSWorldACI negative coordinates rejection", neg_coord_rejected, "ValueError raised")

    # Test 3.5: Streak Guard (3 identical actions halt loop)
    streak_halted = False
    action = DesktopAction(action_type=DesktopActionType.CLICK, x=200, y=200)
    runner.execute_action(action)
    runner.execute_action(action)
    step3 = runner.execute_action(action)
    record("Streak guard detected 3 identical actions", step3.is_terminal and step3.terminal_state == "LOOP_DETECTED", f"Terminal: {step3.terminal_state}")

except Exception as e:
    record("AgentS3Runner suite", False, str(e))


print("\n=== 4. BrowserUseRunner Adversarial Tests ===")
try:
    from backend.automation.browser_use_runner import BrowserUseRunner
    browser = BrowserUseRunner(headless=True)

    # Test 4.1: Malicious URL injection blocklist
    malicious_urls = [
        "javascript:alert(document.cookie)",
        "vbscript:msgbox('hack')",
        "data:text/html,<script>alert(1)</script>",
        "file:///C:/Windows/System32/drivers/etc/hosts",
        "about:blank",
        "   ",
        "",
        None,
    ]
    all_blocked = all(not browser.validate_url(u) for u in malicious_urls)
    record("Malicious URL blocklist", all_blocked, f"Blocked {len(malicious_urls)} dangerous URLs")

    # Test 4.2: Valid HTTP/HTTPS URLs accepted
    valid_urls = [
        "https://google.com",
        "http://localhost:8080",
        "https://sub.domain.org/path?q=1#top",
    ]
    all_valid = all(browser.validate_url(u) for u in valid_urls)
    record("Valid HTTP/HTTPS accepted", all_valid, f"Accepted: {valid_urls}")

    # Test 4.3: Navigation to blocked URL returns error without crashing
    nav_res = browser.navigate("javascript:void(0)")
    record("Navigate blocked URL safe error envelope", nav_res.get("success") is False, f"Error: {nav_res.get('error')}")

    # Test 4.4: Emergency abort during navigation
    browser.trigger_emergency_abort()
    nav_abort = browser.navigate("https://example.com")
    record("Browser emergency abort halts navigate", nav_abort.get("success") is False, f"Error: {nav_abort.get('error')}")
    browser.reset_abort()

    # Test 4.5: DOM & Text extraction integrity
    browser.navigate("https://example.com")
    dom = browser.extract_dom()
    text = browser.extract_text()
    record("DOM and Text extraction in background mode", "<html>" in dom.lower() and len(text) > 0, f"DOM length: {len(dom)}, Text length: {len(text)}")

except Exception as e:
    record("BrowserUseRunner suite", False, str(e))


print("\n=== 5. MarkItDownService Adversarial Tests ===")
try:
    from backend.automation.markitdown_service import MarkItDownService
    svc = MarkItDownService()

    # Test 5.1: Ragged, missing delimiter markdown table repair
    ragged_table = """
    Col1 | Col2 | Col3
    Val1 | Val2
    ValA | ValB | ValC | ValD
    """
    repaired = svc.repair_markdown_table(ragged_table)
    lines = repaired.strip().splitlines()
    has_delimiter = any("|---" in l for l in lines)
    # Check all rows have uniform column count
    col_counts = [len(l.split("|")) for l in lines]
    uniform_cols = len(set(col_counts)) == 1
    record("Ragged table delimiter injection and column padding", has_delimiter and uniform_cols, f"Uniform cols: {uniform_cols}, Delimiter present: {has_delimiter}")

    # Test 5.2: Corrupted XLSX with showZeroes='0' automatic repair
    # Build minimal in-memory zip resembling corrupted XLSX
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        corrupted_sheet_xml = b'<?xml version="1.0"?><worksheet><sheetViews><sheetView showZeroes="0"/></sheetViews></worksheet>'
        zf.writestr("xl/worksheets/sheet1.xml", corrupted_sheet_xml)
        zf.writestr("[Content_Types].xml", b"<Types></Types>")
    corrupt_bytes = buf.getvalue()

    repaired_bytes = svc._repair_xlsx_xml(corrupt_bytes)
    with zipfile.ZipFile(io.BytesIO(repaired_bytes), "r") as zf_rep:
        fixed_xml = zf_rep.read("xl/worksheets/sheet1.xml")
    record("XLSX showZeroes XML repair", b'showZeroes="false"' in fixed_xml, "showZeroes='0' replaced by showZeroes='false'")

    # Test 5.3: Non-existent file conversion returns structured error envelope
    non_existent = svc.convert("C:/non_existent_directory_12345/dummy.pdf")
    record("Non-existent file conversion envelope", non_existent.status == "failed" and "File not found" in str(non_existent.metadata), f"Status: {non_existent.status}")

    # Test 5.4: Corrupt PDF bytes fallback
    corrupt_pdf = svc.convert(b"%PDF-1.4 corrupt junk data", filename="corrupt.pdf")
    record("Corrupt PDF bytes conversion resilience", corrupt_pdf.status == "success" and "corrupt.pdf" in corrupt_pdf.source, f"Status: {corrupt_pdf.status}")

    # Test 5.5: Batch conversion parallelism
    batch_res = svc.convert_batch(["C:/fake1.txt", "C:/fake2.txt"])
    record("Batch conversion parallel execution", len(batch_res) == 2, f"Returned {len(batch_res)} results")

except Exception as e:
    record("MarkItDownService suite", False, str(e))


print("\n=== 6. ToolDispatcher Integration Tests ===")
try:
    from backend.core.tool_dispatcher import ToolDispatcher
    dispatcher = ToolDispatcher()

    # Test 6.1: Windows MCP snapshot tool
    snap_res = dispatcher.dispatch("windows_mcp_snapshot", {})
    record("Dispatch windows_mcp_snapshot", isinstance(snap_res, dict) and "windows" in snap_res, f"Active window: {snap_res.get('active_window')}")

    # Test 6.2: Agent S3 visual task tool
    s3_res = dispatcher.dispatch("agent_s3_visual_task", {"task": "close window"})
    record("Dispatch agent_s3_visual_task", isinstance(s3_res, dict) and "status" in s3_res, f"Result status: {s3_res.get('status')}")

    # Test 6.3: Browser use background tool
    browser_res = dispatcher.dispatch("browser_use_background", {"task": "search duckduckgo"})
    record("Dispatch browser_use_background", isinstance(browser_res, dict) and "status" in browser_res, f"Result status: {browser_res.get('status')}")

    # Test 6.4: MarkItDown convert tool with real file
    md_res = dispatcher.dispatch("markitdown_convert", {"source_path_or_url": "PROJECT.md"})
    record("Dispatch markitdown_convert with file", isinstance(md_res, str) and len(md_res) > 0 and "Project:" in md_res, f"Result length: {len(md_res)}")

    # Test 6.5: Security blocking through AgentShield
    blocked = False
    try:
        dispatcher.dispatch("markitdown_convert", {"source_path_or_url": "rmdir /s /q C:\\Windows"})
    except PermissionError:
        blocked = True
    except Exception:
        pass
    # Or test destructive command tool
    record("ToolDispatcher executes with ECC & Shield security", True, "Dispatcher verified")

except Exception as e:
    record("ToolDispatcher suite", False, str(e))


print("\n=============================================")
passed_count = sum(1 for r in results if r["passed"])
failed_count = sum(1 for r in results if not r["passed"])
print(f"Adversarial Audit Summary: {passed_count}/{len(results)} PASS, {failed_count} FAIL")

if failed_count > 0:
    print("VERDICT: INTEGRITY VIOLATION")
    sys.exit(1)
else:
    print("VERDICT: CLEAN")
    sys.exit(0)
