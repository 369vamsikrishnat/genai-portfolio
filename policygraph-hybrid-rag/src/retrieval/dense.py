from __future__ import annotations

import os
from typing import Any

import psycopg2
from sentence_transformers import SentenceTransformer


# ============================================================
# Configuration
# ============================================================

EMBEDDING_MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL",
    "BAAI/bge-base-en-v1.5",
)

DEFAULT_DATABASE_URL = (
    "postgresql://postgres:postgres@"
    "localhost:5432/policygraph"
)


# ============================================================
# Embedding Model
# ============================================================

model = SentenceTransformer(
    EMBEDDING_MODEL_NAME
)


# ============================================================
# Database Connection
# ============================================================

def get_connection():
    """
    Create a PostgreSQL database connection.

    DATABASE_URL can be supplied through the environment.
    """

    database_url = os.getenv(
        "DATABASE_URL",
        DEFAULT_DATABASE_URL,
    )

    return psycopg2.connect(
        database_url
    )


# ============================================================
# Embeddings
# ============================================================

def embed_text(
    text: str,
) -> list[float]:
    """
    Generate a normalized embedding for one text.

    The configured BGE model produces 768-dimensional
    embeddings.
    """

    if not text or not text.strip():
        raise ValueError(
            "Text cannot be empty when generating an embedding."
        )

    embedding = model.encode(
        text,
        normalize_embeddings=True,
    )

    return embedding.tolist()


def embed_texts(
    texts: list[str],
    batch_size: int = 32,
) -> list[list[float]]:
    """
    Generate normalized embeddings for multiple texts.
    """

    if not texts:
        return []

    if batch_size <= 0:
        raise ValueError(
            "batch_size must be greater than 0."
        )

    cleaned_texts = [
        text.strip()
        for text in texts
    ]

    if any(not text for text in cleaned_texts):
        raise ValueError(
            "Embedding input contains empty text."
        )

    embeddings = model.encode(
        cleaned_texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    return embeddings.tolist()


def embedding_to_vector(
    embedding: list[float],
) -> str:
    """
    Convert a Python embedding list into pgvector format.
    """

    if not embedding:
        raise ValueError(
            "Embedding cannot be empty."
        )

    return "[" + ",".join(
        str(float(value))
        for value in embedding
    ) + "]"


# ============================================================
# Chunk Validation
# ============================================================

def _validate_chunks(
    chunks: list[dict[str, Any]],
) -> None:
    """
    Validate the structure of document chunks before
    performing embedding or database operations.
    """

    if not chunks:
        return

    for chunk in chunks:

        required_fields = (
            "chunk_id",
            "doc_name",
            "page_number",
            "content",
        )

        missing_fields = [
            field
            for field in required_fields
            if field not in chunk
            or chunk[field] is None
            or (
                isinstance(chunk[field], str)
                and not chunk[field].strip()
            )
        ]

        if missing_fields:
            raise ValueError(
                "Chunk is missing required fields: "
                + ", ".join(missing_fields)
            )

        page_number = chunk["page_number"]

        if not isinstance(
            page_number,
            int,
        ):
            raise ValueError(
                "Chunk page_number must be an integer."
            )

        if page_number <= 0:
            raise ValueError(
                "Chunk page_number must be greater than 0."
            )


# ============================================================
# Database Insert Helper
# ============================================================

def _insert_chunks(
    cursor,
    chunks: list[dict[str, Any]],
    embeddings: list[list[float]],
    document_type: str,
) -> None:
    """
    Insert or update chunks using an existing database cursor.

    This function does not commit or rollback.

    Transaction ownership belongs to the caller.
    """

    if len(embeddings) != len(chunks):
        raise RuntimeError(
            "Embedding count does not match chunk count."
        )

    for chunk, embedding in zip(
        chunks,
        embeddings,
    ):
        vector = embedding_to_vector(
            embedding
        )

        cursor.execute(
            """
            INSERT INTO document_chunks
            (
                chunk_id,
                document_name,
                section_number,
                section_title,
                page_number,
                document_type,
                content,
                extraction_method,
                prompt_injection,
                embedding
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s::vector
            )
            ON CONFLICT (chunk_id)
            DO UPDATE SET
                document_name = EXCLUDED.document_name,
                section_number = EXCLUDED.section_number,
                section_title = EXCLUDED.section_title,
                page_number = EXCLUDED.page_number,
                document_type = EXCLUDED.document_type,
                content = EXCLUDED.content,
                extraction_method = EXCLUDED.extraction_method,
                prompt_injection = EXCLUDED.prompt_injection,
                embedding = EXCLUDED.embedding
            """,
            (
                chunk["chunk_id"],
                chunk["doc_name"],
                chunk.get("section_number"),
                chunk.get("section_title"),
                chunk["page_number"],
                document_type,
                chunk["content"],
                chunk.get(
                    "extraction_method",
                    "text",
                ),
                bool(
                    chunk.get(
                        "prompt_injection",
                        False,
                    )
                ),
                vector,
            ),
        )


# ============================================================
# Chunk Storage
# ============================================================

def store_chunks(
    chunks: list[dict[str, Any]],
    document_type: str = "insurance",
) -> int:
    """
    Generate embeddings and store document chunks
    in PostgreSQL.

    Existing chunks with the same chunk_id are updated
    instead of duplicated.

    This function performs an upsert operation.

    It does NOT remove stale chunks belonging to an
    existing document.

    For replacing an entire document, use
    replace_document_chunks() instead.

    Returns:
        Number of chunks processed.
    """

    if not chunks:
        return 0

    _validate_chunks(
        chunks
    )

    contents = [
        chunk["content"]
        for chunk in chunks
    ]

    embeddings = embed_texts(
        contents
    )

    if len(embeddings) != len(chunks):
        raise RuntimeError(
            "Embedding count does not match chunk count."
        )

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            _insert_chunks(
                cursor=cursor,
                chunks=chunks,
                embeddings=embeddings,
                document_type=document_type,
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

    return len(chunks)


# ============================================================
# Atomic Document Replacement
# ============================================================

def replace_document_chunks(
    document_name: str,
    chunks: list[dict[str, Any]],
    document_type: str = "insurance",
) -> int:
    """
    Atomically replace all chunks belonging to one document.

    Transaction:

        BEGIN
          ↓
        DELETE existing document chunks
          ↓
        Generate embeddings
          ↓
        INSERT new chunks
          ↓
        COMMIT

    If any operation fails:

        ROLLBACK

    The previous version of the document therefore remains
    intact if the replacement fails.

    This is the preferred function for document ingestion.

    Returns:
        Number of newly stored chunks.
    """

    if not document_name or not document_name.strip():
        raise ValueError(
            "document_name cannot be empty."
        )

    if not chunks:
        raise ValueError(
            "Cannot replace document with zero chunks."
        )

    _validate_chunks(
        chunks
    )

    # --------------------------------------------------------
    # Make sure every chunk belongs to the document being
    # replaced.
    # --------------------------------------------------------

    mismatched_chunks = [
        chunk["doc_name"]
        for chunk in chunks
        if chunk["doc_name"] != document_name
    ]

    if mismatched_chunks:
        raise ValueError(
            "All chunks must belong to the document being "
            "replaced."
        )

    # --------------------------------------------------------
    # Generate embeddings before modifying the database.
    #
    # This is intentional.
    #
    # If embedding generation fails, the existing database
    # contents have not been touched yet.
    # --------------------------------------------------------

    contents = [
        chunk["content"]
        for chunk in chunks
    ]

    embeddings = embed_texts(
        contents
    )

    if len(embeddings) != len(chunks):
        raise RuntimeError(
            "Embedding count does not match chunk count."
        )

    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            # ------------------------------------------------
            # Delete the complete previous version.
            # ------------------------------------------------

            cursor.execute(
                """
                DELETE FROM document_chunks
                WHERE document_name = %s;
                """,
                (
                    document_name,
                ),
            )

            # ------------------------------------------------
            # Insert the complete new version.
            # ------------------------------------------------

            _insert_chunks(
                cursor=cursor,
                chunks=chunks,
                embeddings=embeddings,
                document_type=document_type,
            )

        # ----------------------------------------------------
        # Both DELETE and INSERT become visible together.
        # ----------------------------------------------------

        connection.commit()

    except Exception:
        # ----------------------------------------------------
        # If DELETE or INSERT failed, restore the previous
        # database state.
        # ----------------------------------------------------

        connection.rollback()
        raise

    finally:
        connection.close()

    return len(chunks)


# ============================================================
# Load Retrieval Corpus
# ============================================================

def load_all_chunks(
    include_prompt_injection: bool = False,
) -> list[dict[str, Any]]:
    """
    Load all stored document chunks from PostgreSQL.

    This is used to build the BM25 corpus.

    By default, chunks flagged as prompt injection are
    excluded from the retrieval corpus.
    """

    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            if include_prompt_injection:
                cursor.execute(
                    """
                    SELECT
                        id,
                        chunk_id,
                        document_name,
                        section_number,
                        section_title,
                        page_number,
                        document_type,
                        content,
                        extraction_method,
                        prompt_injection
                    FROM document_chunks
                    ORDER BY id;
                    """
                )

            else:
                cursor.execute(
                    """
                    SELECT
                        id,
                        chunk_id,
                        document_name,
                        section_number,
                        section_title,
                        page_number,
                        document_type,
                        content,
                        extraction_method,
                        prompt_injection
                    FROM document_chunks
                    WHERE prompt_injection = FALSE
                    ORDER BY id;
                    """
                )

            rows = cursor.fetchall()

    finally:
        connection.close()

    chunks = []

    for row in rows:

        (
            database_id,
            chunk_id,
            document_name,
            section_number,
            section_title,
            page_number,
            document_type,
            content,
            extraction_method,
            prompt_injection,
        ) = row

        chunks.append(
            {
                "id": database_id,
                "chunk_id": chunk_id,
                "doc_name": document_name,
                "section_number": section_number,
                "section_title": section_title,
                "page_number": page_number,
                "document_type": document_type,
                "content": content,
                "extraction_method": extraction_method,
                "prompt_injection": prompt_injection,
            }
        )

    return chunks


# ============================================================
# Dense Retrieval
# ============================================================

def dense_search(
    query: str,
    top_k: int = 10,
    include_prompt_injection: bool = False,
) -> list[tuple[dict[str, Any], float]]:
    """
    Perform dense semantic retrieval using:

        BGE embeddings
            ↓
        PostgreSQL
            ↓
        pgvector cosine distance

    Returns:

        [
            (
                chunk,
                similarity_score
            )
        ]
    """

    if not query or not query.strip():
        return []

    if top_k <= 0:
        raise ValueError(
            "top_k must be greater than 0."
        )

    query_embedding = embed_text(
        query
    )

    query_vector = embedding_to_vector(
        query_embedding
    )

    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            if include_prompt_injection:
                cursor.execute(
                    """
                    SELECT
                        id,
                        chunk_id,
                        document_name,
                        section_number,
                        section_title,
                        page_number,
                        document_type,
                        content,
                        extraction_method,
                        prompt_injection,
                        1 - (
                            embedding <=> %s::vector
                        ) AS similarity
                    FROM document_chunks
                    WHERE embedding IS NOT NULL
                    ORDER BY
                        embedding <=> %s::vector
                    LIMIT %s;
                    """,
                    (
                        query_vector,
                        query_vector,
                        top_k,
                    ),
                )

            else:
                cursor.execute(
                    """
                    SELECT
                        id,
                        chunk_id,
                        document_name,
                        section_number,
                        section_title,
                        page_number,
                        document_type,
                        content,
                        extraction_method,
                        prompt_injection,
                        1 - (
                            embedding <=> %s::vector
                        ) AS similarity
                    FROM document_chunks
                    WHERE
                        embedding IS NOT NULL
                        AND prompt_injection = FALSE
                    ORDER BY
                        embedding <=> %s::vector
                    LIMIT %s;
                    """,
                    (
                        query_vector,
                        query_vector,
                        top_k,
                    ),
                )

            rows = cursor.fetchall()

    finally:
        connection.close()

    results = []

    for row in rows:

        (
            database_id,
            chunk_id,
            document_name,
            section_number,
            section_title,
            page_number,
            document_type,
            content,
            extraction_method,
            prompt_injection,
            similarity,
        ) = row

        chunk = {
            "id": database_id,
            "chunk_id": chunk_id,
            "doc_name": document_name,
            "section_number": section_number,
            "section_title": section_title,
            "page_number": page_number,
            "document_type": document_type,
            "content": content,
            "extraction_method": extraction_method,
            "prompt_injection": prompt_injection,
        }

        results.append(
            (
                chunk,
                float(similarity),
            )
        )

    return results