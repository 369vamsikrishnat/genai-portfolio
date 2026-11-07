"""FastAPI service. Needs `pip install .[serve]`. Thin wrapper over Service (see tests/test_service.py)."""
from __future__ import annotations

import logging
import os
import re
import time
import uuid

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field, field_validator

from ..audit import NotApproved
from ..config import Settings
from ..observability import Metrics, RateLimiter, setup_logging

log = logging.getLogger("complaintiq.api")


class TextIn(BaseModel):
    text: str = Field(min_length=10, max_length=20000)

    @field_validator("text")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must contain non-whitespace characters")
        return value


class ReviewIn(BaseModel):
    reviewer: str = Field(min_length=1, max_length=80)
    note: str = Field(default="", max_length=1000)


def create_app(service=None, settings: Settings | None = None) -> FastAPI:
    setup_logging()
    s = settings or Settings.from_env()
    app = FastAPI(title="ComplaintIQ", version="0.1.0")
    limiter = RateLimiter(s.rate_limit_per_min)
    request_metrics = Metrics()
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

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        errors = [
            {"type": error["type"], "loc": error["loc"], "msg": error["msg"]}
            for error in exc.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": errors})

    @app.middleware("http")
    async def access_log(request: Request, call_next):
        client_request_id = request.headers.get("x-request-id", "")
        request_id = (
            client_request_id
            if re.fullmatch(r"[A-Za-z0-9._-]{1,128}", client_request_id)
            else str(uuid.uuid4())
        )
        request.state.request_id = request_id
        t0 = time.perf_counter()
        error_type = None
        try:
            resp = await call_next(request)
        except Exception as exc:
            error_type = type(exc).__name__
            resp = JSONResponse(
                status_code=500, content={"detail": "internal server error", "request_id": request_id}
            )
        ms = (time.perf_counter() - t0) * 1000
        route = request.scope.get("route")
        route_path = getattr(route, "path", "unmatched")
        request_metrics.inc(
            "ciq_http_requests_total", method=request.method, route=route_path,
            status=str(resp.status_code),
        )
        request_metrics.observe(
            "ciq_http_request_seconds", ms, method=request.method, route=route_path
        )
        resp.headers["X-Request-ID"] = request_id
        fields = {
            "request_id": request_id, "method": request.method, "route": route_path,
            "status": resp.status_code, "ms": round(ms, 1),
        }
        if error_type:
            fields["error_type"] = error_type
        log.log(
            logging.ERROR if error_type else logging.INFO,
            "request_failed" if error_type else "request",
            extra={"extra_fields": fields},
        )
        return resp

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/triage", dependencies=[Depends(guard)])
    def triage(body: TextIn, request: Request):
        return svc().triage(body.text, request_id=request.state.request_id)

    @app.post("/draft", dependencies=[Depends(guard)])
    def draft(body: TextIn, request: Request):
        return svc().draft(body.text, request_id=request.state.request_id)

    @app.get("/queue", dependencies=[Depends(guard)])
    def queue():
        return svc().queue()

    @app.post("/queue/{queue_id}/approve", dependencies=[Depends(guard)])
    def approve(queue_id: int, body: ReviewIn, request: Request):
        try:
            svc().approve(queue_id, body.reviewer, body.note, request_id=request.state.request_id)
        except KeyError:
            raise HTTPException(404, "unknown queue item") from None
        except ValueError as e:
            raise HTTPException(409, str(e)) from None
        return {"ok": True}

    @app.post("/queue/{queue_id}/reject", dependencies=[Depends(guard)])
    def reject(queue_id: int, body: ReviewIn, request: Request):
        try:
            svc().reject(queue_id, body.reviewer, body.note, request_id=request.state.request_id)
        except KeyError:
            raise HTTPException(404, "unknown queue item") from None
        except ValueError as e:
            raise HTTPException(409, str(e)) from None
        return {"ok": True}

    @app.post("/decisions/{decision_id}/send", dependencies=[Depends(guard)])
    def send(decision_id: int, request: Request):
        try:
            svc().send(decision_id, request_id=request.state.request_id)
        except KeyError:
            raise HTTPException(404, "unknown decision") from None
        except NotApproved as e:
            raise HTTPException(403, str(e)) from None
        return {"sent": True}

    @app.get("/metrics", response_class=PlainTextResponse)
    def metrics():
        service_metrics = state["svc"].metrics.render() if state["svc"] is not None else ""
        return request_metrics.render() + service_metrics

    return app


app = create_app() if os.getenv("CIQ_EAGER_APP", "1") == "1" else None
