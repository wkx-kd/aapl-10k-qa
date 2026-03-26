from pydantic import BaseModel, Field
from typing import Optional


class ChatRequest(BaseModel):
    query: str
    filters: Optional[dict] = Field(default_factory=dict)
    history: list[dict] = Field(default_factory=list)
    top_k: int = 5
    stream: bool = True


class SearchRequest(BaseModel):
    query: str
    filters: Optional[dict] = Field(default_factory=dict)
    top_k: int = 10


class SearchResult(BaseModel):
    chunk_id: str
    text: str
    year: int
    section_title: str
    section_category: str
    score: float
    score_details: Optional[dict] = None


class SearchResponse(BaseModel):
    results: list[SearchResult]
    total: int
    query_time_ms: float


class FinancialMetric(BaseModel):
    year: int
    metric_name: str
    value: float
    category: str


class GraphEntity(BaseModel):
    name: str
    type: str
    properties: dict = Field(default_factory=dict)


class GraphRelation(BaseModel):
    source: str
    target: str
    relation_type: str
    properties: dict = Field(default_factory=dict)


class EvalRequest(BaseModel):
    categories: Optional[list[str]] = None
    top_k: int = 5


class EvalResult(BaseModel):
    run_id: str
    timestamp: str
    aggregate: dict
    per_question: list[dict]


class ChunkMetadata(BaseModel):
    chunk_id: str
    year: int
    section_id: int
    section_title: str
    section_category: str
    sub_section: Optional[str] = None
    chunk_index: int
    text: str
