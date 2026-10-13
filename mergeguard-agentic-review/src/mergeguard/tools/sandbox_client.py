from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class TestResult(BaseModel):
    __test__ = False

    status: Literal["passed", "failed", "error"] = "passed"
    summary: str = Field(..., min_length=1)
    coverage_delta: float | None = None
    network_disabled: bool = True


class SandboxedTestRunner:
    def run_tests(self, job_id: str) -> TestResult:
        try:
            UUID(job_id)
        except (AttributeError, TypeError, ValueError) as error:
            raise ValueError("job_id must be a valid UUID.") from error

        from ..sandbox.jobs import submit_sandbox_job

        return submit_sandbox_job(job_id)
