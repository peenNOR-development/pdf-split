from pathlib import Path

import pdfplumber
from pypdf import PdfReader

from pdf_split.errors import PdfSplitError


TEXT_EXTRACTION_HINT = (
    "This can happen when the PDF is locked/password-protected, malformed/corrupt, "
    "or when its text structure cannot be interpreted by pdfplumber. If the PDF is "
    "a scanned image, OCR is required and is not supported by this tool yet."
)


def get_page_count(input_path: Path) -> int:
    try:
        reader = PdfReader(input_path)
        if reader.is_encrypted:
            raise PdfSplitError("Encrypted or password-protected PDFs are not supported.")
        return len(reader.pages)
    except PdfSplitError:
        raise
    except Exception as exc:
        raise PdfSplitError(f"Could not read PDF: {input_path}") from exc


def extract_page_texts(input_path: Path) -> list[str | None]:
    try:
        with pdfplumber.open(input_path) as pdf:
            return [page.extract_text() for page in pdf.pages]
    except Exception as exc:
        raise PdfSplitError(_text_extraction_error(input_path, exc)) from exc


def extract_top_right_page_texts(input_path: Path) -> list[str | None]:
    try:
        with pdfplumber.open(input_path) as pdf:
            texts: list[str | None] = []
            for page in pdf.pages:
                x0, y0, x1, y1 = page.bbox
                width = x1 - x0
                height = y1 - y0
                top_right = page.crop(
                    (x0 + width * 0.65, y0, x1, y0 + height * 0.2)
                )
                texts.append(top_right.extract_text())
            return texts
    except Exception as exc:
        raise PdfSplitError(_text_extraction_error(input_path, exc)) from exc


def _text_extraction_error(input_path: Path, exc: Exception) -> str:
    reason = f"{type(exc).__name__}: {exc}"
    return (
        f"Could not extract text from PDF: {input_path}. "
        f"Reason: {reason}. {TEXT_EXTRACTION_HINT}"
    )
