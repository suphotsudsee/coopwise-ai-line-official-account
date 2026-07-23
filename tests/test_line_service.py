import httpx
import pytest

from app.services.line import LineMessagingError, LineMessagingService


@pytest.mark.asyncio
async def test_push_text_sends_expected_request() -> None:
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        return httpx.Response(200, json={})

    service = LineMessagingService(
        channel_access_token="token",
        base_url="https://api.line.test",
        timeout_seconds=1,
        max_retries=0,
        transport=httpx.MockTransport(handler),
    )
    try:
        request_id = await service.push_text(user_id="U123", text="hello")
        request = captured["request"]
        assert isinstance(request, httpx.Request)
        assert request.headers["Authorization"] == "Bearer token"
        assert request.headers["X-Line-Retry-Key"] == request_id
        assert b'"to":"U123"' in request.content
    finally:
        await service.close()


@pytest.mark.asyncio
async def test_push_text_hides_line_error_detail() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"message": "invalid user"})

    service = LineMessagingService(
        channel_access_token="token",
        base_url="https://api.line.test",
        timeout_seconds=1,
        max_retries=0,
        transport=httpx.MockTransport(handler),
    )
    try:
        with pytest.raises(LineMessagingError) as error:
            await service.push_text(user_id="bad", text="hello")
        assert error.value.status_code == 400
        assert error.value.detail == "invalid user"
    finally:
        await service.close()
