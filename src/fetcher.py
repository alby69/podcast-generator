import re
from datetime import datetime

from playwright.async_api import async_playwright

from src.models import Newsletter


def _parse_date(text: str) -> datetime:
    months = {
        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
        "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
    }
    match = re.search(
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d+),?\s+(\d{4})",
        text,
    )
    if match:
        month = months[match.group(1)]
        day = int(match.group(2))
        year = int(match.group(3))
        return datetime(year, month, day)
    return datetime.now()


async def fetch_latest_newsletter(
    archive_url: str,
    load_more_selector: str = "button:has-text('Load More'), a:has-text('Load More')",
    link_pattern: str = "/p/",
) -> Newsletter:
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        links = await _get_links_from_archive(browser, archive_url, load_more_selector, link_pattern)
        if not links:
            raise RuntimeError("Nessun post trovato nella pagina archive.")
        newsletter = await _fetch_content(browser, links[0])
        await browser.close()

    return newsletter


async def _fetch_content(
    browser, link: dict[str, str]
) -> Newsletter:
    page = await browser.new_page()
    await page.goto(link["href"], wait_until="domcontentloaded", timeout=60000)
    body_text = await page.evaluate("""
        () => {
            const clone = document.body.cloneNode(true);
            clone.querySelectorAll('script, style, nav, footer, header, iframe').forEach(el => el.remove());
            return clone.innerText;
        }
    """)
    await page.close()

    clean = re.sub(r"Hey, \{\{.*?\}\}", "", body_text)
    clean = re.sub(r"\n{3,}", "\n\n", clean).strip()
    title = link["text"].split("•")[0].strip() if "•" in link["text"] else link["text"]
    return Newsletter(
        title=title,
        url=link["href"],
        date=_parse_date(link["text"]),
        content=clean,
    )


async def _get_links_from_archive(
    browser, archive_url: str,
    load_more_selector: str = "button:has-text('Load More'), a:has-text('Load More')",
    link_pattern: str = "/p/",
) -> list[dict[str, str]]:
    page = await browser.new_page()
    await page.goto(archive_url, wait_until="domcontentloaded", timeout=60000)

    while True:
        try:
            load_more = await page.wait_for_selector(
                load_more_selector,
                timeout=3000,
            )
            await load_more.click()
            await page.wait_for_timeout(2000)
        except:
            break

    links = await page.evaluate(
        """(pattern) => {
            const anchors = document.querySelectorAll('a');
            return Array.from(anchors)
                .filter(a => a.href && a.href.includes(pattern))
                .map(a => ({href: a.href, text: a.textContent.trim()}));
        }""",
        link_pattern,
    )
    await page.close()
    return links


async def fetch_multiple_newsletters(
    archive_url: str, count: int = 7,
    load_more_selector: str = "button:has-text('Load More'), a:has-text('Load More')",
    link_pattern: str = "/p/",
) -> list[Newsletter]:
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        links = await _get_links_from_archive(browser, archive_url, load_more_selector, link_pattern)
        selected = links[:count]
        newsletters = [await _fetch_content(browser, link) for link in selected]
        await browser.close()

    return newsletters


async def fetch_all_newsletters(
    archive_url: str,
    load_more_selector: str = "button:has-text('Load More'), a:has-text('Load More')",
    link_pattern: str = "/p/",
) -> list[Newsletter]:
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        links = await _get_links_from_archive(browser, archive_url, load_more_selector, link_pattern)
        if not links:
            raise RuntimeError("Nessun post trovato nella pagina archive.")
        newsletters = [await _fetch_content(browser, link) for link in links]
        await browser.close()

    return newsletters
