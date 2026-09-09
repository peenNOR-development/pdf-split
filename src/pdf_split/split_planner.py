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
