from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from mergeguard.tools.dependency_scanner import scan_dependency_files

mcp = FastMCP("mergeguard-security")


@mcp.tool()
def scan_dependencies(dependency_files: list[dict[str, str]], job_id: str) -> dict[str, Any]:
    """Scan fetched dependency manifest names and contents without installing packages."""
    return scan_dependency_files(dependency_files, job_id)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()