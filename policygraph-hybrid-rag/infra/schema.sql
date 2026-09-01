-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;


-- Document chunks table
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


-- HNSW index for vector similarity search
CREATE INDEX document_chunks_embedding_hnsw
ON document_chunks
USING hnsw (embedding vector_cosine_ops);


-- GIN index for text search
CREATE INDEX document_chunks_content_gin
ON document_chunks
USING gin (to_tsvector('english', content));
