from __future__ import annotations

from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from podcast_generator.config import Settings
from podcast_generator.builder import PodcastGenerator

console = Console()

_PROGRESS = Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    TimeElapsedColumn(),
    console=console,
)


async def daily_episode(cfg: Settings) -> Path:
    gen = PodcastGenerator(cfg)
    with _PROGRESS as progress:
        task = progress.add_task("[yellow]Estrazione newsletter...", total=None)
        episode = await gen.fetch_and_build_latest()
        progress.update(task, description="[green]Fatto!")
    console.print(f"\n[bold green]Episodio creato:[/] {episode.audio_path}")
    console.print(f"[bold]Durata:[/] {episode.duration_minutes:.1f} minuti")
    _warn_duration(cfg, episode)
    return episode.audio_path


async def weekly_episode(cfg: Settings, days: int = 7) -> Path:
    gen = PodcastGenerator(cfg)
    with _PROGRESS as progress:
        task = progress.add_task(
            f"[yellow]Estrazione ultime {days} newsletter...", total=None
        )
        episode = await gen.fetch_and_build_weekly(days)
        progress.update(task, description="[green]Fatto!")
    console.print(f"\n[bold green]Episodio settimanale creato:[/] {episode.audio_path}")
    console.print(f"[bold]Durata:[/] {episode.duration_minutes:.1f} minuti")
    _warn_duration(cfg, episode)
    return episode.audio_path


async def process_all(cfg: Settings, limit: Optional[int] = None) -> dict:
    gen = PodcastGenerator(cfg)
    with _PROGRESS as progress:
        task = progress.add_task("[yellow]Scarico newsletter...", total=None)
        result = await gen.process_backlog(limit)

        if result["unprocessed_count"] == 0:
            progress.update(task, description="[green]Tutto già processato!")
            console.print("[yellow]Nessuna nuova newsletter da processare.[/]")
            return {"daily": [], "weekly": []}

        total = result["total_count"]
        unprocessed = result["unprocessed_count"]
        console.print(
            f"\n[bold]Trovate {unprocessed} nuove newsletter su {total} totali[/]\n"
        )

        for i, _ in enumerate(result["daily"], 1):
            progress.update(
                task, description=f"[yellow][{i}/{unprocessed}] Audio..."
            )

        progress.update(task, description="[yellow]Compilation settimanali...")
        progress.update(task, description="[green]Completato!")

    console.print(
        f"\n[bold green]Puntate giornaliere create:[/] {len(result['daily'])}"
    )
    console.print(
        f"[bold green]Compilation settimanali create:[/] {len(result['weekly'])}"
    )
    return {"daily": result["daily"], "weekly": result["weekly"]}


def _warn_duration(cfg: Settings, episode) -> None:
    if (
        episode.duration_minutes
        and episode.duration_minutes > cfg.max_episode_minutes
    ):
        console.print(
            f"[yellow]Attenzione:[/] supera il limite di {cfg.max_episode_minutes} min"
        )
