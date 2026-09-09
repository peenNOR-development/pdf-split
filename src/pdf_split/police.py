import re

POLICE_CODE_PATTERN = re.compile(r"\b\d{2}(?:,\d{2})*\b")


def detect_police_code(text: str | None) -> str | None:
    if text is None:
        return None

    match = POLICE_CODE_PATTERN.search(text)
    if match is None:
        return None
    return match.group(0)


def normalize_police_code(code: str, level: int) -> str:
    if level < 1:
        raise ValueError("police level must be >= 1")

    parts = code.split(",")
    if len(parts) < level:
        raise ValueError(f"Police document code {code} does not contain level {level}")

    return ",".join(parts[:level])


def police_code_to_filename_part(code: str) -> str:
    return code.replace(",", ".")
