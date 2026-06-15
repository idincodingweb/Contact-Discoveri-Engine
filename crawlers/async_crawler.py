"""Async crawler — BFS within a single site, prioritizes target pages."""
from __future__ import annotations

import asyncio
import logging
from collections import deque
from dataclasses import dataclass
from typing import AsyncIterator

from bs4 import BeautifulSoup

from utils.http import HttpClient, FetchResult
from utils.url import (
    absolutize, base_domain, is_target_page,
    normalize, priority_score, same_site,
)

log = logging.getLogger(__name__)


@dataclass
class CrawlPage:
    url: str
    final_url: str
    html: str
    status: int


class SiteCrawler:
    """BFS crawler that yields homepage + target pages of one site."""

    MAX_PAGES = 25
    MAX_DEPTH = 2

    def __init__(self, client: HttpClient, *, repo=None, resume: bool = False) -> None:
        self.client = client
        self.repo = repo
        self.resume = resume

    async def crawl(self, start_url: str) -> AsyncIterator[CrawlPage]:
        start = normalize(start_url)
        root = base_domain(start)
        if not root:
            return

        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(start, 0)])
        yielded = 0

        # 1) try sitemap discovery cheap
        sitemap_urls = await self._discover_via_sitemap(start)
        for u in sitemap_urls[:30]:
            if is_target_page(u):
                queue.append((u, 1))

        while queue and yielded < self.MAX_PAGES:
            # sort queue by priority before popping
            sorted_q = sorted(queue, key=lambda x: (priority_score(x[0]), x[1]))
            queue = deque(sorted_q)
            url, depth = queue.popleft()
            url = normalize(url)

            if url in visited:
                continue
            visited.add(url)

            if self.resume and self.repo and self.repo.is_crawled(url):
                log.debug("skip (resume): %s", url)
                continue

            res = await self.client.fetch(url)
            if self.repo:
                self.repo.log_crawl(url, res.status, len(res.html or b""), res.error)

            if res.status == 0 or not res.text:
                continue
            if res.status >= 400:
                continue

            page = CrawlPage(url=url, final_url=res.final_url,
                             html=res.text, status=res.status)
            yielded += 1
            yield page

            if depth >= self.MAX_DEPTH:
                continue

            # Extract intra-site links
            for href in self._extract_links(res):
                if not same_site(href, start):
                    continue
                if href in visited:
                    continue
                queue.append((href, depth + 1))

    def _extract_links(self, res: FetchResult) -> list[str]:
        soup = BeautifulSoup(res.text, "lxml")
        out: list[str] = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith(("mailto:", "tel:", "javascript:", "#")):
                continue
            absu = absolutize(res.final_url, href)
            if absu.startswith("http"):
                out.append(normalize(absu))
        return out

    async def _discover_via_sitemap(self, start_url: str) -> list[str]:
        from urllib.parse import urlparse
        p = urlparse(start_url)
        candidates = [
            f"{p.scheme}://{p.netloc}/sitemap.xml",
            f"{p.scheme}://{p.netloc}/sitemap_index.xml",
            f"{p.scheme}://{p.netloc}/robots.txt",
        ]
        urls: list[str] = []
        for u in candidates:
            res = await self.client.fetch(u)
            if res.status != 200 or not res.text:
                continue
            if u.endswith("robots.txt"):
                for line in res.text.splitlines():
                    if line.lower().startswith("sitemap:"):
                        sm = line.split(":", 1)[1].strip()
                        sm_res = await self.client.fetch(sm)
                        urls += self._parse_sitemap(sm_res.text)
            else:
                urls += self._parse_sitemap(res.text)
        return urls

    @staticmethod
    def _parse_sitemap(xml: str) -> list[str]:
        soup = BeautifulSoup(xml, "lxml-xml")
        return [loc.text.strip() for loc in soup.find_all("loc") if loc.text]
