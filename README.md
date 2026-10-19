# 剧本创作 Agent 平台 · Script Creation Agent Platform

<p align="center">
  <strong>生产级 · 多智能体 · 短剧全流程创作系统</strong><br/>
  <em>Plan → Write → Evaluate → Ship — powered by 40+ specialized AI Agents</em>
</p>

<p align="center">
  <a href="#-中文文档">中文</a> ·
  <a href="#-english-documentation">English</a> ·
  <a href="https://github.com/GongLingRui/juben/issues">Issues</a> ·
  <a href="#-联系与支持--contact--support">联系 / Contact</a>
</p>

<p align="center">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-blue.svg" />
  <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-brightgreen.svg" />
  <img alt="React" src="https://img.shields.io/badge/react-18-61DAFB.svg" />
  <img alt="TypeScript" src="https://img.shields.io/badge/typescript-5-3178C6.svg" />
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.104-009688.svg" />
  <img alt="Agents" src="https://img.shields.io/badge/AI%20Agents-40%2B-orange.svg" />
</p>

---

> **GitHub Description（可直接粘贴到仓库 About）**
>
> **中文：** 生产级短剧多智能体创作平台：40+ 专业 AI Agent，覆盖策划、创作、评估全流程；流式交互、双层记忆、知识图谱与完整影视工作流。  
> **English:** Production-ready multi-agent platform for short-drama planning, writing & evaluation — 40+ specialized AI agents, streaming UX, dual-layer memory, knowledge graph, and end-to-end creative workflows.

**相关仓库 / Related**

- 剧本知识库：[GongLingRui/skills](https://github.com/GongLingRui/skills)
- 影视创作 Skills：[GongLingRui/screen-creative-skills](https://github.com/GongLingRui/screen-creative-skills)

**作者 / Author：** 宫灵瑞（Gong Lingrui）

---

# 🇨🇳 中文文档

## 目录

- [为什么是这个项目](#为什么是这个项目)
- [项目截图](#项目截图)
- [功能全景](#功能全景)
- [40+ Agents 一览](#40-agents-一览)
- [系统能力详解](#系统能力详解)
- [技术架构](#技术架构)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [环境变量](#环境变量)
- [常用 API](#常用-api)
- [开发指南](#开发指南)
- [路线图](#路线图)
- [贡献指南](#贡献指南)
- [联系与支持](#-联系与支持--contact--support)
- [许可证](#许可证)

---

## 为什么是这个项目

短剧行业正在爆发，但创作链路仍然碎片化：有人用 ChatGPT 写大纲，有人用表格管人设，有人靠经验「估」商业价值——**工具散、上下文断、质量不可复现**。

**剧本创作 Agent 平台**把「策划 → 创作 → 评估 → 交付」做成一条可编排、可记忆、可审计的多智能体流水线：

| 痛点 | 本项目怎么解 |
|------|-------------|
| 提示词临时拼凑 | 40+ 专职 Agent + 领域 Prompt / Skills |
| 多轮对话丢设定 | 双层记忆 + 剧集上下文 + Checkpoint |
| 质量全凭感觉 | 多维评估 Agent + 评分体系 + 一致性检查 |
| 知识无法沉淀 | LLM Wiki + 向量检索（Milvus）+ 图数据库（Neo4j） |
| 前后端玩具级 Demo | 生产级 FastAPI + React/TS + SSE 流式 + 鉴权 RBAC |

如果你是：

- **编剧 / 短剧团队** —— 想要可落地的创作辅助工作台  
- **AI 工程师** —— 想研究真实多智能体编排、记忆与流式协议  
- **内容公司 / 工作室** —— 想把 IP 筛选、评估、批量分集做成流水线  

欢迎 **⭐ Star** 与 **Fork**，一起把影视创作的 Agent 基建做厚。

---

## 项目截图

> 📸 **截图占位**：请把界面截图放到 [`pictures/screenshots/`](./pictures/screenshots/)，命名见该目录 README。替换下方路径后即可展示。

| Studio 工作台 | 剧集工作区 |
|:---:|:---:|
| ![Studio](./pictures/screenshots/01-studio.svg) | ![Drama Workspace](./pictures/screenshots/02-drama-workspace.svg) |
| *替换为 `01-studio.png`* | *替换为 `02-drama-workspace.png`* |

| Agents 中心 | 知识图谱 |
|:---:|:---:|
| ![Agents Hub](./pictures/screenshots/03-agents-hub.svg) | ![Knowledge Graph](./pictures/screenshots/04-knowledge-graph.svg) |
| *替换为 `03-agents-hub.png`* | *替换为 `04-knowledge-graph.png`* |

| 评估打分 | 流水线管理 |
|:---:|:---:|
| ![Evaluation](./pictures/screenshots/05-evaluation.svg) | ![Pipeline](./pictures/screenshots/06-pipeline.svg) |
| *替换为 `05-evaluation.png`* | *替换为 `06-pipeline.png`* |

| 记忆中心 | 移动端（可选） |
|:---:|:---:|
| ![Memory](./pictures/screenshots/07-memory-center.svg) | ![Mobile](./pictures/screenshots/08-mobile-responsive.svg) |
| *替换为 `07-memory-center.png`* | *替换为 `08-mobile-responsive.png`* |

---

## 功能全景

```
┌─────────────────────────────────────────────────────────────────┐
│                    剧本创作 Agent 平台                          │
├───────────────┬───────────────┬───────────────┬─────────────────┤
│  📋 策划      │  ✍️ 创作       │  ⭐ 评估       │  🔍 分析         │
│  情绪价值     │  分集写作     │  多维打分      │  五元素/情节点   │
│  黄金三秒钩子 │  批量分集     │  IP 价值       │  已播剧拆解      │
│  三幕式结构   │  视频提示词   │  小说筛选      │  逻辑一致性      │
├───────────────┼───────────────┼───────────────┼─────────────────┤
│  👤 人物      │  📖 故事       │  🔄 工作流     │  🛠️ 工具         │
│  小传生成     │  大纲/导图     │  8 阶段流水线  │  搜索/OCR/ASR    │
│  关系网络     │  情节点展开    │  编排/门房     │  知识库/文件引用 │
├───────────────┴───────────────┴───────────────┴─────────────────┤
│  💾 记忆 · 📁 项目 · 🗒️ Notes · 🕸️ 图谱 · 📚 Wiki · 📊 统计      │
└─────────────────────────────────────────────────────────────────┘
```

### 核心亮点

1. **40+ 专业 Agents** — 策划、创作、评估、分析、人物、故事、工作流、工具全覆盖  
2. **SSE 流式交互** — 打字机输出、思考链、工具调用、进度事件实时可见  
3. **双层记忆系统** — 短期对话记忆 + 中期任务总结，跨会话可复用  
4. **剧集工场（Drama Workspace）** — 项目化管理大纲、分集、人设、评估产物  
5. **知识体系** — Skills / LLM Wiki / 向量库 / Neo4j 知识图谱  
6. **批量生产能力** — 分集批量创作、视频提示词批量生成  
7. **生产级基础设施** — 鉴权、限流、幂等、Checkpoint、分布式可靠性加固  
8. **一键本地启动** — `scripts/start_dev.sh` 拉起依赖 + 前后端  

---

## 40+ Agents 一览

### 📋 策划类

| Agent | 能力 |
|-------|------|
| `short_drama_planner` | 情绪价值、黄金三秒钩子、期待-压抑-爆发结构、商业卡点 |
| `juben_concierge` / `juben_conductor` / `juben_orchestrator` | 门房接待、任务编排、多 Agent 调度 |

### ✍️ 创作类

| Agent | 能力 |
|-------|------|
| `short_drama_creator` | 完整短剧剧本、场景与对白、设定约束与语气一致性 |
| `episode_writer` / `episode_batch_creator` | 单集写作 / 多集批量创作 |
| `video_prompt_writer` / `video_prompt_batch` | 视频提示词单集 / 批量生成 |
| `document_generator` | TXT / Markdown / JSON 等文档导出 |

### ⭐ 评估类

| Agent | 能力 |
|-------|------|
| `short_drama_evaluation` | 爽点、人设、桥段、市场竞争力、开发价值打分 |
| `script_evaluation` | 结构问题定位与优化方案 |
| `ip_evaluation` | IP 商业价值与竞品对比 |
| `story_evaluation` / `story_outline_evaluation` | 故事与大纲质量评估 |
| `novel_screening_evaluation` | 小说改编短剧可行性 |
| `score_analyzer` / `result_analyzer_evaluation` | 评分统计与多结果洞察 |
| `text_processor_evaluation` | 文本处理质量评估 |

### 🔍 分析类

| Agent | 能力 |
|-------|------|
| `story_five_elements` | 冲突、人物、结构、主题、情感基调 |
| `drama_analysis` / `series_analysis` | 剧本深度分析 / 已播剧拆解 |
| `plot_points_analyzer` / `major_plot_points` / `detailed_plot_points` | 情节点识别、展开与节奏评估 |
| `story_type_analyzer` | 类型识别与创作规范 |
| `logic_consistency` | 设定与剧情逻辑一致性校验 |

### 👤 人物类

| Agent | 能力 |
|-------|------|
| `character_profile_generator` | 300–500 字人物小传与背景 |
| `character_relationship_analyzer` | 9 种关系类型网络分析 |

### 📖 故事与工作流

| Agent | 能力 |
|-------|------|
| `story_summary_generator` / `mind_map` | 大纲精炼 / 思维导图 |
| `plot_points_workflow` | 8 阶段流水线（验证→预处理→大纲→小传→大情节→细情节→导图→格式化） |
| `drama_workflow` | 创意→大纲→剧本→质检 |
| `result_integrator` / `output_formatter` | 多结果聚合与格式规范化 |
| `meta_optimizer` / `memory_curator` | 元优化与记忆策展 |

### 🛠️ 工具类

| Agent | 能力 |
|-------|------|
| `websearch` / `knowledge` / `graph_rag_agent` | 联网搜索、知识库、图谱 RAG |
| `file_reference` / `ocr_agent` | `@文件` 引用、OCR |
| `series_info` / `series_name_extractor` | 剧集信息与剧名抽取 |
| `text_splitter` / `text_truncator` | 智能切分与截断 |

---

## 系统能力详解

### 1. 创作与剧集工场

- **Studio / Drama Workspace**：围绕一部戏组织大纲、分集、人设、评估与导出  
- **分集编辑器**：单集精写、批量分集、卡点与节奏控制  
- **视频提示词链路**：从剧本到可投喂视频模型的分镜/提示词  
- **Artifacts 面板**：Agent 产物集中浏览、对比、归档  

### 2. 记忆与上下文

- **短期记忆**：最近对话消息（Redis），保证会话连贯  
- **中期记忆**：任务级总结，跨会话复用  
- **ConversationContext**：用户消息、Orchestrator 调用、Notes、共享内存  
- **Checkpoint**：长任务可恢复，降低中断成本  

### 3. Notes 与项目

- Agent 输出自动落为 Note（标题、类型、评论、选择态）  
- 支持 TXT / Markdown / JSON 导出  
- 项目 CRUD、标签、模板、复制、软删除  
- 按类型归档：策划、人设、剧本、情节点、评估、参考资料  

### 4. 知识与图谱

- **LLM Wiki**：可演进的创作知识页（钩子、节奏、人设声线、反派阶梯等）  
- **Milvus**：向量检索专业知识与优秀片段  
- **Neo4j**：人物/事件/设定关系图谱可视化与审核中心  
- **Skills**：可同步的影视创作技能包  

### 5. 质量与一致性

- 多维打分标准（优秀 / 有潜力 / 一般 / 较差）  
- 逻辑一致性 Agent  
- 内容质量评估工具链  
- A/B 与评测脚手架（`evals/`、`scripts/run_agent_evals.py`）  

### 6. 前端体验

- 黑白简明高对比 UI  
- SSE 流式：`MESSAGE` / `LLM_CHUNK` / `THOUGHT` / `TOOL_CALL` / `PROGRESS` / `DONE`…  
- Markdown、代码高亮、思维导图（markmap）、流程图（xyflow）、力导向图谱  
- 虚拟滚动、分屏、工作流监控、Token 用量、统计看板  

### 7. 平台与运维能力

- JWT 鉴权、RBAC、限流  
- 幂等键、缓存（内存 → Redis → PostgreSQL 多层）  
- 飞书集成、百度搜索、反馈闭环、发布管理  
- Docker Compose：Neo4j；可选 Milvus  

---

## 技术架构

```
Browser (React + TS + Vite)
        │  HTTPS / SSE
        ▼
FastAPI Gateway (apis/* · middleware · auth)
        │
        ├─► Orchestrator / Conductor / Concierge
        │         │
        │         ▼
        │   Specialized Agents (agents/*)
        │         │
        │         ▼
        │   Tools · Skills · Prompt Layer
        │
        ├─► PostgreSQL   （业务 / 持久化）
        ├─► Redis        （会话 / 缓存 / 记忆）
        ├─► Milvus       （向量知识）
        └─► Neo4j        （知识图谱）
```

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.10–3.12、FastAPI、Uvicorn、Pydantic v2 |
| 前端 | React 18、TypeScript、Vite、Zustand、xyflow、markmap、Mermaid |
| LLM | DeepSeek（默认）、智谱 AI、OpenAI / OpenRouter（可选） |
| 数据 | PostgreSQL、Redis、Milvus、Neo4j |
| 观测 | structlog、Prometheus、LangSmith（可选） |
| 集成 | 飞书 lark-oapi、百度搜索、OCR / ASR（可选） |

---

## 项目结构

```
juben/
├── main.py                 # FastAPI 入口
├── agents/                 # 40+ Agents
├── apis/                   # 按域拆分的路由（chat / dramas / graph / memory …）
├── prompts/                # Agent 系统提示词
├── utils/                  # 流式、记忆、Wiki、缓存、质量等基础设施
├── middleware/             # 鉴权、限流、缓存控制
├── config/                 # 配置与 pytest
├── frontend/               # React 前端
├── skills/                 # 本地 Skills
├── data/knowledge/         # Wiki / 图谱种子知识（可提交）
├── scripts/start_dev.sh    # 一键本地启动
├── docker-compose.yml      # Neo4j
├── docker-compose.milvus.yml
├── pictures/               # 联系方式二维码 + 截图目录
│   ├── screenshots/        # ← 项目截图放这里
│   ├── 微信好友.JPG
│   ├── 公众号.jpg
│   ├── 微信收款.jpg
│   └── 支付宝收款.jpg
├── tests/                  # 单元 / 集成测试源码
└── requirements.txt
```

> 运行时目录（`projects/`、`logs/`、`juben_outputs/`、`volumes/` 等）已在 `.gitignore` 中忽略，勿提交。

---

## 快速开始

### 环境要求

- Python **3.10+**（推荐 3.12）
- Node.js **18+** + **pnpm**
- PostgreSQL、Redis（可用 Homebrew）
- Docker（用于 Neo4j / 可选 Milvus）
- DeepSeek 或智谱等 LLM API Key

### 1. 克隆与依赖

```bash
git clone https://github.com/GongLingRui/juben.git
cd juben

python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

cd frontend && pnpm install && cd ..
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env：至少配置 DEEPSEEK_API_KEY（或 ZHIPU_API_KEY）与数据库密码
```

### 3. 一键启动（推荐）

```bash
bash scripts/start_dev.sh
```

脚本会尝试：

1. 启动 PostgreSQL / Redis（Homebrew）  
2. `docker compose` 启动 Neo4j，并拉起 Milvus  
3. 后端 → [http://localhost:8000](http://localhost:8000)  
4. 前端 → [http://localhost:5173](http://localhost:5173)  

日志：`/tmp/juben-backend.log`、`/tmp/juben-frontend.log`

### 4. 手动启动（可选）

```bash
# 依赖
brew services start postgresql@16
brew services start redis
docker compose up -d neo4j
docker compose -f docker-compose.milvus.yml up -d

# 后端
source venv/bin/activate
python main.py

# 前端（另开终端）
cd frontend && pnpm dev
```

---

## 环境变量

详见 [`.env.example`](./.env.example)。关键项：

| 变量 | 说明 |
|------|------|
| `DEEPSEEK_API_KEY` | 默认模型提供商 Key |
| `ZHIPU_API_KEY` | 智谱备用 |
| `POSTGRES_*` | PostgreSQL 连接 |
| `REDIS_*` / 缓存相关 | 会话与多层缓存 |
| `JWT_SECRET_KEY` | 鉴权密钥（生产必须更换） |
| `AUTH_ENABLED` | 是否开启鉴权 |
| `NEO4J_*` / `MILVUS_*` | 图谱与向量库 |

⚠️ **切勿将 `.env` 提交到 Git。**

---

## 常用 API

前缀以实际路由注册为准（多为 `/juben/...`）。

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/juben/chat` | 核心对话（可 SSE） |
| GET | `/juben/models` | 可用模型 |
| GET | `/juben/health` | 健康检查 |
| GET | `/juben/agents` | Agent 列表 |
| GET | `/juben/agents/categories` | Agent 分类 |
| CRUD | `/juben/notes` | Notes |
| CRUD | `/juben/projects` | 项目管理 |
| — | dramas / graph / memory / knowledge / pipelines … | 见 `apis/` |

**SSE 事件类型：** `MESSAGE` · `LLM_CHUNK` · `THOUGHT` · `TOOL_CALL` · `TOOL_RETURN` · `PROGRESS` · `ERROR` · `DONE` · `SYSTEM`

---

## 开发指南

```bash
# 后端测试
pytest
pytest --cov=apis --cov=agents --cov-report=html

# 前端
cd frontend
pnpm lint
pnpm type-check
pnpm build
```

新增 Agent 建议：

1. 在 `agents/` 继承 `BaseJubenAgent`  
2. 在 `prompts/` 增加系统提示  
3. 在路由 / Orchestrator 中注册  
4. 补充单元测试  

更多细节见 [`DEVELOPMENT_SETUP.md`](./DEVELOPMENT_SETUP.md)。

---

## 路线图

- [ ] 更丰富的分集协作与版本对比 UI  
- [ ] 更多视频模型提示词模板与导出格式  
- [ ] 评测集与回归看板产品化  
- [ ] 多租户与企业部署文档  
- [ ] 插件化 Skills 市场  

欢迎在 Issues 投票你最想要的能力。

---

## 贡献指南

1. Fork 本仓库并创建特性分支  
2. 保持改动聚焦，附带必要测试  
3. 不要提交 `.env`、日志、`projects/`、评测结果等运行产物  
4. 提交清晰的 PR 说明  

Star 🌟 是对我们最大的鼓励；Issue / PR 同样欢迎。

---

# 🇬🇧 English Documentation

## Table of Contents

- [Why this project](#why-this-project)
- [Screenshots](#screenshots)
- [Feature overview](#feature-overview)
- [40+ Agents at a glance](#40-agents-at-a-glance-1)
- [Capabilities in depth](#capabilities-in-depth)
- [Architecture](#architecture)
- [Tech stack](#tech-stack-1)
- [Repository layout](#repository-layout)
- [Quick start](#quick-start-1)
- [Environment variables](#environment-variables)
- [Key APIs](#key-apis)
- [Development](#development)
- [Roadmap](#roadmap-1)
- [Contributing](#contributing)
- [Contact & Support](#-联系与支持--contact--support)
- [License](#license)

---

## Why this project

Short-drama production is booming, yet the creative stack is still fragmented: ChatGPT for outlines, spreadsheets for characters, gut feeling for “market value.” **Context breaks. Quality doesn’t reproduce.**

**Script Creation Agent Platform** turns **Plan → Write → Evaluate → Deliver** into an orchestrated, memory-aware, auditable multi-agent pipeline:

| Pain | How we address it |
|------|-------------------|
| Ad-hoc prompting | 40+ specialist agents + domain prompts / Skills |
| Lost story bible across turns | Dual-layer memory + drama context + checkpoints |
| Subjective quality | Multi-dimensional evaluation + scoring + consistency checks |
| Knowledge that never compounds | LLM Wiki + Milvus vectors + Neo4j graph |
| Toy demos | Production FastAPI + React/TS + SSE + auth/RBAC |

Built for **writers & studios**, **AI engineers**, and **content companies** who want real agent infrastructure for screen creativity.

If this helps you — please **⭐ Star** and **Fork**.

---

## Screenshots

> 📸 **Placeholders** — drop images into [`pictures/screenshots/`](./pictures/screenshots/) using the filenames below.

| Studio | Drama workspace |
|:---:|:---:|
| ![Studio](./pictures/screenshots/01-studio.svg) | ![Drama Workspace](./pictures/screenshots/02-drama-workspace.svg) |

| Agents hub | Knowledge graph |
|:---:|:---:|
| ![Agents Hub](./pictures/screenshots/03-agents-hub.svg) | ![Knowledge Graph](./pictures/screenshots/04-knowledge-graph.svg) |

| Evaluation | Pipelines |
|:---:|:---:|
| ![Evaluation](./pictures/screenshots/05-evaluation.svg) | ![Pipeline](./pictures/screenshots/06-pipeline.svg) |

| Memory center | Mobile (optional) |
|:---:|:---:|
| ![Memory](./pictures/screenshots/07-memory-center.svg) | ![Mobile](./pictures/screenshots/08-mobile-responsive.svg) |

---

## Feature overview

- **40+ agents** across planning, writing, evaluation, analysis, characters, story, workflows, and tools  
- **Streaming UX** via SSE (tokens, thoughts, tool calls, progress)  
- **Dual-layer memory** (short-term chat + mid-term task summaries)  
- **Drama workspace** for outlines, episodes, profiles, and artifacts  
- **Knowledge stack**: Skills, LLM Wiki, Milvus, Neo4j graph  
- **Batch production**: multi-episode writing & video-prompt batches  
- **Production substrate**: auth, rate limits, idempotency, checkpoints  
- **One-command local boot**: `scripts/start_dev.sh`  

---

## 40+ Agents at a glance

**Planning** — `short_drama_planner`, concierge / conductor / orchestrator  

**Writing** — `short_drama_creator`, `episode_writer`, `episode_batch_creator`, `video_prompt_*`, `document_generator`  

**Evaluation** — short-drama / script / IP / story / outline / novel-screening scorers + analyzers  

**Analysis** — five elements, drama/series analysis, plot-point suite, genre typing, logic consistency  

**Characters** — profile generator, 9-type relationship analyzer  

**Story & workflows** — outline, mind map, 8-stage plot workflow, drama workflow, result integrator, meta optimizer, memory curator  

**Tools** — web search, knowledge, graph RAG, file references, OCR, series extractors, text split/truncate  

---

## Capabilities in depth

1. **Creative studio** — project-centric drama workspace, episode editor, video-prompt pipeline, artifacts panel  
2. **Memory & context** — Redis-backed short/mid-term memory, conversation context, recoverable checkpoints  
3. **Notes & projects** — auto-saved agent notes, export, templates, tagging, soft delete  
4. **Knowledge & graph** — evolvable wiki, vector retrieval, Neo4j visualization & review center, syncable Skills  
5. **Quality** — multi-axis scoring, consistency agent, eval scaffolding  
6. **Frontend** — high-contrast UI, markdown/code highlight, markmap, xyflow, force-graph, virtual scroll, stats & token usage  
7. **Platform** — JWT/RBAC, multi-level cache, Feishu integration, Dockerized Neo4j (+ optional Milvus)  

---

## Architecture

```
Browser (React + TS + Vite)
        │  HTTPS / SSE
        ▼
FastAPI Gateway
        │
        ├─► Orchestrator / Conductor / Concierge → Agents → Tools/Skills
        ├─► PostgreSQL
        ├─► Redis
        ├─► Milvus
        └─► Neo4j
```

---

## Tech stack

Python 3.10–3.12 · FastAPI · React 18 · TypeScript · Vite · Zustand · DeepSeek / Zhipu / OpenAI · PostgreSQL · Redis · Milvus · Neo4j · structlog · Prometheus · optional LangSmith / Feishu / OCR / ASR  

---

## Repository layout

See the Chinese [项目结构](#项目结构) section — same tree. Runtime folders (`projects/`, `logs/`, `juben_outputs/`, `volumes/`, …) are gitignored.

Screenshots & contact QR codes live under [`pictures/`](./pictures/).

---

## Quick start

**Requirements:** Python 3.10+, Node 18+ / pnpm, PostgreSQL, Redis, Docker (Neo4j / optional Milvus), an LLM API key.

```bash
git clone https://github.com/GongLingRui/juben.git
cd juben

python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cd frontend && pnpm install && cd ..

cp .env.example .env   # set DEEPSEEK_API_KEY (or ZHIPU_API_KEY) and DB secrets

bash scripts/start_dev.sh
# Backend http://localhost:8000  ·  Frontend http://localhost:5173
```

Manual alternative: start Postgres/Redis/Neo4j/Milvus yourself, then `python main.py` and `pnpm dev` in `frontend/`.

---

## Environment variables

See [`.env.example`](./.env.example). Never commit `.env`.

Critical: `DEEPSEEK_API_KEY` or `ZHIPU_API_KEY`, `POSTGRES_*`, JWT secret, Redis/cache, Neo4j/Milvus as needed.

---

## Key APIs

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/juben/chat` | Chat (SSE capable) |
| GET | `/juben/models` | Models |
| GET | `/juben/health` | Health |
| GET | `/juben/agents` | Agent catalog |
| CRUD | `/juben/notes` · `/juben/projects` | Notes & projects |

SSE events: `MESSAGE`, `LLM_CHUNK`, `THOUGHT`, `TOOL_CALL`, `TOOL_RETURN`, `PROGRESS`, `ERROR`, `DONE`, `SYSTEM`.

---

## Development

```bash
pytest
cd frontend && pnpm lint && pnpm type-check && pnpm build
```

New agents: subclass `BaseJubenAgent`, add prompts, register with routes/orchestrator, add tests. See [`DEVELOPMENT_SETUP.md`](./DEVELOPMENT_SETUP.md).

---

## Roadmap

- Richer episode collaboration & version diff UI  
- More video-prompt templates / export formats  
- Productized eval dashboards  
- Multi-tenant / enterprise deploy guides  
- Plugin Skills marketplace  

---

## Contributing

1. Fork & branch  
2. Keep PRs focused; add tests when useful  
3. Do **not** commit secrets, logs, `projects/`, or eval result dumps  
4. Open a clear PR  

Stars 🌟 and PRs are deeply appreciated.

---

# 联系与支持 · Contact & Support

**作者 / Author：** 宫灵瑞（Gong Lingrui）

| 渠道 | 链接 / 内容 |
|------|-------------|
| GitHub | [github.com/GongLingRui/juben](https://github.com/GongLingRui/juben) |
| Issues | [提交问题 / Bug reports](https://github.com/GongLingRui/juben/issues) |
| 剧本知识库 | [GongLingRui/skills](https://github.com/GongLingRui/skills) |
| 影视创作 Skills | [GongLingRui/screen-creative-skills](https://github.com/GongLingRui/screen-creative-skills) |

### 微信好友 · Add me on WeChat

扫码添加微信（昵称：暖暖）  
Scan to add WeChat (nickname: 暖暖)

<p align="center">
  <img src="./pictures/微信好友.JPG" alt="WeChat QR" width="280" />
</p>

### 公众号 · WeChat Official Account

<p align="center">
  <img src="./pictures/公众号.jpg" alt="WeChat Official Account" width="220" />
</p>

### 支持项目 · Sponsor

如果本项目对你有帮助，欢迎打赏支持持续开发 ☕  
If this project helps you, sponsorship keeps the work going.

| 微信收款 WeChat Pay | 支付宝 Alipay |
|:---:|:---:|
| <img src="./pictures/微信收款.jpg" alt="WeChat Pay" width="220" /> | <img src="./pictures/支付宝收款.jpg" alt="Alipay" width="220" /> |

---

## 许可证 · License

本项目基于 [MIT License](./LICENSE.txt) 开源。  
Released under the [MIT License](./LICENSE.txt).

---

<p align="center">
  <strong>如果觉得有用，请给一个 ⭐ Star —— 你的支持是最大的动力。</strong><br/>
  <em>If you find this useful, please leave a ⭐ — it means a lot.</em>
</p>
