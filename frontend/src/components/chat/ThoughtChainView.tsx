/**
 * 思考链可视化组件
 * 参考: LangGraph 的思考链展示设计
 *
 * 功能:
 * - 显示 AI 推理步骤
 * - 可折叠/展开
 * - 步骤进度显示
 * - 工具调用可视化
 */

import { useState } from 'react';
import {
  ChevronDown,
  ChevronRight,
  Brain,
  Loader2,
  Settings,
  Search,
  Database,
  FileText,
  CheckCircle2,
  AlertCircle,
  Info,
  Bot,
} from 'lucide-react';
import { useI18n, translate } from '@/i18n';

interface ThoughtStep {
  step: number;
  content: string;
  timestamp: string;
  type?: 'system' | 'tool' | 'reasoning' | 'error' | 'info' | 'subagent' | 'handoff';
  status?: 'running' | 'completed' | 'error';
  toolName?: string;
}

interface ThoughtChainViewProps {
  steps: ThoughtStep[];
  expanded?: boolean;
  onToggle?: () => void;
  isStreaming?: boolean;
}

const typeConfig = {
  system: { icon: Settings, color: 'text-blue-600', bgColor: 'bg-blue-50' },
  tool: { icon: Settings, color: 'text-purple-600', bgColor: 'bg-purple-50' },
  reasoning: { icon: Brain, color: 'text-green-600', bgColor: 'bg-green-50' },
  error: { icon: AlertCircle, color: 'text-red-600', bgColor: 'bg-red-50' },
  info: { icon: Info, color: 'text-gray-600', bgColor: 'bg-gray-50' },
  subagent: { icon: Bot, color: 'text-teal-600', bgColor: 'bg-teal-50' },
  handoff: { icon: Bot, color: 'text-amber-600', bgColor: 'bg-amber-50' },
};

const toolIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  websearch: Search,
  web_search: Search,
  knowledge_query: Search,
  knowledge: Database,
  file_reference: FileText,
  spawn_subagent: Bot,
  transfer_to: Bot,
  compose_agents: Bot,
};

export default function ThoughtChainView({
  steps,
  expanded = false,
  onToggle,
  isStreaming = false,
}: ThoughtChainViewProps) {
  const { t } = useI18n();
  const [localExpanded, setLocalExpanded] = useState(expanded);
  const isExpanded = onToggle ? expanded : localExpanded;

  const handleToggle = () => {
    if (onToggle) {
      onToggle();
    } else {
      setLocalExpanded(!localExpanded);
    }
  };

  if (steps.length === 0 && !isStreaming) {
    return null;
  }

  return (
    <div className="mb-4 border border-gray-200 rounded-lg overflow-hidden">
      {/* 头部 */}
      <button
        onClick={handleToggle}
        className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-gray-600" />
          <span className="text-sm font-medium text-gray-700">{t('chatGraph.thoughtChain.title')}</span>
          {isStreaming && (
            <Loader2 className="w-3 h-3 animate-spin text-gray-400" />
          )}
          <span className="text-xs text-gray-500">
            {t('chatGraph.thoughtChain.steps', { count: steps.length })}
          </span>
        </div>
        {isExpanded ? (
          <ChevronDown className="w-4 h-4 text-gray-500" />
        ) : (
          <ChevronRight className="w-4 h-4 text-gray-500" />
        )}
      </button>

      {/* 思考步骤 */}
      {isExpanded && (
        <div className="p-4 space-y-3 max-h-96 overflow-y-auto">
          {steps.length === 0 && isStreaming && (
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>{t('chatGraph.thoughtChain.thinking')}</span>
            </div>
          )}

          {steps.map((step, index) => {
            const config = typeConfig[step.type || 'info'] || typeConfig.info;
            const Icon = config.icon;
            const ToolIcon = step.toolName ? toolIcons[step.toolName] : null;

            return (
              <div
                key={step.step}
                className={`flex gap-3 p-3 rounded-lg ${config.bgColor} transition-all`}
              >
                {/* 左侧图标和时间线 */}
                <div className="flex flex-col items-center">
                  <div className={`p-1.5 rounded-full ${config.bgColor} border-2 border-white`}>
                    {ToolIcon ? (
                      <ToolIcon className={`w-3.5 h-3.5 ${config.color}`} />
                    ) : (
                      <Icon className={`w-3.5 h-3.5 ${config.color}`} />
                    )}
                  </div>
                  {index < steps.length - 1 && (
                    <div className="w-0.5 h-full bg-gray-300 mt-2" />
                  )}
                </div>

                {/* 右侧内容 */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-medium text-gray-600">
                      {t('chatGraph.thoughtChain.step', { n: step.step })}
                    </span>
                    {step.type && (
                      <span className={`text-xs px-1.5 py-0.5 rounded ${config.bgColor} ${config.color}`}>
                        {step.type === 'system' && t('chatGraph.thoughtChain.type.system')}
                        {step.type === 'tool' && t('chatGraph.thoughtChain.type.tool')}
                        {step.type === 'reasoning' && t('chatGraph.thoughtChain.type.reasoning')}
                        {step.type === 'error' && t('chatGraph.thoughtChain.type.error')}
                        {step.type === 'info' && t('chatGraph.thoughtChain.type.info')}
                      </span>
                    )}
                    {step.status === 'running' && (
                      <Loader2 className="w-3 h-3 animate-spin text-blue-500" />
                    )}
                    {step.status === 'completed' && (
                      <CheckCircle2 className="w-3 h-3 text-green-500" />
                    )}
                    {step.status === 'error' && (
                      <AlertCircle className="w-3 h-3 text-red-500" />
                    )}
                  </div>

                  <p className="text-sm text-gray-700 whitespace-pre-wrap break-words">
                    {step.content}
                  </p>

                  {step.toolName && (
                    <div className="mt-1 text-xs text-gray-500">
                      {t('chatGraph.thoughtChain.toolLabel', { name: step.toolName })}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/**
 * 将后端事件转换为思考步骤
 */
export function convertEventsToThoughtSteps(
  events: Array<{ event: string; data: any; timestamp: string }>
): ThoughtStep[] {
  const steps: ThoughtStep[] = [];
  let stepNumber = 1;

  for (const event of events) {
    // 系统事件
    if (event.event === 'system' && event.data?.content) {
      steps.push({
        step: stepNumber++,
        content: event.data.content,
        timestamp: event.timestamp,
        type: 'system',
        status: 'completed',
      });
    }

    // 工具事件
    if (event.event === 'tool_start') {
      steps.push({
        step: stepNumber++,
        content: translate('chatGraph.thoughtChain.startTool', undefined, {
          tool: event.data?.tool_name || translate('chatGraph.thoughtChain.type.tool'),
        }),
        timestamp: event.timestamp,
        type: 'tool',
        status: 'running',
        toolName: event.data?.tool_name,
      });
    }

    if (event.event === 'tool_processing') {
      steps.push({
        step: stepNumber++,
        content: event.data?.message || translate('chatGraph.thoughtChain.processing'),
        timestamp: event.timestamp,
        type: 'tool',
        status: 'running',
        toolName: event.data?.tool_name,
      });
    }

    if (event.event === 'tool_complete') {
      steps.push({
        step: stepNumber++,
        content: translate('chatGraph.thoughtChain.toolDone', undefined, {
          tool: event.data?.tool_name || translate('chatGraph.thoughtChain.type.tool'),
        }),
        timestamp: event.timestamp,
        type: 'tool',
        status: 'completed',
        toolName: event.data?.tool_name,
      });
    }

    // 错误事件
    if (event.event === 'error') {
      steps.push({
        step: stepNumber++,
        content: event.data?.error || event.data?.content || translate('chatGraph.thoughtChain.errorOccurred'),
        timestamp: event.timestamp,
        type: 'error',
        status: 'error',
      });
    }

    // 计费事件
    if (event.event === 'billing') {
      steps.push({
        step: stepNumber++,
        content: event.data?.content || translate('chatGraph.thoughtChain.billing'),
        timestamp: event.timestamp,
        type: 'info',
        status: 'completed',
      });
    }
  }

  return steps;
}
