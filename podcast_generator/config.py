from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # === LLM Provider ===
    llm_provider: str = Field(
        default="gemini",
        description="LLM provider: gemini, openai, anthropic, ollama",
    )

    # Gemini
    gemini_api_key: str = Field(default="")
    gemini_model: str = Field(default="gemini-2.0-flash")

    # OpenAI
    openai_api_key: str = Field(default="")
    openai_model: str = Field(default="gpt-4o-mini")

    # Anthropic
    anthropic_api_key: str = Field(default="")
    anthropic_model: str = Field(default="claude-3-5-haiku-latest")

    # Ollama
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="llama3")

    # === TTS ===
    tts_provider: str = Field(
        default="edge",
        description="TTS provider: edge, elevenlabs",
    )
    tts_voice: str = Field(default="it-IT-GiuseppeNeural")
    elevenlabs_api_key: str = Field(default="")
    elevenlabs_voice: str = Field(default="")

    # === Newsletter Source ===
    source_name: str = Field(default="newsletter")
    newsletter_url: str = Field(default="")
    archive_url: str = Field(default="")

    # === Scraping Selectors (default Beehiiv) ===
    load_more_selector: str = Field(
        default="button:has-text('Load More'), a:has-text('Load More')"
    )
    link_pattern: str = Field(default="/p/")
    max_articles: int = Field(default=12, ge=1)

    # === Processing ===
    max_episode_minutes: int = Field(default=60, ge=1)
    output_dir: Path = Field(default=Path("./output"))
    use_web_search: bool = Field(default=False)

    # === Intro / Outro ===
    intro_path: Optional[Path] = Field(default=None)
    outro_path: Optional[Path] = Field(default=None)

    # === Web Auth ===
    web_password: str = Field(default="")
    api_token: str = Field(default="")
    web_secret_key: str = Field(default="change-me-in-production")
    web_port: int = Field(default=8000)
    web_host: str = Field(default="0.0.0.0")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    def model_post_init(self, __context):
        if not self.archive_url and self.newsletter_url:
            self.archive_url = f"{self.newsletter_url}/archive"

    def validate(self):
        missing = []
        if self.llm_provider == "gemini" and not self.gemini_api_key:
            missing.append("GEMINI_API_KEY")
        elif self.llm_provider == "openai" and not self.openai_api_key:
            missing.append("OPENAI_API_KEY")
        elif self.llm_provider == "anthropic" and not self.anthropic_api_key:
            missing.append("ANTHROPIC_API_KEY")
        if not self.archive_url:
            missing.append("NEWSLETTER_URL o ARCHIVE_URL")
        if missing:
            from podcast_generator.exceptions import ConfigError

            raise ConfigError(
                f"Missing required env vars: {', '.join(missing)}. "
                f"Copy .env.example to .env and fill it in."
            )
