from dataclasses import dataclass, field
from pathlib import Path
import os

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    gemini_api_key: str = field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY", "")
    )
    gemini_model: str = field(
        default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    )
    tts_voice: str = field(
        default_factory=lambda: os.getenv(
            "TTS_VOICE", "it-IT-GiuseppeNeural"
        )
    )
    output_dir: Path = field(
        default_factory=lambda: Path(
            os.getenv("OUTPUT_DIR", "./output")
        )
    )
    max_episode_minutes: int = field(
        default_factory=lambda: int(os.getenv("MAX_EPISODE_MINUTES", "60"))
    )

    # Fonte delle news
    source_name: str = field(
        default_factory=lambda: os.getenv("SOURCE_NAME", "newsletter")
    )
    newsletter_url: str = field(
        default_factory=lambda: os.getenv("NEWSLETTER_URL", "")
    )
    archive_url: str = field(
        default_factory=lambda: os.getenv("ARCHIVE_URL", "")
    )

    # Selettori per lo scraper (default Beehiiv)
    load_more_selector: str = field(
        default_factory=lambda: os.getenv(
            "LOAD_MORE_SELECTOR",
            "button:has-text('Load More'), a:has-text('Load More')",
        )
    )
    link_pattern: str = field(
        default_factory=lambda: os.getenv("LINK_PATTERN", "/p/")
    )

    def __post_init__(self):
        if not self.archive_url and self.newsletter_url:
            self.archive_url = f"{self.newsletter_url}/archive"

    def validate(self):
        missing = []
        if not self.gemini_api_key:
            missing.append("GEMINI_API_KEY")
        if not self.archive_url:
            missing.append("NEWSLETTER_URL o ARCHIVE_URL")
        if missing:
            raise ValueError(
                f"Missing required env vars: {', '.join(missing)}. "
                f"Copia .env.example in .env e compilalo."
            )
