from pathlib import Path

import pdfplumber
from pypdf import PdfReader

from pdf_split.errors import PdfSplitError


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
        raise PdfSplitError(f"Could not extract text from PDF: {input_path}") from exc


def extract_top_right_page_texts(input_path: Path) -> list[str | None]:
    try:
        with pdfplumber.open(input_path) as pdf:
            texts: list[str | None] = []
            for page in pdf.pages:
                top_right = page.crop(
                    (page.width * 0.65, 0, page.width, page.height * 0.2)
                )
                texts.append(top_right.extract_text())
            return texts
    except Exception as exc:
        raise PdfSplitError(f"Could not extract text from PDF: {input_path}") from exc
