"""CLI script to run evaluation."""

import sys
import asyncio
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    from app.config import get_settings
    from app.core.vector_store import VectorStore
    from app.core.sql_store import SQLStore
    from app.core.graph_store import GraphStore
    from app.core.llm_client import LLMClient
    from app.core.intent_router import IntentRouter
    from evaluation.evaluator import Evaluator

    settings = get_settings()

    # Parse args
    categories = None
    for i, arg in enumerate(sys.argv):
        if arg == "--category" and i + 1 < len(sys.argv):
            categories = sys.argv[i + 1].split(",")
        elif arg == "--categories" and i + 1 < len(sys.argv):
            categories = sys.argv[i + 1].split(",")

    top_k = 5
    for i, arg in enumerate(sys.argv):
        if arg == "--top-k" and i + 1 < len(sys.argv):
            top_k = int(sys.argv[i + 1])

    # Initialize components
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

    llm_client = LLMClient(
        base_url=settings.ollama_base_url,
        model=settings.llm_model,
    )

    router = IntentRouter(
        llm_client=llm_client,
        vector_store=vector_store,
        sql_store=sql_store,
        graph_store=graph_store,
    )

    evaluator = Evaluator(
        intent_router=router,
        sql_store=sql_store,
        vector_store=vector_store,
        graph_store=graph_store,
        llm_client=llm_client,
    )

    try:
        result = await evaluator.run_evaluation(
            categories=categories, top_k=top_k
        )
        print(f"\nResults saved to: evaluation/results/{result['run_id']}.json")
    except Exception as e:
        logger.error(f"Evaluation failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await llm_client.close()
        sql_store.close()
        graph_store.close()


if __name__ == "__main__":
    asyncio.run(main())
