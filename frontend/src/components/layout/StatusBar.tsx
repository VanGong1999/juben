/**
 * 状态栏组件
 */

import { useChatStore } from '@/store/chatStore';
import { useAgents } from '@/hooks/useAgents';
import { useUIStore } from '@/store/uiStore';
import { Loader2, Eye, EyeOff } from 'lucide-react';
import { format } from 'date-fns';
import { useI18n } from '@/i18n';

export default function StatusBar() {
  const { isStreaming, messages, streamingMessageId } = useChatStore();
  const { t } = useI18n();
  const { activeAgentData } = useAgents();
  const { thoughtChainExpanded, toggleThoughtChain } = useUIStore();

  const streamingMessage = messages.find((m) => m.id === streamingMessageId);
  const tokensUsed = streamingMessage?.metadata?.tokensUsed || 0;

  return (
    <div className="flex items-center justify-between px-6 py-2 border-b border-gray-200 bg-gray-50 text-xs">
      {/* 左侧 */}
      <div className="flex items-center gap-4">
        {activeAgentData && (
          <div className="flex items-center gap-2">
            <span className="text-gray-600">{t('ui.agentLabel')}</span>
            <span className="font-medium text-gray-900">{activeAgentData.displayName}</span>
          </div>
        )}

        {isStreaming && (
          <div className="flex items-center gap-2">
            <Loader2 className="w-3 h-3 animate-spin text-black" />
            <span className="text-gray-600">{t('ui.responding')}</span>
            {tokensUsed > 0 && (
              <span className="text-gray-500">{t('ui.generatedTokens', { count: tokensUsed })}</span>
            )}
          </div>
        )}

        {!isStreaming && messages.length > 0 && (
          <div className="text-gray-500">
            <span>{t('ui.totalMessages', { count: messages.length })}</span>
          </div>
        )}
      </div>

      {/* 右侧 */}
      <div className="flex items-center gap-4">
        {/* 思考链切换 */}
        <button
          onClick={toggleThoughtChain}
          className="flex items-center gap-1.5 text-gray-600 hover:text-gray-900 transition-colors"
        >
          {thoughtChainExpanded ? (
            <Eye className="w-3.5 h-3.5" />
          ) : (
            <EyeOff className="w-3.5 h-3.5" />
          )}
          <span>{t('settings.thoughtChain')}</span>
        </button>

        {/* 当前时间 */}
        <div className="text-gray-500">
          {format(new Date(), 'HH:mm')}
        </div>
      </div>
    </div>
  );
}
