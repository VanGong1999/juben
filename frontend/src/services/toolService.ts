/**
 * 工具调用服务
 * 提供 Agent 调用工具的前端接口
 */

import { api } from './api';

// ==================== 类型定义 ====================

export interface ToolSchema {
  name: string;
  label?: string;
  description: string;
  category?: 'prebuilt' | 'external';
  parameters: {
    type: 'object';
    properties: Record<string, {
      type: string;
      description?: string;
      default?: any;
      enum?: string[];
    }>;
    required?: string[];
  };
  requires_sandbox?: boolean;
  dangerous?: boolean;
  enabled?: boolean;
  tags?: string[];
}

export interface ToolExecuteRequest {
  tool_name: string;
  parameters?: Record<string, any>;
  context?: Record<string, any>;
}

export interface ToolExecuteResult {
  success: boolean;
  tool_name: string;
  tool_call_id?: string;
  result?: {
    log_id: string;
    msg: string;
    code: number;
    data: any;
    llm_text?: string;
  };
  error?: string;
}

export interface ToolExecutionHistory {
  tool_name: string;
  parameters: Record<string, any>;
  result: any;
  timestamp: string;
}

export interface SearchResult {
  title: string;
  url: string;
  image_url: string;
  logo_url: string;
  sitename: string;
  summary: string;
  has_image: boolean;
}

// ==================== 工具 API ====================

/**
 * 获取所有工具列表
 */
export async function listTools(): Promise<{
  success: boolean;
  data: ToolSchema[];
  total: number;
}> {
  try {
    const response = await api.get('/tools/list');
    return response.data;
  } catch (error) {
    console.error('[工具列表] 请求失败:', error);
    throw error;
  }
}

/**
 * 获取工具 Schema（用于 LLM Function Calling）
 */
export async function getToolSchemas(): Promise<{
  success: boolean;
  data: ToolSchema[];
  format: string;
}> {
  try {
    const response = await api.get('/tools/schemas');
    return response.data;
  } catch (error) {
    console.error('[工具Schema] 请求失败:', error);
    throw error;
  }
}

/**
 * 执行单个工具
 */
export async function executeTool(request: ToolExecuteRequest): Promise<ToolExecuteResult> {
  try {
    const response = await api.post<{ success: boolean; data: ToolExecuteResult }>('/tools/execute', request);
    return response.data;
  } catch (error) {
    console.error('[工具执行] 请求失败:', error);
    throw error;
  }
}

/**
 * 批量执行工具
 */
export async function batchExecuteTools(tools: ToolExecuteRequest[]): Promise<{
  success: boolean;
  data: ToolExecuteResult[];
  total: number;
}> {
  try {
    const response = await api.post('/tools/batch_execute', { tools });
    return response.data;
  } catch (error) {
    console.error('[批量工具执行] 请求失败:', error);
    throw error;
  }
}

/**
 * 获取工具执行历史
 */
export async function getToolHistory(limit: number = 50): Promise<{
  success: boolean;
  data: ToolExecutionHistory[];
  total: number;
}> {
  try {
    const response = await api.get(`/tools/history?limit=${limit}`);
    return response.data;
  } catch (error) {
    console.error('[工具历史] 请求失败:', error);
    throw error;
  }
}

/**
 * 获取单个工具的 Schema
 */
export async function getToolSchema(toolName: string): Promise<{
  success: boolean;
  data: ToolSchema;
}> {
  try {
    const response = await api.get(`/tools/${toolName}/schema`);
    return response.data;
  } catch (error) {
    console.error('[工具Schema] 请求失败:', error);
    throw error;
  }
}

// ==================== 便捷接口 ====================

/**
 * 快速搜索
 */
export async function quickSearch(query: string, maxResults: number = 10): Promise<{
  success: boolean;
  query: string;
  results: SearchResult[];
  total: number;
}> {
  try {
    const response = await api.post('/tools/search', { query, max_results: maxResults });
    return response.data;
  } catch (error) {
    console.error('[快速搜索] 请求失败:', error);
    throw error;
  }
}

/**
 * 快速百科查询
 */
export async function quickBaike(query: string, includeVideos: boolean = false): Promise<{
  success: boolean;
  query: string;
  baike: any;
  videos: any[];
}> {
  try {
    const response = await api.post('/tools/baike', { query, include_videos: includeVideos });
    return response.data;
  } catch (error) {
    console.error('[快速百科] 请求失败:', error);
    throw error;
  }
}

/**
 * 工具系统健康检查
 */
export async function healthCheck(): Promise<{
  status: string;
  tools_registered: number;
  tools: string[];
}> {
  try {
    const response = await api.get('/tools/health');
    return response.data;
  } catch (error) {
    console.error('[健康检查] 请求失败:', error);
    throw error;
  }
}

// ==================== 导出 ====================

const toolService = {
  // 工具管理
  listTools,
  getToolSchemas,
  getToolSchema,

  // 工具执行
  executeTool,
  batchExecuteTools,

  // 历史记录
  getToolHistory,

  // 便捷接口
  quickSearch,
  quickBaike,
  healthCheck
};

export default toolService;
