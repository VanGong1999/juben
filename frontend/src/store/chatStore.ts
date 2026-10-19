/**
 * 聊天状态管理 Store
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type { Message, MessageStatus, ProcessStepMeta, Thought } from '@/types';
import { sendMessageToAgent } from '@/services/chatService';
import { useWorkspaceStore } from '@/store/workspaceStore';
import { saveDramaArtifact } from '@/services/dramaService';
import { getAgentById } from '@/config/agents';
import { mergeProcessStep } from '@/utils/agentStreamEvents';

interface ChatState {
  messages: Message[];
  currentSession: string | null;
  streamingMessageId: string | null;
  streamingMessage: string | null;  // 新增：流式消息内容
  isStreaming: boolean;
  thoughtChain: Thought[];  // 新增：思维链

  // Actions
  addMessage: (message: Message) => void;
  updateMessage: (id: string, updates: Partial<Message>) => void;
  updateMessageMetadata: (id: string, metadataUpdater: (currentMetadata: any) => any) => void;
  deleteMessage: (id: string) => void;
  clearMessages: () => void;
  setMessages: (messages: Message[]) => void;

  setCurrentSession: (sessionId: string) => void;
  clearCurrentSession: () => void;
  newSession: () => void;

  setStreamingMessageId: (id: string | null) => void;
  setIsStreaming: (isStreaming: boolean) => void;
  setStreamingMessage: (content: string | null) => void;  // 新增
  setThoughtChain: (thoughts: Thought[]) => void;  // 新增
  appendThought: (thought: Thought) => void;  // 新增

  // Streaming helpers
  appendToMessage: (id: string, content: string) => void;
  setMessageStatus: (id: string, status: MessageStatus) => void;

  // 新增：发送消息
  sendMessage: (content: string, agentId: string) => Promise<void>;
}

export const useChatStore = create<ChatState>()(
  devtools(
    (set, get) => ({
      // Initial state
      messages: [],
      currentSession: null,
      streamingMessageId: null,
      streamingMessage: null,
      isStreaming: false,
      thoughtChain: [],

      // Message actions
      addMessage: (message) =>
        set((state) => ({
          messages: [...state.messages, message],
        })),

      updateMessage: (id, updates) =>
        set((state) => ({
          messages: state.messages.map((msg) =>
            msg.id === id ? { ...msg, ...updates } : msg
          ),
        })),

      // 函数式更新 metadata（用于追加系统事件等）
      updateMessageMetadata: (id, metadataUpdater) =>
        set((state) => {
          const updatedMessages = state.messages.map((msg) =>
            msg.id === id
              ? (() => {
                  const currentMetadata = msg.metadata || {};
                  const newMetadataPart = metadataUpdater(currentMetadata);

                  // 深度合并，特别处理数组类型字段
                  const mergedMetadata: any = { ...currentMetadata };

                  // 对 systemEvents 进行特殊处理 - 追加而不是覆盖
                  if (newMetadataPart.systemEvents) {
                    mergedMetadata.systemEvents = [
                      ...(currentMetadata.systemEvents || []),
                      ...newMetadataPart.systemEvents
                    ];
                  }

                  // 对 toolEvents 进行特殊处理 - 追加而不是覆盖
                  if (newMetadataPart.toolEvents) {
                    mergedMetadata.toolEvents = [
                      ...(currentMetadata.toolEvents || []),
                      ...newMetadataPart.toolEvents
                    ];
                  }

                  // 其他字段直接覆盖
                  Object.keys(newMetadataPart).forEach(key => {
                    if (key !== 'systemEvents' && key !== 'toolEvents') {
                      mergedMetadata[key] = newMetadataPart[key];
                    }
                  });

                  console.log('[chatStore] updateMessageMetadata:', id, 'systemEvents count:', mergedMetadata.systemEvents?.length || 0);
                  return { ...msg, metadata: mergedMetadata };
                })()
              : msg
          );
          return { messages: updatedMessages };
        }),

      deleteMessage: (id) =>
        set((state) => ({
          messages: state.messages.filter((msg) => msg.id !== id),
        })),

      clearMessages: () => set({ messages: [] }),

      setMessages: (messages) => set({ messages }),

      // Session actions
      setCurrentSession: (sessionId) => set({ currentSession: sessionId }),
      clearCurrentSession: () => set({ currentSession: null }),
      newSession: () => set({ messages: [], currentSession: null, thoughtChain: [] }),

      // Streaming actions
      setStreamingMessageId: (id) => set({ streamingMessageId: id }),
      setIsStreaming: (isStreaming) => set({ isStreaming }),

      // 新增：流式消息和思维链
      setStreamingMessage: (content) => set({ streamingMessage: content }),
      setThoughtChain: (thoughts) => set({ thoughtChain: thoughts }),
      appendThought: (thought) =>
        set((state) => ({
          thoughtChain: [...state.thoughtChain, thought],
        })),

      // Streaming helpers
      appendToMessage: (id, content) => {
        console.log('[chatStore] appendToMessage:', id, content.substring(0, 50));
        set((state) => {
          const updatedMessages = state.messages.map((msg) =>
            msg.id === id ? { ...msg, content: msg.content + content } : msg
          );
          const updatedMsg = updatedMessages.find(m => m.id === id);
          console.log('[chatStore] Updated message content:', updatedMsg?.content?.substring(0, 50) || 'empty');
          return { messages: updatedMessages };
        });
      },

      setMessageStatus: (id, status) =>
        set((state) => ({
          messages: state.messages.map((msg) =>
            msg.id === id ? { ...msg, status } : msg
          ),
        })),

      // 新增：发送消息
      sendMessage: async (content: string, agentId: string) => {
        const state = get();
        const agentMeta = getAgentById(agentId);

        // 添加用户消息
        const userMessage: Message = {
          id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          role: 'user',
          content,
          timestamp: new Date().toISOString(),
          status: 'complete',
        };
        state.addMessage(userMessage);

        // 流式助手占位（过程 + 正文都挂在这条上）
        const assistantId = `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        const processSteps: ProcessStepMeta[] = [];
        state.addMessage({
          id: assistantId,
          role: 'assistant',
          content: '',
          timestamp: new Date().toISOString(),
          status: 'streaming',
          agentName: agentMeta?.displayName,
          agentId,
          metadata: {
            agentId,
            processSteps: [],
            thoughtChain: [],
          },
        });

        state.setThoughtChain([]);
        state.setStreamingMessage('');
        state.setStreamingMessageId(assistantId);
        state.setIsStreaming(true);

        // 保证有稳定 session_id（新对话自动生成）
        if (!get().currentSession) {
          set({
            currentSession: `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          });
        }
        const sessionId = get().currentSession as string;

        const pushStep = (step: ProcessStepMeta) => {
          processSteps.push(step);
          state.updateMessageMetadata(assistantId, () => ({
            processSteps: [...processSteps],
          }));
        };

        const replaceSteps = (next: ProcessStepMeta[]) => {
          processSteps.length = 0;
          processSteps.push(...next);
          state.updateMessageMetadata(assistantId, () => ({
            processSteps: [...processSteps],
          }));
        };

        try {
          await sendMessageToAgent(
            content,
            agentId,
            (chunk: string, isThought: boolean) => {
              if (isThought) return;
              const current = get().streamingMessage || '';
              const next = current + chunk;
              state.setStreamingMessage(next);
              state.updateMessage(assistantId, { content: next, status: 'streaming' });
            },
            (thought: Thought) => {
              state.appendThought(thought);
              pushStep({
                id: `th-${thought.step}`,
                kind: thought.type || 'thinking',
                title: thought.content.slice(0, 160),
                detail: thought.content.length > 160 ? thought.content : undefined,
                status: 'done',
                timestamp: thought.timestamp,
              });
              state.updateMessageMetadata(assistantId, () => ({
                thoughtChain: get().thoughtChain,
              }));
            },
            (ev) => {
              replaceSteps(mergeProcessStep(processSteps as any, ev) as ProcessStepMeta[]);
              if (ev.event === 'system') {
                state.updateMessageMetadata(assistantId, () => ({
                  systemEvents: [
                    {
                      content:
                        typeof ev.data === 'string'
                          ? ev.data
                          : String(ev.data?.content || ''),
                      timestamp: ev.timestamp,
                    },
                  ],
                }));
              }
              if (String(ev.event).startsWith('tool')) {
                state.updateMessageMetadata(assistantId, () => ({
                  toolEvents: [{ event: ev.event, data: ev.data, timestamp: ev.timestamp }],
                }));
              }
            },
            sessionId
          );

          const finalContent = get().streamingMessage || '';
          state.updateMessage(assistantId, {
            content: finalContent,
            status: 'complete',
          });
          state.updateMessageMetadata(assistantId, () => ({
            processSteps: [...processSteps],
            thoughtChain: get().thoughtChain,
          }));

          const assistantMessage = get().messages.find((m) => m.id === assistantId) || {
            id: assistantId,
            role: 'assistant' as const,
            content: finalContent,
            timestamp: new Date().toISOString(),
            status: 'complete' as const,
            metadata: { agentId, processSteps, thoughtChain: get().thoughtChain },
          };

          // 更新工作区内容
          const assistantContent = assistantMessage.content;
          if (assistantContent) {
            const titleBase = agentMeta?.displayName || agentId;
            useWorkspaceStore.getState().setContent({
              id: assistantMessage.id,
              type: 'document',
              title: `${titleBase} 生成结果`,
              content: assistantContent,
              metadata: {
                agentId,
                agentName: titleBase,
                timestamp: assistantMessage.timestamp,
              },
            });

            // 绑定作品时：自动归档专家产物到该剧 Artifacts
            const dramaId =
              localStorage.getItem('dramaId') ||
              localStorage.getItem('projectId') ||
              '';
            if (dramaId && assistantContent.trim().length >= 40) {
              const skipAgents = new Set([
                'websearch',
                'text_splitter',
                'text_truncator',
                'output_formatter',
                'file_reference',
                'series_name_extractor',
              ]);
              if (!skipAgents.has(agentId)) {
                void saveDramaArtifact(dramaId, {
                  content: assistantContent,
                  agent_id: agentId,
                  agent_name: titleBase,
                  category: agentMeta?.category || '',
                  title: `${titleBase} · ${new Date().toLocaleString('zh-CN', {
                    month: 'numeric',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}`,
                  user_prompt: content.slice(0, 500),
                  sync_bible: true,
                })
                  .then(() => {
                    window.dispatchEvent(
                      new CustomEvent('drama-artifacts-updated', { detail: { dramaId } })
                    );
                  })
                  .catch((err) => {
                    console.warn('[chatStore] 归档产物失败', err);
                  });
              }
            }
          }
        } catch (error) {
          console.error('[chatStore] Send message error:', error);
          state.updateMessage(assistantId, {
            content:
              get().streamingMessage ||
              `发送失败: ${error instanceof Error ? error.message : '未知错误'}`,
            status: 'error',
          });
        } finally {
          state.setIsStreaming(false);
          state.setStreamingMessage(null);
          state.setStreamingMessageId(null);

          // 对话结束后刷新作品面板：若专家在对话里用 save_drama_part 直接改了小传/大纲/剧本，
          // 左侧 artifacts / bible / outline / episodes 需要重新拉取。
          const dramaId =
            localStorage.getItem('dramaId') || localStorage.getItem('projectId') || '';
          if (dramaId) {
            window.dispatchEvent(
              new CustomEvent('drama-artifacts-updated', { detail: { dramaId } })
            );
          }
        }
      },
    }),
    { name: 'ChatStore' }
  )
);
