"""WhatsApp + phone number extraction."""
from __future__ import annotations

import re

import phonenumbers
from bs4 import BeautifulSoup


WA_LINK_RE = re.compile(
    r"https?://(?:api\.whatsapp\.com/send\?phone=|wa\.me/|chat\.whatsapp\.com/)([0-9+]+)",
    re.IGNORECASE,
)


def extract_whatsapp(html: str) -> list[str]:
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    found: set[str] = set()

    # 1) Explicit wa.me / api.whatsapp.com
    for a in soup.find_all("a", href=True):
        href = a["href"]
        m = WA_LINK_RE.search(href)
        if m:
            num = "+" + re.sub(r"\D", "", m.group(1))
            found.add(num)

    # 2) Free-text WhatsApp mention near phone numbers
    text = soup.get_text(" ", strip=True)
    for m in re.finditer(r"(?i)(whatsapp|wa)\s*[:\-]?\s*([+\d][\d \-().]{6,20}\d)", text):
        raw = m.group(2)
        digits = re.sub(r"\D", "", raw)
        if 8 <= len(digits) <= 15:
            found.add("+" + digits)

    return sorted(found)


def extract_phones(text: str, default_region: str | None = None) -> list[str]:
    if not text:
        return []
    out: set[str] = set()
    for m in phonenumbers.PhoneNumberMatcher(text, default_region or "US"):
        out.add(phonenumbers.format_number(m.number, phonenumbers.PhoneNumberFormat.E164))
    return sorted(out)
