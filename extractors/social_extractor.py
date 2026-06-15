"""Social media + Telegram + LinkedIn extraction."""
from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup


SOCIAL_PATTERNS = {
    "linkedin":  re.compile(r"https?://(?:[a-z]{2,3}\.)?linkedin\.com/(?:company|in|school)/[A-Za-z0-9_\-./%]+", re.I),
    "instagram": re.compile(r"https?://(?:www\.)?instagram\.com/[A-Za-z0-9_.]+/?", re.I),
    "facebook":  re.compile(r"https?://(?:www\.|web\.|m\.)?facebook\.com/[A-Za-z0-9_.\-]+/?", re.I),
    "twitter":   re.compile(r"https?://(?:www\.)?(?:twitter|x)\.com/[A-Za-z0-9_]{2,30}/?", re.I),
    "tiktok":    re.compile(r"https?://(?:www\.)?tiktok\.com/@[A-Za-z0-9_.]+/?", re.I),
    "youtube":   re.compile(r"https?://(?:www\.)?youtube\.com/(?:@|c/|channel/|user/)[A-Za-z0-9_\-]+/?", re.I),
    "telegram":  re.compile(r"https?://(?:www\.)?t\.me/[A-Za-z0-9_+]+", re.I),
}

BLOCKED_PATHS = {
    "facebook":  {"sharer.php", "sharer", "share.php", "dialog", "plugins", "tr"},
    "twitter":   {"intent", "share", "home"},
    "linkedin":  {"sharing", "shareArticle"},
    "instagram": {"sharer"},
}


def extract_social(html: str) -> dict[str, list[str]]:
    if not html:
        return {}
    out: dict[str, set[str]] = {k: set() for k in SOCIAL_PATTERNS}

    # 1) <a href="..."> based
    soup = BeautifulSoup(html, "lxml")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        for kind, rx in SOCIAL_PATTERNS.items():
            if rx.search(href):
                if _is_valid(kind, href):
                    out[kind].add(href.rstrip("/"))

    # 2) regex fallback on raw HTML (for JSON-LD, inline scripts)
    for kind, rx in SOCIAL_PATTERNS.items():
        for m in rx.finditer(html):
            url = m.group(0).rstrip("/")
            if _is_valid(kind, url):
                out[kind].add(url)

    return {k: sorted(v) for k, v in out.items() if v}


def _is_valid(kind: str, url: str) -> bool:
    try:
        p = urlparse(url)
    except Exception:
        return False
    path = p.path.strip("/").lower()
    if not path:
        return False
    if kind in BLOCKED_PATHS:
        first = path.split("/")[-1].split("?")[0]
        if first in BLOCKED_PATHS[kind]:
            return False
    return True
