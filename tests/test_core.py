import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_config_validation():
    from podcast_generator.config import Settings
    from podcast_generator.exceptions import ConfigError

    cfg = Settings(gemini_api_key="", newsletter_url="")
    with pytest.raises(ConfigError):
        cfg.validate()

    cfg2 = Settings(gemini_api_key="key", newsletter_url="https://example.com")
    cfg2.validate()


@pytest.mark.asyncio
async def test_podcast_generator_init():
    from podcast_generator.builder import PodcastGenerator
    from podcast_generator.config import Settings

    gen = PodcastGenerator()
    assert gen.config is not None

    cfg = Settings(gemini_api_key="test")
    gen2 = PodcastGenerator(cfg)
    assert gen2.config.gemini_api_key == "test"


@pytest.mark.asyncio
async def test_translate_newsletter(mock_config):
    from podcast_generator.translator import translate_newsletter

    with patch(
        "podcast_generator.translator.GeminiProvider.generate",
        new_callable=AsyncMock,
        return_value="Ciao a tutti e benvenuti...",
    ):
        result = await translate_newsletter(mock_config, "Test content")
        assert "Ciao a tutti" in result
