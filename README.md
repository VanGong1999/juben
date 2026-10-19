# 剧本创作 Agent 平台 · Script Creation Agent Platform

> 💡 **语言切换**  
> - **产品界面**：打开应用后，点击右上角 **中 / EN** 即可切换中英文界面。  
> - **本 README**：点击下方 [中文](#-中文文档) / [English](#-english-documentation) 跳转对应文档；两套文档使用不同截图。

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
  <img alt="DeepSeek" src="https://img.shields.io/badge/LLM-DeepSeek%20%2B%20Zhipu-informational.svg" />
</p>



**相关仓库**

- 剧本知识库：[VanGong1999/skills](https://github.com/VanGong1999/skills)
- 影视创作 Skills：[VanGong1999/screen-creative-skills](https://github.com/VanGong1999/screen-creative-skills)



---

# 🇨🇳 中文文档

## 目录

- [为什么是这个项目](#为什么是这个项目)
- [项目截图](#项目截图)
- [功能全景](#功能全景)
- [40+ Agents 一览](#40-agents-一览)
- [模型与搜索](#模型与搜索)
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

短剧行业正在爆发，但创作链路仍然碎片化：有人用大模型写大纲，有人用表格管人设，有人靠经验「估」商业价值——**工具散、上下文断、质量不可复现**。

**剧本创作 Agent 平台**把「策划 → 创作 → 评估 → 交付」做成一条可编排、可记忆、可审计的多智能体流水线：

| 痛点 | 本项目怎么解 |
|------|-------------|
| 提示词临时拼凑 | 40+ 专职 Agent + 领域提示词 / 技能包 |
| 多轮对话丢设定 | 双层记忆 + 剧集上下文 + 检查点恢复 |
| 质量全凭感觉 | 多维评估 Agent + 评分体系 + 一致性检查 |
| 知识无法沉淀 | LLM 知识页 + 向量检索（Milvus）+ 图数据库（Neo4j） |
| 前后端玩具级演示 | 生产级 FastAPI + React/TS + SSE 流式 + 鉴权权限控制 |

如果你是：

- **编剧 / 短剧团队** —— 想要可落地的创作辅助工作台  
- **内容公司 / 工作室** —— 想把 IP 筛选、评估、批量分集做成流水线  

欢迎 **⭐ Star** 与 **Fork**，一起把影视创作的 Agent 基建做厚。

---

## 项目截图

界面右上角可随时切换中 / EN。以下为**中文界面**截图（英文界面见 [English Screenshots](#screenshots)）。

| 创作工作台 | 剧集工作区 |
|:---:|:---:|
| ![创作工作台](./pictures/01-studio.png) | ![剧集工作区](./pictures/02-drama-workspace.png) |

| Agents 中心 | 知识图谱 |
|:---:|:---:|
| ![Agents 中心](./pictures/03-agents-hub.png) | ![知识图谱](./pictures/04-knowledge-graph.png) |

| 记忆中心 | 工作流 |
|:---:|:---:|
| ![记忆中心](./pictures/07-memory-center.png) | ![工作流](./pictures/工作流.png) |

| 工具箱 | 工具调用 |
|:---:|:---:|
| ![工具箱](./pictures/工具箱.png) | ![工具调用](./pictures/工具调用.png) |

| 上下文压缩 | 故事大纲 |
|:---:|:---:|
| ![上下文压缩](./pictures/上下文压缩.png) | ![故事大纲](./pictures/故事大纲.png) |

| 创作图 | 知识图谱记忆抽取 |
|:---:|:---:|
| ![创作图](./pictures/创作图.png) | ![知识图谱记忆抽取](./pictures/知识图谱记忆抽取.png) |

| 创作产物 | AI对话 |
|:---:|:---:|
| ![创作产物](./pictures/创作产物.png) | ![AI对话](./pictures/AI对话.png) |

| 创作台界面 | AI对话 |
|:---:|:---:|
| ![创作台界面](./pictures/创作台界面.png) | ![AI对话](./pictures/AI对话.png) |

| 分集写作 | 知识图谱抽取 |
|:---:|:---:|
| ![分集写作](./pictures/分集写作.png) | ![知识图谱抽取](./pictures/知识图谱抽取.png) |

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
│  💾 记忆 · 📁 项目 · 🗒️ 笔记 · 🕸️ 图谱 · 📚 知识页 · 📊 统计      │
└─────────────────────────────────────────────────────────────────┘
```

### 核心亮点

1. **40+ 专业 Agents** — 策划、创作、评估、分析、人物、故事、工作流、工具全覆盖  
2. **SSE 流式交互** — 打字机输出、思考链、工具调用、进度事件实时可见  
3. **双层记忆系统** — 短期对话记忆 + 中期任务总结，跨会话可复用  
4. **剧集工场** — 项目化管理大纲、分集、人设、评估产物  
5. **知识体系** — 技能包 / 知识页 / 向量库 / Neo4j 知识图谱  
6. **批量生产能力** — 分集批量创作、视频提示词批量生成  
7. **多模型与联网搜索** — DeepSeek（默认）+ 智谱备用，支持 DeepSeek / 百度搜索  
8. **生产级基础设施** — 鉴权、限流、幂等、检查点、分布式可靠性加固  
9. **一键本地启动** — `scripts/start_dev.sh` 拉起依赖 + 前后端  

---

## 40+ Agents 一览

### 📋 策划类

| 名称 | 能力 |
|------|------|
| 短剧策划助手 | 情绪价值、黄金三秒钩子、期待-压抑-爆发结构、商业卡点 |
| 自动编排 / 自动编排助手 / 门房接待 | 任务编排、多 Agent 调度、接待引导 |

### ✍️ 创作类

| 名称 | 能力 |
|------|------|
| 短剧创作助手 | 完整短剧剧本、场景与对白、设定约束与语气一致性 |
| 单集编剧 / 分集连载编排 | 单集写作 / 多集批量创作 |
| 单集视频提示词 / 视频提示词批量编排 | 视频提示词单集 / 批量生成 |
| 文档生成器 | TXT / Markdown / JSON 等文档导出 |

### ⭐ 评估类

| 名称 | 能力 |
|------|------|
| 短剧评估助手 | 爽点、人设、桥段、市场竞争力、开发价值打分 |
| 剧本评估专家 | 结构问题定位与优化方案 |
| IP价值评估 | IP 商业价值与竞品对比 |
| 故事质量评估 / 大纲评估 | 故事与大纲质量评估 |
| 小说筛选评估 | 小说改编短剧可行性 |
| 评分分析器 / 结果分析评估 | 评分统计与多结果洞察 |
| 文本处理评估 | 文本处理质量评估 |

### 🔍 分析类

| 名称 | 能力 |
|------|------|
| 故事五元素分析 | 冲突、人物、结构、主题、情感基调 |
| 剧本深度分析 / 已播剧集分析 | 剧本深度分析 / 已播剧拆解 |
| 情节点分析 / 大情节点分析 / 详细情节点 | 情节点识别、展开与节奏评估 |
| 故事类型分析 | 类型识别与创作规范 |
| 逻辑一致性校验 | 设定与剧情逻辑一致性校验 |

### 👤 人物类

| 名称 | 能力 |
|------|------|
| 人物小传生成 | 300–500 字人物小传与背景 |
| 人物关系分析 | 9 种关系类型网络分析 |

### 📖 故事与工作流

| 名称 | 能力 |
|------|------|
| 故事大纲生成 / 思维导图 | 大纲精炼 / 思维导图 |
| 情节点工作流 | 8 阶段流水线（验证→预处理→大纲→小传→大情节→细情节→导图→格式化） |
| 剧本创作工作流 | 创意→大纲→剧本→质检 |
| 结果集成器 / 输出格式化 | 多结果聚合与格式规范化 |
| 元优化器 / 记忆策展人 | 元优化与记忆策展 |

### 🛠️ 工具类

| 名称 | 能力 |
|------|------|
| 联网搜索 / 知识库 / 图谱检索 | 联网搜索、知识库、图谱 RAG |
| 文件引用 / OCR | `@文件` 引用、OCR |
| 剧集信息 / 剧名抽取 | 剧集信息与剧名抽取 |
| 文本切分 / 文本截断 | 智能切分与截断 |

---

## 模型与搜索

本项目**默认使用 DeepSeek**，同时支持智谱等备用提供商，并内置联网搜索能力。

### 大模型

| 提供商 | 说明 | 常用模型 |
|--------|------|----------|
| **DeepSeek（默认）** | 主力文本与推理 | `deepseek-flash`、`deepseek-v4-pro`、`deepseek-chat` |
| **智谱 AI（备用）** | 免费 / 低成本备选 | `glm-4.7-flash` 等 Flash 系列 |
| OpenAI / OpenRouter（可选） | 兼容 OpenAI 协议的第三方 | 按需配置 |

在设置页或 `.env` 中配置 `DEEPSEEK_API_KEY`（推荐）或 `ZHIPU_API_KEY` 即可；默认提供商由 `DEFAULT_MODEL_PROVIDER=deepseek` 控制。

### 联网搜索

| 搜索提供商 | 说明 |
|------------|------|
| **DeepSeek 搜索（默认）** | `WEB_SEARCH_PROVIDER=deepseek`，与 DeepSeek 账号体系打通 |
| **百度搜索** | 可切换为百度网页 / 百科等综合检索 |

Agents（如联网搜索）可按意图自动触发搜索，结果带来源标注，便于策划调研与竞品分析。

---

## 系统能力详解

### 1. 创作与剧集工场

- **创作工作台 / 剧集工作区**：围绕一部戏组织大纲、分集、人设、评估与导出  
- **分集编辑器**：单集精写、批量分集、卡点与节奏控制  
- **视频提示词链路**：从剧本到可投喂视频模型的分镜 / 提示词  
- **产物面板**：Agent 产物集中浏览、对比、归档  

### 2. 记忆与上下文

- **短期记忆**：最近对话消息（Redis），保证会话连贯  
- **中期记忆**：任务级总结，跨会话复用  
- **对话上下文**：用户消息、编排调用、笔记、共享内存  
- **检查点**：长任务可恢复，降低中断成本  

### 3. 笔记与项目

- Agent 输出自动落为笔记（标题、类型、评论、选择态）  
- 支持 TXT / Markdown / JSON 导出  
- 项目增删改查、标签、模板、复制、软删除  
- 按类型归档：策划、人设、剧本、情节点、评估、参考资料  

### 4. 知识与图谱

- **知识页**：可演进的创作知识（钩子、节奏、人设声线、反派阶梯等）  
- **Milvus**：向量检索专业知识与优秀片段  
- **Neo4j**：人物 / 事件 / 设定关系图谱可视化与审核中心  
- **技能包**：可同步的影视创作技能  

### 5. 质量与一致性

- 多维打分标准（优秀 / 有潜力 / 一般 / 较差）  
- 逻辑一致性 Agent  
- 内容质量评估工具链  
- A/B 与评测脚手架（`evals/`、`scripts/run_agent_evals.py`）  

### 6. 前端体验

- 高对比简洁界面；右上角一键切换中英文  
- SSE 流式：消息 / 内容片段 / 思考 / 工具调用 / 进度 / 完成…  
- Markdown、代码高亮、思维导图、流程图、力导向图谱  
- 虚拟滚动、分屏、工作流监控、Token 用量、统计看板  

### 7. 平台与运维能力

- JWT 鉴权、角色权限、限流  
- 幂等键、缓存（内存 → Redis → PostgreSQL 多层）  
- 飞书集成、DeepSeek / 百度搜索、反馈闭环、发布管理  
- Docker Compose：Neo4j；可选 Milvus  

---

## 技术架构

```
浏览器（React + TypeScript + Vite）
        │  HTTPS / SSE
        ▼
FastAPI 网关（apis/* · 中间件 · 鉴权）
        │
        ├─► 编排器 / 指挥 / 门房
        │         │
        │         ▼
        │   专业 Agents（agents/*）
        │         │
        │         ▼
        │   工具 · 技能包 · 提示词层
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
| 搜索 | DeepSeek 搜索（默认）、百度搜索（可选） |
| 数据 | PostgreSQL、Redis、Milvus、Neo4j |
| 观测 | structlog、Prometheus、LangSmith（可选） |
| 集成 | 飞书 lark-oapi、OCR / ASR（可选） |

---

## 项目结构

```
juben/
├── main.py                 # FastAPI 入口
├── agents/                 # 40+ Agents
├── apis/                   # 按域拆分的路由（对话 / 剧集 / 图谱 / 记忆 …）
├── prompts/                # Agent 系统提示词
├── utils/                  # 流式、记忆、知识页、缓存、质量等基础设施
├── middleware/             # 鉴权、限流、缓存控制
├── config/                 # 配置与 pytest
├── frontend/               # React 前端
├── skills/                 # 本地技能包
├── data/knowledge/         # 知识页 / 图谱种子知识（可提交）
├── scripts/start_dev.sh    # 一键本地启动
├── docker-compose.yml      # Neo4j
├── docker-compose.milvus.yml
├── pictures/               # README 截图与联系方式二维码
│   ├── 01-studio.png …     # 中文界面截图
│   ├── en-*.png            # 英文界面截图
│   ├── 微信好友.JPG
│   ├── 公众号.jpg
│   ├── 微信收款.jpg
│   └── 支付宝收款.jpg
├── tests/                  # 单元 / 集成测试
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
- **DeepSeek** 或智谱等 LLM API Key（推荐 DeepSeek）

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
# 编辑 .env：至少配置 DEEPSEEK_API_KEY（推荐）或 ZHIPU_API_KEY，以及数据库密码
# 可选：WEB_SEARCH_PROVIDER=deepseek 或 baidu
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

打开前端后，可在**右上角**切换中英文界面。

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
| `DEEPSEEK_API_KEY` | DeepSeek API Key（**推荐，默认提供商**） |
| `DEEPSEEK_MODEL` | 默认模型，如 `deepseek-flash` |
| `DEFAULT_MODEL_PROVIDER` | 默认提供商，通常为 `deepseek` |
| `WEB_SEARCH_PROVIDER` | 搜索提供商：`deepseek`（默认）或 `baidu` |
| `ZHIPU_API_KEY` | 智谱备用 Key |
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
| CRUD | `/juben/notes` | 笔记 |
| CRUD | `/juben/projects` | 项目管理 |
| — | 剧集 / 图谱 / 记忆 / 知识库 / 流水线 … | 见 `apis/` |

**SSE 事件类型：** 消息 · 内容片段 · 思考 · 工具调用 · 工具返回 · 进度 · 错误 · 完成 · 系统

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
3. 在路由 / 编排器中注册  
4. 补充单元测试  

更多细节见 [`DEVELOPMENT_SETUP.md`](./DEVELOPMENT_SETUP.md)。

---

## 路线图

- [ ] 更丰富的分集协作与版本对比界面  
- [ ] 更多视频模型提示词模板与导出格式  
- [ ] 评测集与回归看板产品化  
- [ ] 多租户与企业部署文档  
- [ ] 插件化技能包市场  

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

> 💡 **Language switch**  
> - **In the app:** use the **中 / EN** control in the **top-right** corner.  
> - **In this README:** jump via [中文](#-中文文档) / [English](#-english-documentation). Screenshots below are from the **English UI**.

## Table of Contents

- [Why this project](#why-this-project)
- [Screenshots](#screenshots)
- [Feature overview](#feature-overview)
- [40+ Agents at a glance](#40-agents-at-a-glance-1)
- [Models & search](#models--search)
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

Short-drama production is booming, yet the creative stack is still fragmented: LLMs for outlines, spreadsheets for characters, gut feeling for “market value.” **Context breaks. Quality doesn’t reproduce.**

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

English UI screenshots (`pictures/en-*.png`). For Chinese UI shots, see [项目截图](#项目截图).

| Studio | Agents conversation |
|:---:|:---:|
| ![Studio](./pictures/en-studio.png) | ![Agents talk](./pictures/en-agents-talk.png) |

| Memory center | Settings |
|:---:|:---:|
| ![Memory](./pictures/en-memory.png) | ![Settings](./pictures/en-setting.png) |

---

## Feature overview

- **40+ agents** across planning, writing, evaluation, analysis, characters, story, workflows, and tools  
- **Streaming UX** via SSE (tokens, thoughts, tool calls, progress)  
- **Dual-layer memory** (short-term chat + mid-term task summaries)  
- **Drama workspace** for outlines, episodes, profiles, and artifacts  
- **Knowledge stack**: Skills, LLM Wiki, Milvus, Neo4j graph  
- **Batch production**: multi-episode writing & video-prompt batches  
- **Models & search**: DeepSeek (default) + Zhipu fallback; DeepSeek / Baidu web search  
- **Production substrate**: auth, rate limits, idempotency, checkpoints  
- **One-command local boot**: `scripts/start_dev.sh`  

---

## 40+ Agents at a glance

**Planning** — Short Drama Planner; Auto Orchestration / Conductor / Concierge  

**Writing** — Short Drama Creator; Episode Writer; Episode Batch Creator; Video Prompt (single / batch); Document Generator  

**Evaluation** — Short-drama / Script / IP / Story / Outline / Novel-screening scorers + analyzers  

**Analysis** — Story Five Elements; Drama / Series analysis; Plot-point suite; Genre typing; Logic consistency  

**Characters** — Character Profile Generator; 9-type Relationship Analyzer  

**Story & workflows** — Story Outline; Mind Map; 8-stage Plot Workflow; Drama Workflow; Result Integrator; Meta Optimizer; Memory Curator  

**Tools** — Web Search; Knowledge; Graph RAG; File references; OCR; Series extractors; Text split / truncate  

---

## Models & search

DeepSeek is the **default** provider. Zhipu and OpenAI-compatible endpoints are optional. Web search is built in.

### LLMs

| Provider | Role | Common models |
|----------|------|----------------|
| **DeepSeek (default)** | Primary text & reasoning | `deepseek-flash`, `deepseek-v4-pro`, `deepseek-chat` |
| **Zhipu AI (fallback)** | Low-cost / free options | `glm-4.7-flash` and other Flash models |
| OpenAI / OpenRouter (optional) | OpenAI-compatible APIs | Configure as needed |

Set `DEEPSEEK_API_KEY` (recommended) or `ZHIPU_API_KEY` in `.env`. Default provider: `DEFAULT_MODEL_PROVIDER=deepseek`.

### Web search

| Provider | Notes |
|----------|--------|
| **DeepSeek search (default)** | `WEB_SEARCH_PROVIDER=deepseek` |
| **Baidu search** | Switch for Baidu web / Baike-style retrieval |

Search-capable agents can trigger lookups automatically and cite sources for research and competitive analysis.

---

## Capabilities in depth

1. **Creative studio** — project-centric drama workspace, episode editor, video-prompt pipeline, artifacts panel  
2. **Memory & context** — Redis-backed short/mid-term memory, conversation context, recoverable checkpoints  
3. **Notes & projects** — auto-saved agent notes, export, templates, tagging, soft delete  
4. **Knowledge & graph** — evolvable wiki, vector retrieval, Neo4j visualization & review center, syncable Skills  
5. **Quality** — multi-axis scoring, consistency agent, eval scaffolding  
6. **Frontend** — high-contrast UI, top-right **中 / EN** switch, markdown/code highlight, markmap, xyflow, force-graph, virtual scroll, stats & token usage  
7. **Platform** — JWT/RBAC, multi-level cache, Feishu integration, DeepSeek / Baidu search, Dockerized Neo4j (+ optional Milvus)  

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

| Layer | Stack |
|-------|--------|
| Backend | Python 3.10–3.12, FastAPI, Uvicorn, Pydantic v2 |
| Frontend | React 18, TypeScript, Vite, Zustand, xyflow, markmap, Mermaid |
| LLM | DeepSeek (default), Zhipu AI, OpenAI / OpenRouter (optional) |
| Search | DeepSeek search (default), Baidu (optional) |
| Data | PostgreSQL, Redis, Milvus, Neo4j |
| Observability | structlog, Prometheus, LangSmith (optional) |
| Integrations | Feishu lark-oapi, OCR / ASR (optional) |

---

## Repository layout

See the Chinese [项目结构](#项目结构) section — same tree. Runtime folders (`projects/`, `logs/`, `juben_outputs/`, `volumes/`, …) are gitignored.

Screenshots & contact QR codes live under [`pictures/`](./pictures/): Chinese UI images use numeric / Chinese filenames; English UI images use the `en-` prefix.

---

## Quick start

**Requirements:** Python 3.10+, Node 18+ / pnpm, PostgreSQL, Redis, Docker (Neo4j / optional Milvus), a **DeepSeek** (recommended) or Zhipu LLM API key.

```bash
git clone https://github.com/GongLingRui/juben.git
cd juben

python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cd frontend && pnpm install && cd ..

cp .env.example .env
# set DEEPSEEK_API_KEY (recommended) or ZHIPU_API_KEY, plus DB secrets
# optional: WEB_SEARCH_PROVIDER=deepseek|baidu

bash scripts/start_dev.sh
# Backend http://localhost:8000  ·  Frontend http://localhost:5173
```

After the UI loads, switch language with **中 / EN** in the top-right corner.

Manual alternative: start Postgres/Redis/Neo4j/Milvus yourself, then `python main.py` and `pnpm dev` in `frontend/`.

---

## Environment variables

See [`.env.example`](./.env.example). Never commit `.env`.

| Variable | Purpose |
|----------|---------|
| `DEEPSEEK_API_KEY` | DeepSeek API key (**recommended default**) |
| `DEEPSEEK_MODEL` | e.g. `deepseek-flash` |
| `DEFAULT_MODEL_PROVIDER` | Usually `deepseek` |
| `WEB_SEARCH_PROVIDER` | `deepseek` (default) or `baidu` |
| `ZHIPU_API_KEY` | Zhipu fallback |
| `POSTGRES_*` | PostgreSQL |
| `REDIS_*` / cache | Session & multi-layer cache |
| `JWT_SECRET_KEY` | Auth secret (change in production) |
| `AUTH_ENABLED` | Toggle auth |
| `NEO4J_*` / `MILVUS_*` | Graph & vector stores |

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

| 渠道 / Channel | 链接 / Link |
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
