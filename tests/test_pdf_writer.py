from pathlib import Path

import pytest
from pypdf import PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from pdf_split.errors import PdfSplitError
from pdf_split.models import SplitInterval
from pdf_split.pdf_writer import (
    build_output_paths,
    ensure_outputs_available,
    write_pdf_parts,
)


def create_text_pdf(path: Path, page_texts: list[str]) -> None:
    pdf = canvas.Canvas(str(path), pagesize=letter)
    for text in page_texts:
        pdf.drawString(72, 720, text)
        pdf.showPage()
    pdf.save()


def test_build_output_paths_uses_input_stem_and_padded_part_numbers(tmp_path):
    paths = build_output_paths(Path("stor_fil.pdf"), tmp_path, 3)

    assert paths == [
        tmp_path / "stor_fil_part_001.pdf",
        tmp_path / "stor_fil_part_002.pdf",
        tmp_path / "stor_fil_part_003.pdf",
    ]


def test_ensure_outputs_available_fails_when_file_exists_without_overwrite(tmp_path):
    output = tmp_path / "existing.pdf"
    output.write_bytes(b"already here")

    with pytest.raises(PdfSplitError, match="Output file already exists"):
        ensure_outputs_available([output], overwrite=False)


def test_ensure_outputs_available_allows_existing_file_with_overwrite(tmp_path):
    output = tmp_path / "existing.pdf"
    output.write_bytes(b"already here")

    ensure_outputs_available([output], overwrite=True)


def test_writer_refuses_destination_created_while_part_is_being_written(
    tmp_path, monkeypatch
):
    input_pdf = tmp_path / "input.pdf"
    output_pdf = tmp_path / "input_part_001.pdf"
    create_text_pdf(input_pdf, ["first page"])
    original_write = PdfWriter.write

    def write_then_create_destination(self, stream):
        original_write(self, stream)
        output_pdf.write_bytes(b"appeared during write")

    monkeypatch.setattr(PdfWriter, "write", write_then_create_destination)

    with pytest.raises(PdfSplitError, match="Output file already exists"):
        write_pdf_parts(
            input_pdf,
            [SplitInterval(0, 1)],
            [output_pdf],
            overwrite=False,
        )

    assert output_pdf.read_bytes() == b"appeared during write"
    assert list(tmp_path.glob(".input_part_001.pdf.*.tmp")) == []


def test_writer_preserves_overwritten_destination_when_temp_write_fails(
    tmp_path, monkeypatch
):
    input_pdf = tmp_path / "input.pdf"
    output_pdf = tmp_path / "input_part_001.pdf"
    create_text_pdf(input_pdf, ["first page"])
    output_pdf.write_bytes(b"existing destination")

    def fail_write(self, stream):
        raise OSError("disk full")

    monkeypatch.setattr(PdfWriter, "write", fail_write)

    with pytest.raises(OSError, match="disk full"):
        write_pdf_parts(
            input_pdf,
            [SplitInterval(0, 1)],
            [output_pdf],
            overwrite=True,
        )

    assert output_pdf.read_bytes() == b"existing destination"
    assert list(tmp_path.glob(".input_part_001.pdf.*.tmp")) == []
