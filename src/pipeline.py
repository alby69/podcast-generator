"""Thin async orchestrator: wraps builder with Rich progress reporting."""

from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from src.config import Config
from src.builder import (
    fetch_and_build_latest,
    fetch_and_build_weekly,
    process_backlog,
)

console = Console()

_PROGRESS = Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    TimeElapsedColumn(),
    console=console,
)


async def daily_episode(cfg: Config) -> Path:
    with _PROGRESS as progress:
        task = progress.add_task("[yellow]Estrazione newsletter...", total=None)
        episode = await fetch_and_build_latest(cfg)
        progress.update(task, description="[green]Fatto!")

    console.print(f"\n[bold green]Episodio creato:[/] {episode.audio_path}")
    console.print(f"[bold]Durata:[/] {episode.duration_minutes:.1f} minuti")
    _warn_duration(cfg, episode)
    return episode.audio_path


async def weekly_episode(cfg: Config, days: int = 7) -> Path:
    with _PROGRESS as progress:
        task = progress.add_task(f"[yellow]Estrazione ultime {days} newsletter...", total=None)
        episode = await fetch_and_build_weekly(cfg, days)
        progress.update(task, description="[green]Fatto!")

    console.print(f"\n[bold green]Episodio settimanale creato:[/] {episode.audio_path}")
    console.print(f"[bold]Durata:[/] {episode.duration_minutes:.1f} minuti")
    _warn_duration(cfg, episode)
    return episode.audio_path


async def process_all(cfg: Config, limit: int | None = None) -> dict:
    with _PROGRESS as progress:
        task = progress.add_task("[yellow]Scarico newsletter...", total=None)
        result = await process_backlog(cfg, limit)

        if result["unprocessed_count"] == 0:
            progress.update(task, description="[green]Tutto già processato!")
            console.print("[yellow]Nessuna nuova newsletter da processare.[/]")
            return {"daily": [], "weekly": []}

        total = result["total_count"]
        unprocessed = result["unprocessed_count"]
        console.print(f"\n[bold]Trovate {unprocessed} nuove newsletter su {total} totali[/]\n")

        for i, _ in enumerate(result["daily"], 1):
            progress.update(task, description=f"[yellow][{i}/{unprocessed}] Audio...")

        progress.update(task, description="[yellow]Compilation settimanali...")
        progress.update(task, description="[green]Completato!")

    console.print(f"\n[bold green]Puntate giornaliere create:[/] {len(result['daily'])}")
    console.print(f"[bold green]Compilation settimanali create:[/] {len(result['weekly'])}")
    return {"daily": result["daily"], "weekly": result["weekly"]}


def _warn_duration(cfg: Config, episode) -> None:
    if episode.duration_minutes and episode.duration_minutes > cfg.max_episode_minutes:
        console.print(
            f"[yellow]Attenzione:[/] supera il limite di {cfg.max_episode_minutes} min"
        )
