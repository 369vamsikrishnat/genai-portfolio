"""Orchestration: triage cascade -> routing/risk flags -> drafting -> audit log + human queue."""
from __future__ import annotations

import time

from .audit import AuditLog
from .classify import classification_prompt, parse_label
from .draft import PROMPT_VERSION, Drafter, scan_injection, sanitize
from .llm import cost_usd
from .observability import Metrics
from .pipeline import Artifacts
from .retrieve import HybridRetriever, get_reranker
from .risk import risk_flags

ROUTING = {  # predicted product -> owning team (edit for your org)
    "Credit card": "Cards Disputes", "Mortgage": "Mortgage Servicing",
    "Checking or savings account": "Deposits Ops", "Debt collection": "Collections Compliance",
    "Credit reporting": "Credit Bureau Liaison",
}
DEFAULT_TEAM = "General Review"


class Service:
    def __init__(self, art: Artifacts, llm, settings, audit: AuditLog | None = None,
                 metrics: Metrics | None = None):
        self.art, self.llm, self.s = art, llm, settings
        self.audit = audit or AuditLog(settings.artifacts_dir / "audit.db")
        self.metrics = metrics or Metrics()
        self.artifact_version = str(
            art.manifest.get("artifact_version") or art.manifest.get("built_at") or "unknown"
        )
        sklearn_version = art.manifest.get("runtime_versions", {}).get("scikit_learn", "unrecorded")
        self.classifier_version = f"{type(art.clf).__name__}/scikit-learn-{sklearn_version}"
        self.labels = [str(c) for c in art.clf.classes_]
        self.retriever = HybridRetriever(art.texts, art.vectors, art.embedder, art.bm25,
                                         get_reranker(settings.reranker))
        self.drafter = Drafter(self.retriever, art.meta, llm, min_dense_score=settings.min_dense_score,
                               max_chars=settings.max_chars)

    @classmethod
    def from_artifacts(cls, settings, llm=None) -> Service:
        from .llm import get_llm

        art = Artifacts.load(settings.artifacts_dir)
        return cls(art, llm or get_llm(settings), settings)

    def triage(self, text: str, request_id: str | None = None) -> dict:
        t0 = time.perf_counter()
        try:
            inj = scan_injection(text)
            clean = sanitize(text, self.s.max_chars)
            x = self.art.embedder.encode([clean])
            pred, conf = self.art.clf.predict_with_conf(x)
            label, confidence, source, cost, review = str(pred[0]), float(conf[0]), "classifier", 0.0, []
            if inj:
                review.append("possible prompt injection")
            elif confidence < self.s.llm_threshold:
                r = self.llm.generate(classification_prompt(clean, self.labels), max_tokens=24)
                cost = cost_usd(r.usage, self.s.price_in_per_m, self.s.price_out_per_m)
                llm_label = parse_label(r.text, self.labels)
                source = "llm"
                if llm_label is None:
                    review.append("LLM answer unparsable")
                else:
                    label = llm_label
                    if llm_label != str(pred[0]) and confidence < 0.4:
                        review.append("classifier and LLM disagree at low confidence")
            flags = risk_flags(text)
            if "identity_theft_fraud" in flags:
                review.append("identity_theft_fraud requires human review")
        except Exception as exc:
            self.audit.log_error(
                "triage", text, type(exc).__name__, request_id=request_id,
                model=self.classifier_version, artifact_version=self.artifact_version,
            )
            self.metrics.inc("ciq_triage_errors_total", error_type=type(exc).__name__)
            raise
        result = {"product": label, "confidence": round(confidence, 4), "source": source,
                  "team": ROUTING.get(label, DEFAULT_TEAM), "risk_flags": flags,
                  "needs_review": bool(review), "review_reasons": review, "est_cost_usd": cost}
        model = self.classifier_version
        if source == "llm":
            model += f";llm={getattr(self.llm, 'name', 'unknown')}"
        did = self.audit.log_decision(
            "triage", text, result, model, "triage-v1",
            "pending_review" if review else "logged", request_id=request_id,
            artifact_version=self.artifact_version,
        )
        if review:
            self.audit.enqueue(did, "; ".join(review), request_id=request_id)
        result["decision_id"] = did
        self.metrics.inc("ciq_triage_total", source=source)
        self.metrics.observe("ciq_triage_seconds", time.perf_counter() - t0)
        return result

    def draft(self, text: str, request_id: str | None = None) -> dict:
        t0 = time.perf_counter()
        try:
            d = self.drafter.draft(text)
        except Exception as exc:
            self.audit.log_error(
                "draft", text, type(exc).__name__, request_id=request_id,
                model="evidence-template", artifact_version=self.artifact_version,
            )
            self.metrics.inc("ciq_draft_errors_total", error_type=type(exc).__name__)
            raise
        safe_precedents = [
            {key: precedent[key] for key in ("id", "product", "issue", "outcome", "dense_score")
             if key in precedent}
            for precedent in d.precedents
        ]
        payload = {"status": d.status, "text": d.text, "citations": d.citations,
                   "precedents": safe_precedents, "reasons": d.reasons}
        did = self.audit.log_decision(
            "draft", text, payload, d.model, PROMPT_VERSION, "pending_approval",
            request_id=request_id, artifact_version=self.artifact_version,
        )
        qid = self.audit.enqueue(
            did, "draft approval" if d.status == "ok" else f"draft {d.status}: {'; '.join(d.reasons)}",
            request_id=request_id,
        )
        self.metrics.inc("ciq_draft_total", status=d.status)
        self.metrics.observe("ciq_draft_seconds", time.perf_counter() - t0)
        return {**payload, "decision_id": did, "queue_id": qid}

    def queue(self) -> list[dict]:
        pending = self.audit.pending()
        for item in pending:
            payload = item["payload"]
            payload["precedents"] = [
                {key: value for key, value in precedent.items() if key != "snippet"}
                for precedent in payload.get("precedents", [])
            ]
        return pending

    def approve(self, queue_id: int, reviewer: str, note: str = "",
                request_id: str | None = None) -> None:
        self.audit.resolve(queue_id, reviewer, True, note, request_id=request_id)

    def reject(self, queue_id: int, reviewer: str, note: str = "",
               request_id: str | None = None) -> None:
        self.audit.resolve(queue_id, reviewer, False, note, request_id=request_id)

    def send(self, decision_id: int, request_id: str | None = None) -> None:
        self.audit.mark_sent(decision_id, request_id=request_id)
