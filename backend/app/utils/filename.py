import re


def sanitize_title(value: str) -> str:
    value = re.sub(r"[^\w\s.-]", "", value).strip()
    value = re.sub(r"\s+", " ", value)
    return value[:255] or "Untitled Notes"

