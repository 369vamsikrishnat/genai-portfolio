.PHONY: install install-real test lint demo ui api ingest-real build-real eval-all
PY ?= python

install:            ## minimal install (synthetic demo + tests)
	$(PY) -m pip install -e ".[dev]"

install-real:       ## everything for real data + real models + serving
	$(PY) -m pip install -e ".[dev,data,embed,serve,faiss]"

test:
	$(PY) -m pytest -q

lint:
	ruff check .

demo:               ## synthetic end-to-end run (NOT real results)
	$(PY) -m complaintiq demo

api:
	$(PY) -m complaintiq serve

ui:
	streamlit run src/complaintiq/ui/streamlit_app.py

# ---- real-data pipeline (see README) ----
ingest-real:
	$(PY) -m complaintiq download
	$(PY) -m complaintiq ingest --since 2020

build-real:         ## 100k sample with a real embedding model
	CIQ_EMBEDDER=bge-small CIQ_RERANKER=cross-encoder $(PY) -m complaintiq build --src data/parquet --sample 100000 --since 2020

eval-all:
	CIQ_EMBEDDER=bge-small CIQ_RERANKER=cross-encoder $(PY) -m complaintiq eval-retrieval --n-queries 500
	$(PY) -m complaintiq eval-cascade --n 500
	$(PY) -m complaintiq spikes --brief
	$(PY) -m complaintiq scale --sizes 100000
