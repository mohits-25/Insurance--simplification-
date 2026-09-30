"""
Document ingestion: PyMuPDF text extraction with Tesseract OCR fallback.
Preserves page numbers. Detects Text PDF vs Scanned PDF.
"""
import io
import os
import fitz  # PyMuPDF
import pytesseract
from PIL import Image

TESSERACT_PATH = os.getenv("TESSERACT_PATH", "/opt/homebrew/bin/tesseract")
if os.path.exists(TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

MIN_CHARS_PER_PAGE = 20  # below this, treat page as scanned/empty and try OCR


class IngestionResult:
    def __init__(self):
        self.pages: list[dict] = []  # [{page: int, text: str, ocr_used: bool}]
        self.full_text: str = ""
        self.document_type: str = "Text PDF"
        self.ocr_used: bool = False
        self.page_count: int = 0
        self.warnings: list[str] = []


def extract_document(file_bytes: bytes, filename: str) -> IngestionResult:
    result = IngestionResult()
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if ext in ("png", "jpg", "jpeg", "bmp", "tiff"):
        return _extract_image(file_bytes, result)

    if ext != "pdf":
        # try to open with fitz anyway; fitz can detect format issues
        pass

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        raise ValueError(f"Invalid or corrupted PDF file: {e}")

    if doc.page_count == 0:
        raise ValueError("PDF has no pages.")

    result.page_count = doc.page_count
    any_ocr = False

    for i in range(doc.page_count):
        page = doc.load_page(i)
        text = page.get_text("text").strip()

        page_ocr_used = False
        if len(text) < MIN_CHARS_PER_PAGE:
            # Likely scanned page -> render + OCR
            try:
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # upscale for OCR quality
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                ocr_text = pytesseract.image_to_string(img).strip()
                if len(ocr_text) > len(text):
                    text = ocr_text
                    page_ocr_used = True
                    any_ocr = True
            except Exception as e:
                result.warnings.append(f"OCR failed on page {i + 1}: {e}")

        result.pages.append({"page": i + 1, "text": text, "ocr_used": page_ocr_used})

    doc.close()

    result.ocr_used = any_ocr
    result.document_type = "Scanned PDF" if any_ocr else "Text PDF"

    total_chars = sum(len(p["text"]) for p in result.pages)
    if total_chars < MIN_CHARS_PER_PAGE:
        raise ValueError("No readable text could be extracted from this document (empty or unsupported PDF).")

    result.full_text = "\n\n".join(
        f"--- PAGE {p['page']} ---\n{p['text']}" for p in result.pages
    )
    return result


def _extract_image(file_bytes: bytes, result: IngestionResult) -> IngestionResult:
    try:
        img = Image.open(io.BytesIO(file_bytes))
        text = pytesseract.image_to_string(img).strip()
    except Exception as e:
        raise ValueError(f"OCR failed on uploaded image: {e}")

    if len(text) < MIN_CHARS_PER_PAGE:
        raise ValueError("No readable text could be extracted from this image.")

    result.page_count = 1
    result.ocr_used = True
    result.document_type = "Scanned Image"
    result.pages = [{"page": 1, "text": text, "ocr_used": True}]
    result.full_text = f"--- PAGE 1 ---\n{text}"
    return result
