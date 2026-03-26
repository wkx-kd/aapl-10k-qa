from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Ollama
    ollama_base_url: str = "http://ollama:11434"
    llm_model: str = "qwen2.5:7b"

    # Embedding
    embedding_model: str = "BAAI/bge-m3"

    # Milvus
    milvus_host: str = "milvus-standalone"
    milvus_port: int = 19530
    milvus_collection: str = "aapl_10k_chunks"

    # Neo4j
    neo4j_uri: str = "bolt://neo4j:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "neo4jpassword"

    # Paths
    data_path: str = "/app/data/aapl_10k.json"
    db_path: str = "/app/data/financial.db"

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # RAG parameters
    chunk_size: int = 1500
    chunk_overlap: int = 200
    top_k: int = 5
    dense_weight: float = 0.6
    sparse_weight: float = 0.4

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
