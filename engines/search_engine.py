"""Discover candidate websites from a keyword via Bing / DuckDuckGo HTML SERP."""
from __future__ import annotations

import logging
import re
from urllib.parse import quote_plus, urlparse

from bs4 import BeautifulSoup

from utils.http import HttpClient
from utils.url import base_domain

log = logging.getLogger(__name__)

BING_URL = "https://www.bing.com/search?q={q}&count=30&setlang=en"
DDG_URL = "https://html.duckduckgo.com/html/?q={q}"

SOCIAL_EXCLUDE = {
    "facebook.com", "instagram.com", "twitter.com", "x.com",
    "linkedin.com", "youtube.com", "tiktok.com", "pinterest.com",
    "yelp.com", "tripadvisor.com", "reddit.com", "quora.com",
    "wikipedia.org", "amazon.com", "bing.com", "google.com",
    "duckduckgo.com",
}


def _clean(url: str) -> str:
    if not url:
        return ""
    url = re.sub(r"^https?://[^/]+/url\?q=", "", url)
    url = url.split("&")[0]
    return url


async def search_keyword(client: HttpClient, keyword: str, country: str = "",
                         max_results: int = 20) -> list[str]:
    query = keyword if not country else f"{keyword} {country}"
    domains: list[str] = []
    seen: set[str] = set()

    # 1) Bing
    bing_html = (await client.fetch(BING_URL.format(q=quote_plus(query)))).text
    domains += _parse_bing(bing_html)

    # 2) DuckDuckGo fallback
    if len(domains) < max_results:
        ddg_html = (await client.fetch(DDG_URL.format(q=quote_plus(query)))).text
        domains += _parse_ddg(ddg_html)

    result: list[str] = []
    for d in domains:
        bd = base_domain(d)
        if not bd or bd in SOCIAL_EXCLUDE or bd in seen:
            continue
        seen.add(bd)
        result.append(f"https://{bd}")
        if len(result) >= max_results:
            break

    log.info("SERP found %d domains for query=%r", len(result), query)
    return result


def _parse_bing(html: str) -> list[str]:
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    out: list[str] = []
    for a in soup.select("li.b_algo h2 a, li.b_algo a"):
        href = _clean(a.get("href") or "")
        if href.startswith("http"):
            out.append(href)
    return out


def _parse_ddg(html: str) -> list[str]:
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    out: list[str] = []
    for a in soup.select("a.result__a, a.result__url"):
        href = _clean(a.get("href") or "")
        if href.startswith("//"):
            href = "https:" + href
        if href.startswith("http"):
            out.append(href)
    # DDG sometimes wraps redirects
    for a in soup.find_all("a", href=True):
        h = a["href"]
        m = re.search(r"uddg=([^&]+)", h)
        if m:
            from urllib.parse import unquote
            out.append(unquote(m.group(1)))
    return out
