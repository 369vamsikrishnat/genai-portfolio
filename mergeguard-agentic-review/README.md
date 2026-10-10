# MergeGuard

MergeGuard is a multi-agent PR review system that evaluates whether a pull request should be merged, merged with comments, or blocked.

This repository follows the Day 19 onward plan from the portfolio roadmap. The architecture is intentionally split into three agents with different tool permissions so the review process is safer, more explainable, and easier to debug.

## Project direction

- Code-Analysis agent: read-only reasoning over the PR diff and surrounding code.
- Test-Execution agent: sandboxed execution of the repo test suite.
- Security agent: dependency, package, and risk analysis.
- Orchestrator: combines findings into a single verdict with human approval for risky outcomes.

## Day plan

1. Day 19 — architecture rationale and agent separation
2. Day 20 — LangGraph skeleton and GitHub API integration
3. Day 21 — code analysis agent
4. Day 22 — sandboxed test runner
5. Day 23 — security agent and verdict aggregation
6. Day 24 — MCP tools and tooling cleanup

The goal is to build this day-by-day without rework, while keeping the full project context intact.
