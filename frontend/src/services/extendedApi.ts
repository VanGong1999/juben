/**
 * 扩展的API服务
 * 包含所有后端API接口的前端调用函数
 */

import api, { APIError } from './api';
import type { ChatRequest, SSEEvent } from '@/types';

// ==================== 模型相关接口 ====================

/**
 * 获取可用模型列表
 */
export async function getModels(provider: string = 'deepseek') {
  try {
    return await api.get<{
      success: boolean;
      provider: string;
      models: string[];
      default_model: string;
      purpose_models: Record<string, string>;
      total_count: number;
    }>(`/juben/models?provider=${provider}`);
  } catch (error) {
    if (error instanceof APIError) {
      throw new Error(`获取模型列表失败: ${error.message}`);
    }
    throw error;
  }
}

/**
 * 获取推荐模型
 */
export async function getRecommendedModel(purpose: string = 'default') {
  try {
    return await api.get<{
      success: boolean;
      purpose: string;
      recommended_model: {
        name: string;
        display_name: string;
        description: string;
        max_tokens: number;
        thinking_enabled: boolean;
      };
    }>(`/juben/models/recommend?purpose=${purpose}`);
  } catch (error) {
    if (error instanceof APIError) {
      throw new Error(`获取推荐模型失败: ${error.message}`);
    }
    throw error;
  }
}

/**
 * 按类型获取模型列表
 */
export async function getModelsByType() {
  try {
    return await api.get<{
      success: boolean;
      models: {
        text: Array<{ name: string; display_name: string; description: string; max_tokens: number }>;
        vision: Array<{ name: string; display_name: string; description: string; max_tokens: number }>;
        image_generation: Array<{ name: string; display_name: string; description: string }>;
        video_generation: Array<{ name: string; display_name: string; description: string }>;
      };
    }>('/juben/models/types');
  } catch (error) {
    if (error instanceof APIError) {
      throw new Error(`获取模型类型失败: ${error.message}`);
    }
    throw error;
  }
}

// ==================== 系统配置接口 ====================

/**
 * 获取系统配置
 */
export async function getSystemConfig() {
  try {
    return await api.get<{
      success: boolean;
      config: Record<string, any>;
    }>('/juben/config');
  } catch (error) {
    if (error instanceof APIError) {
      throw new Error(`获取系统配置失败: ${error.message}`);
    }
    throw error;
  }
}

/**
 * 健康检查
 */
export async function healthCheck() {
  try {
    return await api.get<{
      message: string;
      status: string;
      version: string;
      uptime: string;
      dependencies: Record<string, boolean>;
    }>('/juben/health');
  } catch (error) {
    if (error instanceof APIError) {
      throw new Error(`健康检查失败: ${error.message}`);
    }
    throw error;
  }
}

// ==================== 知识库相关接口 ====================

/**
 * 获取知识库集合列表
 */
export async function getKnowledgeCollections() {
  try {
    return await api.get<{
      success: boolean;
      collections: Array<{
        name: string;
        info: any;
      }>;
    }>('/juben/knowledge/collections');
  } catch (error) {
    if (error instanceof APIError) {
      throw new Error(`获取知识库集合失败: ${error.message}`);
    }
    throw error;
  }
}

/**
 * 知识库搜索
 */
export async function searchKnowledge(query: string, collection: string = 'script_segments') {
  try {
    return await api.post<{
      success: boolean;
      search_result: any;
    }>('/juben/knowledge/search', { query, collection });
  } catch (error) {
    if (error instanceof APIError) {
      throw new Error(`知识库搜索失败: ${error.message}`);
    }
    throw error;
  }
}

// ==================== 网络搜索接口 ====================

/**
 * 网络搜索
 */
export async function searchWeb(query: string, count: number = 5) {
  try {
    return await api.post<{
      success: boolean;
      search_result: any;
    }>('/juben/search/web', { query, count });
  } catch (error) {
    if (error instanceof APIError) {
      throw new Error(`网络搜索失败: ${error.message}`);
    }
    throw error;
  }
}

// ==================== Agent 专用接口 ====================

/**
 * 创作助手聊天（流式）
 */
export function streamCreatorChat(
  request: ChatRequest,
  onChunk: (chunk: string) => void,
  onEvent: (event: SSEEvent) => void,
  onComplete: () => void,
  onError: (error: Error) => void
): () => void {
  return api.connectSSE(
    '/juben/chat',
    request,
    (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.event_type === 'message' || data.event_type === 'llm_chunk') {
          onChunk(data.data || '');
        }
        onEvent({
          event: data.event_type,
          data: data.data || {},
          timestamp: data.timestamp || new Date().toISOString(),
        });
        if (data.event_type === 'done' || data.event_type === 'complete') {
          onComplete();
        }
      } catch (e) {
        console.error('Error parsing SSE event:', e);
      }
    },
    onError,
    onComplete
  );
}

/**
 * 获取创作助手信息
 */
export async function getCreatorInfo() {
  try {
    return await api.get<{
      success: boolean;
      agent_info: any;
    }>('/juben/creator/info');
  } catch (error) {
    if (error instanceof APIError) {
      throw new Error(`获取创作助手信息失败: ${error.message}`);
    }
    throw error;
  }
}

/**
 * 评估助手聊天（流式）
 */
export function streamEvaluationChat(
  request: ChatRequest,
  onChunk: (chunk: string) => void,
  onEvent: (event: SSEEvent) => void,
  onComplete: () => void,
  onError: (error: Error) => void
): () => void {
  return api.connectSSE(
    '/juben/evaluation/chat',
    request,
    (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.event_type === 'message' || data.event_type === 'llm_chunk') {
          onChunk(data.data || '');
        }
        onEvent({
          event: data.event_type,
          data: data.data || {},
          timestamp: data.timestamp || new Date().toISOString(),
        });
        if (data.event_type === 'done' || data.event_type === 'complete') {
          onComplete();
        }
      } catch (e) {
        console.error('Error parsing SSE event:', e);
      }
    },
    onError,
    onComplete
  );
}

/**
 * 获取评估助手信息
 */
export async function getEvaluationInfo() {
  try {
    return await api.get<{
      success: boolean;
      agent_info: any;
    }>('/juben/evaluation/info');
  } catch (error) {
    if (error instanceof APIError) {
      throw new Error(`获取评估助手信息失败: ${error.message}`);
    }
    throw error;
  }
}

/**
 * 计算评估分数
 */
export async function calculateEvaluationScore(scores: Record<string, number>) {
  try {
    return await api.post<{
      success: boolean;
      scores: Record<string, number>;
      overall_score: number;
      score_level: string;
      level_description: string;
    }>('/juben/evaluation/score', { scores });
  } catch (error) {
    if (error instanceof APIError) {
      throw new Error(`计算评估分数失败: ${error.message}`);
    }
    throw error;
  }
}

/**
 * 网络搜索助手聊天（流式）
 */
export function streamWebSearchChat(
  request: ChatRequest & { query?: string; count?: number },
  onChunk: (chunk: string) => void,
  onEvent: (event: SSEEvent) => void,
  onComplete: () => void,
  onError: (error: Error) => void
): () => void {
  return api.connectSSE(
    '/juben/websearch/chat',
    request,
    (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.event_type === 'message' || data.event_type === 'llm_chunk') {
          onChunk(data.data || '');
        }
        onEvent({
          event: data.event_type,
          data: data.data || {},
          timestamp: data.timestamp || new Date().toISOString(),
        });
        if (data.event_type === 'done' || data.event_type === 'complete') {
          onComplete();
        }
      } catch (e) {
        console.error('Error parsing SSE event:', e);
      }
    },
    onError,
    onComplete
  );
}

/**
 * 获取网络搜索助手信息
 */
export async function getWebSearchInfo() {
  try {
    return await api.get<{
      success: boolean;
      agent_info: any;
    }>('/juben/websearch/info');
  } catch (error) {
    if (error instanceof APIError) {
      throw new Error(`获取网络搜索助手信息失败: ${error.message}`);
    }
    throw error;
  }
}

/**
 * 知识库查询聊天（流式）
 */
export function streamKnowledgeChat(
  request: ChatRequest & { query?: string; collection?: string; top_k?: number },
  onChunk: (chunk: string) => void,
  onEvent: (event: SSEEvent) => void,
  onComplete: () => void,
  onError: (error: Error) => void
): () => void {
  return api.connectSSE(
    '/juben/knowledge/chat',
    request,
    (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.event_type === 'message' || data.event_type === 'llm_chunk') {
          onChunk(data.data || '');
        }
        onEvent({
          event: data.event_type,
          data: data.data || {},
          timestamp: data.timestamp || new Date().toISOString(),
        });
        if (data.event_type === 'done' || data.event_type === 'complete') {
          onComplete();
        }
      } catch (e) {
        console.error('Error parsing SSE event:', e);
      }
    },
    onError,
    onComplete
  );
}

/**
 * 获取知识库助手信息
 */
export async function getKnowledgeInfo() {
  try {
    return await api.get<{
      success: boolean;
      agent_info: any;
    }>('/juben/knowledge/info');
  } catch (error) {
    if (error instanceof APIError) {
      throw new Error(`获取知识库助手信息失败: ${error.message}`);
    }
    throw error;
  }
}

/**
 * 文件引用解析（流式）
 */
export function streamFileReference(
  request: ChatRequest,
  onChunk: (chunk: string) => void,
  onEvent: (event: SSEEvent) => void,
  onComplete: () => void,
  onError: (error: Error) => void
): () => void {
  return api.connectSSE(
    '/juben/file-reference/chat',
    request,
    (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.event_type === 'message' || data.event_type === 'llm_chunk') {
          onChunk(data.data || '');
        }
        onEvent({
          event: data.event_type,
          data: data.data || {},
          timestamp: data.timestamp || new Date().toISOString(),
        });
        if (data.event_type === 'done' || data.event_type === 'complete') {
          onComplete();
        }
      } catch (e) {
        console.error('Error parsing SSE event:', e);
      }
    },
    onError,
    onComplete
  );
}

/**
 * 获取文件引用助手信息
 */
export async function getFileReferenceInfo() {
  try {
    return await api.get<{
      success: boolean;
      agent_info: any;
    }>('/juben/file-reference/info');
  } catch (error) {
    if (error instanceof APIError) {
      throw new Error(`获取文件引用助手信息失败: ${error.message}`);
    }
    throw error;
  }
}

/**
 * 故事五元素分析（流式）
 */
export function streamStoryAnalysis(
  request: ChatRequest & { file?: string; chunk_size?: number; length_size?: number },
  onChunk: (chunk: string) => void,
  onEvent: (event: SSEEvent) => void,
  onComplete: () => void,
  onError: (error: Error) => void
): () => void {
  return api.connectSSE(
    '/juben/story-analysis/analyze',
    request,
    (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.event_type === 'message' || data.event_type === 'llm_chunk') {
          onChunk(data.data || '');
        }
        onEvent({
          event: data.event_type,
          data: data.data || {},
          timestamp: data.timestamp || new Date().toISOString(),
        });
        if (data.event_type === 'done' || data.event_type === 'complete') {
          onComplete();
        }
      } catch (e) {
        console.error('Error parsing SSE event:', e);
      }
    },
    onError,
    onComplete
  );
}

/**
 * 获取故事分析助手信息
 */
export async function getStoryAnalysisInfo() {
  try {
    return await api.get<{
      success: boolean;
      agent_info: any;
    }>('/juben/story-analysis/info');
  } catch (error) {
    if (error instanceof APIError) {
      throw new Error(`获取故事分析助手信息失败: ${error.message}`);
    }
    throw error;
  }
}

/**
 * 已播剧集分析（流式）
 */
export function streamSeriesAnalysis(
  request: ChatRequest,
  onChunk: (chunk: string) => void,
  onEvent: (event: SSEEvent) => void,
  onComplete: () => void,
  onError: (error: Error) => void
): () => void {
  return api.connectSSE(
    '/juben/series-analysis/analyze',
    request,
    (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.event_type === 'message' || data.event_type === 'llm_chunk') {
          onChunk(data.data || '');
        }
        onEvent({
          event: data.event_type,
          data: data.data || {},
          timestamp: data.timestamp || new Date().toISOString(),
        });
        if (data.event_type === 'done' || data.event_type === 'complete') {
          onComplete();
        }
      } catch (e) {
        console.error('Error parsing SSE event:', e);
      }
    },
    onError,
    onComplete
  );
}

/**
 * 获取已播剧集分析助手信息
 */
export async function getSeriesAnalysisInfo() {
  try {
    return await api.get<{
      success: boolean;
      agent_info: any;
    }>('/juben/series-analysis/info');
  } catch (error) {
    if (error instanceof APIError) {
      throw new Error(`获取已播剧集分析助手信息失败: ${error.message}`);
    }
    throw error;
  }
}

/**
 * 情节点工作流执行（流式）
 */
export function streamPlotPointsWorkflow(
  request: ChatRequest & { chunk_size?: number; length_size?: number; format?: string },
  onChunk: (chunk: string) => void,
  onEvent: (event: SSEEvent) => void,
  onComplete: () => void,
  onError: (error: Error) => void
): () => void {
  return api.connectSSE(
    '/juben/plot-points-workflow/execute',
    request,
    (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type !== 'workflow_error') {
          onChunk(data.message || '');
        }
        onEvent({
          event: data.type || 'message',
          data: data,
          timestamp: data.timestamp || new Date().toISOString(),
        });
        if (data.type === 'done' || data.type === 'complete') {
          onComplete();
        }
      } catch (e) {
        console.error('Error parsing SSE event:', e);
      }
    },
    onError,
    onComplete
  );
}

/**
 * 获取情节点工作流信息
 */
export async function getPlotPointsWorkflowInfo() {
  try {
    return await api.get<{
      success: boolean;
      workflow_info: any;
    }>('/juben/plot-points-workflow/info');
  } catch (error) {
    if (error instanceof APIError) {
      throw new Error(`获取情节点工作流信息失败: ${error.message}`);
    }
    throw error;
  }
}
