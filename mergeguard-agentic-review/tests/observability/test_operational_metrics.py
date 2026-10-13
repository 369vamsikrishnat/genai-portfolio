from mergeguard.observability.metrics import (
    compute_completion_rate,
    compute_override_rate,
    compute_success_rate,
    summarize_run_metrics,
)


def test_success_rate_is_percentage_of_successful_tools():
    events = [
        {"tool": "github_client", "success": True},
        {"tool": "github_client", "success": False},
        {"tool": "sandbox", "success": True},
    ]

    assert compute_success_rate(events) == 66.67


def test_completion_rate_is_percentage_of_completed_runs():
    runs = [
        {"completed": True},
        {"completed": False},
        {"completed": True},
    ]

    assert compute_completion_rate(runs) == 66.67


def test_override_rate_is_percentage_of_human_overrides():
    reviews = [
        {"human_override": True},
        {"human_override": False},
        {"human_override": True},
    ]

    assert compute_override_rate(reviews) == 66.67


def test_summarize_run_metrics_returns_all_key_values():
    summary = summarize_run_metrics(
        tool_events=[
            {"tool": "github_client", "success": True},
            {"tool": "github_client", "success": False},
        ],
        runs=[
            {"completed": True},
            {"completed": False},
        ],
        reviews=[
            {"human_override": True},
            {"human_override": False},
        ],
    )

    assert summary["tool_success_rate"] == 50.0
    assert summary["task_completion_rate"] == 50.0
    assert summary["human_override_rate"] == 50.0
