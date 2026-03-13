# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""Sample MCP client for testing openmeteo-mcp locally."""

from __future__ import annotations

import asyncio

from dedalus_mcp.client import MCPClient


SERVER_URL = "http://localhost:8080/mcp"


async def main() -> None:
    """Connect to the local server and exercise a couple of tools."""
    client = await MCPClient.connect(SERVER_URL)

    result = await client.list_tools()
    print(f"\nAvailable tools ({len(result.tools)}):\n")
    for tool_info in result.tools:
        print(f"  {tool_info.name}")
        if tool_info.description:
            print(f"    {tool_info.description}")
        print()

    print("--- openmeteo_search_locations ---")
    locations = await client.call_tool("openmeteo_search_locations", {"name": "Berlin", "count": 1})
    print(locations)
    print()

    print("--- openmeteo_get_forecast_for_location ---")
    forecast = await client.call_tool(
        "openmeteo_get_forecast_for_location",
        {
            "location": "Berlin",
            "country_code": "DE",
            "current": ["temperature_2m", "weather_code"],
            "hourly": ["temperature_2m", "precipitation_probability"],
            "forecast_days": 2,
        },
    )
    print(forecast)

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
