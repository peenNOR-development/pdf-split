def literal_page_matches(text: str | None, marker: str) -> bool:
    if text is None:
        return False
    return marker in text
