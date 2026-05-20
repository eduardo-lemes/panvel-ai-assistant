from enum import Enum

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: str = Field(min_length=1)
    message: str = Field(min_length=1)


class ChatEventType(str, Enum):
    TRACE = "trace"
    TOKEN = "token"
    SOURCE = "source"
    TOOL_CALL = "tool_call"
    DONE = "done"


class ChatEvent(BaseModel):
    event: ChatEventType
    data: dict[str, str]
