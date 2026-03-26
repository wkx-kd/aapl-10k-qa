"""BGE-M3 embedding model wrapper for dense + sparse vectors."""

import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

_model = None


def get_model():
    """Get or initialize the BGE-M3 model (singleton)."""
    global _model
    if _model is None:
        logger.info("Loading BGE-M3 model... (this may take a minute)")
        from FlagEmbedding import BGEM3FlagModel

        _model = BGEM3FlagModel(
            "BAAI/bge-m3", use_fp16=True
        )
        logger.info("BGE-M3 model loaded successfully")
    return _model


def encode_documents(
    texts: list[str], batch_size: int = 32
) -> dict[str, list]:
    """Encode documents, returning both dense and sparse vectors.

    Returns:
        {
            "dense": list of numpy arrays (1024-dim each),
            "sparse": list of sparse dicts {token_id: weight}
        }
    """
    model = get_model()

    logger.info(f"Encoding {len(texts)} documents with BGE-M3...")
    output = model.encode(
        texts,
        batch_size=batch_size,
        return_dense=True,
        return_sparse=True,
        return_colbert_vecs=False,
    )

    dense_vectors = output["dense_vecs"]
    sparse_vectors = _convert_sparse_output(output["lexical_weights"])

    logger.info(f"Encoded {len(texts)} documents successfully")
    return {
        "dense": dense_vectors,
        "sparse": sparse_vectors,
    }


def encode_query(text: str) -> dict[str, any]:
    """Encode a single query, returning both dense and sparse vectors.

    Returns:
        {
            "dense": numpy array (1024-dim),
            "sparse": sparse dict {token_id: weight}
        }
    """
    model = get_model()

    output = model.encode(
        [text],
        batch_size=1,
        return_dense=True,
        return_sparse=True,
        return_colbert_vecs=False,
    )

    dense_vector = output["dense_vecs"][0]
    sparse_vector = _convert_sparse_output(output["lexical_weights"])[0]

    return {
        "dense": dense_vector,
        "sparse": sparse_vector,
    }


def _convert_sparse_output(lexical_weights: list[dict]) -> list[dict]:
    """Convert BGE-M3 lexical weights to Milvus sparse format.

    BGE-M3 outputs: list of {token_id (int): weight (float)}
    Milvus expects: same format as dict {int: float}
    """
    sparse_vectors = []
    for weights in lexical_weights:
        # Filter out very small weights
        filtered = {
            int(k): float(v) for k, v in weights.items() if abs(v) > 0.001
        }
        sparse_vectors.append(filtered)
    return sparse_vectors


def get_embedding_dim() -> int:
    """Return the dense embedding dimension."""
    return 1024
