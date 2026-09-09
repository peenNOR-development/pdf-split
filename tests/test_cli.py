import logging
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from pdf_split.cli import configure_pdf_logging, run


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
    assert (
        "one of the arguments --pages --split-on --police-level is required"
        in captured.err
    )


def create_text_pdf(path: Path, page_texts: list[str]) -> None:
    pdf = canvas.Canvas(str(path), pagesize=letter)
    for text in page_texts:
        pdf.drawString(72, 720, text)
        pdf.showPage()
    pdf.save()


def create_police_pdf(path: Path, pages: list[tuple[str, str]]) -> None:
    pdf = canvas.Canvas(str(path), pagesize=letter)
    for code, body in pages:
        pdf.setFillColorRGB(1, 0, 0)
        pdf.drawRightString(560, 760, code)
        pdf.setFillColorRGB(0, 0, 0)
        pdf.drawString(72, 720, body)
        pdf.showPage()
    pdf.save()


def create_police_pdf_with_black_top_right_codes(
    path: Path,
    pages: list[tuple[str, str, str]],
) -> None:
    pdf = canvas.Canvas(str(path), pagesize=letter)
    for red_code, black_code, body in pages:
        pdf.setFillColorRGB(0, 0, 0)
        pdf.drawRightString(560, 770, black_code)
        pdf.setFillColorRGB(1, 0, 0)
        pdf.drawRightString(560, 745, red_code)
        pdf.setFillColorRGB(0, 0, 0)
        pdf.drawString(72, 720, body)
        pdf.showPage()
    pdf.save()


def create_police_pdf_with_double_red_codes(
    path: Path,
    pages: list[tuple[str, str, str]],
) -> None:
    pdf = canvas.Canvas(str(path), pagesize=letter)
    for primary_code, secondary_code, body in pages:
        pdf.setFillColorRGB(1, 0, 0)
        pdf.drawRightString(560, 735, secondary_code)
        pdf.drawRightString(560, 760, primary_code)
        pdf.setFillColorRGB(0, 0, 0)
        pdf.drawString(72, 720, body)
        pdf.showPage()
    pdf.save()


def create_rotated_police_pdf(path: Path, pages: list[tuple[str, str]]) -> None:
    source_path = path.with_name(f"{path.stem}_source.pdf")
    pdf = canvas.Canvas(str(source_path), pagesize=letter)
    for code, body in pages:
        pdf.setFillColorRGB(1, 0, 0)
        pdf.drawRightString(560, 760, code)
        pdf.setFillColorRGB(0, 0, 0)
        pdf.drawString(72, 720, body)
        pdf.showPage()
    pdf.save()

    reader = PdfReader(source_path)
    writer = PdfWriter()
    for page in reader.pages:
        page.rotate(90)
        writer.add_page(page)
    with path.open("wb") as output_file:
        writer.write(output_file)


def page_count(path: Path) -> int:
    return len(PdfReader(path).pages)


def page_texts(path: Path) -> list[str]:
    return [page.extract_text().strip() for page in PdfReader(path).pages]


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
    assert page_texts(output_dir / "large_part_001.pdf") == ["one", "two"]
    assert page_texts(output_dir / "large_part_002.pdf") == ["three", "four"]
    assert page_texts(output_dir / "large_part_003.pdf") == ["five"]


def test_cli_verbose_reports_wide_hash_progress(tmp_path, capsys):
    input_pdf = tmp_path / "large.pdf"
    output_dir = tmp_path / "out"
    create_text_pdf(input_pdf, ["one", "two", "three", "four", "five"])

    exit_code = run(
        [str(input_pdf), "--pages", "2", "--out", str(output_dir), "--verbose"]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert (
        "\r[#############---------------------------] 33% Writing part 1/3"
        in captured.err
    )
    assert (
        "\r[###########################-------------] 67% Writing part 2/3"
        in captured.err
    )
    assert "\r[########################################] 100% Done\n" in captured.err


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
    assert page_texts(output_dir / "customers_part_001.pdf") == ["KUNDE A", "page A2"]
    assert page_texts(output_dir / "customers_part_002.pdf") == ["KUNDE B", "page B2"]
    assert page_texts(output_dir / "customers_part_003.pdf") == ["KUNDE C"]


def test_cli_splits_police_documents_by_level_two(tmp_path):
    input_pdf = tmp_path / "police.pdf"
    output_dir = tmp_path / "out"
    create_police_pdf(
        input_pdf,
        [
            ("01,01", "first"),
            ("01,01,01", "child"),
            ("01,02", "second"),
            ("01,02,01", "second child"),
            ("02,01", "third"),
        ],
    )

    exit_code = run([str(input_pdf), "--police-level", "2", "--out", str(output_dir)])

    assert exit_code == 0
    assert page_count(output_dir / "police_01.01.pdf") == 2
    assert page_count(output_dir / "police_01.02.pdf") == 2
    assert page_count(output_dir / "police_02.01.pdf") == 1
    assert page_texts(output_dir / "police_01.01.pdf") == ["01,01\nfirst", "01,01,01\nchild"]
    assert page_texts(output_dir / "police_01.02.pdf") == [
        "01,02\nsecond",
        "01,02,01\nsecond child",
    ]
    assert page_texts(output_dir / "police_02.01.pdf") == ["02,01\nthird"]


def test_cli_police_mode_prefers_red_document_codes(tmp_path):
    input_pdf = tmp_path / "police.pdf"
    output_dir = tmp_path / "out"
    create_police_pdf_with_black_top_right_codes(
        input_pdf,
        [
            ("01,01", "99,99", "first"),
            ("01,02", "98,99", "same top-level case"),
            ("02,01", "97,99", "new top-level case"),
        ],
    )

    exit_code = run([str(input_pdf), "--police-level", "1", "--out", str(output_dir)])

    assert exit_code == 0
    assert sorted(path.name for path in output_dir.iterdir()) == [
        "police_01.pdf",
        "police_02.pdf",
    ]
    assert page_count(output_dir / "police_01.pdf") == 2
    assert page_count(output_dir / "police_02.pdf") == 1


def test_cli_police_mode_handles_rotated_landscape_pages(tmp_path):
    input_pdf = tmp_path / "police.pdf"
    output_dir = tmp_path / "out"
    create_rotated_police_pdf(
        input_pdf,
        [
            ("01,01", "first"),
            ("01,02", "same top-level case"),
            ("02,01", "new top-level case"),
        ],
    )

    exit_code = run([str(input_pdf), "--police-level", "1", "--out", str(output_dir)])

    assert exit_code == 0
    assert sorted(path.name for path in output_dir.iterdir()) == [
        "police_01.pdf",
        "police_02.pdf",
    ]
    assert page_count(output_dir / "police_01.pdf") == 2
    assert page_count(output_dir / "police_02.pdf") == 1


def test_cli_police_mode_uses_top_red_code_when_multiple_red_codes(tmp_path):
    input_pdf = tmp_path / "police.pdf"
    output_dir = tmp_path / "out"
    create_police_pdf_with_double_red_codes(
        input_pdf,
        [
            ("08,14,02", "10,01,01,04", "first"),
            ("08,14,03", "10,01,01,05", "same level two"),
            ("09,01,01", "10,01,01,06", "next level two"),
        ],
    )

    exit_code = run([str(input_pdf), "--police-level", "2", "--out", str(output_dir)])

    assert exit_code == 0
    assert sorted(path.name for path in output_dir.iterdir()) == [
        "police_08.14.pdf",
        "police_09.01.pdf",
    ]
    assert page_count(output_dir / "police_08.14.pdf") == 2
    assert page_count(output_dir / "police_09.01.pdf") == 1


def test_cli_verbose_explains_police_code_analysis(tmp_path, capsys):
    input_pdf = tmp_path / "police.pdf"
    output_dir = tmp_path / "out"
    create_police_pdf(input_pdf, [("01", "first"), ("02", "second")])

    exit_code = run(
        [str(input_pdf), "--police-level", "1", "--out", str(output_dir), "--verbose"]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert (
        "Analyzing police document codes in the upper-right page area..."
        in captured.err
    )
    assert (
        "\r[####################--------------------] 50% Analyzing page 1/2"
        in captured.err
    )
    assert "\r[########################################] 100% Analysis done\n" in captured.err
    assert "Detected 2 coded page(s) and 2 output group(s)." in captured.err


def test_configure_pdf_logging_suppresses_pdfminer_warnings():
    pdfminer_logger = logging.getLogger("pdfminer")
    previous_level = pdfminer_logger.level
    try:
        pdfminer_logger.setLevel(logging.WARNING)

        configure_pdf_logging()

        assert pdfminer_logger.level == logging.ERROR
    finally:
        pdfminer_logger.setLevel(previous_level)


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


def test_cli_reports_output_directory_creation_failure(tmp_path, capsys):
    input_pdf = tmp_path / "input.pdf"
    output_file = tmp_path / "out"
    create_text_pdf(input_pdf, ["one"])
    output_file.write_text("not a directory")

    exit_code = run([str(input_pdf), "--pages", "1", "--out", str(output_file)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Could not create output directory" in captured.err
    assert str(output_file) in captured.err


def test_cli_reports_output_write_failure(tmp_path, capsys, monkeypatch):
    input_pdf = tmp_path / "input.pdf"
    create_text_pdf(input_pdf, ["one"])

    def fail_write(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("pdf_split.cli.write_pdf_parts", fail_write)

    exit_code = run([str(input_pdf), "--pages", "1", "--out", str(tmp_path / "out")])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Could not write output files" in captured.err
    assert "disk full" in captured.err


def test_cli_rejects_encrypted_input(tmp_path, capsys):
    input_pdf = tmp_path / "encrypted.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=letter[0], height=letter[1])
    writer.encrypt("secret")
    with input_pdf.open("wb") as output_file:
        writer.write(output_file)

    exit_code = run([str(input_pdf), "--pages", "1", "--out", str(tmp_path / "out")])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Encrypted or password-protected PDFs are not supported" in captured.err
