import pytest

from pdf_split.police import detect_police_code, normalize_police_code


def test_detect_police_code_finds_first_hierarchical_code():
    assert detect_police_code("Sak 01,02,03 side 4") == "01,02,03"


def test_detect_police_code_returns_none_without_code():
    assert detect_police_code("Ingen kode her") is None


def test_normalize_police_code_keeps_requested_level():
    assert normalize_police_code("01,02,03", 1) == "01"
    assert normalize_police_code("01,02,03", 2) == "01,02"
    assert normalize_police_code("01,02,03", 3) == "01,02,03"


def test_normalize_police_code_rejects_missing_requested_level():
    with pytest.raises(ValueError, match="does not contain level 3"):
        normalize_police_code("01,02", 3)


def test_normalize_police_code_rejects_invalid_level():
    with pytest.raises(ValueError, match="police level must be >= 1"):
        normalize_police_code("01,02", 0)
