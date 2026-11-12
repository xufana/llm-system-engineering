import uuid
from enum import StrEnum

from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionUserMessageParam,
)
from pydantic import BaseModel, Field


class RolesEnum(StrEnum):
    USER = "user"
    ADMIN = "admin"


class ChatRequest(BaseModel):
    """
    Schema for chat request payload.
    """

    query: str = Field(..., description="User query string.")
    history: (
        list[ChatCompletionUserMessageParam | ChatCompletionAssistantMessageParam]
        | None
    ) = Field(None, description="User dialog history")
    role: RolesEnum = RolesEnum.USER
    session_id: str = Field(
        str(uuid.uuid4()), description="Optional session identifier for the chat."
    )


class ChatResponse(BaseModel):
    """
    Schema for chat response payload.
    """

    content: str = Field(..., description="Response content from the chat bot.")
