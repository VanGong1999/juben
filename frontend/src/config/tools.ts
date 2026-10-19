/**
 * Agent 工具目录 — 供专家调用，不是独立专家
 *
 * Prebuilt: harness 自带（读/写/编辑/列表/搜索/日期）
 * External: 设计期注册（原「工具类专家」能力）
 */

export type ToolCategory = 'prebuilt' | 'external';

export interface ToolDefinitionUI {
  name: string;
  label: string;
  description: string;
  category: ToolCategory;
  icon: string;
  /** JSON Schema 摘要，供 UI 展示参数 */
  parameters: {
    type: 'object';
    properties: Record<string, { type: string; description?: string; default?: unknown; enum?: string[]; items?: Record<string, unknown> }>;
    required?: string[];
  };
  requiresSandbox?: boolean;
  dangerous?: boolean;
  /** 旧 utility agent id，便于迁移提示 */
  legacyAgentId?: string;
  tags?: string[];
}

/** Harness 预置工具 */
export const PREBUILT_TOOLS: ToolDefinitionUI[] = [
  {
    name: 'read',
    label: '读取文件',
    description: '读取项目里的文本文件（大纲、故事设定、分集剧本等）',
    category: 'prebuilt',
    icon: '📄',
    requiresSandbox: true,
    parameters: {
      type: 'object',
      properties: {
        path: { type: 'string', description: '相对路径' },
        offset: { type: 'integer', default: 0 },
        limit: { type: 'integer' },
      },
      required: ['path'],
    },
    tags: ['fs'],
  },
  {
    name: 'write',
    label: '写入文件',
    description: '写入或覆盖项目里的文本文件',
    category: 'prebuilt',
    icon: '✍️',
    requiresSandbox: true,
    dangerous: true,
    parameters: {
      type: 'object',
      properties: {
        path: { type: 'string' },
        content: { type: 'string' },
      },
      required: ['path', 'content'],
    },
    tags: ['fs'],
  },
  {
    name: 'edit',
    label: '编辑文件',
    description: '对项目里的已有文件做精确修改',
    category: 'prebuilt',
    icon: '✏️',
    requiresSandbox: true,
    dangerous: true,
    parameters: {
      type: 'object',
      properties: {
        path: { type: 'string' },
        old_string: { type: 'string' },
        new_string: { type: 'string' },
      },
      required: ['path', 'old_string', 'new_string'],
    },
    tags: ['fs'],
  },
  {
    name: 'ls',
    label: '列出目录',
    description: '列出项目目录里的内容',
    category: 'prebuilt',
    icon: '📁',
    requiresSandbox: true,
    parameters: {
      type: 'object',
      properties: { path: { type: 'string', default: '.' } },
    },
    tags: ['fs'],
  },
  {
    name: 'grep',
    label: '内容搜索',
    description: '在项目文件里按关键词搜索内容',
    category: 'prebuilt',
    icon: '🔍',
    requiresSandbox: true,
    parameters: {
      type: 'object',
      properties: {
        pattern: { type: 'string' },
        path: { type: 'string', default: '.' },
      },
      required: ['pattern'],
    },
    tags: ['fs'],
  },
  {
    name: 'find',
    label: '查找文件',
    description: '按名称查找项目里的文件',
    category: 'prebuilt',
    icon: '🗂️',
    requiresSandbox: true,
    parameters: {
      type: 'object',
      properties: {
        pattern: { type: 'string' },
        path: { type: 'string', default: '.' },
      },
      required: ['pattern'],
    },
    tags: ['fs'],
  },
  {
    name: 'date',
    label: '当前时间',
    description: '返回当前日期时间（UTC / 本地），供时效性约束',
    category: 'prebuilt',
    icon: '📅',
    parameters: {
      type: 'object',
      properties: {
        timezone: { type: 'string', description: '可选 IANA 时区', default: 'Asia/Shanghai' },
      },
    },
    tags: ['meta'],
  },
];

/** 外部工具 — 原「工具类专家」改为 Agent 可调用工具 */
export const EXTERNAL_TOOLS: ToolDefinitionUI[] = [
  {
    name: 'web_search',
    label: '网络搜索',
    description: '实时搜索网络信息，获取最新资料',
    category: 'external',
    icon: '🌐',
    dangerous: true,
    legacyAgentId: 'websearch',
    parameters: {
      type: 'object',
      properties: {
        query: { type: 'string', description: '搜索关键词' },
        top_k: { type: 'integer', default: 8 },
      },
      required: ['query'],
    },
  },
  {
    name: 'knowledge_query',
    label: '知识库向量检索',
    description: '在项目知识库中智能检索相关内容',
    category: 'external',
    icon: '📚',
    legacyAgentId: 'knowledge',
    parameters: {
      type: 'object',
      properties: {
        query: { type: 'string' },
        top_k: { type: 'integer', default: 5 },
      },
      required: ['query'],
    },
  },
  {
    name: 'wiki_read',
    label: '读取 Wiki 页',
    description: '读取知识库中的某个条目全文',
    category: 'prebuilt',
    icon: '📖',
    parameters: {
      type: 'object',
      properties: {
        path: { type: 'string', description: '如 craft/cliffhanger.md' },
      },
      required: ['path'],
    },
  },
  {
    name: 'wiki_search',
    label: '搜索 Wiki 目录',
    description: '在知识库目录中搜索相关条目',
    category: 'prebuilt',
    icon: '🔎',
    parameters: {
      type: 'object',
      properties: {
        query: { type: 'string' },
        limit: { type: 'integer', default: 8 },
      },
      required: ['query'],
    },
  },
  {
    name: 'raw_read',
    label: '读取原文',
    description: '读取知识库中的原始资料',
    category: 'prebuilt',
    icon: '📄',
    parameters: {
      type: 'object',
      properties: {
        path: { type: 'string', description: '相对 raw/ 路径' },
      },
      required: ['path'],
    },
  },
  {
    name: 'wiki_ingest',
    label: '入库 Wiki',
    description: '把新内容写入知识库并更新目录',
    category: 'external',
    icon: '⬇️',
    dangerous: true,
    parameters: {
      type: 'object',
      properties: {
        title: { type: 'string' },
        summary: { type: 'string' },
        wiki_body: { type: 'string' },
        raw_path: { type: 'string' },
        content: { type: 'string' },
        category: { type: 'string', default: 'sources' },
      },
      required: ['title', 'summary', 'wiki_body'],
    },
  },
  {
    name: 'file_reference',
    label: '文件引用解析',
    description: '读取并引用项目或外部文件的内容',
    category: 'external',
    icon: '📎',
    requiresSandbox: true,
    legacyAgentId: 'file_reference',
    parameters: {
      type: 'object',
      properties: {
        path: { type: 'string' },
        max_chars: { type: 'integer', default: 12000 },
      },
      required: ['path'],
    },
  },
  {
    name: 'generate_document',
    label: '文档生成器',
    description: '生成标准化剧本文档，可选保存到作品 exports',
    category: 'external',
    icon: '📃',
    dangerous: true,
    legacyAgentId: 'document_generator',
    parameters: {
      type: 'object',
      properties: {
        title: { type: 'string' },
        body: { type: 'string' },
        doc_type: { type: 'string', enum: ['script', 'outline', 'bible', 'report'] },
        save: { type: 'boolean', default: false },
      },
      required: ['title', 'body'],
    },
  },
  {
    name: 'format_output',
    label: '输出格式化',
    description: '格式化 AI 输出为 markdown / plain / script',
    category: 'external',
    icon: '✨',
    legacyAgentId: 'output_formatter',
    parameters: {
      type: 'object',
      properties: {
        text: { type: 'string' },
        style: { type: 'string', enum: ['markdown', 'plain', 'script'] },
      },
      required: ['text'],
    },
  },
  {
    name: 'extract_series_info',
    label: '剧集信息提取',
    description: '从文本中提取剧名、集数、类型等结构化信息',
    category: 'external',
    icon: '📺',
    legacyAgentId: 'series_info',
    parameters: {
      type: 'object',
      properties: { text: { type: 'string' } },
      required: ['text'],
    },
  },
  {
    name: 'extract_series_name',
    label: '剧名提取',
    description: '智能识别并提取短剧名称',
    category: 'external',
    icon: '🏷️',
    legacyAgentId: 'series_name_extractor',
    parameters: {
      type: 'object',
      properties: { text: { type: 'string' } },
      required: ['text'],
    },
  },
  {
    name: 'text_split',
    label: '文本分割',
    description: '智能分割长文本为合适段落',
    category: 'external',
    icon: '✂️',
    legacyAgentId: 'text_splitter',
    parameters: {
      type: 'object',
      properties: {
        text: { type: 'string' },
        chunk_size: { type: 'integer', default: 2000 },
        overlap: { type: 'integer', default: 100 },
      },
      required: ['text'],
    },
  },
  {
    name: 'text_truncate',
    label: '文本截断',
    description: '按要求截断文本并保持完整性',
    category: 'external',
    icon: '✂️',
    legacyAgentId: 'text_truncator',
    parameters: {
      type: 'object',
      properties: {
        text: { type: 'string' },
        max_length: { type: 'integer', default: 8000 },
      },
      required: ['text'],
    },
  },
  {
    name: 'memory_search',
    label: '记忆检索',
    description: '检索作品的设定与情节记忆，写作前避免前后矛盾',
    category: 'external',
    icon: '🧠',
    parameters: {
      type: 'object',
      properties: {
        drama_id: { type: 'string' },
        query: { type: 'string' },
        layer: { type: 'string', enum: ['all', 'episodic', 'semantic', 'rules'] },
      },
      required: ['query'],
    },
  },
  {
    name: 'memory_write_fact',
    label: '写入语义事实',
    description: '记录人物设定、悬念等关键事实，保持一致',
    category: 'external',
    icon: '📌',
    dangerous: true,
    parameters: {
      type: 'object',
      properties: {
        drama_id: { type: 'string' },
        entity_type: { type: 'string' },
        entity_id: { type: 'string' },
        predicate: { type: 'string' },
        value: { type: 'string' },
      },
      required: ['entity_type', 'entity_id', 'predicate', 'value'],
    },
  },
  {
    name: 'memory_read_slice',
    label: '局部读取记忆',
    description: '按需读取部分记忆，避免信息过载',
    category: 'external',
    icon: '📄',
    parameters: {
      type: 'object',
      properties: {
        drama_id: { type: 'string' },
        path: { type: 'string' },
        offset: { type: 'integer', default: 0 },
        length: { type: 'integer', default: 2000 },
      },
      required: ['path'],
    },
  },
  {
    name: 'memory_record_episode',
    label: '记录情节记忆',
    description: '记录一次创作任务的经过与结果',
    category: 'external',
    icon: '📝',
    parameters: {
      type: 'object',
      properties: {
        task_description: { type: 'string' },
        outcome: { type: 'string', enum: ['success', 'failure', 'partial', 'cancelled'] },
        approach: { type: 'string' },
        tags: { type: 'array', items: { type: 'string' } },
      },
      required: ['task_description'],
    },
  },
  {
    name: 'memory_reflect',
    label: '反思成败',
    description: '复盘一次创作成败，沉淀经验',
    category: 'external',
    icon: '🪞',
    parameters: {
      type: 'object',
      properties: {
        episode_id: { type: 'string' },
        kind: { type: 'string', enum: ['success', 'failure', 'partial'] },
        summary: { type: 'string' },
      },
    },
  },
  {
    name: 'memory_promote_skill',
    label: '晋升程序技能',
    description: '把反复成功的写法沉淀为可复用技巧',
    category: 'external',
    icon: '⚡',
    dangerous: true,
    parameters: {
      type: 'object',
      properties: {
        name: { type: 'string' },
        trigger: { type: 'string' },
        min_success: { type: 'integer', default: 3 },
      },
      required: ['name', 'trigger'],
    },
  },
  {
    name: 'memory_dream',
    label: '离线做梦整理',
    description: '离线整理记忆：归档、反思、压缩、沉淀技巧',
    category: 'external',
    icon: '🌙',
    dangerous: true,
    parameters: {
      type: 'object',
      properties: {
        drama_id: { type: 'string' },
        auto_promote: { type: 'boolean', default: true },
      },
    },
  },
  {
    name: 'memory_forget',
    label: '遗忘引擎',
    description: '自动归档过期信息、标记矛盾',
    category: 'external',
    icon: '🗑️',
    dangerous: true,
    parameters: {
      type: 'object',
      properties: { drama_id: { type: 'string' } },
    },
  },
  {
    name: 'memory_delete',
    label: '删除记忆',
    description: '删除或归档某条记忆',
    category: 'external',
    icon: '❌',
    dangerous: true,
    parameters: {
      type: 'object',
      properties: {
        layer: { type: 'string', enum: ['semantic', 'episodic', 'procedural'] },
        target_id: { type: 'string' },
      },
      required: ['layer', 'target_id'],
    },
  },
  {
    name: 'memory_write_resident',
    label: '写常驻记忆',
    description: '更新常驻记忆（你的偏好与作品规则）',
    category: 'external',
    icon: '✏️',
    dangerous: true,
    parameters: {
      type: 'object',
      properties: {
        target: { type: 'string', enum: ['user', 'drama'] },
        content: { type: 'string' },
      },
      required: ['content'],
    },
  },
];

export const ALL_TOOLS: ToolDefinitionUI[] = [...PREBUILT_TOOLS, ...EXTERNAL_TOOLS];

export function getToolByName(name: string): ToolDefinitionUI | undefined {
  return ALL_TOOLS.find((t) => t.name === name);
}

export function groupToolsByCategory(): { category: ToolCategory; label: string; tools: ToolDefinitionUI[] }[] {
  return [
    { category: 'prebuilt', label: '内置工具', tools: PREBUILT_TOOLS },
    { category: 'external', label: '外部工具', tools: EXTERNAL_TOOLS },
  ];
}
