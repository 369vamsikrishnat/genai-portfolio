from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pymupdf
import pytesseract
from PIL import Image


# ============================================================
# CONFIGURATION
# ============================================================

TESSERACT_CMD = os.getenv(
    "TESSERACT_CMD",
    "",
)

OCR_DPI = int(
    os.getenv("OCR_DPI", "200")
)

MIN_EXTRACTED_TEXT_CHARS = int(
    os.getenv("MIN_EXTRACTED_TEXT_CHARS", "20")
)


# Configure Tesseract only when an explicit executable path
# is provided.
#
# Windows:
# TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
#
# Linux/Docker:
# Leave this empty when tesseract is available on PATH.
#
if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD


# ============================================================
# PATH VALIDATION
# ============================================================

def validate_document_path(
    document_path: str | Path,
) -> Path:
    """
    Validate that the supplied document exists and is a PDF.
    """

    path = Path(
        document_path
    )

    if not path.exists():
        raise FileNotFoundError(
            f"Document not found: {path}"
        )

    if not path.is_file():
        raise ValueError(
            f"Document path is not a file: {path}"
        )

    if path.suffix.lower() != ".pdf":
        raise ValueError(
            f"Expected a PDF file, got: {path}"
        )

    return path


# ============================================================
# TEXT EXTRACTION
# ============================================================

def extract_text_from_page(
    page: pymupdf.Page,
) -> str:
    """
    Extract machine-readable text from one PDF page.
    """

    return page.get_text(
        "text"
    ).strip()


# ============================================================
# OCR
# ============================================================

def ocr_page(
    page: pymupdf.Page,
) -> str:
    """
    Render one PDF page and extract text using Tesseract OCR.
    """

    matrix = pymupdf.Matrix(
        OCR_DPI / 72,
        OCR_DPI / 72,
    )

    pixmap = page.get_pixmap(
        matrix=matrix,
        alpha=False,
    )

    image = Image.frombytes(
        "RGB",
        (
            pixmap.width,
            pixmap.height,
        ),
        pixmap.samples,
    )

    return pytesseract.image_to_string(
        image
    ).strip()


# ============================================================
# PAGE-AWARE DOCUMENT LOADING
# ============================================================

def load_document_pages(
    document_path: str | Path,
) -> list[dict[str, Any]]:
    """
    Load a PDF page-by-page.

    Each page is first checked for machine-readable text.
    If insufficient text is available, OCR is used for that
    specific page.

    This supports:

    - normal text PDFs
    - scanned PDFs
    - mixed PDFs

    Returns:

        [
            {
                "page_number": 1,
                "text": "...",
                "extraction_method": "text",
            },
            {
                "page_number": 2,
                "text": "...",
                "extraction_method": "ocr",
            },
        ]
    """

    path = validate_document_path(
        document_path
    )

    pages: list[dict[str, Any]] = []

    with pymupdf.open(path) as document:

        for page_number, page in enumerate(
            document,
            start=1,
        ):

            text = extract_text_from_page(
                page
            )

            if (
                len(text)
                >= MIN_EXTRACTED_TEXT_CHARS
            ):
                pages.append(
                    {
                        "page_number": page_number,
                        "text": text,
                        "extraction_method": "text",
                    }
                )
                continue

            ocr_text = ocr_page(
                page
            )

            if ocr_text:
                pages.append(
                    {
                        "page_number": page_number,
                        "text": ocr_text,
                        "extraction_method": "ocr",
                    }
                )

    return pages


# ============================================================
# PDF TYPE DETECTION
# ============================================================

def detect_pdf_type(
    document_path: str | Path,
) -> str:
    """
    Determine the dominant extraction type of a PDF.

    Returns:

        "text"
        "scanned"
        "mixed"

    This function is diagnostic only.

    Actual extraction is always handled page-by-page by
    load_document_pages().
    """

    pages = load_document_pages(
        document_path
    )

    if not pages:
        return "scanned"

    text_pages = sum(
        page.get("extraction_method") == "text"
        for page in pages
    )

    ocr_pages = sum(
        page.get("extraction_method") == "ocr"
        for page in pages
    )

    if text_pages > 0 and ocr_pages == 0:
        return "text"

    if ocr_pages > 0 and text_pages == 0:
        return "scanned"

    return "mixed"


# ============================================================
# LEGACY-COMPATIBLE HELPERS
# ============================================================

def extract_text_pdf(
    document_path: str | Path,
) -> str:
    """
    Extract all machine-readable text from a PDF.

    This helper is kept for compatibility with older scripts.

    The production pipeline should use load_document_pages()
    because page metadata is required for citations.
    """

    path = validate_document_path(
        document_path
    )

    pages: list[str] = []

    with pymupdf.open(path) as document:

        for page in document:
            text = extract_text_from_page(
                page
            )

            if text:
                pages.append(
                    text
                )

    return "\n".join(
        pages
    )


def extract_scanned_pdf(
    document_path: str | Path,
) -> str:
    """
    OCR every page of a PDF and return the combined text.

    This helper is retained for compatibility.

    The production pipeline should use load_document_pages().
    """

    path = validate_document_path(
        document_path
    )

    pages: list[str] = []

    with pymupdf.open(path) as document:

        for page in document:

            text = ocr_page(
                page
            )

            if text:
                pages.append(
                    text
                )

    return "\n".join(
        pages
    )


def load_document(
    document_path: str | Path,
) -> str:
    """
    Load a document and return combined text.

    Compatibility helper for older code.

    New ingestion code should use:

        load_document_pages()

    because combined text loses page-level provenance.
    """

    pages = load_document_pages(
        document_path
    )

    return "\n".join(
        page["text"]
        for page in pages
    )


# ============================================================
# DEVELOPMENT TEST
# ============================================================

if __name__ == "__main__":

    pdf_path = Path(
        "data/policy T&C.pdf"
    )

    print(
        "=== PDF TYPE ==="
    )

    pdf_type = detect_pdf_type(
        pdf_path
    )

    print(
        f"Detected PDF type: {pdf_type}"
    )

    print(
        "\n=== PAGE EXTRACTION ==="
    )

    pages = load_document_pages(
        pdf_path
    )

    print(
        f"Pages extracted: {len(pages)}"
    )

    for page in pages:

        print(
            f"\nPage {page['page_number']}"
        )

        print(
            f"Method: "
            f"{page['extraction_method']}"
        )

        print(
            f"Characters: "
            f"{len(page['text'])}"
        )

        print(
            page["text"][:500]
        )

    print(
        "\n=== COMBINED TEXT COMPATIBILITY TEST ==="
    )

    text = load_document(
        pdf_path
    )

    print(
        text[:1000]
    )