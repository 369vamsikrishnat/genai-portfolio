from pathlib import Path

import pytest

from mergeguard.workflow import graph
from mergeguard.sandbox import jobs as sandbox_jobs
from mergeguard.sandbox.jobs import _run_workspace_tests
from mergeguard.tools.sandbox_client import TestResult


def _mock_pytest(monkeypatch, return_code: int, output: str) -> None:
    class FakeProcess:
        pid = 123

        def __init__(self, *args, stdout, **kwargs):
            stdout.write(output.encode("utf-8"))

        def wait(self, timeout):
            return return_code

    monkeypatch.setattr(sandbox_jobs.subprocess, "Popen", FakeProcess)


@pytest.mark.parametrize(
    ("return_code", "expected_status"),
    [(0, "passed"), (1, "failed"), (2, "error"), (3, "error"), (4, "error"), (5, "error")],
)
def test_workspace_test_status_uses_pytest_exit_code(
    tmp_path: Path, monkeypatch, return_code: int, expected_status: str
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _mock_pytest(monkeypatch, return_code, "pytest output")

    result = _run_workspace_tests(workspace)

    assert result.status == expected_status


@pytest.mark.parametrize("error_marker", ["ModuleNotFoundError", "ImportError"])
def test_missing_dependency_output_is_an_error_even_outside_summary_tail(
    tmp_path: Path, monkeypatch, error_marker: str
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    output = f"{error_marker}: missing package\n" + ("x" * 1000)
    _mock_pytest(monkeypatch, 1, output)

    result = _run_workspace_tests(workspace)

    assert result.status == "error"
    assert result.summary == "Dependencies missing in the no-network sandbox; tests could not run."


@pytest.mark.parametrize(
    ("test_results", "expected_verdict", "expected_confidence", "expected_reason"),
    [
        ([{"status": "failed", "summary": "assertion failed"}], "BLOCK", 0.9, "tests failed"),
        (
            [{"status": "error", "summary": "Dependencies missing in the no-network sandbox; tests could not run."}],
            "MERGE",
            0.55,
            "tests could not run: dependencies missing",
        ),
        ([{"status": "passed", "summary": "ok"}], "MERGE", 0.72, "tests passed"),
    ],
)
def test_combine_verdict_classifies_test_results(
    test_results: list[dict[str, str]],
    expected_verdict: str,
    expected_confidence: float,
    expected_reason: str,
):
    result = graph.combine_verdict(test_results=test_results)

    assert result["verdict"] == expected_verdict
    assert result["confidence"] == expected_confidence
    assert expected_reason in result["reasons"]


def test_test_error_requests_human_review_and_is_stored_in_state():
    state = {
        "test_results": [
            {
                "status": "error",
                "summary": "Dependencies missing in the no-network sandbox; tests could not run.",
            }
        ]
    }

    result = graph.orchestrator_node(state)

    assert result["verdict"] != "BLOCK"
    assert result["requires_human_approval"] is True
    assert result["reasons"]
    assert result["reasons"] == ["tests could not run: dependencies missing"]