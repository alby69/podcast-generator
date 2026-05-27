from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from podcast_generator.config import Settings
from podcast_generator.models import Newsletter, Episode
from podcast_generator.fetcher import (
    fetch_latest_newsletter as _fetch_latest,
    fetch_multiple_newsletters as _fetch_multiple,
    fetch_all_newsletters as _fetch_all,
    fetch_newsletters_from_urls as _fetch_from_urls,
    fetch_content as _fetch_content,
)
from podcast_generator.translator import translate_newsletter, translate_multiple
from podcast_generator.tts import generate_audio as _synthesize
from podcast_generator.audio import check_duration, merge_audio_files, add_intro_outro
from podcast_generator.tracker import Tracker

_PLAYWRIGHT_CONTEXT = None


async def _get_shared_context():
    global _PLAYWRIGHT_CONTEXT
    if _PLAYWRIGHT_CONTEXT is None:
        from playwright.async_api import async_playwright

        p = await async_playwright().start()
        browser = await p.firefox.launch(headless=True)
        _PLAYWRIGHT_CONTEXT = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        )
    return _PLAYWRIGHT_CONTEXT


def _slugify(text: str, max_len: int = 50) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:max_len]


def _save_script(script: str, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(script, encoding="utf-8")


class PodcastGenerator:
    """Main public API for podcast generation.

    Usage:
        gen = PodcastGenerator()
        episode = await gen.fetch_and_build_latest()
        # or
        articles = await gen.fetch_articles("https://...")
        episode = await gen.build_from_urls([articles[0].href])
    """

    def __init__(self, config: Optional[Settings] = None):
        self.config = config or Settings()

    # --- Fetching ---

    async def fetch_articles(
        self,
        newsletter_url: Optional[str] = None,
    ) -> list:
        from podcast_generator.fetcher import get_article_list

        url = newsletter_url or self.config.newsletter_url
        archive = f"{url}/archive" if newsletter_url else self.config.archive_url
        return await get_article_list(
            archive,
            load_more_selector=self.config.load_more_selector,
            link_pattern=self.config.link_pattern,
            max_articles=self.config.max_articles,
        )

    async def fetch_newsletter_content(
        self,
        context,
        link: dict[str, str],
    ) -> Newsletter:
        return await _fetch_content(context, link)

    # --- Building ---

    async def build_daily(self, newsletter: Newsletter) -> Episode:
        script = await translate_newsletter(self.config, newsletter.content)
        date_str = newsletter.date.strftime("%Y-%m-%d")
        slug = _slugify(newsletter.title)

        daily_dir = self.config.output_dir / "daily"
        daily_dir.mkdir(parents=True, exist_ok=True)
        audio_path = daily_dir / f"{date_str}_{slug}.mp3"
        script_path = daily_dir / f"{date_str}_{slug}.txt"

        await _synthesize(self.config, script, audio_path)
        _save_script(script, script_path)

        if self.config.intro_path or self.config.outro_path:
            add_intro_outro(
                audio_path,
                self.config.intro_path,
                self.config.outro_path,
                audio_path,
            )

        Tracker(self.config.output_dir).mark_processed(
            newsletter.url,
            newsletter.title,
            date_str,
            str(audio_path),
            str(script_path),
        )

        duration, _ = check_duration(audio_path, self.config.max_episode_minutes)
        return Episode(
            audio_path=audio_path,
            script_path=script_path,
            script=script,
            date_str=date_str,
            title=newsletter.title,
            url=newsletter.url,
            duration_minutes=duration,
        )

    async def fetch_and_build_latest(self) -> Episode:
        newsletter = await _fetch_latest(
            self.config.archive_url,
            load_more_selector=self.config.load_more_selector,
            link_pattern=self.config.link_pattern,
        )
        return await self.build_daily(newsletter)

    async def build_from_urls(self, urls: list[str], titles: Optional[list[str]] = None) -> Episode:
        newsletters = await _fetch_from_urls(
            self.config.archive_url,
            urls,
            titles=titles,
            load_more_selector=self.config.load_more_selector,
            link_pattern=self.config.link_pattern,
        )
        if len(newsletters) == 1:
            return await self.build_daily(newsletters[0])
        return await self.build_weekly(newsletters)

    async def build_weekly(self, newsletters: list[Newsletter]) -> Episode:
        items = [(n.title, n.content) for n in newsletters]
        script = await translate_multiple(self.config, items)

        today = datetime.now()
        iso = today.isocalendar()
        week_label = f"{iso[0]}-W{iso[1]:02d}"

        weekly_dir = self.config.output_dir / "weekly"
        weekly_dir.mkdir(parents=True, exist_ok=True)
        audio_path = weekly_dir / f"{week_label}.mp3"
        script_path = weekly_dir / f"{week_label}.txt"

        await _synthesize(self.config, script, audio_path)
        _save_script(script, script_path)

        duration, _ = check_duration(audio_path, self.config.max_episode_minutes)
        return Episode(
            audio_path=audio_path,
            script_path=script_path,
            script=script,
            date_str=today.strftime("%Y-%m-%d"),
            title=week_label,
            url="",
            duration_minutes=duration,
        )

    async def fetch_and_build_weekly(self, days: int = 7) -> Episode:
        newsletters = await _fetch_multiple(
            self.config.archive_url,
            days,
            load_more_selector=self.config.load_more_selector,
            link_pattern=self.config.link_pattern,
        )
        return await self.build_weekly(newsletters)

    async def process_backlog(self, limit: Optional[int] = None) -> dict:
        tracker = Tracker(self.config.output_dir)

        newsletters = await _fetch_all(
            self.config.archive_url,
            load_more_selector=self.config.load_more_selector,
            link_pattern=self.config.link_pattern,
        )
        if limit:
            newsletters = newsletters[:limit]

        unprocessed = [
            n for n in newsletters if not tracker.is_processed(n.url)
        ]

        daily: list[Path] = []
        for nl in unprocessed:
            daily_dir = self.config.output_dir / "daily"
            daily_dir.mkdir(parents=True, exist_ok=True)
            date_str = nl.date.strftime("%Y-%m-%d")
            slug = _slugify(nl.title)
            audio_path = daily_dir / f"{date_str}_{slug}.mp3"
            script_path = daily_dir / f"{date_str}_{slug}.txt"

            if audio_path.exists():
                tracker.mark_processed(
                    nl.url, nl.title, date_str,
                    str(audio_path), str(script_path),
                )
                daily.append(audio_path)
                continue

            script = await translate_newsletter(self.config, nl.content)
            await _synthesize(self.config, script, audio_path)
            _save_script(script, script_path)

            tracker.mark_processed(
                nl.url, nl.title, date_str,
                str(audio_path), str(script_path),
            )
            daily.append(audio_path)

        weekly = self._generate_weekly_compilations(tracker)
        return {
            "daily": daily,
            "weekly": weekly,
            "unprocessed_count": len(unprocessed),
            "total_count": len(newsletters),
        }

    def _generate_weekly_compilations(self, tracker: Tracker) -> list[Path]:
        weekly_dir = self.config.output_dir / "weekly"
        weekly_dir.mkdir(parents=True, exist_ok=True)
        weekly_paths: list[Path] = []

        for week_key, items in sorted(tracker.get_by_week().items()):
            weekly_audio = weekly_dir / f"{week_key}.mp3"
            if weekly_audio.exists():
                continue

            daily_audios = [
                Path(it["daily_file"])
                for it in items
                if Path(it["daily_file"]).exists()
            ]
            if len(daily_audios) < 2:
                continue

            merge_audio_files(daily_audios, weekly_audio)
            weekly_paths.append(weekly_audio)

        return weekly_paths


def _with_search(cfg: Settings, enabled: Optional[bool]) -> Settings:
    if enabled is not None:
        cfg.use_web_search = enabled
    return cfg
