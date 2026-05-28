import logging
from abc import ABC, abstractmethod
from typing import Any
from podcast_generator.config import Settings

class BaseAgent(ABC):
    """Base class for all specialized agents in PodcastGen v3.0."""

    def __init__(self, config: Settings):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    @abstractmethod
    async def start(self):
        """Initialize and start the agent's background tasks."""
        pass

    @abstractmethod
    async def stop(self):
        """Gracefully stop the agent."""
        pass

    async def emit_event(self, event_type: str, data: Any):
        """Emit an event that other agents or the system might be interested in."""
        self.logger.info(f"Event Emitted: {event_type} - {data}")
