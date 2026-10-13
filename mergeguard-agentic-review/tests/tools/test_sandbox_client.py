from inspect import signature

import pytest

from mergeguard.tools.sandbox_client import SandboxedTestRunner, TestResult


def test_sandbox_runner_delegates_valid_job_id(monkeypatch):
    expected = TestResult(status="passed", summary="Isolated tests passed.")
    calls = []

    def submit_sandbox_job(job_id: str) -> TestResult:
        calls.append(job_id)
        return expected

    monkeypatch.setattr("mergeguard.sandbox.jobs.submit_sandbox_job", submit_sandbox_job)

    result = SandboxedTestRunner().run_tests("d9428888-122b-4c01-a4cf-2fca3fc3e45e")

    assert result is expected
    assert calls == ["d9428888-122b-4c01-a4cf-2fca3fc3e45e"]


def test_sandbox_runner_rejects_invalid_job_id():
    with pytest.raises(ValueError, match="valid UUID"):
        SandboxedTestRunner().run_tests("not-a-uuid")


def test_sandbox_runner_has_no_command_parameter():
    parameters = signature(SandboxedTestRunner.run_tests).parameters

    assert list(parameters) == ["self", "job_id"]