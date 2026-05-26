#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

import typer
from rich import print as rprint

sys.path.insert(0, str(Path(__file__).parent))

from src.config import Config
from src.pipeline import daily_episode as _daily, weekly_episode as _weekly, process_all as _all
from src.tracker import Tracker

app = typer.Typer(
    name="podcast-generator",
    help="Genera episodi podcast da una newsletter (configurabile via .env)",
)


def _get_cfg() -> Config:
    cfg = Config()
    try:
        cfg.validate()
    except ValueError as e:
        rprint(f"[bold red]Errore:[/] {e}")
        rprint("Crea un file .env basato su .env.example con le tue API key.")
        raise typer.Exit(code=1) from e
    return cfg


@app.command()
def daily(
    search: bool = typer.Option(
        None, "--search/--no-search", help="Abilita/disabilita Google Search grounding"
    ),
):
    """Episodio giornaliero: ultima newsletter → traduzione → audio."""
    path = asyncio.run(_daily(_get_cfg()))
    rprint(f"[green]Episodio salvato in:[/] {path}")


@app.command()
def weekly(
    days: int = typer.Option(7, "--days", "-d", help="Numero giorni da aggregare"),
    search: bool = typer.Option(
        None, "--search/--no-search", help="Abilita/disabilita Google Search grounding"
    ),
):
    """Episodio settimanale: aggrega N newsletter → traduzione → audio."""
    path = asyncio.run(_weekly(_get_cfg(), days))
    rprint(f"[green]Episodio salvato in:[/] {path}")


@app.command()
def fetch_all(
    limit: int = typer.Option(
        None, "--limit", "-l", help="Limite massimo newsletter da processare"
    ),
    search: bool = typer.Option(
        None, "--search/--no-search", help="Abilita/disabilita Google Search grounding"
    ),
):
    """Scarica TUTTE le newsletter non ancora processate."""
    result = asyncio.run(_all(_get_cfg(), limit=limit))
    rprint(
        f"[green]Fatto:[/] {len(result['daily'])} giornaliere, "
        f"{len(result['weekly'])} settimanali"
    )


@app.command()
def status():
    """Mostra lo stato del tracker: puntate processate e settimane coperte."""
    cfg = _get_cfg()
    tracker = Tracker(cfg.output_dir)
    total = len(tracker.data["processed"])
    by_week = tracker.get_by_week()
    rprint(f"\n[bold]Tracker:[/] {cfg.output_dir / '.processed.json'}")
    rprint(f"[bold]Puntate processate:[/] {total}")
    rprint(f"[bold]Settimane coperte:[/] {len(by_week)}")
    for wk in sorted(by_week):
        rprint(f"  [cyan]{wk}[/]: {len(by_week[wk])} puntate")


if __name__ == "__main__":
    app()
