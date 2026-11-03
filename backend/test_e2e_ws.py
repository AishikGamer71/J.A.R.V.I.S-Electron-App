"""
backend/test_e2e_ws.py
Live End-to-End WebSocket, Telemetry, and Agent Execution Test.
"""

import sys
import os
import asyncio
import json
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn
import websockets
from backend.main import app
from backend.core.tool_registry import tool_registry
from backend.hardware.power_guardian import power_guardian

async def run_e2e_test():
    print("=" * 60)
    print("STARTING LIVE END-TO-END WEBSOCKET & RUNTIME VERIFICATION")
    print("=" * 60)

    # 1. Start uvicorn server in background
    config = uvicorn.Config(app, host="127.0.0.1", port=8765, log_level="warning")
    server = uvicorn.Server(config)
    server_task = asyncio.create_task(server.serve())

    # Wait for server to bind port
    await asyncio.sleep(2.0)

    try:
        # 2. Connect WebSocket client
        uri = "ws://127.0.0.1:8765/ws"
        print(f"Connecting to WebSocket: {uri}...")
        async with websockets.connect(uri) as ws:
            print("  [PASS] WebSocket connection established successfully!")

            # 3. Receive initial telemetry frame
            raw_msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
            telemetry_data = json.loads(raw_msg)
            assert telemetry_data.get("type") == "telemetry", f"Expected telemetry, got {telemetry_data.get('type')}"
            hw = telemetry_data.get("hardware", {})
            assert "battery_percent" in hw, "Missing battery_percent"
            assert "ac_plugged_in" in hw, "Missing ac_plugged_in"
            print(f"  [PASS] Live Hardware Telemetry verified: Battery={hw.get('battery_percent')}%, AC={hw.get('ac_plugged_in')}, RAM={hw.get('ram_percent')}%")

            # 4. Test ECC AgentShield command blocking
            print("Testing tool security rejection over tool registry...")
            denied_res = await tool_registry.execute("run_safe_terminal", {"command": "rm -rf /root"})
            assert denied_res["outcome"] == "DENIED", f"Expected DENIED, got {denied_res['outcome']}"
            print(f"  [PASS] AgentShield successfully denied dangerous tool execution: {denied_res['result']}")

            # 5. Send User Message over WebSocket
            print("Sending chat message over WebSocket to agent loop...")
            await ws.send(json.dumps({
                "type": "user.message",
                "content": "Status report, please.",
                "session_id": "test_e2e_session",
                "model": "offline-fallback"
            }))

            # Expect terminal log or agent response
            received_response = False
            start_wait = time.time()
            while time.time() - start_wait < 10.0:
                msg_str = await asyncio.wait_for(ws.recv(), timeout=6.0)
                msg = json.loads(msg_str)
                mtype = msg.get("type")
                if mtype == "terminal_log":
                    print(f"  [STREAM] TerminalLog event received: [{msg.get('level')}] {msg.get('message')[:60]}")
                elif mtype == "agent_response":
                    print(f"  [PASS] AgentResponse event received: {msg.get('content')[:80]}...")
                    received_response = True
                    break

            assert received_response, "Did not receive agent_response envelope"

            # 6. Test Charger State Alert Simulation
            print("Testing Power Guardian charger interrupt handling...")
            # Trigger power alert callback directly
            for cb in power_guardian._alert_listeners:
                cb("CRITICAL", "Sir, external power has been disconnected. Running on internal battery at 98 percent.")

            received_alert = False
            start_wait = time.time()
            while time.time() - start_wait < 6.0:
                raw_item = await asyncio.wait_for(ws.recv(), timeout=4.0)
                item = json.loads(raw_item)
                if item.get("type") == "terminal_log" and "external power has been disconnected" in item.get("message", ""):
                    received_alert = True
                    break
            assert received_alert, "Did not receive power guardian alert message on WebSocket"
            print("  [PASS] Power Guardian alert broadcast received over WebSocket successfully!")

    finally:
        server.should_exit = True
        await server_task

    print("=" * 60)
    print("LIVE END-TO-END RUNTIME VERIFICATION COMPLETE (100% PASS)")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_e2e_test())
