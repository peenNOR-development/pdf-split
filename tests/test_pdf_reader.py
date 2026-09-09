from pypdf import PdfWriter
import pytest

from pdf_split.errors import PdfSplitError
from pdf_split.pdf_reader import get_page_count


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
