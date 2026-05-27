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
        context = await browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        links = await _get_links_from_archive(context, archive_url, load_more_selector, link_pattern)
        if not links:
            raise RuntimeError("Nessun post trovato nella pagina archive.")
        newsletter = await fetch_content(context, links[0])
        await browser.close()

    return newsletter


async def fetch_content(
    context, link: dict[str, str]
) -> Newsletter:
    page = await context.new_page()
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


async def get_article_list(
    archive_url: str,
    load_more_selector: str = "button:has-text('Load More'), a:has-text('Load More')",
    link_pattern: str = "/p/",
) -> list[dict[str, str]]:
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        links = await _get_links_from_archive(context, archive_url, load_more_selector, link_pattern)
        await browser.close()
    return links


async def _get_links_from_archive(
    context, archive_url: str,
    load_more_selector: str = "button:has-text('Load More'), a:has-text('Load More')",
    link_pattern: str = "/p/",
) -> list[dict[str, str]]:
    page = await context.new_page()
    await page.goto(archive_url, wait_until="domcontentloaded", timeout=60000)

    for _ in range(5):  # Limit load more to 5 times for responsiveness
        try:
            load_more = await page.wait_for_selector(
                load_more_selector,
                timeout=3000,
            )
            if await load_more.is_visible():
                await load_more.click()
                await page.wait_for_timeout(2000)
            else:
                break
        except:
            break

    links = await page.evaluate(
        """(pattern) => {
            const results = [];
            const seen = new Set();
            const anchors = document.querySelectorAll('a');

            for (const a of anchors) {
                const href = a.href;
                // Beehiiv sometimes uses absolute paths in JS but they might not have the full domain yet
                if (href && (href.includes(pattern) || (href.startsWith('/') && href.includes('/p/')) || href.includes('/posts/'))) {
                    // Normalize URL to avoid duplicates with query params
                    const urlObj = new URL(href);
                    const url = urlObj.origin + urlObj.pathname;

                    if (seen.has(url)) continue;
                    seen.add(url);

                    let title = a.textContent.trim();
                    let description = "";

                    const container = a.closest('div[data-testid="post-preview"]') || a.closest('article') || a.parentElement;
                    if (container) {
                        if (title.length < 5) {
                            const titleEl = container.querySelector('h1, h2, h3, .post-preview-title');
                            if (titleEl) title = titleEl.textContent.trim();
                        }
                        const descEl = container.querySelector('.post-preview-description, .post-preview-excerpt, .subtitle, p');
                        if (descEl && descEl.textContent.trim() !== title) {
                            description = descEl.textContent.trim();
                        }
                    }

                    if (title && title.length > 3) {
                        results.push({href: url, text: title, description: description});
                    } else {
                        console.log("Skipping link with short title:", title, "URL:", url);
                    }
                }
            }
            return results;
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
        context = await browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        links = await _get_links_from_archive(context, archive_url, load_more_selector, link_pattern)
        selected = links[:count]
        newsletters = [await fetch_content(context, link) for link in selected]
        await browser.close()

    return newsletters


async def fetch_all_newsletters(
    archive_url: str,
    load_more_selector: str = "button:has-text('Load More'), a:has-text('Load More')",
    link_pattern: str = "/p/",
) -> list[Newsletter]:
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        links = await _get_links_from_archive(context, archive_url, load_more_selector, link_pattern)
        if not links:
            raise RuntimeError("Nessun post trovato nella pagina archive.")
        newsletters = [await fetch_content(context, link) for link in links]
        await browser.close()

    return newsletters
