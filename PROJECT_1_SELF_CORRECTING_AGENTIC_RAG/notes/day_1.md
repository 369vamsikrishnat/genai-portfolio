# RAG Patterns & Agentic RAG — Interview Revision Notes

> Day 1 revision notes: Corrective RAG (CRAG), Self-RAG, Adaptive RAG, and LangGraph Agentic RAG.

---

## 1. RAG Fundamentals

### Basic RAG

The standard RAG flow is:

```text
Question → Retrieve → Generate
```

The core assumption is that the retrieved documents are relevant and trustworthy enough for generation.

### Problem with Basic RAG

Retrieval can return:

- Irrelevant documents
- Partially relevant documents
- Outdated information
- Insufficient evidence

If the system blindly passes poor retrieval results to the LLM, the final answer can be incorrect.

---

# 2. Corrective RAG (CRAG)

## Core idea

> **Retrieve → Evaluate → Correct → Generate**

CRAG does not blindly trust retrieved documents. It evaluates their quality and takes corrective action when the evidence is insufficient or unreliable.

### Mental model

```text
Question
   ↓
Retrieve
   ↓
Evaluate retrieved evidence
   ↓
Is evidence good?
   ├── Yes → Generate
   └── No  → Correct / Refine / Search for better evidence
                    ↓
                 Generate
```

## What problem does CRAG solve?

**Poor retrieval quality.**

A retriever may return documents that look relevant but do not actually contain enough reliable information to answer the question.

CRAG introduces an evaluation/correction step before generation.

## Important concepts

### Retrieval evaluation

Ask:

> "Does the retrieved information provide useful evidence for answering the question?"

Possible conceptual outcomes:

```text
GOOD
AMBIGUOUS
BAD
```

### Knowledge refinement

Instead of treating an entire retrieved document as equally useful, the system can focus on the parts that actually contain useful evidence and reduce irrelevant information.

### External search

If the initial retrieval is poor, the system can seek additional evidence from another source, such as web search.

## CRAG interview answer

> CRAG improves standard RAG by evaluating retrieved evidence and taking corrective action when the retrieval is insufficient or unreliable.

## Key distinction

**CRAG asks:**

> "Can I trust what I retrieved?"

---

# 3. Self-RAG

## Core idea

> **Decide whether retrieval is needed → Retrieve if needed → Generate → Reflect/Critique → Improve**

Self-RAG makes retrieval and reflection part of the model's decision process.

### Mental model

```text
Question
   ↓
Do I need retrieval?
   ├── No → Generate
   └── Yes
         ↓
      Retrieve
         ↓
      Generate
         ↓
      Critique
         ↓
   Improve if needed
```

## What problem does Self-RAG solve?

Traditional RAG retrieves for every query.

But retrieval is not always necessary.

Example:

```text
"What is 2 + 2?"
        ↓
Retrieval unnecessary
```

Whereas:

```text
"What changed in the latest API version?"
        ↓
Retrieval useful
```

Self-RAG allows the system to decide whether retrieval adds value.

## Reflection

After generating an answer, the system can evaluate things such as:

- Is the answer relevant?
- Is the answer supported by the retrieved evidence?
- Is the answer useful?

The system can then improve the response if necessary.

## Reflection tokens

The Self-RAG paper introduces special reflection tokens that allow the model to make decisions/evaluations around retrieval and generation.

Conceptually:

```text
Need retrieval?
Relevant evidence?
Supported answer?
Useful answer?
```

The important idea is that these judgments are incorporated into the trained model's behavior.

## Self-RAG interview answer

> Self-RAG allows the model to decide when retrieval is needed and uses reflection to evaluate the relevance, support, and quality of its generated response.

## Key distinction

**Self-RAG asks:**

> "Should I retrieve, and can I trust what I generated?"

---

# 4. Adaptive RAG

## Core idea

> **Question → Route → Choose the appropriate strategy → Execute → Generate**

Adaptive RAG dynamically chooses the retrieval strategy based on the query.

### Mental model

```text
Question
   ↓
Router
   ├── Direct → Generate
   ├── Local retrieval → Retrieve → Generate
   └── External/Web → Search → Generate
```

## What problem does Adaptive RAG solve?

A single retrieval strategy is not optimal for every question.

Examples:

### Simple question

```text
"What is 2 + 2?"
        ↓
Direct answer
```

### Internal knowledge question

```text
"What does our HR policy say about parental leave?"
        ↓
Internal knowledge-base retrieval
```

### Current/external question

```text
"What are the latest changes in Python?"
        ↓
External/web search
```

## Router

The router determines what kind of strategy the query requires.

Conceptually:

```text
Question
   ↓
Query Router
   ↓
Classification
   ├── NO_RETRIEVAL
   ├── LOCAL_RETRIEVAL
   └── WEB_RETRIEVAL
```

## Adaptive RAG interview answer

> Adaptive RAG dynamically selects an appropriate retrieval strategy based on the characteristics of the user's query instead of applying the same retrieval process to every question.

## Key distinction

**Adaptive RAG asks:**

> "Which strategy should I use for this query?"

---

# 5. CRAG vs Self-RAG vs Adaptive RAG

| Pattern | Main question | Core behavior |
|---|---|---|
| **CRAG** | Can I trust the retrieved evidence? | Evaluate and correct retrieval |
| **Self-RAG** | Should I retrieve, and is my answer good? | Selective retrieval + reflection |
| **Adaptive RAG** | Which strategy should I use? | Route the query to an appropriate strategy |

### Memory trick

```text
CRAG       → Correct
Self-RAG   → Reflect
Adaptive   → Route
```

---

# 6. LangGraph Agentic RAG

## Core idea

> **LangGraph represents an agentic workflow as a graph of nodes, state, and edges.**

This is useful because RAG workflows are not always linear.

Basic RAG:

```text
Question → Retrieve → Generate
```

Agentic RAG:

```text
Question
   ↓
Decision
  ↙ ↘
Node Node
  ↓   ↓
Decision
  ↙ ↘
...
```

The system can choose what to do next.

---

# 7. LangGraph Concepts

## State

State is the shared information carried through the workflow.

Example:

```text
state = {
    question,
    documents,
    generation
}
```

The state can evolve as nodes execute.

Example:

```text
Initial:
question = "What is our refund policy?"
documents = []
generation = ""

After retrieval:
question = "What is our refund policy?"
documents = [document1, document2]
generation = ""

After generation:
question = "What is our refund policy?"
documents = [document1, document2]
generation = "The refund period is..."
```

### Interview definition

> **State is the shared information that nodes read from and update as the graph executes.**

---

## Nodes

Nodes represent individual operations.

Examples:

```text
retrieve
generate
grade_documents
web_search
```

### Interview definition

> **A node is an individual operation/function in the graph.**

---

## Edges

Edges define how the workflow moves from one node to another.

Example:

```text
retrieve → grade_documents → generate
```

### Interview definition

> **An edge defines the transition between nodes.**

---

## Conditional edges

Conditional edges choose the next path based on the current result/state.

Example:

```text
             grade
            ↙     ↘
         good      bad
          ↓         ↓
       generate   web_search
```

### Interview definition

> **A conditional edge routes execution to different nodes based on a decision or the current state.**

---

# 8. Why LangGraph fits Agentic RAG

Agentic RAG requires control flow such as:

- Routing
- Retrieval evaluation
- Correction
- Retries
- Loops
- Multiple retrieval strategies
- Direct answering

These map naturally to:

```text
State
  +
Nodes
  +
Edges
  +
Conditional edges
```

---

# 9. Mapping the RAG Patterns to LangGraph

## CRAG

Concept:

```text
Retrieve → Evaluate → Correct
```

Possible graph:

```text
retrieve_node
      ↓
grade_node
    ↙   ↘
 good   bad
  ↓      ↓
answer  correction
```

---

## Self-RAG

Concept:

```text
Decide → Retrieve if needed → Generate → Reflect
```

Possible graph:

```text
decision_node
    ↙     ↘
 direct   retrieve
             ↓
          generate
             ↓
          critique
             ↓
       improve / finish
```

---

## Adaptive RAG

Concept:

```text
Question → Route → Strategy
```

Possible graph:

```text
              router
            ↙   ↓   ↘
        local   web  direct
          ↓      ↓     ↓
       retrieve search answer
```

---

# 10. Agent vs Pipeline

## Pipeline

A pipeline has a mostly predetermined sequence:

```text
A → B → C → D
```

## Agentic workflow

An agentic workflow can make decisions:

```text
A
↓
Decision
↙ ↘
B   C
```

It can also loop:

```text
Retrieve
   ↓
Evaluate
   ↓
Bad?
   ↓
Search
   ↓
Evaluate again
```

### Interview takeaway

> LangGraph is useful for agentic RAG because it allows us to explicitly model stateful, branching, and iterative workflows.

---

# 11. End-to-End Mental Model

```text
                     USER QUESTION
                           │
                           ▼
                    ┌─────────────┐
                    │   ROUTER    │
                    └──────┬──────┘
                           │
                ┌──────────┼──────────┐
                ▼          ▼          ▼
             Direct     Local RAG    Web
                │          │          │
                │       Retrieve    Search
                │          │          │
                │       Evaluate     │
                │          │          │
                │       Correct      │
                │          │          │
                └──────────┼──────────┘
                           ▼
                       Generate
                           │
                           ▼
                        Answer
```

This is a **conceptual combination**, not a requirement that every implementation must contain every step.

---

# 12. Interview Cheat Sheet

### Q: What is RAG?

> Retrieval-Augmented Generation retrieves external knowledge and provides it to an LLM to improve the factual grounding of generated answers.

### Q: What problem does CRAG solve?

> It addresses poor retrieval by evaluating retrieved evidence and taking corrective action when necessary.

### Q: What is the key idea behind Self-RAG?

> The model learns to decide when retrieval is needed and uses reflection to evaluate and improve its generated response.

### Q: What is Adaptive RAG?

> Adaptive RAG routes different queries to different retrieval or answering strategies instead of using one fixed retrieval pipeline.

### Q: CRAG vs Self-RAG?

> CRAG focuses on correcting retrieval quality, while Self-RAG focuses on selective retrieval and self-reflection over the generated answer.

### Q: Self-RAG vs Adaptive RAG?

> Self-RAG asks whether retrieval is needed and evaluates the generation; Adaptive RAG focuses on selecting the appropriate strategy/path for the query.

### Q: Why LangGraph for Agentic RAG?

> LangGraph provides state, nodes, edges, and conditional routing, making it suitable for branching, iterative, and stateful RAG workflows.

### Q: What is a node?

> An individual operation in the graph.

### Q: What is state?

> Shared information carried and updated throughout the graph.

### Q: What is a conditional edge?

> A routing mechanism that chooses the next node based on the current state or decision.

---

# 13. 30-Second Interview Explanation

> "Basic RAG follows a retrieve-then-generate pipeline, but retrieval isn't always reliable or even necessary. CRAG addresses retrieval quality by evaluating retrieved evidence and correcting it when needed. Self-RAG makes retrieval selective and adds reflection so the model can evaluate whether its generation is supported and useful. Adaptive RAG focuses on routing each query to the appropriate strategy, such as direct answering, local retrieval, or external search. LangGraph is useful for implementing these agentic workflows because it lets us model state, operations as nodes, transitions as edges, and decision-making through conditional edges."

---

# 14. Final Memory Map

```text
                         RAG
                          │
             ┌────────────┼────────────┐
             │            │            │
             ▼            ▼            ▼
           CRAG        Self-RAG    Adaptive RAG
             │            │            │
          Correct       Reflect       Route
             │            │            │
       "Is retrieval   "Should I     "Which
        reliable?"      retrieve?"    strategy?"
             │            │            │
             └────────────┼────────────┘
                          ▼
                     LangGraph
                          │
              ┌───────────┼───────────┐
              │           │           │
             State       Nodes       Edges
                                      │
                              Conditional edges
                                      │
                                      ▼
                             Agentic workflow
```

---

## One-line memory trick

**CRAG = Correct retrieval**

**Self-RAG = Reflect on retrieval + generation**

**Adaptive RAG = Route the query**

**LangGraph = Build the decision workflow**

---

# 15. Day 1 Research Resources

These are the exact resources from the Day 1 learning plan used as the basis for these notes.

1. **Corrective Retrieval Augmented Generation (CRAG)**  
   [arXiv — Corrective Retrieval Augmented Generation](https://arxiv.org/abs/2401.15884)  
   Read: **Abstract + figures only**

2. **Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection**  
   [arXiv — Self-RAG](https://arxiv.org/abs/2310.11511)  
   Read: **Abstract + figures only**

3. **Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language Models through Question Complexity**  
   [arXiv — Adaptive-RAG](https://arxiv.org/abs/2403.14403)  
   Read: **Abstract only**

4. **LangGraph Agentic RAG**  
   [LangChain — LangGraph Agentic RAG tutorial](https://langchain-ai.github.io/langgraph/tutorials/rag/langgraph_agentic_rag/)  
   Read: **Fully**

---
