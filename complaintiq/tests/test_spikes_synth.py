import pandas as pd

from complaintiq.risk import risk_flags
from complaintiq.spikes import (
    cluster_embeddings,
    detect_spikes,
    detect_weekly_spikes,
    evaluate_historical_spikes,
    top_terms,
    weekly_counts_wide,
    write_brief,
)
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
    assert "legal_threat" in risk_flags("I will pursue legal action")
    assert risk_flags("my statement was late") == []


def _weekly_counts(values, group=("A", "Product", "Issue")):
    rows = []
    start = pd.Timestamp("2025-01-06")
    for week, count in enumerate(values):
        if count:
            rows.append({
                "company": group[0], "product": group[1], "issue": group[2],
                "week": start + pd.Timedelta(weeks=week), "n": count,
            })
    return pd.DataFrame(rows)


def test_spike_requires_minimum_historical_support():
    counts = _weekly_counts([1] * 8 + [20])
    wide = weekly_counts_wide(counts, ("company", "product", "issue"))

    alerts = detect_weekly_spikes(
        wide, ("company", "product", "issue"), min_count=10, min_baseline_count=20,
    )

    assert alerts.empty


def test_historical_alerts_are_invariant_to_future_groups_and_weeks():
    base = _weekly_counts([3] * 8 + [25])
    future = _weekly_counts([0] * 11 + [50], ("Future Co", "Future product", "Future issue"))
    all_counts = pd.concat([base, future], ignore_index=True)
    keys = ("company", "product", "issue")

    base_alerts = detect_weekly_spikes(weekly_counts_wide(base, keys), keys)
    all_alerts = detect_weekly_spikes(weekly_counts_wide(all_counts, keys), keys)
    base_week = base["week"].max()
    before = all_alerts[all_alerts["week"] <= base_week]

    assert len(base_alerts) == 1
    fields = ["company", "product", "issue", "week", "count", "z", "p_value", "alpha"]
    assert before[fields].reset_index(drop=True).equals(
        base_alerts[fields].reset_index(drop=True)
    )


def test_historical_spike_report_distinguishes_unlabeled_alerts():
    counts = _weekly_counts([3] * 8 + [25])

    report = evaluate_historical_spikes(
        counts, keys=("company", "product", "issue"),
    )

    assert report["evaluation_type"] == "chronological_unlabeled_backtest"
    assert report["alert_summary"]["alerts"] == 1
    assert report["alert_summary"]["severity_counts"]["high"] == 1
    assert report["alert_summary"]["false_alert_count"] is None
    assert report["alert_summary"]["detection_latency_weeks"] is None
    assert report["ground_truth"]["available"] is False
    assert report["alerts"][0]["baseline_count"] == 24
