"""End-to-end discovery pipeline."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from crawlers.async_crawler import SiteCrawler
from crawlers.playwright_crawler import render_page
from database.repo import Repository
from engines.search_engine import search_keyword
from extractors.email_extractor import extract_emails, guess_role_from_email
from extractors.person_extractor import extract_people
from extractors.phone_extractor import extract_whatsapp
from extractors.social_extractor import extract_social
from utils.http import HttpClient
from utils.url import base_domain, normalize

log = logging.getLogger(__name__)


@dataclass
class DiscoveryPipeline:
    repo: Repository
    concurrency: int = 10
    timeout: int = 20
    max_results: int = 20
    render_js: bool = False
    resume: bool = False

    async def run(self, jobs: list[dict]) -> None:
        async with HttpClient(timeout=self.timeout, concurrency=self.concurrency) as client:
            for job in jobs:
                await self._handle_job(client, job)

    async def _handle_job(self, client: HttpClient, job: dict) -> None:
        jtype = job["type"]
        value = job["value"]
        country = job.get("country", "")
        niche = value if jtype == "keyword" else ""

        if jtype == "keyword":
            log.info("[bold cyan]Keyword job:[/bold cyan] %s (%s)", value, country)
            sites = await search_keyword(client, value, country, self.max_results)
        elif jtype == "domain":
            sites = [f"https://{value}"]
        elif jtype == "website":
            sites = [value]
        elif jtype == "company":
            sites = await search_keyword(client, f'"{value}" official site', country, 10)
        else:
            return

        # Parallel-process sites (bounded by HttpClient.semaphore)
        await asyncio.gather(
            *[self._process_site(client, s, country, niche) for s in sites],
            return_exceptions=True,
        )

    async def _process_site(self, client: HttpClient, site: str,
                            country: str, niche: str) -> None:
        site = normalize(site)
        domain = base_domain(site)
        if not domain:
            return

        log.info("[green]→[/green] %s", site)

        company_id = self.repo.upsert_company(
            name=None, domain=domain, website=site,
            country=country, niche=niche,
        )

        crawler = SiteCrawler(client, repo=self.repo, resume=self.resume)
        pages_processed = 0

        async for page in crawler.crawl(site):
            pages_processed += 1
            html = page.html

            # JS fallback if rendered DOM seems sparse
            if self.render_js and len(html) < 3000:
                rendered = await render_page(page.final_url)
                if rendered:
                    html = rendered

            self._extract_and_store(company_id, page.final_url, html)

        log.info("[dim]   processed %d pages on %s[/dim]", pages_processed, domain)

    def _extract_and_store(self, company_id: int, source_url: str, html: str) -> None:
        # ----- Emails -----
        emails = extract_emails(html)
        for e in emails:
            self.repo.add_discovery(company_id, "email", e, source_url, 0.9)

        # ----- WhatsApp -----
        for wa in extract_whatsapp(html):
            self.repo.add_discovery(company_id, "whatsapp", wa, source_url, 0.8)

        # ----- Social -----
        socials = extract_social(html)
        for kind, urls in socials.items():
            for u in urls:
                self.repo.add_discovery(company_id, kind, u, source_url, 0.85)

        # ----- People -----
        people = extract_people(html)
        for p in people:
            # Try to match an email to the person heuristically (first name match)
            matched_email = _match_email_to_person(p.name, emails)
            payload = {
                "contact_name": p.name,
                "role": p.role,
                "role_priority": p.priority,
                "email": matched_email,
                "whatsapp": None,
                "telegram": _first(socials.get("telegram", [])),
                "linkedin": _first(socials.get("linkedin", [])),
                "instagram": _first(socials.get("instagram", [])),
                "facebook": _first(socials.get("facebook", [])),
                "twitter": _first(socials.get("twitter", [])),
                "tiktok": _first(socials.get("tiktok", [])),
                "youtube": _first(socials.get("youtube", [])),
                "source_url": source_url,
            }
            self.repo.insert_contact(company_id, payload)

        # ----- Generic role-from-email fallback -----
        for e in emails:
            role = guess_role_from_email(e)
            if not role:
                continue
            self.repo.insert_contact(company_id, {
                "contact_name": None,
                "role": role,
                "role_priority": 10,
                "email": e,
                "whatsapp": None,
                "telegram": _first(socials.get("telegram", [])),
                "linkedin": _first(socials.get("linkedin", [])),
                "instagram": _first(socials.get("instagram", [])),
                "facebook": _first(socials.get("facebook", [])),
                "twitter": _first(socials.get("twitter", [])),
                "tiktok": _first(socials.get("tiktok", [])),
                "youtube": _first(socials.get("youtube", [])),
                "source_url": source_url,
            })


def _first(xs):
    return xs[0] if xs else None


def _match_email_to_person(name: str, emails: list[str]) -> str | None:
    if not name or not emails:
        return None
    parts = [p.lower() for p in name.split() if p]
    if not parts:
        return None
    first, last = parts[0], parts[-1]
    for e in emails:
        local = e.split("@", 1)[0].lower()
        if first in local or last in local:
            return e
    return None
