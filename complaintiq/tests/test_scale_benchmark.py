from types import SimpleNamespace

import numpy as np
import pandas as pd

from complaintiq import cli, quant
from complaintiq.embed import HashingEmbedder
from complaintiq.evals import scale
from complaintiq.retrieve import BM25


class _Classifier:
    classes_ = np.array(["Credit card", "Mortgage"])

    def predict_with_conf(self, vectors):
        labels = np.where(vectors[:, 0] > -1, "Credit card", "Mortgage")
        return labels, np.full(len(vectors), 0.99)


def _small_artifact():
    texts = [
        "Unauthorized transfer from my checking account",
        "Credit card charge was not authorized by me",
        "Mortgage escrow payment was applied incorrectly",
        "I dispute an unauthorized card transaction",
        "My checking transfer is missing from the account",
        "The mortgage company changed my escrow payment",
    ]
    embedder = HashingEmbedder()
    vectors = embedder.encode(texts)
    meta = pd.DataFrame({
        "narrative": texts,
        "product": ["Checking"] * 3 + ["Credit card"] * 2 + ["Mortgage"],
        "issue": ["Transfers"] * 3 + ["Card dispute"] * 2 + ["Escrow"],
        "company": ["Example Bank"] * 6,
        "date_received": pd.date_range("2024-01-01", periods=len(texts), freq="MS"),
    })
    return SimpleNamespace(
        manifest={"n_train": 4, "n": 6, "data_source_type": "test", "embedder_arg": "hashing"},
        vectors=vectors,
        meta=meta,
        clf=_Classifier(),
        bm25=BM25().fit(texts[:4]),
        embedder=embedder,
        texts=texts,
    )


def test_real_benchmark_measures_temporal_retrieval_and_workloads(settings, tmp_path):
    art = _small_artifact()
    report = scale.run_real_benchmark(
        art, tmp_path / "missing-source", settings, [2, 4], [1],
        n_queries=2, api_requests=1, concurrency=(1,), seed=4,
    )

    assert [row["rows"] for row in report["classification"]["batch_workloads"]] == [2, 4]
    assert [row["index_rows"] for row in report["retrieval"]] == [2] * 4 + [4] * 4
    assert {row["mode"] for row in report["retrieval"]} == {
        "bm25", "dense", "rrf", "rrf_rerank"
    }
    assert report["replay"]["records_processed"] == len(art.meta)
    assert report["api"]["sequential_statuses"] == {"200": 1}
    assert report["cost"]["measured_external_spend_usd"] == 0
    assert report["quantization"][0]["memory_mb"]["binary+int8_rescore"] == round(
        (quant.memory_bytes(2, 384)["binary"] + quant.memory_bytes(2, 384)["int8"]) / 2**20, 2
    )


def test_benchmark_cli_writes_json_and_markdown(monkeypatch, settings, capsys):
    import complaintiq.evals.scale as scale_module

    report = {"sample": "benchmark"}
    monkeypatch.setattr(cli.Settings, "from_env", classmethod(lambda cls: settings))
    monkeypatch.setattr(cli, "_art", lambda _settings: object())
    monkeypatch.setattr(scale_module, "run_real_benchmark", lambda *args, **kwargs: report)
    monkeypatch.setattr(scale_module, "benchmark_to_markdown", lambda _report: "# benchmark")

    cli.main([
        "benchmark", "--sizes", "4", "--ingest-sizes", "2", "--n-queries", "3",
        "--api-requests", "2", "--concurrency", "1",
    ])

    assert (settings.results_dir / "performance_evaluation.json").read_text() == (
        '{\n  "sample": "benchmark"\n}'
    )
    assert (settings.results_dir / "performance_evaluation.md").read_text() == "# benchmark"
    assert capsys.readouterr().out == "# benchmark\n"


def test_memory_measurement_reports_supported_fields():
    memory = scale._process_memory_mb()

    assert set(memory) == {"working_set_mb", "peak_working_set_mb", "private_bytes_mb"}
    assert all(value is None or value >= 0 for value in memory.values())
