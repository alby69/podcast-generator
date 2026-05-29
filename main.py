#!/usr/bin/env python3
"""CLI entrypoint for podcast-generator.

Usage:
    python main.py daily
    python main.py weekly --days 7
    python main.py fetch-all --limit 10
    python main.py status
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint

sys.path.insert(0, str(Path(__file__).parent))

from podcast_generator.config import Settings
from podcast_generator.pipeline import (
    daily_episode as _daily,
    weekly_episode as _weekly,
    process_all as _all,
)
from podcast_generator.tracker import Tracker
from podcast_generator.exceptions import ConfigError

app = typer.Typer(
    name="podcast-generator",
    help="Genera episodi podcast da una newsletter (configurabile via .env)",
)


def _get_cfg() -> Settings:
    cfg = Settings()
    try:
        cfg.validate()
    except ConfigError as e:
        rprint(f"[bold red]Errore:[/] {e}")
        raise typer.Exit(code=1) from e
    return cfg


@app.command()
def daily(
    search: Optional[bool] = typer.Option(
        None,
        "--search/--no-search",
        help="Abilita/disabilita Google Search grounding",
    ),
):
    """Episodio giornaliero: ultima newsletter → traduzione → audio."""
    cfg = _get_cfg()
    if search is not None:
        cfg.use_web_search = search
    path = asyncio.run(_daily(cfg))
    rprint(f"[green]Episodio salvato in:[/] {path}")


@app.command()
def weekly(
    days: int = typer.Option(7, "--days", "-d", help="Numero giorni da aggregare"),
    search: Optional[bool] = typer.Option(
        None,
        "--search/--no-search",
        help="Abilita/disabilita Google Search grounding",
    ),
):
    """Episodio settimanale: aggrega N newsletter → traduzione → audio."""
    cfg = _get_cfg()
    if search is not None:
        cfg.use_web_search = search
    path = asyncio.run(_weekly(cfg, days))
    rprint(f"[green]Episodio salvato in:[/] {path}")


@app.command()
def fetch_all(
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        "-l",
        help="Limite massimo newsletter da processare",
    ),
    search: Optional[bool] = typer.Option(
        None,
        "--search/--no-search",
        help="Abilita/disabilita Google Search grounding",
    ),
):
    """Scarica TUTTE le newsletter non ancora processate."""
    cfg = _get_cfg()
    if search is not None:
        cfg.use_web_search = search
    result = asyncio.run(_all(cfg, limit=limit))
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


@app.command()
def v3_generate():
    """V3 PoC: Fetch -> ContentAgent -> StorageAgent (IPFS) -> NetworkAgent (Nostr)."""
    from podcast_generator.agents.content_agent import ContentAgent
    from podcast_generator.agents.storage_agent import StorageAgent
    from podcast_generator.agents.network_agent import NetworkAgent

    async def run_v3():
        cfg = _get_cfg()

        content_agent = ContentAgent(cfg)
        storage_agent = StorageAgent(cfg)
        network_agent = NetworkAgent(cfg)

        # Start agents
        await content_agent.start()
        await storage_agent.start()
        await network_agent.start()

        try:
            rprint("[yellow]V3 Flow: Fetching latest newsletter...[/]")
            nl = await content_agent.fetch_latest()

            rprint(f"[yellow]V3 Flow: Generating episode for '{nl.title}'...[/]")
            episode = await content_agent.generate_episode_from_newsletter(nl)

            rprint("[yellow]V3 Flow: Uploading to IPFS...[/]")
            cid = await storage_agent.upload_file(episode.audio_path)

            if cid:
                rprint(f"[green]V3 Flow: IPFS CID: {cid}[/]")
                rprint("[yellow]V3 Flow: Publishing to Nostr...[/]")
                event_id = await network_agent.publish_podcast(episode.title, cid, {})
                if event_id:
                    rprint(f"[bold green]V3 Flow COMPLETE![/]")
                    rprint(f"Nostr Event ID: {event_id.to_bech32()}")
                    rprint(f"IPFS Gateway: {await storage_agent.get_file_url(cid)}")

        finally:
            await content_agent.stop()
            await storage_agent.stop()
            await network_agent.stop()

    asyncio.run(run_v3())


if __name__ == "__main__":
    app()
