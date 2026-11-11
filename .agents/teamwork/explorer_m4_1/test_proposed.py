"""
Test verification script for proposed M4 components:
1. proposed_windows_mcp_bridge.py
2. proposed_omniparser_service.py
"""

import unittest
import sys
from pathlib import Path

# Add current agent directory to path for proposed modules
CURRENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CURRENT_DIR))

from proposed_windows_mcp_bridge import WindowsMCPBridge
from proposed_omniparser_service import (
    OmniParserService,
    OmniParserClient,
    OMNIPARSER_PORT,
    DEFAULT_OMNIPARSER_PORT,
)


class TestProposedWindowsMCPBridge(unittest.TestCase):
    def test_f24_01_windows_mcp_bridge_exists(self):
        self.assertTrue((CURRENT_DIR / "proposed_windows_mcp_bridge.py").exists())

    def test_f24_02_exclude_jarvis_electron_hwnd(self):
        bridge = WindowsMCPBridge()
        self.assertTrue(bridge.is_excluded_window("J.A.R.V.I.S."))
        self.assertTrue(bridge.is_excluded_window("J.A.R.V.I.S. - Workspace"))
        self.assertTrue(bridge.is_excluded_window("JARVIS"))
        self.assertTrue(bridge.is_excluded_window("jarvis-electron-app"))
        self.assertFalse(bridge.is_excluded_window("Notepad"))
        self.assertFalse(bridge.is_excluded_window("Google Chrome"))

    def test_f24_03_inspect_desktop_tree(self):
        bridge = WindowsMCPBridge()
        elements = bridge.get_root_elements()
        self.assertIsInstance(elements, list)
        self.assertGreater(len(elements), 0)

    def test_f24_04_send_click_simulation(self):
        bridge = WindowsMCPBridge()
        res = bridge.simulate_click(x=100, y=100, dry_run=True)
        self.assertTrue(res.get("success", False))
        self.assertEqual(res.get("x"), 100)
        self.assertEqual(res.get("y"), 100)

    def test_f24_05_find_elements_by_name(self):
        bridge = WindowsMCPBridge()
        hits = bridge.find_elements_by_name("Taskbar")
        self.assertIsInstance(hits, list)
        self.assertGreater(len(hits), 0)
        self.assertIn("taskbar", hits[0]["name"].lower())


class TestProposedOmniParserService(unittest.TestCase):
    def test_f25_01_omniparser_service_exists(self):
        self.assertTrue((CURRENT_DIR / "proposed_omniparser_service.py").exists())

    def test_f25_02_omniparser_port(self):
        self.assertEqual(OMNIPARSER_PORT, 8002)
        self.assertEqual(DEFAULT_OMNIPARSER_PORT, 8002)

    def test_f25_03_omniparser_parse_empty_image(self):
        parser = OmniParserService()
        parsed = parser.parse_screen(image_bytes=b"")
        self.assertEqual(parsed.get("elements"), [])

    def test_f25_04_omniparser_models_specification(self):
        parser = OmniParserService()
        self.assertIn("YOLO", parser.detection_model_name.upper())

    def test_f25_05_omniparser_element_schema(self):
        parser = OmniParserService()
        elem = parser.format_element(box=[10, 20, 30, 40], label="button", caption="Submit")
        self.assertEqual(elem["label"], "button")
        self.assertEqual(elem["caption"], "Submit")
        self.assertEqual(elem["box"], [10, 20, 30, 40])

    def test_omniparser_tier2_opencv(self):
        import cv2
        import numpy as np
        # Create a synthetic image with two rectangles
        img = np.zeros((400, 600, 3), dtype=np.uint8)
        img[50:100, 50:200] = (255, 255, 255)  # A button
        img[150:200, 50:100] = (200, 200, 200) # An icon
        _, buf = cv2.imencode(".png", img)
        png_bytes = buf.tobytes()

        parser = OmniParserService(force_tier=2)
        parsed = parser.parse_screen(png_bytes)
        self.assertEqual(parsed["tier_used"], "tier2_opencv")
        self.assertGreater(len(parsed["elements"]), 0)

    def test_omniparser_tier3_heuristics(self):
        parser = OmniParserService(force_tier=3)
        dummy_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x01\x00\x00\x00\x01\x00\x08\x06\x00\x00\x00"
        parsed = parser.parse_screen(dummy_png)
        self.assertEqual(parsed["tier_used"], "tier3_heuristics")
        self.assertGreater(len(parsed["elements"]), 0)
        self.assertTrue(any(e["label"] == "button" for e in parsed["elements"]))

    def test_omniparser_client_in_process_fallback(self):
        client = OmniParserClient(base_url="http://127.0.0.1:9999", timeout=0.1) # nonexistent port
        parsed = client.parse_screen(b"")
        self.assertEqual(parsed.get("elements"), [])
        
        # Test with real image bytes through fallback
        dummy_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x01\x00\x00\x00\x01\x00\x08\x06\x00\x00\x00"
        parsed2 = client.parse_screen(dummy_png)
        self.assertEqual(parsed2.get("source"), "in_process_fallback")
        self.assertGreater(len(parsed2.get("elements", [])), 0)


if __name__ == "__main__":
    unittest.main()
