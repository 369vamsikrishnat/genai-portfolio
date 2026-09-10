# Day 4 — Local Cross-Encoder Reranking

## 🎯 Goal

Add a local cross-encoder reranking stage after RRF retrieval.

The pipeline becomes:

```text
Query
  ↓
Dense Retrieval + BM25
  ↓
RRF
  ↓
Top 20 candidates
  ↓
Cross-Encoder Reranker
  ↓
Top 5 results
```

The purpose of reranking is to improve the ordering of the retrieved candidates by evaluating the query and each candidate chunk together.

---

## 📚 What I Learned

### Bi-Encoder vs Cross-Encoder

The Day 1 BGE model is used as a **bi-encoder**.

The query and document are encoded independently:

```text
Query ──→ BGE ──→ Query Embedding
Chunk ──→ BGE ──→ Chunk Embedding
```

Their embeddings are then compared using similarity.

The important property is that the query and chunk do not interact inside the model during encoding.

A **cross-encoder** processes the query and chunk together:

```text
Query + Chunk
     ↓
Cross-Encoder
     ↓
Relevance Score
```

Because the model evaluates the query-document pair jointly, it can make a more fine-grained relevance judgment.

### Why Use Both?

Dense retrieval is efficient for finding candidate documents from a large corpus because document embeddings can be created and stored beforehand.

The cross-encoder is more computationally expensive because it evaluates each query-document pair.

Therefore:

```text
Dense/BM25/RRF → Candidate Retrieval
Cross-Encoder  → Candidate Reranking
```

The cross-encoder does not replace the initial retrieval stage.

---

## 🧠 Why Rerank Only the Top 20?

Running the cross-encoder over the entire corpus would be expensive.

For example, if there are 1,000,000 chunks, evaluating:

```text
1 query × 1,000,000 chunks
```

would require 1,000,000 query-document evaluations.

Instead, the existing retrieval pipeline first reduces the search space:

```text
Large corpus
    ↓
Dense + BM25
    ↓
RRF
    ↓
Top 20
    ↓
Cross-Encoder
    ↓
Top 5
```

This gives the cross-encoder a small set of strong candidates to evaluate while keeping the system practical.

---

## 🛠️ What I Built

Created:

```text
src/retrieval/reranker.py
```

The reranker uses:

```text
cross-encoder/ms-marco-MiniLM-L-6-v2
```

and runs locally.

The implementation:

1. Loads the cross-encoder.
2. Takes the RRF candidate chunks.
3. Creates `(query, chunk)` pairs.
4. Sends the pairs to the cross-encoder.
5. Receives relevance scores.
6. Sorts candidates by score.
7. Returns the top 5.

Conceptually:

```python
pairs = [
    (query, chunk["content"])
    for chunk in chunks
]

scores = reranker.predict(pairs)
```

The model therefore evaluates:

```text
(query, chunk 1)
(query, chunk 2)
(query, chunk 3)
...
```

and assigns a relevance score to each pair.

---

## 🔎 Reranking Results

The five test queries were:

1. `What is covered for flood damage?`
2. `Clause 4(b)`
3. `What happens if property damage is intentional?`
4. `How long do I have to report property damage?`
5. `What water damage is covered?`

The cross-encoder successfully produced five reranked results for each query.

### Example: Reranking Changed the Top Result

Query:

```text
What is covered for flood damage?
```

Before reranking — RRF:

```text
#1 Clause 2(c) — Internal Water Damage
#2 Clause 2(a) — Flood Damage
#3 Clause 2(b) — External Water Sources
```

After reranking — Cross-Encoder:

```text
#1 Clause 2(a) — Flood Damage
#2 Clause 2(c) — Internal Water Damage
#3 Clause 2(b) — External Water Sources
```

The cross-encoder therefore changed the top result from **Internal Water Damage** to **Flood Damage**.

This demonstrates the purpose of the reranking stage: RRF provides a candidate ranking, while the cross-encoder evaluates the query-document relationship more directly and can reorder those candidates.

---

## 🔬 Other Observations

For:

```text
Clause 4(b)
```

the cross-encoder ranked:

```text
#1 Clause 4(b) — Policy Limits and Deductibles
Score: 7.9624
```

For:

```text
How long do I have to report property damage?
```

it ranked:

```text
#1 Clause 3(a) — Notice of Loss
Score: 8.2866
```

For:

```text
What water damage is covered?
```

it ranked:

```text
#1 Clause 2(c) — Internal Water Damage
Score: 7.3528
```

The model can produce both positive and negative scores. The important factor for this retrieval stage is the **relative ranking of candidates**, not treating the score as a universal probability.

---

## 💡 Key Technical Decisions

### Why a Cross-Encoder?

A cross-encoder can evaluate the relationship between a specific query and document together, allowing more detailed relevance assessment than independently encoded embeddings.

### Why `cross-encoder/ms-marco-MiniLM-L-6-v2`?

It was the specified local cross-encoder model for this stage of the project.

### Why Top-20 → Top-5?

The existing retrieval pipeline narrows the corpus to 20 candidates first. The more expensive cross-encoder then reranks those candidates and returns the five highest-ranked results.

### Why Keep Dense + BM25 + RRF?

Dense retrieval provides semantic matching, BM25 provides lexical/exact matching, and RRF combines their rankings before the more expensive reranking stage.

---

## ⚠️ Problems / Important Observations

The main conceptual distinction learned today was that **cross-encoder reranking is not about embedding dimensions**.

The difference is how the models process the query and document:

```text
Bi-Encoder:
Query → embedding
Chunk → embedding
       ↓
   similarity


Cross-Encoder:
Query + Chunk
      ↓
joint processing
      ↓
relevance score
```

The cross-encoder's advantage comes from jointly evaluating the query and chunk, not from simply using a different embedding dimension.

---

## 🎤 Interview Questions

### 1. What is the difference between a bi-encoder and a cross-encoder?

A bi-encoder independently encodes the query and document and compares their embeddings. A cross-encoder processes the query and document together and produces a relevance score.

### 2. Why is a cross-encoder generally more accurate for reranking?

Because the query and candidate document are processed jointly, allowing the model to evaluate their relationship more directly.

### 3. Why don't we run the cross-encoder over the entire corpus?

Because evaluating every query-document pair is computationally expensive.

### 4. Why do we rerank only the top 20 RRF results?

The first retrieval stages efficiently reduce the search space. The cross-encoder can then spend more computation evaluating only the strongest candidates.

### 5. What is the role of BGE in this pipeline?

BGE performs dense semantic retrieval and helps identify candidate chunks efficiently.

### 6. What is the role of BM25?

BM25 performs lexical retrieval and is useful when exact terms or phrases matter.

### 7. What is the role of RRF?

RRF combines the rankings from different retrieval methods, such as dense retrieval and BM25.

### 8. What is the role of the cross-encoder?

It reranks the retrieved candidates by evaluating each query-document pair together.

---

## ⚡ Quick Revision

```text
BGE
→ Dense semantic retrieval

BM25
→ Lexical/exact-term retrieval

RRF
→ Combines rankings

Top 20
→ Candidate set

Cross-Encoder
→ Jointly evaluates query + chunk

Top 5
→ Final reranked candidates
```

Remember:

> **Bi-encoder retrieves; cross-encoder reranks.**

And:

> **RRF combines rankings; it is not the cross-encoder reranker.**

---

## ✅ Day 4 Checkpoint

### 1. Explain why rerank only runs on top-20, not the full corpus

**Completed.**

The cross-encoder evaluates query-document pairs jointly and is more computationally expensive. Therefore, the retrieval pipeline first reduces the corpus to the top 20 candidates using Dense + BM25 + RRF, and the cross-encoder reranks only those candidates.

### 2. Show one query where rerank changed the top result

**Completed.**

Query:

```text
What is covered for flood damage?
```

Before reranking:

```text
#1 Clause 2(c) — Internal Water Damage
#2 Clause 2(a) — Flood Damage
#3 Clause 2(b) — External Water Sources
```

After reranking:

```text
#1 Clause 2(a) — Flood Damage
#2 Clause 2(c) — Internal Water Damage
#3 Clause 2(b) — External Water Sources
```

Therefore, the cross-encoder changed the top result.

---

## 📌 One-Minute Interview Summary

Today I added a local cross-encoder reranking stage to the hybrid RAG retrieval pipeline. Dense BGE retrieval and BM25 first produce candidates, and RRF combines their rankings. Instead of running the expensive cross-encoder over the entire corpus, I rerank only the top 20 RRF candidates and return the top 5. The cross-encoder processes each query and chunk together, allowing more fine-grained relevance assessment. I tested it on five insurance-policy queries and demonstrated a case where reranking changed the top result from Internal Water Damage to Flood Damage.
