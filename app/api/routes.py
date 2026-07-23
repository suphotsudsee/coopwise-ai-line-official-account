import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from app.config import Settings, get_settings
from app.schemas import (
    FlexMessageRequest,
    HealthStatus,
    MessageAccepted,
    TextMessageRequest,
)
from app.security import require_internal_api_key, verify_line_signature
from app.services.line import LineMessagingError, LineMessagingService

logger = logging.getLogger(__name__)
router = APIRouter()
SettingsDependency = Annotated[Settings, Depends(get_settings)]


def get_line_service(request: Request) -> LineMessagingService:
    return request.app.state.line_service


LineServiceDependency = Annotated[LineMessagingService, Depends(get_line_service)]


def resolve_user_id(user_id: str | None, settings: Settings) -> str:
    destination = user_id or settings.line_default_destination_user_id
    if not destination:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="user_id is required when no default destination is configured",
        )
    return destination


@router.get("/health/live", response_model=HealthStatus, tags=["health"])
async def liveness() -> HealthStatus:
    return HealthStatus(status="ok")


@router.get("/health/ready", response_model=HealthStatus, tags=["health"])
async def readiness(request: Request) -> HealthStatus:
    if not hasattr(request.app.state, "line_service"):
        raise HTTPException(status_code=503, detail="LINE service is not initialized")
    return HealthStatus(status="ok")


@router.post("/webhooks/line", status_code=status.HTTP_200_OK, tags=["line"])
async def line_webhook(
    request: Request,
    settings: SettingsDependency,
    x_line_signature: Annotated[str | None, Header()] = None,
) -> dict[str, str]:
    body = await request.body()
    secret = settings.line_channel_secret.get_secret_value()
    if not x_line_signature or not verify_line_signature(body, x_line_signature, secret):
        raise HTTPException(status_code=401, detail="Invalid LINE signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    events = payload.get("events", [])
    if not isinstance(events, list):
        raise HTTPException(status_code=400, detail="Invalid events payload")

    for event in events:
        if isinstance(event, dict):
            source = event.get("source", {})
            logger.info(
                "LINE webhook event received",
                extra={
                    "line_event_type": event.get("type"),
                    "line_source_type": source.get("type") if isinstance(source, dict) else None,
                },
            )
    return {"status": "ok"}


@router.post(
    "/api/v1/messages/text",
    response_model=MessageAccepted,
    dependencies=[Depends(require_internal_api_key)],
    tags=["messages"],
)
async def send_text_message(
    payload: TextMessageRequest,
    settings: SettingsDependency,
    service: LineServiceDependency,
) -> MessageAccepted:
    user_id = resolve_user_id(payload.user_id, settings)
    try:
        request_id = await service.push_text(
            user_id=user_id,
            text=payload.text,
            notification_disabled=payload.notification_disabled,
        )
    except LineMessagingError as exc:
        logger.warning("LINE text push failed", extra={"line_status_code": exc.status_code})
        raise HTTPException(status_code=502, detail="LINE message delivery failed") from exc
    return MessageAccepted(request_id=request_id)


@router.post(
    "/api/v1/messages/flex",
    response_model=MessageAccepted,
    dependencies=[Depends(require_internal_api_key)],
    tags=["messages"],
)
async def send_flex_message(
    payload: FlexMessageRequest,
    settings: SettingsDependency,
    service: LineServiceDependency,
) -> MessageAccepted:
    user_id = resolve_user_id(payload.user_id, settings)
    try:
        request_id = await service.push_flex(
            user_id=user_id,
            alt_text=payload.alt_text,
            contents=payload.contents,
            notification_disabled=payload.notification_disabled,
        )
    except LineMessagingError as exc:
        logger.warning("LINE flex push failed", extra={"line_status_code": exc.status_code})
        raise HTTPException(status_code=502, detail="LINE message delivery failed") from exc
    return MessageAccepted(request_id=request_id)
