# MergeGuard architecture rationale

## Why three agents instead of one

The core idea is simple: an LLM is powerful, but it behaves better when each decision is constrained to a small, well-scoped problem. Lilian Weng’s agent overview describes the important pattern clearly — an agent is not just a single model with a large prompt, but a controller with planning, memory, and tool use. In other words, intelligence improves when tools and responsibilities are separated and the model is given a narrow job rather than a broad unrestricted one.

For MergeGuard, one large generic agent would be too weak in three ways. First, it would mix reasoning about code logic, security risk, and test execution into one context window, which reduces precision and makes the review harder to trust. Second, it would carry too much power in one place: if the same model could both inspect code and run commands, the blast radius of a mistake or prompt injection becomes much larger. Third, the system would be harder to debug because a single agent could hide the reason behind a bad verdict behind a long, mixed narrative.

This is why MergeGuard intentionally uses three specialized agents with separate privileges.

## Code-Analysis agent: read-only, high-signal reasoning

The Code-Analysis agent should look at the PR diff, surrounding functions, and relevant files, but should not execute arbitrary code. Its job is to reason about correctness, regression risk, API contract breaks, and maintainability issues in the changed code.

This separation matters because “review logic” and “run commands” are different tasks with different failure modes. A code reviewer should be able to inspect intent and context without being able to mutate the repository or run risky shell commands. That makes the review output more trustworthy and makes prompt injection or malicious PR content less dangerous.

This agent produces structured findings such as severity, reason, and file/line reference. It is the human-readable intelligence layer for the workflow.

## Test-Execution agent: execution privilege, sandboxed only

The Test-Execution agent is the only component that is allowed to run the repo’s tests. It needs execution access because a merge decision is not credible without real evidence from the project’s build and test flow. However, that privilege must be isolated.

The agent should run in a container or sandbox with no internet access, read-only repository mount, and a separate scratch directory for generated artifacts. The system should never allow a broad or unrestricted environment where the agent can pull packages or reach external endpoints. This is a safety boundary, not just a convenience.

This gives us two major benefits: it preserves the ability to verify behavior, while reducing the risk of a malicious or buggy action causing external effects. The Test-Execution agent can answer “what actually broke?” without becoming the same as a general-purpose command runner.

## Security agent: dependency and supply-chain risk

The Security agent should be focused on dependency risk, package vulnerability checks, and suspicious changes that affect security posture. It is not the same as code reasoning and it is not the same as test execution. It looks at dependency manifests, lock files, package versions, and security scanning outputs.

This scope matters because dependency-related risk is often orthogonal to logic bugs or test failures. A PR can be functionally fine and still carry a serious supply-chain issue. The Security agent should produce structured findings with severity and explanations, then feed its output into the decision process.

## Orchestrator: not another model that does everything

The orchestrator is where the verdict is formed. It should not be a free-form “single teacher” model making the final call from raw data without structure. It should combine structured outputs from the three agents and apply rules such as:

- if any critical security finding exists, escalate or block;
- if tests fail, do not merge unless explicitly overridden;
- if the code-review agent finds material logic risk, surface it clearly;
- if confidence is low, require human review.

This is where we also add human-in-the-loop checkpoints. If a verdict is BLOCK or low-confidence, the process pauses and waits for explicit approval rather than silently proceeding.

## Why this is the right architecture for MergeGuard

This design follows the same principle behind strong agent systems: use specialized tools, constrain permissions, and keep reasoning separated from high-impact actions. It is more robust than a single-model PR reviewer because each agent owns a narrower objective, the system is easier to explain in interviews, and the resulting pipeline is easier to evaluate against actual PRs.

For a portfolio project, this is the right tradeoff. It demonstrates that we understand both the reasoning and the operational risk of building autonomous agents. The final result is not just “an AI reviewer,” but a controlled review workflow with actual safety boundaries.
