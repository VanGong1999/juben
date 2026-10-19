/**
 * 内容类型渲染组件
 * 根据 StreamContentType 渲染不同样式的内容块
 *
 * 功能:
 * - 根据 content_type 显示不同的图标和样式
 * - 支持折叠/展开
 * - 专业的视觉区分
 */

import { useMemo, useState } from 'react';
import {
  Brain,
  ClipboardList,
  Lightbulb,
  BarChart3,
  PenTool,
  CheckCircle2,
  User,
  Link2,
  BookOpen,
  Film,
  ScrollText,
  Star,
  Settings2,
  Wrench,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import StreamingText from './StreamingText';
import { parseMindMap, type MindMapData } from '@/utils/mindMap';
import MindMapViewer from '@/components/mindmap/MindMapViewer';
import { useI18n } from '@/i18n';
// 内容类型枚举（与后端保持一致）- juben剧本创作专用
export type StreamContentTypeEnum =
  // 基础类型
  | 'text'
  | 'markdown'
  | 'json'
  // 思考和分析类
  | 'thought'
  | 'plan_step'
  | 'insight'
  // 人物相关
  | 'character_profile'
  | 'character_relationship'
  // 故事结构相关
  | 'story_summary'
  | 'story_outline'
  | 'story_type'
  | 'five_elements'
  | 'series_info'
  | 'series_analysis'
  // 情节相关
  | 'major_plot'
  | 'detailed_plot'
  | 'drama_analysis'
  | 'plot_analysis'
  // 创作相关
  | 'script'
  | 'drama_plan'
  | 'proposal'
  // 可视化
  | 'mind_map'
  // 评估相关
  | 'evaluation'
  | 'script_evaluation'
  | 'story_evaluation'
  | 'outline_evaluation'
  | 'ip_evaluation'
  | 'novel_screening'
  | 'score_analysis'
  // 工具相关
  | 'search_result'
  | 'knowledge_result'
  | 'reference_result'
  | 'document'
  | 'formatted_content'
  // 系统相关
  | 'system_progress'
  | 'tool_result'
  | 'workflow_progress'
  | 'result_integration'
  | 'text_operation'
  | 'batch_progress'
  // 其他
  | 'final_answer'
  | 'error_content';

interface ContentBlockProps {
  contentType: StreamContentTypeEnum;
  content: string;
  isStreaming?: boolean;
  agentSource?: string;
  timestamp?: string;
  metadata?: Record<string, any>;
}

// 内容类型配置 - juben剧本创作专用
const CONTENT_TYPE_CONFIG: Record<StreamContentTypeEnum, {
  icon: React.ComponentType<{ className?: string }>;
  labelKey: string;
  color: string;
  bgColor: string;
  textColor: string;
}> = {
  // 基础类型
  text: {
    icon: Settings2,
    labelKey: 'chatGraph.contentType.text',
    color: 'text-gray-600',
    bgColor: 'bg-gray-50',
    textColor: 'text-gray-900',
  },
  markdown: {
    icon: BookOpen,
    labelKey: 'chatGraph.contentType.markdown',
    color: 'text-gray-600',
    bgColor: 'bg-gray-50',
    textColor: 'text-gray-900',
  },
  json: {
    icon: Settings2,
    labelKey: 'chatGraph.contentType.json',
    color: 'text-slate-600',
    bgColor: 'bg-slate-50',
    textColor: 'text-slate-900',
  },

  // 思考和分析类
  thought: {
    icon: Brain,
    labelKey: 'chatGraph.contentType.thought',
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    textColor: 'text-blue-900',
  },
  plan_step: {
    icon: ClipboardList,
    labelKey: 'chatGraph.contentType.planStep',
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
    textColor: 'text-purple-900',
  },
  insight: {
    icon: Lightbulb,
    labelKey: 'chatGraph.contentType.insight',
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-50',
    textColor: 'text-yellow-900',
  },

  // 人物相关
  character_profile: {
    icon: User,
    labelKey: 'chatGraph.contentType.characterProfile',
    color: 'text-indigo-600',
    bgColor: 'bg-indigo-50',
    textColor: 'text-indigo-900',
  },
  character_relationship: {
    icon: Link2,
    labelKey: 'chatGraph.contentType.characterRelationship',
    color: 'text-pink-600',
    bgColor: 'bg-pink-50',
    textColor: 'text-pink-900',
  },

  // 故事结构相关
  story_summary: {
    icon: BookOpen,
    labelKey: 'chatGraph.contentType.storySummary',
    color: 'text-amber-600',
    bgColor: 'bg-amber-50',
    textColor: 'text-amber-900',
  },
  story_outline: {
    icon: BookOpen,
    labelKey: 'chatGraph.contentType.storyOutline',
    color: 'text-orange-600',
    bgColor: 'bg-orange-50',
    textColor: 'text-orange-900',
  },
  story_type: {
    icon: Settings2,
    labelKey: 'chatGraph.contentType.storyType',
    color: 'text-stone-600',
    bgColor: 'bg-stone-50',
    textColor: 'text-stone-900',
  },
  five_elements: {
    icon: Settings2,
    labelKey: 'chatGraph.contentType.fiveElements',
    color: 'text-violet-600',
    bgColor: 'bg-violet-50',
    textColor: 'text-violet-900',
  },
  series_info: {
    icon: Settings2,
    labelKey: 'chatGraph.contentType.seriesInfo',
    color: 'text-cyan-600',
    bgColor: 'bg-cyan-50',
    textColor: 'text-cyan-900',
  },
  series_analysis: {
    icon: BarChart3,
    labelKey: 'chatGraph.contentType.seriesAnalysis',
    color: 'text-teal-600',
    bgColor: 'bg-teal-50',
    textColor: 'text-teal-900',
  },

  // 情节相关
  major_plot: {
    icon: Film,
    labelKey: 'chatGraph.contentType.majorPlot',
    color: 'text-red-600',
    bgColor: 'bg-red-50',
    textColor: 'text-red-900',
  },
  detailed_plot: {
    icon: Film,
    labelKey: 'chatGraph.contentType.detailedPlot',
    color: 'text-rose-600',
    bgColor: 'bg-rose-50',
    textColor: 'text-rose-900',
  },
  drama_analysis: {
    icon: ScrollText,
    labelKey: 'chatGraph.contentType.dramaAnalysis',
    color: 'text-red-700',
    bgColor: 'bg-red-50',
    textColor: 'text-red-900',
  },
  plot_analysis: {
    icon: Film,
    labelKey: 'chatGraph.contentType.plotAnalysis',
    color: 'text-red-800',
    bgColor: 'bg-red-50',
    textColor: 'text-red-900',
  },

  // 创作相关
  script: {
    icon: ScrollText,
    labelKey: 'chatGraph.contentType.script',
    color: 'text-emerald-600',
    bgColor: 'bg-emerald-50',
    textColor: 'text-emerald-900',
  },
  drama_plan: {
    icon: PenTool,
    labelKey: 'chatGraph.contentType.dramaPlan',
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    textColor: 'text-green-900',
  },
  proposal: {
    icon: PenTool,
    labelKey: 'chatGraph.contentType.proposal',
    color: 'text-lime-600',
    bgColor: 'bg-lime-50',
    textColor: 'text-lime-900',
  },

  // 可视化
  mind_map: {
    icon: Brain,
    labelKey: 'chatGraph.contentType.mindMap',
    color: 'text-sky-600',
    bgColor: 'bg-sky-50',
    textColor: 'text-sky-900',
  },

  // 评估相关
  evaluation: {
    icon: Star,
    labelKey: 'chatGraph.contentType.evaluation',
    color: 'text-orange-600',
    bgColor: 'bg-orange-50',
    textColor: 'text-orange-900',
  },
  script_evaluation: {
    icon: Star,
    labelKey: 'chatGraph.contentType.scriptEvaluation',
    color: 'text-amber-600',
    bgColor: 'bg-amber-50',
    textColor: 'text-amber-900',
  },
  story_evaluation: {
    icon: Star,
    labelKey: 'chatGraph.contentType.storyEvaluation',
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-50',
    textColor: 'text-yellow-900',
  },
  outline_evaluation: {
    icon: Star,
    labelKey: 'chatGraph.contentType.outlineEvaluation',
    color: 'text-yellow-700',
    bgColor: 'bg-yellow-50',
    textColor: 'text-yellow-900',
  },
  ip_evaluation: {
    icon: Star,
    labelKey: 'chatGraph.contentType.ipEvaluation',
    color: 'text-fuchsia-600',
    bgColor: 'bg-fuchsia-50',
    textColor: 'text-fuchsia-900',
  },
  novel_screening: {
    icon: Star,
    labelKey: 'chatGraph.contentType.novelScreening',
    color: 'text-violet-600',
    bgColor: 'bg-violet-50',
    textColor: 'text-violet-900',
  },
  score_analysis: {
    icon: BarChart3,
    labelKey: 'chatGraph.contentType.scoreAnalysis',
    color: 'text-indigo-600',
    bgColor: 'bg-indigo-50',
    textColor: 'text-indigo-900',
  },

  // 工具相关
  search_result: {
    icon: Wrench,
    labelKey: 'chatGraph.contentType.searchResult',
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    textColor: 'text-blue-900',
  },
  knowledge_result: {
    icon: BookOpen,
    labelKey: 'chatGraph.contentType.knowledgeResult',
    color: 'text-cyan-600',
    bgColor: 'bg-cyan-50',
    textColor: 'text-cyan-900',
  },
  reference_result: {
    icon: BookOpen,
    labelKey: 'chatGraph.contentType.referenceResult',
    color: 'text-teal-600',
    bgColor: 'bg-teal-50',
    textColor: 'text-teal-900',
  },
  document: {
    icon: Settings2,
    labelKey: 'chatGraph.contentType.document',
    color: 'text-stone-600',
    bgColor: 'bg-stone-50',
    textColor: 'text-stone-900',
  },
  formatted_content: {
    icon: Settings2,
    labelKey: 'chatGraph.contentType.formattedContent',
    color: 'text-zinc-600',
    bgColor: 'bg-zinc-50',
    textColor: 'text-zinc-900',
  },

  // 系统相关
  system_progress: {
    icon: Settings2,
    labelKey: 'chatGraph.contentType.systemProgress',
    color: 'text-gray-600',
    bgColor: 'bg-gray-50',
    textColor: 'text-gray-900',
  },
  tool_result: {
    icon: Wrench,
    labelKey: 'chatGraph.contentType.toolResult',
    color: 'text-slate-600',
    bgColor: 'bg-slate-50',
    textColor: 'text-slate-900',
  },
  workflow_progress: {
    icon: Settings2,
    labelKey: 'chatGraph.contentType.workflowProgress',
    color: 'text-coolGray-600',
    bgColor: 'bg-gray-50',
    textColor: 'text-gray-900',
  },
  result_integration: {
    icon: Settings2,
    labelKey: 'chatGraph.contentType.resultIntegration',
    color: 'text-neutral-600',
    bgColor: 'bg-neutral-50',
    textColor: 'text-neutral-900',
  },
  text_operation: {
    icon: Settings2,
    labelKey: 'chatGraph.contentType.textOperation',
    color: 'text-zinc-600',
    bgColor: 'bg-zinc-50',
    textColor: 'text-zinc-900',
  },
  batch_progress: {
    icon: Settings2,
    labelKey: 'chatGraph.contentType.batchProgress',
    color: 'text-warmGray-600',
    bgColor: 'bg-gray-50',
    textColor: 'text-gray-900',
  },

  // 其他
  final_answer: {
    icon: CheckCircle2,
    labelKey: 'chatGraph.contentType.finalAnswer',
    color: 'text-emerald-600',
    bgColor: 'bg-emerald-50',
    textColor: 'text-emerald-900',
  },
  error_content: {
    icon: Wrench,
    labelKey: 'chatGraph.contentType.error',
    color: 'text-red-600',
    bgColor: 'bg-red-50',
    textColor: 'text-red-900',
  },
};

export default function ContentTypeRenderer({
  contentType,
  content,
  isStreaming = false,
  agentSource,
  timestamp,
  metadata = {},
}: ContentBlockProps) {
  const { t, language } = useI18n();
  const [expanded, setExpanded] = useState(true);
  const config = CONTENT_TYPE_CONFIG[contentType] || CONTENT_TYPE_CONFIG.text;
  const Icon = config.icon;
  const mindMapData = useMemo<MindMapData | null>(() => {
    if (contentType !== 'mind_map') return null;
    const fromMeta = metadata?.mindMapData;
    return parseMindMap(fromMeta || content);
  }, [contentType, metadata, content]);

  // 判断是否可折叠（长内容或特定类型）
  const isCollapsible = content.length > 200 || [
    // 思考和分析类通常较长
    'thought',
    'plan_step',
    'insight',
    // 故事结构分析
    'story_summary',
    'story_outline',
    'five_elements',
    'series_analysis',
    // 情节分析
    'major_plot',
    'detailed_plot',
    'drama_analysis',
    'plot_analysis',
    // 剧本和策划
    'script',
    'drama_plan',
    // 评估类通常包含详细内容
    'evaluation',
    'script_evaluation',
    'story_evaluation',
    'outline_evaluation',
    'ip_evaluation',
    'novel_screening',
    'score_analysis',
    // 工具结果
    'search_result',
    'knowledge_result',
    'reference_result',
    'document',
  ].includes(contentType);

  return (
    <div
      className={`mb-3 rounded-lg border transition-all duration-300 ${
        isStreaming ? 'shadow-sm animate-fade-in' : 'shadow-sm'
      } ${config.bgColor} ${config.color}`}
    >
      {/* 头部 */}
      <div
        className={`flex items-center justify-between px-4 py-2.5 border-b ${config.color} border-opacity-20`}
        onClick={() => isCollapsible && setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2.5">
          {/* 图标 */}
          <div className={`p-1.5 rounded-lg ${config.bgColor} ${config.color}`}>
            <Icon className="w-4 h-4" />
          </div>

          {/* 类型名称 */}
          <span className={`text-sm font-semibold ${config.textColor}`}>
            {t(config.labelKey)}
          </span>

          {/* Agent来源 */}
          {agentSource && (
            <span className="text-xs text-gray-500 bg-white px-2 py-0.5 rounded-full">
              {agentSource}
            </span>
          )}

          {/* 流式状态 */}
          {isStreaming && (
            <div className="flex items-center gap-1.5 text-xs text-gray-500">
              <div className="w-1.5 h-1.5 bg-current rounded-full animate-pulse" />
              <span>{t('chatGraph.contentType.generating')}</span>
            </div>
          )}
        </div>

        {/* 折叠按钮 */}
        {isCollapsible && (
          <button className="p-1 hover:bg-white hover:bg-opacity-50 rounded transition-colors">
            {expanded ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
          </button>
        )}
      </div>

      {/* 内容 */}
      {expanded && (
        <div className="p-4">
          {contentType === 'mind_map' && mindMapData ? (
            <div className="space-y-3">
              <div className="text-base font-semibold text-gray-900">{mindMapData.title}</div>
              <MindMapViewer data={mindMapData} agentSource={agentSource} />
            </div>
          ) : (
            <div className={`prose prose-sm max-w-none ${config.textColor}`}>
              <StreamingText
                content={content}
                isStreaming={isStreaming}
                compact
              />
            </div>
          )}

          {/* 元数据 */}
          {Object.keys(metadata).length > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-200 border-opacity-30">
              <details className="text-xs">
                <summary className="cursor-pointer text-gray-600 hover:text-gray-900">
                  {t('chatGraph.contentType.viewMetadata')}
                </summary>
                <pre className="mt-2 p-2 bg-white bg-opacity-50 rounded overflow-x-auto">
                  {JSON.stringify(metadata, null, 2)}
                </pre>
              </details>
            </div>
          )}

          {/* 时间戳 */}
          {timestamp && (
            <div className="mt-2 text-xs text-gray-500 text-right">
              {new Date(timestamp).toLocaleString(language === 'zh' ? 'zh-CN' : 'en-US')}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * 内容块列表组件
 * 用于渲染多个连续的内容块
 */
interface ContentBlockListProps {
  blocks: Array<{
    contentType: StreamContentTypeEnum;
    content: string;
    agentSource?: string;
    timestamp?: string;
    metadata?: Record<string, any>;
  }>;
  isStreaming?: boolean;
}

export function ContentBlockList({ blocks, isStreaming = false }: ContentBlockListProps) {
  if (!blocks || blocks.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3">
      {blocks.map((block, index) => (
        <ContentTypeRenderer
          key={index}
          contentType={block.contentType}
          content={block.content}
          isStreaming={isStreaming && index === blocks.length - 1}
          agentSource={block.agentSource}
          timestamp={block.timestamp}
          metadata={block.metadata}
        />
      ))}
    </div>
  );
}

/**
 * 解析后端事件为内容块
 */
export function parseEventToContentBlock(event: any): {
  contentType: StreamContentTypeEnum;
  content: string;
  agentSource?: string;
  timestamp?: string;
  metadata?: Record<string, any>;
} | null {
  try {
    // 兼容多种事件格式
    const contentType = event.payload?.content_type || event.content_type || 'text';
    const content = event.payload?.data || event.content || '';
    const agentSource = event.agent_source || event.agentSource;
    const timestamp = event.timestamp;
    const metadata = event.payload?.metadata || event.metadata || {};

    return {
      contentType,
      content,
      agentSource,
      timestamp,
      metadata,
    };
  } catch (error) {
    console.error('Failed to parse event:', error);
    return null;
  }
}
