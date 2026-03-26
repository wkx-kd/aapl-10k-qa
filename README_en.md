# AAPL 10-K QA System

A multi-datasource intelligent routing question-answering system built based on Apple Inc.'s 2020-2025 10-K annual reports (SEC filings). The system integrates **BGE-M3 Hybrid Vector Retrieval**, **Text-to-SQL**, **Neo4j Knowledge Graph**, and **LLM Intent Routing** to provide users with an accurate financial Q&A experience.

## System Architecture

```text
                         ┌──────────────┐
                         │   Browser    │ :3000
                         └──────┬───────┘
                                │
                         ┌──────▼───────┐
                         │    nginx     │ React Frontend
                         └──────┬───────┘
                                │ /api Reverse Proxy
                         ┌──────▼───────┐
                         │   FastAPI    │ :8000
                         │   Backend    │
                         │ ┌──────────┐ │
                         │ │  Router  │ │ LLM Intent Classification
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

### Intent Routing Workflow

```text
User Question → LLM Intent Classification
    ├── quantitative (Quantitative Queries) → SQLite (Text-to-SQL) → Precise financial numbers
    ├── narrative (Narrative Questions) → Milvus (BGE-M3 Hybrid) → 10-K Original text RAG
    ├── relationship (Relationship Queries) → Neo4j (Cypher generation) → Entity relationships
    └── hybrid (Hybrid Queries) → SQL + Vector Retrieval → Comprehensive analysis
```

## Core Features

| Feature | Implementation |
|---------|----------------|
| **Hybrid Retrieval** | BGE-M3 outputs both dense and sparse vectors, natively fused by Milvus WeightedRanker. |
| **Text-to-SQL** | LLM generates SQL statements to directly query structured financial data in SQLite. |
| **Knowledge Graph** | Neo4j stores relationships between products, business segments, executives, and risks. |
| **Intent Routing** | LLM few-shot classification automatically routes queries to the most suitable datasource. |
| **Streaming Output** | SSE streaming transmission for real-time word-by-word LLM responses. |
| **Data Visualization** | Recharts financial dashboard (revenue, margins, assets, liabilities, ratios). |
| **Evaluation Framework** | 30 predefined tests covering intent accuracy and keyword matching rates. |

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI (Python 3.11) |
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS |
| LLM | Ollama + Qwen2.5:7b (Local Deployment) |
| Embedding Model | BAAI/bge-m3 (Dense 1024-dim + Sparse vectors) |
| Vector DB | Milvus Standalone |
| Relational DB | SQLite |
| Graph DB | Neo4j Community |
| Charts | Recharts |
| Orchestration | Docker Compose (7 Services) |

---

## Startup Fixes Log

During environment adaptation and one-click deployment testing, we debugged and fixed several critical issues to ensure the project runs smoothly across platforms (including macOS and Linux):

1. **macOS Script Compatibility**: The `df -BG` disk check command in `deploy.sh` caused an `integer expression expected` syntax error on macOS. It has been fixed to automatically adapt using OS detection (`uname`).
2. **Container & Port Conflicts**: Removed hardcoded `container_name` fields in `docker-compose.yml` to prevent startup collisions with legacy or existing containers.
3. **Infrastructure Auto-start Exceptions**:
   - **Milvus**: The official standalone image omitted the run command, causing it to exit immediately. Fixed by adding `command: ["milvus", "run", "standalone"]`.
   - **Ollama**: Official images stripped out the `curl` binary making older health checks fail. Fixed by replacing with the native `ollama list` command.
4. **Backend Container Crash (Infinite Restart Loop)**:
   - **Dependency Chain Collapse**: The latest `marshmallow` removed `__version_info__`, crippling the `environs` library (a sub-dependency of `pymilvus`). Fixed by hard-pinning `marshmallow<3.20.0` in `requirements.txt`.
   - **SQLite Permission Denied**: The data volume was incorrectly mounted as read-only (`- ./data:/app/data:ro`), preventing the SQLite `financial.db` from being initialized. Fixed by removing the `:ro` flag.
   - **Missing C/C++ Headers**: The Dockerfile lacked `zlib1g-dev`, causing `pip install` to fail when compiling the `zlib-state` package. Fixed by integrating it into the `apt-get` system dependencies.

---

## Quick Start

### Prerequisites

| Requirement | Minimum Spec | Description |
|-------------|--------------|-------------|
| Docker | Docker Engine 20+ | Includes Docker Compose V2 |
| RAM | **16GB RAM** | Ollama Inference + BGE-M3 require high memory |
| Storage | ~10GB Free Space | Model files (~7GB) + Docker Images + Data |
| Network | Required initially | To pull images and Hugging Face / Ollama models |

### One-Click Deployment (Recommended)

The project provides a one-click deployment script that automatically checks environments and starts services:

```bash
# 1. Clone repository
git clone <repo-url>
cd aapl-10k-qa

# 2. Run deployment script
chmod +x deploy.sh
./deploy.sh
```

The script will:
1. Check Docker and Docker Compose installation.
2. Verify available RAM and disk space.
3. Generate a `.env` configuration file (if missing).
4. Build backend and frontend Docker images.
5. Start all 7 services in dependency order.
6. Wait for all services to become healthy.
7. Print access URIs.

### Manual Deployment

To manually control the process:

```bash
# 1. Clone repository
git clone <repo-url>
cd aapl-10k-qa

# 2. Create environment config
cp .env.example .env

# 3. Build images
docker compose build

# 4. Start all services
docker compose up -d
```

### Initial Startup Process

On its first launch, the system automatically initializes parameters (which takes 5-15 minutes depending on network speed):

```text
1. Start Infrastructure Services
   ├── etcd (Milvus Metadata)
   ├── MinIO (Milvus Object Storage)
   ├── Neo4j Graph Database
   └── Ollama LLM Service

2. Start Milvus Vector DB
   └── Waits for etcd + MinIO to be ready

3. Backend Service Initialization
   ├── Wait for Milvus / Neo4j / Ollama
   ├── Pull Qwen2.5:7b model (~4.7GB, first time only)
   ├── Download BGE-M3 embedding model (~2.3GB, first time only)
   ├── Build Indexes
   │   ├── Parse aapl_10k.json (164 records)
   │   ├── Parse structured metrics → SQLite
   │   ├── Text chunking → BGE-M3 Encoding → Milvus
   │   └── Extract relationships → Neo4j
   └── Start FastAPI Service

4. Start Frontend
   └── nginx reverse proxy /api → Backend
```

**Subsequent startups** skip model downloading and indexing, completing within 30 seconds.

### Access URIs

| Service | URI | Description |
|---------|-----|-------------|
| Frontend UI | http://localhost:3000 | Chat / Dashboard / Graph Views |
| Backend API Docs | http://localhost:8000/docs | Swagger UI for API debugging |
| Neo4j Browser | http://localhost:7474 | Username: `neo4j` / Password: `neo4jpassword` |

### Common Commands

```bash
# Using Makefile
make up          # Start all services in background
make down        # Stop all services
make logs        # View live logs
make logs-backend # View backend logs only
make eval        # Run evaluation tests
make index       # Force rebuild indexes
make clean       # Stop services and remove volumes (Proceed with caution)

# Using docker compose
docker compose up -d           # Background run
docker compose down            # Stop all
docker compose logs -f backend # Check backend logs
docker compose ps              # Check container status
docker compose restart backend # Restart backend
```

---

## Project Structure

```text
aapl-10k-qa/
├── docker-compose.yml          # Container orchestration
├── deploy.sh                   # Deployment script
├── Makefile                    # Makefile shortcuts
├── .env.example                # ENV template
├── data/aapl_10k.json          # Raw SEC Data
│
├── backend/
│   ├── Dockerfile
│   ├── entrypoint.sh           # Waits for dependencies → pulls model → builds index
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py             # FastAPI entrypoint + lifespan
│   │   ├── config.py           # Pydantic Settings
│   │   ├── api/                # API Routing
│   │   ├── core/               # Core Components (Embedding, SQL, Vector, Graph, Router)
│   │   ├── services/           # Data Loaders, Indexers, Graph Builders
│   │   └── models/             # Pydantic Schemas & Prompts
│   ├── evaluation/             # Eval suite
│   └── scripts/                # CLI Tools
│
├── frontend/
│   ├── Dockerfile              # Multi-stage CI: node build → nginx serve
│   ├── nginx.conf              # Reverse proxy config
│   └── src/                    # React UI Code
│
└── scripts/
    └── wait-for-it.sh          # Dependency ready poller
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/chat` | Streaming Q&A (SSE), auto intent routing |
| POST | `/api/search` | Direct Hybrid Vector Retrieval |
| GET | `/api/financial/metrics` | Query metrics by year |
| GET | `/api/financial/compare?metric=revenue` | Compare metrics across years |
| GET | `/api/financial/summary` | Financial summary table |
| GET | `/api/graph/entities` | Knowledge graph identity list |
| GET | `/api/graph/query?q=...` | Natural language graph traversal |
| GET | `/api/sections` | Available years and sections |
| POST | `/api/eval/run` | Run evaluations |
| GET | `/api/eval/results` | Fetch evaluation outputs |
| GET | `/health` | Health Check |

---

## Troubleshooting

### FAQ

**Q: Milvus keeps failing healthchecks on startup?**
```bash
# Check logs for Milvus dependencies
docker compose logs milvus-etcd milvus-minio milvus-standalone
# If etcd or MinIO are broken, clean and relaunch
docker compose down -v && docker compose up -d
```

**Q: The backend is stuck waiting for models indefinitely?**
```bash
# Verify Ollama's background pull progress
docker compose logs -f ollama
```

**Q: Backend Python containers enter CrashLoopBackOff?**
```bash
# Verify dependency conflicts
docker compose logs backend
# Check our applied fixes in the Startup Fixes Log section above.
```

**Q: Frontend UI cannot reach the API?**
```bash
# Check backend server port explicitly
curl http://localhost:8000/health
# Verify nginx logs
docker compose logs frontend
```
