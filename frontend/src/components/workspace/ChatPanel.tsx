/**
 * 聊天面板 — 紧凑密度 + Cursor 风格工作过程
 */

import { useChatStore } from '@/store/chatStore';
import { useAgentStore } from '@/store/agentStore';
import { useWorkspaceStore } from '@/store/workspaceStore';
import ChatMessage from '@/components/chat/ChatMessage';
import ChatInputArea from '@/components/workspace/ChatInputArea';
import { Loader2, MessageCircle, History, Plus } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import {
  listChatSessions,
  getChatSessionHistory,
  type ChatSessionMeta,
} from '@/services/chatService';
import type { Message } from '@/types';
import { useI18n } from '@/i18n';

export default function ChatPanel() {
  const { messages, isStreaming, sendMessage, newSession, setMessages, setCurrentSession } =
    useChatStore();
  const { agents, activeAgent } = useAgentStore();
  const { notes, setViewMode } = useWorkspaceStore();
  const { t, language } = useI18n();
  const location = useLocation();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [sessions, setSessions] = useState<ChatSessionMeta[]>([]);
  const [loadingSessions, setLoadingSessions] = useState(false);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  useEffect(() => {
    if (!location.hash) return;
    const targetId = location.hash.replace('#', '');
    const element = document.getElementById(targetId);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [location.hash, messages]);

  const currentAgent = agents.find((a) => a.id === activeAgent);
  const selectedNotesCount = notes.filter((n) => n.select_status === 1).length;
  const totalNotesCount = notes.length;

  const getAgentSuggestions = () => {
    const category = currentAgent?.category;
    const base = [currentAgent?.inputExample || t('workspace.suggestion.default')];
    const categorySuggestions: Record<string, string[]> = {
      planning: [t('workspace.suggestion.outline'), t('workspace.suggestion.bios')],
      creation: [t('workspace.suggestion.scene1'), t('workspace.suggestion.dialogue')],
      evaluation: [t('workspace.suggestion.score'), t('workspace.suggestion.optimize')],
      analysis: [t('workspace.suggestion.theme'), t('workspace.suggestion.relations')],
      workflow: [t('workspace.suggestion.steps'), t('workspace.suggestion.tasks')],
      character: [t('workspace.suggestion.relationMap'), t('workspace.suggestion.background')],
      story: [t('workspace.suggestion.synopsis'), t('workspace.suggestion.plotTurns')],
      orchestration: [t('workspace.suggestion.orchestrate')],
    };
    const extras = category ? categorySuggestions[category] || [] : [];
    const notesHint = selectedNotesCount > 0 ? [t('workspace.suggestion.notesHint')] : [];
    return [...base, ...extras, ...notesHint].filter(Boolean);
  };

  const suggestions = getAgentSuggestions();

  const handleSendMessage = async (content: string) => {
    await sendMessage(content, activeAgent);
  };

  const loadSessions = async () => {
    setLoadingSessions(true);
    try {
      const userId = localStorage.getItem('userId') || 'default_user';
      const res = await listChatSessions(userId);
      setSessions(res.sessions || []);
    } catch {
      setSessions([]);
    } finally {
      setLoadingSessions(false);
    }
  };

  const toggleHistory = () => {
    const next = !historyOpen;
    setHistoryOpen(next);
    if (next) void loadSessions();
  };

  const switchSession = async (sessionId: string) => {
    try {
      const res = await getChatSessionHistory(sessionId);
      const history = res.history || [];
      const mapped: Message[] = history.map((h, i) => ({
        id: h.id || `hist-${i}-${h.created_at || Date.now()}`,
        role: (h.message_type === 'user' ? 'user' : 'assistant') as Message['role'],
        content: h.content || '',
        timestamp: h.created_at || new Date().toISOString(),
        agentName: h.agent_name,
        status: 'complete' as const,
      }));
      setCurrentSession(sessionId);
      setMessages(mapped);
      setHistoryOpen(false);
    } catch {
      /* ignore */
    }
  };

  const handleNewSession = () => {
    newSession();
    setHistoryOpen(false);
  };

  return (
    <div className="flex flex-col h-full bg-transparent min-h-0">
      {/* 紧凑标题 */}
      <div className="flex-shrink-0 px-3 py-2 border-b border-pearl-line/80 relative">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg flex items-center justify-center bg-atelier-teal-soft text-sm border border-pearl-line shrink-0">
            {currentAgent?.icon || '✦'}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5">
              <h3 className="font-display font-semibold text-ink text-[13px] truncate leading-tight">
                {currentAgent?.displayName || t('workspace.chooseExpert')}
              </h3>
              {currentAgent?.category && (
                <span className="text-[9px] px-1 py-0.5 rounded bg-pearl-soft text-ink-faint shrink-0">
                  {{
                    planning: t('workspace.category.planning'),
                    story: t('workspace.category.story'),
                    analysis: t('workspace.category.analysis'),
                    character: t('workspace.category.character'),
                    creation: t('workspace.category.creation'),
                    evaluation: t('workspace.category.evaluation'),
                    workflow: t('workspace.category.workflow'),
                    utility: t('workspace.category.utility'),
                    orchestration: t('workspace.category.orchestration'),
                  }[currentAgent.category] || currentAgent.category}
                </span>
              )}
            </div>
            <p className="text-[10px] text-ink-muted truncate leading-tight mt-0.5">
              {currentAgent?.description || t('workspace.fallbackDesc')}
            </p>
          </div>
          {isStreaming && (
            <div className="flex items-center gap-1 text-[10px] text-atelier-teal font-medium shrink-0">
              <Loader2 className="w-3 h-3 animate-spin" />
              {t('workspace.working')}
            </div>
          )}
          <button
            type="button"
            onClick={toggleHistory}
            className="p-1.5 rounded-lg text-ink-muted hover:bg-pearl-soft hover:text-atelier-teal shrink-0"
            title={t('workspace.history')}
          >
            <History className="w-4 h-4" />
          </button>
        </div>
        {totalNotesCount > 0 && (
          <button
            type="button"
            onClick={() => setViewMode('notes')}
            className="mt-1 text-[10px] text-ink-faint hover:text-atelier-teal"
          >
            {t('workspace.notesView', { selected: selectedNotesCount, total: totalNotesCount })}
          </button>
        )}
      </div>

      {historyOpen && (
        <div className="absolute right-3 top-full mt-1 w-72 max-h-96 overflow-y-auto rounded-xl border border-pearl-line bg-white shadow-atelier-lg z-50">
          <div className="flex items-center justify-between px-3 py-2 border-b border-pearl-line">
            <span className="text-xs font-semibold text-ink">{t('workspace.history')}</span>
            <button
              type="button"
              onClick={handleNewSession}
              className="flex items-center gap-1 text-[11px] text-atelier-teal hover:underline"
            >
              <Plus className="w-3 h-3" /> {t('workspace.newChat')}
            </button>
          </div>
          {loadingSessions ? (
            <div className="px-3 py-6 text-center text-xs text-ink-faint">{t('workspace.loading')}</div>
          ) : sessions.length === 0 ? (
            <div className="px-3 py-6 text-center text-xs text-ink-faint">{t('workspace.noHistory')}</div>
          ) : (
            <ul>
              {sessions.map((s) => (
                <li key={s.session_id}>
                  <button
                    type="button"
                    onClick={() => switchSession(s.session_id)}
                    className="w-full text-left px-3 py-2 hover:bg-pearl-soft/60 transition-colors border-b border-pearl-line/40"
                  >
                    <div className="text-xs font-medium text-ink truncate">
                      {(s.title || t('workspace.unnamed')).slice(0, 40)}
                    </div>
                    <div className="mt-0.5 flex items-center gap-2 text-[10px] text-ink-faint">
                      <span>{t('workspace.messageCount', { count: s.message_count || 0 })}</span>
                      <span>·</span>
                      <span>
                        {s.last_active
                          ? new Date(s.last_active).toLocaleString(language === 'zh' ? 'zh-CN' : 'en-US', {
                              month: 'numeric',
                              day: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit',
                            })
                          : ''}
                      </span>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-2.5 py-2 space-y-2.5 min-h-0">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center px-4 text-center">
            <div className="w-11 h-11 rounded-2xl bg-atelier-teal-soft text-atelier-teal flex items-center justify-center mb-3 border border-pearl-line">
              <MessageCircle className="w-5 h-5" />
            </div>
            <p className="font-display text-sm font-semibold text-ink">{t('workspace.chatWithExpert')}</p>
            <p className="text-[11px] mt-1.5 leading-relaxed max-w-[220px] text-ink-muted">
              {t('workspace.processHint')}
            </p>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <ChatMessage key={message.id} message={message} showThoughtChain compact />
            ))}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      <div className="flex-shrink-0 p-2.5 border-t border-white/40 bg-white/40 backdrop-blur-md">
        <ChatInputArea
          onSend={handleSendMessage}
          disabled={isStreaming}
          placeholder={
            currentAgent
              ? t('workspace.chatPlaceholder', { name: currentAgent.displayName })
              : t('workspace.selectExpertFirst')
          }
          suggestions={suggestions}
          compact
        />
      </div>
    </div>
  );
}
