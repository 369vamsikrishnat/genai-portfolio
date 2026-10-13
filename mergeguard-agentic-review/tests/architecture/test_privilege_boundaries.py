from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AGENT_FILES = (
    PROJECT_ROOT / "src" / "mergeguard" / "agents" / "code_analysis.py",
    PROJECT_ROOT / "src" / "mergeguard" / "agents" / "security.py",
)
SANDBOX_FILE = PROJECT_ROOT / "src" / "mergeguard" / "tools" / "sandbox_client.py"


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = (node.module or "").lstrip(".")
            if module:
                modules.add(module)
            modules.update(
                f"{module}.{alias.name}" if module else alias.name
                for alias in node.names
            )
    return modules


def _has_forbidden_import(modules: set[str], forbidden: str) -> bool:
    return any(forbidden in module.split(".") for module in modules)


def test_review_agents_do_not_cross_execution_privilege_boundary():
    forbidden_modules = ("subprocess", "sandbox", "sandbox_client")
    for path in AGENT_FILES:
        imported_modules = _imported_modules(path)
        for forbidden in forbidden_modules:
            assert not _has_forbidden_import(imported_modules, forbidden), (
                f"{path.relative_to(PROJECT_ROOT)} imports forbidden module {forbidden}"
            )


def test_sandbox_runner_module_does_not_import_subprocess():
    imported_modules = _imported_modules(SANDBOX_FILE)

    assert not _has_forbidden_import(imported_modules, "subprocess")
