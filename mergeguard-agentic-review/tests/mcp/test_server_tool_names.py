from __future__ import annotations

import asyncio

from mcp.shared.memory import create_connected_server_and_client_session

from mergeguard.mcp_servers import github_server, security_server, test_runner_server


async def _tool_names(server):
    async with create_connected_server_and_client_session(server) as session:
        response = await session.list_tools()
        return {tool.name for tool in response.tools}


def test_servers_expose_protocol_tools():
    assert asyncio.run(_tool_names(github_server.mcp)) == {
        "get_pull_request",
        "get_changed_files",
        "get_file_content",
        "get_pr_conversation",
    }
    assert asyncio.run(_tool_names(test_runner_server.mcp)) == {"run_tests"}
    assert asyncio.run(_tool_names(security_server.mcp)) == {"scan_dependencies"}
