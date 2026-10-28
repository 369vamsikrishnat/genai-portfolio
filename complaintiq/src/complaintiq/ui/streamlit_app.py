"""Streamlit demo UI. Run: streamlit run src/complaintiq/ui/streamlit_app.py (needs .[serve])."""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from complaintiq.config import Settings
from complaintiq.pipeline import Artifacts
from complaintiq.service import Service

st.set_page_config(page_title="ComplaintIQ", layout="wide")
s = Settings.from_env()


@st.cache_resource
def get_service():
    if not Artifacts.exists(s.artifacts_dir):
        from complaintiq.cli import cmd_ensure
        import argparse

        cmd_ensure(argparse.Namespace(n=20000), s)
    return Service.from_artifacts(s)


svc = get_service()
st.title("ComplaintIQ")
st.caption(f"LLM provider: {s.llm_provider} | embedder: {svc.art.manifest['embedder_arg']} | "
           f"corpus: {svc.art.manifest['n']:,} complaints")
if s.llm_provider == "mock" or svc.art.manifest["embedder_arg"] == "hashing":
    st.warning("Demo mode: stand-in components on synthetic data. Not real model quality.")

t1, t2, t3, t4 = st.tabs(["Triage and draft", "Review queue", "Emerging issues", "Eval results"])

with t1:
    text = st.text_area("Paste a complaint narrative", height=160)
    c1, c2 = st.columns(2)
    if c1.button("Triage") and text.strip():
        st.json(svc.triage(text))
    if c2.button("Draft cited reply") and text.strip():
        d = svc.draft(text)
        st.write(f"Status: **{d['status']}**")
        st.write(d["text"])
        if d["precedents"]:
            st.dataframe(pd.DataFrame(d["precedents"]))

with t2:
    items = svc.queue()
    st.write(f"{len(items)} pending")
    for it in items:
        with st.expander(f"#{it['queue_id']} {it['kind']}: {it['reason']}"):
            st.json(it["payload"])
            who = st.text_input("Reviewer", key=f"who{it['queue_id']}", value="reviewer")
            a, r = st.columns(2)
            if a.button("Approve", key=f"a{it['queue_id']}"):
                svc.approve(it["queue_id"], who)
                st.rerun()
            if r.button("Reject", key=f"r{it['queue_id']}"):
                svc.reject(it["queue_id"], who)
                st.rerun()

with t3:
    p = s.results_dir / "spikes.json"
    if p.exists():
        st.dataframe(pd.DataFrame(json.loads(p.read_text())))
    else:
        st.info("Run `python -m complaintiq spikes --brief` first.")

with t4:
    for name in ("ablation", "cost_table", "scale"):
        f = Path(s.docs_dir) / f"{name}.md"
        if f.exists():
            st.markdown(f.read_text())
