import asyncio
import uuid
from typing import Any

import httpx


class LineMessagingError(RuntimeError):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(f"LINE Messaging API returned {status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail


class LineMessagingService:
    def __init__(
        self,
        *,
        channel_access_token: str,
        base_url: str,
        timeout_seconds: float,
        max_retries: int,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._max_retries = max_retries
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout_seconds,
            transport=transport,
            headers={
                "Authorization": f"Bearer {channel_access_token}",
                "Content-Type": "application/json",
            },
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def push_text(
        self,
        *,
        user_id: str,
        text: str,
        notification_disabled: bool = False,
    ) -> str:
        return await self._push(
            user_id=user_id,
            messages=[{"type": "text", "text": text}],
            notification_disabled=notification_disabled,
        )

    async def push_flex(
        self,
        *,
        user_id: str,
        alt_text: str,
        contents: dict[str, Any],
        notification_disabled: bool = False,
    ) -> str:
        return await self._push(
            user_id=user_id,
            messages=[
                {
                    "type": "flex",
                    "altText": alt_text,
                    "contents": contents,
                }
            ],
            notification_disabled=notification_disabled,
        )

    async def reply_text(self, *, reply_token: str, text: str) -> None:
        response = await self._client.post(
            "/v2/bot/message/reply",
            json={
                "replyToken": reply_token,
                "messages": [{"type": "text", "text": text}],
            },
        )
        if response.status_code >= 400:
            raise LineMessagingError(response.status_code, _response_detail(response))

    async def _push(
        self,
        *,
        user_id: str,
        messages: list[dict[str, Any]],
        notification_disabled: bool,
    ) -> str:
        retry_key = str(uuid.uuid4())
        payload = {
            "to": user_id,
            "messages": messages,
            "notificationDisabled": notification_disabled,
        }
        headers = {"X-Line-Retry-Key": retry_key}

        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.post(
                    "/v2/bot/message/push",
                    json=payload,
                    headers=headers,
                )
            except (httpx.ConnectError, httpx.ReadTimeout) as exc:
                if attempt == self._max_retries:
                    raise LineMessagingError(503, "LINE Messaging API is unavailable") from exc
                await asyncio.sleep(0.25 * (2**attempt))
                continue

            if response.status_code < 400:
                return retry_key

            if (
                response.status_code not in {429, 500, 502, 503, 504}
                or attempt == self._max_retries
            ):
                detail = _response_detail(response)
                raise LineMessagingError(response.status_code, detail)

            retry_after = response.headers.get("Retry-After")
            delay = (
                float(retry_after) if retry_after and retry_after.isdigit() else 0.25 * (2**attempt)
            )
            await asyncio.sleep(min(delay, 5.0))

        raise LineMessagingError(503, "LINE Messaging API is unavailable")


def _response_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
        if isinstance(payload, dict) and isinstance(payload.get("message"), str):
            return payload["message"]
    except ValueError:
        pass
    return response.text[:500] or "Unknown error"
