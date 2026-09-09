from pdf_split.matcher import literal_page_matches


def test_literal_page_matches_substring():
    assert literal_page_matches("Faktura KUNDE 123", "KUNDE") is True


def test_literal_page_match_is_case_sensitive():
    assert literal_page_matches("Faktura kunde 123", "KUNDE") is False


def test_literal_page_match_treats_none_as_no_text():
    assert literal_page_matches(None, "KUNDE") is False
