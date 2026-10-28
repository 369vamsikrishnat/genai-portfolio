import zipfile

import pytest

from complaintiq.schema import COLUMN_MAP

duckdb = pytest.importorskip("duckdb")


def test_ingest_roundtrip(tmp_path, synth_df):
    from complaintiq.data import load_complaints
    from complaintiq.ingest import ingest

    raw = synth_df.head(500).copy()
    raw.loc[raw.index[0], "narrative"] = "Call me at 415-555-0134 or mail jane@example.com"
    raw["date_received"] = raw["date_received"].map(lambda d: f"{d[5:7]}/{d[8:10]}/{d[:4]}")  # CFPB-style MM/DD/YYYY
    for c in ("zip3", "submitted_via", "disputed", "date_sent", "tags", "consent", "company_public_response"):
        raw[c] = ""
    dup = raw.head(1)
    raw = __import__("pandas").concat([raw, dup])  # duplicate complaint_id must be deduped
    raw.rename(columns={v: k for k, v in COLUMN_MAP.items()}).to_csv(tmp_path / "complaints.csv", index=False)
    with zipfile.ZipFile(tmp_path / "complaints.csv.zip", "w") as z:
        z.write(tmp_path / "complaints.csv", "complaints.csv")

    expected = int(synth_df.head(500).narrative.str.len().gt(0).sum())
    r1 = ingest(tmp_path / "complaints.csv.zip", tmp_path / "pq")
    assert not r1["skipped"] and r1["rows"] == expected
    assert ingest(tmp_path / "complaints.csv.zip", tmp_path / "pq")["skipped"]  # idempotent
    df = load_complaints(tmp_path / "pq")
    assert len(df) == expected and df.complaint_id.is_unique
    assert not df.narrative.str.contains("415-555-0134|jane@example.com", regex=True).any()
