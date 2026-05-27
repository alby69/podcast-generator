import pytest
from unittest.mock import MagicMock, patch
from podcast_generator.fetcher import get_rss_articles, get_email_articles, fetch_email_content

@pytest.mark.asyncio
async def test_get_rss_articles():
    mock_feed = MagicMock()
    # Pydantic requires strings for ArticleSummary.date, so we need to mock appropriately
    entry1 = MagicMock(spec=["link", "title", "summary", "published"])
    entry1.link = "http://example.com/1"
    entry1.title = "Title 1"
    entry1.summary = "Summary 1"
    entry1.published = "2024-01-01"

    entry2 = MagicMock(spec=["link", "title", "summary", "updated"])
    entry2.link = "http://example.com/2"
    entry2.title = "Title 2"
    entry2.summary = "Summary 2"
    entry2.updated = "2024-01-02"

    mock_feed.entries = [entry1, entry2]

    with patch("feedparser.parse", return_value=mock_feed):
        articles = await get_rss_articles("http://example.com/rss")
        assert len(articles) == 2
        assert articles[0].text == "Title 1"
        assert articles[1].date == "2024-01-02"

@pytest.mark.asyncio
async def test_get_email_articles():
    mock_msg = MagicMock()
    mock_msg.uid = "123"
    mock_msg.subject = "Email Subject"
    mock_msg.text = "Email body text content"
    mock_msg.date = MagicMock()
    mock_msg.date.strftime.return_value = "2024-05-26 10:00:00"

    with patch("podcast_generator.fetcher.MailBox") as MockMailBox:
        mock_mailbox_instance = MockMailBox.return_value
        mock_mailbox_instance.login.return_value.__enter__.return_value.fetch.return_value = [mock_msg]

        articles = await get_email_articles("host", "user", "pass")
        assert len(articles) == 1
        assert articles[0].href == "email://123"
        assert articles[0].text == "Email Subject"

@pytest.mark.asyncio
async def test_fetch_email_content():
    mock_msg = MagicMock()
    mock_msg.uid = "123"
    mock_msg.subject = "Email Subject"
    mock_msg.html = "<html><body>Email HTML content</body></html>"
    mock_msg.text = "Email body text content"
    mock_msg.date = MagicMock()

    with patch("podcast_generator.fetcher.MailBox") as MockMailBox:
        mock_mailbox_instance = MockMailBox.return_value
        mock_mailbox_instance.login.return_value.__enter__.return_value.fetch.return_value = [mock_msg]

        with patch("trafilatura.extract", return_value="Extracted content"):
            newsletter = await fetch_email_content("host", "user", "pass", "123")
            assert newsletter.title == "Email Subject"
            assert newsletter.content == "Extracted content"
