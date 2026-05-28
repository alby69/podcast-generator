from pathlib import Path
from typing import Optional, List
from podcast_generator.agents.base import BaseAgent
from podcast_generator.config import Settings
from podcast_generator.models import Newsletter, Episode
from podcast_generator.builder import PodcastGenerator

class ContentAgent(BaseAgent):
    """Refactors the core generation logic into an agentic form."""

    def __init__(self, config: Settings):
        super().__init__(config)
        self.generator = PodcastGenerator(config)

    async def start(self):
        self.logger.info("ContentAgent ready for generation tasks.")

    async def stop(self):
        pass

    async def generate_episode_from_newsletter(self, newsletter: Newsletter) -> Episode:
        """Generates an episode from a newsletter object."""
        self.logger.info(f"Generating episode for: {newsletter.title}")
        episode = await self.generator.build_daily(newsletter)

        await self.emit_event("episode_generated", {
            "title": episode.title,
            "path": str(episode.audio_path),
            "date": episode.date_str
        })

        return episode

    async def fetch_latest(self) -> Newsletter:
        """Fetches the latest newsletter content."""
        from podcast_generator.fetcher import fetch_latest_newsletter
        newsletter = await fetch_latest_newsletter(
            self.config.archive_url,
            load_more_selector=self.config.load_more_selector,
            link_pattern=self.config.link_pattern,
        )
        return newsletter
