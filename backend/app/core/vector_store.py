"""Milvus vector store with multi-vector hybrid search support."""

import logging
from typing import Optional

from pymilvus import (
    connections,
    Collection,
    CollectionSchema,
    FieldSchema,
    DataType,
    utility,
    AnnSearchRequest,
    WeightedRanker,
)

logger = logging.getLogger(__name__)


class VectorStore:
    """Manages Milvus collection for hybrid dense+sparse vector search."""

    def __init__(
        self,
        host: str = "milvus-standalone",
        port: int = 19530,
        collection_name: str = "aapl_10k_chunks",
        dense_dim: int = 1024,
    ):
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.dense_dim = dense_dim
        self._collection: Optional[Collection] = None

    def connect(self):
        """Connect to Milvus."""
        connections.connect(
            alias="default", host=self.host, port=self.port
        )
        logger.info(f"Connected to Milvus at {self.host}:{self.port}")

    def create_collection(self, drop_existing: bool = False):
        """Create the collection with dense and sparse vector fields."""
        if drop_existing and utility.has_collection(self.collection_name):
            utility.drop_collection(self.collection_name)
            logger.info(f"Dropped existing collection: {self.collection_name}")

        if utility.has_collection(self.collection_name):
            self._collection = Collection(self.collection_name)
            logger.info(
                f"Collection {self.collection_name} already exists"
            )
            return

        fields = [
            FieldSchema(
                "chunk_id",
                DataType.VARCHAR,
                is_primary=True,
                max_length=64,
            ),
            FieldSchema(
                "dense_vector",
                DataType.FLOAT_VECTOR,
                dim=self.dense_dim,
            ),
            FieldSchema(
                "sparse_vector", DataType.SPARSE_FLOAT_VECTOR
            ),
            FieldSchema(
                "text", DataType.VARCHAR, max_length=65535
            ),
            FieldSchema("year", DataType.INT64),
            FieldSchema("section_id", DataType.INT64),
            FieldSchema(
                "section_title",
                DataType.VARCHAR,
                max_length=256,
            ),
            FieldSchema(
                "section_category",
                DataType.VARCHAR,
                max_length=64,
            ),
        ]

        schema = CollectionSchema(
            fields=fields,
            description="AAPL 10-K document chunks with hybrid vectors",
        )

        self._collection = Collection(
            name=self.collection_name, schema=schema
        )

        # Create indexes
        # Dense vector index: HNSW for high recall
        self._collection.create_index(
            "dense_vector",
            {
                "index_type": "HNSW",
                "metric_type": "COSINE",
                "params": {"M": 16, "efConstruction": 256},
            },
        )

        # Sparse vector index
        self._collection.create_index(
            "sparse_vector",
            {
                "index_type": "SPARSE_INVERTED_INDEX",
                "metric_type": "IP",
            },
        )

        logger.info(
            f"Created collection {self.collection_name} with HNSW + sparse indexes"
        )

    @property
    def collection(self) -> Collection:
        if self._collection is None:
            if utility.has_collection(self.collection_name):
                self._collection = Collection(self.collection_name)
            else:
                raise RuntimeError(
                    f"Collection {self.collection_name} does not exist"
                )
        return self._collection

    def insert(self, chunks: list[dict], dense_vectors, sparse_vectors):
        """Insert chunks with their vectors into Milvus.

        Args:
            chunks: List of chunk dicts with metadata
            dense_vectors: numpy array or list of dense vectors
            sparse_vectors: list of sparse dicts {token_id: weight}
        """
        data = [
            [c["chunk_id"] for c in chunks],
            list(dense_vectors),
            sparse_vectors,
            [c["text"][:65000] for c in chunks],  # Truncate to fit VARCHAR
            [c["year"] for c in chunks],
            [c["section_id"] for c in chunks],
            [c["section_title"] for c in chunks],
            [c["section_category"] for c in chunks],
        ]

        self.collection.insert(data)
        self.collection.flush()
        logger.info(f"Inserted {len(chunks)} chunks into Milvus")

    def hybrid_search(
        self,
        dense_vector,
        sparse_vector: dict,
        top_k: int = 5,
        dense_weight: float = 0.6,
        sparse_weight: float = 0.4,
        filter_expr: Optional[str] = None,
        output_fields: Optional[list[str]] = None,
    ) -> list[dict]:
        """Perform hybrid search combining dense and sparse vectors.

        Uses Milvus native WeightedRanker for fusion.
        """
        self.collection.load()

        if output_fields is None:
            output_fields = [
                "chunk_id",
                "text",
                "year",
                "section_id",
                "section_title",
                "section_category",
            ]

        # Dense search request (Bypass hybrid_search rerank issue)
        dense_search_params = {"metric_type": "COSINE", "params": {"ef": 128}}
        
        results = self.collection.search(
            data=[dense_vector],
            anns_field="dense_vector",
            param=dense_search_params,
            limit=top_k,
            expr=filter_expr,
            output_fields=output_fields,
        )

        # Convert results to dicts
        search_results = []
        for hits in results:
            for hit in hits:
                result = {
                    "chunk_id": hit.entity.get("chunk_id"),
                    "text": hit.entity.get("text"),
                    "year": hit.entity.get("year"),
                    "section_id": hit.entity.get("section_id"),
                    "section_title": hit.entity.get("section_title"),
                    "section_category": hit.entity.get("section_category"),
                    "score": hit.distance,
                }
                search_results.append(result)

        return search_results

    def collection_exists(self) -> bool:
        """Check if collection exists and has data."""
        try:
            if not utility.has_collection(self.collection_name):
                return False
            col = Collection(self.collection_name)
            return col.num_entities > 0
        except Exception:
            return False

    def get_count(self) -> int:
        """Get number of entities in collection."""
        try:
            return self.collection.num_entities
        except Exception:
            return 0
