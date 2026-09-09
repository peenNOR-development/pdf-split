from pathlib import Path

import pytest

from pdf_split.errors import PdfSplitError
from pdf_split.pdf_writer import build_output_paths, ensure_outputs_available


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
