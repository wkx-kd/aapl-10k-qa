"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.llm_client import LLMClient
from app.core.vector_store import VectorStore
from app.core.sql_store import SQLStore
from app.core.graph_store import GraphStore
from app.core.intent_router import IntentRouter
from app.core.rag_pipeline import RAGPipeline

from app.api import chat, search, financial, graph, sections

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup application resources."""
    settings = get_settings()
    logger.info("Starting AAPL 10-K QA System...")

    # Initialize stores
    vector_store = VectorStore(
        host=settings.milvus_host,
        port=settings.milvus_port,
        collection_name=settings.milvus_collection,
    )
    vector_store.connect()

    sql_store = SQLStore(db_path=settings.db_path)

    graph_store = GraphStore(
        uri=settings.neo4j_uri,
        user=settings.neo4j_user,
        password=settings.neo4j_password,
    )
    graph_store.verify_connection()

    llm_client = LLMClient(
        base_url=settings.ollama_base_url,
        model=settings.llm_model,
    )

    # Build intent router and pipeline
    router = IntentRouter(
        llm_client=llm_client,
        vector_store=vector_store,
        sql_store=sql_store,
        graph_store=graph_store,
    )
    pipeline = RAGPipeline(router=router)

    # Store in app state
    app.state.vector_store = vector_store
    app.state.sql_store = sql_store
    app.state.graph_store = graph_store
    app.state.llm_client = llm_client
    app.state.pipeline = pipeline

    logger.info("All services initialized successfully")
    yield

    # Cleanup
    logger.info("Shutting down...")
    await llm_client.close()
    sql_store.close()
    graph_store.close()


app = FastAPI(
    title="AAPL 10-K Intelligent Q&A System",
    description="Multi-source RAG system with intent routing for Apple 10-K financial reports",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(search.router, prefix="/api", tags=["Search"])
app.include_router(financial.router, prefix="/api", tags=["Financial"])
app.include_router(graph.router, prefix="/api", tags=["Graph"])
app.include_router(sections.router, prefix="/api", tags=["Sections"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    settings = get_settings()
    return {
        "status": "ok",
        "service": "AAPL 10-K QA Backend",
        "model": settings.llm_model,
        "embedding": settings.embedding_model,
    }
