# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

from __future__ import annotations

import asyncio
import socket

from dedalus_mcp import MCPClient
import pytest

from openmeteo import openmeteo_tools
from server import create_server
from smoke import smoke_tools


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


async def _try_connect(url: str) -> tuple[MCPClient | None, Exception | None]:
    try:
        return await MCPClient.connect(url), None
    except Exception as exc:
        return None, exc


async def _wait_for_server(url: str, attempts: int = 20, delay: float = 0.1) -> None:
    last_error: Exception | None = None
    for _ in range(attempts):
        client, error = await _try_connect(url)
        if client:
            await client.close()
            return
        last_error = error
        await asyncio.sleep(delay)
    raise RuntimeError(f"MCP server failed to start: {last_error}")


@pytest.mark.asyncio
async def test_server_starts_and_exposes_tools() -> None:
    port = _free_port()
    server = create_server()
    server.collect(*smoke_tools, *openmeteo_tools)

    task = asyncio.create_task(server.serve(host="127.0.0.1", port=port, log_level="warning", verbose=False))
    try:
        url = f"http://127.0.0.1:{port}/mcp"
        await _wait_for_server(url)
        async with await MCPClient.connect(url) as client:
            tools = await client.list_tools()
            tool_names = {tool.name for tool in tools.tools}
            assert "smoke_ping" in tool_names
            assert "openmeteo_search_locations" in tool_names
            assert "openmeteo_get_forecast" in tool_names
            assert "openmeteo_get_forecast_for_location" in tool_names

            result = await client.call_tool("smoke_ping", {"message": "weather-ok"})
            assert result.isError is False
            assert result.structuredContent is not None
            assert result.structuredContent["ok"] is True
            assert result.structuredContent["message"] == "weather-ok"
    finally:
        await server.shutdown()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
