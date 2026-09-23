# Architecture Decisions

## ADR-01: Why pgvector

### Context
Policy and compliance content is dense, long-form, and often contains repeated concepts across sections. We need retrieval that is precise enough for policy answers while still supporting semantic matching across wording differences.

### Decision
We use pgvector as the vector store for the hybrid retrieval pipeline.

### Why
- It keeps retrieval state close to the application data model instead of depending on a separate vector-only service.
- It fits naturally with Postgres-backed workflows and operational simplicity.
- It supports similarity search without forcing a large architecture change for a research project.
- It makes experimentation with metadata filtering and policy-aware retrieval easier.

### Trade-offs
- We accept a little less flexibility than a dedicated vector database optimized for very large-scale similarity workloads.
- Postgres-based vector search is easier to operate and reason about, but it is not the absolute fastest option at extreme scale.

### Alternatives considered
- Pinecone / Qdrant / FAISS: stronger pure vector-DB specialization, but more operational overhead and less alignment with the project’s existing database-first architecture.
- Keeping everything in application memory: simpler for demos, but not realistic for persistent retrieval or multi-user use.

### Consequence
We gain a practical, low-friction vector store for semantic lookup while staying within a familiar database stack.

---

## ADR-02: Why BGE


### Context
The retrieval layer must understand policy language well enough to bridge paraphrases, legal phrasing, and policy-specific terminology without overfitting to a narrow domain.

### Decision
We use BGE embeddings as the default dense embedding model.

### Why
- BGE is strong on retrieval quality across general and domain-adjacent tasks.
- It balances semantic recall with manageable runtime cost.
- It works well with hybrid retrieval patterns where dense candidates are combined with lexical retrieval.
- It is a pragmatic choice for a portfolio project: high enough quality to show the pattern, without requiring a custom embedding pipeline.

### Trade-offs
- We are choosing a strong general-purpose embedding model over a fully specialized legal embedding stack.
- The model is likely good enough for policy retrieval, but domain-specific tuning would require more data and iteration.

### Alternatives considered
- Domain-tuned legal embeddings: potentially better on narrow compliance tasks, but more expensive to build and harder to justify for a prototype project.
- Small or ultra-fast embedding models: cheaper and faster, but weaker on nuanced policy paraphrases and retrieval recall.

### Consequence
We prioritize robust retrieval quality and speed over building a bespoke embedding model from scratch.

---

## ADR-03: Why section-chunking



### Context
Policies are structured documents, not plain prose. Splitting on arbitrary fixed-size chunks breaks document meaning and often separates related obligations, definitions, and exceptions.

### Decision
We chunk documents by logical sections instead of using naive fixed-length segmentation.

### Why
- Policy questions usually depend on the local section context, not a random token window.
- Section-aware chunks preserve headings, rules, exemptions, and scope.
- They improve retrieval precision for questions like “what is the policy for contractors?” or “when does this exception apply?”
- They reduce the chance of retrieving a misleading fragment from the middle of a policy chapter.

### Trade-offs
- Section-aware chunking is more work than fixed-size splitting and requires some document-structure awareness.
- It can produce uneven chunk lengths depending on section complexity and formatting.

### Alternatives considered
- Fixed-length chunks: simpler to implement, but much worse at preserving policy semantics and clause boundaries.
- Whole-document retrieval: easy to reason about, but too broad and noisy for precise policy answers.

### Consequence
Retrieval is more faithful to document structure, which is especially important for compliance and policy reasoning.

---

## ADR-04: Why RRF


### Context
Lexical and dense retrieval each have different strengths: BM25 is strong on exact terms, while embeddings are better on semantic similarity. Using only one side creates blind spots.

### Decision
We combine retrieval results with Reciprocal Rank Fusion (RRF).

### Why
- RRF is simple, robust, and effective for hybrid search.
- It rewards results that rank highly in either retrieval system without requiring fragile score normalization.
- It reduces the risk of one retrieval method dominating the other.
- It is a strong fit for policy QA where exact terminology and semantic paraphrase both matter.

### Trade-offs
- RRF is less explicit than learned fusion models and does not optimize for a particular score distribution.
- It is a strong default, but it is not the only valid way to combine retrieval signals.

### Alternatives considered
- Weighted score blending: more flexible, but much more sensitive to calibration and tuning.
- Dense-only retrieval: simpler, but worse on exact terminology and policy-specific wording.
- Sparse-only retrieval: easier to explain, but poor at semantic paraphrase and conceptual matching.

### Consequence
The final candidate set is more stable and useful than either sparse or dense retrieval alone.

---

## Summary
These decisions reflect a practical goal: make policy retrieval more faithful to the actual document structure and the way users phrase questions, while keeping the system understandable and maintainable.
