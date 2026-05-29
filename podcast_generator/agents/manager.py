import asyncio
from typing import Optional
from podcast_generator.agents.content_agent import ContentAgent
from podcast_generator.agents.network_agent import NetworkAgent
from podcast_generator.agents.storage_agent import StorageAgent
from podcast_generator.agents.social_agent import SocialAgent
from podcast_generator.config import Settings

_agents_instance = None

class AgentsManager:
    def __init__(self, config: Settings):
        self.config = config
        self.content = ContentAgent(config)
        self.network = NetworkAgent(config)
        self.storage = StorageAgent(config)
        self.social = SocialAgent(config, network_agent=self.network)
        self._started = False

    async def start(self):
        if self._started:
            return
        await self.content.start()
        await self.storage.start()
        await self.network.start()
        await self.social.start()
        self._started = True

    async def stop(self):
        if not self._started:
            return
        await self.content.stop()
        await self.storage.stop()
        await self.network.stop()
        await self.social.stop()
        self._started = False

def get_agents(config: Optional[Settings] = None) -> AgentsManager:
    global _agents_instance
    if _agents_instance is None:
        if config is None:
            from podcast_generator.config import Settings
            config = Settings()
        _agents_instance = AgentsManager(config)
    return _agents_instance
