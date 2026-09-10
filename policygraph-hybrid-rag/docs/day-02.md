# Day 2 — Section-Aware Chunking + BM25 Retrieval

## Goal

Improve retrieval for structured insurance-policy documents by:

* Keeping sections and clauses intact during chunking.
* Preserving useful document metadata.
* Adding BM25 lexical retrieval.
* Understanding when BM25 is more useful than dense retrieval.

---

## What I Learned

### 1. Section-Aware Chunking

Fixed-size chunking can split a logically complete clause across multiple chunks.

For example, **Clause 4(b)** was split across fixed-size chunks, while section-aware chunking kept the complete clause together.

Insurance documents have explicit structure:

```text
Section 4: Exclusions and Special Conditions

Clause 4(b): Policy Limits and Deductibles

The insurer's payment...
```

A section-aware chunker uses this structure instead of blindly splitting based on character/token count.

### 2. Metadata

Each section-aware chunk stores:

* `section_number`
* `section_title`
* `doc_name`
* `page_number`
* `content`

### 3. BM25

BM25 is a **lexical/keyword-based retrieval algorithm**.

It considers:

* Term Frequency (TF)
* Inverse Document Frequency (IDF)
* Document length

#### TF — Term Frequency

How often a term occurs in a document.

#### IDF — Inverse Document Frequency

Measures how rare/informative a term is across the document collection.

```text
Rare term → more informative
Common term → less informative
```

#### Document Length

BM25 applies length normalization so longer documents do not automatically receive an advantage simply because they contain more words.

### 4. Dense vs BM25

Dense retrieval and BM25 solve different retrieval problems.

```text
Dense retrieval → semantic / meaning-based matching

BM25 → lexical / keyword-based matching
```

Dense retrieval is useful for questions where meaning matters.

BM25 is particularly useful for exact identifiers, names, and domain-specific terms.

For example:

```text
Clause 4(b)
```

is an exact identifier, making BM25 particularly useful.

---

## What I Built

### Section-Aware Chunker

Created:

```text
src/ingestion/chunker.py
```

The chunker uses regex-based section and clause detection.

It preserves the complete clause together with its section context.

### Synthetic Insurance Policies

Created three synthetic insurance-policy documents containing numbered sections and clauses.

Example structure:

```text
Section 4: Exclusions and Special Conditions

Clause 4(a): Intentional Damage
Clause 4(b): Policy Limits and Deductibles
Clause 4(c): Effective Coverage
```

### BM25 Retriever

Created:

```text
src/retrieval/bm25.py
```

Implemented BM25 using:

```python
from rank_bm25 import BM25Okapi
```

The implementation:

1. Tokenizes chunks.
2. Builds a BM25 index.
3. Tokenizes the query.
4. Calculates BM25 scores.
5. Sorts chunks by score.
6. Returns the top-k results.

---

## Important Code / Commands

### Install BM25

```bash
pip install rank-bm25
```

### Run BM25

```bash
python -m src.retrieval.bm25
```

### Tokenization

A custom tokenizer was used so identifiers such as:

```text
4(b)
```

can match correctly despite punctuation such as:

```text
4(b):
```

---

## Retrieval Tests

### Test 1 — Exact Clause Identifier

Query:

```text
Clause 4(b)
```

Result:

```text
2.0160 | Section 4: Exclusions and Special Conditions

Clause 4(b): Policy Limits and Deductibles
```

The correct clause ranked **#1**.

This demonstrates BM25's strength for exact lexical matching.

### Test 2 — Vague Query

Query:

```text
what is covered
```

Top result:

```text
0.7193 | Section 2: Flood Protection

Clause 2(a): Flood Damage
```

Other highly ranked results included covered-property and coverage-related clauses.

This demonstrates that BM25 can find keyword matches but does not perform semantic understanding like dense retrieval.

---

## Comparison With Day 1 Dense Retrieval

For the Day 1 flood-damage query, BGE produced:

```text
0.8542  Flood damage covered
0.7590  External water sources
0.6995  Storm-related damage
0.6821  Fire
0.6769  Water damage
```

BM25 is better suited to queries such as:

```text
Clause 4(b)
```

because the query is an exact document identifier.

Dense retrieval is better suited to queries where the user expresses an idea or meaning rather than an exact phrase.

---

## Key Technical Decisions

### 1. Keep clauses intact

Insurance clauses represent complete pieces of policy meaning, so splitting them arbitrarily can damage retrieval quality.

### 2. Preserve section context

The section heading is included with the clause so retrieved chunks retain their structural context.

### 3. Use BM25 for lexical matching

BM25 provides a complementary retrieval method to the BGE dense retriever from Day 1.

### 4. Custom tokenization

Simple whitespace tokenization caused:

```text
4(b)
```

and:

```text
4(b):
```

to become different tokens.

The tokenizer was adjusted to preserve identifiers such as `4(b)`.

---

## Problems / Errors

### BM25 initially failed to rank Clause 4(b) correctly

Initial whitespace tokenization produced:

```text
Query:
4(b)

Document:
4(b):
```

Because these were treated as different tokens, the expected clause did not rank first.

### Fix

A regex-based tokenizer was introduced to normalize the clause identifier and allow:

```text
4(b)
```

to match:

```text
4(b):
```

After the fix, `Clause 4(b)` ranked **#1**.

---

# Interview Questions

### 1. What is BM25?

BM25 is a lexical information-retrieval ranking algorithm based on term frequency, inverse document frequency, and document length normalization.

### 2. What is the difference between BM25 and dense retrieval?

BM25 performs lexical/keyword matching, while dense retrieval performs semantic/meaning-based matching using embeddings.

### 3. Why is BM25 useful for insurance documents?

Insurance documents contain exact identifiers such as sections, clauses, policy terms, and specific terminology where lexical matching can be very effective.

### 4. What is TF?

Term Frequency measures how frequently a term occurs in a document.

### 5. What is IDF?

Inverse Document Frequency measures how rare and informative a term is across the document collection.

### 6. Why does BM25 consider document length?

To prevent longer documents from receiving an unfair advantage simply because they contain more words.

### 7. Why can fixed-size chunking be problematic for policy documents?

It can split a logically complete clause across multiple chunks, separating related information.

### 8. Why use section-aware chunking?

It uses the document's existing structure to create semantically meaningful chunks while preserving section and clause context.

### 9. Why did `Clause 4(b)` initially fail to rank first?

Whitespace tokenization treated `4(b)` and `4(b):` as different tokens.

### 10. When would you prefer BM25 over dense retrieval?

When the query contains exact identifiers, names, keywords, or terminology where literal matching is important.

---

# Quick Revision

```text
Fixed-size chunking
        ↓
Can split clauses
        ↓
Section-aware chunking
        ↓
Keeps logical policy units intact
```

```text
BM25
 ├── TF
 ├── IDF
 └── Document length normalization
```

```text
Dense retrieval
→ semantic similarity

BM25
→ lexical similarity
```

Remember:

> **Dense asks: "What does this query mean?"**

> **BM25 asks: "Which documents contain the important words from this query?"**

---

# Day 2 Checkpoint

* [x] Section-aware chunking example demonstrated.
* [x] Fixed-size chunking shown splitting Clause 4(b).
* [x] Section-aware chunking shown preserving Clause 4(b).
* [x] Three synthetic insurance policy documents created.
* [x] Section/clause metadata implemented.
* [x] BM25 concepts understood.
* [x] `rank_bm25` implemented.
* [x] `Clause 4(b)` successfully ranked #1 by BM25.
* [x] Vague query `what is covered` tested.
* [x] BM25 behavior compared conceptually with Day 1 dense retrieval.

## Status: DAY 2 COMPLETE ✅

---

# One-Minute Interview Summary

> On Day 2, I improved retrieval for structured insurance documents using section-aware chunking and BM25. Instead of splitting documents into arbitrary fixed-size chunks, I used section and clause boundaries so that complete policy clauses remain intact with their section context and metadata. I then implemented BM25 using `rank_bm25` for lexical retrieval. BM25 was particularly effective for exact identifiers such as `Clause 4(b)`, where dense semantic retrieval may not be ideal. Dense retrieval and BM25 therefore provide complementary retrieval capabilities: dense retrieval handles semantic similarity, while BM25 handles important lexical and exact-term matches.

---
