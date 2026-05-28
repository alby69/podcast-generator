import asyncio
from typing import Optional
from podcast_generator.agents.base import BaseAgent
from podcast_generator.config import Settings

try:
    from nostr_sdk import (
        Client,
        Keys,
        EventBuilder,
        Tag,
        Metadata,
        Event,
        Nip19Event,
        Filter,
        HandleNotification,
        RelayOptions,
        ClientBuilder
    )
except ImportError:
    # Fallback for environment where nostr-sdk is not yet installed
    Client = None

class NetworkAgent(BaseAgent):
    """Handles P2P identity and communication using the Nostr protocol."""

    def __init__(self, config: Settings, secret_key: Optional[str] = None):
        super().__init__(config)
        if Client is None:
            self.logger.error("nostr-sdk not installed. NetworkAgent will be dysfunctional.")
            self.client = None
            return

        if secret_key:
            self.keys = Keys.parse(secret_key)
        else:
            # In a real app, we'd load this from a secure store
            self.keys = Keys.generate()

        self.client = Client(self.keys)
        self.relays = ["wss://relay.damus.io", "wss://nos.lol", "wss://relay.snort.social"]

    async def start(self):
        if not self.client:
            return

        for relay in self.relays:
            await self.client.add_relay(relay)

        await self.client.connect()
        self.logger.info(f"Connected to Nostr as {self.keys.public_key().to_bech32()}")

    async def stop(self):
        if self.client:
            await self.client.disconnect()

    async def publish_podcast(self, title: str, ipfs_cid: str, metadata: dict):
        """Publishes a podcast episode as a Nostr event."""
        if not self.client:
            return

        content = f"New Podcast Episode: {title}\nListen on IPFS: ipfs://{ipfs_cid}"

        # NIP-94 style tags for file metadata could be added here
        tags = [
            Tag.parse(["t", "podcastgen"]),
            Tag.parse(["alt", content]),
            Tag.parse(["r", f"https://ipfs.io/ipfs/{ipfs_cid}"])
        ]

        event = EventBuilder(1, content, tags).to_event(self.keys)
        event_id = await self.client.send_event(event)
        self.logger.info(f"Published podcast event: {event_id.to_bech32()}")
        return event_id
