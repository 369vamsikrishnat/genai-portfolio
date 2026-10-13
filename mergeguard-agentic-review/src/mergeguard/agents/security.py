from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

from mergeguard.observability import tracing
from mergeguard.observability.tracing import should_skip_security_review

from .common import MergeGuardState, SecurityFinding
from .mcp_client import call_agent_tool


def _security_review_node(state: MergeGuardState) -> dict[str, Any]:
    if should_skip_security_review(state.get("changed_files", [])):
        return {"security_findings": [], "agents_skipped": ["security_review"]}

    owner = state.get("owner", "")
    repo = state.get("repo", "")
    head_sha = state.get("head_sha", "")
    dependency_files: list[dict[str, str]] = []
    reasons: list[str] = []
    unsupported_findings: list[SecurityFinding] = []

    for repo_path in state.get("changed_files", []):
        name = PurePosixPath(repo_path.replace("\\", "/")).name.lower()
        is_requirements = name.startswith("requirements") and name.endswith(".txt")
        is_npm_manifest = name in {"package.json", "package-lock.json"}
        is_supported_manifest = is_requirements or is_npm_manifest
        if not is_supported_manifest:
            reason = f"dependency scan skipped: {repo_path} is not a supported manifest"
            reasons.append(reason)
            unsupported_findings.append(
                SecurityFinding(severity="low", description=reason, package_name="unknown")
            )
            continue
        content = tracing.record_tool_call(
            state["job_id"],
            "github.get_file_content.security",
            lambda repo_path=repo_path: call_agent_tool(
                "security_review",
                "github",
                "get_file_content",
                {"owner": owner, "repo": repo, "path": repo_path, "ref": head_sha},
            ),
        )
        if content is None:
            reasons.append(f"dependency scan skipped: {repo_path} was not available at the PR head")
            continue
        project = str(PurePosixPath(repo_path.replace("\\", "/")).parent)
        dependency_files.append({"name": name, "content": content, "project": project})

    scan_result = tracing.record_tool_call(
        state["job_id"],
        "mcp.security.scan_dependencies",
        lambda: call_agent_tool(
            "security_review",
            "security",
            "scan_dependencies",
            {"dependency_files": dependency_files, "job_id": state["job_id"]},
        ),
    )
    findings = unsupported_findings + [
        SecurityFinding.model_validate(item) for item in scan_result.get("security_findings", [])
    ]
    reasons.extend(scan_result.get("reasons", []))
    return {"security_findings": findings, "reasons": reasons}


def security_review_node(state: MergeGuardState) -> dict[str, Any]:
    with tracing.trace_observation(state.get("job_id", ""), "security_review") as agent_span:
        result = _security_review_node(state)
        tracing.update_observation(
            agent_span,
            output={
                "finding_count": len(result.get("security_findings", [])),
                "reason_count": len(result.get("reasons", [])),
                "skipped": "security_review" in result.get("agents_skipped", []),
            },
        )
        return result
