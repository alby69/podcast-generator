from typing import List
from podcast_generator.agents.base import BaseAgent
from podcast_generator.config import Settings

try:
    from nostr_sdk import (
        Filter,
        Kind,
        Timestamp
    )
except ImportError:
    Filter = None
    Kind = None

class SocialAgent(BaseAgent):
    """Manages community interactions, discovery, and social graph via Nostr."""

    def __init__(self, config: Settings, network_agent=None):
        super().__init__(config)
        self.network_agent = network_agent

    async def start(self):
        self.logger.info("SocialAgent monitoring decentralized feed...")

    async def stop(self):
        pass

    async def discover_podcasts(self, hours: int = 24) -> List[dict]:
        """Discovers recent podcast events on the network."""
        if not self.network_agent or not self.network_agent.client:
            self.logger.warning("SocialAgent requires a started NetworkAgent for discovery.")
            return []

        self.logger.info(f"Scanning Nostr for podcasts from the last {hours} hours...")

        kind_1063 = Kind(1063) if Kind else 1063
        since = (Timestamp.now().as_secs() if Timestamp else 0) - (hours * 3600)

        # Filter for Kind 1063 with tag 't' = 'podcastgen'
        try:
            f = Filter().kind(kind_1063).custom_tag("t", ["podcastgen"]).since(Timestamp.from_secs(since))
            events = await self.network_agent.client.get_events_of([f], None)
        except Exception as e:
            self.logger.error(f"Error fetching events: {e}")
            return []

        podcasts = []
        for event in events:
            p = {
                "id": event.id().to_bech32(),
                "pubkey": event.author().to_bech32(),
                "created_at": event.created_at().to_human_datetime(),
                "title": "Untitled",
                "url": ""
            }
            # Parse tags
            for tag in event.tags():
                t_list = tag.as_vec()
                if len(t_list) >= 2:
                    if t_list[0] == "title":
                        p["title"] = t_list[1]
                    elif t_list[0] == "url":
                        p["url"] = t_list[1]

            podcasts.append(p)

        self.logger.info(f"Discovered {len(podcasts)} podcasts.")
        return podcasts

    async def handle_new_episode(self, episode_title: str, nostr_event_id: str):
        """Reacts to a new episode being published on the network."""
        self.logger.info(f"Broadcasting social interaction for {episode_title}...")
        # Future: auto-like or auto-comment on own episodes if configured
        pass
