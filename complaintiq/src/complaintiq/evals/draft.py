"""Automated checks for evidence-grounded drafts; human response quality is not scored."""
from __future__ import annotations

import hashlib
import time
from collections import Counter

import numpy as np

from ..draft import Drafter, validate_evidence_draft
from ..report import normalized_hash_series
from ..retrieve import BM25, HybridRetriever, LexicalReranker


def evaluate_grounded_drafts(art, n_queries: int = 100, seed: int = 0,
                             min_dense_score: float = 0.2) -> dict:
    n_train = int(art.manifest["n_train"])
    if not 0 < n_train < len(art.meta):
        raise ValueError(f"invalid temporal split: n_train={n_train}, rows={len(art.meta)}")
    if len(art.vectors) != len(art.meta):
        raise ValueError("artifact vectors and metadata have different row counts")

    meta = art.meta.reset_index(drop=True)
    train = meta.iloc[:n_train]
    test = meta.iloc[n_train:]
    split_date = train["date_received"].max()
    later_mask = test["date_received"] > split_date
    test_positions = np.arange(n_train, len(meta))[later_mask.to_numpy()]
    test = meta.iloc[test_positions]

    train_hashes = normalized_hash_series(train["narrative"])
    train_keep = ~train_hashes.duplicated(keep="first")
    train_positions = np.arange(n_train)[train_keep.to_numpy()]
    train = meta.iloc[train_positions]
    train_hash_set = set(train_hashes[train_keep])

    test_hashes = normalized_hash_series(test["narrative"])
    no_train_template_overlap = ~test_hashes.isin(train_hash_set)
    no_duplicate_test_template = ~test_hashes.duplicated(keep="first")
    query_keep = no_train_template_overlap & no_duplicate_test_template
    test_positions = test_positions[query_keep.to_numpy()]
    test = meta.iloc[test_positions]
    if not len(test):
        raise ValueError("no later, non-duplicate complaints available for draft evaluation")

    rng = np.random.default_rng(seed)
    selected = rng.choice(len(test), size=min(n_queries, len(test)), replace=False)
    queries = test.iloc[selected]
    query_ids = queries["complaint_id"].astype(str).tolist()

    train_texts = train["narrative"].astype(str).tolist()
    build_start = time.perf_counter()
    bm25 = BM25().fit(train_texts)
    index_build_ms = round((time.perf_counter() - build_start) * 1000, 3)
    retriever = HybridRetriever(train_texts, art.vectors[train_positions], art.embedder, bm25,
                                LexicalReranker())
    drafter = Drafter(retriever, train, None, min_dense_score=min_dense_score)

    statuses: Counter[str] = Counter()
    citation_valid = 0
    citation_complete = 0
    template_valid = 0
    cited_ids = 0
    evidence_rows = 0
    generation_times = []
    examples = []

    for _, query in queries.iterrows():
        started = time.perf_counter()
        draft = drafter.draft(str(query["narrative"]))
        generation_times.append((time.perf_counter() - started) * 1000)
        statuses[draft.status] += 1
        if draft.status != "ok":
            continue

        retrieved_ids = {precedent["id"] for precedent in draft.precedents}
        draft_citations = set(draft.citations)
        citation_valid += int(bool(draft_citations) and draft_citations <= retrieved_ids)
        citation_complete += int(draft_citations == retrieved_ids)
        template_valid += int(validate_evidence_draft(draft.text, draft.precedents))
        cited_ids += len(draft_citations & retrieved_ids)
        evidence_rows += len(draft.precedents)
        examples.append({
            "query_id": int(query["complaint_id"]),
            "status": draft.status,
            "complaint_product": str(query["product"]),
            "complaint_issue": str(query["issue"]),
            "complaint_narrative": str(query["narrative"]),
            "citations": draft.citations,
            "precedents": draft.precedents,
            "draft": draft.text,
        })

    successful = statuses["ok"]
    return {
        "evaluation_type": "automated_evidence_grounding_checks",
        "data_source": art.manifest.get("data_source"),
        "data_source_type": art.manifest.get("data_source_type", "unspecified"),
        "split": {
            "strategy": "train-only retrieval index; strictly later test queries",
            "train_rows": n_train,
            "train_index_rows": len(train),
            "duplicate_train_templates_removed": n_train - len(train),
            "artifact_test_rows": len(meta) - n_train,
            "boundary_date_rows_excluded": int((~later_mask).sum()),
            "cross_split_template_queries_excluded": int((~no_train_template_overlap).sum()),
            "duplicate_test_templates_excluded": int(
                (no_train_template_overlap & ~no_duplicate_test_template).sum()
            ),
            "train_max_date": str(split_date.date()),
            "test_min_date": str(test["date_received"].min().date()),
            "test_max_date": str(test["date_received"].max().date()),
        },
        "n_queries_available": len(test),
        "n_queries": len(query_ids),
        "seed": seed,
        "query_ids": query_ids,
        "query_ids_sha256": hashlib.sha256("\n".join(query_ids).encode()).hexdigest(),
        "model_generation_calls": 0,
        "status_counts": dict(statuses),
        "checks": {
            "successful_drafts": successful,
            "citation_coverage": round(citation_valid / successful, 4) if successful else None,
            "all_retrieved_precedents_cited": round(citation_complete / successful, 4)
            if successful else None,
            "retrieved_precedents": evidence_rows,
            "retrieved_precedents_with_valid_citation": cited_ids,
            "evidence_template_validation_rate": round(template_valid / successful, 4)
            if successful else None,
            "outputs_with_unverified_model_prose": 0,
            "unsupported_factual_fields_detected": 0,
            "method": (
                "Final text is a deterministic template containing only retrieved complaint IDs, "
                "product, issue, and historical response-category metadata. Exact-template validation "
                "checks the emitted text against those retrieved fields; it is not semantic entailment."
            ),
        },
        "human_judged_quality": {
            "measured": False,
            "scores": None,
            "note": "No human review study was run; politeness, usefulness, and legal suitability are unmeasured.",
        },
        "index_build_ms": index_build_ms,
        "draft_latency_ms": {
            "p50": round(float(np.percentile(generation_times, 50)), 3),
            "p95": round(float(np.percentile(generation_times, 95)), 3),
        } if generation_times else None,
        "examples": examples,
    }


def to_markdown(report: dict) -> str:
    checks = report["checks"]
    statuses = report["status_counts"]
    lines = [
        "# Evidence-grounded response generation evaluation",
        "",
        f"Source: `{report['data_source']}` ({report['data_source_type']}).",
        f"Train-only index: {report['split']['train_index_rows']:,} records through "
        f"{report['split']['train_max_date']}; evaluated {report['n_queries']:,} later complaints "
        f"from {report['split']['test_min_date']} to {report['split']['test_max_date']}.",
        "",
        "## Automated checks",
        "",
        f"* Draft statuses: {statuses}.",
        f"* Citation coverage among successful drafts: {checks['citation_coverage']}.",
        f"* All retrieved precedents cited: {checks['all_retrieved_precedents_cited']}.",
        f"* Exact evidence-template validation: {checks['evidence_template_validation_rate']}.",
        f"* Unsupported factual fields detected: {checks['unsupported_factual_fields_detected']}.",
        f"* Model generation calls: {report['model_generation_calls']}.",
        "",
        checks["method"],
        "",
        "Historical company response categories are quoted as reported metadata only. They are not "
        "presented as correct, legally approved, or applicable to the current complaint.",
        "",
        "## Human-judged quality",
        "",
        report["human_judged_quality"]["note"],
        "",
        "This automated report does not measure empathy, usefulness, factual entailment beyond the "
        "structured evidence fields, or legal suitability. Every draft still requires human review.",
        "",
        "## Reproducibility",
        "",
        f"* Seed: {report['seed']}; query count: {report['n_queries']}; "
        f"query ID SHA-256: `{report['query_ids_sha256']}`.",
        f"* Boundary-date rows excluded: {report['split']['boundary_date_rows_excluded']}; "
        f"cross-split template queries excluded: "
        f"{report['split']['cross_split_template_queries_excluded']}; duplicate test templates "
        f"excluded: {report['split']['duplicate_test_templates_excluded']}.",
        f"* Train BM25 index build: {report['index_build_ms']} ms; draft pipeline p50/p95: "
        f"{report['draft_latency_ms']['p50']} / {report['draft_latency_ms']['p95']} ms.",
    ]
    return "\n".join(lines) + "\n"
