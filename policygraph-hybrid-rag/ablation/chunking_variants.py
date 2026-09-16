from __future__ import annotations

from typing import Any

from src.ingestion.chunker import fixed_size_split


def build_fixed_size_chunks(
    pages: list[dict[str, Any]],
    doc_name: str,
    chunk_size: int = 200,
) -> list[dict[str, Any]]:
    """
    Build fixed-size chunks for the Day 13 ablation experiment.

    The production section-aware chunker is not modified.
    """

    chunks: list[dict[str, Any]] = []

    for page in pages:
        page_number = page.get("page_number")
        text = page.get("text", "")

        if not text.strip():
            continue

        fixed_chunks = fixed_size_split(
            text,
            chunk_size=chunk_size,
        )

        for index, content in enumerate(
            fixed_chunks,
            start=1,
        ):
            chunks.append(
                {
                    "chunk_id": (
                        f"{doc_name}_fixed_"
                        f"p{page_number}_"
                        f"c{index}"
                    ),
                    "doc_name": doc_name,
                    "page_number": page_number,
                    "section_number": None,
                    "section_title": None,
                    "document_type": "insurance_policy",
                    "content": content,
                    "extraction_method": "fixed_size",
                    "prompt_injection": False,
                }
            )

    return chunks