# AAPL 10-K 财报智能问答系统

基于 Apple Inc. 2020-2025 年 10-K 年报（SEC 文件）构建的多数据源智能路由问答系统。系统融合 **BGE-M3 混合向量检索**、**SQL Text-to-SQL**、**Neo4j 知识图谱** 和 **LLM 意图路由**，为用户提供精准的财务问答体验。

## 系统架构

```
                         ┌──────────────┐
                         │   Browser    │ :3000
                         └──────┬───────┘
                                │
                         ┌──────▼───────┐
                         │    nginx     │ React 前端
                         └──────┬───────┘
                                │ /api 反向代理
                         ┌──────▼───────┐
                         │   FastAPI    │ :8000
                         │   后端服务    │
                         │ ┌──────────┐ │
                         │ │  意图路由  │ │ LLM 分类
                         │ └────┬─────┘ │
                    ┌────┼──────┼───────┼────┐
                    │    │      │       │    │
             ┌──────▼┐ ┌▼─────▼┐ ┌────▼──┐ │
             │Milvus │ │SQLite │ │Neo4j  │ │
             │混合检索│ │Text2  │ │图谱   │ │
             │       │ │SQL    │ │查询   │ │
             └───────┘ └───────┘ └───────┘ │
                    │                       │
             ┌──────▼───┐          ┌───────▼──┐
             │ BGE-M3   │          │  Ollama  │
             │dense+    │          │qwen2.5:7b│
             │sparse    │          │          │
             └──────────┘          └──────────┘
```

### 意图路由流程

```
用户提问 → LLM 意图分类
    ├── quantitative（定量查询）→ SQLite (Text-to-SQL) → 精确财务数字
    ├── narrative（叙述性问题）→ Milvus (BGE-M3 混合检索) → 10-K 原文 RAG
    ├── relationship（关系查询）→ Neo4j (Cypher 生成) → 实体关系
    └── hybrid（混合查询）    → SQL + 向量检索 → 综合分析
```

## 核心特性

| 特性 | 实现方式 |
|------|---------|
| **混合检索** | BGE-M3 同时输出稠密+稀疏向量，Milvus 原生 WeightedRanker 融合 |
| **Text-to-SQL** | LLM 生成 SQL 语句，直接查询 SQLite 中的结构化财务数据 |
| **知识图谱** | Neo4j 存储产品、业务分部、高管、风险分类等实体关系 |
| **意图路由** | LLM few-shot 分类，自动路由到最适合的数据源 |
| **流式输出** | SSE 流式传输，实时逐字显示 LLM 回答 |
| **数据可视化** | Recharts 财务仪表盘（营收、利润率、资产负债、财务比率） |
| **评估框架** | 30 道测试题，覆盖意图准确率 + 关键词匹配率评估 |

## 技术栈

| 组件 | 技术选型 |
|------|---------|
| 后端 | FastAPI (Python 3.11) |
| 前端 | React 18 + TypeScript + Vite + Tailwind CSS |
| 大语言模型 | Ollama + Qwen2.5:7b（本地部署） |
| 嵌入模型 | BAAI/bge-m3（稠密 1024 维 + 稀疏向量） |
| 向量数据库 | Milvus Standalone |
| 关系数据库 | SQLite |
| 图数据库 | Neo4j Community |
| 图表库 | Recharts |
| 容器编排 | Docker Compose（7 个服务） |

---

## 启动修复记录 (Startup Fixes Log)

在环境适配与一键部署的过程中，我们排查并修复了以下导致系统启动失败的关键问题，以确保本项目能在各个平台（包含 macOS 和 Linux）顺畅运行：

1. **macOS 脚本兼容性**：`deploy.sh` 磁盘检测命令 `df -BG` 在 macOS 上引发 `integer expression expected`，现已自适应内核探测（`uname`）。
2. **容器与端口冲突**：剥离了 `docker-compose.yml` 中的固定 `container_name` 防止新老容器名冲突。
3. **基础设施自启异常**：
   - **Milvus**：官方独立版镜像缺失 `command` 导致秒退，现补充了 `milvus run standalone`。
   - **Ollama**：官方镜像剥离了 `curl` 导致旧版健康检查失效，现改用原生的 `ollama list`。
4. **后端容器崩溃 (无限重启)**：
   - **依赖包链式崩塌**：最新的 `marshmallow` 移除了 `__version_info__` 导致 `environs` (由 `pymilvus` 选用) 瘫痪。现已在 `requirements.txt` 硬锁定 `marshmallow<3.20.0`。
   - **SQLite 权限被拒**：原挂载数据卷为只读 `- ./data:/app/data:ro`，导致无法实时创建 `financial.db`，现已移除 `:ro`。
   - **C++ 源码编译缺失**：Dockerfile 缺少 `zlib1g-dev`，导致 `zlib-state` 模块在 `pip install` 阶段编译失败，已通过 `apt-get` 补全。

---

## 快速开始

### 环境要求

| 要求 | 最低配置 | 说明 |
|------|---------|------|
| Docker | Docker Engine 20+ | 包含 Docker Compose V2 |
| 内存 | **16GB RAM** | Ollama 推理 + BGE-M3 嵌入模型需要较多内存 |
| 磁盘 | ~10GB 可用空间 | 模型文件（~7GB）+ Docker 镜像 + 数据 |
| 网络 | 首次需联网 | 下载 Docker 镜像和模型文件 |

### 一键部署（推荐）

项目提供了一键部署脚本，自动完成所有环境检查和服务启动：

```bash
# 1. 克隆仓库
git clone <repo-url>
cd aapl-10k-qa

# 2. 运行一键部署脚本
chmod +x deploy.sh
./deploy.sh
```

脚本会自动完成以下步骤：
1. 检查 Docker 和 Docker Compose 是否安装
2. 检查系统内存和磁盘空间是否满足要求
3. 生成 `.env` 配置文件（如不存在）
4. 构建后端和前端 Docker 镜像
5. 按依赖顺序启动全部 7 个服务
6. 等待所有服务健康就绪
7. 输出各服务的访问地址

### 手动部署

如果你希望手动逐步操作：

```bash
# 1. 克隆仓库
git clone <repo-url>
cd aapl-10k-qa

# 2. 创建环境配置文件
cp .env.example .env

# 3. 构建镜像
docker-compose build

# 4. 启动所有服务（前台运行，可查看日志）
docker-compose up

# 或者后台运行
docker-compose up -d
```

### 首次启动流程

首次启动时，系统会自动执行以下初始化操作（需要 5-15 分钟，取决于网络速度）：

```
1. 启动基础设施服务
   ├── etcd（Milvus 元数据存储）
   ├── MinIO（Milvus 对象存储）
   ├── Neo4j 图数据库
   └── Ollama LLM 服务

2. 启动 Milvus 向量数据库
   └── 依赖 etcd + MinIO 就绪

3. 后端服务初始化
   ├── 等待 Milvus / Neo4j / Ollama 全部就绪
   ├── 拉取 Qwen2.5:7b 模型（~4.7GB，仅首次）
   ├── 下载 BGE-M3 嵌入模型（~2.3GB，仅首次）
   ├── 构建索引
   │   ├── 解析 aapl_10k.json（164 条记录）
   │   ├── 解析结构化财务数据 → 写入 SQLite
   │   ├── 文本分块 → BGE-M3 编码 → 写入 Milvus
   │   └── 提取实体关系 → 写入 Neo4j
   └── 启动 FastAPI 服务

4. 启动前端服务
   └── nginx 代理 /api → 后端
```

**后续启动**会跳过模型下载和索引构建，通常 30 秒内完成。

### 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端界面 | http://localhost:3000 | Chat 对话 / 财务仪表盘 / 知识图谱 |
| 后端 API 文档 | http://localhost:8000/docs | Swagger UI，可在线调试 API |
| Neo4j 浏览器 | http://localhost:7474 | 账号 `neo4j` / 密码 `neo4jpassword` |

### 常用命令

```bash
# 使用 Makefile
make up          # 后台启动所有服务
make down        # 停止所有服务
make logs        # 查看实时日志
make logs-backend # 仅查看后端日志
make eval        # 运行评估测试
make index       # 强制重建索引
make clean       # 停止服务并删除所有数据卷（慎用）

# 使用 docker-compose
docker-compose up -d           # 后台启动
docker-compose down            # 停止
docker-compose logs -f backend # 查看后端日志
docker-compose ps              # 查看服务状态
docker-compose restart backend # 重启后端
```

---

## 项目结构

```
aapl-10k-qa/
├── docker-compose.yml          # 7 个服务编排
├── deploy.sh                   # 一键部署脚本
├── Makefile                    # 快捷命令
├── .env.example                # 环境变量模板
├── data/aapl_10k.json          # 原始数据（164 条记录，2020-2025 年）
│
├── backend/
│   ├── Dockerfile
│   ├── entrypoint.sh           # 容器启动脚本（等待依赖 → 拉取模型 → 建索引）
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py             # FastAPI 应用入口 + lifespan 生命周期管理
│   │   ├── config.py           # Pydantic Settings 配置
│   │   ├── api/                # API 路由层
│   │   │   ├── chat.py         # POST /api/chat（SSE 流式问答）
│   │   │   ├── search.py       # POST /api/search（直接混合检索）
│   │   │   ├── financial.py    # GET /api/financial/*（财务数据接口）
│   │   │   ├── graph.py        # GET /api/graph/*（知识图谱接口）
│   │   │   ├── sections.py     # GET /api/sections
│   │   │   └── evaluation.py   # POST /api/eval/*（评估接口）
│   │   ├── core/               # 核心组件
│   │   │   ├── embedding.py    # BGE-M3 稠密+稀疏向量编码
│   │   │   ├── vector_store.py # Milvus 混合检索
│   │   │   ├── sql_store.py    # SQLite 安全查询执行
│   │   │   ├── graph_store.py  # Neo4j 图谱操作
│   │   │   ├── intent_router.py# LLM 意图分类 + 路由分发
│   │   │   ├── llm_client.py   # Ollama 异步客户端
│   │   │   ├── rag_pipeline.py # 多源 RAG 编排
│   │   │   └── chunking.py     # 章节感知的文本分块
│   │   ├── services/           # 数据处理服务
│   │   │   ├── data_loader.py  # JSON 数据解析
│   │   │   ├── financial_parser.py # 结构化财务报表解析
│   │   │   ├── graph_builder.py    # 知识图谱构建
│   │   │   └── indexer.py          # 全量索引编排
│   │   └── models/             # 数据模型
│   │       ├── schemas.py      # Pydantic 请求/响应模型
│   │       └── prompts.py      # 所有 Prompt 模板
│   ├── evaluation/             # 评估框架
│   │   ├── test_questions.json # 30 道测试题（含意图标签）
│   │   └── evaluator.py        # 评估器
│   └── scripts/                # CLI 工具
│       ├── build_index.py      # 索引构建脚本
│       └── evaluate.py         # 评估运行脚本
│
├── frontend/
│   ├── Dockerfile              # 多阶段构建：node build → nginx serve
│   ├── nginx.conf              # 反向代理配置（/api → 后端，SSE 支持）
│   └── src/
│       ├── App.tsx             # 主应用（Chat / Dashboard / Graph 三视图）
│       ├── components/
│       │   ├── chat/           # 对话界面（流式输出 + 来源引用）
│       │   ├── dashboard/      # 财务仪表盘（Recharts 图表）
│       │   ├── graph/          # 知识图谱查看器
│       │   ├── sidebar/        # 年份/章节过滤器
│       │   └── common/         # 布局组件
│       ├── hooks/              # useChat, useFinancialData, useFilters
│       ├── services/api.ts     # API 客户端
│       └── types/index.ts      # TypeScript 类型定义
│
└── scripts/
    └── wait-for-it.sh          # 服务就绪检测脚本
```

---

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/chat` | 流式问答（SSE），自动意图路由 |
| POST | `/api/search` | 直接混合向量检索 |
| GET | `/api/financial/metrics` | 按年份查询财务指标 |
| GET | `/api/financial/compare?metric=revenue` | 跨年指标对比 |
| GET | `/api/financial/summary` | 财务摘要表 |
| GET | `/api/graph/entities` | 知识图谱实体列表 |
| GET | `/api/graph/query?q=...` | 自然语言图谱查询 |
| GET | `/api/sections` | 可用年份和章节类型 |
| POST | `/api/eval/run` | 运行评估测试 |
| GET | `/api/eval/results` | 获取最新评估结果 |
| GET | `/health` | 健康检查 |

---

## 设计决策

### 为什么选择 BGE-M3 而非 BM25 + 独立嵌入模型？

BGE-M3 单个模型同时产出稠密向量和稀疏向量。Milvus 原生支持多向量混合检索（`WeightedRanker`），无需额外引入 BM25 库，也无需手动实现 RRF 融合。架构更简洁，检索质量更好。

### 为什么采用多源路由而非纯 RAG？

纯 RAG 在回答精确财务数字时表现较差（如"2025 年营收是多少？"），因为它依赖文本检索和 LLM 提取。Text-to-SQL 直接查询结构化数据库，能给出精确可靠的答案。意图路由器根据问题类型智能选择最佳数据源。

### 为什么用 Neo4j 做知识图谱？

实体关系（产品线、业务分部、高管、风险因素）天然是图结构。Cypher 查询语言提供了简洁的关系遍历接口。Neo4j Community 版在 Docker 中开箱即用，配置简单。

### 为什么用 SQLite 而非 PostgreSQL？

财务数据集很小（约 6 年的指标），以只读查询为主。SQLite 在进程内运行，零配置，无需额外的 Docker 服务。在这个规模下，这是最务实的选择。

---

## 评估体系

评估套件包含 30 道预定义测试题，覆盖 5 个类别：

| 类别 | 数量 | 测试内容 | 期望路由 |
|------|------|---------|---------|
| 定量查询 | 8 | 营收、EPS、利润率等精确数据 | SQL |
| 叙述性问题 | 8 | 风险因素、管理层讨论、业务战略 | RAG (向量检索) |
| 关系查询 | 4 | 产品线、CEO、业务分部 | Graph (图谱) |
| 跨年对比 | 6 | 年度趋势、增长分析 | Hybrid (混合) |
| 综合分析 | 4 | 多维度深度分析 | Hybrid (混合) |

**评估指标：**
- **意图准确率**：路由分类是否正确
- **关键词匹配率**：回答中是否包含期望的关键信息
- **响应时间**：端到端响应耗时

```bash
# 运行完整评估
docker-compose exec backend python -m scripts.evaluate

# 运行指定类别
docker-compose exec backend python -m scripts.evaluate --category quantitative,narrative

# 调整检索数量
docker-compose exec backend python -m scripts.evaluate --top-k 10
```

---

## 故障排查

### 常见问题

**Q: 启动时 Milvus 一直不健康？**
```bash
# 检查 Milvus 及其依赖的日志
docker-compose logs milvus-etcd milvus-minio milvus-standalone
# 如果 etcd 或 MinIO 有问题，清除数据重新启动
docker-compose down -v && docker-compose up -d
```

**Q: 后端启动后一直在等待模型下载？**
```bash
# 查看 Ollama 下载进度
docker-compose logs -f ollama
# 模型约 4.7GB，首次下载需要几分钟到十几分钟
```

**Q: 内存不足导致服务崩溃？**
```bash
# 检查各容器内存占用
docker stats
# 建议至少 16GB RAM，Ollama 推理时峰值内存较高
```

**Q: 前端页面无法访问 API？**
```bash
# 确认后端服务是否正常运行
curl http://localhost:8000/health
# 检查 nginx 代理配置
docker-compose logs frontend
```

---

## AI-Coding 协作说明

本项目在 AI 辅助（Claude）下完成开发。协作方式如下：

1. **架构设计**：通过多轮讨论确定系统架构，选择 BGE-M3 + 多源路由方案而非简单 RAG
2. **迭代实现**：分 7 个阶段递进开发——基础设施 → 数据处理 → 检索引擎 → 智能路由 → API 层 → 前端 → 评估
3. **代码审查**：AI 生成初始代码后，逐一审查并优化安全性（SQL 注入防护、安全 Cypher 执行）和最佳实践
4. **人工决策**：技术选型（Milvus、Neo4j、BGE-M3）、路由策略、评估标准均由人工决定

Git 提交历史反映了完整的增量开发过程，每个阶段对应一次有意义的提交。
