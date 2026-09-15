from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import psycopg2
from dotenv import load_dotenv
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Request,
    Security,
)
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.api.cost_tracker import CostTracker
from src.ingestion.chunker import section_aware_split
from src.ingestion.ocr import load_document_pages
from src.pipeline import (
    refresh_bm25_index,
    run_pipeline,
)
from src.retrieval.dense import (
    replace_document_chunks,
)

load_dotenv()


# ============================================================
# Configuration
# ============================================================

APP_TITLE = "PolicyGraph Hybrid RAG API"

DATA_DIR = Path(
    os.getenv(
        "DATA_DIR",
        "data",
    )
).resolve()

MAX_QUESTION_LENGTH = int(
    os.getenv(
        "MAX_QUESTION_LENGTH",
        "2000",
    )
)

MAX_SOURCE_LENGTH = int(
    os.getenv(
        "MAX_SOURCE_LENGTH",
        "255",
    )
)

API_KEY = os.getenv("API_KEY")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    (
        "postgresql://postgres:postgres@"
        "localhost:5432/policygraph"
    ),
)


# ============================================================
# FastAPI application
# ============================================================

app = FastAPI(
    title=APP_TITLE,
    version="1.0.0",
)


# ============================================================
# Rate limiting
# ============================================================

limiter = Limiter(
    key_func=get_remote_address,
)

app.state.limiter = limiter

app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler,
)


# ============================================================
# Authentication
# ============================================================

api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
)


def verify_api_key(
    api_key: str | None = Security(
        api_key_header
    ),
) -> str:
    """
    Validate the API key supplied by the client.
    """

    if not API_KEY:
        raise HTTPException(
            status_code=500,
            detail=(
                "API_KEY is not configured on the server."
            ),
        )

    if not api_key or api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key.",
        )

    return api_key


# ============================================================
# Request models
# ============================================================

class QueryRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=MAX_QUESTION_LENGTH,
    )


class IngestRequest(BaseModel):
    source: str = Field(
        min_length=1,
        max_length=MAX_SOURCE_LENGTH,
    )


# ============================================================
# Cost tracking
# ============================================================

tracker = CostTracker()


# ============================================================
# Database helpers
# ============================================================

def get_database_connection():
    """
    Create a PostgreSQL connection using DATABASE_URL.
    """

    return psycopg2.connect(
        DATABASE_URL
    )


def check_database_connection() -> bool:
    """
    Check whether PostgreSQL is reachable.
    """

    connection = None

    try:
        connection = get_database_connection()

        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            cursor.fetchone()

        return True

    except Exception:
        return False

    finally:
        if connection is not None:
            connection.close()


# ============================================================
# Ingestion source validation
# ============================================================

def resolve_ingestion_source(
    source: str,
) -> Path:
    """
    Resolve and validate a document path.

    Relative paths are resolved inside DATA_DIR.

    Absolute paths are also allowed only when they resolve
    inside DATA_DIR.

    This prevents the API from being used to ingest arbitrary
    files from the server filesystem.
    """

    source = source.strip()

    if not source:
        raise HTTPException(
            status_code=400,
            detail="Source cannot be empty.",
        )

    requested_path = Path(source)

    if requested_path.is_absolute():
        candidate = requested_path.resolve()
    else:
        candidate = (
            DATA_DIR / requested_path
        ).resolve()

    try:
        candidate.relative_to(
            DATA_DIR
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid source path. "
                "Documents must be inside the configured "
                "data directory."
            ),
        ) from error

    if not candidate.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"Document not found: {source}"
            ),
        )

    if not candidate.is_file():
        raise HTTPException(
            status_code=400,
            detail=(
                "The ingestion source must be a file."
            ),
        )

    if candidate.suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=400,
            detail=(
                "Only PDF documents are currently supported."
            ),
        )

    return candidate


# ============================================================
# Document ingestion
# ============================================================

def ingest_document(
    source: Path,
) -> dict[str, Any]:
    """
    Extract, chunk, embed, and store one document.

    Database replacement is handled atomically by
    replace_document_chunks().
    """

    document_name = source.name

    # --------------------------------------------------------
    # 1. Extract pages
    # --------------------------------------------------------

    pages = load_document_pages(
        source
    )

    if not pages:
        raise ValueError(
            "No text could be extracted from the document."
        )

    # --------------------------------------------------------
    # 2. Create structure-aware chunks
    # --------------------------------------------------------

    chunks = section_aware_split(
        pages,
        document_name,
    )

    if not chunks:
        raise ValueError(
            "Document extraction succeeded, "
            "but no chunks were created."
        )

    # --------------------------------------------------------
    # 3. Atomically replace the document in PostgreSQL
    # --------------------------------------------------------

    stored_chunks = replace_document_chunks(
        document_name=document_name,
        chunks=chunks,
        document_type="insurance",
    )

    # --------------------------------------------------------
    # 4. Refresh BM25 after database update
    # --------------------------------------------------------

    refresh_bm25_index()

    # --------------------------------------------------------
    # 5. Build extraction statistics
    # --------------------------------------------------------

    extraction_methods: dict[str, int] = {}

    for page in pages:
        method = page.get(
            "extraction_method",
            "unknown",
        )

        extraction_methods[method] = (
            extraction_methods.get(
                method,
                0,
            )
            + 1
        )

    # --------------------------------------------------------
    # 6. Return ingestion result
    # --------------------------------------------------------

    return {
        "document": document_name,
        "pages_processed": len(pages),
        "chunks_created": stored_chunks,
        "extraction_methods": extraction_methods,
        "status": "completed",
    }


# ============================================================
# Health endpoint
# ============================================================

@app.get("/health")
def health():
    """
    Liveness/readiness check for the API and PostgreSQL.
    """

    database_healthy = (
        check_database_connection()
    )

    if not database_healthy:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "database": "unavailable",
            },
        )

    return {
        "status": "ok",
        "database": "ok",
    }


# ============================================================
# Protected endpoint
# ============================================================

@app.get(
    "/protected",
    dependencies=[
        Depends(verify_api_key)
    ],
)
@limiter.limit("30/minute")
def protected(
    request: Request,
):
    """
    Simple endpoint used to verify API authentication.
    """

    return {
        "message": "Authenticated successfully",
    }


# ============================================================
# Query endpoint
# ============================================================

@app.post(
    "/query",
    dependencies=[
        Depends(verify_api_key)
    ],
)
@limiter.limit("30/minute")
def query(
    request: Request,
    body: QueryRequest,
):
    """
    Execute the complete Hybrid RAG pipeline.
    """

    question = body.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty.",
        )

    try:
        (
            answer,
            reranked_results,
            timings,
            usage_metadata,
            _,
        ) = run_pipeline(
            question,
            tracker=tracker,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except RuntimeError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "An unexpected error occurred "
                "while processing the query."
            ),
        ) from error

    # --------------------------------------------------------
    # Token usage
    # --------------------------------------------------------

    usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "thinking_tokens": 0,
        "total_tokens": 0,
    }

    query_cost = 0.0

    if usage_metadata is not None:
        input_tokens = getattr(
            usage_metadata,
            "prompt_token_count",
            0,
        ) or 0

        output_tokens = getattr(
            usage_metadata,
            "candidates_token_count",
            0,
        ) or 0

        thinking_tokens = getattr(
            usage_metadata,
            "thoughts_token_count",
            0,
        ) or 0

        total_tokens = getattr(
            usage_metadata,
            "total_token_count",
            0,
        ) or 0

        usage = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "thinking_tokens": thinking_tokens,
            "total_tokens": total_tokens,
        }

        query_cost = tracker.calculate_cost(
            input_tokens=input_tokens,
            output_tokens=(
                output_tokens
                + thinking_tokens
            ),
        )

    # --------------------------------------------------------
    # Citation metadata
    # --------------------------------------------------------

    citations = []

    for chunk, score in reranked_results:
        citations.append(
            {
                "document": chunk.get(
                    "doc_name"
                ),
                "page": chunk.get(
                    "page_number"
                ),
                "section": chunk.get(
                    "section_number"
                ),
                "section_title": chunk.get(
                    "section_title"
                ),
                "content": chunk.get(
                    "content"
                ),
                "score": float(score),
            }
        )

    # --------------------------------------------------------
    # API response
    # --------------------------------------------------------

    return {
        "question": question,
        "answer": answer,
        "citations": citations,
        "timings": timings,
        "usage": usage,
        "cost": {
            "query_cost": query_cost,
        },
    }


# ============================================================
# Ingestion endpoint
# ============================================================

@app.post(
    "/ingest",
    dependencies=[
        Depends(verify_api_key)
    ],
)
@limiter.limit("10/minute")
def ingest(
    request: Request,
    body: IngestRequest,
):
    """
    Ingest a PDF document into PostgreSQL + pgvector.
    """

    source = resolve_ingestion_source(
        body.source
    )

    try:
        result = ingest_document(
            source
        )

        return result

    except HTTPException:
        raise

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Document ingestion failed.",
        ) from error


# ============================================================
# Metrics endpoint
# ============================================================

@app.get(
    "/metrics",
    dependencies=[
        Depends(verify_api_key)
    ],
)
@limiter.limit("30/minute")
def metrics(
    request: Request,
):
    """
    Return process-local query and cost metrics.
    """

    return {
        "total_queries": (
            tracker.total_queries
        ),
        "total_input_tokens": (
            tracker.total_input_tokens
        ),
        "total_output_tokens": (
            tracker.total_output_tokens
        ),
        "total_cost": (
            tracker.total_cost
        ),
        "average_cost_per_query": (
            tracker.average_cost_per_query()
        ),
    }