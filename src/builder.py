"""Async building blocks — pure logic, no progress bars, no CLI.
Suitable for both CLI (pipeline) and web app usage."""

import re
from datetime import datetime
from pathlib import Path

from src.config import Config
from src.models import Newsletter, Episode
from src.fetcher import (
    fetch_latest_newsletter as _fetch_latest,
    fetch_multiple_newsletters as _fetch_multiple,
    fetch_all_newsletters as _fetch_all,
)
from src.translator import translate_newsletter, translate_multiple
from src.tts import generate_audio as _synthesize
from src.audio import check_duration, merge_audio_files
from src.tracker import Tracker


def _slugify(text: str, max_len: int = 50) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:max_len]


def _save_script(script: str, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(script, encoding="utf-8")


async def generate_script_daily(cfg: Config, newsletter: Newsletter) -> str:
    return translate_newsletter(
        cfg.gemini_api_key,
        cfg.gemini_model,
        newsletter.content,
        use_search=cfg.use_web_search,
    )


async def generate_script_weekly(cfg: Config, newsletters: list[Newsletter]) -> str:
    items = [(n.title, n.content) for n in newsletters]
    return translate_multiple(
        cfg.gemini_api_key,
        cfg.gemini_model,
        items,
        use_search=cfg.use_web_search,
    )


async def build_daily(cfg: Config, newsletter: Newsletter) -> Episode:
    script = await generate_script_daily(cfg, newsletter)
    date_str = newsletter.date.strftime("%Y-%m-%d")
    slug = _slugify(newsletter.title)

    daily_dir = cfg.output_dir / "daily"
    daily_dir.mkdir(parents=True, exist_ok=True)
    audio_path = daily_dir / f"{date_str}_{slug}.mp3"
    script_path = daily_dir / f"{date_str}_{slug}.txt"

    await _synthesize(
        script, cfg.tts_voice, audio_path, elevenlabs_api_key=cfg.elevenlabs_api_key
    )
    _save_script(script, script_path)

    Tracker(cfg.output_dir).mark_processed(
        newsletter.url, newsletter.title, date_str,
        str(audio_path), str(script_path),
    )

    duration, _ = check_duration(audio_path, cfg.max_episode_minutes)
    return Episode(
        audio_path=audio_path,
        script_path=script_path,
        script=script,
        date_str=date_str,
        title=newsletter.title,
        url=newsletter.url,
        duration_minutes=duration,
    )


async def fetch_and_build_latest(cfg: Config) -> Episode:
    newsletter = await _fetch_latest(
        cfg.archive_url,
        load_more_selector=cfg.load_more_selector,
        link_pattern=cfg.link_pattern,
    )
    return await build_daily(cfg, newsletter)


async def build_weekly(cfg: Config, newsletters: list[Newsletter]) -> Episode:
    script = await generate_script_weekly(cfg, newsletters)

    today = datetime.now()
    iso = today.isocalendar()
    week_label = f"{iso[0]}-W{iso[1]:02d}"

    weekly_dir = cfg.output_dir / "weekly"
    weekly_dir.mkdir(parents=True, exist_ok=True)
    audio_path = weekly_dir / f"{week_label}.mp3"
    script_path = weekly_dir / f"{week_label}.txt"

    await _synthesize(
        script, cfg.tts_voice, audio_path, elevenlabs_api_key=cfg.elevenlabs_api_key
    )
    _save_script(script, script_path)

    duration, _ = check_duration(audio_path, cfg.max_episode_minutes)
    return Episode(
        audio_path=audio_path,
        script_path=script_path,
        script=script,
        date_str=today.strftime("%Y-%m-%d"),
        title=week_label,
        url="",
        duration_minutes=duration,
    )


async def fetch_and_build_weekly(cfg: Config, days: int = 7) -> Episode:
    newsletters = await _fetch_multiple(
        cfg.archive_url, days,
        load_more_selector=cfg.load_more_selector,
        link_pattern=cfg.link_pattern,
    )
    return await build_weekly(cfg, newsletters)


def _generate_weekly_compilations(cfg: Config, tracker: Tracker) -> list[Path]:
    weekly_dir = cfg.output_dir / "weekly"
    weekly_dir.mkdir(parents=True, exist_ok=True)
    weekly_paths: list[Path] = []

    for week_key, items in sorted(tracker.get_by_week().items()):
        weekly_audio = weekly_dir / f"{week_key}.mp3"
        if weekly_audio.exists():
            continue

        daily_audios = [Path(it["daily_file"]) for it in items if Path(it["daily_file"]).exists()]
        if len(daily_audios) < 2:
            continue

        merge_audio_files(daily_audios, weekly_audio)
        weekly_paths.append(weekly_audio)

    return weekly_paths


async def process_backlog(cfg: Config, limit: int | None = None) -> dict:
    tracker = Tracker(cfg.output_dir)

    newsletters = await _fetch_all(
        cfg.archive_url,
        load_more_selector=cfg.load_more_selector,
        link_pattern=cfg.link_pattern,
    )
    if limit:
        newsletters = newsletters[:limit]

    unprocessed = [n for n in newsletters if not tracker.is_processed(n.url)]

    daily: list[Path] = []
    for nl in unprocessed:
        daily_dir = cfg.output_dir / "daily"
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

        script = translate_newsletter(
            cfg.gemini_api_key,
            cfg.gemini_model,
            nl.content,
            use_search=cfg.use_web_search,
        )
        await _synthesize(
            script, cfg.tts_voice, audio_path, elevenlabs_api_key=cfg.elevenlabs_api_key
        )
        _save_script(script, script_path)

        tracker.mark_processed(
            nl.url, nl.title, date_str,
            str(audio_path), str(script_path),
        )
        daily.append(audio_path)

    weekly = _generate_weekly_compilations(cfg, tracker)
    return {"daily": daily, "weekly": weekly, "unprocessed_count": len(unprocessed), "total_count": len(newsletters)}
