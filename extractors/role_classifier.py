"""Map free-form role string → canonical role + priority bucket."""
from __future__ import annotations

from extractors.person_extractor import ROLE_KEYWORDS, ROLE_PRIORITY


def classify_role(text: str) -> tuple[str | None, int]:
    if not text:
        return None, 99
    low = text.lower()
    for canonical, kws in ROLE_KEYWORDS.items():
        if any(kw in low for kw in kws):
            return canonical, ROLE_PRIORITY.get(canonical, 50)
    return None, 99
