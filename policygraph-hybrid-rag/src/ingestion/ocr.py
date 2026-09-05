import pymupdf
import pytesseract
from PIL import Image
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


def detect_pdf_type(pdf_path):
    doc = pymupdf.open(pdf_path)

    total_text = ""

    for page in doc:
        total_text += page.get_text()

    doc.close()

    if total_text.strip():
        return "text"

    return "scanned"


def extract_text_pdf(pdf_path):
    doc = pymupdf.open(pdf_path)

    pages = []

    for page in doc:
        text = page.get_text()

        if text.strip():
            pages.append(text)

    doc.close()

    return "\n".join(pages)


def extract_scanned_pdf(pdf_path):
    doc = pymupdf.open(pdf_path)

    pages = []

    for page in doc:
        pixmap = page.get_pixmap()

        image = Image.frombytes(
            "RGB",
            [pixmap.width, pixmap.height],
            pixmap.samples
        )

        text = pytesseract.image_to_string(image)

        if text.strip():
            pages.append(text)

    doc.close()

    return "\n".join(pages)


def load_document(pdf_path):
    pdf_type = detect_pdf_type(pdf_path)

    if pdf_type == "text":
        return extract_text_pdf(pdf_path)

    return extract_scanned_pdf(pdf_path)

if __name__ == "__main__":
    text_pdf = "data/synthetic_policies/text_policy.pdf"
    scanned_pdf = "data/synthetic_policies/scanned_policy.pdf"

    print("Text PDF type:", detect_pdf_type(text_pdf))
    print("Scanned PDF type:", detect_pdf_type(scanned_pdf))

# if __name__ == "__main__":
#     text_pdf = "data/synthetic_policies/text_policy.pdf"
#     scanned_pdf = "data/synthetic_policies/scanned_policy.pdf"

#     print("\n=== TEXT PDF ===")
#     text_result = load_document(text_pdf)
#     print(text_result[:500])

#     print("\n=== SCANNED PDF ===")
#     scanned_result = load_document(scanned_pdf)
#     print(scanned_result[:500])
