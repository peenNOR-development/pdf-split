from pypdf import PdfWriter
import pytest

from pdf_split.errors import PdfSplitError
from pdf_split.pdf_reader import extract_page_texts, get_page_count


def test_get_page_count_translates_malformed_page_tree_errors(tmp_path):
    malformed_pdf = tmp_path / "malformed-page-tree.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(malformed_pdf)
    valid_bytes = malformed_pdf.read_bytes()
    malformed_bytes = valid_bytes.replace(
        b"/Kids [ 4 0 R ]", b"/Kids  4 0 R  ", 1
    )
    assert malformed_bytes != valid_bytes
    malformed_pdf.write_bytes(malformed_bytes)

    with pytest.raises(PdfSplitError, match="Could not read PDF"):
        get_page_count(malformed_pdf)


def test_extract_page_texts_includes_underlying_failure_and_hints(
    tmp_path,
    monkeypatch,
):
    input_pdf = tmp_path / "problem.pdf"
    input_pdf.write_bytes(b"%PDF-1.4\n")

    def fail_open(_path):
        raise ValueError("document has no /Root object")

    monkeypatch.setattr("pdf_split.pdf_reader.pdfplumber.open", fail_open)

    with pytest.raises(PdfSplitError) as exc_info:
        extract_page_texts(input_pdf)

    message = str(exc_info.value)
    assert f"Could not extract text from PDF: {input_pdf}" in message
    assert "Reason: ValueError: document has no /Root object" in message
    assert "locked/password-protected, malformed/corrupt" in message
