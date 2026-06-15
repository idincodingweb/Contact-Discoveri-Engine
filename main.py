"""
Contact Discovery Engine — main entrypoint
Author: Idin Code AI
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from rich.console import Console

from database.repo import Repository
from engines.pipeline import DiscoveryPipeline
from exporters.exporter import Exporter
from utils.logger import setup_logger

console = Console()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="contact-discovery-engine",
        description="Find decision-maker contacts from companies / niches / domains.",
    )
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--keyword", type=str, help='Niche keyword, e.g. "Dental Marketing Agency"')
    src.add_argument("--domain", type=str, help="Single domain, e.g. nike.com")
    src.add_argument("--website", type=str, help="Full URL, e.g. https://nike.com")
    src.add_argument("--company", type=str, help="Company name, e.g. 'Acme Corp'")
    src.add_argument("--input-file", type=str, help="Path to txt file (1 keyword/domain per line)")

    p.add_argument("--country", type=str, default="", help="Country filter, e.g. US / Indonesia")
    p.add_argument("--max-results", type=int, default=20, help="Max SERP results per keyword")
    p.add_argument("--concurrency", type=int, default=10)
    p.add_argument("--timeout", type=int, default=20)
    p.add_argument("--render-js", action="store_true", help="Enable Playwright JS rendering")
    p.add_argument("--db", type=str, default="outputs/contacts.db")
    p.add_argument("--output-prefix", type=str, default="outputs/results")
    p.add_argument("--resume", action="store_true", help="Skip URLs already crawled in DB")
    p.add_argument("--log-level", type=str, default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return p.parse_args()


def collect_inputs(args: argparse.Namespace) -> list[dict]:
    """Normalize CLI args into a list of input jobs."""
    jobs: list[dict] = []

    if args.input_file:
        lines = Path(args.input_file).read_text(encoding="utf-8").splitlines()
        for raw in lines:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            jobs.append(_classify_input(line, args.country))
        return jobs

    if args.keyword:
        jobs.append({"type": "keyword", "value": args.keyword, "country": args.country})
    elif args.domain:
        jobs.append({"type": "domain", "value": args.domain.lower().strip(), "country": args.country})
    elif args.website:
        jobs.append({"type": "website", "value": args.website.strip(), "country": args.country})
    elif args.company:
        jobs.append({"type": "company", "value": args.company.strip(), "country": args.country})
    return jobs


def _classify_input(line: str, country: str) -> dict:
    if line.startswith(("http://", "https://")):
        return {"type": "website", "value": line, "country": country}
    if "." in line and " " not in line:
        return {"type": "domain", "value": line.lower(), "country": country}
    return {"type": "keyword", "value": line, "country": country}


async def run(args: argparse.Namespace) -> int:
    setup_logger(args.log_level)
    Path("outputs").mkdir(exist_ok=True, parents=True)

    repo = Repository(args.db)
    repo.init_schema()

    jobs = collect_inputs(args)
    if not jobs:
        console.print("[red]No input provided.[/red]")
        return 2

    console.rule("[bold cyan]Contact Discovery Engine — Idin Code AI[/bold cyan]")
    console.print(f"[green]Jobs queued:[/green] {len(jobs)}")

    pipeline = DiscoveryPipeline(
        repo=repo,
        concurrency=args.concurrency,
        timeout=args.timeout,
        max_results=args.max_results,
        render_js=args.render_js,
        resume=args.resume,
    )

    await pipeline.run(jobs)

    exporter = Exporter(repo)
    exporter.export_all(prefix=args.output_prefix)

    console.print("[bold green]✓ Done. Files written to outputs/[/bold green]")
    return 0


def main() -> None:
    args = parse_args()
    try:
        rc = asyncio.run(run(args))
    except KeyboardInterrupt:
        console.print("[yellow]Interrupted by user.[/yellow]")
        rc = 130
    sys.exit(rc)


if __name__ == "__main__":
    main()
