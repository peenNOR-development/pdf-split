from pathlib import Path
from typing import Callable

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


def extract_top_right_page_texts(
    input_path: Path,
    progress_callback: Callable[[int, int], None] | None = None,
) -> list[str | None]:
    try:
        with pdfplumber.open(input_path) as pdf:
            texts: list[str | None] = []
            total_pages = len(pdf.pages)
            for page_number, page in enumerate(pdf.pages, start=1):
                x0, y0, x1, y1 = page.bbox
                width = x1 - x0
                height = y1 - y0
                top_right = page.crop(
                    (x0 + width * 0.65, y0, x1, y0 + height * 0.2)
                )
                red_text = _extract_red_text(top_right.chars)
                texts.append(red_text if red_text else top_right.extract_text())
                if progress_callback is not None:
                    progress_callback(page_number, total_pages)
            return texts
    except Exception as exc:
        raise PdfSplitError(_text_extraction_error(input_path, exc)) from exc


def _extract_red_text(chars: list[dict]) -> str | None:
    text = "".join(char.get("text", "") for char in chars if _is_red_char(char))
    return text or None


def _is_red_char(char: dict) -> bool:
    color = char.get("non_stroking_color")
    if not isinstance(color, (list, tuple)):
        return False

    try:
        values = tuple(float(value) for value in color)
    except (TypeError, ValueError):
        return False

    if len(values) == 3:
        red, green, blue = values
        return red >= 0.5 and green <= 0.35 and blue <= 0.35

    if len(values) == 4:
        cyan, magenta, yellow, black = values
        return cyan <= 0.35 and magenta >= 0.5 and yellow >= 0.5 and black <= 0.35

    return False


def _text_extraction_error(input_path: Path, exc: Exception) -> str:
    reason = f"{type(exc).__name__}: {exc}"
    return (
        f"Could not extract text from PDF: {input_path}. "
        f"Reason: {reason}. {TEXT_EXTRACTION_HINT}"
    )
