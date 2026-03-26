# AAPL 10-K Intelligent Financial Q&A System

A multi-source intelligent routing Q&A system built on Apple Inc.'s 10-K SEC filings (2020-2025). The system combines **BGE-M3 hybrid vector retrieval**, **SQL Text-to-SQL**, **Neo4j knowledge graph**, and **LLM-based intent routing** to provide accurate answers to financial questions.

## Architecture

```
                         ┌──────────────┐
                         │   Browser    │ :3000
                         └──────┬───────┘
                                │
                         ┌──────▼───────┐
                         │    nginx     │ React Frontend
                         └──────┬───────┘
                                │ /api proxy
                         ┌──────▼───────┐
                         │   FastAPI    │ :8000
                         │   Backend    │
                         │ ┌──────────┐ │
                         │ │  Intent  │ │ LLM-based Classification
                         │ │  Router  │ │
                         │ └────┬─────┘ │
                    ┌────┼──────┼───────┼────┐
                    │    │      │       │    │
             ┌──────▼┐ ┌▼─────▼┐ ┌────▼──┐ │
             │Milvus │ │SQLite │ │Neo4j  │ │
             │Hybrid │ │Text2  │ │Graph  │ │
             │Search │ │SQL    │ │Query  │ │
             └───────┘ └───────┘ └───────┘ │
                    │                       │
             ┌──────▼───┐          ┌───────▼──┐
             │ BGE-M3   │          │  Ollama  │
             │dense+    │          │qwen2.5:7b│
             │sparse    │          │          │
             └──────────┘          └──────────┘
```

### Intent Routing Flow

```
User Query → LLM Intent Classification
    ├── quantitative → SQLite (Text-to-SQL) → precise financial numbers
    ├── narrative    → Milvus (BGE-M3 hybrid search) → RAG from 10-K text
    ├── relationship → Neo4j (Cypher generation) → entity relationships
    └── hybrid       → SQL + Vector search → combined analysis
```

## Key Features

| Feature | Implementation |
|---------|---------------|
| **Hybrid Retrieval** | BGE-M3 dense+sparse vectors, Milvus native WeightedRanker fusion |
| **Text-to-SQL** | LLM generates SQL for precise financial queries against SQLite |
| **Knowledge Graph** | Neo4j with products, segments, executives, risk categories |
| **Intent Routing** | LLM few-shot classification into 4 query types |
| **Streaming** | SSE streaming with real-time token display |
| **Visualization** | Recharts financial dashboard (Revenue, Margins, Balance Sheet, Ratios) |
| **Evaluation** | 30-question test suite with intent accuracy + keyword matching |

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI (Python 3.11) |
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS |
| LLM | Ollama + Qwen2.5:7b (local) |
| Embedding | BAAI/bge-m3 (dense 1024-dim + sparse) |
| Vector DB | Milvus Standalone |
| SQL | SQLite |
| Graph DB | Neo4j Community |
| Charts | Recharts |
| Container | Docker Compose (7 services) |

## Quick Start

### Prerequisites

- Docker & Docker Compose
- At least **16GB RAM** (for Ollama + BGE-M3)
- ~10GB disk space (models + data)

### Run

```bash
# Clone the repository
git clone <repo-url>
cd aapl-10k-qa

# Start all services (first run will download models, ~5-15 min)
docker-compose up

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs
# Neo4j Browser: http://localhost:7474
```

### First-Time Startup

On first launch, the system will:
1. Start infrastructure services (Milvus, Neo4j, Ollama)
2. Pull the Qwen2.5:7b model (~4.7GB)
3. Download BGE-M3 embedding model (~2.3GB)
4. Build indexes: chunk documents → encode → store in Milvus + SQLite + Neo4j
5. Start the FastAPI server

Subsequent starts skip model download and index building.

### Common Commands

```bash
make up          # Start services (detached)
make down        # Stop services
make logs        # View logs
make eval        # Run evaluation
make index       # Force rebuild indexes
make clean       # Remove all data and volumes
```

## Project Structure

```
aapl-10k-qa/
├── docker-compose.yml          # 7 services orchestration
├── data/aapl_10k.json          # Source data (164 records, 2020-2025)
│
├── backend/
│   ├── app/
│   │   ├── api/                # FastAPI endpoints
│   │   │   ├── chat.py         # POST /api/chat (SSE streaming)
│   │   │   ├── search.py       # POST /api/search
│   │   │   ├── financial.py    # GET /api/financial/*
│   │   │   ├── graph.py        # GET /api/graph/*
│   │   │   └── evaluation.py   # POST /api/eval/*
│   │   ├── core/               # Core components
│   │   │   ├── embedding.py    # BGE-M3 dense+sparse encoding
│   │   │   ├── vector_store.py # Milvus hybrid search
│   │   │   ├── sql_store.py    # SQLite + safe query execution
│   │   │   ├── graph_store.py  # Neo4j operations
│   │   │   ├── intent_router.py# LLM intent classification + routing
│   │   │   ├── llm_client.py   # Ollama async client
│   │   │   ├── rag_pipeline.py # Multi-source RAG orchestration
│   │   │   └── chunking.py     # Section-aware text chunking
│   │   ├── services/           # Data processing
│   │   │   ├── data_loader.py
│   │   │   ├── financial_parser.py
│   │   │   ├── graph_builder.py
│   │   │   └── indexer.py
│   │   └── models/             # Schemas + prompts
│   ├── evaluation/             # Test suite + evaluator
│   └── scripts/                # CLI tools
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── chat/           # Chat UI with streaming
│   │   │   ├── dashboard/      # Financial charts (Recharts)
│   │   │   ├── graph/          # Knowledge graph viewer
│   │   │   └── sidebar/        # Filters
│   │   ├── hooks/              # useChat, useFinancialData, useFilters
│   │   └── services/api.ts     # API client
│   ├── Dockerfile              # Multi-stage build
│   └── nginx.conf              # Reverse proxy
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat` | Streaming Q&A with intent routing (SSE) |
| POST | `/api/search` | Direct hybrid vector search |
| GET | `/api/financial/metrics` | Financial metrics by year |
| GET | `/api/financial/compare?metric=revenue` | Cross-year metric comparison |
| GET | `/api/financial/summary` | Key financial summary table |
| GET | `/api/graph/entities` | Knowledge graph entities |
| GET | `/api/graph/query?q=...` | Natural language graph query |
| GET | `/api/sections` | Available years and section types |
| POST | `/api/eval/run` | Run evaluation suite |
| GET | `/api/eval/results` | Latest evaluation results |
| GET | `/health` | Health check |

## Design Decisions

### Why BGE-M3 over separate BM25 + embedding?
BGE-M3 produces both dense and sparse vectors from a single model. Milvus natively supports multi-vector hybrid search with `WeightedRanker`, eliminating the need for a separate BM25 library and manual RRF fusion. Simpler architecture, better quality.

### Why multi-source routing instead of pure RAG?
Pure RAG struggles with exact financial numbers ("What was revenue in 2025?") because it relies on text retrieval and LLM extraction. Text-to-SQL against a structured database gives precise, reliable answers. The intent router intelligently selects the best data source for each query type.

### Why Neo4j for knowledge graph?
Entity relationships (products, segments, executives, risks) are naturally graph-structured. Cypher queries provide a clean interface for relationship traversal. Neo4j Community runs well in Docker with minimal configuration.

### Why SQLite instead of PostgreSQL?
The financial dataset is small (~6 years of metrics) and read-heavy. SQLite runs in-process with zero configuration and no additional Docker service. For this scale, it's the pragmatic choice.

## Evaluation

The evaluation suite includes 30 pre-defined questions across 5 categories:

| Category | Count | Tests |
|----------|-------|-------|
| Quantitative | 8 | Revenue, EPS, margins → SQL routing |
| Narrative | 8 | Risk factors, strategy → RAG routing |
| Relationship | 4 | Products, CEO, segments → Graph routing |
| Comparison | 6 | Cross-year trends → Hybrid routing |
| Complex | 4 | Multi-faceted analysis → Hybrid routing |

**Metrics evaluated:**
- Intent routing accuracy
- Keyword match rate (expected terms in answers)
- Response time

```bash
# Run evaluation
docker-compose exec backend python -m scripts.evaluate

# Run specific categories
docker-compose exec backend python -m scripts.evaluate --category quantitative,narrative
```

## AI-Coding Collaboration

This project was built with AI assistance (Claude). The collaboration approach:

1. **Architecture Design**: Discussed and iterated on system architecture, choosing BGE-M3 + multi-source routing over simpler RAG
2. **Iterative Implementation**: Built in 7 phases from infrastructure → data processing → retrieval → routing → frontend → evaluation
3. **Code Review**: AI generated initial code, reviewed and refined for correctness, security (SQL injection prevention, safe Cypher execution), and best practices
4. **Key human decisions**: Tech stack selection (Milvus, Neo4j, BGE-M3), routing strategy, evaluation criteria

The git history reflects the incremental development process with meaningful commit messages at each phase.
