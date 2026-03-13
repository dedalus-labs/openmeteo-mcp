# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

from __future__ import annotations

import asyncio
import socket

from dedalus_mcp import MCPClient
import pytest

import openmeteo
from openmeteo import openmeteo_tools
from server import create_server


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
    server.collect(*openmeteo_tools)

    task = asyncio.create_task(server.serve(host="127.0.0.1", port=port, log_level="warning", verbose=False))
    try:
        url = f"http://127.0.0.1:{port}/mcp"
        await _wait_for_server(url)
        async with await MCPClient.connect(url) as client:
            tools = await client.list_tools()
            tool_names = {tool.name for tool in tools.tools}
            assert "openmeteo_search_locations" in tool_names
            assert "openmeteo_get_forecast" in tool_names
            assert "openmeteo_get_forecast_for_location" in tool_names
    finally:
        await server.shutdown()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


@pytest.mark.asyncio
async def test_server_accepts_string_enum_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_get_json(
        base_url: openmeteo.ApiBaseUrl, path: str, params: dict[str, object]
    ) -> openmeteo.OpenMeteoResult:
        assert base_url == openmeteo.ApiBaseUrl.FORECAST
        assert path == "/forecast"
        assert params["temperature_unit"] == "fahrenheit"
        assert params["wind_speed_unit"] == "mph"
        assert params["precipitation_unit"] == "inch"
        return openmeteo.OpenMeteoResult(success=True, data={"ok": True, "params": params})

    monkeypatch.setattr(openmeteo, "_get_json", fake_get_json)

    port = _free_port()
    server = create_server()
    server.collect(*openmeteo_tools)

    task = asyncio.create_task(server.serve(host="127.0.0.1", port=port, log_level="warning", verbose=False))
    try:
        url = f"http://127.0.0.1:{port}/mcp"
        await _wait_for_server(url)
        async with await MCPClient.connect(url) as client:
            result = await client.call_tool(
                "openmeteo_get_forecast",
                {
                    "latitude": 52.52,
                    "longitude": 13.41,
                    "temperature_unit": "fahrenheit",
                    "wind_speed_unit": "mph",
                    "precipitation_unit": "inch",
                },
            )
            assert result.isError is False
            assert result.structuredContent is not None
            assert result.structuredContent["success"] is True
            assert result.structuredContent["data"]["ok"] is True
    finally:
        await server.shutdown()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
