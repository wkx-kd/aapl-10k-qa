#!/bin/bash
#
# AAPL 10-K 财报智能问答系统 - 一键部署脚本
#
# 用法: chmod +x deploy.sh && ./deploy.sh
#
set -e

# ============================================================
# 颜色定义
# ============================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ============================================================
# 工具函数
# ============================================================
info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; }

print_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════╗"
    echo "║       AAPL 10-K 财报智能问答系统 - 一键部署        ║"
    echo "║                                                      ║"
    echo "║  BGE-M3 混合检索 | Text-to-SQL | Neo4j 知识图谱     ║"
    echo "║           LLM 意图路由 | Ollama + Qwen2.5            ║"
    echo "╚══════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# ============================================================
# Step 1: 环境检查
# ============================================================
check_prerequisites() {
    info "Step 1/6: 检查运行环境..."

    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        error "Docker 未安装。请先安装 Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi
    local docker_version
    docker_version=$(docker --version | grep -oE '[0-9]+\.[0-9]+' | head -1)
    success "Docker 已安装 (版本: $docker_version)"

    # 检查 Docker Compose (V2 或 V1)
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
        local compose_version
        compose_version=$(docker compose version --short 2>/dev/null || echo "V2")
        success "Docker Compose V2 已安装 (版本: $compose_version)"
    elif command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
        local compose_version
        compose_version=$(docker-compose --version | grep -oE '[0-9]+\.[0-9]+' | head -1)
        success "Docker Compose V1 已安装 (版本: $compose_version)"
    else
        error "Docker Compose 未安装。请安装 Docker Compose。"
        exit 1
    fi

    # 检查 Docker daemon 是否运行
    if ! docker info &> /dev/null 2>&1; then
        error "Docker daemon 未运行。请启动 Docker Desktop 或 Docker 服务。"
        exit 1
    fi
    success "Docker daemon 运行正常"

    # 检查内存
    local total_mem_gb
    if [[ "$(uname)" == "Darwin" ]]; then
        total_mem_gb=$(( $(sysctl -n hw.memsize) / 1024 / 1024 / 1024 ))
    else
        total_mem_gb=$(( $(grep MemTotal /proc/meminfo | awk '{print $2}') / 1024 / 1024 ))
    fi

    if [ "$total_mem_gb" -lt 12 ]; then
        error "系统内存不足: ${total_mem_gb}GB（建议 16GB 以上）"
        error "Ollama 推理 + BGE-M3 嵌入模型需要较多内存。"
        exit 1
    elif [ "$total_mem_gb" -lt 16 ]; then
        warn "系统内存: ${total_mem_gb}GB（建议 16GB 以上，可能运行较慢）"
    else
        success "系统内存: ${total_mem_gb}GB"
    fi

    # 检查磁盘空间
    local free_disk_gb
    if [[ "$(uname)" == "Darwin" ]]; then
        free_disk_gb=$(df -g . | tail -1 | awk '{print $4}')
    else
        free_disk_gb=$(df -BG . 2>/dev/null | tail -1 | awk '{gsub("G",""); print $4}' 2>/dev/null || echo "0")
    fi
    free_disk_gb=${free_disk_gb:-0}

    if [ "$free_disk_gb" -lt 10 ]; then
        error "磁盘空间不足: ${free_disk_gb}GB 可用（需要至少 10GB）"
        exit 1
    fi
    success "磁盘空间: ${free_disk_gb}GB 可用"

    # 检查端口占用
    local ports_in_use=""
    for port in 3000 8000 7474 7687 19530; do
        if lsof -i :"$port" &> /dev/null 2>&1 || ss -tlnp 2>/dev/null | grep -q ":$port "; then
            ports_in_use="$ports_in_use $port"
        fi
    done
    if [ -n "$ports_in_use" ]; then
        warn "以下端口已被占用:$ports_in_use"
        warn "可能与本项目的服务冲突，请确认是否需要先停止其他程序。"
        echo ""
        read -r -p "是否继续部署？(y/N) " response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            info "部署已取消。"
            exit 0
        fi
    else
        success "所需端口 (3000, 8000, 7474, 7687, 19530) 均可用"
    fi

    echo ""
}

# ============================================================
# Step 2: 准备配置文件
# ============================================================
prepare_config() {
    info "Step 2/6: 准备配置文件..."

    if [ ! -f ".env" ]; then
        cp .env.example .env
        success "已从 .env.example 创建 .env 配置文件"
    else
        success ".env 配置文件已存在，跳过创建"
    fi

    # 确保 data 目录和数据文件存在
    if [ ! -f "data/aapl_10k.json" ]; then
        error "数据文件 data/aapl_10k.json 不存在！"
        error "请确保项目根目录下有 data/aapl_10k.json 文件。"
        exit 1
    fi
    success "数据文件 data/aapl_10k.json 已就绪"

    echo ""
}

# ============================================================
# Step 3: 构建 Docker 镜像
# ============================================================
build_images() {
    info "Step 3/6: 构建 Docker 镜像（首次构建约 3-5 分钟）..."
    echo ""

    info "构建后端镜像..."
    $COMPOSE_CMD build backend 2>&1 | tail -3
    success "后端镜像构建完成"

    info "构建前端镜像..."
    $COMPOSE_CMD build frontend 2>&1 | tail -3
    success "前端镜像构建完成"

    echo ""
}

# ============================================================
# Step 4: 启动基础设施服务
# ============================================================
start_infrastructure() {
    info "Step 4/6: 启动基础设施服务..."

    # 先启动 Milvus 依赖 + Neo4j + Ollama
    info "启动 etcd, MinIO, Neo4j, Ollama..."
    $COMPOSE_CMD up -d milvus-etcd milvus-minio neo4j ollama

    # 等待 etcd 和 MinIO 就绪后启动 Milvus
    info "等待 etcd 和 MinIO 就绪..."
    local retries=0
    while [ $retries -lt 30 ]; do
        if $COMPOSE_CMD ps milvus-etcd 2>/dev/null | grep -q "healthy" && \
           $COMPOSE_CMD ps milvus-minio 2>/dev/null | grep -q "healthy"; then
            break
        fi
        retries=$((retries + 1))
        sleep 5
    done

    info "启动 Milvus 向量数据库..."
    $COMPOSE_CMD up -d milvus-standalone

    # 等待所有基础设施就绪
    info "等待所有基础设施服务健康就绪（可能需要 1-2 分钟）..."
    local max_wait=180
    local elapsed=0

    while [ $elapsed -lt $max_wait ]; do
        local all_healthy=true

        # 检查 Milvus
        if ! curl -sf http://localhost:19530/healthz > /dev/null 2>&1 && \
           ! curl -sf http://localhost:9091/healthz > /dev/null 2>&1; then
            all_healthy=false
        fi

        # 检查 Neo4j
        if ! curl -sf http://localhost:7474 > /dev/null 2>&1; then
            all_healthy=false
        fi

        # 检查 Ollama
        if ! curl -sf http://localhost:11434/ > /dev/null 2>&1; then
            all_healthy=false
        fi

        if $all_healthy; then
            break
        fi

        elapsed=$((elapsed + 5))
        printf "\r  等待中... %ds / %ds" "$elapsed" "$max_wait"
        sleep 5
    done
    echo ""

    if [ $elapsed -ge $max_wait ]; then
        warn "部分基础设施服务可能尚未完全就绪，但将继续启动后端服务。"
        warn "后端的 entrypoint.sh 会继续等待依赖服务。"
    else
        success "所有基础设施服务已就绪"
    fi

    echo ""
}

# ============================================================
# Step 5: 启动应用服务
# ============================================================
start_application() {
    info "Step 5/6: 启动应用服务..."

    info "启动后端服务（首次启动将自动下载模型和构建索引）..."
    $COMPOSE_CMD up -d backend

    info "启动前端服务..."
    $COMPOSE_CMD up -d frontend

    success "所有服务已启动"
    echo ""

    # 等待后端 API 可用
    info "等待后端 API 就绪..."
    info "(首次启动需要下载模型和构建索引，可能需要 5-15 分钟)"
    info "(可以新开终端运行 '$COMPOSE_CMD logs -f backend' 查看详细进度)"
    echo ""

    local max_wait=900  # 15 分钟超时
    local elapsed=0

    while [ $elapsed -lt $max_wait ]; do
        if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
            echo ""
            success "后端 API 已就绪！"
            break
        fi

        elapsed=$((elapsed + 10))
        local minutes=$((elapsed / 60))
        local seconds=$((elapsed % 60))
        printf "\r  等待后端初始化... %dm%02ds" "$minutes" "$seconds"
        sleep 10
    done

    if [ $elapsed -ge $max_wait ]; then
        echo ""
        warn "后端服务启动超时（15 分钟）。可能仍在下载模型。"
        warn "请运行以下命令查看后端日志："
        echo "  $COMPOSE_CMD logs -f backend"
    fi

    echo ""
}

# ============================================================
# Step 6: 验证部署
# ============================================================
verify_deployment() {
    info "Step 6/6: 验证部署状态..."

    echo ""
    echo -e "${CYAN}服务状态：${NC}"
    $COMPOSE_CMD ps
    echo ""

    # 逐个检查服务
    local all_ok=true

    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        success "后端 API:     http://localhost:8000       [运行中]"
    else
        warn  "后端 API:     http://localhost:8000       [启动中...]"
        all_ok=false
    fi

    if curl -sf http://localhost:3000 > /dev/null 2>&1; then
        success "前端界面:     http://localhost:3000       [运行中]"
    else
        warn  "前端界面:     http://localhost:3000       [启动中...]"
        all_ok=false
    fi

    if curl -sf http://localhost:7474 > /dev/null 2>&1; then
        success "Neo4j 浏览器: http://localhost:7474       [运行中]"
    else
        warn  "Neo4j 浏览器: http://localhost:7474       [启动中...]"
        all_ok=false
    fi

    if curl -sf http://localhost:8000/docs > /dev/null 2>&1; then
        success "API 文档:     http://localhost:8000/docs  [运行中]"
    else
        warn  "API 文档:     http://localhost:8000/docs  [启动中...]"
    fi

    echo ""
    echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"

    if $all_ok; then
        echo -e "${GREEN}"
        echo "  部署成功！所有服务已正常运行。"
        echo ""
        echo "  打开浏览器访问: http://localhost:3000"
        echo ""
        echo "  试试这些问题："
        echo "    - What was Apple's total revenue in fiscal year 2025?"
        echo "    - What are the main risk factors Apple faces?"
        echo "    - What products does Apple offer?"
        echo "    - Compare Apple's revenue trend from 2020 to 2025"
        echo -e "${NC}"
    else
        echo -e "${YELLOW}"
        echo "  部分服务仍在初始化中。"
        echo ""
        echo "  查看实时日志: $COMPOSE_CMD logs -f"
        echo "  查看后端日志: $COMPOSE_CMD logs -f backend"
        echo ""
        echo "  后端首次启动需要下载模型并构建索引，完成后即可使用。"
        echo "  请稍等片刻后访问: http://localhost:3000"
        echo -e "${NC}"
    fi

    echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "常用命令："
    echo "  $COMPOSE_CMD logs -f backend   # 查看后端日志"
    echo "  $COMPOSE_CMD ps                # 查看服务状态"
    echo "  $COMPOSE_CMD down              # 停止所有服务"
    echo "  $COMPOSE_CMD down -v           # 停止并清除所有数据"
    echo ""
}

# ============================================================
# 主流程
# ============================================================
main() {
    # 切换到脚本所在目录
    cd "$(dirname "$0")"

    print_banner

    check_prerequisites
    prepare_config
    build_images
    start_infrastructure
    start_application
    verify_deployment
}

main "$@"
