import os
from pathlib import Path
import tempfile

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
    overwrite: bool,
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

        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix=f".{output_path.name}.",
                suffix=".tmp",
                dir=output_path.parent,
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                writer.write(temporary_file)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())

            if overwrite:
                os.replace(temporary_path, output_path)
            else:
                try:
                    os.link(temporary_path, output_path)
                except FileExistsError as exc:
                    raise PdfSplitError(f"Output file already exists: {output_path}") from exc
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
