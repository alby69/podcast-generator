import pytest
from fastapi.testclient import TestClient
from src.web.app import app
from src.web.db import engine, EpisodeDB
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    from src.web.app import get_session
    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

def test_read_main(client: TestClient):
    response = client.get("/", follow_redirects=True)
    assert response.status_code == 200
    assert "Podcast Generator" in response.text

def test_login(client: TestClient):
    import os
    with patch.dict(os.environ, {"WEB_PASSWORD": "testpassword"}):
        # Unauthorized
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307

        # Correct login
        response = client.post("/login", data={"password": "testpassword"}, follow_redirects=False)
        assert response.status_code == 303
        assert "auth_token=testpassword" in response.headers["set-cookie"]

def test_rss_empty(client: TestClient):
    response = client.get("/rss")
    assert response.status_code == 200
    assert "application/xml" in response.headers["content-type"]
    assert "<channel>" in response.text

from unittest.mock import patch
