# 云服务器部署技术文档

本文档记录将 AAPL 10-K 财报智能问答系统部署到云服务器并实现持久化运行的完整步骤。

---

## 目录

1. [服务器选型与规格要求](#1-服务器选型与规格要求)
2. [服务器初始化](#2-服务器初始化)
3. [安装 Docker 环境](#3-安装-docker-环境)
4. [上传项目代码](#4-上传项目代码)
5. [配置环境变量](#5-配置环境变量)
6. [执行一键部署](#6-执行一键部署)
7. [验证服务运行状态](#7-验证服务运行状态)
8. [GPU 加速配置（可选）](#8-gpu-加速配置可选)
9. [配置域名与 HTTPS（可选）](#9-配置域名与-https可选)
10. [持久化机制说明](#10-持久化机制说明)
11. [日常运维操作](#11-日常运维操作)
12. [故障排查手册](#12-故障排查手册)

---

## 1. 服务器选型与规格要求

### 1.1 硬件要求

本项目运行 7 个 Docker 服务，包含 Ollama 大语言模型推理和 BGE-M3 嵌入模型。**默认为纯 CPU 部署**，不依赖 GPU，但若服务器有 GPU 可开启加速（见第 8 节）。

### CPU 模式 vs GPU 模式对比

| 对比项 | CPU 模式（默认） | GPU 模式（可选） |
|--------|--------------|--------------|
| 硬件要求 | 16-32 GB RAM | 8-10 GB 显存（VRAM） |
| LLM 推理速度 | ~5-10 token/s | ~50-100 token/s |
| BGE-M3 编码速度 | 慢（索引约 3-5 分钟） | 快（索引约 30 秒） |
| 服务器成本 | 低（普通内存型） | 高（GPU 型） |
| 适用场景 | 演示、评测、低并发 | 生产、高并发 |

### CPU 部署最低硬件要求

| 资源 | 最低要求 | 推荐配置 | 说明 |
|------|---------|---------|------|
| CPU | 4 核 | 8 核 | 模型推理为 CPU 密集型 |
| 内存 | 16 GB | 32 GB | Ollama + BGE-M3 峰值约 12-14 GB |
| 磁盘 | 50 GB SSD | 100 GB SSD | 模型文件约 7 GB，Docker 镜像约 10 GB |
| 网络 | 5 Mbps | 10 Mbps 以上 | 首次下载模型约 7 GB |
| 操作系统 | Ubuntu 20.04 LTS | **Ubuntu 22.04 LTS** | 推荐 22.04，apt 源更新 |

> **注意**：如服务器内存低于 12 GB，`deploy.sh` 会报错终止。16-32 GB 是实际可用范围。

### 1.2 各云服务商推荐机型

**国内（中文界面，人民币计费）：**

| 云服务商 | 推荐机型 | 配置 | 参考价格 |
|---------|---------|------|---------|
| 阿里云 ECS | `ecs.r7.xlarge` | 4 核 32 GB | ¥400-600/月 |
| 腾讯云 CVM | `SA3.4XLARGE32` | 4 核 32 GB | ¥350-500/月 |
| 华为云 ECS | `m6.xlarge.8` | 4 核 32 GB | ¥380-550/月 |

**海外（学术/测试场景，可直连 HuggingFace）：**

| 云服务商 | 推荐机型 | 配置 | 参考价格 |
|---------|---------|------|---------|
| AWS EC2 | `r5.xlarge` | 4 核 32 GB | ~$160/月 |
| DigitalOcean | Memory-Optimized | 4 核 32 GB | ~$168/月 |
| Vultr | High Memory | 4 核 32 GB | ~$160/月 |

**GPU 机型（可选，推理速度提升 10-20 倍）：**

Qwen2.5:7b Q4 量化版约需 **5-6 GB 显存**，BGE-M3 约需 **2-3 GB 显存**，合计约 **8-9 GB 显存**。

| 云服务商 | 推荐机型 | GPU 规格 | 参考价格 |
|---------|---------|---------|---------|
| 阿里云 ECS | `ecs.gn6i-c4g1.xlarge` | T4 16 GB | ¥800-1200/月 |
| 腾讯云 GN | `GN7.LARGE20` | T4 16 GB | ¥700-1000/月 |
| AWS EC2 | `g4dn.xlarge` | T4 16 GB | ~$380/月 |
| RunPod | RTX 4090 | 24 GB | ~$0.74/h（按量） |

> 如果只是演示和评测用途，**CPU 模式已足够**，不必投入 GPU 资源。

### 1.3 安全组端口配置

在云控制台的安全组（或防火墙规则）中，开放以下入站规则：

| 端口 | 协议 | 用途 | 访问范围 |
|------|------|------|---------|
| 22 | TCP | SSH 登录 | 仅限你的 IP |
| 3000 | TCP | 前端界面 | 0.0.0.0/0（公开） |
| 8000 | TCP | 后端 API | 0.0.0.0/0（或仅内网） |
| 7474 | TCP | Neo4j 浏览器 | 仅限你的 IP（可选） |
| 80 | TCP | HTTP（配域名时用） | 0.0.0.0/0 |
| 443 | TCP | HTTPS（配域名时用） | 0.0.0.0/0 |

> **安全建议**：22 端口务必限制为你的 IP，避免暴力破解。7474（Neo4j）不建议公开，仅用于调试时临时开放。

---

## 2. 服务器初始化

通过 SSH 登录服务器，依次执行以下命令完成基础配置。

```bash
# 使用密钥登录（推荐）
ssh -i ~/.ssh/your_key.pem ubuntu@<服务器公网IP>

# 或使用密码登录
ssh root@<服务器公网IP>
```

### 2.1 系统更新

```bash
apt update && apt upgrade -y
apt install -y curl git vim htop unzip
```

### 2.2 配置 Swap（内存扩展，可选但推荐）

如果服务器内存恰好 16 GB，建议配置 8 GB Swap 作为缓冲，防止 OOM（内存耗尽）导致容器崩溃：

```bash
# 检查当前 Swap
free -h

# 创建 8 GB Swap 文件
fallocate -l 8G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile

# 设置开机自动挂载
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# 调整 Swap 使用优先级（60 = 内存用到 40% 才启用 Swap）
echo 'vm.swappiness=60' >> /etc/sysctl.conf
sysctl -p

# 验证
free -h
```

---

## 3. 安装 Docker 环境

### 3.1 安装 Docker Engine

```bash
# 使用官方一键安装脚本
curl -fsSL https://get.docker.com | sh

# 启动并设置开机自启
systemctl enable docker
systemctl start docker

# 验证安装
docker --version
# 预期输出：Docker version 27.x.x, build ...
```

**国内服务器加速（可选）：** 如果 Docker Hub 拉取镜像较慢，配置镜像加速器：

```bash
mkdir -p /etc/docker
cat > /etc/docker/daemon.json << 'EOF'
{
  "registry-mirrors": [
    "https://mirror.ccs.tencentyun.com",
    "https://registry.cn-hangzhou.aliyuncs.com"
  ]
}
EOF

systemctl daemon-reload
systemctl restart docker
```

### 3.2 安装 Docker Compose V2

Docker Engine 24+ 已内置 Docker Compose V2（`docker compose` 命令）。如果版本较旧，手动安装：

```bash
# 检查是否已内置
docker compose version

# 若未安装，手动安装插件
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL "https://github.com/docker/compose/releases/download/v2.29.0/docker-compose-linux-x86_64" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# 再次验证
docker compose version
# 预期输出：Docker Compose version v2.29.0
```

### 3.3 允许非 root 用户运行 Docker（可选）

```bash
# 将当前用户加入 docker 组（替换 ubuntu 为你的用户名）
usermod -aG docker ubuntu

# 重新加载组权限（或重新登录 SSH）
newgrp docker
```

---

## 4. 上传项目代码

选择以下任一方式将代码传输到服务器。

### 方式 A：scp 直接上传（本地执行）

```bash
# 在本地终端执行，将整个项目目录上传到服务器 /opt/ 目录
scp -r /path/to/aapl-10k-qa ubuntu@<服务器IP>:/opt/

# 上传完成后 SSH 进入服务器确认
ssh ubuntu@<服务器IP>
ls /opt/aapl-10k-qa
```

### 方式 B：从 Git 仓库克隆（服务器上执行）

```bash
# SSH 进入服务器后执行
git clone <你的仓库地址> /opt/aapl-10k-qa
cd /opt/aapl-10k-qa
ls
```

### 方式 C：rsync 同步（推荐用于后续代码更新）

```bash
# 首次同步
rsync -avz --progress /path/to/aapl-10k-qa/ ubuntu@<服务器IP>:/opt/aapl-10k-qa/

# 后续更新只同步变更文件（排除大型 volume 数据）
rsync -avz --exclude='.git' /path/to/aapl-10k-qa/ ubuntu@<服务器IP>:/opt/aapl-10k-qa/
```

### 4.1 确认关键文件存在

```bash
cd /opt/aapl-10k-qa
ls -la

# 必须存在的文件：
# ├── docker-compose.yml
# ├── deploy.sh
# ├── .env.example
# ├── data/aapl_10k.json      ← 核心数据文件
# ├── backend/
# └── frontend/
```

**确保数据文件存在：**

```bash
ls -lh data/aapl_10k.json
# 预期：-rw-r--r-- 1 root root 2.1M ... data/aapl_10k.json
```

---

## 5. 配置环境变量

### 5.1 创建 .env 文件

```bash
cd /opt/aapl-10k-qa
cp .env.example .env
```

### 5.2 关键配置项说明

用编辑器打开 `.env` 文件：

```bash
vim .env
```

文件内容如下，按实际情况修改：

```bash
# LLM 配置
OLLAMA_BASE_URL=http://ollama:11434   # 不需要修改，容器间通信
LLM_MODEL=qwen2.5:7b                  # 默认 7B 模型，如内存充足可改 14b

# 嵌入模型
EMBEDDING_MODEL=BAAI/bge-m3

# ⚠️  国内服务器必须取消注释下一行，否则 BGE-M3 下载会超时失败
# HF_ENDPOINT=https://hf-mirror.com

# Milvus 向量数据库（不需要修改）
MILVUS_HOST=milvus-standalone
MILVUS_PORT=19530
MILVUS_COLLECTION=aapl_10k_chunks

# Neo4j 图数据库（如需修改密码，同步修改 docker-compose.yml）
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=neo4jpassword

# 后端路径（不需要修改）
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
DATA_PATH=/app/data/aapl_10k.json
DB_PATH=/app/data/financial.db
```

### 5.3 国内服务器：必须配置 HuggingFace 镜像

BGE-M3 嵌入模型（~2.3 GB）从 HuggingFace 下载，国内服务器直连会超时。**必须**启用镜像：

```bash
# 编辑 .env，取消注释 HF_ENDPOINT 一行
sed -i 's|# HF_ENDPOINT=https://hf-mirror.com|HF_ENDPOINT=https://hf-mirror.com|' .env

# 确认修改生效
grep HF_ENDPOINT .env
# 预期输出：HF_ENDPOINT=https://hf-mirror.com
```

---

## 6. 执行一键部署

### 6.1 运行 deploy.sh

```bash
cd /opt/aapl-10k-qa
chmod +x deploy.sh
./deploy.sh
```

脚本会依次执行 6 个阶段，终端输出示例：

```
╔══════════════════════════════════════════════════════╗
║       AAPL 10-K 财报智能问答系统 - 一键部署        ║
╚══════════════════════════════════════════════════════╝

[INFO] Step 1/6: 检查运行环境...
[OK]   Docker 已安装 (版本: 27.3)
[OK]   Docker Compose V2 已安装 (版本: 2.29.0)
[OK]   Docker daemon 运行正常
[OK]   系统内存: 32GB
[OK]   磁盘空间: 80GB 可用
[OK]   所需端口 (3000, 8000, 7474, 7687, 19530) 均可用

[INFO] Step 2/6: 准备配置文件...
[OK]   已从 .env.example 创建 .env 配置文件
[OK]   数据文件 data/aapl_10k.json 已就绪

[INFO] Step 3/6: 构建 Docker 镜像（首次构建约 3-5 分钟）...
[OK]   后端镜像构建完成
[OK]   前端镜像构建完成

[INFO] Step 4/6: 启动基础设施服务...
[INFO] 启动 etcd, MinIO, Neo4j, Ollama...
[INFO] 等待所有基础设施服务健康就绪（可能需要 1-2 分钟）...
[OK]   所有基础设施服务已就绪

[INFO] Step 5/6: 启动应用服务...
[INFO] 首次启动需要下载模型和构建索引，可能需要 5-15 分钟
       等待后端初始化... 8m30s
[OK]   后端 API 已就绪！

[INFO] Step 6/6: 验证部署状态...
[OK]   后端 API:     http://localhost:8000       [运行中]
[OK]   前端界面:     http://localhost:3000       [运行中]
[OK]   Neo4j 浏览器: http://localhost:7474       [运行中]
[OK]   API 文档:     http://localhost:8000/docs  [运行中]

  部署成功！所有服务已正常运行。
  打开浏览器访问: http://<服务器IP>:3000
```

### 6.2 首次启动时间预估

| 阶段 | 耗时 | 说明 |
|------|------|------|
| Docker 镜像构建 | 3-5 分钟 | 编译 Python 依赖、编译前端 |
| 基础设施启动 | 1-2 分钟 | etcd、MinIO、Milvus、Neo4j 初始化 |
| Ollama 模型下载 | 5-15 分钟 | Qwen2.5:7b 约 4.7 GB |
| BGE-M3 模型下载 | 5-15 分钟 | BAAI/bge-m3 约 2.3 GB（国内走镜像） |
| 索引构建 | 2-5 分钟 | 解析 → 分块 → 编码 → 写入 Milvus/SQLite/Neo4j |
| **合计（首次）** | **~20-40 分钟** | 取决于网络和服务器性能 |
| **合计（后续）** | **< 1 分钟** | 跳过模型下载和索引构建 |

### 6.3 在后台监控首次启动进度

首次启动时，建议新开一个 SSH 窗口，实时追踪日志：

```bash
# 查看后端日志（包含模型下载和索引构建进度）
docker compose -f /opt/aapl-10k-qa/docker-compose.yml logs -f backend

# 关键日志标志：
# "Pulling qwen2.5:7b model..." → 正在下载 LLM 模型
# "Downloading shards:"         → 正在下载 BGE-M3
# "Building index..."           → 正在构建向量索引
# "Starting FastAPI server..."  → 初始化完成，服务就绪
# "Application startup complete." → 可以访问了
```

---

## 7. 验证服务运行状态

### 7.1 检查所有容器状态

```bash
cd /opt/aapl-10k-qa
docker compose ps
```

预期所有服务状态为 `Up` 或 `healthy`：

```
NAME                 IMAGE                          STATUS
milvus-etcd          quay.io/coreos/etcd:v3.5.16    Up (healthy)
milvus-minio         minio/minio:...                Up (healthy)
milvus-standalone    milvusdb/milvus:v2.4.17        Up (healthy)
neo4j                neo4j:5-community              Up (healthy)
ollama               ollama/ollama:latest           Up (healthy)
backend              aapl-10k-qa-backend            Up
frontend             aapl-10k-qa-frontend           Up
```

### 7.2 通过 API 验证功能

```bash
# 1. 健康检查
curl http://localhost:8000/health
# 预期：{"status": "ok"}

# 2. 测试财务数据接口
curl "http://localhost:8000/api/financial/summary" | python3 -m json.tool | head -30

# 3. 测试知识图谱接口
curl "http://localhost:8000/api/graph/entities" | python3 -m json.tool | head -20

# 4. 测试问答接口（非流式版本用于验证）
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "What was Apple revenue in 2024?", "top_k": 3}' \
  | python3 -m json.tool
```

### 7.3 从外网访问

浏览器打开：

```
http://<服务器公网IP>:3000
```

如能看到问答界面，则部署成功。

---

## 8. GPU 加速配置（可选）

本节说明如何在有 NVIDIA GPU 的服务器上开启 GPU 推理加速。如使用纯 CPU 部署，可跳过此节。

### 8.1 显存需求分析

| 组件 | 模型 | 显存需求 | 说明 |
|------|------|---------|------|
| Ollama | Qwen2.5:7b（Q4_K_M 量化） | ~5-6 GB | 默认加载量化版本 |
| FlagEmbedding | BGE-M3 | ~2-3 GB | 嵌入编码，索引时占用 |
| **合计** | — | **~8-9 GB** | 同时运行时的峰值 |

> **推荐显卡**：RTX 3090（24 GB）、RTX 4090（24 GB）、A10G（24 GB）、T4（16 GB）均可满足需求。显存越大余量越多，推理越稳定。

### 8.2 安装 NVIDIA 驱动和 Container Toolkit

```bash
# 1. 检查是否已有 NVIDIA 驱动
nvidia-smi
# 如能看到 GPU 信息则跳过驱动安装

# 2. 安装 NVIDIA 驱动（Ubuntu 22.04）
apt install -y ubuntu-drivers-common
ubuntu-drivers autoinstall
reboot  # 安装驱动后需要重启

# 重启后验证
nvidia-smi
# 预期看到 GPU 型号、显存大小、驱动版本
```

```bash
# 3. 安装 nvidia-container-toolkit（让 Docker 容器能访问 GPU）
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

apt update && apt install -y nvidia-container-toolkit

# 配置 Docker 使用 NVIDIA runtime
nvidia-ctk runtime configure --runtime=docker
systemctl restart docker

# 验证 Docker 能访问 GPU
docker run --rm --gpus all nvidia/cuda:12.0-base-ubuntu22.04 nvidia-smi
# 预期输出 GPU 信息，说明配置成功
```

### 8.3 修改 docker-compose.yml 开启 GPU

编辑项目根目录的 `docker-compose.yml`，为 **ollama** 和 **backend** 两个服务添加 GPU 资源声明：

```bash
cd /opt/aapl-10k-qa
vim docker-compose.yml
```

找到 `ollama` 服务，将 `deploy.resources` 部分替换为：

```yaml
  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama_models:/root/.ollama
    ports:
      - "11434:11434"
    healthcheck:
      test: ["CMD", "ollama", "list"]
      interval: 15s
      timeout: 10s
      retries: 5
    restart: unless-stopped
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

找到 `backend` 服务，在 `restart: unless-stopped` 后添加：

```yaml
  backend:
    # ... 其他配置不变 ...
    restart: unless-stopped
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

### 8.4 验证 GPU 已生效

重启服务后验证：

```bash
# 重启服务（会重新加载 GPU 配置）
docker compose down
docker compose up -d

# 验证 Ollama 是否使用 GPU
docker compose exec ollama nvidia-smi
# 预期：能看到 GPU 信息

# 查看 Ollama 日志，是否提到 GPU 加速
docker compose logs ollama | grep -i "gpu\|cuda"
# 预期类似：msg="inference compute" id=GPU0 library=cuda ...

# 验证 Backend 的 BGE-M3 是否使用 GPU
docker compose logs backend | grep -i "device\|cuda\|gpu"
# 首次编码时会打印：device='cuda' 或 using GPU
```

### 8.5 性能对比参考

| 操作 | CPU 模式（32 GB RAM） | GPU 模式（T4 16 GB） |
|------|---------------------|---------------------|
| BGE-M3 索引全量文档 | ~3-5 分钟 | ~20-30 秒 |
| LLM 回答一个问题 | ~20-60 秒 | ~3-8 秒 |
| 首 token 延迟 | ~5-10 秒 | ~0.5-1 秒 |

---

## 9. 配置域名与 HTTPS（可选）

如果你有域名（如 `aapl-qa.example.com`），可以配置 HTTPS 访问，替代 IP:端口 的方式。

### 9.1 将域名解析到服务器

在域名服务商的 DNS 控制台添加 A 记录：

```
记录类型：A
主机记录：aapl-qa（或 @ 表示根域名）
记录值：<服务器公网 IP>
TTL：600
```

等待 DNS 生效（通常 5-10 分钟），验证：

```bash
ping aapl-qa.example.com
# 预期能 ping 通且 IP 与服务器一致
```

### 9.2 安装 nginx 和 Certbot

```bash
apt install -y nginx certbot python3-certbot-nginx
```

### 9.3 创建 nginx 配置

```bash
cat > /etc/nginx/sites-available/aapl-qa << 'NGINX_EOF'
server {
    listen 80;
    server_name aapl-qa.example.com;  # 替换为你的域名

    # 前端静态资源
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # 后端 API（包含 SSE 流式传输特殊配置）
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        # SSE 流式传输必须关闭缓冲
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Connection '';
        proxy_http_version 1.1;

        # 超时设置（LLM 生成时间较长）
        proxy_read_timeout 300s;
        proxy_connect_timeout 10s;
    }
}
NGINX_EOF

# 启用站点配置
ln -s /etc/nginx/sites-available/aapl-qa /etc/nginx/sites-enabled/

# 测试配置语法
nginx -t

# 重新加载 nginx
systemctl reload nginx
```

### 9.4 申请 SSL 证书（Let's Encrypt 免费）

```bash
# 自动申请证书并配置 HTTPS
certbot --nginx -d aapl-qa.example.com

# 按提示操作：
# - 输入邮箱（用于证书过期通知）
# - 同意服务条款：Y
# - 选择是否重定向 HTTP → HTTPS：推荐选 2（自动重定向）
```

证书申请成功后，可通过 `https://aapl-qa.example.com` 访问。

**证书自动续期：** Certbot 安装时已自动配置 systemd 定时任务，证书在到期前 30 天自动续期，无需手动干预。

---

## 10. 持久化机制说明

### 9.1 Docker Named Volume

项目使用 Docker Named Volume 存储所有状态数据，卷数据独立于容器生命周期，容器删除或更新后数据不丢失。

`docker-compose.yml` 中定义了 6 个 volume：

```yaml
volumes:
  etcd_data:         # Milvus 元数据（集群状态）
  minio_data:        # Milvus 向量数据（实际存储的 embedding）
  milvus_data:       # Milvus 本地索引文件
  neo4j_data:        # Neo4j 图数据库数据
  ollama_models:     # Ollama LLM 模型文件（~4.7 GB）
  hf_cache:          # HuggingFace 缓存（BGE-M3，~2.3 GB）
```

查看卷的存储位置：

```bash
docker volume inspect aapl-10k-qa_ollama_models
# 输出中的 "Mountpoint" 字段是宿主机上的实际路径
# 通常为 /var/lib/docker/volumes/aapl-10k-qa_ollama_models/_data
```

### 9.2 容器自动重启

所有服务配置了 `restart: unless-stopped`，保证：

| 场景 | 行为 |
|------|------|
| 容器进程崩溃 | Docker 自动重启容器 |
| 服务器重启 | Docker 随系统启动，容器自动恢复 |
| `docker compose down` | 容器停止，数据保留在 volume |
| `docker compose down -v` | ⚠️ 容器停止且**删除所有 volume 数据** |

验证服务器重启后自动恢复：

```bash
# 模拟重启（服务器管理员执行）
reboot

# 重启完成后验证
docker ps
# 预期所有容器已自动启动
```

### 9.3 数据备份

建议定期备份关键数据，防止磁盘损坏导致数据丢失。

**手动备份（按需执行）：**

```bash
mkdir -p /opt/backups
DATE=$(date +%Y%m%d_%H%M%S)

# 备份 Neo4j 图数据库
docker run --rm \
  -v aapl-10k-qa_neo4j_data:/source \
  -v /opt/backups:/backup \
  alpine tar czf /backup/neo4j_${DATE}.tar.gz -C /source .

# 备份 Milvus 数据
docker run --rm \
  -v aapl-10k-qa_milvus_data:/source \
  -v /opt/backups:/backup \
  alpine tar czf /backup/milvus_${DATE}.tar.gz -C /source .

# 查看备份文件
ls -lh /opt/backups/
```

**自动定时备份（每天凌晨 3 点）：**

```bash
# 创建备份脚本
cat > /opt/backup-aapl-qa.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d)
mkdir -p /opt/backups

docker run --rm \
  -v aapl-10k-qa_neo4j_data:/source \
  -v /opt/backups:/backup \
  alpine tar czf /backup/neo4j_${DATE}.tar.gz -C /source . 2>/dev/null

# 保留最近 7 天的备份
find /opt/backups -name "*.tar.gz" -mtime +7 -delete
EOF

chmod +x /opt/backup-aapl-qa.sh

# 添加定时任务
crontab -e
# 在文件末尾添加：
# 0 3 * * * /opt/backup-aapl-qa.sh
```

---

## 11. 日常运维操作

### 10.1 常用命令速查

```bash
# 进入项目目录（后续命令均在此目录执行）
cd /opt/aapl-10k-qa

# 查看所有服务状态
docker compose ps

# 查看实时日志（全部服务）
docker compose logs -f

# 查看特定服务日志
docker compose logs -f backend
docker compose logs -f ollama
docker compose logs -f milvus-standalone

# 停止所有服务（保留数据）
docker compose down

# 启动所有服务
docker compose up -d

# 重启特定服务
docker compose restart backend

# 查看容器资源占用（CPU/内存）
docker stats
```

### 10.2 代码更新与重新部署

当后端或前端代码有更新时：

```bash
cd /opt/aapl-10k-qa

# 1. 拉取最新代码（或 scp 上传）
git pull  # 如果使用 git

# 2. 重新构建镜像（仅重建有变化的服务）
docker compose build backend    # 后端有变化时
docker compose build frontend   # 前端有变化时

# 3. 滚动重启
docker compose up -d backend
docker compose up -d frontend

# 4. 确认服务正常
docker compose ps
curl http://localhost:8000/health
```

### 10.3 强制重建索引

如果数据文件更新（`data/aapl_10k.json` 变更），需要重建索引：

```bash
docker compose exec backend python -m scripts.build_index --force
```

### 10.4 运行评估测试

```bash
# 完整评估（30 道测试题）
docker compose exec backend python -m scripts.evaluate

# 指定类别评估
docker compose exec backend python -m scripts.evaluate --category quantitative,narrative

# 查看评估结果
curl http://localhost:8000/api/eval/results | python3 -m json.tool
```

### 10.5 查看磁盘使用情况

```bash
# Docker 镜像/容器/卷的磁盘占用
docker system df

# 各 volume 占用详情
docker system df -v | grep aapl
```

---

## 12. 故障排查手册

### 11.1 服务启动失败：查看日志定位原因

```bash
# 查看所有服务的最近 100 行日志
docker compose logs --tail=100

# 查看某个服务的日志
docker compose logs --tail=100 backend
docker compose logs --tail=100 milvus-standalone
```

---

### 11.2 Milvus 容器状态异常

**现象：** `milvus-standalone` 一直处于 `Exit` 或 `Restarting` 状态

**原因与排查：**

```bash
# 查看 Milvus 日志
docker compose logs milvus-standalone

# 检查依赖服务（etcd 和 MinIO）是否健康
docker compose ps milvus-etcd milvus-minio
```

**修复：**

```bash
# 等待 etcd 和 MinIO 完全就绪后再启动 Milvus
docker compose up -d milvus-etcd milvus-minio
sleep 30
docker compose up -d milvus-standalone

# 如果仍然失败，清除数据重新初始化（会丢失向量索引，需重建）
docker compose down -v
docker compose up -d
```

---

### 11.3 后端容器无限重启

**现象：** `backend` 状态反复在 `Up` 和 `Restarting` 之间切换

**排查：**

```bash
docker compose logs --tail=50 backend
```

**常见原因及修复：**

| 错误日志关键词 | 原因 | 修复方法 |
|-------------|------|---------|
| `cannot connect to Milvus` | 向量数据库未就绪 | 等待 1-2 分钟后后端会自动重连 |
| `PermissionError: financial.db` | 数据卷只读 | 检查 `docker-compose.yml` 中是否有 `:ro` 标志，移除它 |
| `ImportError: marshmallow` | Python 依赖冲突 | 确认 `requirements.txt` 中有 `marshmallow<3.20.0` |
| `No space left on device` | 磁盘满 | 清理磁盘：`docker system prune -f` |

---

### 11.4 BGE-M3 模型下载失败（国内服务器）

**现象：** 后端日志出现 `ConnectionError` 或 `Timeout` 且关键词包含 `huggingface.co`

**修复：**

```bash
# 1. 确认 .env 中已开启镜像
grep HF_ENDPOINT .env
# 必须输出：HF_ENDPOINT=https://hf-mirror.com

# 2. 如果没有，手动设置
echo "HF_ENDPOINT=https://hf-mirror.com" >> .env

# 3. 重启后端（会重新尝试下载）
docker compose restart backend

# 4. 观察下载进度
docker compose logs -f backend
```

---

### 11.5 Ollama 模型下载慢或失败

**现象：** 后端日志卡在 `Pulling qwen2.5:7b` 超过 30 分钟

**排查：**

```bash
# 查看 Ollama 服务状态
docker compose logs -f ollama

# 在 Ollama 容器内手动拉取
docker compose exec ollama ollama pull qwen2.5:7b

# 查看已有模型
docker compose exec ollama ollama list
```

**国内网络慢的替代方案：** 可提前在有良好网络的机器上拉取模型，再将 volume 迁移到目标服务器：

```bash
# 在有良好网络的机器上（先启动 ollama 容器并拉取模型）
docker compose up -d ollama
docker compose exec ollama ollama pull qwen2.5:7b

# 打包 ollama volume
docker run --rm \
  -v aapl-10k-qa_ollama_models:/source \
  -v $(pwd):/backup \
  alpine tar czf /backup/ollama_models.tar.gz -C /source .

# 将 ollama_models.tar.gz 传输到目标服务器，然后在目标服务器恢复
docker volume create aapl-10k-qa_ollama_models
docker run --rm \
  -v aapl-10k-qa_ollama_models:/target \
  -v /path/to/ollama_models.tar.gz:/backup.tar.gz \
  alpine tar xzf /backup.tar.gz -C /target
```

---

### 11.6 内存不足（OOM）导致容器崩溃

**现象：** 某个容器突然退出，`docker compose logs` 显示 `Killed` 或 `OOM`

**排查：**

```bash
# 查看内存使用情况
free -h
docker stats --no-stream

# 查看系统 OOM 日志
dmesg | grep -i "out of memory" | tail -20
```

**修复：**

```bash
# 1. 如果没有配置 Swap，立即配置（见第 2.2 节）
fallocate -l 8G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile

# 2. 减少并发推理压力（降低 LLM 上下文长度）
# 在 .env 中添加（如果 config.py 支持）：
# OLLAMA_NUM_CTX=2048

# 3. 重启被 OOM 杀死的服务
docker compose up -d
```

---

### 12.7 GPU 未被识别或显存不足

**现象：** 配置 GPU 后 Ollama 仍使用 CPU，或报 `CUDA out of memory`

**排查：**

```bash
# 检查宿主机 GPU 状态
nvidia-smi

# 检查 Docker 是否能访问 GPU
docker run --rm --gpus all nvidia/cuda:12.0-base-ubuntu22.04 nvidia-smi

# 检查 Ollama 容器的 GPU 访问
docker compose exec ollama nvidia-smi

# 查看 Ollama 是否加载到 GPU
docker compose logs ollama | grep -i "cuda\|gpu\|device"
```

**常见原因及修复：**

| 现象 | 原因 | 修复方法 |
|------|------|---------|
| `docker: Error ... no devices` | nvidia-container-toolkit 未安装 | 执行第 8.2 节的安装步骤 |
| Ollama 日志无 GPU 信息 | `docker-compose.yml` 未配置 GPU | 执行第 8.3 节的配置步骤 |
| `CUDA out of memory` | 显存不足 | 换小一级的模型（`qwen2.5:3b`）或升级 GPU |
| 两个服务抢 GPU 显存 | Backend 和 Ollama 同时占用 | 优先保证 Ollama 使用 GPU，Backend(BGE-M3) 可 CPU 运行 |

**如果显存只有 8 GB 以下：** Ollama 和 BGE-M3 不能同时上 GPU。建议只给 Ollama 配 GPU，Backend 保持 CPU 模式（默认行为，不为 backend 添加 GPU 配置即可）。

---

### 12.8 端口被占用

**现象：** `deploy.sh` 报端口冲突，或 `docker compose up` 报 `port is already allocated`

```bash
# 查看端口被哪个进程占用
ss -tlnp | grep -E '3000|8000|7474|7687|19530'

# 或者
lsof -i :3000

# 停止占用端口的进程（谨慎操作，确认是哪个程序）
kill -9 <PID>

# 重新启动服务
docker compose up -d
```

---

**文档版本：** 2026-03-28
**适用项目版本：** AAPL 10-K QA System（所有 commits）
