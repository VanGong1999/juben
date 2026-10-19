/**
 * 系统进度显示组件
 * 实时显示 Agent 执行过程中的系统消息
 */

import { useMemo } from 'react';
import { CheckCircle, Circle, Loader2, Search, Database, Globe, FileText, Wrench } from 'lucide-react';
import { useI18n } from '@/i18n';

interface SystemEvent {
  content: string;
  timestamp?: string;
}

interface SystemProgressProps {
  events: SystemEvent[];
  isStreaming: boolean;
}

// 根据内容匹配图标
function getEventIcon(content: string) {
  if (content.includes('🎬') || content.includes('开始分析')) {
    return { icon: Circle, color: 'text-blue-500', bg: 'bg-blue-50' };
  }
  if (content.includes('🔍') || content.includes('分析需求') || content.includes('意图')) {
    return { icon: Search, color: 'text-purple-500', bg: 'bg-purple-50' };
  }
  if (content.includes('✅') || content.includes('完成')) {
    return { icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-50' };
  }
  if (content.includes('🔧') || content.includes('调用') || content.includes('工具')) {
    return { icon: Wrench, color: 'text-orange-500', bg: 'bg-orange-50' };
  }
  if (content.includes('知识库') || content.includes('Database')) {
    return { icon: Database, color: 'text-cyan-500', bg: 'bg-cyan-50' };
  }
  if (content.includes('网络搜索') || content.includes('web') || content.includes('Globe')) {
    return { icon: Globe, color: 'text-indigo-500', bg: 'bg-indigo-50' };
  }
  if (content.includes('🎭') || content.includes('生成') || content.includes('创作')) {
    return { icon: Loader2, color: 'text-amber-500', bg: 'bg-amber-50', spin: true };
  }
  if (content.includes('📊') || content.includes('Token') || content.includes('积分')) {
    return { icon: FileText, color: 'text-gray-500', bg: 'bg-gray-50' };
  }
  return { icon: Circle, color: 'text-gray-400', bg: 'bg-gray-50' };
}

// 根据内容判断状态
function getEventStatus(content: string): 'pending' | 'active' | 'completed' | 'info' {
  if (content.includes('✅') || content.includes('完成')) {
    return 'completed';
  }
  if (content.includes('🎭') || content.includes('生成') || content.includes('正在')) {
    return 'active';
  }
  if (content.includes('🎬') || content.includes('开始')) {
    return 'pending';
  }
  return 'info';
}

export default function SystemProgress({ events, isStreaming }: SystemProgressProps) {
  const { t } = useI18n();
  // 过滤并格式化事件
  const displayEvents = useMemo(() => {
    try {
      if (!events || !Array.isArray(events)) {
        console.warn('[SystemProgress] Invalid events:', events);
        return [];
      }

      return events.map((event, index) => {
        // 确保每个 event 都有 content
        const content = event?.content || t('chatGraph.systemProgress.unknownEvent');
        const status = getEventStatus(content);
        const { icon: Icon, color, bg, spin } = getEventIcon(content);

        return {
          id: index,
          content,
          timestamp: event?.timestamp,
          status,
          Icon,
          color,
          bg,
          spin: spin || false
        };
      });
    } catch (error) {
      console.error('[SystemProgress] Error processing events:', error);
      return [];
    }
  }, [events, t]);

  if (!displayEvents || displayEvents.length === 0) {
    return null;
  }

  return (
    <div className="mb-3 rounded-xl border border-gray-200 bg-white/80 p-3">
      <div className="flex items-center gap-2 text-xs text-gray-600 mb-2">
        <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
        <span>{t('chatGraph.systemProgress.title')}</span>
      </div>

      <div className="relative">
        {displayEvents.map((event, index) => {
          const IconComponent = event.Icon;
          const isLast = index === displayEvents.length - 1;
          return (
            <div key={index} className="relative flex items-start gap-3 pb-3 last:pb-0">
              {!isLast && (
                <div className="absolute left-[14px] top-7 h-[calc(100%-12px)] w-px bg-gray-200" />
              )}

              <div className={`relative z-10 mt-0.5 flex h-7 w-7 items-center justify-center rounded-full ${event.bg}`}>
                <IconComponent
                  className={`w-4 h-4 ${event.color} ${
                    event.spin && event.status === 'active' && isStreaming ? 'animate-spin' : ''
                  }`}
                />
              </div>

              <div
                className={`flex-1 rounded-lg border px-3 py-2 ${
                  event.status === 'completed'
                    ? 'border-green-200 bg-green-50'
                    : event.status === 'active'
                    ? 'border-amber-200 bg-amber-50'
                    : 'border-gray-200 bg-gray-50'
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <p
                    className={`text-xs leading-5 ${
                      event.status === 'completed'
                        ? 'text-green-800'
                        : event.status === 'active'
                        ? 'text-gray-900 font-medium'
                        : 'text-gray-700'
                    }`}
                  >
                    {event.content}
                  </p>
                  {event.status === 'active' && isStreaming && (
                    <div className="flex gap-1 text-amber-500">
                      <div className="w-1 h-1 bg-current rounded-full animate-pulse" />
                      <div className="w-1 h-1 bg-current rounded-full animate-pulse delay-100" />
                      <div className="w-1 h-1 bg-current rounded-full animate-pulse delay-200" />
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
