-- ============================================================
-- PolicyGraph Hybrid RAG - Database Schema
-- PostgreSQL 17 + pgvector
-- ============================================================


-- ============================================================
-- 1. Extensions
-- ============================================================

CREATE EXTENSION IF NOT EXISTS vector;


-- ============================================================
-- 2. Document Chunks
-- ============================================================

CREATE TABLE IF NOT EXISTS document_chunks (

    -- Internal database identifier
    id BIGSERIAL PRIMARY KEY,

    -- Stable application-level chunk identity
    chunk_id TEXT NOT NULL UNIQUE,

    -- Source document metadata
    document_name TEXT NOT NULL,
    document_type TEXT NOT NULL DEFAULT 'insurance',
    effective_date DATE,

    -- Policy structure
    section_number TEXT,
    section_title TEXT,

    -- Source location
    page_number INTEGER NOT NULL,

    -- Extracted chunk text
    content TEXT NOT NULL,

    -- Extraction metadata
    extraction_method TEXT NOT NULL DEFAULT 'text',

    -- Security signal generated during ingestion
    prompt_injection BOOLEAN NOT NULL DEFAULT FALSE,

    -- Dense embedding
    embedding VECTOR(768),

    -- Record creation timestamp
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Basic data validation
    CONSTRAINT document_chunks_page_number_positive
        CHECK (page_number > 0),

    CONSTRAINT document_chunks_extraction_method_valid
        CHECK (
            extraction_method IN ('text', 'ocr')
        )
);


-- ============================================================
-- 3. Vector Similarity Index
-- ============================================================

CREATE INDEX IF NOT EXISTS document_chunks_embedding_hnsw
ON document_chunks
USING hnsw (embedding vector_cosine_ops);


-- ============================================================
-- 4. Full-Text Search Index
-- ============================================================

CREATE INDEX IF NOT EXISTS document_chunks_content_gin
ON document_chunks
USING gin (
    to_tsvector('english', content)
);


-- ============================================================
-- 5. Retrieval / Filtering Indexes
-- ============================================================

CREATE INDEX IF NOT EXISTS document_chunks_document_name_idx
ON document_chunks (document_name);


CREATE INDEX IF NOT EXISTS document_chunks_document_type_idx
ON document_chunks (document_type);


CREATE INDEX IF NOT EXISTS document_chunks_page_number_idx
ON document_chunks (page_number);


CREATE INDEX IF NOT EXISTS document_chunks_prompt_injection_idx
ON document_chunks (prompt_injection);


-- ============================================================
-- 6. Useful Composite Index
-- ============================================================

CREATE INDEX IF NOT EXISTS document_chunks_document_page_idx
ON document_chunks (
    document_name,
    page_number
);