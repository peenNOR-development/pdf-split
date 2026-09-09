from pathlib import Path

from pypdf import PdfReader, PdfWriter

from pdf_split.errors import PdfSplitError
from pdf_split.models import SplitInterval


def build_output_paths(input_path: Path, output_dir: Path, part_count: int) -> list[Path]:
    return [
        output_dir / f"{input_path.stem}_part_{part_number:03d}.pdf"
        for part_number in range(1, part_count + 1)
    ]


def ensure_outputs_available(paths: list[Path], overwrite: bool) -> None:
    if overwrite:
        return

    existing_paths = [path for path in paths if path.exists()]
    if existing_paths:
        raise PdfSplitError(f"Output file already exists: {existing_paths[0]}")


def write_pdf_parts(
    input_path: Path,
    intervals: list[SplitInterval],
    output_paths: list[Path],
) -> None:
    if len(intervals) != len(output_paths):
        raise ValueError("intervals and output_paths must have the same length")

    reader = PdfReader(input_path)
    if reader.is_encrypted:
        raise PdfSplitError("Encrypted or password-protected PDFs are not supported.")

    for interval, output_path in zip(intervals, output_paths, strict=True):
        writer = PdfWriter()
        for page_index in range(interval.start_page, interval.end_page_exclusive):
            writer.add_page(reader.pages[page_index])

        with output_path.open("wb") as output_file:
            writer.write(output_file)
