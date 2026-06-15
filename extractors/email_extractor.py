"""Email extraction — regex + obfuscation decoding + priority bucket."""
from __future__ import annotations

import re
from html import unescape

from bs4 import BeautifulSoup


EMAIL_RE = re.compile(
    r"(?i)\b([A-Z0-9._%+\-]+)\s*(?:@|\[at\]|\(at\)|\s+at\s+)\s*"
    r"([A-Z0-9.\-]+)\s*(?:\.|\[dot\]|\(dot\)|\s+dot\s+)\s*([A-Z]{2,24})\b"
)

PRIORITY_PREFIXES = (
    "founder", "ceo", "owner", "director", "hello",
    "info", "contact", "support", "sales", "press", "hi", "team",
)

ROLE_PREFIX_HINTS = {
    "founder": "Founder",
    "ceo": "CEO",
    "owner": "Owner",
    "director": "Director",
}


def extract_emails(html: str) -> list[str]:
    """Returns deduplicated lowercase emails found in HTML/text."""
    if not html:
        return []

    # 1) parse mailto:
    soup = BeautifulSoup(html, "lxml")
    mailto = {a["href"].split(":", 1)[1].split("?", 1)[0].strip().lower()
              for a in soup.select("a[href^='mailto:']") if a.get("href")}

    # 2) regex (incl. obfuscation)
    text = unescape(soup.get_text(" ", strip=True) + " " + html)
    found: set[str] = set(mailto)
    for m in EMAIL_RE.finditer(text):
        local, dom, tld = m.group(1), m.group(2), m.group(3)
        candidate = f"{local}@{dom}.{tld}".lower()
        if _looks_like_email(candidate):
            found.add(candidate)

    # 3) Filter junk
    cleaned = {e for e in found if _looks_like_email(e)}
    return sorted(cleaned, key=_email_priority)


def _looks_like_email(e: str) -> bool:
    if e.count("@") != 1:
        return False
    if any(x in e for x in (" ", ",", "\n", "..", "@.")):
        return False
    if e.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")):
        return False
    local, dom = e.split("@", 1)
    if not local or not dom or "." not in dom:
        return False
    if len(e) > 80:
        return False
    return True


def _email_priority(e: str) -> int:
    local = e.split("@", 1)[0]
    for i, p in enumerate(PRIORITY_PREFIXES):
        if local.startswith(p):
            return i
    return 99


def guess_role_from_email(email: str) -> str | None:
    local = email.split("@", 1)[0].lower()
    for k, v in ROLE_PREFIX_HINTS.items():
        if local.startswith(k):
            return v
    return None
