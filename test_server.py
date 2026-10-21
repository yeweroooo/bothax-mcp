#!/usr/bin/env python3
"""
Server-side test without the game:
 1. bridge channel: submit -> fake polling client -> POST result -> result received
 2. MCP stdio: spawn server.py, list tools, panggil device_info (ADB nyata)
"""
import asyncio
import json
import os
import sys
import threading
import time
import urllib.request

# Own port: if another server holds 8770 the test falls into attached mode and the
# result comes from a real game instead of the fake client below.
os.environ["GT_BRIDGE_PORT"] = "8771"

import server as srv  # noqa: E402  (port harus diset sebelum modul diimpor)


def test_bridge_channel():
    srv.start_bridge_server()
    time.sleep(0.3)
    got = {}

    def fake_game():
        # polling seperti bridge.lua
        deadline = time.time() + 10
        body = None
        while time.time() < deadline:
            with urllib.request.urlopen(f"http://127.0.0.1:{srv.BRIDGE_PORT}/poll") as r:
                payload = r.read().decode()
            if payload != "none":
                body = payload
                break
        assert body, "no command received"
        cmd_id, code = body.split("|", 1)
        got["code"] = code
        result = f'{cmd_id}|ok|{{name="BridgeTest"}}'.encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{srv.BRIDGE_PORT}/result", data=result, method="POST"
        )
        urllib.request.urlopen(req).read()

    t = threading.Thread(target=fake_game, daemon=True)
    t.start()
    out = srv.BRIDGE.submit("return GetLocal()", 8)
    t.join(5)
    print("  code sent     :", got.get("code"))
    print("  result received:", out)
    assert out == '{name="BridgeTest"}', out
    print("  [OK] two-way bridge channel")


async def test_mcp_stdio():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(
        command=sys.executable,
        args=[str(__file__).replace("test_server.py", "server.py")],
        env={**os.environ, "GT_BRIDGE_PORT": "8771"},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = [t.name for t in tools.tools]
            print(f"  {len(names)} tool:", ", ".join(names))
            res = await session.call_tool("device_info", {})
            text = res.content[0].text
            if text.startswith("ERROR"):
                print("  device_info:", text, "(no device attached, so the ADB path is untested)")
            else:
                data = json.loads(text)
                print("  device_info:", json.dumps({k: data[k] for k in ("model", "android", "game_running") if k in data}))
            print("  [OK] MCP stdio")


if __name__ == "__main__":
    print("1) bridge channel")
    test_bridge_channel()
    print("2) MCP stdio")
    asyncio.run(test_mcp_stdio())
    print("\nALL TESTS PASSED")
