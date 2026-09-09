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
                rotation = getattr(page, "rotation", 0)
                page_red_text = _extract_red_text(
                    _visual_top_right_chars(
                        getattr(page, "chars", []),
                        page.bbox,
                        rotation,
                    ),
                    rotation,
                )
                if page_red_text:
                    texts.append(page_red_text)
                    if progress_callback is not None:
                        progress_callback(page_number, total_pages)
                    continue

                x0, y0, x1, y1 = page.bbox
                width = x1 - x0
                height = y1 - y0
                top_right = page.crop(
                    (x0 + width * 0.65, y0, x1, y0 + height * 0.2)
                )
                red_text = _extract_red_text(
                    top_right.chars,
                    getattr(top_right, "rotation", 0),
                )
                texts.append(red_text if red_text else top_right.extract_text())
                if progress_callback is not None:
                    progress_callback(page_number, total_pages)
            return texts
    except Exception as exc:
        raise PdfSplitError(_text_extraction_error(input_path, exc)) from exc


def _extract_red_text(chars: list[dict], rotation: int = 0) -> str | None:
    red_chars = [char for char in chars if _is_red_char(char)]
    lines = _group_chars_into_lines(red_chars, rotation)
    text = "\n".join(_line_text(line, rotation) for line in lines)
    return text or None


def _group_chars_into_lines(chars: list[dict], rotation: int) -> list[list[dict]]:
    lines: list[list[dict]] = []
    line_tolerance = 3.0
    rotation = rotation % 360
    line_axis = 0 if rotation in (90, 270) else 1

    for char in sorted(
        chars,
        key=lambda item: _line_order_value(item, rotation),
    ):
        center = _char_center(char)
        for line in lines:
            line_center = _char_center(line[0])
            if abs(center[line_axis] - line_center[line_axis]) <= line_tolerance:
                line.append(char)
                break
        else:
            lines.append([char])

    return lines


def _line_text(chars: list[dict], rotation: int) -> str:
    return "".join(
        char.get("text", "")
        for char in sorted(
            chars,
            key=lambda item: _char_order_value(item, rotation),
        )
    )


def _line_order_value(char: dict, rotation: int) -> float:
    x, y = _char_center(char)
    if rotation == 90:
        return -x
    if rotation == 180:
        return -y
    if rotation == 270:
        return x
    return y


def _char_order_value(char: dict, rotation: int) -> float:
    x, y = _char_center(char)
    if rotation == 90:
        return y
    if rotation == 180:
        return -x
    if rotation == 270:
        return -y
    return x


def _visual_top_right_chars(
    chars: list[dict],
    page_bbox: tuple[float, float, float, float],
    rotation: int,
) -> list[dict]:
    x0, y0, x1, y1 = page_bbox
    width = x1 - x0
    height = y1 - y0
    rotation = rotation % 360

    return [
        char
        for char in chars
        if _is_in_visual_top_right(
            _char_center(char),
            x0,
            y0,
            width,
            height,
            rotation,
        )
    ]


def _char_center(char: dict) -> tuple[float, float]:
    x_center = (float(char.get("x0", 0)) + float(char.get("x1", 0))) / 2
    y_center = (float(char.get("top", 0)) + float(char.get("bottom", 0))) / 2
    return x_center, y_center


def _is_in_visual_top_right(
    center: tuple[float, float],
    x0: float,
    y0: float,
    width: float,
    height: float,
    rotation: int,
) -> bool:
    x, y = center
    right = x >= x0 + width * 0.65
    left = x <= x0 + width * 0.35
    top = y <= y0 + height * 0.35
    bottom = y >= y0 + height * 0.65

    if rotation == 90:
        return right and bottom
    if rotation == 180:
        return left and bottom
    if rotation == 270:
        return left and top
    return right and top


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
