/**
 * 聊天消息 — 支持紧凑工作室样式 + Cursor 风格过程时间线
 */

import { useMemo, useState, useEffect } from 'react';
import { User, Bot, Layers } from 'lucide-react';
import { useChat } from '@/hooks/useChat';
import { useSettingsStore } from '@/store/settingsStore';
import { format } from 'date-fns';
import clsx from 'clsx';
import StreamingText from './StreamingText';
import { useI18n } from '@/i18n';
import { convertEventsToThoughtSteps } from './ThoughtChainView';
import ThoughtChainView from './ThoughtChainView';
import AgentProcessTimeline, {
  thoughtsToProcessSteps,
  type ProcessStep,
} from './AgentProcessTimeline';
import EnhancedMessageActions from './EnhancedMessageActions';
import ContentTypeRenderer, { parseEventToContentBlock } from './ContentTypeRenderer';
import MindMapViewer from '@/components/mindmap/MindMapViewer';
import type { MindMapData } from '@/utils/mindMap';
import { parseMindMap } from '@/utils/mindMap';
import { parseContentType } from '@/utils/contentTypeConfig';
import type { Message, StreamContentType } from '@/types';

interface ChatMessageProps {
  message: Message;
  showThoughtChain?: boolean;
  compact?: boolean;
}

export default function ChatMessage({
  message,
  showThoughtChain = true,
  compact = false,
}: ChatMessageProps) {
  const { regenerateMessage, editMessage, createBranch, deleteMessage } = useChat();
  const { showTimestamp } = useSettingsStore();
  const { t } = useI18n();
  const isUser = message.role === 'user';
  const isStreaming = message.status === 'streaming';

  const [showContentTypeView, setShowContentTypeView] = useState(
    message.metadata?.contentType === 'mind_map'
  );

  useEffect(() => {
    if (message.metadata?.contentType === 'mind_map') {
      setShowContentTypeView(true);
    }
  }, [message.metadata?.contentType]);

  const inlineMindMapData = useMemo<MindMapData | null>(() => {
    if (!message.content) return null;
    return parseMindMap(message.content);
  }, [message.content]);

  const processSteps: ProcessStep[] = useMemo(() => {
    const fromMeta = (message.metadata?.processSteps || []) as ProcessStep[];
    if (fromMeta.length > 0) return fromMeta;

    const thoughts = message.metadata?.thoughtChain || [];
    if (thoughts.length > 0) return thoughtsToProcessSteps(thoughts);

    const toolEvents = message.metadata?.toolEvents || [];
    const systemEvents = message.metadata?.systemEvents || [];
    const allEvents = [
      ...toolEvents.map((e: any) => ({
        event: e.event,
        data: e.data,
        timestamp: e.timestamp || '',
      })),
      ...systemEvents.map((e: any) => ({
        event: 'system',
        data: { content: e.content },
        timestamp: e.timestamp || '',
      })),
    ];
    return convertEventsToThoughtSteps(allEvents).map((s) => ({
      id: `legacy-${s.step}`,
      kind: (s.type as ProcessStep['kind']) || 'info',
      title: s.content,
      status: s.status === 'completed' ? 'done' : s.status === 'error' ? 'error' : s.status || 'done',
      toolName: s.toolName,
      timestamp: s.timestamp,
    }));
  }, [message.metadata]);

  const contentBlocks = useMemo(() => {
    const blocks: Array<{
      contentType: StreamContentType;
      content: string;
      agentSource?: string;
      timestamp?: string;
      metadata?: Record<string, any>;
    }> = [];

    if (message.metadata?.contentBlocks) {
      for (const block of message.metadata.contentBlocks) {
        blocks.push({
          contentType: parseContentType(block.contentType),
          content: block.content || '',
          agentSource: block.agentSource,
          timestamp: block.timestamp,
          metadata: block.metadata,
        });
      }
    }
    if (message.metadata?.enhancedEvents) {
      for (const event of message.metadata.enhancedEvents) {
        const parsed = parseEventToContentBlock(event);
        if (parsed && parsed.content) blocks.push(parsed);
      }
    }
    return blocks;
  }, [message.metadata]);

  const canRetry = message.metadata?.canRetry === true && message.status === 'error';
  const hasContentTypeBlocks = contentBlocks.length > 0;
  const canShowContentTypeView = hasContentTypeBlocks || Boolean(message.metadata?.contentType);
  const displayContent = message.content || '';

  if (isUser) {
    return (
      <div id={`message-${message.id}`} className="flex gap-2 justify-end group">
        <div className={clsx('min-w-0', compact ? 'max-w-[88%]' : 'max-w-[70%]')}>
          <div
            className={clsx(
              'bg-ink text-white rounded-2xl rounded-br-md',
              compact ? 'px-3 py-2 text-[12.5px] leading-snug' : 'px-4 py-3 text-sm'
            )}
          >
            {message.content}
          </div>
          {showTimestamp && message.timestamp && (
            <div className="mt-0.5 text-[10px] text-ink-faint text-right pr-1">
              {format(new Date(message.timestamp), 'HH:mm')}
            </div>
          )}
          {!compact && (
            <div className="mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <EnhancedMessageActions
                message={message}
                onEdit={(id, content) => editMessage(id, content)}
                onDelete={deleteMessage}
                onBranch={createBranch}
                isStreaming={false}
                canRegenerate={false}
                canEdit={true}
              />
            </div>
          )}
        </div>
        <div
          className={clsx(
            'flex-shrink-0 rounded-full bg-pearl-soft flex items-center justify-center',
            compact ? 'w-7 h-7' : 'w-9 h-9'
          )}
        >
          <User className={clsx(compact ? 'w-3.5 h-3.5' : 'w-4 h-4', 'text-ink-muted')} />
        </div>
      </div>
    );
  }

  return (
    <div id={`message-${message.id}`} className="flex gap-2 justify-start group">
      <div
        className={clsx(
          'flex-shrink-0 rounded-full bg-ink flex items-center justify-center',
          compact ? 'w-7 h-7' : 'w-9 h-9'
        )}
      >
        <Bot className={clsx(compact ? 'w-3.5 h-3.5' : 'w-4 h-4', 'text-white')} />
      </div>

      <div className={clsx('flex-1 min-w-0', compact ? 'max-w-[94%]' : 'max-w-[85%]')}>
        <div className="flex items-center gap-1.5 mb-1">
          <span className={clsx('font-medium text-ink', compact ? 'text-[11px]' : 'text-sm')}>
            {message.agentName || t('chat.assistant')}
          </span>
          {showTimestamp && message.timestamp && (
            <span className="text-[10px] text-ink-faint">
              {format(new Date(message.timestamp), 'HH:mm')}
            </span>
          )}
          {canShowContentTypeView && (
            <button
              type="button"
              onClick={() => setShowContentTypeView(!showContentTypeView)}
              className="p-0.5 hover:bg-pearl-soft rounded"
              title={t('chat.toggleView')}
            >
              <Layers className="w-3 h-3 text-ink-faint" />
            </button>
          )}
        </div>

        {/* Cursor 风格工作过程 — 始终可见（可折叠） */}
        {showThoughtChain && (processSteps.length > 0 || isStreaming) && (
          <AgentProcessTimeline
            steps={processSteps}
            isStreaming={isStreaming}
            defaultExpanded
            className="mb-1.5"
          />
        )}

        {/* 兼容旧 ThoughtChain（无 processSteps 时） */}
        {!message.metadata?.processSteps?.length &&
          showThoughtChain &&
          !compact &&
          convertEventsToThoughtSteps([]).length > 0 && (
            <ThoughtChainView steps={[]} isStreaming={isStreaming} />
          )}

        {showContentTypeView && canShowContentTypeView ? (
          <div className="space-y-2">
            {hasContentTypeBlocks &&
              contentBlocks.map((block, index) => (
                <ContentTypeRenderer
                  key={index}
                  contentType={block.contentType}
                  content={block.content}
                  isStreaming={isStreaming && index === contentBlocks.length - 1}
                  agentSource={block.agentSource}
                  timestamp={block.timestamp}
                  metadata={block.metadata}
                />
              ))}
            {!hasContentTypeBlocks && message.metadata?.contentType && (
              <ContentTypeRenderer
                contentType={parseContentType(message.metadata.contentType)}
                content={message.content}
                isStreaming={isStreaming}
                agentSource={message.agentName}
                timestamp={message.timestamp}
                metadata={message.metadata}
              />
            )}
          </div>
        ) : (
          <div
            className={clsx(
              'rounded-2xl rounded-tl-md border border-pearl-line/80 bg-white/80',
              compact ? 'px-2.5 py-2' : 'p-4'
            )}
          >
            {(message.metadata?.contentType === 'mind_map' &&
              (message.metadata as any)?.mindMapData) ||
            inlineMindMapData ? (
              <div className="space-y-2">
                <div className="text-sm font-semibold text-ink">
                  {(
                    ((message.metadata as any)?.mindMapData as MindMapData | undefined)?.title ||
                    inlineMindMapData?.title
                  )}
                </div>
                <MindMapViewer
                  data={
                    (((message.metadata as any)?.mindMapData as MindMapData) ||
                      inlineMindMapData) as MindMapData
                  }
                  agentSource={message.agentName}
                />
              </div>
            ) : (
              <StreamingText content={displayContent} isStreaming={isStreaming} compact={compact} />
            )}

            {message.status === 'error' && message.metadata?.error && (
              <div className="mt-2 p-2 bg-rose-50 border border-rose-200 rounded-lg">
                <p className="text-[11px] text-rose-700">{message.metadata.error}</p>
                {canRetry && regenerateMessage && (
                  <button
                    type="button"
                    onClick={() => regenerateMessage(message.id)}
                    className="mt-1.5 px-2 py-1 text-[11px] bg-rose-600 text-white rounded"
                  >
                    {t('common.retry')}
                  </button>
                )}
              </div>
            )}
          </div>
        )}

        {!compact && (
          <div className="mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <EnhancedMessageActions
              message={message}
              onRegenerate={() => regenerateMessage(message.id)}
              onEdit={(id, content) => editMessage(id, content)}
              onDelete={deleteMessage}
              onBranch={createBranch}
              isStreaming={isStreaming}
              canRegenerate={true}
              canEdit={false}
            />
          </div>
        )}
      </div>
    </div>
  );
}
