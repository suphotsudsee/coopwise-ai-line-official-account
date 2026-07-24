import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.config import Settings, get_settings
from app.services.line import LineMessagingService


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    configured_settings = settings or get_settings()
    configure_logging(configured_settings.app_log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.line_service = LineMessagingService(
            channel_access_token=configured_settings.line_channel_access_token.get_secret_value(),
            base_url=configured_settings.line_api_base_url,
            timeout_seconds=configured_settings.line_request_timeout_seconds,
            max_retries=configured_settings.line_max_retries,
        )
        yield
        await app.state.line_service.close()

    docs_url = "/docs" if configured_settings.app_docs_enabled else None
    openapi_url = "/openapi.json" if configured_settings.app_docs_enabled else None
    app = FastAPI(
        title="CoopWise AI LINE Gateway",
        version="0.1.0",
        docs_url=docs_url,
        redoc_url=None,
        openapi_url=openapi_url,
        lifespan=lifespan,
    )
    app.include_router(router)
    return app


app = create_app()
