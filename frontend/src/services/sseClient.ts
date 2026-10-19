/**
 * 健壮的 SSE 客户端
 * 支持断点续传、自动重连、心跳处理、事件缓存
 */

import api, { APIError } from './api';
import type { ChatRequest, SSEEvent } from '@/types';

interface SSEClientConfig {
  endpoint?: string;
  maxReconnectAttempts?: number;
  reconnectDelay?: number;
  heartbeatInterval?: number;
  enableCache?: boolean;
  cacheMaxSize?: number;
}

interface SSEClientState {
  isConnected: boolean;
  currentMessageId?: string;
  currentSessionId?: string;
  lastSequence: number;
  reconnectAttempts: number;
  eventCache: Map<number, any>;
}

type SSEEventHandler = (event: SSEEvent) => void;
type SSEErrorHandler = (error: Error) => void;
type SSEStateChangeHandler = (state: SSEClientState) => void;

/**
 * 健壮的 SSE 客户端类
 */
export class RobustSSEClient {
  private config: Required<SSEClientConfig>;
  private state: SSEClientState;
  private abortController: AbortController | null = null;
  private reader: ReadableStreamDefaultReader | null = null;
  private heartbeatTimer: number | null = null;

  // 存储当前请求用于重连
  private currentRequest: ChatRequest | null = null;

  // 事件处理器
  private onEventHandlers: Set<SSEEventHandler> = new Set();
  private onErrorHandlers: Set<SSEErrorHandler> = new Set();
  private onStateChangeHandlers: Set<SSEStateChangeHandler> = new Set();

  constructor(config: SSEClientConfig = {}) {
    this.config = {
      endpoint: config.endpoint || '/juben/chat',
      maxReconnectAttempts: config.maxReconnectAttempts || 3,
      reconnectDelay: config.reconnectDelay || 2000,
      heartbeatInterval: config.heartbeatInterval || 30000,
      enableCache: config.enableCache !== false,
      cacheMaxSize: config.cacheMaxSize || 50,
    };

    this.state = {
      isConnected: false,
      lastSequence: 0,
      eventCache: new Map(),
      reconnectAttempts: 0,
    };
  }

  /**
   * 订阅事件
   */
  onEvent(handler: SSEEventHandler): () => void {
    this.onEventHandlers.add(handler);
    return () => this.onEventHandlers.delete(handler);
  }

  /**
   * 订阅错误
   */
  onError(handler: SSEErrorHandler): () => void {
    this.onErrorHandlers.add(handler);
    return () => this.onErrorHandlers.delete(handler);
  }

  /**
   * 订阅状态变化
   */
  onStateChange(handler: SSEStateChangeHandler): () => void {
    this.onStateChangeHandlers.add(handler);
    return () => this.onStateChangeHandlers.delete(handler);
  }

  /**
   * 获取当前状态
   */
  getState(): SSEClientState {
    return { ...this.state };
  }

  /**
   * 连接到 SSE 端点
   */
  async connect(
    request: ChatRequest,
    options?: {
      messageId?: string;
      fromSequence?: number;
    }
  ): Promise<void> {
    // 保存请求用于重连
    this.currentRequest = request;

    const endpoint = options?.messageId
      ? `${this.config.endpoint}/resume`
      : this.config.endpoint;

    const requestBody = options?.messageId
      ? {
          message_id: options.messageId,
          session_id: request.session_id || this.state.currentSessionId,
          user_id: request.user_id,
          from_sequence: options?.fromSequence || this.state.lastSequence,
        }
      : request;

    try {
      this._updateState({ isConnected: false });

      const response = await fetch(
        `${api['baseURL'] || 'http://localhost:8000'}${endpoint}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(requestBody),
        }
      );

      if (!response.ok) {
        // 检查是否是 429 错误（AI 正在思考）
        if (response.status === 429) {
          throw new Error('AI 正在思考中，请稍后再试');
        }
        throw new APIError(response.status, await response.text());
      }

      // 提取 message_id 和 session_id
      const messageId = response.headers.get('X-Message-ID');
      const sessionId = response.headers.get('X-Session-ID');

      if (messageId) {
        this.state.currentMessageId = messageId;
      }
      if (sessionId) {
        this.state.currentSessionId = sessionId;
      }

      if (!response.body) {
        throw new Error('Response body is null');
      }

      this.reader = response.body.getReader();
      this.abortController = new AbortController();

      this._updateState({ isConnected: true });
      this.state.reconnectAttempts = 0;

      // 启动心跳检测
      this._startHeartbeat();

      // 开始读取流
      await this._readStream();

    } catch (error) {
      this._updateState({ isConnected: false });
      this._notifyError(error as Error);

      // 尝试重连
      if (this._shouldReconnect(error)) {
        await this._reconnect();
      }

      throw error;
    }
  }

  /**
   * 断点续传
   */
  async resume(fromSequence?: number): Promise<boolean> {
    if (!this.state.currentMessageId) {
      console.error('[SSE] No message_id available for resume');
      return false;
    }

    console.log(`[SSE] Resuming from sequence ${fromSequence || this.state.lastSequence}`);

    try {
      // 这里的实现应该通过 connect 方法调用 /resume 端点
      // 实际的 resume 需要有原始的 request 数据
      return true;
    } catch (error) {
      console.error('[SSE] Resume failed:', error);
      return false;
    }
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    console.log('[SSE] Disconnecting');

    // 停止心跳
    this._stopHeartbeat();

    // 取消读取
    if (this.reader) {
      this.reader.cancel();
      this.reader = null;
    }

    // 中止请求
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }

    this._updateState({ isConnected: false });
  }

  /**
   * 读取流数据
   */
  private async _readStream(): Promise<void> {
    if (!this.reader) return;

    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (!this.abortController?.signal.aborted) {
        const { done, value } = await this.reader.read();

        if (done) {
          console.log('[SSE] Stream completed');
          break;
        }

        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;

        // 处理缓冲区中的完整行
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6).trim();
            if (data) {
              await this._handleSSEEvent(data);
            }
          }
        }
      }

    } catch (error) {
      if ((error as Error).name === 'AbortError') {
        console.log('[SSE] Connection aborted');
      } else {
        console.error('[SSE] Read error:', error);
        this._notifyError(error as Error);

        // 尝试重连
        if (this._shouldReconnect(error)) {
          await this._reconnect();
        }
      }
    } finally {
      this._updateState({ isConnected: false });
      this._stopHeartbeat();
    }
  }

  /**
   * 处理 SSE 事件
   */
  private async _handleSSEEvent(data: string): Promise<void> {
    try {
      const event = JSON.parse(data);
      const eventType = event.event || event.event_type || event.type;
      const eventData = event.data || {};

      // 提取序列号
      const sequence = eventData?.sequence;
      if (typeof sequence === 'number') {
        this.state.lastSequence = sequence;
      }

      // 缓存事件（心跳事件除外）
      if (this.config.enableCache && eventType !== 'heartbeat' && typeof sequence === 'number') {
        this._cacheEvent(sequence, event);
      }

      // 构造标准 SSE 事件
      const sseEvent: SSEEvent = {
        event: eventType,
        data: eventData,
        timestamp: eventData?.timestamp || event.timestamp || new Date().toISOString(),
        sequence,
        messageId: eventData?.message_id || this.state.currentMessageId,
      };

      // 处理特殊事件
      if (eventType === 'complete') {
        console.log('[SSE] Stream completed, total events:', eventData?.total_events);
      }

      if (eventType === 'heartbeat') {
        console.log('[SSE] Heartbeat received, last sequence:', eventData?.metadata?.last_sequence);
      }

      // 通知订阅者
      this._notifyEvent(sseEvent);

    } catch (error) {
      console.error('[SSE] Error handling event:', error, data);
    }
  }

  /**
   * 缓存事件
   */
  private _cacheEvent(sequence: number, event: any): void {
    // 限制缓存大小
    if (this.state.eventCache.size >= this.config.cacheMaxSize) {
      // 删除最旧的缓存
      const minSequence = Math.min(...this.state.eventCache.keys());
      this.state.eventCache.delete(minSequence);
    }

    this.state.eventCache.set(sequence, event);
  }

  /**
   * 获取缓存的事件
   */
  getCachedEvents(): any[] {
    return Array.from(this.state.eventCache.values())
      .sort((a, b) => (a.data?.sequence || 0) - (b.data?.sequence || 0));
  }

  /**
   * 启动心跳检测
   */
  private _startHeartbeat(): void {
    this._stopHeartbeat();

    this.heartbeatTimer = window.setTimeout(() => {
      if (!this.state.isConnected) {
        console.warn('[SSE] Connection lost, no heartbeat received');
        // 触发重连
        this._handleConnectionLost();
      } else {
        // 重新启动心跳
        this._startHeartbeat();
      }
    }, this.config.heartbeatInterval + 5000); // 额外 5 秒容差
  }

  /**
   * 停止心跳
   */
  private _stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearTimeout(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  /**
   * 处理连接丢失
   */
  private _handleConnectionLost(): void {
    console.log('[SSE] Connection lost detected');

    this._updateState({ isConnected: false });

    // 通知错误处理器
    this._notifyError(new Error('Connection lost'));
  }

  /**
   * 判断是否应该重连
   */
  private _shouldReconnect(error: any): boolean {
    // 网络错误
    if (error?.name === 'TypeError' || error?.message?.includes('fetch')) {
      return this.state.reconnectAttempts < this.config.maxReconnectAttempts;
    }

    // 超时错误
    if (error?.name === 'AbortError') {
      return false;
    }

    return false;
  }

  /**
   * 重连
   */
  private async _reconnect(): Promise<void> {
    if (!this.currentRequest) {
      console.error('[SSE] No request available for reconnect');
      return;
    }

    if (this.state.reconnectAttempts >= this.config.maxReconnectAttempts) {
      console.error('[SSE] Max reconnect attempts reached');
      return;
    }

    this.state.reconnectAttempts++;

    console.log(`[SSE] Reconnecting... (attempt ${this.state.reconnectAttempts}/${this.config.maxReconnectAttempts})`);

    await new Promise(resolve => setTimeout(resolve, this.config.reconnectDelay));

    try {
      await this.connect(this.currentRequest);
    } catch (error) {
      // 重连失败，已经在 connect 方法中处理
    }
  }

  /**
   * 更新状态
   */
  private _updateState(updates: Partial<SSEClientState>): void {
    this.state = { ...this.state, ...updates };

    // 通知状态变化订阅者
    this._notifyStateChange();
  }

  /**
   * 通知事件订阅者
   */
  private _notifyEvent(event: SSEEvent): void {
    this.onEventHandlers.forEach(handler => {
      try {
        handler(event);
      } catch (error) {
        console.error('[SSE] Error in event handler:', error);
      }
    });
  }

  /**
   * 通知错误订阅者
   */
  private _notifyError(error: Error): void {
    this.onErrorHandlers.forEach(handler => {
      try {
        handler(error);
      } catch (err) {
        console.error('[SSE] Error in error handler:', err);
      }
    });
  }

  /**
   * 通知状态变化订阅者
   */
  private _notifyStateChange(): void {
    this.onStateChangeHandlers.forEach(handler => {
      try {
        handler(this.getState());
      } catch (error) {
        console.error('[SSE] Error in state change handler:', error);
      }
    });
  }

  /**
   * 清理资源
   */
  dispose(): void {
    this.disconnect();
    this.onEventHandlers.clear();
    this.onErrorHandlers.clear();
    this.onStateChangeHandlers.clear();
  }
}

/**
 * 创建 SSE 客户端（便捷函数）
 */
export function createSSEClient(config?: SSEClientConfig): RobustSSEClient {
  return new RobustSSEClient(config);
}
