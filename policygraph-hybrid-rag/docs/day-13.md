# Day 13 — Retrieval Ablation Study

## What I Learned

Day 13 focused on retrieval ablation — measuring how much each retrieval technique and chunking strategy contributes to finding the correct evidence in a RAG system.

The main idea behind ablation testing is:

> Change one part of the system while keeping the other parts as consistent as possible, then measure the impact.

This helps understand whether a component actually improves the system instead of assuming that adding more components automatically makes the system better.

---

## 1. Retrieval Ablation

The retrieval pipeline was evaluated using three configurations.

### Dense Only

Dense retrieval converts the query into an embedding and finds semantically similar document chunks.

    Query
      ↓
    BGE Embedding
      ↓
    Vector Similarity
      ↓
    Top Results

This provides the baseline.

### Dense + BM25 + RRF

Dense retrieval and BM25 lexical retrieval are combined using Reciprocal Rank Fusion (RRF).

    Query
       ├── Dense Retrieval
       └── BM25 Retrieval
               ↓
           RRF Fusion
               ↓
           Top Results

Dense retrieval helps with semantic similarity, while BM25 helps with exact terms, keywords, and clause identifiers.

RRF combines the rankings from both retrieval methods.

### Dense + BM25 + RRF + Reranking

After fusion, a cross-encoder reranks the retrieved candidates.

    Dense + BM25
         ↓
      RRF Fusion
         ↓
    Candidate Results
         ↓
    Cross-Encoder
         ↓
    Reranked Results

The cross-encoder evaluates the relationship between the query and each candidate chunk more deeply than the initial embedding similarity.

---

## 2. Retrieval Ablation Results

The experiment used 47 answerable cases from the golden set.

| Configuration | Recall@5 | Hit@1 | Hit@3 | Hit@5 | MRR |
|---|---:|---:|---:|---:|---:|
| Dense Only | 0.7660 | 0.5957 | 0.7447 | 0.7660 | 0.6766 |
| Dense + BM25 + RRF | 0.8085 | 0.6383 | 0.7660 | 0.8085 | 0.7131 |
| Dense + BM25 + RRF + Reranking | 0.7447 | 0.7447 | 0.7447 | 0.7447 | 0.7447 |

### Observations

- Dense-only retrieval provides the baseline.
- Adding BM25 and RRF increased Recall@5 from 0.7660 to 0.8085.
- Reranking produced a higher Hit@1 than dense-only and hybrid retrieval.
- Reranking also had higher query latency because the cross-encoder performs additional computation.
- Adding another retrieval component does not automatically improve every metric.
- Different retrieval stages can affect ranking quality differently.

These results are specific to the current policy document and golden set.

---

## 3. Understanding Hit@K

Hit@K asks:

> Did the correct evidence appear anywhere within the top K results?

### Hit@1

Only rank 1 matters.

    Rank 1 → Correct

Result:

    Hit@1 = 1

If the correct chunk is at rank 3:

    Rank 1 → Wrong
    Rank 2 → Wrong
    Rank 3 → Correct

Then:

    Hit@1 = 0

### Hit@3

The correct evidence can appear anywhere from rank 1 through rank 3.

### Hit@5

The correct evidence can appear anywhere from rank 1 through rank 5.

Therefore:

    Hit@1 ≤ Hit@3 ≤ Hit@5

for the same evaluation set.

---

## 4. Understanding MRR

MRR stands for Mean Reciprocal Rank.

It measures how highly the first relevant result appears.

For a relevant result at rank r:

    Reciprocal Rank = 1 / r

Examples:

    Rank 1 → 1.00
    Rank 2 → 0.50
    Rank 3 → 0.33
    Rank 4 → 0.25
    Rank 5 → 0.20

If no relevant result appears:

    Reciprocal Rank = 0

MRR is the average reciprocal rank across all evaluation cases.

Therefore, MRR rewards systems that place the correct evidence closer to the top.

---

## 5. Why Reranking Had Identical Metric Values

The reranking experiment produced:

    Hit@1 = 0.7447
    Hit@3 = 0.7447
    Hit@5 = 0.7447
    MRR   = 0.7447

This does not mean the metric calculation is incorrect.

It happened because, for this particular evaluation set, successful cases generally had the correct evidence at rank 1, while unsuccessful cases did not have matching evidence within the top 5.

For a successful case:

    Rank 1 → Correct

we get:

    Hit@1 = 1
    Hit@3 = 1
    Hit@5 = 1
    MRR   = 1

For an unsuccessful case:

    No relevant result in top 5

we get:

    Hit@1 = 0
    Hit@3 = 0
    Hit@5 = 0
    MRR   = 0

When averaged across the cases, all four metrics therefore become the same value.

This is a characteristic of the observed ranking distribution on this dataset, not a general property of reranking.

---

## 6. Chunking Ablation

A second experiment tested the effect of chunking strategy.

The two strategies were:

    Section-aware chunking

and:

    Fixed-size chunking

The purpose was to determine whether preserving the structure of the policy document helps retrieval.

---

## 7. Section-Aware Chunking

Section-aware chunking understands the structure of the document.

Chunks can preserve information such as:

- Section number
- Section title
- Clause structure
- Page number
- Document name

This is useful for structured documents such as insurance policies because meaning is often connected to sections and clauses.

The experiment produced:

    32 section-aware chunks

---

## 8. Fixed-Size Chunking

Fixed-size chunking divides text according to a fixed size without understanding the document's logical structure.

The experiment used:

    200

as the fixed chunk size and produced:

    108 fixed-size chunks

This approach is simpler, but it can split related information across chunk boundaries.

---

## 9. Chunking Ablation Results

The experiment used the same 47 answerable golden-set cases and the same dense BGE retrieval method for both chunking strategies.

| Configuration | Chunks | Recall@5 | Hit@1 | Hit@3 | Hit@5 | MRR |
|---|---:|---:|---:|---:|---:|---:|
| Section-aware | 32 | 0.9574 | 0.8298 | 0.9149 | 0.9574 | 0.8840 |
| Fixed-size | 108 | 0.7660 | 0.6383 | 0.7447 | 0.7660 | 0.7000 |

### Observations

- Section-aware chunks retrieved the expected evidence more frequently on this golden set.
- Section-aware chunking achieved 0.9574 Recall@5 compared with 0.7660 for fixed-size chunking.
- Section-aware chunking achieved higher MRR (0.8840 vs 0.7000).
- The experiment demonstrates the potential value of preserving document structure during chunking.
- The result is specific to this policy document and the current 47 answerable evaluation cases.

---

## 10. Controlled Experiments

A key lesson from Day 13 is the importance of controlling variables during an experiment.

For the chunking experiment:

    Embedding model     → Same
    Retrieval method    → Same
    Golden set          → Same
    Evaluation metrics  → Same

The main variable changed was:

    Chunking strategy

This makes the comparison meaningful.

If both the chunking strategy and retrieval algorithm changed simultaneously, it would become difficult to determine what caused the difference.

---

## 11. Production Evaluation vs Ablation Evaluation

The production evaluator and the ablation experiments answer different questions.

### Production Evaluation

The production evaluator measures the current complete retrieval pipeline:

    Dense
      ↓
    BM25
      ↓
    RRF
      ↓
    Cross-Encoder Reranking
      ↓
    Top Results

It answers:

> How well does the current complete retrieval pipeline retrieve the expected evidence?

### Chunking Ablation

The chunking experiment uses dense retrieval consistently and changes the chunking strategy.

    Chunking Strategy
          ↓
    BGE Dense Retrieval
          ↓
        Top 20
          ↓
    Evaluate Top 5

It answers:

> How does the chunking strategy affect dense retrieval performance?

Therefore, the absolute metrics from the production evaluator and chunking ablation should not be treated as directly comparable results.

They represent different experiments.

---

## 12. Evaluation Interface Lesson

During the chunking experiment, the initial implementation passed retrieval results as wrappers containing both the chunk and its score.

However, the existing evaluate_case() function expects a list of plain chunk dictionaries.

The retrieval results therefore had to be converted into plain chunks before being passed to the evaluator.

Conceptually:

    Retrieved result
        ↓
    (chunk, score)
        ↓
    chunk
        ↓
    evaluate_case()

This reinforced an important engineering lesson:

> Evaluation code has a defined data contract, and experimental code must respect the same contract when reusing existing evaluation functions.

---

## Main Takeaways

### Retrieval

- Dense retrieval provides a semantic baseline.
- BM25 adds lexical matching.
- RRF combines independent retrieval rankings.
- Cross-encoder reranking provides a more expensive second-stage ranking step.
- Adding components can improve one metric while hurting another.
- Retrieval quality and retrieval latency should both be measured.

### Chunking

- Chunking is an important part of RAG retrieval quality.
- Structured documents can benefit from structure-aware chunking.
- Fixed-size chunking is simple but may break logical relationships.
- Chunking should be evaluated independently from retrieval components.

### Evaluation

- A golden set provides controlled questions and expected evidence.
- Hit@K measures whether the expected evidence appears within the top K.
- MRR measures how high the first relevant result appears.
- Ablation studies help identify which system components contribute to performance.
- Controlled experiments make it easier to attribute performance changes to a specific component.
- Results should always be interpreted within the context of the dataset and evaluation set.

---

## Day 13 Outcome

By the end of Day 13, I learned how to evaluate a RAG retrieval system scientifically rather than judging it only from individual query results.

I compared:

    Dense Retrieval
    Dense + BM25 + RRF
    Dense + BM25 + RRF + Reranking

and separately compared:

    Section-Aware Chunking
    vs
    Fixed-Size Chunking

The experiments provided measurable evidence about how retrieval components and chunking strategy affect retrieval quality.