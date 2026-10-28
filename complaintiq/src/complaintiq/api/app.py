"""FastAPI service. Needs `pip install .[serve]`. Thin wrapper over Service (see tests/test_service.py)."""
from __future__ import annotations

import logging
import os
import time

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from ..audit import NotApproved
from ..config import Settings
from ..observability import RateLimiter, setup_logging

log = logging.getLogger("complaintiq.api")


class TextIn(BaseModel):
    text: str = Field(min_length=10, max_length=20000)


class ReviewIn(BaseModel):
    reviewer: str = Field(min_length=1, max_length=80)
    note: str = Field(default="", max_length=1000)


def create_app(service=None, settings: Settings | None = None) -> FastAPI:
    setup_logging()
    s = settings or Settings.from_env()
    app = FastAPI(title="ComplaintIQ", version="0.1.0")
    limiter = RateLimiter(s.rate_limit_per_min)
    state = {"svc": service}

    def svc():
        if state["svc"] is None:
            from ..pipeline import Artifacts
            from ..service import Service

            if not Artifacts.exists(s.artifacts_dir):
                raise HTTPException(503, "artifacts not built; run `python -m complaintiq build`")
            state["svc"] = Service.from_artifacts(s)
        return state["svc"]

    def guard(request: Request, x_api_key: str | None = Header(default=None)):
        if s.api_key and x_api_key != s.api_key:
            raise HTTPException(401, "invalid or missing X-API-Key")
        who = x_api_key or (request.client.host if request.client else "anon")
        if not limiter.allow(who):
            raise HTTPException(429, "rate limit exceeded")

    @app.middleware("http")
    async def access_log(request: Request, call_next):
        t0 = time.perf_counter()
        resp = await call_next(request)
        ms = (time.perf_counter() - t0) * 1000
        log.info("request", extra={"extra_fields": {"path": request.url.path, "status": resp.status_code,
                                                    "ms": round(ms, 1)}})
        return resp

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/triage", dependencies=[Depends(guard)])
    def triage(body: TextIn):
        return svc().triage(body.text)

    @app.post("/draft", dependencies=[Depends(guard)])
    def draft(body: TextIn):
        return svc().draft(body.text)

    @app.get("/queue", dependencies=[Depends(guard)])
    def queue():
        return svc().queue()

    @app.post("/queue/{queue_id}/approve", dependencies=[Depends(guard)])
    def approve(queue_id: int, body: ReviewIn):
        try:
            svc().approve(queue_id, body.reviewer, body.note)
        except KeyError:
            raise HTTPException(404, "unknown queue item") from None
        except ValueError as e:
            raise HTTPException(409, str(e)) from None
        return {"ok": True}

    @app.post("/queue/{queue_id}/reject", dependencies=[Depends(guard)])
    def reject(queue_id: int, body: ReviewIn):
        try:
            svc().reject(queue_id, body.reviewer, body.note)
        except KeyError:
            raise HTTPException(404, "unknown queue item") from None
        except ValueError as e:
            raise HTTPException(409, str(e)) from None
        return {"ok": True}

    @app.post("/decisions/{decision_id}/send", dependencies=[Depends(guard)])
    def send(decision_id: int):
        try:
            svc().send(decision_id)
        except KeyError:
            raise HTTPException(404, "unknown decision") from None
        except NotApproved as e:
            raise HTTPException(403, str(e)) from None
        return {"sent": True}

    @app.get("/metrics", response_class=PlainTextResponse)
    def metrics():
        return svc().metrics.render()

    return app


app = create_app() if os.getenv("CIQ_EAGER_APP", "1") == "1" else None
