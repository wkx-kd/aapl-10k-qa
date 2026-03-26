"""Orchestrates the full indexing pipeline: JSON → Milvus + SQLite + Neo4j."""

import logging
import time

from app.config import get_settings
from app.services.data_loader import load_records
from app.services.financial_parser import extract_financial_metrics
from app.services.graph_builder import build_knowledge_graph
from app.core.chunking import chunk_records
from app.core.embedding import encode_documents
from app.core.vector_store import VectorStore
from app.core.sql_store import SQLStore
from app.core.graph_store import GraphStore

logger = logging.getLogger(__name__)


def build_all_indexes(
    vector_store: VectorStore,
    sql_store: SQLStore,
    graph_store: GraphStore,
    force: bool = False,
):
    """Build all indexes from scratch.

    Args:
        force: If True, rebuild even if indexes already exist
    """
    settings = get_settings()
    start_time = time.time()

    logger.info("=" * 60)
    logger.info("Starting full index build pipeline")
    logger.info("=" * 60)

    # 1. Load raw data
    logger.info("[1/6] Loading data from JSON...")
    records = load_records(settings.data_path)
    logger.info(f"  Loaded {len(records)} records")

    # 2. Extract and store financial metrics in SQLite
    logger.info("[2/6] Extracting financial metrics → SQLite...")
    financial_metrics = extract_financial_metrics(records)
    sql_store.init_tables()
    sql_store.insert_metrics(financial_metrics)
    logger.info(f"  Stored metrics for {len(financial_metrics)} years")

    # 3. Chunk documents
    logger.info("[3/6] Chunking documents...")
    chunks = chunk_records(
        records,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    logger.info(f"  Created {len(chunks)} chunks")

    # 4. Generate embeddings and store in Milvus
    logger.info("[4/6] Generating BGE-M3 embeddings...")
    texts = [c["text"] for c in chunks]
    embeddings = encode_documents(texts, batch_size=32)
    logger.info(f"  Generated {len(texts)} dense + sparse vectors")

    logger.info("[5/6] Storing vectors in Milvus...")
    vector_store.create_collection(drop_existing=force)
    # Insert in batches
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i : i + batch_size]
        batch_dense = embeddings["dense"][i : i + batch_size]
        batch_sparse = embeddings["sparse"][i : i + batch_size]
        vector_store.insert(batch_chunks, batch_dense, batch_sparse)
    logger.info(f"  Stored {len(chunks)} chunks in Milvus")

    # 5. Build knowledge graph in Neo4j
    logger.info("[6/6] Building knowledge graph in Neo4j...")
    build_knowledge_graph(graph_store, records, financial_metrics)
    logger.info("  Knowledge graph built")

    elapsed = time.time() - start_time
    logger.info("=" * 60)
    logger.info(f"Index build complete in {elapsed:.1f}s")
    logger.info(f"  Chunks in Milvus: {vector_store.get_count()}")
    logger.info(f"  SQLite initialized: {sql_store.is_initialized()}")
    logger.info(f"  Neo4j populated: {graph_store.has_data()}")
    logger.info("=" * 60)


def check_indexes_exist(
    vector_store: VectorStore,
    sql_store: SQLStore,
    graph_store: GraphStore,
) -> bool:
    """Check if all indexes have been built."""
    try:
        milvus_ok = vector_store.collection_exists()
        sql_ok = sql_store.is_initialized()
        neo4j_ok = graph_store.has_data()

        logger.info(
            f"Index status: Milvus={milvus_ok}, SQLite={sql_ok}, Neo4j={neo4j_ok}"
        )
        return milvus_ok and sql_ok and neo4j_ok
    except Exception as e:
        logger.warning(f"Error checking indexes: {e}")
        return False
