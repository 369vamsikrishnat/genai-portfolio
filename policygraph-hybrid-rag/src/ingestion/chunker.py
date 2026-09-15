from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from src.ingestion.ocr import (
    detect_pdf_type,
    load_document_pages,
)


# ============================================================
# PROMPT INJECTION DETECTION
# ============================================================

PROMPT_INJECTION_PATTERNS = [
    r"\bignore\s+(?:all\s+)?previous\s+instructions\b",
    r"\bdisregard\s+(?:all\s+)?previous\s+instructions\b",
    r"\bforget\s+(?:all\s+)?previous\s+instructions\b",
    r"\bsystem\s+override\b",
    r"\bdeveloper\s+message\b",
    r"\bignore\s+(?:the\s+)?system\s+prompt\b",
    r"\bignore\s+(?:the\s+)?developer\s+instructions\b",
]


def detect_prompt_injection(
    text: str,
) -> bool:
    """
    Detect common prompt-injection patterns in document text.

    This is only a security signal.

    It is NOT a complete prompt-injection defense.

    Retrieved document content must always be treated as
    untrusted data by the generation layer.
    """

    if not text:
        return False

    text_lower = text.lower()

    return any(
        re.search(
            pattern,
            text_lower,
            flags=re.IGNORECASE,
        )
        for pattern in PROMPT_INJECTION_PATTERNS
    )


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_page_text(
    text: str,
) -> str:
    """
    Clean extracted page text while preserving meaningful
    document structure.

    Removes:
    - empty lines
    - standalone page numbers
    - excessive whitespace

    Does not aggressively rewrite the source text.
    """

    if not text:
        return ""

    lines = text.splitlines()

    cleaned_lines: list[str] = []

    for line in lines:

        stripped = line.strip()

        if not stripped:
            continue

        # Remove standalone page numbers.
        if re.fullmatch(
            r"\d+",
            stripped,
        ):
            continue

        # Normalize repeated spaces/tabs.
        normalized = re.sub(
            r"[ \t]+",
            " ",
            stripped,
        )

        cleaned_lines.append(
            normalized
        )

    return "\n".join(
        cleaned_lines
    ).strip()


def clean_document_pages(
    pages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Clean page text while preserving page metadata.
    """

    cleaned_pages: list[dict[str, Any]] = []

    for page in pages:

        cleaned_text = clean_page_text(
            page.get(
                "text",
                "",
            )
        )

        if not cleaned_text:
            continue

        cleaned_pages.append(
            {
                "page_number": page[
                    "page_number"
                ],
                "text": cleaned_text,
                "extraction_method": page.get(
                    "extraction_method",
                    "text",
                ),
            }
        )

    return cleaned_pages


# ============================================================
# HEADING DETECTION
# ============================================================

def _normalize_heading(
    line: str,
) -> str:
    return re.sub(
        r"\s+",
        " ",
        line.strip(),
    )


def is_major_heading(
    line: str,
) -> bool:
    """
    Detect major policy-level headings.

    These boundaries are based on the structure of the
    insurance policy used by this project.
    """

    normalized = _normalize_heading(
        line
    )

    if not normalized:
        return False

    patterns = [
        r"^SECTION\s+I(?:\.)?\s*-?",
        r"^SECTION\s+II\s*-?",
        r"^SECTION\s+III$",
        (
            r"^PERSONAL\s+ACCIDENT\s+COVER\s+"
            r"FOR\s+OWNER-DRIVER\s+SECTION$"
        ),
        (
            r"^SUM\s+INSURED,\s+"
            r"INSURED['’]S\s+DECLARED\s+VALUE"
        ),
        (
            r"^AVOIDANCE\s+OF\s+CERTAIN\s+TERMS\s+"
            r"AND\s+RIGHT\s+OF\s+RECOVERY$"
        ),
        (
            r"^APPLICATION\s+OF\s+LIMITS\s+"
            r"OF\s+INDEMNITY"
        ),
        r"^GENERAL\s+EXCEPTIONS$",
        r"^DEDUCTIBLE$",
        r"^CONDITIONS$",
    ]

    return any(
        re.match(
            pattern,
            normalized,
            flags=re.IGNORECASE,
        )
        for pattern in patterns
    )


# ============================================================
# MAJOR SECTION BUILDING
# ============================================================

def build_major_sections(
    pages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Build logical major sections from page-aware text.

    Each section contains:

        heading
        content
        start_page
        end_page
        pages
    """

    sections: list[dict[str, Any]] = []

    current_section: dict[str, Any] | None = None

    for page in pages:

        page_number = page[
            "page_number"
        ]

        lines = page[
            "text"
        ].splitlines()

        index = 0

        while index < len(lines):

            line = lines[
                index
            ].strip()

            if not line:
                index += 1
                continue

            # ------------------------------------------------
            # SECTION III SPECIAL CASE
            # ------------------------------------------------
            #
            # In the source policy, SECTION III and
            # PERSONAL ACCIDENT COVER FOR OWNER-DRIVER
            # SECTION can appear as a two-line heading.
            # ------------------------------------------------

            if re.match(
                r"^SECTION\s+III$",
                line,
                flags=re.IGNORECASE,
            ):

                heading_lines = [
                    line
                ]

                next_index = (
                    index + 1
                )

                while (
                    next_index < len(lines)
                    and not lines[
                        next_index
                    ].strip()
                ):
                    next_index += 1

                if next_index < len(lines):

                    next_line = lines[
                        next_index
                    ].strip()

                    if (
                        "PERSONAL ACCIDENT COVER"
                        in next_line.upper()
                    ):
                        heading_lines.append(
                            next_line
                        )

                        index = (
                            next_index + 1
                        )

                    else:
                        index += 1

                else:
                    index += 1

                if current_section:

                    sections.append(
                        current_section
                    )

                current_section = {
                    "heading": "\n".join(
                        heading_lines
                    ),
                    "content": [],
                    "start_page": page_number,
                    "end_page": page_number,
                    "pages": [],
                }

                continue

            # ------------------------------------------------
            # NORMAL MAJOR HEADING
            # ------------------------------------------------

            if is_major_heading(
                line
            ):

                if current_section:

                    sections.append(
                        current_section
                    )

                current_section = {
                    "heading": line,
                    "content": [],
                    "start_page": page_number,
                    "end_page": page_number,
                    "pages": [],
                }

                index += 1
                continue

            # ------------------------------------------------
            # CONTENT BEFORE FIRST MAJOR HEADING
            # ------------------------------------------------

            if current_section is None:

                current_section = {
                    "heading": "POLICY INTRODUCTION",
                    "content": [],
                    "start_page": page_number,
                    "end_page": page_number,
                    "pages": [],
                }

            current_section[
                "content"
            ].append(
                line
            )

            current_section[
                "end_page"
            ] = page_number

            index += 1

        # ----------------------------------------------------
        # Preserve page membership
        # ----------------------------------------------------

        if current_section is not None:

            existing_pages = {
                item["page_number"]
                for item in current_section[
                    "pages"
                ]
            }

            if page_number not in existing_pages:

                current_section[
                    "pages"
                ].append(
                    {
                        "page_number": page_number,
                        "text": page["text"],
                        "extraction_method": page.get(
                            "extraction_method",
                            "text",
                        ),
                    }
                )

    # --------------------------------------------------------
    # Close final section
    # --------------------------------------------------------

    if current_section:

        sections.append(
            current_section
        )

    # --------------------------------------------------------
    # Convert content lists to strings
    # --------------------------------------------------------

    for section in sections:

        section[
            "content"
        ] = "\n".join(
            section[
                "content"
            ]
        ).strip()

    return sections


# ============================================================
# TOP-LEVEL NUMBERED CLAUSES
# ============================================================

def split_numbered_clauses(
    text: str,
) -> list[str]:
    """
    Split a major section into top-level numbered clauses.

    Example:

        1. First clause
        2. Second clause
        3. Third clause

    creates three chunks.

    Lower-level markers such as:

        a.
        b.
        i.
        ii.

    remain inside their parent clause.
    """

    if not text or not text.strip():
        return []

    clause_pattern = re.compile(
        r"(?m)^\s*(?P<number>\d+)\.\s+"
    )

    matches = list(
        clause_pattern.finditer(
            text
        )
    )

    # No numbered clauses.
    if not matches:

        return [
            text.strip()
        ]

    clauses: list[str] = []

    # --------------------------------------------------------
    # Preamble before first numbered clause
    # --------------------------------------------------------

    preamble = text[
        :matches[0].start()
    ].strip()

    if preamble:

        clauses.append(
            preamble
        )

    # --------------------------------------------------------
    # Numbered clauses
    # --------------------------------------------------------

    for index, match in enumerate(
        matches
    ):

        start = match.start()

        if index + 1 < len(matches):

            end = matches[
                index + 1
            ].start()

        else:

            end = len(text)

        clause = text[
            start:end
        ].strip()

        if clause:

            clauses.append(
                clause
            )

    return clauses


# ============================================================
# PAGE MAPPING
# ============================================================

def find_chunk_page(
    chunk_text: str,
    section_pages: list[dict[str, Any]],
    fallback_page: int,
) -> int:
    """
    Determine the most likely source page for a chunk.

    The first meaningful portion of the chunk is searched
    against the pages belonging to its major section.

    If no match is found, the section's starting page is used.
    """

    normalized_chunk = re.sub(
        r"\s+",
        " ",
        chunk_text.strip(),
    )

    if not normalized_chunk:
        return fallback_page

    # Use enough text to reduce false matches while avoiding
    # problems caused by OCR/whitespace differences.
    search_text = normalized_chunk[
        :200
    ]

    for page in section_pages:

        normalized_page = re.sub(
            r"\s+",
            " ",
            page.get(
                "text",
                "",
            ).strip(),
        )

        if (
            search_text
            and search_text in normalized_page
        ):

            return int(
                page[
                    "page_number"
                ]
            )

    return fallback_page


# ============================================================
# STABLE CHUNK ID
# ============================================================

def build_chunk_id(
    doc_name: str,
    section_number: str,
    page_number: int,
    content: str,
) -> str:
    """
    Build a deterministic chunk identity.

    The database currently has its own BIGSERIAL ID.
    This stable ID is useful for application-level identity,
    deduplication, and retrieval fusion.
    """

    raw_identity = "|".join(
        [
            doc_name,
            section_number,
            str(page_number),
            content,
        ]
    )

    return hashlib.sha256(
        raw_identity.encode(
            "utf-8"
        )
    ).hexdigest()


# ============================================================
# SECTION-AWARE CHUNKING
# ============================================================

def section_aware_split(
    pages: list[dict[str, Any]],
    doc_name: str,
) -> list[dict[str, Any]]:
    """
    Create structurally meaningful chunks from page-aware text.

    Each chunk contains:

        chunk_id
        section_number
        section_title
        doc_name
        page_number
        content
        prompt_injection
        extraction_method
    """

    if not pages:
        return []

    if not doc_name:
        raise ValueError(
            "doc_name cannot be empty."
        )

    cleaned_pages = clean_document_pages(
        pages
    )

    if not cleaned_pages:
        return []

    sections = build_major_sections(
        cleaned_pages
    )

    chunks: list[dict[str, Any]] = []

    for section in sections:

        heading = section[
            "heading"
        ]

        section_content = section[
            "content"
        ]

        if not section_content.strip():
            continue

        section_pages = section[
            "pages"
        ]

        clauses = split_numbered_clauses(
            section_content
        )

        for clause in clauses:

            clause = clause.strip()

            if not clause:
                continue

            page_number = find_chunk_page(
                chunk_text=clause,
                section_pages=section_pages,
                fallback_page=section[
                    "start_page"
                ],
            )

            # Include the section heading inside the chunk.
            # This gives the embedding model important policy
            # context during retrieval.
            content = (
                f"{heading}\n\n"
                f"{clause}"
            ).strip()

            prompt_injection = (
                detect_prompt_injection(
                    content
                )
            )

            extraction_methods = [
                page.get(
                    "extraction_method",
                    "text",
                )
                for page in section_pages
                if page.get(
                    "page_number"
                ) == page_number
            ]

            extraction_method = (
                extraction_methods[0]
                if extraction_methods
                else "text"
            )

            chunk_id = build_chunk_id(
                doc_name=doc_name,
                section_number=heading,
                page_number=page_number,
                content=content,
            )

            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "section_number": heading,
                    "section_title": heading,
                    "doc_name": doc_name,
                    "page_number": page_number,
                    "content": content,
                    "prompt_injection": prompt_injection,
                    "extraction_method": extraction_method,
                }
            )

    return chunks


# ============================================================
# FIXED-SIZE CHUNKING
# ============================================================

def fixed_size_split(
    text: str,
    chunk_size: int = 200,
) -> list[str]:
    """
    Simple fixed-size chunking used only for experiments.

    It is NOT used by the production retrieval pipeline.
    """

    if chunk_size <= 0:

        raise ValueError(
            "chunk_size must be greater than 0."
        )

    if not text:
        return []

    return [
        text[
            index:index + chunk_size
        ]
        for index in range(
            0,
            len(text),
            chunk_size,
        )
    ]


# ============================================================
# DEVELOPMENT TEST
# ============================================================

if __name__ == "__main__":

    pdf_path = Path(
        "data/policy T&C.pdf"
    )

    # --------------------------------------------------------
    # PDF type
    # --------------------------------------------------------

    print(
        "\n=== PDF TYPE ==="
    )

    pdf_type = detect_pdf_type(
        pdf_path
    )

    print(
        f"PDF type: {pdf_type}"
    )

    # --------------------------------------------------------
    # Extract pages
    # --------------------------------------------------------

    print(
        "\n=== PAGE EXTRACTION ==="
    )

    pages = load_document_pages(
        pdf_path
    )

    print(
        f"Pages extracted: "
        f"{len(pages)}"
    )

    for page in pages:

        print(
            f"Page {page['page_number']}: "
            f"{len(page['text'])} characters "
            f"({page['extraction_method']})"
        )

    # --------------------------------------------------------
    # Section-aware chunks
    # --------------------------------------------------------

    print(
        "\n=== SECTION-AWARE CHUNKING ==="
    )

    chunks = section_aware_split(
        pages,
        "policy T&C.pdf",
    )

    print(
        f"Section-aware chunks: "
        f"{len(chunks)}"
    )

    # --------------------------------------------------------
    # Print chunks
    # --------------------------------------------------------

    for index, chunk in enumerate(
        chunks,
        start=1,
    ):

        print(
            f"\n--- Chunk {index} ---"
        )

        print(
            f"ID: "
            f"{chunk['chunk_id']}"
        )

        print(
            f"Page: "
            f"{chunk['page_number']}"
        )

        print(
            f"Section: "
            f"{chunk['section_number']}"
        )

        print(
            f"Extraction: "
            f"{chunk['extraction_method']}"
        )

        print(
            f"Prompt injection: "
            f"{chunk['prompt_injection']}"
        )

        print(
            chunk["content"]
        )

    # --------------------------------------------------------
    # Prompt injection test
    # --------------------------------------------------------

    print(
        "\n=== PROMPT INJECTION DETECTION ==="
    )

    injection_found = False

    for chunk in chunks:

        if chunk[
            "prompt_injection"
        ]:

            injection_found = True

            print(
                "\nPROMPT INJECTION DETECTED"
            )

            print(
                f"Page: "
                f"{chunk['page_number']}"
            )

            print(
                chunk["content"]
            )

    if not injection_found:

        print(
            "No prompt injection detected."
        )

    # --------------------------------------------------------
    # Fixed-size comparison
    # --------------------------------------------------------

    print(
        "\n=== FIXED-SIZE CHUNK TEST ==="
    )

    full_text = "\n\n".join(
        page["text"]
        for page in pages
    )

    fixed_chunks = fixed_size_split(
        full_text,
        chunk_size=200,
    )

    print(
        f"Fixed-size chunks: "
        f"{len(fixed_chunks)}"
    )