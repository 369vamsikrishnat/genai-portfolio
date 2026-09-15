# Day 10 — RAGAS Setup

## Goal

Set up the evaluation foundation for the PolicyGraph Hybrid RAG pipeline using RAGAS:

* Understand RAGAS
* Learn the four core RAGAS metrics
* Understand retrieval vs generation evaluation
* Prepare the RAG pipeline for measurable evaluation

---

## 1. RAGAS

RAGAS is a framework for evaluating Retrieval-Augmented Generation (RAG) systems.

It evaluates different parts of a RAG pipeline instead of judging only the final generated answer.

RAGAS helps evaluate:

* Retrieved context
* Generated answer
* Relationship between the question, context, and answer

---

## 2. Faithfulness

**Faithfulness** measures whether the generated answer is supported by the retrieved context.

**Key question:**

> Is the generated answer grounded in the retrieved information?

A faithful answer should not contain unsupported claims or hallucinated information.

---

## 3. Answer Relevancy

**Answer Relevancy** measures whether the generated answer is relevant to the user's question.

**Key question:**

> Does the answer actually address the question?

An answer can contain correct information but still have poor relevancy if it does not properly answer the user's question.

---

## 4. Context Precision

**Context Precision** measures whether relevant information is ranked highly within the retrieved context.

**Key question:**

> Are the relevant retrieved chunks ranked higher than irrelevant chunks?

Higher context precision means useful information appears earlier in the retrieved results.

---

## 5. Context Recall

**Context Recall** measures whether the retrieved context contains the information required to answer the question.

**Key question:**

> Did the retrieval system retrieve the information needed to answer the question?

If important information required for the answer is missing from the retrieved context, context recall is lower.

---

## 6. Four RAGAS Metrics

| Metric | What it evaluates |
|---|---|
| **Faithfulness** | Whether the answer is supported by the retrieved context |
| **Answer Relevancy** | Whether the answer addresses the question |
| **Context Precision** | Whether relevant context is ranked highly |
| **Context Recall** | Whether the required information was retrieved |

---

## 7. Retrieval vs Generation Evaluation

The four metrics can be grouped into two areas.

### Retrieval

* **Context Precision**
* **Context Recall**

These evaluate the quality of the context retrieved by the RAG system.

### Generation

* **Faithfulness**
* **Answer Relevancy**

These evaluate the quality of the answer generated from the retrieved context.

---

## 8. Key Understanding

A RAG system can fail at different stages:

```text
Question
   ↓
Retrieval
   ↓
Retrieved Context
   ↓
Generation
   ↓
Answer
