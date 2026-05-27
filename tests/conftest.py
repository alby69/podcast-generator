import pytest
from unittest.mock import MagicMock
from src.config import Config

@pytest.fixture
def mock_config():
    return Config(
        gemini_api_key="test_key",
        newsletter_url="https://example.com/newsletter"
    )

@pytest.fixture
def mock_newsletter():
    from src.models import Newsletter
    from datetime import datetime
    return Newsletter(
        title="Test Title",
        url="https://example.com/p/test",
        date=datetime.now(),
        content="Test Content"
    )
