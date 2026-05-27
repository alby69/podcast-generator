import pytest
from datetime import datetime

from podcast_generator.config import Settings


@pytest.fixture
def mock_config():
    return Settings(
        gemini_api_key="test_key",
        newsletter_url="https://example.com/newsletter",
    )


@pytest.fixture
def mock_newsletter():
    from podcast_generator.models import Newsletter

    return Newsletter(
        title="Test Title",
        url="https://example.com/p/test",
        date=datetime.now(),
        content="Test Content",
    )
