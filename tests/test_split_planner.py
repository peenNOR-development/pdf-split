import pytest

from pdf_split.models import SplitInterval
from pdf_split.split_planner import (
    plan_marker_splits,
    plan_page_count_splits,
    plan_police_code_splits,
)


def test_page_count_splits_into_full_and_partial_parts():
    assert plan_page_count_splits(total_pages=250, pages_per_part=100) == [
        SplitInterval(0, 100),
        SplitInterval(100, 200),
        SplitInterval(200, 250),
    ]


def test_page_count_rejects_zero_pages_per_part():
    with pytest.raises(ValueError, match="pages_per_part must be >= 1"):
        plan_page_count_splits(total_pages=10, pages_per_part=0)


def test_page_count_rejects_empty_pdf():
    with pytest.raises(ValueError, match="total_pages must be >= 1"):
        plan_page_count_splits(total_pages=0, pages_per_part=10)


def test_marker_splits_start_matching_pages_after_page_one():
    assert plan_marker_splits(total_pages=100, matching_pages=[0, 42, 87]) == [
        SplitInterval(0, 42),
        SplitInterval(42, 87),
        SplitInterval(87, 100),
    ]


def test_marker_splits_whole_pdf_when_no_later_matches():
    assert plan_marker_splits(total_pages=5, matching_pages=[0]) == [
        SplitInterval(0, 5),
    ]


def test_marker_splits_support_consecutive_matches():
    assert plan_marker_splits(total_pages=5, matching_pages=[1, 2]) == [
        SplitInterval(0, 1),
        SplitInterval(1, 2),
        SplitInterval(2, 5),
    ]


def test_police_code_splits_when_selected_level_changes():
    intervals, codes = plan_police_code_splits(["01", "01", "02", "02"])

    assert intervals == [SplitInterval(0, 2), SplitInterval(2, 4)]
    assert codes == ["01", "02"]


def test_police_code_splits_consecutive_level_two_codes():
    intervals, codes = plan_police_code_splits(["01,01", "01,01", "01,02"])

    assert intervals == [SplitInterval(0, 2), SplitInterval(2, 3)]
    assert codes == ["01,01", "01,02"]


def test_police_code_splits_reject_first_page_without_code():
    with pytest.raises(ValueError, match="No police document code found on page 1"):
        plan_police_code_splits([None, "01"])


def test_police_code_splits_carries_missing_page_code_forward():
    intervals, codes = plan_police_code_splits(["01", None, "02"])

    assert intervals == [SplitInterval(0, 2), SplitInterval(2, 3)]
    assert codes == ["01", "02"]
