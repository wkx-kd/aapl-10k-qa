"""LLM-based intent classification and query routing."""

import asyncio
import json
import logging
import time
from typing import AsyncGenerator, Optional

from app.core.llm_client import LLMClient
from app.core.vector_store import VectorStore
from app.core.sql_store import SQLStore
from app.core.graph_store import GraphStore
from app.core.embedding import encode_query
from app.models.prompts import (
    INTENT_CLASSIFICATION_SYSTEM,
    RAG_SYSTEM_PROMPT,
    RAG_USER_PROMPT,
    RAG_USER_PROMPT_WITH_DATA,
    SQL_ANSWER_SYSTEM,
    SQL_ANSWER_USER,
    CYPHER_ANSWER_SYSTEM,
    CYPHER_ANSWER_USER,
    HYBRID_SYSTEM,
    HYBRID_USER,
)

logger = logging.getLogger(__name__)

VALID_INTENTS = ["quantitative", "narrative", "relationship", "hybrid"]


class IntentRouter:
    """Routes user queries to appropriate data sources based on LLM intent classification."""

    def __init__(
        self,
        llm_client: LLMClient,
        vector_store: VectorStore,
        sql_store: SQLStore,
        graph_store: GraphStore,
    ):
        self.llm = llm_client
        self.vector_store = vector_store
        self.sql_store = sql_store
        self.graph_store = graph_store

    async def classify_intent(self, query: str) -> str:
        """Classify the intent of a user query."""
        intent = await self.llm.classify(
            prompt=query,
            system=INTENT_CLASSIFICATION_SYSTEM,
            valid_labels=VALID_INTENTS,
        )
        logger.info(f"Query intent: {intent} for: {query[:80]}...")
        return intent

    async def route_and_generate(
        self,
        query: str,
        filters: Optional[dict] = None,
        history: Optional[list[dict]] = None,
        top_k: int = 5,
    ) -> AsyncGenerator[dict, None]:
        """Route query and stream response as SSE events.

        Yields dicts:
            {"type": "intent", "intent": "quantitative"}
            {"type": "sources", "sources": [...]}
            {"type": "token", "content": "..."}
            {"type": "done"}
            {"type": "error", "message": "..."}
        """
        try:
            # Step 1: Classify intent
            intent = await self.classify_intent(query)
            yield {"type": "intent", "intent": intent}

            # Step 2: Route to appropriate handler
            if intent == "quantitative":
                async for event in self._handle_quantitative(query, history):
                    yield event
            elif intent == "narrative":
                async for event in self._handle_narrative(query, filters, history, top_k):
                    yield event
            elif intent == "relationship":
                async for event in self._handle_relationship(query, history):
                    yield event
            elif intent == "hybrid":
                async for event in self._handle_hybrid(query, filters, history, top_k):
                    yield event
            else:
                async for event in self._handle_narrative(query, filters, history, top_k):
                    yield event

            yield {"type": "done"}

        except Exception as e:
            logger.error(f"Route error: {e}", exc_info=True)
            yield {"type": "error", "message": str(e)}

    async def _handle_quantitative(
        self, query: str, history: Optional[list[dict]]
    ) -> AsyncGenerator[dict, None]:
        """Handle quantitative queries via Text-to-SQL."""
        try:
            # Generate SQL
            schema = self.sql_store.get_table_schema()
            sql = await self.llm.generate_sql(query, schema)
            logger.info(f"Generated SQL: {sql}")

            # Execute SQL
            results = self.sql_store.execute_safe_query(sql)
            results_str = json.dumps(results, indent=2, default=str)

            yield {
                "type": "sources",
                "sources": [{
                    "type": "sql",
                    "query": sql,
                    "results": results,
                }],
            }

            # Generate natural language answer
            prompt = SQL_ANSWER_USER.format(
                query=query, sql=sql, results=results_str
            )
            async for token in self.llm.generate_stream(
                prompt=prompt,
                system=SQL_ANSWER_SYSTEM,
                history=history,
            ):
                yield {"type": "token", "content": token}

        except ValueError as e:
            logger.warning(f"SQL error: {e}, falling back to narrative")
            async for event in self._handle_narrative(query, None, history, 5):
                yield event

    async def _handle_narrative(
        self,
        query: str,
        filters: Optional[dict],
        history: Optional[list[dict]],
        top_k: int,
    ) -> AsyncGenerator[dict, None]:
        """Handle narrative queries via vector search + RAG."""
        # Encode query
        query_vectors = encode_query(query)

        # Build filter expression
        filter_expr = _build_filter_expr(filters)

        # Hybrid search
        results = self.vector_store.hybrid_search(
            dense_vector=query_vectors["dense"],
            sparse_vector=query_vectors["sparse"],
            top_k=top_k,
            filter_expr=filter_expr,
        )

        yield {
            "type": "sources",
            "sources": [
                {
                    "type": "vector",
                    "chunk_id": r["chunk_id"],
                    "year": r["year"],
                    "section_title": r["section_title"],
                    "section_category": r["section_category"],
                    "score": r["score"],
                    "text": r["text"][:500],
                }
                for r in results
            ],
        }

        # Assemble context
        context = _assemble_context(results)
        prompt = RAG_USER_PROMPT.format(context=context, query=query)

        async for token in self.llm.generate_stream(
            prompt=prompt,
            system=RAG_SYSTEM_PROMPT,
            history=history,
        ):
            yield {"type": "token", "content": token}

    async def _handle_relationship(
        self, query: str, history: Optional[list[dict]]
    ) -> AsyncGenerator[dict, None]:
        """Handle relationship queries via Neo4j knowledge graph."""
        try:
            schema = self.graph_store.get_schema_description()
            cypher = await self.llm.generate_cypher(query, schema)
            logger.info(f"Generated Cypher: {cypher}")

            results = self.graph_store.execute_cypher(cypher)
            results_str = json.dumps(results, indent=2, default=str)

            yield {
                "type": "sources",
                "sources": [{
                    "type": "graph",
                    "query": cypher,
                    "results": results,
                }],
            }

            prompt = CYPHER_ANSWER_USER.format(
                query=query, results=results_str
            )
            async for token in self.llm.generate_stream(
                prompt=prompt,
                system=CYPHER_ANSWER_SYSTEM,
                history=history,
            ):
                yield {"type": "token", "content": token}

        except ValueError as e:
            logger.warning(f"Cypher error: {e}, falling back to narrative")
            async for event in self._handle_narrative(query, None, history, 5):
                yield event

    async def _handle_hybrid(
        self,
        query: str,
        filters: Optional[dict],
        history: Optional[list[dict]],
        top_k: int,
    ) -> AsyncGenerator[dict, None]:
        """Handle hybrid queries combining SQL + vector search."""
        sources = []

        # Run SQL and vector search in parallel
        async def get_sql_data():
            try:
                schema = self.sql_store.get_table_schema()
                sql = await self.llm.generate_sql(query, schema)
                results = self.sql_store.execute_safe_query(sql)
                return {"sql": sql, "results": results}
            except Exception as e:
                logger.warning(f"SQL in hybrid failed: {e}")
                return None

        async def get_vector_data():
            query_vectors = encode_query(query)
            filter_expr = _build_filter_expr(filters)
            return self.vector_store.hybrid_search(
                dense_vector=query_vectors["dense"],
                sparse_vector=query_vectors["sparse"],
                top_k=top_k,
                filter_expr=filter_expr,
            )

        sql_data, vector_results = await asyncio.gather(
            get_sql_data(), get_vector_data()
        )

        # Build sources
        if sql_data:
            sources.append({
                "type": "sql",
                "query": sql_data["sql"],
                "results": sql_data["results"],
            })

        sources.extend([
            {
                "type": "vector",
                "chunk_id": r["chunk_id"],
                "year": r["year"],
                "section_title": r["section_title"],
                "score": r["score"],
                "text": r["text"][:500],
            }
            for r in vector_results
        ])

        yield {"type": "sources", "sources": sources}

        # Build context
        context = _assemble_context(vector_results)
        financial_data = (
            json.dumps(sql_data["results"], indent=2, default=str)
            if sql_data
            else "No structured data available"
        )

        prompt = HYBRID_USER.format(
            financial_data=financial_data,
            context=context,
            query=query,
        )

        async for token in self.llm.generate_stream(
            prompt=prompt,
            system=HYBRID_SYSTEM,
            history=history,
        ):
            yield {"type": "token", "content": token}


def _build_filter_expr(filters: Optional[dict]) -> Optional[str]:
    """Build Milvus filter expression from user filters."""
    if not filters:
        return None

    conditions = []

    years = filters.get("years", [])
    if years:
        years_str = ", ".join(str(y) for y in years)
        conditions.append(f"year in [{years_str}]")

    sections = filters.get("sections", [])
    if sections:
        sections_str = ", ".join(f'"{s}"' for s in sections)
        conditions.append(f"section_category in [{sections_str}]")

    return " and ".join(conditions) if conditions else None


def _assemble_context(results: list[dict], max_chars: int = 12000) -> str:
    """Assemble retrieved chunks into context string."""
    # Sort by year then section_id for coherent reading
    sorted_results = sorted(
        results, key=lambda x: (x.get("year", 0), x.get("section_id", 0))
    )

    context_parts = []
    total_chars = 0

    for r in sorted_results:
        text = r.get("text", "")
        header = f"[{r.get('year', '?')} | {r.get('section_title', '?')}]"
        chunk = f"{header}\n{text}"

        if total_chars + len(chunk) > max_chars:
            break

        context_parts.append(chunk)
        total_chars += len(chunk)

    return "\n\n---\n\n".join(context_parts)
