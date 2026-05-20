from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.application.services.chat import stream_chat_events
from app.domain.models.chat import ChatRequest


router = APIRouter()


@router.post("/chat/stream", summary="Stream chat response")
def chat_stream(payload: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        stream_chat_events(payload),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
