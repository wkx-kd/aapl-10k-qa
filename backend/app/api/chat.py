"""Chat API endpoint with SSE streaming."""

import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.models.schemas import ChatRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat")
async def chat(request: Request, chat_req: ChatRequest):
    """Stream a RAG response via Server-Sent Events."""
    pipeline = request.app.state.pipeline

    async def event_stream():
        try:
            async for event in pipeline.query(
                query=chat_req.query,
                filters=chat_req.filters,
                history=chat_req.history,
                top_k=chat_req.top_k,
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"Chat stream error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
