import os

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

os.environ.setdefault("INTERNAL_API_KEY", "test-api-key-that-is-at-least-32-chars")
os.environ.setdefault("LINE_CHANNEL_ACCESS_TOKEN", "test-token")
os.environ.setdefault("LINE_CHANNEL_SECRET", "test-secret")

from app.api.routes import get_line_service
from app.config import Settings, get_settings
from app.main import create_app


class FakeLineService:
    def __init__(self) -> None:
        self.replies: list[dict[str, object]] = []

    async def push_text(self, **kwargs: object) -> str:
        self.last_text = kwargs
        return "11111111-1111-4111-8111-111111111111"

    async def push_flex(self, **kwargs: object) -> str:
        self.last_flex = kwargs
        return "22222222-2222-4222-8222-222222222222"

    async def reply_text(self, **kwargs: object) -> None:
        self.replies.append(kwargs)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        app_env="test",
        internal_api_key=SecretStr("test-api-key-that-is-at-least-32-chars"),
        line_channel_access_token=SecretStr("test-token"),
        line_channel_secret=SecretStr("test-secret"),
        line_default_destination_user_id="Udefault",
    )


@pytest.fixture
def fake_line_service() -> FakeLineService:
    return FakeLineService()


@pytest.fixture
def client(settings: Settings, fake_line_service: FakeLineService):
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_line_service] = lambda: fake_line_service
    with TestClient(app) as test_client:
        yield test_client
