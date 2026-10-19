# 剧本创作 Agent 平台

> 专业的短剧策划、创作、评估平台 - 支持 40+ AI Agents
> 黑白简明设计风格 | 生产级前后端分离架构

<img width="1224" height="705" alt="image" src="https://github.com/user-attachments/assets/9c4f9b0e-a268-4f32-a1dc-d7be0d0a20da" />

<img width="1234" height="734" alt="image" src="https://github.com/user-attachments/assets/1cd4c98e-691a-469f-baee-73277e9a8b92" />


<img width="1247" height="739" alt="image" src="https://github.com/user-attachments/assets/4f1c5b31-6a38-4817-948a-4a99ccfb73ac" />


**作者**: 宫灵瑞
**创建时间**: 2026年
**项目类型**: AI 剧本创作辅助系统

## 剧本知识库：
https://github.com/GongLingRui/skills

## 影视创作skills：
https://github.com/GongLingRui/screen-creative-skills

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-brightgreen.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/react-18+-61DAFB.svg)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/typescript-5.0+-3178C6.svg)](https://www.typescriptlang.org/)

## 目录

- [项目简介](#项目简介)
- [核心功能](#核心功能)
- [系统功能详解](#系统功能详解)
- [高级技术特性](#高级技术特性)
- [项目优势](#项目优势)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [系统架构详解](#系统架构详解)
- [快速开始](#快速开始)
- [API 端点](#api-端点)
- [开发指南](#开发指南)
- [联系与支持](#联系与支持)

## 项目简介

剧本创作 Agent 平台是一个基于 AI 的专业短剧创作辅助系统，整合了 40+ 个专业 Agents，覆盖从策划、创作到评估的全流程。系统采用黑白简明设计风格，提供流式实时交互体验。

## 核心功能

### 🎯 核心能力概览

```
┌────────────────────────────────────────────────────────┐
│                    剧本创作 Agent 平台                 │
│                      核心功能矩阵                          │
├────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┬─────────────┬─────────────┐                │
│  │  创作阶段   │  优化阶段    │  交付阶段     │                │
│  └─────────────┴─────────────┴─────────────┘                │
│           │                │                │                │
│           ▼                ▼                ▼                │
│  ┌──────────────────────────────────────────────┐      │
│  │  📋 策划类 (8个Agent)                          │      │
│  │  ✍️ 创作类 (5个Agent)                          │      │
│  │  ⭐ 评估类 (8个Agent)                          │      │
│  │  🔍 分析类 (5个Agent)                          │      │
│  │  🔄 工作流类 (2个Agent)                          │      │
│  │  👤 人物类 (2个Agent)                          │      │
│  │  📖 故事类 (5个Agent)                          │      │
│  │  🛠️ 工具类 (6个Agent)                          │      │
│  └──────────────────────────────────────────────┘      │
│           │                │                │                │
│           ▼                ▼                ▼                │
│  ┌──────────────────────────────────────────────┐      │
│  │  💾 记忆系统     │  📁 文件系统     │  🗒️ 笔记系统     │      │
│  │  双层记忆       │  项目管理       │  Note管理       │      │
│  └──────────────────────────────────────────────┘      │
│                                                         │
└────────────────────────────────────────────────────────┘
```

### 📊 功能统计

| 类别 | 数量 | 说明 |
|------|------|------|
| **Agents** | 40+ | 覆盖策划、创作、评估、分析、工作流、人物、故事、工具 8 大类 |
| **模型支持** | 8 | 智谱 AI 免费模型（文本、视觉、图像、视频生成） |
| **记忆类型** | 2 | 短期消息记忆 + 中期任务记忆 |
| **存储层级** | 3 | 内存 → Redis → PostgreSQL 三层架构 |
| **工作流阶段** | 8 | 从输入验证到结果格式化的完整流程 |
| **关系类型** | 9 | 家庭、恋爱、友情、工作、对抗、师徒、竞争、盟友、陌生人 |
| **内容类型** | 40+ | 覆盖文本、Markdown、JSON、各种专业分析类型 |
| **事件类型** | 9 | MESSAGE、LLM_CHUNK、THOUGHT、TOOL_CALL 等 |

## 系统功能详解

### 🎯 一、核心创作功能

#### 1.1 剧本策划 (📋 策划类)

**短剧策划助手** (`short_drama_planner`)
- ✅ 情绪价值第一性原理分析
- ✅ 黄金三秒钩子法则应用
- ✅ 期待-压抑-爆发三幕式结构设计
- ✅ 人设即容器理论指导
- ✅ 商业化卡点逻辑优化
- ✅ 智能工具调用（网络搜索、知识库、文件引用）
- ✅ 创作建议和指导

**使用场景**:
- "帮我策划一个关于都市爱情的短剧剧本"
- "分析这个短剧的商业价值和市场潜力"
- "优化这个剧本的情节结构"

#### 1.2 剧本创作 (✍️ 创作类)

**短剧创作助手** (`short_drama_creator`)
- ✅ 完整短剧剧本创作
- ✅ 生动的场景描写
- ✅ 符合人物性格的对话
- ✅ 引人入胜的故事情节
- ✅ **故事设定自动提取和约束管理**
- ✅ **角色语气一致性控制**
- ✅ 支持多种类型（现代都市爱情、轻松幽默喜剧、情感剧情、悬疑惊悚）

**使用场景**:
- "创作一个悬疑短剧的第一场戏"
- "根据这个大纲写第三场戏"
- "为这两个角色设计一段冲突对话"

**故事大纲生成** (`story_summary_generator`)
- ✅ 长篇故事精炼为大纲
- ✅ 核心情节提取
- ✅ 结构脉络梳理

**详细情节点** (`detailed_plot_points`)
- ✅ 简略情节点展开
- ✅ 细节补充和丰富
- ✅ 场景描写添加
- ✅ 情节衔接优化

**文档生成器** (`document_generator`)
- ✅ 格式转换（TXT、Markdown、JSON）
- ✅ 标准排版美化
- ✅ 批量文档生成
- ✅ PDF/Word 导出

#### 1.3 质量评估 (📊 评估类)

**短剧评估助手** (`short_drama_evaluation`)
- ✅ 故事文本深度评估与打分
- ✅ 多维度专业分析（核心爽点、故事类型、人物设定、人物关系、情节桥段）
- ✅ 市场竞争力分析
- ✅ 开发价值评估
- ✅ 优化建议提供
- ✅ 评分标准：优秀(8.5-10)、有潜力(8.0-8.4)、一般(7.5-7.9)、较差(0-7.4)

**剧本评估专家** (`script_evaluation`)
- ✅ 剧本结构深度分析
- ✅ 潜在问题识别
- ✅ 薄弱环节定位
- ✅ 具体优化方案提供
- ✅ 行业标准对比

**IP 价值评估** (`ip_evaluation`)
- ✅ IP 商业价值评估
- ✅ 市场潜力分析
- ✅ 受众定位
- ✅ IP 开发建议
- ✅ 同类 IP 竞品对比

**故事质量评估** (`story_evaluation`)
- ✅ 故事整体质量打分
- ✅ 吸引力要素分析
- ✅ 改进建议提供
- ✅ 优秀作品对比

**大纲评估** (`story_outline_evaluation`)
- ✅ 大纲结构完整性检查
- ✅ 创作可行性评估
- ✅ 调整建议提供
- ✅ 补充部分指出

**小说筛选评估** (`novel_screening_evaluation`)
- ✅ 小说改编短剧可行性评估
- ✅ IP 价值分析
- ✅ 改编建议提供
- ✅ 版权相关事项分析

**结果分析评估** (`result_analyzer_evaluation`)
- ✅ 多 Agent 结果深度分析
- ✅ 数据洞察提取
- ✅ 趋势发现
- ✅ 改进建议生成

**评分分析器** (`score_analyzer`)
- ✅ 评分数据统计分析
- ✅ 评分分布分析
- ✅ 趋势解读
- ✅ 历史数据对比

**文本处理评估** (`text_processor_evaluation`)
- ✅ 文本处理质量评估
- ✅ 处理效果分析
- ✅ 潜在问题识别
- ✅ 改进建议提供

#### 1.4 故事分析 (🔍 分析类)

**故事五元素分析** (`story_five_elements`)
- ✅ 核心冲突分析
- ✅ 人物设定分析
- ✅ 情节结构分析
- ✅ 主题思想分析
- ✅ 情感基调分析

**已播剧集分析** (`series_analysis`)
- ✅ 剧集数据统计
- ✅ 成功要素提取
- ✅ 行业趋势总结
- ✅ 可复制经验归纳

**剧本深度分析** (`drama_analysis`)
- ✅ 剧本结构解析
- ✅ 人物关系梳理
- ✅ 情节节奏分析
- ✅ 潜在价值挖掘

**故事类型分析** (`story_type_analyzer`)
- ✅ 故事类型识别
- ✅ 类型特征分析
- ✅ 创作规范建议
- ✅ 目标市场定位

**情节点分析** (`plot_points_analyzer`)
- ✅ 关键情节点识别
- ✅ 情节点结构分析
- ✅ 节奏评估
- ✅ 优化建议提供

#### 1.5 工作流编排 (🔄 工作流类)

**情节点工作流** (`plot_points_workflow`)
- ✅ 8 个工作流阶段自动执行
- ✅ 状态持久化和恢复
- ✅ 用户反馈注入
- ✅ 进度追踪

**8 个工作流阶段**:
1. 输入验证 (INPUT_VALIDATION)
2. 文本预处理 (TEXT_PREPROCESSING)
3. 故事大纲 (STORY_OUTLINE)
4. 人物小传 (CHARACTER_PROFILES)
5. 大情节点 (MAJOR_PLOT_POINTS)
6. 详细情节点 (DETAILED_PLOT_POINTS)
7. 思维导图 (MIND_MAP)
8. 结果格式化 (RESULT_FORMATTING)

**剧本创作工作流** (`drama_workflow`)
- ✅ 创意开发 → 大纲生成 → 剧本创作 → 质量检验
- ✅ 多阶段质量控制
- ✅ 支持迭代优化
- ✅ 输出标准化剧本

**结果集成器** (`result_integrator`)
- ✅ 多 Agent 结果聚合
- ✅ 格式统一
- ✅ 去重和合并
- ✅ 优先级排序

#### 1.6 人物管理 (👤 人物类)

**人物小传生成** (`character_profile_generator`)
- ✅ 识别人物
- ✅ 生成 300-500 字详细小传
- ✅ 分析人物性格特征
- ✅ 构建完整背景故事
- ✅ 定义人际关系

**人物关系分析** (`character_relationship_analyzer`)
- ✅ 识别人物
- ✅ 分析人物关系（9 种类型）
- ✅ 丰富关系详情
- ✅ 构建关系网络
- ✅ 生成分析报告

**9 种关系类型**:
1. 家庭关系 (family)
2. 恋爱关系 (romantic)
3. 友情关系 (friendship)
4. 工作/同事关系 (work)
5. 对抗/敌对关系 (antagonistic)
6. 师徒/指导关系 (mentor)
7. 竞争关系 (rival)
8. 盟友关系 (ally)
9. 陌生人关系 (stranger)

#### 1.7 故事创作 (📖 故事类)

**思维导图** (`mind_map`)
- ✅ 提取故事结构层次
- ✅ 生成可视化思维导图
- ✅ 支持在线编辑
- ✅ 导出多种格式

**故事大纲生成** (`story_summary_generator`)
- ✅ 内容提取
- ✅ 要点总结
- ✅ 结构梳理
- ✅ 精炼表达

**详细情节点** (`detailed_plot_points`)
- ✅ 情节点展开
- ✅ 细节补充
- ✅ 场景描写
- ✅ 情节衔接

**大情节点分析** (`major_plot_points`)
- ✅ 核心情节点提取
- ✅ 关键转折点识别
- ✅ 时间线构建
- ✅ 结构优化

**情节点分析** (`plot_points_analyzer`)
- ✅ 情节点识别
- ✅ 结构分析
- ✅ 节奏评估
- ✅ 优化建议

#### 1.8 智能工具 (🛠️ 工具类)

**网络搜索** (`websearch`)
- ✅ 实时搜索最新信息
- ✅ 聚合多个来源结果
- ✅ 标注信息来源
- ✅ 生成智能摘要

**知识库查询** (`knowledge`)
- ✅ 检索剧本创作专业知识
- ✅ 基于相似度匹配
- ✅ 提供权威专业资料
- ✅ 参考优秀作品片段

**文件引用解析** (`file_reference`)
- ✅ 解析 @ 符号引用（@file1, @image1 等）
- ✅ 解析自然语言引用（"第一个文件" 等）
- ✅ 提取文件内容
- ✅ 智能引用相关部分

**输出格式化** (`output_formatter`)
- ✅ 按规范格式化输出
- ✅ 统一样式风格
- ✅ 自动修正格式错误
- ✅ 提升输出质量

**剧集信息提取** (`series_info`)
- ✅ 智能提取剧集关键信息
- ✅ 整理结构化数据
- ✅ 规范化输出格式
- ✅ 支持批量处理

**剧名提取** (`series_name_extractor`)
- ✅ 准确识别短剧名称
- ✅ 提取别名和简称
- ✅ 规范化名称格式
- ✅ 过滤重复内容

**文本分割** (`text_splitter`)
- ✅ 智能识别分割边界
- ✅ 控制段落长度
- ✅ 保持语义完整性
- ✅ 识别章节场景边界

**文本截断** (`text_truncator`)
- ✅ 按指定长度截断
- ✅ 保证截断处语义完整
- ✅ 保留关键摘要信息
- ✅ 优化截断边界位置

### 💾 二、记忆与数据管理功能

#### 2.1 双层记忆系统

**短期记忆 (Short-Term Memory)**
- ✅ Redis List 存储
- ✅ 最近的 N 条对话消息
- ✅ 上下文连续性保证
- ✅ 会话级 TTL

**中期记忆 (Middle-Term Memory)**
- ✅ Redis List 存储
- ✅ Agent 完成任务后的总结
- ✅ 跨会话的知识复用
- ✅ 7 天 TTL

**记忆管理流程**:
1. Agent 处理前：构建上下文（短期消息 + 相关历史任务总结）
2. Agent 完成后：保存任务总结到中期记忆

#### 2.2 多轮对话上下文管理

**对话上下文 (ConversationContext)**
- ✅ 用户消息队列管理
- ✅ Orchestrator 调用记录
- ✅ 创建的 Notes 追踪
- ✅ 全局上下文管理
- ✅ 各 Agent 上下文隔离
- ✅ 共享内存管理
- ✅ 对话历史保存
- ✅ 压缩历史记录
- ✅ 上下文摘要生成
- ✅ 自动压缩触发

**上下文状态 (ContextState)**
- ✅ 用户/会话/Agent 名称
- ✅ 上下文数据存储
- ✅ 上下文类型分类
- ✅ 版本号管理
- ✅ 活跃状态标记
- ✅ 过期时间管理

#### 2.3 Notes 系统管理

**Note 数据结构**
- ✅ 用户/会话关联
- ✅ Agent 动作类型
- ✅ Note 名称和标题
- ✅ 内容类型分类
- ✅ 上下文内容
- ✅ 选择状态管理
- ✅ 用户评论支持
- ✅ 元数据扩展

**Notes 功能**
- ✅ Agent 输出自动保存为 Note
- ✅ 按动作类型查询
- ✅ 获取已选择的 Notes
- ✅ 批量更新选择状态
- ✅ 导出（TXT、JSON、MD 格式）
- ✅ 包含/排除用户评论

### 📁 三、项目管理功能

#### 3.1 项目生命周期管理

**项目 CRUD 操作**
- ✅ 创建项目（自动生成项目 ID）
- ✅ 获取项目信息
- ✅ 更新项目（名称、描述、状态、标签、元数据）
- ✅ 删除项目（软删除/永久删除）
- ✅ 列出项目（过滤、分页、排序）

**项目状态**
- ✅ ACTIVE - 活跃
- ✅ ARCHIVED - 已归档
- ✅ DELETED - 已删除

#### 3.2 项目文件管理

**文件操作**
- ✅ 添加文件到项目
- ✅ 获取项目文件列表
- ✅ 获取单个文件
- ✅ 更新文件内容
- ✅ 删除文件

**文件类型**
- ✅ CONVERSATION - 对话记录
- ✅ DRAMA_PLANNING - 策划结果
- ✅ CHARACTER_PROFILE - 人物小传
- ✅ SCRIPT - 剧本内容
- ✅ PLOT_POINTS - 情节点
- ✅ EVALUATION - 评估结果
- ✅ NOTE - 笔记
- ✅ REFERENCE - 参考文献

#### 3.3 项目目录结构

```
projects/
├── {project_id}/
│   ├── project.json              # 项目元数据
│   ├── conversations/            # 对话记录
│   ├── agent_outputs/           # Agent 输出
│   │   ├── drama_planning/      # 策划结果
│   │   ├── character_profiles/  # 人物小传
│   │   ├── scripts/            # 剧本内容
│   │   ├── plot_points/        # 情节点
│   │   └── evaluations/        # 评估结果
│   ├── resources/               # 资源文件
│   │   ├── images/            # 图片
│   │   ├── references/        # 参考文献
│   │   └── notes/            # 笔记
│   ├── exports/                 # 导出文件
│   │   ├── markdown/          # Markdown 导出
│   │   ├── pdf/              # PDF 导出
│   │   └── json/             # JSON 导出
│   └── versions/               # 版本历史
```

#### 3.4 项目搜索和模板

**搜索功能**
- ✅ 关键词搜索
- ✅ 用户 ID 过滤
- ✅ 标签过滤
- ✅ 日期范围过滤

**模板系统**
- ✅ 保存项目为模板
- ✅ 从模板创建项目
- ✅ 模板分类管理
- ✅ 公共/私有模板

**项目复制**
- ✅ 复制项目
- ✅ 选择性包含文件
- ✅ 文件类型过滤

### 🔧 四、辅助功能

#### 4.1 模型支持

**智谱 AI 免费模型** (8 种)
- ✅ glm-4-flash - 默认快速文本生成
- ✅ glm-4.7-flash - 最新版快速文本生成
- ✅ glm-4-flash-250414 - 特定版本 Flash 模型
- ✅ glm-4.1v-thinking-flash - 带思考链的推理模型
- ✅ glm-4v-flash - 视觉理解模型
- ✅ glm-4.6v-flash - 最新视觉理解模型
- ✅ cogview-3-flash - 图像生成模型
- ✅ cogvideox-flash - 视频生成模型

#### 4.2 搜索和知识库

**网络搜索**
- ✅ 自动意图识别
- ✅ 实时搜索
- ✅ 信息聚合
- ✅ 来源标注

**知识库查询**
- ✅ 语义搜索
- ✅ 相似度匹配
- ✅ 专业资料
- ✅ 片段参考

#### 4.3 文件处理

**支持的文件格式**
- ✅ PDF 文档
- ✅ Word 文档
- ✅ Excel 表格
- ✅ TXT 文本
- ✅ 图片文件
- ✅ 音频文件
- ✅ 视频文件

**引用格式**
- ✅ @ 符号引用：@file1, @image1, @pdf1 等
- ✅ 自然语言引用："第一个文件"、"最新上传的图片" 等

### 🎨 五、前端功能

#### 5.1 界面特性

- ✅ 黑白简明设计风格
- ✅ 高对比度配色
- ✅ 极简主义 UI
- ✅ 响应式布局
- ✅ 虚拟滚动（大量消息）

#### 5.2 交互体验

- ✅ SSE 流式实时响应
- ✅ 打字机效果
- ✅ 思考链展示
- ✅ 进度跟踪
- ✅ 状态指示

#### 5.3 内容展示

- ✅ Markdown 渲染
- ✅ 代码高亮
- ✅ 结构化数据展示
- ✅ 可视化图表支持

### 🔌 六、后端 API 功能

#### 6.1 核心 API

- ✅ `/juben/chat` - 聊天接口
- ✅ `/juben/models` - 模型列表
- ✅ `/juben/config` - 系统配置
- ✅ `/juben/health` - 健康检查

#### 6.2 Agents API

- ✅ `/juben/agents/list` - Agent 列表
- ✅ `/juben/agents/{agent_id}` - Agent 详情
- ✅ `/juben/agents/categories` - Agent 分类
- ✅ `/juben/agents/search` - 搜索 Agents

#### 6.3 专用 Agent 端点

- ✅ `/juben/creator/chat` - 创作助手
- ✅ `/juben/evaluation/chat` - 评估助手
- ✅ `/juben/websearch/chat` - 网络搜索
- ✅ `/juben/knowledge/chat` - 知识库查询

### 🚀 七、高级特性

#### 7.1 Agent as Tool 模式

- ✅ Agent 间相互调用
- ✅ 上下文隔离
- ✅ 结果聚合
- ✅ 超时控制（120 秒）

#### 7.2 故事设定管理

**设定类型**
- ✅ CHARACTER - 人物设定
- ✅ RELATIONSHIP - 人际关系
- ✅ LOCATION - 场景地点
- ✅ PROP - 重要道具
- ✅ EVENT - 重要事件
- ✅ DEATH - 角色死亡
- ✅ BIRTH - 角色出生
- ✅ ABILITY - 特殊能力
- ✅ BACKGROUND - 背景设定

**设定管理流程**
- ✅ 自动提取（LLM + 规则）
- ✅ Redis Hash 存储
- ✅ 自动去重和合并
- ✅ 生成约束文本
- ✅ 创作时自动应用

#### 7.3 角色语气控制

**语气风格** (12 种)
- ✅ CASUAL - 随意
- ✅ FORMAL - 正式
- ✅ AGGRESSIVE - 强势
- ✅ GENTLE - 温柔
- ✅ HUMOROUS - 幽默
- ✅ COLD - 冷漠
- ✅ ENTHUSIASTIC - 热情
- ✅ SARCASTIC - 讽刺
- ✅ SHY - 害羞
- ✅ CONFIDENT - 自信
- ✅ MYSTERIOUS - 神秘
- ✅ CHILDLIKE - 天真

**功能**
- ✅ 角色档案创建
- ✅ 对白样本管理
- ✅ Prompt 生成
- ✅ 场景匹配
- ✅ 项目关联

#### 7.4 工作流编排

**工作流阶段** (8 个)
1. ✅ INPUT_VALIDATION - 输入验证
2. ✅ TEXT_PREPROCESSING - 文本预处理
3. ✅ STORY_OUTLINE - 故事大纲
4. ✅ CHARACTER_PROFILES - 人物小传
5. ✅ MAJOR_PLOT_POINTS - 大情节点
6. ✅ DETAILED_PLOT_POINTS - 详细情节点
7. ✅ MIND_MAP - 思维导图
8. ✅ RESULT_FORMATTING - 结果格式化

**执行模式**
- ✅ 自动模式：完成当前阶段自动进入下一阶段
- ✅ 交互模式：每阶段完成后暂停，等待用户反馈
- ✅ 恢复模式：从任意阶段恢复执行

**状态管理**
- ✅ 状态持久化到 Redis
- ✅ 支持从任意阶段恢复
- ✅ 用户反馈注入
- ✅ 进度追踪

#### 7.5 流式事件系统

**事件类型** (9 种)
- ✅ MESSAGE - 普通消息
- ✅ LLM_CHUNK - LLM 内容片段
- ✅ THOUGHT - 思考过程
- ✅ TOOL_CALL - 工具调用开始
- ✅ TOOL_RETURN - 工具调用返回
- ✅ TOOL_PROCESSING - 工具处理中
- ✅ ERROR - 错误事件
- ✅ DONE - 完成信号
- ✅ BILLING - 计费信息
- ✅ PROGRESS - 进度更新
- ✅ SYSTEM - 系统消息

**内容类型** (40+ 种)
- ✅ 基础类型：TEXT, MARKDOWN, JSON
- ✅ 思考分析：THOUGHT, PLAN_STEP, INSIGHT
- ✅ 人物相关：CHARACTER_PROFILE, CHARACTER_RELATIONSHIP
- ✅ 故事结构：STORY_SUMMARY, STORY_OUTLINE, STORY_TYPE, FIVE_ELEMENTS
- ✅ 情节相关：MAJOR_PLOT, DETAILED_PLOT, DRAMA_ANALYSIS, PLOT_ANALYSIS
- ✅ 创作相关：SCRIPT, DRAMA_PLAN, PROPOSAL
- ✅ 可视化：MIND_MAP
- ✅ 评估相关：EVALUATION, SCRIPT_EVALUATION, STORY_EVALUATION 等
- ✅ 工具相关：SEARCH_RESULT, KNOWLEDGE_RESULT, REFERENCE_RESULT, DOCUMENT
- ✅ 系统相关：SYSTEM_PROGRESS, TOOL_RESULT, WORKFLOW_PROGRESS, RESULT_INTEGRATION

### 📊 八、数据统计与分析

#### 8.1 Token 使用统计

- ✅ 请求 Token 数
- ✅ 响应 Token 数
- ✅ 总 Token 数
- ✅ 积分扣减
- ✅ 请求时间戳
- ✅ 计费摘要

#### 8.2 性能监控

- ✅ 请求超时控制（30 秒）
- ✅ 最大重试次数（3 次）
- ✅ 连接池管理（10 个连接）
- ✅ 多级缓存（L1/L2/L3）
- ✅ 缓存 TTL 管理

### 🔐 九、安全与认证

#### 9.1 用户认证

- ✅ JWT Token 认证
- ✅ Cookie 认证支持
- ✅ 用户会话管理

#### 9.2 权限控制

- ✅ 用户 ID 隔离
- ✅ 会话 ID 隔离
- ✅ 项目 ID 隔离

### 📦 十、部署与运维

#### 10.1 启动方式

- ✅ 一键启动：`bash scripts/start_dev.sh`（自动拉起 PostgreSQL/Redis/Neo4j/Milvus + 前后端）
- ✅ 手动启动后端：`venv/bin/python main.py`（端口 8000）
- ✅ 手动启动前端：`cd frontend && pnpm dev`（端口 5173）

#### 10.2 环境配置

- ✅ 环境变量配置（.env 文件）
- ✅ 多环境配置（development/production）
- ✅ YAML 配置文件
- ✅ API Key 管理

## ⚡ 十一、高级技术特性

### 11.1 Server-Sent Events (SSE) 流式架构

**核心技术亮点**
- ✅ **实时双向通信**：基于 SSE 的流式响应，支持打字机效果
- ✅ **事件缓存机制**：Redis 缓存所有事件，支持断点续传
- ✅ **心跳检测**：30秒心跳间隔，自动检测连接状态
- ✅ **自动重连**：连接断开时自动重连，最多 3 次
- ✅ **增量传输**：支持 from_sequence 参数的增量传输
- ✅ **会话恢复**：通过 /chat/resume 端点恢复中断的会话

**SSE 数据流**
```
用户请求 → FastAPI → Agent Generator → SSE Events → 前端渲染
         ↓                                    ↓
    Redis 缓存 ← 事件序列化 ← emit_juben_event ← 实时更新
```

**事件序列化**
- ✅ 序列号：自增序列号，支持断点续传
- ✅ 时间戳：ISO 8601 格式
- ✅ 事件类型：9种标准事件类型
- ✅ 内容类型：40+ 种细分内容类型
- ✅ 元数据扩展：支持自定义元数据

### 11.2 Agent as Tool 模式

**设计理念**
- ✅ **递归调用**：Agent 可以调用其他 Agent 作为工具
- ✅ **上下文隔离**：每个 Agent 有独立的上下文和记忆
- ✅ **结果聚合**：支持多 Agent 结果聚合和集成
- ✅ **超时控制**：120 秒超时保护
- ✅ **错误传播**：子 Agent 错误向上传播
- ✅ **Token 累计**：支持跨 Agent Token 使用统计

**调用流程**
```
主 Agent 请求
    ↓
识别需要调用子 Agent
    ↓
构建子 Agent 请求（context 包含 parent_agent）
    ↓
子 Agent 处理（上下文隔离）
    ↓
返回结果给主 Agent
    ↓
主 Agent 聚合结果
```

**实现细节**
```python
# 子 Agent 调用示例
sub_agent = CharacterProfileGeneratorAgent()
context = {
    "parent_agent": self.agent_name,
    "tool_call": True,
    "user_id": user_id,
    "session_id": session_id
}
async for event in sub_agent.process_request(request_data, context):
    yield event
```

### 11.3 双层记忆系统

**架构设计**
- ✅ **L1 短期记忆**：Redis List，存储最近 N 条消息
- ✅ **L2 中期记忆**：Redis List，存储 Agent 任务总结
- ✅ **自动压缩**：消息数量超限时自动压缩
- ✅ **智能摘要**：使用 LLM 生成对话摘要
- ✅ **跨会话复用**：中期记忆可跨会话访问
- ✅ **TTL 管理**：短期 1 小时，中期 7 天

**记忆层次**
```
┌─────────────────────────────────────────┐
│         用户对话上下文                    │
├─────────────────────────────────────────┤
│  L1 短期记忆（最近 N 条消息）              │
│  - 存储：Redis List                      │
│  - TTL：1 小时                          │
│  - 容量：动态配置                        │
├─────────────────────────────────────────┤
│  L2 中期记忆（任务总结）                  │
│  - 存储：Redis List                      │
│  - TTL：7 天                            │
│  - 内容：Agent 任务完成后生成              │
├─────────────────────────────────────────┤
│  L3 持久化存储（PostgreSQL）              │
│  - 存储：Notes、Projects、Files          │
│  - TTL：永久                            │
└─────────────────────────────────────────┘
```

**记忆管理流程**
1. **读取阶段**：加载 L1 短期记忆 + L2 相关中期记忆
2. **处理阶段**：Agent 处理请求
3. **写入阶段**：保存消息到 L1，生成任务总结到 L2
4. **压缩阶段**：L1 容量超限时自动压缩

### 11.4 连接池管理系统

**单例模式实现**
- ✅ **连接池管理器**：`ConnectionPoolManager` 单例
- ✅ **多模型支持**：每个模型独立连接池
- ✅ **连接复用**：同一模型的多个请求复用连接
- ✅ **生命周期管理**：自动创建和回收连接
- ✅ **并发控制**：支持异步并发请求
- ✅ **健康检查**：定期检查连接状态

**连接池配置**
```python
# 每个模型 10 个连接
pool_size = 10
max_overflow = 5
pool_timeout = 30
pool_recycle = 3600
```

**性能优化**
- ✅ **连接预热**：启动时预创建连接
- ✅ **连接复用**：避免频繁创建销毁
- ✅ **超时回收**：空闲连接自动回收
- ✅ **并发优化**：异步 I/O 提升吞吐量

### 11.5 工作流编排引擎

**8 阶段自动化工作流**
```
INPUT_VALIDATION → TEXT_PREPROCESSING → STORY_OUTLINE
     ↓                  ↓                      ↓
CHARACTER_PROFILES → MAJOR_PLOT_POINTS → DETAILED_PLOT_POINTS
     ↓                  ↓                      ↓
  MIND_MAP → RESULT_FORMATTING → COMPLETE
```

**状态持久化**
- ✅ **Redis 存储**：工作流状态持久化到 Redis
- ✅ **阶段恢复**：从任意阶段恢复执行
- ✅ **用户反馈**：每阶段支持用户反馈注入
- ✅ **进度追踪**：实时追踪执行进度

**执行模式**
- ✅ **自动模式**：完成当前阶段自动进入下一阶段
- ✅ **交互模式**：每阶段完成后暂停，等待用户反馈
- ✅ **恢复模式**：从指定阶段恢复执行

### 11.6 个性化系统

**PersonaHelper 角色语气控制**
- ✅ **12 种语气风格**：CASUAL, FORMAL, AGGRESSIVE 等
- ✅ **对白样本管理**：收集和分析角色对白样本
- ✅ **Prompt 生成**：根据角色特征生成个性化 Prompt
- ✅ **场景匹配**：根据场景自动调整语气
- ✅ **项目关联**：角色档案与项目关联

**故事设定管理**
- ✅ **8 种设定类型**：CHARACTER, RELATIONSHIP, LOCATION 等
- ✅ **自动提取**：LLM + 规则自动提取设定
- ✅ **去重合并**：自动去重和合并重复设定
- ✅ **约束生成**：生成创作约束文本
- ✅ **自动应用**：创作时自动应用设定约束

### 11.7 三层存储架构

**存储层次**
```
┌─────────────────────────────────────────┐
│  L1 内存缓存（Python Dict）              │
│  - 速度：最快                           │
│  - 容量：最小                           │
│  - TTL：进程生命周期                     │
├─────────────────────────────────────────┤
│  L2 Redis 缓存                          │
│  - 速度：快                             │
│  - 容量：中等                           │
│  - TTL：可配置（1小时-7天）              │
├─────────────────────────────────────────┤
│  L3 PostgreSQL 持久化                    │
│  - 速度：中等                           │
│  - 容量：最大                           │
│  - TTL：永久                            │
└─────────────────────────────────────────┘
```

**缓存策略**
- ✅ **L1 → L2 → L3**：逐级查找，未命中时查找下一级
- ✅ **写回策略**：L1 写入后异步写回 L2 和 L3
- ✅ **TTL 管理**：自动过期和清理
- ✅ **容量控制**：LRU 淘汰策略

### 11.8 异步流式生成器

**Python Async Generator**
- ✅ **异步生成**：使用 `async for` 流式生成事件
- ✅ **非阻塞 I/O**：不阻塞主线程
- ✅ **内存优化**：逐条生成，不占用大量内存
- ✅ **实时反馈**：实时发送事件到前端

**代码示例**
```python
async def process_request(self, request_data, context):
    yield await self.emit_juben_event("start", "开始处理...")
    result = await self._process()
    yield await self.emit_juben_event("complete", "完成", result)
```

### 11.9 前端高级特性

**React Hooks 架构**
- ✅ **useStream Hook**：统一的事件流管理
- ✅ **useChat Hook**：聊天状态和逻辑封装
- ✅ **RobustSSEClient**：健壮的 SSE 客户端
- ✅ **虚拟滚动**：大量消息时的性能优化
- ✅ **自动重试**：请求失败时自动重试

**状态管理**
- ✅ **React Context**：全局状态管理
- ✅ **消息队列**：事件队列管理
- ✅ **缓存策略**：消息和事件缓存
- ✅ **乐观更新**：先更新 UI，后同步服务端

### 11.10 后端高级特性

**FastAPI 架构**
- ✅ **类型安全**：Pydantic 模型验证
- ✅ **自动文档**：OpenAPI/Swagger 自动生成
- ✅ **依赖注入**：优雅的依赖管理
- ✅ **中间件**：CORS、日志、认证等中间件

**动态 Agent 加载**
- ✅ **运行时加载**：使用 `importlib` 动态加载 Agent
- ✅ **命名映射**：前端 agent_id 到后端类的映射
- ✅ **错误处理**：加载失败时返回 404
- ✅ **扩展性**：新增 Agent 无需修改路由

**流式响应生成**
- ✅ **StreamResponseGenerator**：统一的事件流生成器
- ✅ **事件转换**：Agent 事件转换为 SSE 事件
- ✅ **序列号管理**：自增序列号
- ✅ **缓存机制**：Redis 缓存所有事件

### 11.11 可观测性系统

**结构化日志**
- ✅ **分级日志**：DEBUG, INFO, WARNING, ERROR
- ✅ **上下文信息**：user_id, session_id, agent_name
- ✅ **结构化输出**：JSON 格式日志
- ✅ **日志轮转**：按大小和时间轮转

**性能监控**
- ✅ **Token 统计**：请求和响应 Token 数
- ✅ **响应时间**：每个请求的响应时间
- ✅ **错误率**：错误请求统计
- ✅ **并发数**：当前并发请求数

**错误追踪**
- ✅ **错误堆栈**：完整的错误堆栈信息
- ✅ **上下文数据**：错误发生时的上下文
- ✅ **错误分类**：按类型分类错误
- ✅ **告警机制**：关键错误实时告警

### 11.12 高可用性设计

**容错机制**
- ✅ **自动重试**：LLM 请求失败时自动重试（最多 3 次）
- ✅ **超时控制**：30 秒超时保护
- ✅ **降级策略**：核心功能降级保障
- ✅ **熔断机制**：连续失败时熔断

**数据一致性**
- ✅ **事务管理**：数据库操作使用事务
- ✅ **幂等性**：API 设计保证幂等性
- ✅ **数据校验**：Pydantic 模型校验
- ✅ **备份机制**：定期数据备份

**负载均衡**
- ✅ **连接池**：数据库连接池
- ✅ **并发控制**：异步并发控制
- ✅ **请求队列**：请求队列管理
- ✅ **限流机制**：API 限流保护

## 🏆 十二、项目优势

### 12.1 业务领域优势

**专业深耕**
- ✅ **剧本创作垂直领域**：专注于短剧创作，覆盖策划、创作、评估全流程
- ✅ **40+ 专业 Agents**：每个 Agent 针对特定任务优化
- ✅ **8 大 Agent 分类**：策划、创作、评估、分析、工作流、人物、故事、工具
- ✅ **行业最佳实践**：融合剧本创作行业经验和 AI 技术

**智能化创作**
- ✅ **情绪价值第一性原理**：基于情绪价值分析剧本吸引力
- ✅ **黄金三秒钩子法则**：优化开场吸引观众注意力
- ✅ **期待-压抑-爆发结构**：三幕式结构设计
- ✅ **人设即容器理论**：人物设定驱动故事发展

### 12.2 技术架构优势

**微服务架构**
- ✅ **前后端分离**：React 前端 + FastAPI 后端
- ✅ **Agent 模块化**：每个 Agent 独立模块
- ✅ **服务解耦**：各模块低耦合，易于维护和扩展
- ✅ **水平扩展**：支持水平扩展和负载均衡

**流式响应**
- ✅ **实时交互**：SSE 流式响应，实时反馈
- ✅ **打字机效果**：模拟人类打字，提升用户体验
- ✅ **断点续传**：网络中断后可恢复
- ✅ **事件缓存**：所有事件缓存到 Redis

**记忆系统**
- ✅ **双层记忆**：短期 + 中期双层记忆
- ✅ **智能压缩**：自动压缩和摘要
- ✅ **跨会话复用**：中期记忆跨会话访问
- ✅ **TTL 管理**：自动过期和清理

### 12.3 用户体验优势

**极简设计**
- ✅ **黑白简明风格**：极简主义 UI 设计
- ✅ **高对比度**：黑色背景白色文字，清晰易读
- ✅ **无干扰界面**：专注于创作本身
- ✅ **响应式布局**：适配各种设备

**实时反馈**
- ✅ **流式响应**：实时显示 Agent 思考和输出
- ✅ **进度跟踪**：显示当前处理阶段
- ✅ **状态指示**：清晰的加载和完成状态
- ✅ **错误提示**：友好的错误提示和解决建议

**智能辅助**
- ✅ **自动保存**：Agent 输出自动保存为 Notes
- ✅ **文件引用**：支持 @ 符号引用文件
- ✅ **知识库查询**：智能检索专业知识
- ✅ **网络搜索**：实时搜索最新信息

### 12.4 开发效率优势

**统一架构**
- ✅ **BaseJubenAgent**：统一的 Agent 基类
- ✅ **标准化接口**：统一的 LLM 调用接口
- ✅ **事件系统**：统一的事件发射和接收
- ✅ **错误处理**：统一的错误处理机制

**可扩展性**
- ✅ **Agent as Tool**：Agent 可调用其他 Agent
- ✅ **动态加载**：运行时动态加载 Agent
- ✅ **插件化**：新增 Agent 无需修改核心代码
- ✅ **配置驱动**：YAML 配置驱动行为

**开发体验**
- ✅ **类型安全**：Pydantic 模型类型检查
- ✅ **自动文档**：OpenAPI/Swagger 自动生成
- ✅ **日志系统**：结构化日志便于调试
- ✅ **测试支持**：支持单元测试和集成测试

### 12.5 性能优势

**高性能**
- ✅ **异步 I/O**：Python async/await 提升 I/O 性能
- ✅ **连接池**：数据库连接池复用连接
- ✅ **多级缓存**：L1/L2/L3 三级缓存
- ✅ **流式传输**：逐条生成，降低内存占用

**可扩展性**
- ✅ **水平扩展**：支持多实例部署
- ✅ **负载均衡**：支持负载均衡
- ✅ **分布式缓存**：Redis 分布式缓存
- ✅ **数据库分片**：支持数据库分片

**成本优化**
- ✅ **免费模型**：使用智谱 AI 免费模型
- ✅ **Token 优化**：智能控制 Token 使用
- ✅ **缓存策略**：减少重复请求
- ✅ **按需付费**：按使用量付费

### 12.6 稳定性优势

**容错机制**
- ✅ **自动重试**：LLM 请求失败时自动重试
- ✅ **超时控制**：30 秒超时保护
- ✅ **降级策略**：核心功能降级保障
- ✅ **熔断机制**：连续失败时熔断

**数据安全**
- ✅ **用户隔离**：用户 ID 隔离
- ✅ **会话隔离**：会话 ID 隔离
- ✅ **项目隔离**：项目 ID 隔离
- ✅ **数据加密**：敏感数据加密存储

**监控告警**
- ✅ **结构化日志**：JSON 格式日志
- ✅ **性能监控**：Token、响应时间监控
- ✅ **错误追踪**：完整错误堆栈
- ✅ **实时告警**：关键错误实时告警

### 12.7 创新性优势

**技术创新**
- ✅ **Agent as Tool 模式**：创新的 Agent 调用模式
- ✅ **双层记忆系统**：短期 + 中期双层记忆
- ✅ **流式事件系统**：SSE 流式事件系统
- ✅ **个性化系统**：PersonaHelper 个性化系统

**业务创新**
- ✅ **故事设定管理**：自动提取和应用故事设定
- ✅ **角色语气控制**：12 种语气风格控制
- ✅ **工作流编排**：8 阶段自动化工作流
- ✅ **智能评估**：多维度剧本质量评估

**用户体验创新**
- ✅ **流式交互**：实时流式交互体验
- ✅ **断点续传**：网络中断后可恢复
- ✅ **智能引用**：@ 符号智能引用文件
- ✅ **自动保存**：Agent 输出自动保存

### 12.8 生态优势

**多模型支持**
- ✅ **智谱 AI**：8 种免费模型
- ✅ **文本生成**：glm-4-flash, glm-4.7-flash
- ✅ **视觉理解**：glm-4v-flash, glm-4.6v-flash
- ✅ **图像生成**：cogview-3-flash
- ✅ **视频生成**：cogvideox-flash

**多格式支持**
- ✅ **文档格式**：PDF, Word, Excel, TXT
- ✅ **导出格式**：Markdown, JSON, TXT
- ✅ **图像格式**：PNG, JPG, JPEG
- ✅ **音视频**：MP3, MP4, AVI

**开放性**
- ✅ **API 开放**：RESTful API
- ✅ **文档完善**：详细的 API 文档
- ✅ **示例丰富**：丰富的使用示例
- ✅ **社区支持**：活跃的社区支持

## 技术栈

### 后端技术栈

#### 核心框架
- **FastAPI 0.104.1** - 现代化、高性能的 Web 框架
- **Uvicorn 0.24.0** - ASGI 服务器
- **Python 3.8+** - 编程语言

#### 数据验证与配置
- **Pydantic 2.5.0** - 数据验证和设置管理
- **Pydantic Settings 2.0.0** - 配置管理
- **Python-dotenv 1.0.0** - 环境变量管理
- **PyYAML 6.0.1** - YAML 配置文件

#### HTTP 客户端
- **aiohttp 3.9.0** - 异步 HTTP 客户端
- **httpx 0.25.0** - 现代化 HTTP 客户端

#### AI/LLM 集成
- **zhipuai 2.1.5** - 智谱 AI SDK
- **OpenAI 1.3.0** - OpenAI API (可选)
- **LangChain 0.1.0** - LLM 应用框架
- **LangSmith 0.0.69** - LLM 应用追踪

#### 阿里云服务
- **DashScope 1.14.0** - 阿里云模型服务

#### 数据库
- **asyncpg 0.29.0** - 异步 PostgreSQL 驱动
- **redis 5.0.0** - Redis 客户端
- **PyMilvus 2.4.0** - 向量数据库 Milvus
- **neo4j 5.14.0** - 图数据库 (可选)

#### 日志与监控
- **structlog 23.2.0** - 结构化日志
- **prometheus-client 0.20.0** - Prometheus 监控

#### 认证与安全
- **PyJWT 2.8.0** - JWT 认证
- **passlib 1.7.4** - 密码哈希
- **python-multipart 0.0.6** - 文件上传

#### 性能优化
- **tenacity 8.2.0** - 重试机制
- **backoff 2.2.0** - 退避策略

#### 开发工具
- **pytest 7.4.0** - 测试框架
- **pytest-asyncio 0.21.0** - 异步测试
- **pytest-cov 4.1.0** - 测试覆盖率
- **black 23.11.0** - 代码格式化
- **flake8 6.1.0** - 代码检查

### 前端技术栈

#### 核心框架
- **React 18.3.1** - UI 框架
- **React DOM 18.3.1** - DOM 渲染
- **TypeScript 5.4.5** - 类型安全
- **Vite 5.2.8** - 构建工具

#### 路由
- **React Router DOM 6.22.0** - 客户端路由

#### UI 组件
- **lucide-react 0.344.0** - 图标库
- **clsx 2.1.0** - 条件类名
- **@xyflow/react 12.0.0** - 流程图组件

#### 数据可视化
- **d3-force 3.0.0** - 力导向图
- **react-force-graph-2d 1.29.1** - 2D 力导向图 React 组件
- **markmap-lib 0.18.0** - 思维导图库
- **markmap-view 0.18.0** - 思维导图查看器
- **mermaid 10.9.1** - 图表绘制

#### Markdown 渲染
- **react-markdown 9.0.1** - Markdown 渲染
- **remark-gfm 4.0.0** - GitHub Flavored Markdown
- **react-syntax-highlighter 7.3.0** - 代码高亮
- **rehype-highlight 7.0.0** - 代码高亮插件

#### SSE 与实时通信
- **eventsource-parser 1.1.2** - Server-Sent Events 解析

#### 工具库
- **date-fns 3.3.1** - 日期处理
- **zustand 4.5.2** - 状态管理
- **@tanstack/react-virtual 3.10.8** - 虚拟滚动

#### 开发工具
- **ESLint 8.57.0** - 代码检查
- **@typescript-eslint 7.7.0** - TypeScript ESLint
- **Tailwind CSS 3.4.3** - CSS 框架
- **PostCSS 8.4.38** - CSS 处理
- **Autoprefixer 10.4.19** - CSS 自动前缀

### 基础设施

#### 数据存储
- **PostgreSQL** - 关系型数据库
- **Redis** - 缓存和会话存储
- **Milvus** - 向量数据库 (知识库)

#### AI 模型
- **智谱 AI** - glm-4-flash, glm-4.7-flash, glm-4v-flash, cogview-3-flash, cogvideox-flash
- **阿里云通义千问** - 备用模型

## 项目结构

### 整体架构

```
juben/
├── frontend/                 # 前端项目 (React + TypeScript + Vite)
│   ├── src/
│   │   ├── components/      # React 组件
│   │   ├── hooks/          # 自定义 Hooks
│   │   ├── services/       # API 服务
│   │   ├── utils/          # 工具函数
│   │   ├── types/          # TypeScript 类型
│   │   ├── store/          # 状态管理
│   │   └── App.tsx         # 主应用
│   ├── public/             # 静态资源
│   ├── package.json        # 依赖配置
│   └── vite.config.ts     # Vite 配置
│
├── apis/                   # 后端 API 层
│   └── core/
│       ├── api_routes.py   # 核心 API 路由
│       ├── chat_routes.py  # 聊天 API 路由
│       ├── schemas.py      # Pydantic 模型
│       └── distributed_lock_dependencies.py  # 分布式锁依赖
│
├── agents/                 # Agent 智能体
│   ├── base_juben_agent.py           # Agent 基类
│   ├── short_drama_planner_agent.py  # 短剧策划助手
│   ├── short_drama_creator_agent.py  # 短剧创作助手
│   ├── short_drama_evaluation_agent.py  # 短剧评估助手
│   ├── character_profile_generator_agent.py  # 人物小传生成
│   ├── character_relationship_analyzer_agent.py  # 人物关系分析
│   ├── story_five_elements_agent.py  # 故事五元素分析
│   ├── plot_points_workflow_agent.py  # 情节点工作流
│   ├── websearch_agent.py      # 网络搜索
│   ├── knowlege_agent.py        # 知识库查询
│   ├── file_reference_agent.py  # 文件引用解析
│   └── ...                     # 其他 30+ Agents
│
├── workflows/              # 工作流编排
│   ├── plot_points_workflow.py  # 情节点工作流编排器
│   └── drama_workflow.py       # 剧本创作工作流
│
├── utils/                  # 工具模块
│   ├── storage_manager.py      # 存储管理器
│   ├── stream_manager.py       # 流式响应管理器
│   ├── agent_dispatch.py       # Agent 调度器
│   ├── reference_resolver.py   # 引用解析器
│   ├── logger.py              # 日志工具
│   ├── error_handler.py       # 错误处理
│   ├── persona_helper.py      # 角色语气助手
│   ├── llm_connection_pool.py  # LLM 连接池
│   └── ...
│
├── config/                 # 配置文件
│   └── settings.py          # 系统配置
│
├── models/                 # 数据模型
│   ├── conversation.py      # 对话模型
│   ├── message.py           # 消息模型
│   ├── note.py              # 笔记模型
│   ├── project.py           # 项目模型
│   └── user.py              # 用户模型
│
├── db/                     # 数据库
│   ├── session.py           # 数据库会话
│   ├── crud.py              # CRUD 操作
│   └── migrations/          # 数据库迁移
│
├── tests/                  # 测试
│   ├── test_agents.py       # Agent 测试
│   ├── test_api.py          # API 测试
│   └── test_utils.py        # 工具测试
│
├── docs/                   # 文档
│   └── SSE_TECHNICAL_DOCUMENTATION.md  # SSE 技术文档
│
├── requirements.txt         # Python 依赖
├── .env.example           # 环境变量示例
├── scripts/start_dev.sh   # 唯一启动入口（外部依赖 + 前后端）
├── docker-compose.yml     # Neo4j 图数据库
├── docker-compose.milvus.yml  # Milvus 向量数据库
└── README.md             # 项目说明文档
```

### 目录说明

#### frontend/ - 前端项目
- **components/**: React 组件，包括聊天界面、消息列表、文件管理器等
- **hooks/**: 自定义 React Hooks，包括 useStream, useChat 等
- **services/**: API 服务封装，包括 chatService, sseClient 等
- **utils/**: 前端工具函数
- **types/**: TypeScript 类型定义
- **store/**: Zustand 状态管理

#### apis/ - 后端 API 层
- **core/api_routes.py**: 核心 API 端点（健康检查、模型列表、配置等）
- **core/chat_routes.py**: 聊天 API 端点（聊天、会话管理等）
- **core/schemas.py**: Pydantic 数据模型

#### agents/ - Agent 智能体
- **base_juben_agent.py**: 所有 Agent 的基类
- **short_drama_planner_agent.py**: 短剧策划助手
- **short_drama_creator_agent.py**: 短剧创作助手
- **short_drama_evaluation_agent.py**: 短剧评估助手
- 其他 40+ 个专业 Agent

#### workflows/ - 工作流编排
- **plot_points_workflow.py**: 8 阶段情节点工作流
- **drama_workflow.py**: 剧本创作工作流

#### utils/ - 工具模块
- **storage_manager.py**: 三层存储架构管理器
- **stream_manager.py**: SSE 流式响应管理器
- **agent_dispatch.py**: Agent 调度器
- **reference_resolver.py**: 文件引用解析器
- **logger.py**: 结构化日志工具
- **error_handler.py**: 统一错误处理
- **persona_helper.py**: 角色语气控制助手

## 系统架构详解

### 整体架构图

```
┌────────────────────────────────────────────────────────┐
│                   用户浏览器                        │
│              (React + TypeScript)                   │
└────────────────────┬───────────────────────────────┘
                     │ SSE / WebSocket
                     ▼
┌────────────────────────────────────────────────────────┐
│              FastAPI 后端服务器                     │
│  ┌──────────────────────────────────────────────┐  │
│  │  API 路由层 (chat_routes, api_routes)     │  │
│  └──────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────┐  │
│  │  Agent 调度层 (agent_dispatch)            │  │
│  └──────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────┐  │
│  │  Agent 执行层 (40+ Agents)                │  │
│  │  - 策划类 Agent                          │  │
│  │  - 创作类 Agent                          │  │
│  │  - 评估类 Agent                          │  │
│  │  - 分析类 Agent                          │  │
│  │  - 工具类 Agent                          │  │
│  └──────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────┐  │
│  │  工作流编排层 (workflows)                │  │
│  └──────────────────────────────────────────────┘  │
└────────────────────┬───────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
┌───────────┐ ┌──────────┐ ┌────────────┐
│   Redis   │ │PostgreSQL│ │  智谱 AI   │
│ (缓存层)  │ │ (持久化) │ │  (LLM)     │
└───────────┘ └──────────┘ └────────────┘
```

### 数据流图

```
用户输入
   │
   ▼
前端组件 (React)
   │
   │ HTTP POST /juben/chat
   ▼
API 路由层 (chat_routes.py)
   │
   │ 解析请求
   ▼
Agent 调度器 (agent_dispatch.py)
   │
   │ 动态加载 Agent
   ▼
Agent 执行 (具体 Agent)
   │
   ├─→ LLM 调用 (智谱 AI)
   ├─→ 工具调用 (搜索、知识库、文件引用)
   └─→ 子 Agent 调用 (Agent as Tool)
   │
   │ emit_juben_event()
   ▼
流式响应管理器 (stream_manager.py)
   │
   │ SSE 事件流
   ▼
前端渲染 (useStream Hook)
   │
   ▼
用户界面更新
```

### Agent 架构图

```
BaseJubenAgent (基类)
   │
   ├─→ 统一 LLM 调用接口
   ├─→ 事件发射系统
   ├─→ 记忆管理系统
   ├─→ 连接池管理
   └─→ 错误处理
   │
   ▼
┌─────────────────────────────────────┐
│         具体 Agent 实现            │
├─────────────────────────────────────┤
│ - process_request()               │
│   - 上下文构建                   │
│   - 记忆加载                     │
│   - LLM 调用                     │
│   - 结果格式化                   │
│   - emit_juben_event()          │
└─────────────────────────────────────┘
   │
   │ Agent as Tool
   ▼
子 Agent 调用
   │
   └─→ 上下文隔离
   └─→ 独立记忆
   └─→ 结果聚合
```

## 快速开始

### 环境要求

- **Python**: 3.8 或更高版本
- **Node.js**: 18 或更高版本
- **PostgreSQL**: 13 或更高版本
- **Redis**: 6 或更高版本

### 安装步骤

#### 1. 克隆项目

```bash
git clone https://github.com/your-repo/juben.git
cd juben
```

#### 2. 配置环境变量

复制 `.env.example` 到 `.env` 并配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# 智谱 AI API Key
ZHIPUAI_API_KEY=your_api_key_here

# 数据库配置
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/juben
REDIS_URL=redis://localhost:6379/0

# 阿里云 DashScope (可选)
DASHSCOPE_API_KEY=your_dashscope_key_here

# OpenAI API Key (可选)
OPENAI_API_KEY=your_openai_key_here
```

#### 3. 安装后端依赖

```bash
pip install -r requirements.txt
```

#### 4. 初始化数据库

```bash
# 创建数据库
createdb juben

# 运行迁移
python -m db.migrations.init
```

#### 5. 安装前端依赖

```bash
cd frontend
npm install
```

#### 6. 启动服务

**唯一启动入口（自动拉起外部依赖 + 前后端）：**

```bash
bash scripts/start_dev.sh
```

该脚本会自动：
1. 启动外部依赖：PostgreSQL/Redis（homebrew）、Neo4j/Milvus（docker compose）
2. 启动后端：http://localhost:8000
3. 启动前端：http://localhost:5173

**手动启动（可选）：**

后端:
```bash
venv/bin/python main.py
```

前端:
```bash
cd frontend
pnpm dev
```

#### 7. 访问应用

- 前端: http://localhost:5173
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

### 验证安装

访问健康检查端点：

```bash
curl http://localhost:8000/juben/health
```

预期返回：
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

## API 端点

### 核心 API

#### 健康检查
```
GET /juben/health
```

**响应**:
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

#### 获取模型列表
```
GET /juben/models
```

**响应**:
```json
{
  "models": [
    {
      "id": "glm-4-flash",
      "name": "GLM-4 Flash",
      "type": "text",
      "provider": "zhipuai"
    }
  ]
}
```

#### 获取系统配置
```
GET /juben/config
```

**响应**:
```json
{
  "features": {
    "websearch": true,
    "knowledge": true,
    "file_reference": true
  },
  "models": {
    "default": "glm-4-flash",
    "vision": "glm-4v-flash"
  }
}
```

### 聊天 API

#### 发送聊天消息
```
POST /juben/chat
```

**请求体**:
```json
{
  "input": "帮我策划一个都市爱情短剧",
  "user_id": "user123",
  "session_id": "session456",
  "agent_id": "short_drama_planner",
  "file_ids": ["file1", "file2"],
  "auto_mode": true,
  "user_selections": []
}
```

**响应**: Server-Sent Events (SSE) 流

#### 恢复会话
```
POST /juben/chat/resume
```

**请求体**:
```json
{
  "session_id": "session456",
  "message_id": "msg789",
  "from_sequence": 10
}
```

#### 停止会话
```
POST /juben/chat/stop
```

**请求体**:
```json
{
  "session_id": "session456",
  "message_id": "msg789"
}
```

#### 获取会话列表
```
GET /juben/chat/sessions?user_id=user123
```

#### 获取会话历史
```
GET /juben/chat/sessions/{session_id}
```

#### 删除会话
```
DELETE /juben/chat/sessions/{session_id}
```

### Agents API

#### 获取 Agent 列表
```
GET /juben/agents/list
```

**响应**:
```json
{
  "agents": [
    {
      "agent_id": "short_drama_planner",
      "name": "短剧策划助手",
      "category": "策划类",
      "description": "专业短剧策划，提供创作建议"
    }
  ]
}
```

#### 获取 Agent 详情
```
GET /juben/agents/{agent_id}
```

#### 获取 Agent 分类
```
GET /juben/agents/categories
```

#### 搜索 Agents
```
GET /juben/agents/search?q=策划
```

### Notes API

#### 创建 Note
```
POST /juben/notes
```

**请求体**:
```json
{
  "user_id": "user123",
  "session_id": "session456",
  "title": "剧本大纲",
  "content": "...",
  "content_type": "DRAMA_PLANNING",
  "metadata": {}
}
```

#### 获取 Notes 列表
```
GET /juben/notes?user_id=user123
```

#### 更新 Note
```
PUT /juben/notes/{note_id}
```

#### 删除 Note
```
DELETE /juben/notes/{note_id}
```

#### 批量选择 Notes
```
POST /juben/notes/select
```

**请求体**:
```json
{
  "note_ids": ["note1", "note2"],
  "selected": true
}
```

#### 导出 Notes
```
POST /juben/notes/export
```

**请求体**:
```json
{
  "note_ids": ["note1", "note2"],
  "format": "markdown",
  "include_comments": true
}
```

### Projects API

#### 创建项目
```
POST /juben/projects
```

**请求体**:
```json
{
  "user_id": "user123",
  "name": "我的短剧项目",
  "description": "项目描述",
  "tags": ["都市", "爱情"]
}
```

#### 获取项目列表
```
GET /juben/projects?user_id=user123
```

#### 获取项目详情
```
GET /juben/projects/{project_id}
```

#### 更新项目
```
PUT /juben/projects/{project_id}
```

#### 删除项目
```
DELETE /juben/projects/{project_id}
```

#### 添加文件到项目
```
POST /juben/projects/{project_id}/files
```

### SSE 事件格式

所有 SSE 事件遵循以下格式：

```
event: {event_type}
data: {json_data}
id: {sequence_id}
retry: 3000
```

**事件类型**:
- `MESSAGE`: 普通消息
- `LLM_CHUNK`: LLM 内容片段
- `THOUGHT`: 思考过程
- `TOOL_CALL`: 工具调用
- `TOOL_RETURN`: 工具返回
- `PROGRESS`: 进度更新
- `ERROR`: 错误事件
- `DONE`: 完成信号
- `SYSTEM`: 系统消息

## 开发指南

### 开发环境设置

#### 1. Python 开发环境

```bash
# 安装开发依赖
pip install -r requirements.txt

# 安装 pre-commit hooks
pre-commit install

# 运行测试
pytest

# 运行测试并查看覆盖率
pytest --cov=apis --cov=agents --cov-report=html
```

#### 2. 前端开发环境

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 运行类型检查
npm run type-check

# 运行 lint
npm run lint
```

### 创建新 Agent

#### 1. 创建 Agent 文件

在 `agents/` 目录创建新文件：

```python
# agents/my_custom_agent.py
from typing import AsyncGenerator, Dict, Any, Optional
from agents.base_juben_agent import BaseJubenAgent

class MyCustomAgent(BaseJubenAgent):
    """我的自定义 Agent"""

    def __init__(self, model_provider: str = "zhipu"):
        super().__init__(
            agent_name="my_custom_agent",
            model_provider=model_provider
        )

    async def process_request(
        self,
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """处理请求"""
        # 发送开始事件
        yield await self.emit_juben_event(
            "start",
            "开始处理...",
            {"stage": "init"}
        )

        try:
            # 处理逻辑
            result = await self._process(request_data)

            # 发送完成事件
            yield await self.emit_juben_event(
                "complete",
                "处理完成",
                {"result": result}
            )
        except Exception as e:
            # 发送错误事件
            yield await self.emit_juben_event(
                "error",
                f"处理失败: {str(e)}",
                {"error": str(e)}
            )

    async def _process(self, request_data: Dict[str, Any]) -> Any:
        """实际处理逻辑"""
        input_text = request_data.get("input", "")
        # 调用 LLM
        messages = [
            {"role": "system", "content": "你是一个专业助手"},
            {"role": "user", "content": input_text}
        ]
        response = await self._call_llm(messages)
        return response
```

#### 2. 注册 Agent

在 `apis/core/chat_routes.py` 的 `_resolve_agent_import()` 函数中添加映射：

```python
def _resolve_agent_import(agent_id: Optional[str]) -> tuple[str, str]:
    mapping = {
        # ... 其他映射
        "my_custom": ("agents.my_custom_agent", "MyCustomAgent"),
    }
    # ...
```

#### 3. 测试 Agent

```bash
# 启动服务
bash scripts/start_dev.sh

# 发送测试请求
curl -X POST http://localhost:8000/juben/chat \
  -H "Content-Type: application/json" \
  -d '{
    "input": "测试请求",
    "user_id": "test_user",
    "agent_id": "my_custom"
  }'
```

### 创建新工作流

#### 1. 定义工作流阶段

```python
# workflows/my_custom_workflow.py
from enum import Enum
from typing import Dict, Any, List

class MyWorkflowStage(Enum):
    """工作流阶段"""
    STAGE_1 = "stage_1"
    STAGE_2 = "stage_2"
    STAGE_3 = "stage_3"
```

#### 2. 实现工作流编排器

```python
from workflows.base_workflow import BaseWorkflow

class MyCustomWorkflow(BaseWorkflow):
    """自定义工作流"""

    def __init__(self):
        super().__init__()
        self.stages = [
            MyWorkflowStage.STAGE_1,
            MyWorkflowStage.STAGE_2,
            MyWorkflowStage.STAGE_3
        ]

    async def execute_stage(
        self,
        stage: MyWorkflowStage,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行阶段"""
        if stage == MyWorkflowStage.STAGE_1:
            return await self._execute_stage_1(context)
        elif stage == MyWorkflowStage.STAGE_2:
            return await self._execute_stage_2(context)
        elif stage == MyWorkflowStage.STAGE_3:
            return await self._execute_stage_3(context)

    async def _execute_stage_1(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """阶段 1 实现"""
        # 处理逻辑
        return {"stage_1_result": "..."}

    # ... 其他阶段实现
```

### 添加新的 SSE 事件类型

#### 1. 定义事件类型

在 `apis/core/schemas.py` 中添加：

```python
class StreamEventType(str, Enum):
    # 现有事件类型
    MESSAGE = "message"
    # ...

    # 新增事件类型
    MY_CUSTOM_EVENT = "my_custom_event"
```

#### 2. 发送事件

在 Agent 中发送新事件：

```python
yield await self.emit_juben_event(
    "my_custom_event",
    "自定义事件消息",
    {"custom_data": "..."}
)
```

#### 3. 前端处理事件

在 `frontend/src/hooks/useStream.ts` 中添加处理：

```typescript
switch (event.event_type) {
  case "my_custom_event":
    // 处理自定义事件
    console.log("Custom event:", event.data);
    break;
}
```

### 测试指南

#### 单元测试

```python
# tests/test_my_custom_agent.py
import pytest
from agents.my_custom_agent import MyCustomAgent

@pytest.mark.asyncio
async def test_my_custom_agent():
    """测试自定义 Agent"""
    agent = MyCustomAgent()

    request_data = {
        "input": "测试输入",
        "user_id": "test_user"
    }

    events = []
    async for event in agent.process_request(request_data):
        events.append(event)

    assert len(events) > 0
    assert events[-1]["event_type"] == "complete"
```

#### 集成测试

```python
# tests/test_api_integration.py
import pytest
from fastapi.testclient import TestClient
from apis.main import app

client = TestClient(app)

def test_chat_endpoint():
    """测试聊天端点"""
    response = client.post(
        "/juben/chat",
        json={
            "input": "测试输入",
            "user_id": "test_user"
        }
    )
    assert response.status_code == 200
```

### 调试技巧

#### 1. 启用调试日志

```bash
# 设置日志级别
export LOG_LEVEL=DEBUG

# 或在 .env 中设置
LOG_LEVEL=DEBUG
```

#### 2. 查看 SSE 事件

使用 curl 查看 SSE 事件流：

```bash
curl -N http://localhost:8000/juben/chat \
  -H "Content-Type: application/json" \
  -d '{"input": "测试", "user_id": "test"}'
```

#### 3. Redis 调试

```bash
# 连接到 Redis
redis-cli

# 查看所有键
KEYS *

# 查看特定键
GET session:user123:session456

# 查看列表内容
LRANGE session:user123:session456 0 -1
```

#### 4. PostgreSQL 调试

```bash
# 连接到数据库
psql -U user -d juben

# 查询表
SELECT * FROM conversations LIMIT 10;

# 查询 Notes
SELECT * FROM notes WHERE user_id = 'user123';
```

### 性能优化

#### 1. LLM 调用优化

- 使用连接池复用连接
- 批量处理请求
- 启用响应缓存

#### 2. 数据库查询优化

- 使用索引
- 避免 N+1 查询
- 使用查询结果缓存

#### 3. 前端性能优化

- 虚拟滚动 (react-virtual)
- 懒加载组件
- 优化渲染

### 部署指南

#### 本地开发部署

```bash
# 一键启动（自动拉起外部依赖 + 前后端）
bash scripts/start_dev.sh

# 或手动启动
venv/bin/python main.py          # 后端 http://localhost:8000
cd frontend && pnpm dev          # 前端 http://localhost:5173
```

#### 生产环境配置

```env
# .env.production
DEBUG=false
LOG_LEVEL=INFO

# 使用生产数据库
DATABASE_URL=postgresql+asyncpg://user:password@prod-db:5432/juben
REDIS_URL=redis://prod-redis:6379/0

# 配置 CORS
ALLOWED_ORIGINS=https://your-domain.com
```

---

## 联系与支持

- **作者**: 宫灵瑞
- **项目地址**: https://github.com/GongLingRui/juben
- **文档地址**: https://github.com/GongLingRui/juben/wiki
- **问题反馈**: https://github.com/GongLingRui/juben/issues

## 许可证

MIT License

---

**最后更新**: 2026年
