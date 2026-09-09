from pdf_split.models import SplitInterval


def plan_page_count_splits(total_pages: int, pages_per_part: int) -> list[SplitInterval]:
    if total_pages < 1:
        raise ValueError("total_pages must be >= 1")
    if pages_per_part < 1:
        raise ValueError("pages_per_part must be >= 1")

    return [
        SplitInterval(start, min(start + pages_per_part, total_pages))
        for start in range(0, total_pages, pages_per_part)
    ]


def plan_marker_splits(total_pages: int, matching_pages: list[int]) -> list[SplitInterval]:
    if total_pages < 1:
        raise ValueError("total_pages must be >= 1")

    split_starts = [0]
    split_starts.extend(
        page for page in sorted(set(matching_pages)) if 0 < page < total_pages
    )

    intervals: list[SplitInterval] = []
    for index, start_page in enumerate(split_starts):
        end_page = split_starts[index + 1] if index + 1 < len(split_starts) else total_pages
        intervals.append(SplitInterval(start_page, end_page))
    return intervals


def plan_police_code_splits(
    page_codes: list[str | None],
) -> tuple[list[SplitInterval], list[str]]:
    if not page_codes:
        raise ValueError("total_pages must be >= 1")
    if page_codes[0] is None:
        raise ValueError("No police document code found on page 1")

    intervals: list[SplitInterval] = []
    interval_codes: list[str] = []
    current_code = page_codes[0]
    start_page = 0

    for page_index, page_code in enumerate(page_codes[1:], start=1):
        if page_code is None or page_code == current_code:
            continue

        intervals.append(SplitInterval(start_page, page_index))
        interval_codes.append(current_code)
        current_code = page_code
        start_page = page_index

    intervals.append(SplitInterval(start_page, len(page_codes)))
    interval_codes.append(current_code)
    return intervals, interval_codes
