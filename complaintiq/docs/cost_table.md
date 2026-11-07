# Cascade cost table

| mode | threshold | macro-F1 | escalated | est. $/1k complaints | est. latency (ms) |
|---|---|---|---|---|---|
| classifier_only |  | 0.456 | 0.0% | 0.0000 | 0.2 |
| llm_only |  | 0.694 | 100.0% | 0.1150 | 7125.1 |
| cascade | 0.7 | 0.666 | 51.7% | 0.0570 | 3681.5 |

Sample: 300 held-out (later-in-time) complaints. LLM: `gemini:gemini-3.5-flash-lite`. Costs are token counts x list price ($0.3/1M in, $2.5/1M out), not actual spend; latency is estimated from measured per-call times.
