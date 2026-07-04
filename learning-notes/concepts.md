# Core Concepts Reference

## RAG (Retrieval-Augmented Generation)

### Why it matters
- LLMs have knowledge cutoff and can hallucinate
- RAG grounds responses in retrieved documents
- Enables working with private/proprietary data

### Key steps
1. **Embedding**: Convert text to vectors
2. **Storage**: Store in vector database
3. **Retrieval**: Find top-K similar documents
4. **Generation**: Feed retrieved docs to LLM
5. **Response**: LLM generates answer grounded in retrieved context

### Common pitfalls
- Chunks too large → less precise retrieval
- Chunks too small → missing context
- No reranking → wrong documents used
- No source citation → unverifiable answers

---

## Embeddings

### What are they?
Numerical representations of text that capture semantic meaning.

### Key models
- `all-MiniLM-L6-v2`: Fast, 384-dim, good for most cases
- `all-mpnet-base-v2`: Better quality, slower, 768-dim
- Proprietary (OpenAI, Cohere): Expensive but best quality

### Distance metrics
- **Cosine similarity**: Most common, works well for text
- **Euclidean**: Works but not as good as cosine
- **Dot product**: Fast but needs normalized vectors

---

## Vector Databases

### Why not just SQL?
- SQL can't efficiently find "most similar" vectors in high dimensions
- Vector DBs use specialized indexing (HNSW, IVF)
- Return results in milliseconds, not seconds

### Options
- **Pinecone**: Fully managed, easy to use
- **Weaviate**: Open source, self-hosted
- **Milvus**: High performance, complex setup
- **Supabase pgvector**: Postgres-based, simple

---

Continue adding as you learn...
