from __future__ import annotations

from typing import Any

from mergeguard.observability import tracing
from mergeguard.tools.sandbox_client import TestResult

from .common import MergeGuardState
from .mcp_client import call_agent_tool

__test__ = False


def test_execution_node(state: MergeGuardState) -> dict[str, Any]:
    with tracing.trace_observation(state.get("job_id", ""), "test_execution") as agent_span:
        if state.get("test_results") is not None:
            tracing.update_observation(agent_span, output={"status": "precomputed"})
            return {}

        result_payload = tracing.record_tool_call(
            state["job_id"],
            "sandbox.run_tests",
            lambda: call_agent_tool(
                "test_execution",
                "test_runner",
                "run_tests",
                {"job_id": state["job_id"]},
            ),
        )
        result = TestResult.model_validate(result_payload)
        tracing.update_observation(agent_span, output={"status": result.status})
        return {"test_results": [result.model_dump()]}