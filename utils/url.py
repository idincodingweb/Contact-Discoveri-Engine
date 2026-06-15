"""URL helpers — normalization, dedupe, target-page classification."""
from __future__ import annotations

from urllib.parse import urljoin, urlparse, urlunparse

import tldextract


TARGET_KEYWORDS = (
    "about", "team", "staff", "leadership", "people", "management",
    "contact", "contact-us", "reach", "founders", "company", "who-we-are",
    "our-team", "meet", "executives",
)


def normalize(url: str) -> str:
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    p = urlparse(url)
    scheme = p.scheme or "https"
    netloc = p.netloc.lower().lstrip(".")
    path = (p.path or "/").rstrip("/") or "/"
    return urlunparse((scheme, netloc, path, "", p.query, ""))


def base_domain(url: str) -> str:
    ext = tldextract.extract(url)
    if not ext.suffix:
        return ""
    return f"{ext.domain}.{ext.suffix}".lower()


def same_site(a: str, b: str) -> bool:
    return base_domain(a) == base_domain(b)


def absolutize(base: str, href: str) -> str:
    try:
        return urljoin(base, href)
    except Exception:
        return ""


def is_target_page(url: str) -> bool:
    low = url.lower()
    return any(k in low for k in TARGET_KEYWORDS)


def priority_score(url: str) -> int:
    """Lower = more important to crawl first."""
    low = url.lower()
    if any(k in low for k in ("contact", "team", "leadership")):
        return 0
    if any(k in low for k in ("about", "staff", "people", "founders")):
        return 1
    if any(k in low for k in TARGET_KEYWORDS):
        return 2
    return 5
