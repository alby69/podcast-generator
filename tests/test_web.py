import pytest
from fastapi.testclient import TestClient

from podcast_generator.web.app import app
from podcast_generator.web.db import init_db


@pytest.fixture(name="client")
def client_fixture():
    import os
    os.environ["DB_PATH"] = ":memory:"
    init_db()
    client = TestClient(app)
    yield client


def test_read_main(client: TestClient):
    response = client.get("/", follow_redirects=True)
    assert response.status_code == 200
    assert "Podcast Generator" in response.text


def test_rss_empty(client: TestClient):
    response = client.get("/rss")
    assert response.status_code == 200
    assert "application/xml" in response.headers["content-type"]
    assert "<channel>" in response.text


def test_api_no_auth_required_by_default(client: TestClient):
    response = client.get("/api/v1/episodes")
    assert response.status_code == 200


def test_api_requires_token_when_configured(client: TestClient):
    import os
    original = os.environ.get("API_TOKEN")
    os.environ["API_TOKEN"] = "test-token"

    response = client.get("/api/v1/episodes")
    assert response.status_code == 401

    response = client.get(
        "/api/v1/episodes",
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 200

    if original is None:
        del os.environ["API_TOKEN"]
    else:
        os.environ["API_TOKEN"] = original
