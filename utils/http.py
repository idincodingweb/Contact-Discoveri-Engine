"""Async HTTP client with retries + rate limiting + UA rotation."""
from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass
from typing import Optional

import httpx
from tenacity import (
    retry, retry_if_exception_type, stop_after_attempt,
    wait_exponential_jitter,
)

log = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
]


@dataclass
class FetchResult:
    url: str
    status: int
    text: str
    html: bytes
    final_url: str
    error: str = ""


class HttpClient:
    def __init__(self, *, timeout: int = 20, concurrency: int = 10) -> None:
        self.timeout = timeout
        self.sem = asyncio.Semaphore(concurrency)
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "HttpClient":
        self._client = httpx.AsyncClient(
            http2=True,
            follow_redirects=True,
            timeout=self.timeout,
            headers={"Accept-Language": "en-US,en;q=0.9"},
            verify=False,  # tolerant on misconfigured certs
        )
        return self

    async def __aexit__(self, *exc) -> None:
        if self._client:
            await self._client.aclose()

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=8),
        retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
    )
    async def _get(self, url: str) -> httpx.Response:
        assert self._client is not None
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        r = await self._client.get(url, headers=headers)
        if r.status_code >= 500:
            raise httpx.HTTPStatusError("server error", request=r.request, response=r)
        return r

    async def fetch(self, url: str) -> FetchResult:
        async with self.sem:
            try:
                r = await self._get(url)
                # politeness jitter
                await asyncio.sleep(random.uniform(0.2, 0.8))
                return FetchResult(
                    url=url,
                    status=r.status_code,
                    text=r.text,
                    html=r.content,
                    final_url=str(r.url),
                )
            except Exception as e:
                log.debug("fetch failed url=%s err=%s", url, e)
                return FetchResult(url=url, status=0, text="", html=b"",
                                   final_url=url, error=str(e))
