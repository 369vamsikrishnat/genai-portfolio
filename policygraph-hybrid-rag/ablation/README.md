# Retrieval Ablation Study

This folder contains the Day 13 retrieval ablation experiments for the PolicyGraph Hybrid RAG system.

## Purpose

The experiments measure how different retrieval techniques and chunking strategies affect retrieval quality.

## Retrieval Configurations

Three retrieval configurations were evaluated:

1. **Dense Only**
   - BGE embedding retrieval
   - Top-k vector similarity search

2. **Dense + BM25 + RRF**
   - Dense retrieval
   - BM25 lexical retrieval
   - Reciprocal Rank Fusion (RRF)

3. **Dense + BM25 + RRF + Reranking**
   - Dense retrieval
   - BM25 retrieval
   - RRF fusion
   - Cross-encoder reranking

## Chunking Comparison

A separate experiment compares:

- Section-aware chunking
- Fixed-size chunking

The same golden set and dense retrieval approach are used so that chunking is the primary variable being evaluated.

## Evaluation

The experiments use the retrieval golden set and measure:

- Recall@5
- Hit@1
- Hit@3
- Hit@5
- Mean Reciprocal Rank (MRR)
- Query latency

The raw results and aggregate metrics are stored in the `results/` directory.

## Key Result

For the current 47 answerable golden-set cases:

- Section-aware chunking achieved **0.9574 Recall@5**
- Fixed-size chunking achieved **0.7660 Recall@5**

The results show the impact that chunking strategy can have on retrieval quality for structured policy documents.