"""Search API endpoint for direct hybrid retrieval."""

import logging

from fastapi import APIRouter, Request

from app.models.schemas import SearchRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/search")
async def search(request: Request, search_req: SearchRequest):
    """Perform hybrid search without LLM generation."""
    pipeline = request.app.state.pipeline

    result = await pipeline.search_only(
        query=search_req.query,
        filters=search_req.filters,
        top_k=search_req.top_k,
    )

    return result
