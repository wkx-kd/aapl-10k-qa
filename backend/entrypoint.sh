#!/bin/bash
set -e

echo "=== AAPL 10-K QA System Backend ==="

# Wait for Milvus
echo "Waiting for Milvus..."
until curl -sf http://milvus-standalone:9091/healthz > /dev/null 2>&1; do
    echo "  Milvus not ready, retrying in 5s..."
    sleep 5
done
echo "Milvus is ready."

# Wait for Neo4j
echo "Waiting for Neo4j..."
until curl -sf http://neo4j:7474 > /dev/null 2>&1; do
    echo "  Neo4j not ready, retrying in 5s..."
    sleep 5
done
echo "Neo4j is ready."

# Wait for Ollama
echo "Waiting for Ollama..."
until curl -sf http://ollama:11434/ > /dev/null 2>&1; do
    echo "  Ollama not ready, retrying in 5s..."
    sleep 5
done
echo "Ollama is ready."

# Pull LLM model if not present
echo "Ensuring LLM model is available..."
if ! curl -sf http://ollama:11434/api/tags | grep -q "qwen2.5:7b"; then
    echo "Pulling qwen2.5:7b model (this may take a while on first run)..."
    curl -sf http://ollama:11434/api/pull -d '{"name": "qwen2.5:7b"}' | while read -r line; do
        status=$(echo "$line" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',''))" 2>/dev/null || echo "")
        if [ -n "$status" ]; then
            echo "  $status"
        fi
    done
    echo "Model pull complete."
else
    echo "Model qwen2.5:7b already available."
fi

# Build index if not already built
echo "Checking index status..."
python -m scripts.build_index --skip-if-exists

# Start the FastAPI server
echo "Starting FastAPI server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info
