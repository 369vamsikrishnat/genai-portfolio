
"""Build and load serving artifacts: embeddings, classifier, BM25, metadata, manifest."""
from __future__ import annotations

import hashlib
import json
import platform
import time
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn

from .classify import TriageClassifier, macro_f1, temporal_split
from .data import load_complaints
from .embed import get_embedder
from .retrieve import BM25

META_COLS = [
    "complaint_id", "date_received", "product", "issue",
    "company", "company_response", "narrative",
]


def _dedupe_templates(df: pd.DataFrame) -> pd.DataFrame:
    """Keep the earliest complaint for each normalized narrative."""
    from .report import normalized_hash_series

    key = (
        df["narrative_hash"]
        if "narrative_hash" in df.columns
        else normalized_hash_series(df["narrative"])
    )
    return df.loc[~key.duplicated(keep="first")].reset_index(drop=True)


def _sample_training(df: pd.DataFrame, sample: int | None, seed: int) -> pd.DataFrame:
    """Deterministically sample training candidates only."""
    if sample is not None and sample > 0 and len(df) > sample:
        df = df.sample(n=sample, random_state=seed)
    return df.sort_values(["date_received", "complaint_id"]).reset_index(drop=True)


def build(
    src: str | Path,
    out_dir: str | Path,
    sample: int | None = None,
    since_year: int | None = None,
    embedder_name: str = "hashing",
    max_chars: int = 2000,
    seed: int = 0,
    label_col: str = "product",
    dedupe_templates: bool = True,
    data_source_type: str = "unspecified",
    test_cutoff: str | None = None,
    classifier_only: bool = False,
) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Load all eligible rows. Sampling happens after the frozen test split.
    df = load_complaints(
        src,
        since_year=since_year,
        only_narrative=True,
        limit=None if test_cutoff else sample,
        seed=seed,
    )

    if "company_response" not in df.columns:
        df["company_response"] = "unknown"

    df = df.sort_values(["date_received", "complaint_id"]).reset_index(drop=True)
    n_before = len(df)

    if dedupe_templates:
        df = _dedupe_templates(df)

    cutoff = None
    test_ids_hash = None

    if test_cutoff:
        cutoff = pd.Timestamp(test_cutoff)
        if pd.isna(cutoff):
            raise ValueError(f"Invalid test_cutoff: {test_cutoff}")

        train_candidates = df[df["date_received"] < cutoff].copy()
        test_df = df[df["date_received"] >= cutoff].copy()

        if train_candidates.empty:
            raise ValueError("No training complaints exist before test_cutoff.")
        if test_df.empty:
            raise ValueError("No test complaints exist on or after test_cutoff.")

        # Sample only the training period; the test set is never sampled.
        train_df = _sample_training(train_candidates, sample, seed)
        df = pd.concat([train_df, test_df], ignore_index=True)
        df = df.sort_values(["date_received", "complaint_id"]).reset_index(drop=True)
        n_train = len(train_df)
        split_strategy = "fixed_date_cutoff"
        test_start = test_df["date_received"].min().date().isoformat()
        train_end = train_df["date_received"].max().date().isoformat()

        # Save a stable, sorted list of frozen test complaint IDs.
        test_ids = sorted(test_df["complaint_id"].astype(str).unique())
        test_ids_content = "\n".join(test_ids) + "\n"
        test_ids_path = out / "test_ids.txt"
        test_ids_path.write_text(test_ids_content, encoding="utf-8")
        test_ids_hash = hashlib.sha256(
            test_ids_content.encode("utf-8")
        ).hexdigest()

        # The training rows are first because the combined frame is chronological
        # only when the cutoff boundary is respected.
        df = pd.concat([train_df, test_df], ignore_index=True)
        df = df.sort_values(["date_received", "complaint_id"]).reset_index(drop=True)

        # Re-establish the split position after sorting.
        n_train = int((df["date_received"] < cutoff).sum())
        if n_train == 0 or n_train == len(df):
            raise ValueError("The cutoff produced an empty training or test set.")

    else:
        # Preserve the original sampling and chronological 80/20 behavior.
        df = df.sort_values(["date_received", "complaint_id"]).reset_index(drop=True)
        n_train = temporal_split(df)
        if n_train == 0 or n_train == len(df):
            raise ValueError("The chronological split produced an empty training or test set.")
        split_strategy = "chronological_80_20"
        train_end = df["date_received"].iloc[n_train - 1].date().isoformat()
        test_start = df["date_received"].iloc[n_train].date().isoformat()

    texts = df["narrative"].fillna("").astype(str).str.slice(0, max_chars).tolist()

    emb = get_embedder(embedder_name)
    t0 = time.perf_counter()
    X = emb.encode(texts)
    embed_s = time.perf_counter() - t0

    y = df[label_col].to_numpy()
    clf = TriageClassifier().fit(X[:n_train], y[:n_train])
    pred, _ = clf.predict_with_conf(X[n_train:])
    f1 = macro_f1(y[n_train:], pred)

    bm25_s = None
    if not classifier_only:
        t0 = time.perf_counter()
        bm25 = BM25().fit(texts)
        bm25_s = time.perf_counter() - t0
        joblib.dump(bm25, out / "bm25.joblib")

    np.save(out / "vectors.npy", X)
    joblib.dump(clf, out / "clf.joblib")
    joblib.dump(df[META_COLS].assign(narrative=texts), out / "meta.joblib")

    built_at = time.strftime("%Y-%m-%dT%H:%M:%S")
    manifest = {
        "n": len(df),
        "dim": int(X.shape[1]),
        "embedder": emb.name if emb.name != "hashing" else "hashing",
        "embedder_arg": embedder_name,
        "label_col": label_col,
        "n_train": n_train,
        "n_test": len(df) - n_train,
        "data_source": str(Path(src).resolve()),
        "data_source_type": data_source_type,
        "sample": sample,
        "classifier_only": classifier_only,
        "test_cutoff": cutoff.date().isoformat() if cutoff is not None else None,
        "test_ids_file": "test_ids.txt" if cutoff is not None else None,
        "test_ids_sha256": test_ids_hash,
        "temporal_split": {
            "strategy": split_strategy,
            "train_rows": n_train,
            "test_rows": len(df) - n_train,
            "train_end": train_end,
            "test_start": test_start,
        },
        "classifier_macro_f1_test": round(float(f1), 4),
        "n_before_template_dedupe": n_before,
        "n_after_template_dedupe": (
            len(df) if test_cutoff else len(df)
            ),
        "embed_seconds": round(embed_s, 2),
        "bm25_build_seconds": round(bm25_s, 2) if bm25_s is not None else None,
        "since_year": since_year,
        "seed": seed,
        "built_at": built_at,
        "artifact_version": f"ciq-{built_at}-{len(df)}-{seed}",
        "runtime_versions": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scikit_learn": sklearn.__version__,
        },
    }

    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


@dataclass
class Artifacts:
    manifest: dict
    vectors: np.ndarray
    meta: pd.DataFrame
    clf: TriageClassifier
    bm25: BM25 | None
    embedder: object

    @property
    def texts(self) -> list[str]:
        return self.meta["narrative"].tolist()

    @classmethod
    def exists(cls, d: str | Path) -> bool:
        return (Path(d) / "manifest.json").exists()

    @classmethod
    def load(cls, d: str | Path) -> Artifacts:
        d = Path(d)
        man = json.loads((d / "manifest.json").read_text())
        bm25_path = d / "bm25.joblib"
        bm25 = joblib.load(bm25_path) if bm25_path.exists() else None

        return cls(
            man,
            np.load(d / "vectors.npy"),
            joblib.load(d / "meta.joblib"),
            joblib.load(d / "clf.joblib"),
            bm25,
            get_embedder(man["embedder_arg"]),
        )
