"""Async Ollama LLM client for generation, classification, and structured queries."""

import json
import logging
from typing import AsyncGenerator, Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Async client for Ollama API."""

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        settings = get_settings()
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.llm_model
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url, timeout=120.0
            )
        return self._client

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        """Generate a complete response (non-streaming)."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await self.client.post(
            "/api/chat",
            json={
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            },
        )
        response.raise_for_status()
        data = response.json()
        return data.get("message", {}).get("content", "")

    async def generate_stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        history: Optional[list[dict]] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response, yielding tokens."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        async with self.client.stream(
            "POST",
            "/api/chat",
            json={
                "model": self.model,
                "messages": messages,
                "stream": True,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            },
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    content = data.get("message", {}).get("content", "")
                    if content:
                        yield content
                    if data.get("done"):
                        break
                except json.JSONDecodeError:
                    continue

    async def classify(
        self,
        prompt: str,
        system: str,
        valid_labels: list[str],
    ) -> str:
        """Classify input into one of the valid labels."""
        response = await self.generate(
            prompt=prompt, system=system, temperature=0.0, max_tokens=50
        )

        # Extract label from response
        response_lower = response.strip().lower()
        for label in valid_labels:
            if label.lower() in response_lower:
                return label

        # Default fallback
        logger.warning(
            f"Could not classify response '{response}' into {valid_labels}, "
            f"defaulting to 'narrative'"
        )
        return "narrative"

    async def generate_sql(self, query: str, schema: str) -> str:
        """Generate a SQL query from natural language."""
        system = f"""You are a SQL expert. Generate a SQLite SELECT query based on the user's question.

{schema}

Rules:
- Only output a single SELECT statement, nothing else
- Do not include any explanation, just the SQL
- Use proper column names from the schema above
- For monetary values, they are stored as raw numbers (e.g., 416161000000.0 for $416.161 billion)
- Margins are stored as decimals (e.g., 0.469 for 46.9%)"""

        response = await self.generate(
            prompt=query, system=system, temperature=0.0, max_tokens=300
        )

        # Clean the response - extract SQL
        sql = response.strip()
        # Remove markdown code blocks if present
        if sql.startswith("```"):
            lines = sql.split("\n")
            sql = "\n".join(
                l for l in lines if not l.startswith("```")
            ).strip()
        # Remove trailing semicolons
        sql = sql.rstrip(";")

        return sql

    async def generate_cypher(self, query: str, schema: str) -> str:
        """Generate a Cypher query from natural language."""
        system = f"""You are a Neo4j Cypher expert. Generate a read-only Cypher query based on the user's question.

{schema}

Rules:
- Only output a single MATCH...RETURN statement, nothing else
- Do not include any explanation, just the Cypher query
- Always start with MATCH
- Use the exact node labels and relationship types from the schema
- The company name is 'Apple Inc.'"""

        response = await self.generate(
            prompt=query, system=system, temperature=0.0, max_tokens=300
        )

        cypher = response.strip()
        if cypher.startswith("```"):
            lines = cypher.split("\n")
            cypher = "\n".join(
                l for l in lines if not l.startswith("```")
            ).strip()

        return cypher

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
