from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

import feedparser
import trafilatura
from imap_tools import MailBox, AND
from playwright.async_api import async_playwright

from podcast_generator.exceptions import FetchError
from podcast_generator.models import Newsletter, ArticleSummary

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


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


_DATE_RE = re.compile(
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d+),?\s+(\d{4})"
)
_DURATION_RE = re.compile(r"•\s*(\d+\s*min\s*read)")


def _parse_article_text(text: str) -> dict:
    """Parse Beehiiv-style article text into date, duration, title, description.
    
    Input format: "May 26, 2026•3 min readTitleHereDescriptionHere...SourceName"
    """
    result = {"date": "", "duration": "", "title": text, "description": ""}

    date_match = _DATE_RE.search(text)
    if date_match:
        result["date"] = date_match.group(0)

    dur_match = _DURATION_RE.search(text)
    if dur_match:
        result["duration"] = dur_match.group(1).strip()

    after_dur = _DURATION_RE.split(text, maxsplit=1)
    remaining = after_dur[2].strip() if len(after_dur) > 2 else text

    remaining = re.sub(r"\s*There's An AI For That\s*$", "", remaining)

    parts = re.split(
        r"(?<=[a-z)])(?=[A-Z](?:[a-z]|\s))|(?<=[A-Z])(?=[A-Z][a-z])",
        remaining, maxsplit=1,
    )
    if len(parts) == 2:
        title, desc = parts
        result["title"] = title.strip()
        result["description"] = desc.strip()
    else:
        parts = re.split(r"(?<=\.\.\.)\s*(?=[A-Z])", remaining, maxsplit=1)
        if len(parts) == 2:
            result["title"] = parts[0].strip()
            result["description"] = parts[1].strip()
        else:
            result["title"] = remaining.strip()

    return result


async def fetch_content(
    context, link: dict[str, str]
) -> Newsletter:
    # Try trafilatura first for cleaner extraction
    downloaded = trafilatura.fetch_url(link["href"])
    if downloaded:
        content = trafilatura.extract(downloaded)
        if content:
            title = link["text"].split("•")[0].strip() if "•" in link["text"] else link["text"]
            return Newsletter(
                title=title,
                url=link["href"],
                date=_parse_date(link.get("text", "")),
                content=content,
            )

    # Fallback to Playwright if trafilatura fails
    page = await context.new_page()
    try:
        await page.goto(link["href"], wait_until="domcontentloaded", timeout=60000)
        body_text = await page.evaluate("""
            () => {
                const clone = document.body.cloneNode(true);
                clone.querySelectorAll('script, style, nav, footer, header, iframe').forEach(el => el.remove());
                return clone.innerText;
            }
        """)
    except Exception as e:
        raise FetchError(f"Failed to fetch content from {link['href']}: {e}") from e
    finally:
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


async def fetch_article_html(url: str) -> str:
    """Fetch a single article page and return clean HTML content."""
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context(user_agent=_USER_AGENT)
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            html = await page.evaluate("""
                () => {
                    const clone = document.body.cloneNode(true);
                    clone.querySelectorAll(
                        'script, style, nav, footer, header, iframe, ' +
                        '[class*="header"], [class*="footer"], [class*="nav"], ' +
                        '[class*="sidebar"], [role="navigation"], ' +
                        '.publication-branding, .publication-footer, .post-footer, ' +
                        '[data-rht-toaster], [class*="cookie"], [class*="consent"], ' +
                        '#cookie-consent, [class*="toast"]'
                    ).forEach(el => el.remove());

                    const article = clone.querySelector('article') ||
                                    clone.querySelector('[class*="post-content"]') ||
                                    clone.querySelector('[class*="article-body"]') ||
                                    clone.querySelector('main') ||
                                    clone.querySelector('[data-testid*="post"]') ||
                                    clone.querySelector('.dream-block')?.closest('div');

                    const root = article || clone.body || clone;

                    const unwanted = [
                        /what'?d you think/i,
                        /vote below/i,
                        /how we're doing|how we are doing/i,
                        /login or subscribe/i,
                        /too frequent/i,
                        /update your preference/i,
                        /\\bunsubscribe\\b/i,
                        /hated it and want/i,
                        /that'?s all for today/i,
                        /have a great week/i,
                        /signing off/i,
                        /follow us on/i,
                        /— there'?s an ai for that/i,
                        /there'?s an ai for that\\s*$/i,
                        /if something caught your eye/i,
                        /found this useful/i,
                        /share it with friends/i,
                        /for the latest ai scoops/i,
                        /absolutely loved it/i,
                        /better than usual/i,
                        /meh,? it was okay/i,
                        /could be better/i,
                    ];

                    const all = root.querySelectorAll('p, h1, h2, h3, h4, h5, h6, div, section, table');
                    const toRemove = [];
                    for (const el of all) {
                        const text = el.textContent.trim();
                        if (text.length < 5 || text.length > 500) continue;
                        if (unwanted.some(r => r.test(text))) {
                            toRemove.push(el);
                        }
                    }
                    toRemove.forEach(el => el.remove());

                    if (article) return article.innerHTML;
                    return root.innerHTML;
                }
            """)
        except Exception as e:
            raise FetchError(f"Failed to fetch article HTML from {url}: {e}") from e
        finally:
            await page.close()
        await browser.close()
    return html


async def fetch_latest_newsletter(
    archive_url: str,
    load_more_selector: str = "button:has-text('Load More'), a:has-text('Load More')",
    link_pattern: str = "/p/",
    max_articles: int = 60,
) -> Newsletter:
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context(user_agent=_USER_AGENT)
        try:
            links = await _get_links_from_archive(
                context, archive_url, load_more_selector, link_pattern, max_articles
            )
            if not links:
                raise FetchError("Nessun post trovato nella pagina archive.")
            newsletter = await fetch_content(context, links[0])
        finally:
            await browser.close()
    return newsletter


async def get_article_list(
    archive_url: str,
    load_more_selector: str = "button:has-text('Load More'), a:has-text('Load More')",
    link_pattern: str = "/p/",
    max_articles: int = 60,
) -> list[ArticleSummary]:
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context(user_agent=_USER_AGENT)
        try:
            raw = await _get_links_from_archive(
                context, archive_url, load_more_selector, link_pattern, max_articles
            )
        finally:
            await browser.close()

    articles = []
    for item in raw:
        parsed = _parse_article_text(item.get("text", ""))
        title = item.get("title") or parsed["title"]
        description = item.get("description") or parsed["description"]
        articles.append(ArticleSummary(
            href=item.get("href", ""),
            text=title,
            description=description,
            date=parsed["date"],
            duration=parsed["duration"],
        ))
    return articles


async def _get_links_from_archive(
    context,
    archive_url: str,
    load_more_selector: str = "button:has-text('Load More'), a:has-text('Load More')",
    link_pattern: str = "/p/",
    max_articles: int = 60,
) -> list[dict[str, str]]:
    page = await context.new_page()
    try:
        await page.goto(archive_url, wait_until="domcontentloaded", timeout=60000)

        seen_urls: set[str] = set()
        all_links: list[dict[str, str]] = []

        next_page_selector = 'button[aria-label="Next page"]'
        await page.wait_for_timeout(3000)

        for attempt in range(50):
            links = await page.evaluate(
                """(pattern) => {
                    const results = [];
                    const seen = new Set();
                    const anchors = document.querySelectorAll('a');

                    for (const a of anchors) {
                        const href = a.href;
                        if (href && (href.includes(pattern) ||
                            (href.startsWith('/') && href.includes('/p/')) ||
                            href.includes('/posts/'))) {
                            const urlObj = new URL(href);
                            const url = urlObj.origin + urlObj.pathname;
                            if (seen.has(url)) continue;
                            seen.add(url);

                            const raw = a.textContent.trim();
                            let title = raw;
                            let description = "";
                            const container = a.closest('div[data-testid="post-preview"]') ||
                                              a.closest('article') || a.parentElement;
                            if (container) {
                                const strongEl = container.querySelector('strong');
                                if (strongEl) title = strongEl.textContent.trim();

                                const descEl = container.querySelector('p.line-clamp-3');
                                if (descEl && descEl.textContent.trim() !== title) {
                                    description = descEl.textContent.trim();
                                }
                            }
                            if (title && title.length > 3) {
                                results.push({href: url, text: raw, title, description});
                            }
                        }
                    }
                    return results;
                }""",
                link_pattern,
            )

            new_count = 0
            for item in links:
                if item["href"] not in seen_urls:
                    seen_urls.add(item["href"])
                    all_links.append(item)
                    new_count += 1

            if len(all_links) >= max_articles:
                break

            if new_count == 0 and attempt > 0:
                break

            next_btn = await page.query_selector(next_page_selector)
            if not next_btn:
                break

            is_disabled = await next_btn.get_attribute("disabled") is not None or await next_btn.evaluate(
                "el => el.style.pointerEvents === 'none'"
            )
            if is_disabled:
                break

            await next_btn.click()
            await page.wait_for_timeout(2000)

        return all_links
    except Exception as e:
        raise FetchError(f"Failed to parse archive page: {e}") from e
    finally:
        await page.close()


async def fetch_multiple_newsletters(
    archive_url: str,
    count: int = 7,
    load_more_selector: str = "button:has-text('Load More'), a:has-text('Load More')",
    link_pattern: str = "/p/",
    max_articles: int = 60,
) -> list[Newsletter]:
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context(user_agent=_USER_AGENT)
        try:
            links = await _get_links_from_archive(
                context, archive_url, load_more_selector, link_pattern, max_articles
            )
            selected = links[:count]
            newsletters = [await fetch_content(context, link) for link in selected]
        finally:
            await browser.close()
    return newsletters


async def get_rss_articles(rss_url: str) -> list[ArticleSummary]:
    feed = feedparser.parse(rss_url)
    articles = []
    for entry in feed.entries:
        date_str = ""
        if hasattr(entry, "published"):
            date_str = entry.published
        elif hasattr(entry, "updated"):
            date_str = entry.updated

        articles.append(ArticleSummary(
            href=entry.link,
            text=entry.title,
            description=getattr(entry, "summary", ""),
            date=date_str,
        ))
    return articles


async def get_email_articles(
    imap_host: str, imap_user: str, imap_password: str, folder: str = "INBOX"
) -> list[ArticleSummary]:
    if not imap_host or not imap_user or not imap_password:
        return []

    articles = []
    try:
        with MailBox(imap_host).login(imap_user, imap_password, folder) as mailbox:
            for msg in mailbox.fetch(limit=10, reverse=True):
                # We use a special URN for emails so the builder knows how to fetch them
                # format: email://{uid}
                articles.append(ArticleSummary(
                    href=f"email://{msg.uid}",
                    text=msg.subject,
                    description=msg.text[:200] if msg.text else "",
                    date=msg.date.strftime("%Y-%m-%d %H:%M:%S"),
                ))
    except Exception as e:
        raise FetchError(f"IMAP error: {e}") from e
    return articles


async def fetch_email_content(
    imap_host: str, imap_user: str, imap_password: str, uid: str, folder: str = "INBOX"
) -> Newsletter:
    try:
        with MailBox(imap_host).login(imap_user, imap_password, folder) as mailbox:
            for msg in mailbox.fetch(AND(uid=uid)):
                html = msg.html or ""
                content = trafilatura.extract(html) or msg.text or ""
                return Newsletter(
                    title=msg.subject,
                    url=f"email://{msg.uid}",
                    date=msg.date,
                    content=content,
                )
    except Exception as e:
        raise FetchError(f"IMAP error fetching UID {uid}: {e}") from e
    raise FetchError(f"Email with UID {uid} not found")


async def fetch_newsletters_from_urls(
    archive_url: str,
    urls: list[str],
    titles: Optional[list[str]] = None,
    load_more_selector: str = "button:has-text('Load More'), a:has-text('Load More')",
    link_pattern: str = "/p/",
) -> list[Newsletter]:
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context(user_agent=_USER_AGENT)
        try:
            link_objects = []
            for i, url in enumerate(urls):
                text = titles[i] if titles and i < len(titles) and titles[i] else "Articolo"
                link_objects.append({"href": url, "text": text})
            newsletters = [await fetch_content(context, link) for link in link_objects]
        finally:
            await browser.close()
    return newsletters


async def fetch_all_newsletters(
    archive_url: str,
    load_more_selector: str = "button:has-text('Load More'), a:has-text('Load More')",
    link_pattern: str = "/p/",
) -> list[Newsletter]:
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context(user_agent=_USER_AGENT)
        try:
            links = await _get_links_from_archive(
                context, archive_url, load_more_selector, link_pattern
            )
            if not links:
                raise FetchError("Nessun post trovato nella pagina archive.")
            newsletters = [await fetch_content(context, link) for link in links]
        finally:
            await browser.close()
    return newsletters
