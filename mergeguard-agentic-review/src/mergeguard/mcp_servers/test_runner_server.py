from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mergeguard.tools.sandbox_client import SandboxedTestRunner

mcp = FastMCP("mergeguard-test-runner")


@mcp.tool()
def run_tests(job_id: str) -> dict[str, object]:
    """Run tests for a staged job through the isolated sandbox runner."""
    return SandboxedTestRunner().run_tests(job_id).model_dump()


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()