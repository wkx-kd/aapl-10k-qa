# 部署问题排查与解决方案文档

## 概述

本文档记录了将 AAPL 10-K 财报智能问答系统部署至云服务器（阿里云 ECS，Ubuntu 22.04）过程中遇到的全部问题及对应解决方案。问题涵盖网络访问、容器配置、依赖兼容、SSE 流式传输等多个维度。

---

## 问题一：Docker Hub 镜像拉取超时

### 现象

```
failed to solve: python:3.11-slim: failed to resolve source metadata for docker.io/library/python:3.11-slim:
dial tcp 104.244.46.246:443: i/o timeout
```

`docker compose up` 时所有需要从 Docker Hub 拉取的镜像（python、nginx、neo4j、milvus 等）均超时失败。

### 根本原因

国内云服务器无法直连 `registry-1.docker.io`（Docker Hub 官方源被封锁或限速）。

### 解决方案

配置国内镜像加速器，编辑 `/etc/docker/daemon.json`：

```bash
mkdir -p /etc/docker
cat > /etc/docker/daemon.json << 'EOF'
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://dockerproxy.cn",
    "https://hub.rat.dev",
    "https://docker.1panel.live"
  ]
}
EOF

systemctl daemon-reload
systemctl restart docker
```

**云服务商专属镜像（速度更快）：**

| 云服务商 | 镜像地址 |
|---------|---------|
| 阿里云 ECS | `https://<专属ID>.mirror.aliyuncs.com`（需登录控制台获取） |
| 腾讯云 CVM | `https://mirror.ccs.tencentyun.com` |
| 华为云 ECS | `https://05f073ad3c0010ea0f4bc00b7105ec20.mirror.swr.myhuaweicloud.com` |

验证生效：

```bash
docker info | grep -A5 "Registry Mirrors"
```

---

## 问题二：BGE-M3 模型无法从 HuggingFace 下载

### 现象

```
OSError: We couldn't connect to 'https://huggingface.co' to load this file
HTTPSConnection(host='huggingface.co', port=443): Failed to establish a new connection: [Errno 101] Network is unreachable
```

后端容器启动后在 `[4/6] Generating BGE-M3 embeddings` 阶段卡住，不断重试后报错退出。

### 根本原因

国内云服务器无法访问 `huggingface.co`，`FlagEmbedding` 库默认从官方源下载 `BAAI/bge-m3` 模型文件（约 2.3 GB）。

### 解决方案

在 `.env.example` 中启用 HuggingFace 国内镜像：

```bash
# 取消注释 HF_ENDPOINT 行
sed -i 's|# HF_ENDPOINT=https://hf-mirror.com|HF_ENDPOINT=https://hf-mirror.com|' .env.example
```

**注意**：修改 env 文件后必须使用 `--force-recreate` 重建容器，`docker compose restart` 不会重新读取 env 文件：

```bash
# 错误方式（env 变量不会更新）
docker compose restart backend

# 正确方式（重新读取 env_file）
docker compose up -d --force-recreate backend
```

---

## 问题三：hf-mirror.com 下载 .DS_Store 文件返回 403

### 现象

```
huggingface_hub.errors.HfHubHTTPError: 403 Forbidden: None.
Cannot access content at: https://hf-mirror.com/api/resolve-cache/models/BAAI/bge-m3/
5617a9f61b028005a4858fdac845db406aefb181/imgs%2F.DS_Store.
Make sure your token has the correct permissions.
```

配置 `HF_ENDPOINT` 后，模型文件开始下载，但在下载 `imgs/.DS_Store`（macOS 系统生成的元数据文件，被意外提交到了 BAAI/bge-m3 模型仓库）时，hf-mirror.com 返回 403，导致整个 `snapshot_download` 失败。

### 根本原因

`FlagEmbedding` 内部调用 `huggingface_hub.snapshot_download()` 时会下载仓库中的所有文件，包含 `.DS_Store`。而 hf-mirror.com 对此类特殊文件没有缓存权限，返回 403 中断下载。

### 解决方案

修改 `backend/app/core/embedding.py`，在 `get_model()` 中先用 `snapshot_download` 并传入 `ignore_patterns` 跳过问题文件，再从本地路径加载模型：

```python
def get_model():
    global _model
    if _model is None:
        from FlagEmbedding import BGEM3FlagModel
        from huggingface_hub import snapshot_download

        # 预先下载，跳过触发 403 的 .DS_Store 文件
        model_path = snapshot_download(
            "BAAI/bge-m3",
            ignore_patterns=["*.DS_Store", "imgs/"],
        )

        _model = BGEM3FlagModel(model_path, use_fp16=True)
    return _model
```

**关键点**：通过 `model_path`（本地缓存路径）初始化模型，避免 `BGEM3FlagModel` 再次触发网络下载。

---

## 问题四：前端 "Thinking..." 永不结束（nginx SSE 超时）

### 现象

浏览器提交问题后，前端界面一直停留在 "Thinking..." 状态，始终不显示回答。后端日志显示推理正常完成（`intent` 分类成功、Ollama 返回 200），但前端收不到 token。

### 根本原因

nginx 的 `proxy_read_timeout` 默认值为 **60 秒**。CPU 模式下 qwen2.5:7b 的意图分类耗时约 50-60 秒，加上实际生成阶段，总耗时轻易超过 60 秒。超时后 nginx 静默断开连接，但前端不会显示错误，只是一直等待。

### 诊断方法

```bash
# 直接测试后端 SSE 流，绕过前端 nginx
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What products does Apple sell?"}' \
  --no-buffer -N

# 如果能看到 data: {"type": "intent"...} 说明后端正常
# 前端收不到是 nginx 超时截断的问题
```

### 解决方案

在 `frontend/nginx.conf` 的 `/api/` location 中增加超时配置：

```nginx
location /api/ {
    proxy_pass http://backend:8000/api/;

    # SSE 必要配置
    proxy_set_header Connection '';
    proxy_http_version 1.1;
    proxy_buffering off;
    proxy_cache off;

    # CPU LLM 推理慢，需要更长超时（默认 60s 不够）
    proxy_read_timeout 600s;
    proxy_connect_timeout 10s;
    proxy_send_timeout 600s;
}
```

**注意**：`nginx.conf` 打包在 Docker 镜像内，修改后必须重新构建前端镜像：

```bash
docker compose build frontend
docker compose up -d --force-recreate frontend
```

---

## 问题五：安全组未开放端口，外网无法访问

### 现象

服务器本地 `curl http://localhost:3000` 返回 200，但浏览器访问 `http://<公网IP>:3000` 无法连接。

### 根本原因

云服务器（阿里云 ECS）的安全组默认只开放 22 端口，3000、8000 等端口未放行。

### 解决方案

在阿里云控制台 → ECS → 安全组 → 入方向规则中添加：

| 协议 | 端口 | 来源 | 用途 |
|------|------|------|------|
| TCP | 3000 | 0.0.0.0/0 | 前端界面 |
| TCP | 8000 | 0.0.0.0/0 | 后端 API（可选内网限制） |

添加后立即生效，无需重启服务。

---

## 问题六：镜像缺失系统依赖导致 pip install 编译失败

### 现象

```
ERROR: Failed building wheel for zlib-state
error: command '/usr/bin/gcc' failed with exit code 1
```

后端 Docker 镜像构建时，`pip install` 阶段编译 C 扩展包失败。

### 根本原因

`python:3.11-slim` 基础镜像体积精简，缺少编译部分 Python 包（如 `zlib-state`）所需的 `zlib1g-dev` 头文件。

### 解决方案

在 `backend/Dockerfile` 的系统依赖安装步骤中补充 `zlib1g-dev`：

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    netcat-openbsd \
    build-essential \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*
```

---

## 问题七：marshmallow 版本不兼容导致后端无限重启

### 现象

```
AttributeError: module 'marshmallow' has no attribute '__version_info__'
```

后端容器 `docker compose ps` 显示反复 `Restarting`，日志中 `pymilvus` 依赖链报错崩溃。

### 根本原因

`pymilvus` 依赖 `environs`，`environs` 依赖 `marshmallow`。`marshmallow` 最新版本（3.20+）移除了 `__version_info__` 属性，导致旧版 `environs` 初始化失败。

### 解决方案

在 `backend/requirements.txt` 中硬锁定 `marshmallow` 版本：

```
marshmallow<3.20.0
```

---

## 问题八：SQLite 数据库写入权限被拒

### 现象

```
PermissionError: [Errno 13] Permission denied: '/app/data/financial.db'
```

后端启动时写入 `financial.db` 失败。

### 根本原因

`docker-compose.yml` 中数据卷挂载时添加了 `:ro`（只读）标志：

```yaml
volumes:
  - ./data:/app/data:ro  # 错误：只读模式无法创建 financial.db
```

但后端需要在运行时在该目录下创建 SQLite 数据库文件。

### 解决方案

移除 `:ro` 标志：

```yaml
volumes:
  - ./data:/app/data     # 正确：可读写
```

---

## 问题九：Ollama 健康检查失败

### 现象

`ollama` 容器一直处于 `unhealthy` 状态，导致 `backend` 容器因依赖未满足而无法启动。

### 根本原因

旧版健康检查配置使用 `curl` 命令：

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:11434/"]
```

但新版 `ollama/ollama:latest` 镜像精简后不再内置 `curl`，导致健康检查命令执行失败。

### 解决方案

改用 Ollama 原生命令替代 curl：

```yaml
healthcheck:
  test: ["CMD", "ollama", "list"]
  interval: 15s
  timeout: 10s
  retries: 5
```

---

## 问题十：Milvus standalone 容器启动后秒退

### 现象

`milvus-standalone` 容器状态在 `Up` 和 `Exit` 之间反复循环。

### 根本原因

`milvusdb/milvus:v2.4.17` 独立版镜像要求显式传入启动命令，缺少 `command` 配置时进程立即退出。

### 解决方案

在 `docker-compose.yml` 的 milvus-standalone 服务中补充 `command`：

```yaml
milvus-standalone:
  image: milvusdb/milvus:v2.4.17
  command: ["milvus", "run", "standalone"]
```

---

## 快速诊断命令参考

```bash
# 查看所有服务状态
docker compose ps

# 实时查看后端日志
docker compose logs -f backend

# 过滤关键错误信息
docker compose logs backend 2>&1 | grep -E "ERROR|Exception|Traceback"

# 直接测试 SSE 流（绕过前端 nginx）
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What products does Apple sell?"}' \
  --no-buffer -N

# 测试 Ollama 推理速度
curl http://localhost:11434/api/generate \
  -d '{"model": "qwen2.5:7b", "prompt": "Hello", "stream": false}' \
  | python3 -m json.tool | grep eval_duration

# 强制重建容器（用于 env 变量或配置变更后）
docker compose up -d --force-recreate <service_name>

# 重建镜像并重启（用于代码或 Dockerfile 变更后）
docker compose build <service_name>
docker compose up -d --force-recreate <service_name>
```

---

## 问题汇总

| # | 问题 | 触发条件 | 关键修复 |
|---|------|---------|---------|
| 1 | Docker Hub 拉取超时 | 国内服务器 | 配置 Docker 镜像加速器 |
| 2 | BGE-M3 下载连接失败 | 国内服务器 | 设置 `HF_ENDPOINT=https://hf-mirror.com` |
| 3 | hf-mirror.com 403 (.DS_Store) | 使用 HF 镜像 | `snapshot_download(ignore_patterns=["*.DS_Store"])` |
| 4 | 前端永久 Thinking（nginx 超时）| CPU 慢推理 | nginx 设置 `proxy_read_timeout 600s` |
| 5 | 外网无法访问端口 | 阿里云 ECS | 安全组开放 3000、8000 端口 |
| 6 | pip install 编译失败 | Dockerfile 缺依赖 | 添加 `zlib1g-dev` |
| 7 | marshmallow 版本冲突 | pymilvus 依赖链 | 锁定 `marshmallow<3.20.0` |
| 8 | SQLite 写入权限被拒 | volume 只读挂载 | 移除数据卷 `:ro` 标志 |
| 9 | Ollama healthcheck 失败 | 镜像不含 curl | 改用 `ollama list` 健康检查 |
| 10 | Milvus 秒退 | 缺少启动命令 | 补充 `command: ["milvus", "run", "standalone"]` |
