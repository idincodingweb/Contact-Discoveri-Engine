"""Optional JS rendering fallback for SPA-heavy sites."""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)


async def render_page(url: str, timeout: int = 25) -> str:
    """Returns rendered HTML or empty string on failure."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        log.warning("Playwright not installed — pip install playwright && playwright install chromium")
        return ""

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
            ctx = await browser.new_context(
                user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 Chrome/126.0 Safari/537.36"),
            )
            page = await ctx.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
            await page.wait_for_timeout(1500)
            html = await page.content()
            await browser.close()
            return html
    except Exception as e:
        log.debug("playwright failed %s: %s", url, e)
        return ""
