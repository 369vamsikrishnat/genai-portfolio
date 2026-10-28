"""Build and load the serving artifacts: embeddings, classifier, BM25, metadata, manifest."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from .classify import TriageClassifier, macro_f1, temporal_split
from .data import load_complaints
from .embed import get_embedder
from .retrieve import BM25

META_COLS = ["complaint_id", "date_received", "product", "issue", "company", "company_response", "narrative"]


def build(src: str | Path, out_dir: str | Path, sample: int | None = None, since_year: int | None = None,
          embedder_name: str = "hashing", max_chars: int = 2000, seed: int = 0,
          label_col: str = "product") -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    df = load_complaints(src, since_year=since_year, only_narrative=True, limit=sample, seed=seed)
    if "company_response" not in df.columns:
        df["company_response"] = "unknown"
    df = df.sort_values("date_received").reset_index(drop=True)
    texts = df["narrative"].str.slice(0, max_chars).tolist()

    emb = get_embedder(embedder_name)
    t0 = time.perf_counter()
    X = emb.encode(texts)
    embed_s = time.perf_counter() - t0

    n_train = temporal_split(df)
    y = df[label_col].to_numpy()
    clf = TriageClassifier().fit(X[:n_train], y[:n_train])
    pred, _ = clf.predict_with_conf(X[n_train:])
    f1 = macro_f1(y[n_train:], pred)

    t0 = time.perf_counter()
    bm25 = BM25().fit(texts)
    bm25_s = time.perf_counter() - t0

    np.save(out / "vectors.npy", X)
    joblib.dump(df[META_COLS].assign(narrative=texts), out / "meta.joblib")
    joblib.dump(clf, out / "clf.joblib")
    joblib.dump(bm25, out / "bm25.joblib")
    manifest = {"n": len(df), "dim": int(X.shape[1]), "embedder": emb.name if emb.name != "hashing" else "hashing",
                "embedder_arg": embedder_name, "label_col": label_col, "n_train": n_train,
                "classifier_macro_f1_test": round(f1, 4), "embed_seconds": round(embed_s, 2),
                "bm25_build_seconds": round(bm25_s, 2), "since_year": since_year, "seed": seed,
                "built_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


@dataclass
class Artifacts:
    manifest: dict
    vectors: np.ndarray
    meta: pd.DataFrame
    clf: TriageClassifier
    bm25: BM25
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
        return cls(man, np.load(d / "vectors.npy"), joblib.load(d / "meta.joblib"),
                   joblib.load(d / "clf.joblib"), joblib.load(d / "bm25.joblib"),
                   get_embedder(man["embedder_arg"]))
