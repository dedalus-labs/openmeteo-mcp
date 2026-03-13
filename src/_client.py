# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""Sample hosted client for openmeteo-mcp.

Environment variables:
    DEDALUS_API_KEY: Your Dedalus API key (dsk_*)
    DEDALUS_API_URL: Product API base URL
    DEDALUS_AS_URL: Authorization server URL

Open-Meteo is a public API, so no downstream credentials are required.
"""

from __future__ import annotations

import asyncio
import os

from dedalus_labs import AsyncDedalus, DedalusRunner
from dotenv import load_dotenv


class MissingEnvError(ValueError):
    """Required environment variable not set."""


def get_env(key: str) -> str:
    """Get required env var or raise."""
    val = os.getenv(key)
    if not val:
        raise MissingEnvError(key)
    return val


def load_env() -> tuple[str, str, str | None]:
    """Load and validate environment configuration."""
    load_dotenv()
    api_url = get_env("DEDALUS_API_URL")
    as_url = get_env("DEDALUS_AS_URL")
    api_key = os.getenv("DEDALUS_API_KEY")
    return api_url, as_url, api_key


async def run_with_runner() -> None:
    """Demo using DedalusRunner."""
    api_url, as_url, api_key = load_env()
    client = AsyncDedalus(api_key=api_key, base_url=api_url, as_base_url=as_url)
    runner = DedalusRunner(client)

    result = await runner.run(
        input="Get tomorrow's weather forecast for Berlin, Germany using the Open-Meteo MCP server.",
        model="openai/gpt-4.1",
        mcp_servers=["windsor/openmeteo-mcp"],
    )

    print("=== Model Output ===")
    print(result.output)

    if result.mcp_results:
        print("\n=== MCP Tool Results ===")
        for tool_result in result.mcp_results:
            print(f"  {tool_result.tool_name} ({tool_result.duration_ms}ms): {str(tool_result.result)[:200]}")


async def run_raw() -> None:
    """Demo using raw client."""
    api_url, as_url, api_key = load_env()
    client = AsyncDedalus(api_key=api_key, base_url=api_url, as_base_url=as_url)

    resp = await client.chat.completions.create(
        model="openai/gpt-4.1",
        messages=[
            {
                "role": "user",
                "content": "Get the current temperature in Berlin, Germany using the Open-Meteo MCP server.",
            }
        ],
        mcp_servers=["windsor/openmeteo-mcp"],
    )

    print("=== Model Output ===")
    print(resp.choices[0].message.content)

    if resp.mcp_tool_results:
        print("\n=== MCP Tool Results ===")
        for tool_result in resp.mcp_tool_results:
            print(f"  {tool_result.tool_name} ({tool_result.duration_ms}ms): {str(tool_result.result)[:200]}")


async def main() -> None:
    """Run both demo modes."""
    print("=" * 60)
    print("DedalusRunner")
    print("=" * 60)
    await run_with_runner()

    print("\n" + "=" * 60)
    print("Raw Client")
    print("=" * 60)
    await run_raw()


if __name__ == "__main__":
    asyncio.run(main())
