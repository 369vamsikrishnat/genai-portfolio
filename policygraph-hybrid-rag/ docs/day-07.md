# DAY 7 — End-to-End Pipeline + Timing

## Objective

Build the complete RAG pipeline by connecting all previously implemented components:

**Question → Dense Retrieval → BM25 → RRF → Cross-Encoder Reranking → Generation**

Also add per-step timing to identify which parts of the pipeline are slowest.

---

## 1. End-to-End Flow

The complete pipeline is:

```text
User Question
     │
     ▼
Dense Retrieval
     │
     ├──────────────┐
     ▼              ▼
BM25 Retrieval
     │              │
     └──────┬───────┘
            ▼
     Reciprocal Rank Fusion
            │
            ▼
     Candidate Documents
            │
            ▼
     Cross-Encoder Reranking
            │
            ▼
       Top Documents
            │
            ▼
       Gemini Generation
            │
            ▼
         Answer
```

### What each stage does

**Dense retrieval**

Finds documents based on semantic similarity between the question and document embeddings.

In the current implementation, the query embedding is created inside `dense_search()`.

**BM25 retrieval**

Finds documents based on lexical/keyword matching.

This is useful when the query contains exact policy terms, clause numbers, or specific words.

**RRF**

Reciprocal Rank Fusion combines the dense and BM25 rankings into one ranking.

The current implementation uses:

```text
RRF score = 1 / (k + rank)
```

with `k = 60`.

**Cross-Encoder reranking**

The Cross-Encoder receives the query together with each candidate document and directly scores their relevance.

It then sorts the candidates according to those scores.

Important distinction:

```text
reranker_load → loads the Cross-Encoder model

rerank → gives the model the query + documents,
         calculates relevance scores,
         and sorts the documents
```

**Generation**

The top reranked documents are passed to Gemini, which generates a document-grounded answer.

---

## 2. Pipeline Implementation

Created:

```text
src/pipeline.py
```

The pipeline connects:

```python
dense_search()
build_bm25()
search_bm25()
reciprocal_rank_fusion()
load_reranker()
rerank()
generate()
```

Each major stage is timed using:

```python
time.perf_counter()
```

The timings are stored in a dictionary so the execution time of each stage can be inspected.

---

## 3. Test Query

The pipeline was tested with:

```text
What happens if property damage is intentional?
```

The generated answer correctly identified that intentional damage caused by the policyholder, or someone acting with their knowledge or permission, is not covered.

The answer cited the relevant policy clauses:

```text
Document 1, Clause 1(b)
Document 2, Clause 4(a)
```

---

## 4. Final Reranked Results

The Cross-Encoder produced the following top results:

### 1. Clause 1(b) — Covered Events

Cross-Encoder score:

```text
3.1875
```

The clause states that covered damage must result from an unexpected event and must not be caused intentionally by the policyholder.

### 2. Clause 4(a) — Intentional Damage

Cross-Encoder score:

```text
2.6083
```

This directly states that intentional damage caused by the policyholder, or someone acting with their knowledge or permission, is not covered.

The remaining results were less relevant:

```text
Clause 2(c) — Internal Water Damage
Clause 2(a) — Flood Damage
Clause 1(a) — Covered Property
```

This demonstrates the purpose of reranking: the Cross-Encoder puts the most relevant candidates at the top after retrieval and fusion.

---

## 5. Timing Results

Actual pipeline timings from the test run:

```text
bm25_build           0.0023 seconds
reranker_load        7.8747 seconds
dense                7.0182 seconds
bm25                 0.0010 seconds
rrf                  0.0001 seconds
rerank               1.6826 seconds
generate             3.2927 seconds
```

### Slowest measured step

The slowest measured step was:

```text
reranker_load → 7.8747 seconds
```

However, this is primarily a **one-time model-loading cost**.

The Cross-Encoder model is loaded before reranking and then used for the actual reranking operation.

The actual reranking operation took:

```text
rerank → 1.6826 seconds
```

The dense retrieval step took:

```text
dense → 7.0182 seconds
```

Therefore, for repeated queries where the reranker is already loaded, dense retrieval is an important per-query cost in the current implementation.

---

## 6. Important Understanding

The pipeline has two different types of timing:

### Initialization cost

```text
reranker_load
```

This prepares the model.

### Query-time cost

```text
dense
bm25
rrf
rerank
generate
```

These operations happen as part of processing the query.

This distinction matters when evaluating the real performance of a RAG system.

---

## 7. Day 7 Checkpoint

### Walk the full flow from memory

✅ Question

→ Dense retrieval

→ BM25 retrieval

→ RRF fusion

→ Cross-Encoder reranking

→ Gemini generation

→ Final answer

### Identify the slowest step

✅ Slowest measured step:

```text
reranker_load = 7.8747 seconds
```

But this is model initialization.

The major per-query retrieval cost observed in this run was:

```text
dense = 7.0182 seconds
```

---

## Day 7 Status

**COMPLETE**

The project now has a working end-to-end RAG pipeline with per-step timing.
