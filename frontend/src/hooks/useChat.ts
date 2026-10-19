/**
 * 聊天 Hook - 增强版
 * 参考: LangGraph 的可靠执行模式
 * https://www.langchain.com/langgraph
 *
 * 功能:
 * - 自动重试
 * - 错误恢复
 * - 消息重新生成
 * - 消息编辑
 */

import { useCallback, useRef } from 'react';
import { useChatStore } from '@/store/chatStore';
import { useAgentStore } from '@/store/agentStore';
import { useSettingsStore } from '@/store/settingsStore';
import { useWorkspaceStore } from '@/store/workspaceStore';
import { streamMessage, analyzeIntent } from '@/services/chatService';
import { retryWithBackoff, globalRetryManager, RetryResult } from '@/services/retryService';
import type { Message, ChatRequest } from '@/types';
import { parseMindMap, toMarkdownTree } from '@/utils/mindMap';
import { getLlmRequestOverrides } from '@/utils/llmRequest';

export function useChat() {
  const {
    messages,
    currentSession,
    isStreaming,
    streamingMessageId,
    addMessage,
    updateMessage,
    updateMessageMetadata,
    deleteMessage,
    setStreamingMessageId,
    setIsStreaming,
    appendToMessage,
    setMessageStatus,
  } = useChatStore();

  const { activeAgent, setActiveAgent, getActiveAgent, agents } = useAgentStore();
  const {
    streamEnabled,
    model,
    modelProvider,
    enableWebSearch,
    enableKnowledgeBase,
    enableRetryOnError,
    maxRetries,
  } = useSettingsStore();

  const abortControllerRef = useRef<AbortController | null>(null);
  const currentRequestRef = useRef<ChatRequest | null>(null);

  /**
   * 发送消息（带重试机制）
   */
  const sendMessage = useCallback(
    async (content: string, agentId?: string, retryCount: number = 0) => {
      // 添加用户消息
      const userMessage: Message = {
        id: `user-${Date.now()}-${retryCount}`,
        role: 'user',
        content,
        timestamp: new Date().toISOString(),
      };
      addMessage(userMessage);

      // 创建 AI 消息占位符
      const agent = agentId
        ? agents.find((a) => a.id === agentId)
        : getActiveAgent();
      const aiMessageId = `ai-${Date.now()}-${retryCount}`;
      const aiMessage: Message = {
        id: aiMessageId,
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
        agentName: agent?.displayName,
        agentId: agentId || activeAgent,
        status: 'streaming',
        metadata: {
          retryCount,
          originalContent: content,
        },
      };
      addMessage(aiMessage);
      setStreamingMessageId(aiMessageId);
      setIsStreaming(true);

      // 构建请求：auto / juben_conductor 不传 agent_id，由后端 Conductor 编排
      const llm = getLlmRequestOverrides();
      const resolvedAgentId = agentId || activeAgent;
      const isAutoMode =
        !resolvedAgentId ||
        resolvedAgentId === 'auto' ||
        resolvedAgentId === 'juben_conductor';
      const request: ChatRequest = {
        input: content,
        user_id: localStorage.getItem('userId') || 'default-user',
        session_id: currentSession || undefined,
        project_id:
          localStorage.getItem('dramaId') ||
          localStorage.getItem('projectId') ||
          undefined,
        model_provider: llm.model_provider || modelProvider,
        model: llm.model || model,
        api_key: llm.api_key,
        base_url: llm.base_url,
        enable_web_search: enableWebSearch,
        enable_knowledge_base: enableKnowledgeBase,
        ...(isAutoMode ? {} : { agent_id: resolvedAgentId }),
      };
      currentRequestRef.current = request;

      // Initialize result with default values for error handling
      let result: RetryResult<{ success: boolean }> = {
        data: null,
        error: null,
        retryCount: 0,
        succeeded: false,
      };

      try {
        // 使用重试机制发送请求
        result = await retryWithBackoff(
          async () => {
            console.log('[useChat] Starting retryWithBackoff, retryCount:', retryCount);

            // 自动编排模式由后端 Conductor 决策；仅在用户已选具体专家且未指定时才做前端意图切换
            const shouldAutoSwitchAgent =
              !agentId &&
              retryCount === 0 &&
              activeAgent !== 'auto' &&
              activeAgent !== 'juben_conductor';
            if (shouldAutoSwitchAgent) {
              console.log('[useChat] Calling analyzeIntent...');
              const intentResult = await analyzeIntent(content);
              console.log('[useChat] analyzeIntent completed:', intentResult);
              const suggestedAgent = intentResult.suggestedAgent;
              if (suggestedAgent && suggestedAgent !== activeAgent) {
                console.log('[useChat] Auto-switching to suggested agent:', suggestedAgent);
                setActiveAgent(suggestedAgent);
              }
            }

            return new Promise<{ success: boolean }>((resolve, reject) => {
              if (streamEnabled) {
                // 流式响应
                let fullContent = '';
                let hasError = false;
                let errorMessage = '';

                const close = streamMessage(
                  request,
                  (chunk) => {
                    fullContent += chunk;
                    console.log('[useChat] appendToMessage called with:', chunk.substring(0, 50));
                    appendToMessage(aiMessageId, chunk);
                  },
                  (event) => {
                    console.log('[useChat] Received event:', event.event, event.data);

                    // 处理系统事件 - 每次追加一个新事件
                    if (event.event === 'system' && event.data?.content) {
                      updateMessageMetadata(aiMessageId, () => ({
                        systemEvents: [{ content: event.data.content, timestamp: event.timestamp }]
                      }));
                    }

                    // 处理计费事件
                    if (event.event === 'billing' && event.data?.content) {
                      updateMessage(aiMessageId, {
                        metadata: {
                          billing: event.data.content,
                        },
                      });
                    }

                    // 处理工具事件 - 每次追加一个新事件
                    if (event.event.startsWith('tool_')) {
                      updateMessageMetadata(aiMessageId, () => ({
                        toolEvents: [{ event: event.event, data: event.data, timestamp: event.timestamp }]
                      }));
                    }

                    // 编排事件：路由 / 子专家 / 交接
                    if (
                      event.event === 'agent_decision' ||
                      event.event === 'subagent' ||
                      event.event === 'handoff' ||
                      event.event === 'composition'
                    ) {
                      const meta = event.data?.metadata || {};
                      updateMessageMetadata(aiMessageId, (current) => ({
                        orchestrationEvents: [
                          ...((current as any)?.orchestrationEvents || []),
                          {
                            event: event.event,
                            data: event.data,
                            timestamp: event.timestamp,
                          },
                        ],
                        activeAgent:
                          meta.active_agent ||
                          meta.to_agent ||
                          (current as any)?.activeAgent,
                      }));
                      if (event.event === 'handoff' && meta.to_agent) {
                        const to = String(meta.to_agent);
                        if (to === 'juben_conductor' || to === 'auto') {
                          setActiveAgent('auto');
                        } else {
                          setActiveAgent(to);
                        }
                      }
                      if (event.event === 'agent_decision' && meta.active_agent) {
                        // 仅展示，不强制切 UI（除非来自 session handoff 路由）
                        const src = meta.route_source || event.data?.content;
                        // content 可能是 JSON 字符串
                      }
                    }

                    // 处理错误事件
                    if (event.event === 'error') {
                      hasError = true;
                      errorMessage = event.data.error || event.data.content || '未知错误';
                      updateMessage(aiMessageId, {
                        metadata: {
                          error: errorMessage,
                        },
                      });
                    }
                  },
                  () => {
                    if (hasError) {
                      reject(new Error(errorMessage));
                    } else {
                      setMessageStatus(aiMessageId, 'complete');
                      let workspaceContent = fullContent;
                      const mindMapData = parseMindMap(fullContent);
                      if (mindMapData) {
                        workspaceContent = toMarkdownTree(mindMapData);
                        updateMessage(aiMessageId, {
                          content: workspaceContent,
                        });
                        updateMessageMetadata(aiMessageId, (current) => ({
                          ...current,
                          contentType: 'mind_map',
                          mindMapData,
                        }));
                      }

                      // 同步最新AI结果到左侧文档工作区，确保用户可继续保存为Note
                      useWorkspaceStore.getState().setContent({
                        id: `msg_${aiMessageId}`,
                        type: mindMapData ? 'mindmap' : 'document',
                        title: `${agent?.displayName || activeAgent} 生成结果`,
                        content: workspaceContent,
                        metadata: {
                          agentId: agentId || activeAgent,
                          agentName: agent?.displayName,
                          timestamp: new Date().toISOString(),
                        },
                      });

                      resolve({ success: true });
                    }
                    setIsStreaming(false);
                    setStreamingMessageId(null);
                  },
                  (error) => {
                    hasError = true;
                    errorMessage = error.message;
                    reject(error);
                  }
                );

                abortControllerRef.current = {
                  abort: close,
                } as any;
              } else {
                // 非流式响应
                resolve({ success: true });
                setIsStreaming(false);
                setStreamingMessageId(null);
              }
            });
          },
          {
            maxRetries: enableRetryOnError ? maxRetries : 0,
            initialDelay: 1000,
            isRetriable: (error) => {
              // 网络错误、超时、限流可重试
              const errorMessage = error.message.toLowerCase();
              return (
                errorMessage.includes('network') ||
                errorMessage.includes('timeout') ||
                errorMessage.includes('rate limit') ||
                errorMessage.includes('fetch')
              );
            },
          }
        );

        if (!result.succeeded || result.error) {
          throw result.error || new Error('Request failed');
        }

        // 成功后重置重试计数
        if (currentRequestRef.current) {
          const retryKey = `${currentRequestRef.current.user_id}-${currentRequestRef.current.session_id}`;
          globalRetryManager.resetRetryCount(retryKey);
        }
      } catch (error) {
        const errorObj = error as Error;
        const retryCount = result.retryCount || 0;
        setMessageStatus(aiMessageId, 'error');
        updateMessage(aiMessageId, {
          content: `\`\`\`\n❌ 错误: ${errorObj.message}\n\n${retryCount > 0 ? `已重试 ${retryCount} 次` : ''}\n\`\`\``,
          metadata: {
            ...aiMessage.metadata,
            error: errorObj.message,
            retryCount,
            canRetry: retryCount < 3,
          },
        });
        setIsStreaming(false);
        setStreamingMessageId(null);
      }
    },
    [
      activeAgent,
      currentSession,
      streamEnabled,
      addMessage,
      updateMessage,
      setStreamingMessageId,
      setIsStreaming,
      setActiveAgent,
      appendToMessage,
      setMessageStatus,
      getActiveAgent,
      agents,
      modelProvider,
      enableWebSearch,
      enableKnowledgeBase,
      enableRetryOnError,
      maxRetries,
    ]
  );

  /**
   * 重新生成消息
   */
  const regenerateMessage = useCallback(
    async (messageId: string) => {
      const message = messages.find(m => m.id === messageId);
      if (!message || message.role !== 'assistant') {
        return;
      }

      // 找到对应的用户消息
      const messageIndex = messages.findIndex(m => m.id === messageId);
      const userMessage = messages[messageIndex - 1];

      if (!userMessage || userMessage.role !== 'user') {
        console.warn('Cannot find user message to regenerate');
        return;
      }

      // 删除旧的 AI 消息
      deleteMessage(messageId);

      // 重新发送
      await sendMessage(userMessage.content, message.agentId, (message.metadata?.retryCount || 0) + 1);
    },
    [messages, sendMessage, deleteMessage]
  );

  /**
   * 编辑消息
   */
  const editMessage = useCallback(
    async (messageId: string, newContent: string) => {
      const message = messages.find(m => m.id === messageId);
      if (!message) {
        return;
      }

      // 更新消息内容
      updateMessage(messageId, { content: newContent });

      // 如果是用户消息，删除后续的所有消息并重新生成
      if (message.role === 'user') {
        const messageIndex = messages.findIndex(m => m.id === messageId);
        const messagesToDelete = messages.slice(messageIndex + 1);

        // 删除后续消息
        for (const msg of messagesToDelete) {
          deleteMessage(msg.id);
        }

        // 重新发送
        await sendMessage(newContent, undefined, 0);
      }
    },
    [messages, updateMessage, deleteMessage, sendMessage]
  );

  /**
   * 停止流式响应
   */
  const stopStreaming = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
    setStreamingMessageId(null);
  }, [setIsStreaming, setStreamingMessageId]);

  /**
   * 清除消息
   */
  const clearMessages = useCallback(() => {
    const { clearMessages: clear } = useChatStore.getState();
    clear();
  }, []);

  /**
   * 从消息创建分支
   */
  const createBranch = useCallback(
    (messageId: string) => {
      const messageIndex = messages.findIndex(m => m.id === messageId);
      if (messageIndex === -1) {
        return;
      }

      // 保留到此消息为止的历史
      const branchMessages = messages.slice(0, messageIndex + 1);

      // 清空当前消息，设置分支消息
      const { setMessages } = useChatStore.getState();
      setMessages(branchMessages);

      // 保存分支到本地存储
      try {
        const branchKey = `juben_chat_branch_${messageId}`;
        localStorage.setItem(branchKey, JSON.stringify(branchMessages));
      } catch (error) {
        console.warn('保存分支到本地存储失败:', error);
      }
    },
    [messages]
  );

  return {
    messages,
    isStreaming,
    streamingMessageId,
    activeAgent,
    sendMessage,
    regenerateMessage,
    editMessage,
    stopStreaming,
    clearMessages,
    createBranch,
    setActiveAgent,
    deleteMessage,
  };
}
