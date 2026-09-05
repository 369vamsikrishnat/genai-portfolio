# DAY 5 — OCR Pipeline

## Objective

Build an OCR-enabled ingestion pipeline that can handle both:

* Text-based PDFs
* Scanned/image-based PDFs

The pipeline should detect the PDF type and route it to the appropriate extraction method.

---

## Hour 1 — Study: `pytesseract`

### What is OCR?

OCR stands for **Optical Character Recognition**.

OCR converts text contained inside images into machine-readable text.

```text
Image
  ↓
OCR
  ↓
Text
```

### Tesseract vs `pytesseract`

**Tesseract** is the actual OCR engine responsible for recognizing characters from images.

**`pytesseract`** is the Python interface used to interact with the Tesseract OCR engine from Python.

```text
Python application
       ↓
  pytesseract
       ↓
   Tesseract
       ↓
     Text
```

---

## Hours 2–3 — Build OCR Pipeline

Created:

```text
src/ingestion/ocr.py
```

The module contains four functions:

```text
detect_pdf_type()
extract_text_pdf()
extract_scanned_pdf()
load_document()
```

### 1. `detect_pdf_type()`

Determines whether the PDF contains meaningful machine-readable text.

The detection process is:

```text
PDF
 ↓
PyMuPDF text extraction
 ↓
Check extracted text
 ↓
Meaningful text?
 ├── Yes → text PDF
 └── No  → scanned PDF
```

The implementation uses PyMuPDF and checks whether extracted text contains meaningful content.

---

### 2. `extract_text_pdf()`

Handles normal text-based PDFs.

```text
Text PDF
   ↓
PyMuPDF
   ↓
Extract page text
   ↓
Combine text
```

PyMuPDF is used directly because the PDF already contains machine-readable text.

---

### 3. `extract_scanned_pdf()`

Handles scanned PDFs.

The process is:

```text
Scanned PDF
    ↓
PyMuPDF
    ↓
Render PDF page as image
    ↓
PIL Image
    ↓
pytesseract
    ↓
Tesseract
    ↓
Extracted text
```

Each PDF page is rendered into an image and passed to Tesseract through `pytesseract`.

---

### 4. `load_document()`

Acts as the router for the ingestion pipeline.

```text
                    PDF
                     ↓
             detect_pdf_type()
                /          \
               /            \
            text           scanned
             ↓                ↓
     extract_text_pdf()  extract_scanned_pdf()
             \                /
              \              /
                   text
```

This allows the rest of the RAG pipeline to receive extracted text regardless of whether the source PDF was text-based or scanned.

---

## Test Document

Created a scanned test document by converting an image into a PDF.

The pipeline was tested using:

```text
data/synthetic_policies/text_policy.pdf
data/synthetic_policies/scanned_policy.pdf
```

---

## Testing

### Text PDF

The text PDF was correctly detected as:

```text
Text PDF type: text
```

The extracted content was readable:

```text
PROPERTY INSURANCE POLICY
Policy Number: POL-2026-001
Section 1: Property Coverage
Clause 1(a): Covered Property
...
```

### Scanned PDF

The scanned PDF was correctly detected as:

```text
Scanned PDF type: scanned
```

OCR successfully recovered readable text:

```text
PROPERTY INSURANCE POLICY
Policy Number: POL-2028-SCAN
Section 3: Claimsand Reporting
Clause 3a: Notice of Loss
...
```

### OCR imperfections observed

The OCR output contained some recognition/formatting errors, including:

```text
Claimsand → Claims and
3a → 3(a)
tot he → to the
assoon → as soon
unlesscircumstancesoutside → unless circumstances outside
```

This demonstrates an important property of OCR:

> OCR can recover text from scanned documents, but the resulting text may contain recognition errors.

---

# Day 5 Checkpoint

## 1. Explain scanned-vs-text detection

We first use PyMuPDF to extract text from the PDF.

If meaningful text is present, the document is treated as a **text PDF** and normal PyMuPDF extraction is used.

If little or no text is extracted, the document is treated as a **scanned PDF** and its pages are sent through the OCR pipeline.

```text
PDF
 ↓
PyMuPDF extraction
 ↓
Meaningful text?
 ├── Yes → Text extraction
 └── No  → OCR
```

## 2. Three OCR failure modes

Three common OCR failure modes are:

1. **Poor image quality** — blurry, noisy, or low-resolution scans can cause incorrect recognition.
2. **Handwriting** — handwritten text can be difficult for OCR to recognize accurately.
3. **Complex layouts** — tables, columns, forms, and unusual layouts can lead to incorrect text ordering or recognition.

---

# Key Takeaways

* OCR is required when a PDF contains images instead of machine-readable text.
* Tesseract is the OCR engine.
* `pytesseract` provides the Python interface to Tesseract.
* PyMuPDF handles normal text-based PDF extraction.
* The ingestion pipeline first determines the PDF type.
* Scanned pages are rendered as images before being passed to Tesseract.
* OCR output is not guaranteed to be perfect.
* OCR errors can propagate into downstream RAG retrieval quality.

---

## Day 5 Status

**Status: COMPLETE ✅**

```text
PDF
 ↓
Detect type
 ↓
 ┌──────────────────┐
 │                  │
Text              Scanned
 │                  │
 ↓                  ↓
PyMuPDF          Tesseract OCR
 │                  │
 └────────┬─────────┘
          ↓
     Extracted text
```

