# Day 3 — Reciprocal Rank Fusion (RRF)

## 🎯 Goal

Combine dense retrieval from Day 1 and BM25 retrieval from Day 2 using Reciprocal Rank Fusion (RRF), and compare the individual and fused rankings across five insurance-policy queries.

---

## 📚 What I Learned

### Reciprocal Rank Fusion (RRF)

**What it is:**

RRF is a ranking-fusion method that combines results from multiple retrieval systems into one ranking.

In this project, it combines:

* Dense retrieval
* BM25 retrieval

**Why we use it:**

Dense retrieval and BM25 produce scores using different methods, so their raw scores should not simply be added together.

RRF uses the **rank position** of each result instead.

**How it works:**

The formula used is:

```text
score(d) = Σ 1 / (k + rank(d))
```

For this project:

```text
k = 60
```

A document that appears highly ranked in multiple retrieval systems receives contributions from both systems.

---

## 🛠️ What I Built

Created:

```text
src/retrieval/fusion.py
```

The implementation:

1. Runs dense retrieval.
2. Runs BM25 retrieval.
3. Takes the ranked results from both retrievers.
4. Calculates an RRF score for each chunk.
5. Combines the rankings.
6. Sorts the chunks by their fused RRF score.
7. Returns the top results.

---

## 🔎 Retrieval Comparison

Tested RRF using five insurance-policy queries.

The five queries were:

```text
What is covered for flood damage?

Clause 4(b)

What happens if property damage is intentional?

How long do I have to report property damage?

What water damage is covered?
```

For each query, the implementation compared:

```text
Dense-only results
        ↓
BM25-only results
        ↓
RRF fused results
```

The results showed how the two retrieval methods can produce different rankings and how RRF combines their rankings.

---

## 💻 Important Code / Commands

### RRF Formula

```text
score(d) = Σ 1 / (k + rank(d))
```

with:

```text
k = 60
```

### Run the fusion implementation

```bash
python -m src.retrieval.fusion
```

### Core RRF calculation

```python
scores[chunk_id]["score"] += 1 / (k + rank)
```

The contribution is calculated from the document's rank rather than its original dense or BM25 score.

---

## 🧠 Key Technical Decisions

### Why use RRF?

Dense retrieval and BM25 use different scoring systems.

Instead of trying to combine their raw scores directly, RRF combines their **rank positions**.

This allows the two retrieval approaches to contribute to a common ranking.

### Why combine Dense + BM25?

The two retrieval methods provide different retrieval behavior:

```text
Dense → semantic / meaning-based retrieval

BM25 → lexical / keyword-based retrieval
```

Combining their rankings allows both retrieval approaches to contribute to the final result.

---

## ⚠️ Problems / Errors I Faced

### Initial BM25 exact-match issue from Day 2

The initial BM25 implementation had an issue matching:

```text
Clause 4(b)
```

with:

```text
Clause 4(b):
```

because simple whitespace tokenization treated them differently.

The tokenizer was adjusted so the clause identifier could be matched correctly.

After the fix, `Clause 4(b)` ranked first in the BM25 results.

---

## 🎤 Interview Questions

### Basic

**1. What is RRF?**

RRF is a method for combining rankings from multiple retrieval systems into one ranking.

**2. What formula does RRF use?**

```text
score(d) = Σ 1 / (k + rank(d))
```

For this implementation, `k = 60`.

### Practical

**3. Why did you use RRF in your RAG system?**

To combine dense semantic retrieval with BM25 lexical retrieval without directly combining their incompatible raw scores.

**4. What retrieval methods did you combine?**

Dense retrieval using the embedding-based retriever from Day 1 and BM25 retrieval from Day 2.

### Why / Trade-off

**5. Why not simply add the dense and BM25 scores?**

Their scores are produced differently and are not directly comparable. RRF avoids this by using ranking positions.

**6. What happens when a document appears highly ranked in both retrievers?**

It receives an RRF contribution from both rankings, increasing its final fused score.

### Project-specific

**7. What did you test RRF on?**

Five insurance-policy queries, including exact clause queries and more general coverage questions.

**8. What is the purpose of comparing dense-only, BM25-only, and fused results?**

To observe how each retriever ranks the documents and how RRF combines those rankings.

---

## ⚡ Quick Revision

* **RRF** → combines rankings from multiple retrieval systems.
* Dense retrieval → semantic/meaning-based retrieval.
* BM25 → lexical/keyword-based retrieval.
* RRF uses **rank**, not raw retrieval scores.
* Formula:

```text
score(d) = Σ 1 / (60 + rank(d))
```

* A document appearing highly in both rankings receives contributions from both.
* Tested the fusion pipeline on **5 insurance-policy queries**.
* Implemented RRF in:

```text
src/retrieval/fusion.py
```

---

## 📌 One-Minute Interview Summary

> Today I implemented Reciprocal Rank Fusion to combine the dense retrieval and BM25 retrieval approaches from the previous two days. Instead of adding their raw scores, I used the RRF formula with `k = 60`, which scores documents based on their rank in each retrieval system. I tested the fused retrieval on five insurance-policy queries and compared the dense-only, BM25-only, and fused rankings. This gives the system a way to combine semantic and lexical retrieval results into a single ranking.
