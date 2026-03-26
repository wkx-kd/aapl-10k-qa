"""Knowledge graph API endpoints."""

import logging

from fastapi import APIRouter, Request, Query

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/graph/entities")
async def get_entities(request: Request):
    """Get all entities in the knowledge graph."""
    graph_store = request.app.state.graph_store
    entities = graph_store.get_all_entities()
    return entities


@router.get("/graph/query")
async def query_graph(
    request: Request,
    q: str = Query(..., description="Natural language query for the knowledge graph"),
):
    """Execute a natural language query against the knowledge graph."""
    graph_store = request.app.state.graph_store
    llm_client = request.app.state.llm_client

    schema = graph_store.get_schema_description()
    cypher = await llm_client.generate_cypher(q, schema)

    try:
        results = graph_store.execute_cypher(cypher)
        return {
            "query": q,
            "cypher": cypher,
            "results": results,
        }
    except ValueError as e:
        return {"error": str(e), "cypher": cypher}
