"""Multi-source RAG pipeline orchestration."""

import logging
from typing import AsyncGenerator, Optional

from app.core.intent_router import IntentRouter

logger = logging.getLogger(__name__)


class RAGPipeline:
    """High-level RAG pipeline that wraps IntentRouter for the API layer."""

    def __init__(self, router: IntentRouter):
        self.router = router

    async def query(
        self,
        query: str,
        filters: Optional[dict] = None,
        history: Optional[list[dict]] = None,
        top_k: int = 5,
    ) -> AsyncGenerator[dict, None]:
        """Process a query through the full RAG pipeline.

        Yields SSE-formatted events.
        """
        async for event in self.router.route_and_generate(
            query=query,
            filters=filters,
            history=history,
            top_k=top_k,
        ):
            yield event

    async def search_only(
        self,
        query: str,
        filters: Optional[dict] = None,
        top_k: int = 10,
    ) -> dict:
        """Perform hybrid search without LLM generation."""
        from app.core.embedding import encode_query
        from app.core.intent_router import _build_filter_expr
        import time

        start = time.time()
        query_vectors = encode_query(query)
        filter_expr = _build_filter_expr(filters)

        results = self.router.vector_store.hybrid_search(
            dense_vector=query_vectors["dense"],
            sparse_vector=query_vectors["sparse"],
            top_k=top_k,
            filter_expr=filter_expr,
        )

        elapsed = (time.time() - start) * 1000

        return {
            "results": results,
            "total": len(results),
            "query_time_ms": round(elapsed, 1),
        }
