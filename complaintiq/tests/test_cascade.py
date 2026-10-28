
from complaintiq.classify import (TriageClassifier, classification_prompt, evaluate_cascade, macro_f1,
                                  parse_label, run_llm_labels, temporal_split)
from complaintiq.embed import HashingEmbedder
from complaintiq.llm import MockLLM

LABELS = ["Credit card", "Mortgage", "Debt collection"]


def test_parse_label():
    assert parse_label("Category: mortgage.", LABELS) == "Mortgage"
    assert parse_label("no idea", LABELS) is None


def test_prompt_marks_untrusted():
    p = classification_prompt("hello", LABELS)
    assert "untrusted" in p and "<complaint>" in p


def test_temporal_split_is_positional():
    import pandas as pd

    assert temporal_split(pd.DataFrame({"a": range(100)})) == 80


def test_cascade_endpoints_and_cost_monotonic(synth_df):
    df = synth_df[synth_df.narrative.fillna("").str.len() > 0].sort_values("date_received").reset_index(drop=True)
    texts = df.narrative.tolist()
    X = HashingEmbedder().encode(texts)
    n = int(len(df) * 0.8)
    y = df["product"].to_numpy()
    clf = TriageClassifier().fit(X[:n], y[:n])
    sel = slice(n, n + 200)
    pred, conf = clf.predict_with_conf(X[sel])
    ytrue, tt = y[sel], texts[sel]
    truth = {t[:1500].strip(): g for t, g in zip(tt, ytrue, strict=True)}
    run = run_llm_labels(MockLLM(truth, accuracy=1.0), tt, list(clf.classes_), 0.75, 3.75)
    rows = evaluate_cascade(ytrue, pred, conf, run, [0.0, 0.6, 0.9, 1.01], 0.1)
    by = {(r["mode"], r["threshold"]): r for r in rows}
    assert by[("llm_only", None)]["macro_f1"] == 1.0
    assert abs(by[("cascade", 0.0)]["macro_f1"] - by[("classifier_only", None)]["macro_f1"]) < 1e-9
    assert abs(by[("cascade", 1.01)]["macro_f1"] - 1.0) < 1e-9
    costs = [by[("cascade", t)]["cost_per_1k_usd"] for t in (0.0, 0.6, 0.9, 1.01)]
    assert costs == sorted(costs) and costs[0] == 0.0
    assert abs(costs[-1] - by[("llm_only", None)]["cost_per_1k_usd"]) < 1e-9
    assert macro_f1(ytrue, pred) > 0.5
