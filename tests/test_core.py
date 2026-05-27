import pytest
from unittest.mock import AsyncMock, patch
from src.builder import generate_script_daily

@pytest.mark.asyncio
async def test_generate_script_daily(mock_config, mock_newsletter):
    with patch("src.builder.translate_newsletter", return_value="Translated Script") as mock_translate:
        script = await generate_script_daily(mock_config, mock_newsletter)
        assert script == "Translated Script"
        mock_translate.assert_called_once()

def test_config_validation():
    from src.config import Config
    cfg = Config(gemini_api_key="", newsletter_url="")
    with pytest.raises(ValueError):
        cfg.validate()

    cfg2 = Config(gemini_api_key="key", newsletter_url="url")
    cfg2.validate() # Should not raise
