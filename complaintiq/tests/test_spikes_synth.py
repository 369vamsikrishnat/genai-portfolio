import pandas as pd

from complaintiq.risk import risk_flags
from complaintiq.spikes import cluster_embeddings, detect_spikes, top_terms, write_brief
from complaintiq.synth import SPIKE, generate


def test_synth_schema(synth_df):
    assert synth_df.complaint_id.is_unique
    assert {"complaint_id", "date_received", "product", "issue", "narrative", "company"} <= set(synth_df.columns)
    assert (synth_df.narrative == "").any()  # blank narratives exist to exercise filters


def test_detects_injected_spike_and_few_false_alarms():
    df = generate(20000, seed=0)
    df["date_received"] = pd.to_datetime(df["date_received"])
    sp = detect_spikes(df)
    top = sp.iloc[0]
    assert top.company == SPIKE["company"] and top.issue == SPIKE["issue"]
    assert pd.Timestamp("2023-07-17") == top.week
    assert len(sp) <= 3


def test_false_alarm_rate_on_pure_noise_within_budget():
    # Regression test. A plug-in Poisson p-value (ignoring that the baseline rate is estimated from
    # a few weeks) gave ~4 false alarms in 12 noise-only scans. With the Gamma-Poisson predictive
    # p-value + Bonferroni the budget is <= 0.05 false alarms per scan (expected ~1 over 20 scans).
    total = 0
    for seed in range(20):
        df = generate(20000, seed=seed, spike=False)
        df["date_received"] = pd.to_datetime(df["date_received"])
        total += len(detect_spikes(df))
    assert total <= 3, f"{total} false alarms over 20 noise-only scans"


def test_brief_falls_back_when_llm_fails():
    class Boom:
        def generate(self, *a, **k):
            raise RuntimeError("down")

    spike = {"company": "A", "issue": "B", "week": pd.Timestamp("2023-01-02"), "count": 30,
             "baseline_mean": 3.0, "z": 9.0}
    assert "30" in write_brief(spike, ["x"], Boom())


def test_clusters_and_terms(synth_df):
    from complaintiq.embed import HashingEmbedder

    texts = synth_df.narrative[synth_df.narrative != ""].head(1200).tolist()
    labels = cluster_embeddings(HashingEmbedder().encode(texts), min_cluster_size=15)
    assert len(labels) == len(texts)
    terms = top_terms(texts, labels)
    assert all(isinstance(v, list) for v in terms.values())


def test_risk_flags():
    assert "legal_threat" in risk_flags("I will contact my attorney")
    assert risk_flags("my statement was late") == []
