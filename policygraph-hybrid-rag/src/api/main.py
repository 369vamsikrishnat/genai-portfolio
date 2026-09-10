import os
import uuid

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    HTTPException,
    Security,
    Request
)

from fastapi.security import APIKeyHeader

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from pydantic import BaseModel

from src.pipeline import run_pipeline
from src.api.cost_tracker import CostTracker


app = FastAPI(
    title="PolicyGraph Hybrid RAG API"
)


# --------------------------------------------------
# Rate limiting
# --------------------------------------------------

limiter = Limiter(
    key_func=get_remote_address
)

app.state.limiter = limiter

app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler
)


# --------------------------------------------------
# API key authentication
# --------------------------------------------------

API_KEY = os.getenv("API_KEY")

api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False
)


def verify_api_key(
    api_key: str = Security(api_key_header)
):
    if not API_KEY or api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key"
        )

    return api_key


# --------------------------------------------------
# Shared cost tracker
# --------------------------------------------------

tracker = CostTracker()


# --------------------------------------------------
# Background jobs
# --------------------------------------------------

jobs = {}


def run_ingestion_job(job_id: str, source: str):
    """
    Run document loading and chunking in the background.
    """

    jobs[job_id]["status"] = "running"

    try:
        from src.ingestion.ocr import load_document
        from src.ingestion.chunker import section_aware_split

        text = load_document(source)

        chunks = section_aware_split(
            text,
            source
        )

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["chunks"] = len(chunks)

    except Exception as error:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(error)


# --------------------------------------------------
# Request models
# --------------------------------------------------

class QueryRequest(BaseModel):
    question: str


class IngestRequest(BaseModel):
    source: str


# --------------------------------------------------
# Health check
# --------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "ok"
    }


# --------------------------------------------------
# Protected test endpoint
# --------------------------------------------------

@app.get(
    "/protected",
    dependencies=[Depends(verify_api_key)]
)
@limiter.limit("30/minute")
def protected(request: Request):
    return {
        "message": "Authenticated successfully"
    }


# --------------------------------------------------
# Query endpoint
# --------------------------------------------------

@app.post(
    "/query",
    dependencies=[Depends(verify_api_key)]
)
@limiter.limit("30/minute")
def query(
    request: Request,
    body: QueryRequest
):

    answer, reranked_results, timings, usage_metadata, _ = (
        run_pipeline(
            body.question,
            tracker=tracker
        )
    )

    return {
        "question": body.question,

        "answer": answer,

        "citations": [
            {
                "content": chunk["content"],
                "score": float(score)
            }
            for chunk, score in reranked_results
        ],

        "timings": timings,

        "usage": {
            "input_tokens": usage_metadata.prompt_token_count,
            "output_tokens": usage_metadata.candidates_token_count,
            "thinking_tokens": usage_metadata.thoughts_token_count,
            "total_tokens": usage_metadata.total_token_count
        },

        "cost": {
            "query_cost": tracker.calculate_cost(
                usage_metadata.prompt_token_count,
                (
                    usage_metadata.candidates_token_count
                    + usage_metadata.thoughts_token_count
                )
            )
        }
    }


# --------------------------------------------------
# Ingestion endpoint
# --------------------------------------------------

@app.post(
    "/ingest",
    dependencies=[Depends(verify_api_key)]
)
@limiter.limit("30/minute")
def ingest(
    request: Request,
    body: IngestRequest,
    background_tasks: BackgroundTasks
):

    job_id = str(uuid.uuid4())

    jobs[job_id] = {
        "status": "queued",
        "source": body.source
    }

    background_tasks.add_task(
    run_ingestion_job,
    job_id,
    body.source
    )

    return {
        "job_id": job_id,
        "status": "queued"
    }


# --------------------------------------------------
# Job status endpoint
# --------------------------------------------------

@app.get(
    "/job/{job_id}",
    dependencies=[Depends(verify_api_key)]
)
@limiter.limit("30/minute")
def job_status(
    request: Request,
    job_id: str
):

    if job_id not in jobs:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    return jobs[job_id]


# --------------------------------------------------
# Metrics endpoint
# --------------------------------------------------

@app.get(
    "/metrics",
    dependencies=[Depends(verify_api_key)]
)
@limiter.limit("30/minute")
def metrics(request: Request):

    return {
        "total_queries": tracker.total_queries,
        "total_input_tokens": tracker.total_input_tokens,
        "total_output_tokens": tracker.total_output_tokens,
        "total_cost": tracker.total_cost,
        "average_cost_per_query": (
            tracker.average_cost_per_query()
        )
    }