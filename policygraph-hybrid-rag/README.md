# PolicyGraph

One-line tagline: hybrid-retrieval insurance document intelligence engine

## The Problem

Naive RAG breaks down on legal and insurance documents because the content is long, highly structured, and full of exceptions, definitions, and cross-references that are easy to misread when retrieval is based only on keyword overlap or a single coarse chunk. In this setting, citation-grounding is not optional: users need to know which clause, policy section, or page actually supports the answer, not just a fluent but unsupported summary.

## Architecture

```mermaid
flowchart LR
    A[User Query] --> B[Embed Query]
    B --> C[Dense Search<br/>pgvector]
    A --> D[BM25 Search<br/>keyword]
    C --> E[Reciprocal Rank Fusion]
    D --> E
    E --> F[Cross-Encoder Reranker]
    F --> G[Citation-Grounded Generation]
    H[PDF / Scanned Docs] --> I[OCR + Section-Aware Chunking]
    I --> J[Vector Store<br/>pgvector]
    J --> C
    I --> K[BM25 Index]
    K --> D
    G --> L[Answer + Sources + Confidence]

    style A fill:#f0f0eb,stroke:#d9d6d5
    style B fill:#f0f0eb,stroke:#d9d6d5
    style C fill:#f0f0eb,stroke:#d9d6d5
    style D fill:#f0f0eb,stroke:#d9d6d5
    style E fill:#f0f0eb,stroke:#d9d6d5
    style F fill:#f0f0eb,stroke:#d9d6d5
    style G fill:#f0f0eb,stroke:#d9d6d5
    style H fill:#f0f0eb,stroke:#d9d6d5
    style I fill:#f0f0eb,stroke:#d9d6d5
    style J fill:#f0f0eb,stroke:#d9d6d5
    style K fill:#f0f0eb,stroke:#d9d6d5
    style L fill:#f0f0eb,stroke:#d9d6d5
```

The pipeline moves left to right: a user asks a policy question, the query is embedded and compared against dense and lexical retrieval indexes, those candidates are combined through Reciprocal Rank Fusion, reranked for precision, and then passed to a citation-grounded generation step that returns the answer with supporting sources and confidence. On the ingestion side, PDFs and scans are OCR’d and section-aware chunked before being indexed in pgvector and BM25 so the retrieval stage can reason over the actual structure of policy documents instead of random text windows.

## Results (real, from your audit)

| Configuration | Recall@5 | Hit@1 | MRR |
|---|---:|---:|---:|
| Dense only | 0.766 | 0.596 | 0.677 |
| + BM25 (hybrid) | 0.809 | 0.638 | 0.713 |
| + Reranking | 0.745 | 0.745 | 0.745 |
| Section-aware chunking | 0.957 | 0.83 | — |

Reranking improves the top answer quality (Hit@1 rises), but it narrows the candidate pool enough that Recall@5 falls — the classic precision-vs-recall trade-off in policy retrieval.

## Tech Stack

| Component | Tool | Why |
|---|---|---|
| Document ingestion | PDF/OCR pipeline | Converts scanned and mixed-format insurance documents into readable text before retrieval. |
| Vector search | pgvector | Supports semantic retrieval with low operational overhead and easy metadata filtering. See [docs/decisions.md](docs/decisions.md). |
| Dense embeddings | BGE | Strong retrieval quality for semantic matching across paraphrased policy language. See [docs/decisions.md](docs/decisions.md). |
| Lexical retrieval | BM25 | Finds exact term matches and policy-specific phrases that dense embeddings may miss. |
| Hybrid fusion | RRF | Combines sparse and dense rankings without brittle score normalization. See [docs/decisions.md](docs/decisions.md). |
| Reranking | Cross-encoder reranker | Improves top-result precision, especially when the answer needs a single authoritative clause. |
| Generation | Gemini models | Produces grounded answers while staying fast and cost-aware. |
| API layer | FastAPI | Exposes a clean, testable endpoint for the retrieval and generation workflow. |
| Cache | Redis | Reuses semantically similar answers to reduce redundant LLM work and cost. |
| Observability | Langfuse | Tracks prompt quality, usage, and debugging signals across retrieval and generation. |

## How to Run

1. Copy your environment variables into a local `.env` file. The app expects values such as:

```bash
API_KEY=your-api-key
GEMINI_API_KEY=your-gemini-key
LANGFUSE_PUBLIC_KEY=your-langfuse-public-key
LANGFUSE_SECRET_KEY=your-langfuse-secret-key
LANGFUSE_BASE_URL=https://cloud.langfuse.com
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/policygraph
REDIS_URL=redis://localhost:6379
CACHE_SIMILARITY_THRESHOLD=0.95
CACHE_TTL_SECONDS=86400
```

2. Start the stack:

```bash
docker-compose up --build
```

3. The API will be available at:

- API: `http://localhost:8000`
- UI: `http://localhost:8501`
- Swagger docs: `http://localhost:8000/docs`

4. Hit the query endpoint:

```bash
curl -X POST http://localhost:8000/query \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"question":"What coverage applies to water damage?"}'
```

## Live Demo

[Cloud Run URL] · [90-second Loom link]

## API Reference

See the FastAPI auto-generated docs at `http://localhost:8000/docs` when the service is running. This README intentionally does not duplicate the full endpoint schema.

## Known Limitations

- OCR quality degrades on low-resolution or heavily skewed scans, which can reduce retrieval recall for older documents.
- Section-aware chunking improves precision, but it is still sensitive to malformed document structure or inconsistent policy formatting.
- Hybrid retrieval is stronger than single-method retrieval, but edge-case legal phrasing can still confuse exact-match and similarity ranking.
- The current stack is designed for a single deployment pattern and is not yet hardened for multi-tenant enterprise policy governance.

## What's Next

1. Add policy graph linking so the system can trace definitions, exceptions, and cross-references across multiple documents instead of only retrieving local chunks.
2. Add a human-review loop for low-confidence citations and OCR-flagged pages to improve trust and ground-truth quality.
3. Add version-aware policy indexing so the system can answer questions against the correct policy edition and avoid stale interpretations.

## Related Decisions

See [docs/decisions.md](docs/decisions.md) for the reasoning behind the key architectural choices: pgvector, BGE embeddings, section-aware chunking, and RRF.
