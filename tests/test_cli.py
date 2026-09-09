from pathlib import Path

from pypdf import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from pdf_split.cli import run


def test_cli_requires_existing_input_file(capsys):
    exit_code = run(["missing.pdf", "--pages", "100"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Input file does not exist" in captured.err


def test_cli_requires_one_split_mode(tmp_path, capsys):
    input_file = tmp_path / "input.pdf"
    input_file.write_bytes(b"%PDF-1.4\n")

    exit_code = run([str(input_file)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "one of the arguments --pages --split-on is required" in captured.err


def create_text_pdf(path: Path, page_texts: list[str]) -> None:
    pdf = canvas.Canvas(str(path), pagesize=letter)
    for text in page_texts:
        pdf.drawString(72, 720, text)
        pdf.showPage()
    pdf.save()


def page_count(path: Path) -> int:
    return len(PdfReader(path).pages)


def test_cli_splits_by_page_count(tmp_path, capsys):
    input_pdf = tmp_path / "large.pdf"
    output_dir = tmp_path / "out"
    create_text_pdf(input_pdf, ["one", "two", "three", "four", "five"])

    exit_code = run([str(input_pdf), "--pages", "2", "--out", str(output_dir)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Wrote 3 file(s)" in captured.out
    assert page_count(output_dir / "large_part_001.pdf") == 2
    assert page_count(output_dir / "large_part_002.pdf") == 2
    assert page_count(output_dir / "large_part_003.pdf") == 1


def test_cli_splits_by_text_marker(tmp_path):
    input_pdf = tmp_path / "customers.pdf"
    output_dir = tmp_path / "out"
    create_text_pdf(
        input_pdf,
        [
            "KUNDE A",
            "page A2",
            "KUNDE B",
            "page B2",
            "KUNDE C",
        ],
    )

    exit_code = run([str(input_pdf), "--split-on", "KUNDE", "--out", str(output_dir)])

    assert exit_code == 0
    assert page_count(output_dir / "customers_part_001.pdf") == 2
    assert page_count(output_dir / "customers_part_002.pdf") == 2
    assert page_count(output_dir / "customers_part_003.pdf") == 1


def test_cli_refuses_to_overwrite_existing_output(tmp_path, capsys):
    input_pdf = tmp_path / "input.pdf"
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    create_text_pdf(input_pdf, ["one", "two"])
    (output_dir / "input_part_001.pdf").write_bytes(b"existing")

    exit_code = run([str(input_pdf), "--pages", "2", "--out", str(output_dir)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Output file already exists" in captured.err


def test_cli_overwrites_existing_output_when_requested(tmp_path):
    input_pdf = tmp_path / "input.pdf"
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    create_text_pdf(input_pdf, ["one", "two"])
    (output_dir / "input_part_001.pdf").write_bytes(b"existing")

    exit_code = run(
        [str(input_pdf), "--pages", "2", "--out", str(output_dir), "--overwrite"]
    )

    assert exit_code == 0
    assert page_count(output_dir / "input_part_001.pdf") == 2
