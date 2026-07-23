from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class TextMessageRequest(BaseModel):
    user_id: str | None = Field(default=None, min_length=1, max_length=128)
    text: str = Field(min_length=1, max_length=5000)
    notification_disabled: bool = False


class FlexContainer(BaseModel):
    model_config = {"extra": "allow"}

    type: Literal["bubble", "carousel"]


class FlexMessageRequest(BaseModel):
    user_id: str | None = Field(default=None, min_length=1, max_length=128)
    alt_text: str = Field(min_length=1, max_length=400)
    contents: dict[str, Any]
    notification_disabled: bool = False

    @model_validator(mode="after")
    def validate_contents_type(self) -> "FlexMessageRequest":
        FlexContainer.model_validate(self.contents)
        return self


class MessageAccepted(BaseModel):
    status: Literal["sent"] = "sent"
    request_id: str


class HealthStatus(BaseModel):
    status: Literal["ok", "not_ready"]
