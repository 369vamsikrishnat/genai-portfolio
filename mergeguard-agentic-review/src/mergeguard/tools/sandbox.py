from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field


@dataclass
class SandboxConfig:
    network_disabled: bool = True
    read_only_mounts: list[str] = field(default_factory=lambda: ["/repo"])
    scratch_dir: str = "/tmp/mergeguard-scratch"


class TestResult(BaseModel):
    __test__ = False

    status: Literal["passed", "failed", "error"] = "passed"
    summary: str = Field(..., min_length=1)
    coverage_delta: float | None = 0.0
    network_disabled: bool = True


class SandboxedTestRunner:
    def __init__(self, config: SandboxConfig | None = None):
        self.config = config or SandboxConfig()

    def _prepare_environment(self) -> dict[str, str]:
        env = os.environ.copy()
        if self.config.network_disabled:
            env["NO_PROXY"] = "*"
            env["HTTP_PROXY"] = ""
            env["HTTPS_PROXY"] = ""
            env["http_proxy"] = ""
            env["https_proxy"] = ""
        return env

    def run_tests(self, repo_path: str = ".", command: list[str] | None = None) -> TestResult:
        cmd = command or ["python", "-m", "pytest", "-q"]
        env = self._prepare_environment()
        try:
            completed = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                env=env,
                timeout=180,
            )
        except subprocess.TimeoutExpired:
            return TestResult(
                status="error",
                summary="Sandboxed test execution timed out.",
                coverage_delta=None,
                network_disabled=self.config.network_disabled,
            )

        output = (completed.stdout or "") + "\n" + (completed.stderr or "")
        status = "passed" if completed.returncode == 0 else "failed"
        coverage_match = re.search(r"(?P<value>\d+(?:\.\d+)?)%", output)
        coverage_delta = float(coverage_match.group("value")) if coverage_match else 0.0
        summary = output.strip() or ("Tests passed." if status == "passed" else "Tests failed.")

        return TestResult(
            status=status,
            summary=summary[:500],
            coverage_delta=coverage_delta,
            network_disabled=self.config.network_disabled,
        )
