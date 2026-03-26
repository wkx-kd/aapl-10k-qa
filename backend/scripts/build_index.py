"""CLI script to build all indexes."""

import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    from app.config import get_settings
    from app.core.vector_store import VectorStore
    from app.core.sql_store import SQLStore
    from app.core.graph_store import GraphStore
    from app.services.indexer import build_all_indexes, check_indexes_exist

    settings = get_settings()

    # Parse args
    skip_if_exists = "--skip-if-exists" in sys.argv
    force = "--force" in sys.argv

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

    # Check if indexes already exist
    if skip_if_exists and not force:
        if check_indexes_exist(vector_store, sql_store, graph_store):
            logger.info("All indexes already exist. Skipping build.")
            return

    # Build indexes
    try:
        build_all_indexes(
            vector_store=vector_store,
            sql_store=sql_store,
            graph_store=graph_store,
            force=force,
        )
    except Exception as e:
        logger.error(f"Index build failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        sql_store.close()
        graph_store.close()


if __name__ == "__main__":
    main()
