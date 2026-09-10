# Day 1 — pgvector Setup + Embedding Model Upgrade

## 🎯 Goal

Set up PostgreSQL with pgvector locally and on Supabase, compare two embedding models for insurance document retrieval, choose an embedding model, and verify vector retrieval through SQL.

---

## 📚 What I Learned

### pgvector

**What it is:**

pgvector is a PostgreSQL extension that allows PostgreSQL to store and search vector embeddings.

**Why we use it:**

It allows the project to keep document content, metadata, and embeddings inside PostgreSQL instead of maintaining a separate vector database.

**How it works:**

After enabling the extension:

```sql
CREATE EXTENSION vector;
```

PostgreSQL can use vector columns such as:

```sql
embedding VECTOR(768)
```

---

### pgvector vs Pinecone

**Pinecone:**

```text
PostgreSQL → metadata/content
Pinecone   → vectors
```

**pgvector:**

```text
PostgreSQL
├── metadata/content
└── vectors
```

The key difference is that pgvector stores vectors directly inside PostgreSQL alongside the project's metadata and content.

---

### Embeddings

An embedding converts text into a numerical vector representing its semantic meaning.

For example:

```text
Insurance sentence
       ↓
Embedding model
       ↓
Vector
```

Similar text should produce vectors that are closer in vector space.

---

### all-MiniLM-L6-v2

* Embedding model tested during Day 1.
* Produces 384-dimensional embeddings.
* Tested against the insurance sentences using a flood-damage query.

---

### BAAI/bge-base-en-v1.5

* Embedding model tested during Day 1.
* Produces 768-dimensional embeddings.
* Produced a more useful ranking in our insurance retrieval experiment.
* Its 768 dimensions also match the project's `VECTOR(768)` schema.

---

### MTEB

MTEB (Massive Text Embedding Benchmark) was skimmed to understand how embedding models can be benchmarked and compared.

The project-specific comparison was still performed using our own insurance retrieval test.

---

### HNSW Index

HNSW was used as the vector index on the embedding column.

```text
embedding → HNSW → vector similarity search
```

---

### GIN Index

A GIN index was created for the `content` column for text search.

```text
content → GIN → text search
```

---

### Cosine Similarity

The embedding models were compared using cosine similarity.

For the SQL vector search, pgvector's cosine-distance operator was used:

```sql
<=>
```

A similarity-style score was calculated as:

```sql
1 - distance
```

Higher similarity means a more similar result.

---

## 🛠️ What I Built

* Created a Supabase PostgreSQL project.
* Created a local Docker PostgreSQL + pgvector database.
* Enabled pgvector on both databases.
* Created the `policygraph-hybrid-rag` Git repository.
* Created the required project folder structure.
* Created `docker-compose.yml` for the local PostgreSQL setup.
* Created the `document_chunks` table.
* Created an HNSW index on `embedding`.
* Created a GIN index on `content`.
* Stored 10 insurance test sentences in PostgreSQL.
* Generated BGE embeddings for the test sentences.
* Stored the embeddings in PostgreSQL.
* Queried the stored embeddings using SQL similarity search.
* Compared `all-MiniLM-L6-v2` and `BAAI/bge-base-en-v1.5`.
* Selected `BAAI/bge-base-en-v1.5` for the project.

---

## 💻 Important Code / Commands

### Enable pgvector

```sql
CREATE EXTENSION vector;
```

Enables the pgvector extension in PostgreSQL.

---

### Document chunks table

```sql
CREATE TABLE document_chunks (
    id BIGSERIAL PRIMARY KEY,
    document_name TEXT,
    section_number TEXT,
    section_title TEXT,
    page_number INTEGER,
    document_type TEXT,
    effective_date DATE,
    content TEXT,
    embedding VECTOR(768)
);
```

The `VECTOR(768)` column stores the 768-dimensional BGE embeddings.

---

### HNSW index

```sql
CREATE INDEX document_chunks_embedding_hnsw
ON document_chunks
USING hnsw (embedding vector_cosine_ops);
```

Creates the vector similarity search index.

---

### GIN index

```sql
CREATE INDEX document_chunks_content_gin
ON document_chunks
USING gin (to_tsvector('english', content));
```

Creates the text-search index for the content column.

---

### Verify stored embeddings

```sql
SELECT id, embedding IS NOT NULL AS has_embedding
FROM document_chunks;
```

All 10 test chunks returned `t`, confirming that embeddings were stored.

---

### Vector similarity query

```sql
SELECT
    id,
    content,
    1 - (embedding <=> '[QUERY_EMBEDDING]') AS similarity
FROM document_chunks
WHERE embedding IS NOT NULL
ORDER BY embedding <=> '[QUERY_EMBEDDING]'
LIMIT 5;
```

This retrieves the most similar chunks to the query embedding.

---

## 🧠 Key Technical Decisions

### Why pgvector instead of Pinecone?

* Vectors can be stored directly inside PostgreSQL.
* Metadata, content, and embeddings can live in the same database.
* SQL can be used with the stored document data and vectors.
* The project therefore does not need a separate vector database service for this setup.

---

### Why BGE instead of MiniLM?

Both models were tested against the same 10 insurance sentences using:

```text
Does the insurance policy cover damage caused by flooding?
```

Top results:

```text
MiniLM
0.8528 — Flood damage...
0.6439 — Flooding...
0.5877 — Intentional damage...

BGE
0.8542 — Flood damage...
0.7590 — Flooding...
0.6995 — Storm-related damage...
```

BGE produced a more useful ranking for this insurance retrieval test, particularly ranking the second flood-related sentence higher and pushing the unrelated intentional-damage sentence lower.

BGE also produces 768-dimensional embeddings, matching:

```sql
embedding VECTOR(768)
```

---

## ⚠️ Problems / Errors I Faced

No major issues encountered.

The Day 1 database setup, embedding storage, and SQL similarity retrieval were successfully completed.

---

## 🎤 Interview Questions

### Basic

**1. What is pgvector?**

pgvector is a PostgreSQL extension that allows PostgreSQL to store and search vector embeddings.

**2. What is an embedding?**

An embedding is a numerical vector representation of text that captures semantic information.

### Practical

**3. What embedding models did you compare?**

`all-MiniLM-L6-v2` and `BAAI/bge-base-en-v1.5`.

**4. What were their embedding dimensions?**

MiniLM produces 384-dimensional embeddings, while BGE-base produces 768-dimensional embeddings.

**5. How did you test the two embedding models?**

I encoded 10 insurance sentences with both models and compared their rankings for a flood-damage query using cosine similarity.

### Why / Trade-off

**6. Why did you choose BGE?**

BGE produced a more useful ranking for the insurance retrieval test and its 768-dimensional output matches the project's `VECTOR(768)` schema.

**7. What is the key difference between Pinecone and pgvector?**

Pinecone is a separate vector database/service, while pgvector stores vectors directly inside PostgreSQL alongside metadata and content.

### Project-specific

**8. What indexes did you create?**

An HNSW index was created on the embedding column for vector similarity search, and a GIN index was created on content for text search.

**9. How did you verify that vector retrieval was working?**

I stored the BGE embeddings in PostgreSQL and ran a SQL similarity query using pgvector's cosine-distance operator. The flood-related chunks were returned at the top.

---

## ⚡ Quick Revision

* **pgvector** → stores and searches vectors inside PostgreSQL.
* **Pinecone** → separate vector database/service.
* **Embedding** → numerical representation of text.
* **MiniLM** → 384-dimensional embeddings.
* **BGE-base** → 768-dimensional embeddings.
* **Chosen model** → `BAAI/bge-base-en-v1.5`.
* **HNSW** → vector similarity search index.
* **GIN** → text-search index.
* **`VECTOR(768)`** → PostgreSQL vector column for 768-dimensional embeddings.
* **`<=>`** → pgvector cosine-distance operator used in the SQL query.
* **Higher similarity** → more semantically similar result.

---

## ✅ Day 1 Checkpoint

* [x] Both DBs have pgvector working
* [x] Explain the one key Pinecone-vs-pgvector difference
* [x] BGE vs MiniLM compared, one chosen with a stated reason
* [x] Chunks retrievable via SQL

---

## 📌 One-Minute Interview Summary

Today I set up PostgreSQL with pgvector both locally using Docker and on Supabase. I created a `document_chunks` table containing insurance metadata, content, and 768-dimensional embeddings, along with HNSW and GIN indexes. I compared `all-MiniLM-L6-v2` and `BAAI/bge-base-en-v1.5` on an insurance flood-damage retrieval task and chose BGE because it produced a more useful ranking and matched the required 768-dimensional schema. Finally, I stored the BGE embeddings in PostgreSQL and verified that relevant chunks could be retrieved through SQL similarity search.
