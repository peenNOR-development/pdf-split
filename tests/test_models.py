import pytest

from pdf_split.models import SplitInterval


def test_split_interval_rejects_negative_start():
    with pytest.raises(ValueError, match="start_page must be >= 0"):
        SplitInterval(start_page=-1, end_page_exclusive=2)


def test_split_interval_rejects_empty_interval():
    with pytest.raises(ValueError, match="end_page_exclusive must be greater than start_page"):
        SplitInterval(start_page=3, end_page_exclusive=3)


def test_split_interval_formats_user_range():
    interval = SplitInterval(start_page=0, end_page_exclusive=3)

    assert interval.to_user_range() == "pages 1-3"
