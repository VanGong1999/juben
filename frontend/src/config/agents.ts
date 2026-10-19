/**
 * Agents 配置文件
 * 包含所有可用的智能体及其详细信息
 */

export type NavTier = 'core' | 'extended' | 'utility';

export type ProductLine = 'short_drama' | 'general' | 'shared';

export type PipelineStage =
  | '策划'
  | '故事'
  | '情节点'
  | '人物'
  | '创作'
  | '评估'
  | '工具';

export interface AgentConfig {
  id: string;
  name: string;
  displayName: string;
  description: string;
  category: AgentCategory;
  icon: string;
  model: string;
  apiEndpoint: string;
  features: string[];
  capabilities: string[];
  inputExample: string;
  outputExample: string;
  status: 'active' | 'beta' | 'experimental';
  /** 导航暴露层级：工作室默认只露 core */
  navTier?: NavTier;
  /** 创作流水线阶段（杂志目录分组） */
  pipelineStage?: PipelineStage;
  /** 产品线：短剧 / 通用剧本 / 共享 */
  productLine?: ProductLine;
}

export type AgentCategory =
  | 'planning'        // 策划类
  | 'creation'        // 创作类
  | 'evaluation'      // 评估类
  | 'analysis'        // 分析类
  | 'workflow'        // 工作流
  | 'utility'         // 工具类
  | 'character'       // 人物类
  | 'story'           // 故事类
  | 'orchestration';  // 编排总控

/** 工作室默认展示的核心专家 */
export const CORE_AGENT_IDS = [
  'auto',
  'short_drama_planner',
  'story_five_elements',
  'major_plot_points',
  'character_profile_generator',
  'short_drama_creator',
  'episode_batch_creator',
  'video_prompt_batch',
  'short_drama_evaluation',
] as const;

const UTILITY_AGENT_IDS = new Set([
  'websearch',
  'knowledge',
  'file_reference',
  'document_generator',
  'output_formatter',
  'series_info',
  'series_name_extractor',
  'text_splitter',
  'text_truncator',
]);

const STAGE_BY_CATEGORY: Partial<Record<AgentCategory, PipelineStage>> = {
  planning: '策划',
  story: '故事',
  analysis: '情节点',
  workflow: '情节点',
  character: '人物',
  creation: '创作',
  evaluation: '评估',
  utility: '工具',
};

const STAGE_BY_ID: Partial<Record<string, PipelineStage>> = {
  short_drama_planner: '策划',
  story_five_elements: '故事',
  story_summary_generator: '故事',
  mind_map: '故事',
  major_plot_points: '情节点',
  detailed_plot_points: '情节点',
  plot_points_analyzer: '情节点',
  plot_points_workflow: '情节点',
  character_profile_generator: '人物',
  character_relationship_analyzer: '人物',
  short_drama_creator: '创作',
  episode_batch_creator: '创作',
  episode_writer: '创作',
  video_prompt_writer: '创作',
  video_prompt_batch: '创作',
  drama_workflow: '创作',
  short_drama_evaluation: '评估',
  script_evaluation: '评估',
  story_evaluation: '评估',
  story_outline_evaluation: '评估',
  novel_screening_evaluation: '评估',
  ip_evaluation: '评估',
};

export function resolveNavTier(agent: Pick<AgentConfig, 'id' | 'category' | 'navTier'>): NavTier {
  if (agent.navTier) return agent.navTier;
  if ((CORE_AGENT_IDS as readonly string[]).includes(agent.id)) return 'core';
  if (UTILITY_AGENT_IDS.has(agent.id) || agent.category === 'utility') return 'utility';
  return 'extended';
}

const SHORT_DRAMA_AGENT_IDS = new Set([
  'short_drama_planner',
  'short_drama_creator',
  'episode_batch_creator',
  'episode_writer',
  'video_prompt_writer',
  'video_prompt_batch',
  'short_drama_evaluation',
]);

const GENERAL_AGENT_IDS = new Set([
  'drama_analysis',
  'script_evaluation',
  'story_evaluation',
  'story_outline_evaluation',
  'ip_evaluation',
  'novel_screening_evaluation',
  'character_profile_generator',
  'character_relationship_analyzer',
  'plot_points_analyzer',
  'plot_points_workflow',
  'major_plot_points',
  'detailed_plot_points',
  'story_five_elements',
  'story_type_analyzer',
  'series_analysis',
  'drama_workflow',
  'result_analyzer_evaluation',
  'result_integrator',
  'score_analyzer',
  'text_processor_evaluation',
]);

/** 解析产品线：后端目录优先提供 productLine，本地回退按 id 归类，其余为 shared */
export function resolveProductLine(
  agent: Pick<AgentConfig, 'id' | 'productLine'>
): ProductLine {
  if (agent.productLine) return agent.productLine;
  if (SHORT_DRAMA_AGENT_IDS.has(agent.id)) return 'short_drama';
  if (GENERAL_AGENT_IDS.has(agent.id)) return 'general';
  return 'shared';
}

/** 按产品线筛选（精确匹配） */
export function getAgentsByProductLine(
  line: ProductLine,
  agents: AgentConfig[] = AGENTS_CONFIG
): AgentConfig[] {
  return agents.filter((a) => resolveProductLine(a) === line);
}

/** 某模式下可见的产品线集合（如 general 模式 = general + shared） */
export function getProductLinesForMode(mode: 'short_drama' | 'general'): ProductLine[] {
  return mode === 'general' ? ['general', 'shared'] : ['short_drama', 'shared'];
}

export function resolvePipelineStage(
  agent: Pick<AgentConfig, 'id' | 'category' | 'pipelineStage'>
): PipelineStage {
  if (agent.pipelineStage) return agent.pipelineStage;
  return STAGE_BY_ID[agent.id] || STAGE_BY_CATEGORY[agent.category] || '工具';
}

export const PIPELINE_STAGE_ORDER: PipelineStage[] = [
  '策划',
  '故事',
  '情节点',
  '人物',
  '创作',
  '评估',
  '工具',
];

/**
 * 所有可用的 Agents 配置
 */
export const AGENTS_CONFIG: AgentConfig[] = [
  // ==================== 自动编排 ====================
  {
    id: 'auto',
    name: 'JubenConductor',
    displayName: '自动编排',
    description: '不用选专家，直接说需求，AI 自动协调各专业助手帮你完成',
    category: 'orchestration',
    icon: '🧭',
    model: 'deepseek-flash',
    apiEndpoint: '/juben/chat',
    features: ['auto route', 'subagent', 'handoff', 'compose'],
    capabilities: [
      '无需先选专家即可对话',
      '按需调用子专家并合成回复',
      '会话级交接给专业 Agent',
      '并行组合多个专家',
    ],
    inputExample: '帮我策划一部都市逆袭短剧，并评估商业化潜力',
    outputExample: '（自动调用策划/评估专家后汇总）',
    status: 'active',
    navTier: 'core',
  },
  {
    id: 'juben_conductor',
    name: 'JubenConductor',
    displayName: '自动编排助手',
    description: '智能调度多个创作专家，按你的需求自动分工、协作、汇总结果',
    category: 'orchestration',
    icon: '🧭',
    model: 'deepseek-flash',
    apiEndpoint: '/juben/chat',
    features: ['auto route', 'subagent', 'handoff', 'compose'],
    capabilities: ['总控路由', 'spawn 子专家', 'handoff', 'compose'],
    inputExample: '我想做一个重生复仇短剧，从题材到人物一起想',
    outputExample: '（编排多个专家后汇总）',
    status: 'active',
    navTier: 'extended',
  },
  {
    id: 'memory_curator',
    name: 'MemoryCuratorAgent',
    displayName: '记忆策展人',
    description: '自动整理作品的创作记忆，沉淀成功经验、遗忘冗余信息，让 AI 越写越懂你的故事',
    category: 'utility',
    icon: '🧠',
    model: 'deepseek-flash',
    apiEndpoint: '/juben/chat',
    features: ['recall', 'reflection', 'skill extract', 'dreaming', 'governance'],
    capabilities: [
      '检索情节/语义记忆（不全量进上下文）',
      '对成败做 reflection',
      '把成功路径晋升为 procedural skill',
      '离线 dreaming 整理 MEMORY',
      '编辑删除记忆并写审计',
    ],
    inputExample: '整理这部短剧的记忆，并把卡点写作成功路径晋升为技能',
    outputExample: '已 dreaming：归档过期悬念，晋升技能「路径:cliffhanger」',
    status: 'active',
    navTier: 'extended',
    pipelineStage: '工具',
  },

  // ==================== 策划类 ====================
  {
    id: 'short_drama_planner',
    name: 'ShortDramaPlannerAgent',
    displayName: '短剧策划助手',
    description: '专业的短剧策划和创作建议助手，提供剧本结构、情节设计、人物塑造等全方位策划支持',
    category: 'planning',
    icon: '📋',
    model: 'deepseek-flash',
    apiEndpoint: '/juben/chat',
    features: [
      '剧本策划',
      '情节设计建议',
      '结构优化',
      '创作指导'
    ],
    capabilities: [
      '分析剧本需求并提供专业策划建议',
      '设计合理的情节结构和故事节奏',
      '提供人物塑造和对话写作指导',
      '优化剧本的商业价值和观赏性'
    ],
    inputExample: '帮我策划一个关于都市爱情的短剧剧本',
    outputExample: '根据您的需求，我为您策划了以下短剧方案...',
    status: 'active'
  },

  // ==================== 创作类 ====================
  {
    id: 'short_drama_creator',
    name: 'ShortDramaCreatorAgent',
    displayName: '短剧创作助手',
    description: '专业短剧内容创作助手，帮助生成高质量剧本内容',
    category: 'creation',
    icon: '✍️',
    model: 'deepseek-flash',
    apiEndpoint: '/juben/chat',
    features: [
      '剧本创作',
      '场景描写',
      '对话生成',
      '情节展开'
    ],
    capabilities: [
      '创作完整的短剧剧本',
      '生成生动的场景描写',
      '编写符合人物性格的对话',
      '展开引人入胜的故事情节'
    ],
    inputExample: '创作一个悬疑短剧的第一场戏',
    outputExample: '【第一场】\n场景：废弃工厂 - 夜',
    status: 'active'
  },
  {
    id: 'episode_batch_creator',
    name: 'EpisodeBatchCreatorAgent',
    displayName: '分集连载编排',
    description: '前置完成后先写连贯性草稿，再并行派出单集编剧（一集一个），保证前后连贯、不重复',
    category: 'creation',
    icon: '🎞️',
    model: 'deepseek-flash',
    apiEndpoint: '/juben/chat',
    features: ['连贯性草稿', '并行单集 subagents', '结构化手递', '分集落盘'],
    capabilities: [
      '读取策划/人物/大纲等前置产物',
      '生成跨集连贯性草稿',
      '并行调用单集编剧，一集一个 Agent',
      '按用户要求调整语气与禁忌',
    ],
    inputExample: '前置已完成，请并行写第1–5集，偏爽感打脸',
    outputExample: '连贯性草稿就绪 → 5 个单集编剧并行完成',
    status: 'active',
    navTier: 'core',
  },
  {
    id: 'episode_writer',
    name: 'EpisodeWriterAgent',
    displayName: '单集编剧',
    description: '分集连载子专家：根据连贯性草稿只写指定一集',
    category: 'creation',
    icon: '📝',
    model: 'deepseek-flash',
    apiEndpoint: '/juben/chat',
    features: ['单集写作', '连贯性约束', '禁止重复'],
    capabilities: ['按槽位节拍撰写单集', '遵守 carry_in/out', '落实用户要求'],
    inputExample: '（由分集连载编排自动调用）',
    outputExample: '# 第3集 · 标题\n## 场景1 …',
    status: 'active',
    navTier: 'extended',
  },
  {
    id: 'video_prompt_writer',
    name: 'VideoPromptWriterAgent',
    displayName: '单集视频提示词',
    description: '把单集剧本转为豆包/即梦 Seedance 可复制视频生成提示词',
    category: 'creation',
    icon: '🎥',
    model: 'deepseek-flash',
    apiEndpoint: '/juben/chat',
    features: ['剧本转提示词', 'Seedance', '分镜可复制', '竖屏'],
    capabilities: [
      '拆分镜写景别运镜',
      '输出台词/音效符号',
      '锁定视觉锚点并落盘',
    ],
    inputExample: '把第1集剧本转成豆包视频提示词',
    outputExample: '# 第1集 · Seedance\n### SHOT-01\n> 可复制提示词…',
    status: 'active',
    navTier: 'core',
  },
  {
    id: 'video_prompt_batch',
    name: 'VideoPromptBatchAgent',
    displayName: '视频提示词批量编排',
    description: '先写视觉连贯性草稿，再并行把多集剧本转为豆包视频提示词并落盘',
    category: 'creation',
    icon: '🎬',
    model: 'deepseek-flash',
    apiEndpoint: '/juben/chat',
    features: ['视觉连贯性', '并行转换', '批量落盘', 'Seedance'],
    capabilities: [
      '跨集锁定人物与场景',
      '一集一个子专家并行',
      '保存到 video_prompts/',
    ],
    inputExample: '把第1–5集全部转成豆包视频提示词',
    outputExample: '视觉草稿就绪 → 5 集提示词已写入',
    status: 'active',
    navTier: 'core',
  },

  // ==================== 评估类 ====================
  {
    id: 'short_drama_evaluation',
    name: 'ShortDramaEvaluationAgent',
    displayName: '短剧评估助手',
    description: '专业的短剧质量评估助手，从多维度评估剧本质量并提供改进建议',
    category: 'evaluation',
    icon: '📊',
    model: 'deepseek-v4-pro',
    apiEndpoint: '/juben/evaluation/chat',
    features: [
      '质量评估',
      '多维度打分',
      '改进建议',
      '市场分析'
    ],
    capabilities: [
      '从情节、人物、对话等维度评估剧本',
      '提供详细的评分和改进建议',
      '分析剧本的市场潜力',
      '对比同类优秀作品'
    ],
    inputExample: '请评估我的短剧剧本质量',
    outputExample: '【评估报告】\n综合评分：85/100',
    status: 'active'
  },

  {
    id: 'script_evaluation',
    name: 'ScriptEvaluationAgent',
    displayName: '剧本评估专家',
    description: '深度剧本分析评估，提供专业的质量诊断和优化方案',
    category: 'evaluation',
    icon: '🎯',
    model: 'deepseek-v4-pro',
    apiEndpoint: '/juben/script/evaluation',
    features: [
      '剧本诊断',
      '质量评分',
      '问题定位',
      '优化方案'
    ],
    capabilities: [
      '深度分析剧本结构和逻辑',
      '识别潜在问题和薄弱环节',
      '提供具体的优化方案',
      '对比行业标准'
    ],
    inputExample: '帮我诊断这个剧本的问题',
    outputExample: '【诊断结果】\n发现3个主要问题...',
    status: 'active'
  },

  {
    id: 'ip_evaluation',
    name: 'IPEvaluationAgent',
    displayName: 'IP价值评估',
    description: '评估IP的商业价值和开发潜力',
    category: 'evaluation',
    icon: '💎',
    model: 'deepseek-v4-pro',
    apiEndpoint: '/juben/ip/evaluation',
    features: [
      'IP价值评估',
      '市场潜力分析',
      '商业化建议',
      '竞品对比'
    ],
    capabilities: [
      '评估IP的商业价值',
      '分析市场潜力和受众定位',
      '提供IP开发建议',
      '对比同类IP竞品'
    ],
    inputExample: '评估这个故事IP的开发价值',
    outputExample: '【IP评估报告】\n综合评级：A级',
    status: 'beta'
  },

  // ==================== 分析类 ====================
  {
    id: 'story_five_elements',
    name: 'StoryFiveElementsAgent',
    displayName: '故事五元素分析',
    description: '分析故事的核心五元素：人物、情节、环境、主题、风格',
    category: 'analysis',
    icon: '🔍',
    model: 'deepseek-flash',
    apiEndpoint: '/juben/story-analysis/analyze',
    features: [
      '五元素分析',
      '结构梳理',
      '主题提炼',
      '风格识别'
    ],
    capabilities: [
      '深度分析故事五要素',
      '梳理故事结构和脉络',
      '提炼核心主题思想',
      '识别故事风格特征'
    ],
    inputExample: '分析这个故事的核心元素',
    outputExample: '【五元素分析】\n一、人物分析...',
    status: 'active'
  },

  {
    id: 'series_analysis',
    name: 'SeriesAnalysisAgent',
    displayName: '已播剧集分析',
    description: '分析已播剧集的数据和表现，提取成功经验',
    category: 'analysis',
    icon: '📺',
    model: 'deepseek-flash',
    apiEndpoint: '/juben/series-analysis/analyze',
    features: [
      '剧集数据分析',
      '成功要素提取',
      '趋势总结',
      '经验归纳'
    ],
    capabilities: [
      '分析已播剧集的各项数据',
      '提取成功剧集的关键要素',
      '总结行业趋势和规律',
      '归纳可复制的经验'
    ],
    inputExample: '分析《某某短剧》的成功要素',
    outputExample: '【剧集分析报告】\n一、数据概览...',
    status: 'active'
  },

  {
    id: 'drama_analysis',
    name: 'DramaAnalysisAgent',
    displayName: '剧本深度分析',
    description: '对剧本进行深度专业分析，挖掘潜在价值',
    category: 'analysis',
    icon: '🔬',
    model: 'deepseek-v4-pro',
    apiEndpoint: '/juben/drama/analysis',
    features: [
      '剧本结构分析',
      '人物关系梳理',
      '情节节奏分析',
      '价值挖掘'
    ],
    capabilities: [
      '深度解析剧本结构',
      '梳理复杂人物关系',
      '分析情节节奏变化',
      '挖掘潜在商业价值'
    ],
    inputExample: '深度分析这个剧本',
    outputExample: '【深度分析】\n一、结构分析...',
    status: 'active'
  },

  {
    id: 'story_type_analyzer',
    name: 'StoryTypeAnalyzerAgent',
    displayName: '故事类型分析',
    description: '识别和分析故事类型，提供类型化创作建议',
    category: 'analysis',
    icon: '📚',
    model: 'deepseek-flash',
    apiEndpoint: '/juben/story-type/analyze',
    features: [
      '类型识别',
      '类型特征分析',
      '创作规范建议',
      '市场定位'
    ],
    capabilities: [
      '准确识别故事类型',
      '分析类型的核心特征',
      '提供类型化创作规范',
      '定位目标市场'
    ],
    inputExample: '分析这个故事的类型',
    outputExample: '【类型分析】\n类型：都市爱情 + 悬疑',
    status: 'active'
  },

  // ==================== 工作流类 ====================
  {
    id: 'plot_points_workflow',
    name: 'PlotPointsWorkflowAgent',
    displayName: '情节点工作流',
    description: '完整的大情节点与详细情节点生成工作流',
    category: 'workflow',
    icon: '🔄',
    model: 'deepseek-flash',
    apiEndpoint: '/juben/plot-points-workflow/execute',
    features: [
      '大情节点生成',
      '详细情节点展开',
      '结构化输出',
      '可视化展示'
    ],
    capabilities: [
      '生成完整的大情节点框架',
      '展开详细的情节点内容',
      '提供结构化输出格式',
      '支持可视化展示'
    ],
    inputExample: '生成这个故事的完整情节点',
    outputExample: '【情节点工作流】\n一、大情节点...',
    status: 'active'
  },

  {
    id: 'drama_workflow',
    name: 'DramaWorkflowAgent',
    displayName: '剧本创作工作流',
    description: '端到端的剧本创作工作流，从创意到成品',
    category: 'workflow',
    icon: '🎬',
    model: 'deepseek-flash',
    apiEndpoint: '/juben/drama-workflow/execute',
    features: [
      '创意开发',
      '大纲生成',
      '剧本创作',
      '质量检验'
    ],
    capabilities: [
      '从创意开发到剧本成品的完整流程',
      '多阶段质量控制',
      '支持迭代优化',
      '输出标准化剧本'
    ],
    inputExample: '执行完整的剧本创作工作流',
    outputExample: '【工作流执行】\n阶段1：创意开发...',
    status: 'beta'
  },

  // ==================== 人物类 ====================
  {
    id: 'character_profile_generator',
    name: 'CharacterProfileGeneratorAgent',
    displayName: '人物小传生成',
    description: '为故事中的主要人物生成详细的人物小传',
    category: 'character',
    icon: '👤',
    model: 'deepseek-flash',
    apiEndpoint: '/juben/character/profile',
    features: [
      '人物识别',
      '小传生成',
      '性格分析',
      '背景构建'
    ],
    capabilities: [
      '识别故事中的主要人物',
      '生成300-500字的详细小传',
      '分析人物性格特征',
      '构建完整的背景故事'
    ],
    inputExample: '为这个故事生成人物小传',
    outputExample: '【人物小传】\n1. 张三（主角）...',
    status: 'active'
  },

  {
    id: 'character_relationship_analyzer',
    name: 'CharacterRelationshipAnalyzerAgent',
    displayName: '人物关系分析',
    description: '分析故事中人物之间的复杂关系网络',
    category: 'character',
    icon: '👥',
    model: 'deepseek-flash',
    apiEndpoint: '/juben/character/relationship',
    features: [
      '关系识别',
      '关系类型分析',
      '关系网络构建',
      '关系演变追踪'
    ],
    capabilities: [
      '识别各种类型的人物关系',
      '分析关系的性质和强度',
      '构建完整的关系网络',
      '追踪关系的演变过程'
    ],
    inputExample: '分析这个故事中的人物关系',
    outputExample: '【人物关系分析】\n1. 张三 ↔ 李四：恋人关系...',
    status: 'active'
  },

  // ==================== 故事类 ====================
  {
    id: 'story_summary_generator',
    name: 'StorySummaryGeneratorAgent',
    displayName: '故事大纲生成',
    description: '为长篇故事生成精炼的故事大纲',
    category: 'story',
    icon: '📝',
    model: 'deepseek-flash',
    apiEndpoint: '/juben/story/summary',
    features: [
      '内容提取',
      '要点总结',
      '结构梳理',
      '精炼表达'
    ],
    capabilities: [
      '从长文本中提取核心内容',
      '总结故事要点和关键情节',
      '梳理故事结构脉络',
      '生成精炼的故事大纲'
    ],
    inputExample: '为这个故事生成大纲',
    outputExample: '【故事大纲】\n一、故事梗概...',
    status: 'active'
  },

  {
    id: 'detailed_plot_points',
    name: 'DetailedPlotPointsAgent',
    displayName: '详细情节点',
    description: '展开详细的情节点内容，丰富故事细节',
    category: 'story',
    icon: '📍',
    model: 'deepseek-flash',
    apiEndpoint: '/juben/plot-points/detailed',
    features: [
      '情节点展开',
      '细节补充',
      '场景描写',
      '情节衔接'
    ],
    capabilities: [
      '展开简略的情节点',
      '补充丰富的细节内容',
      '添加生动的场景描写',
      '确保情节衔接自然'
    ],
    inputExample: '展开这个情节点',
    outputExample: '【详细情节点】\n情节展开如下...',
    status: 'active'
  },

  {
    id: 'plot_points_analyzer',
    name: 'PlotPointsAnalyzerAgent',
    displayName: '情节点分析',
    description: '分析和优化故事情节点的设计',
    category: 'story',
    icon: '📌',
    model: 'deepseek-v4-pro',
    apiEndpoint: '/juben/plot-points/analyze',
    features: [
      '情节点识别',
      '结构分析',
      '节奏评估',
      '优化建议'
    ],
    capabilities: [
      '识别故事中的关键情节点',
      '分析情节点结构分布',
      '评估情节节奏',
      '提供优化建议'
    ],
    inputExample: '分析这个故事情节点的设计',
    outputExample: '【情节点分析】\n共识别15个关键情节点...',
    status: 'active'
  },

  {
    id: 'mind_map',
    name: 'MindMapAgent',
    displayName: '思维导图',
    description: '生成故事结构可视化思维导图',
    category: 'story',
    icon: '🧠',
    model: 'deepseek-flash',
    apiEndpoint: '/juben/mind-map/generate',
    features: [
      '结构提取',
      '导图生成',
      '可视化展示',
      '编辑导出'
    ],
    capabilities: [
      '提取故事结构层次',
      '生成可视化思维导图',
      '支持在线编辑',
      '可导出多种格式'
    ],
    inputExample: '为这个故事生成思维导图',
    outputExample: '【思维导图】\n已生成，点击查看',
    status: 'active'
  },

  {
    id: 'major_plot_points',
    name: 'MajorPlotPointsAgent',
    displayName: '大情节点分析',
    description: '分析并提取故事的主要情节点',
    category: 'story',
    icon: '🎬',
    model: 'deepseek-flash',
    apiEndpoint: '/juben/major-plot-points/chat',
    features: [
      '大情节点提取',
      '情节点描述',
      '时间线构建',
      '结构优化'
    ],
    capabilities: [
      '识别故事的核心情节点',
      '提取关键转折点',
      '构建故事时间线',
      '优化情节点结构'
    ],
    inputExample: '分析这个故事的大情节点',
    outputExample: '【大情节点】\n1. 开端：主角登场...',
    status: 'active'
  },

  // 原「工具类专家」已迁至 config/tools.ts（Agent Tools，非专家）

  // ==================== 更多评估类 ====================
  {
    id: 'story_evaluation',
    name: 'StoryEvaluationAgent',
    displayName: '故事质量评估',
    description: '评估故事的整体质量和吸引力',
    category: 'evaluation',
    icon: '⭐',
    model: 'deepseek-v4-pro',
    apiEndpoint: '/juben/story/evaluation',
    features: [
      '质量打分',
      '吸引力分析',
      '改进建议',
      '对比评估'
    ],
    capabilities: [
      '对故事质量进行多维度打分',
      '分析故事吸引力要素',
      '提供具体改进建议',
      '与优秀作品对比评估'
    ],
    inputExample: '评估这个故事的质量',
    outputExample: '【质量评估】\n综合评分：88/100...',
    status: 'active'
  },

  {
    id: 'story_outline_evaluation',
    name: 'StoryOutlineEvaluationAgent',
    displayName: '大纲评估',
    description: '评估故事大纲的完整性和可行性',
    category: 'evaluation',
    icon: '📋',
    model: 'deepseek-v4-pro',
    apiEndpoint: '/juben/outline/evaluation',
    features: [
      '完整性检查',
      '可行性评估',
      '结构调整',
      '补充建议'
    ],
    capabilities: [
      '检查大纲结构完整性',
      '评估创作可行性',
      '提供结构调整建议',
      '指出需要补充的部分'
    ],
    inputExample: '评估这个故事大纲',
    outputExample: '【大纲评估】\n结构完整性：85%...',
    status: 'active'
  },

  {
    id: 'novel_screening_evaluation',
    name: 'NovelScreeningEvaluationAgent',
    displayName: '小说筛选评估',
    description: '评估小说是否适合改编为短剧',
    category: 'evaluation',
    icon: '📖',
    model: 'deepseek-v4-pro',
    apiEndpoint: '/juben/novel/screening',
    features: [
      '改编可行性',
      'IP价值评估',
      '改编建议',
      '版权分析'
    ],
    capabilities: [
      '评估小说改编短剧的可行性',
      '分析IP的商业价值',
      '提供专业改编建议',
      '分析版权相关事项'
    ],
    inputExample: '评估这本小说的改编价值',
    outputExample: '【改编评估】\n改编可行性：高...',
    status: 'active'
  },

  // series_info / text_* 等见 config/tools.ts

  // ==================== 结果处理类 ====================
  {
    id: 'result_analyzer_evaluation',
    name: 'ResultAnalyzerEvaluationAgent',
    displayName: '结果分析评估',
    description: '分析评估结果，提供洞察',
    category: 'evaluation',
    icon: '📊',
    model: 'deepseek-v4-pro',
    apiEndpoint: '/juben/result/analyze',
    features: [
      '结果分析',
      '数据洞察',
      '趋势发现',
      '建议生成'
    ],
    capabilities: [
      '深度分析评估结果',
      '提取数据洞察',
      '发现隐藏趋势',
      '生成改进建议'
    ],
    inputExample: '分析这些评估结果',
    outputExample: '【分析报告】\n关键洞察：...',
    status: 'active'
  },

  {
    id: 'result_integrator',
    name: 'ResultIntegratorAgent',
    displayName: '结果集成器',
    description: '集成多个Agent的结果',
    category: 'workflow',
    icon: '🔗',
    model: 'deepseek-flash',
    apiEndpoint: '/juben/result/integrate',
    features: [
      '结果聚合',
      '格式统一',
      '去重合并',
      '优先级排序'
    ],
    capabilities: [
      '聚合多个Agent输出',
      '统一结果格式',
      '去重和合并内容',
      '按优先级排序'
    ],
    inputExample: '集成多个Agent的结果',
    outputExample: '【集成结果】\n已整合5个来源...',
    status: 'active'
  },

  {
    id: 'score_analyzer',
    name: 'ScoreAnalyzerAgent',
    displayName: '评分分析器',
    description: '分析评分数据，提供解读',
    category: 'evaluation',
    icon: '📈',
    model: 'deepseek-v4-pro',
    apiEndpoint: '/juben/score/analyze',
    features: [
      '评分统计',
      '分布分析',
      '趋势解读',
      '对比分析'
    ],
    capabilities: [
      '统计分析评分数据',
      '分析评分分布',
      '解读评分趋势',
      '对比历史数据'
    ],
    inputExample: '分析这些评分数据',
    outputExample: '【评分分析】\n平均分：85...',
    status: 'active'
  },

  {
    id: 'text_processor_evaluation',
    name: 'TextProcessorEvaluationAgent',
    displayName: '文本处理评估',
    description: '评估文本处理的质量和效果',
    category: 'evaluation',
    icon: '📝',
    model: 'deepseek-flash',
    apiEndpoint: '/juben/chat',
    features: [
      '质量评估',
      '效果分析',
      '问题识别',
      '改进建议'
    ],
    capabilities: [
      '评估文本处理质量',
      '分析处理效果',
      '识别潜在问题',
      '提供改进建议'
    ],
    inputExample: '评估这段文本处理的效果',
    outputExample: '【处理评估】\n质量得分：90...',
    status: 'active'
  },
];

/**
 * 按分类获取 Agents
 */
export function getAgentsByCategory(category: AgentCategory): AgentConfig[] {
  return AGENTS_CONFIG.filter(agent => agent.category === category);
}

/**
 * 根据 ID 获取 Agent
 */
export function getAgentById(id: string): AgentConfig | undefined {
  return AGENTS_CONFIG.find(agent => agent.id === id);
}

/**
 * 获取激活的 Agents
 */
export function getActiveAgents(): AgentConfig[] {
  return AGENTS_CONFIG.filter(agent => agent.status === 'active');
}

/** 按导航层级筛选 */
export function getAgentsByTier(tier: NavTier, agents: AgentConfig[] = AGENTS_CONFIG): AgentConfig[] {
  return agents.filter((a) => resolveNavTier(a) === tier);
}

/** 工作室默认核心专家（保持 CORE 顺序） */
export function getCoreAgents(agents: AgentConfig[] = AGENTS_CONFIG): AgentConfig[] {
  return CORE_AGENT_IDS.map((id) => agents.find((a) => a.id === id) || getAgentById(id)).filter(
    Boolean
  ) as AgentConfig[];
}

/** 按流水线阶段分组（杂志目录） */
export function groupAgentsByPipelineStage(
  agents: AgentConfig[] = AGENTS_CONFIG,
  options?: { includeUtility?: boolean }
): { stage: PipelineStage; agents: AgentConfig[] }[] {
  const includeUtility = options?.includeUtility ?? false;
  const map = new Map<PipelineStage, AgentConfig[]>();
  for (const stage of PIPELINE_STAGE_ORDER) map.set(stage, []);
  for (const agent of agents) {
    const tier = resolveNavTier(agent);
    if (!includeUtility && tier === 'utility') continue;
    const stage = resolvePipelineStage(agent);
    map.get(stage)!.push(agent);
  }
  return PIPELINE_STAGE_ORDER.map((stage) => ({ stage, agents: map.get(stage) || [] })).filter(
    (g) => g.agents.length > 0
  );
}

/**
 * 获取 Agent 分类列表
 */
export function getAgentCategories(): { category: AgentCategory; name: string; icon: string }[] {
  return [
    { category: 'planning', name: '策划类', icon: '📋' },
    { category: 'creation', name: '创作类', icon: '✍️' },
    { category: 'evaluation', name: '评估类', icon: '📊' },
    { category: 'analysis', name: '分析类', icon: '🔍' },
    { category: 'workflow', name: '工作流', icon: '🔄' },
    { category: 'character', name: '人物类', icon: '👤' },
    { category: 'story', name: '故事类', icon: '📖' },
    // utility 已迁至 Agent Tools（config/tools.ts）
  ];
}

/**
 * 搜索 Agents
 */
export function searchAgents(query: string): AgentConfig[] {
  const lowerQuery = query.toLowerCase();
  return AGENTS_CONFIG.filter(
    (agent) =>
      resolveNavTier(agent) !== 'utility' &&
      (agent.name.toLowerCase().includes(lowerQuery) ||
        agent.displayName.toLowerCase().includes(lowerQuery) ||
        agent.description.toLowerCase().includes(lowerQuery) ||
        agent.features.some((f) => f.toLowerCase().includes(lowerQuery)))
  );
}
