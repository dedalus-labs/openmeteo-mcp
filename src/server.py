# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""MCP server entrypoint for the public Open-Meteo APIs."""

import os

from dedalus_mcp import MCPServer
from dedalus_mcp.server import TransportSecuritySettings

from openmeteo import openmeteo_tools


def create_server() -> MCPServer:
    """Create MCP server with current env config."""
    as_url = os.getenv("DEDALUS_AS_URL", "https://as.dedaluslabs.ai")
    return MCPServer(
        name="openmeteo-mcp",
        http_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
        streamable_http_stateless=True,
        authorization_server=as_url,
    )


async def main() -> None:
    """Start MCP server."""
    server = create_server()
    server.collect(*openmeteo_tools)
    await server.serve(port=8080)
