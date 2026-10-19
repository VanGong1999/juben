/**
 * Agent 服务
 */

import api from './api';
import type { Agent, ModelListResponse } from '@/types';

// ==================== 后端数据类型 ====================

interface BackendAgent {
  id?: string;
  /** 后端 core/agent_routes 用 `type` 字段承载 agent id */
  type?: string;
  name: string;
  display_name?: string;
  displayName?: string;
  description: string;
  category: string;
  icon?: string;
  model?: string;
  api_endpoint?: string;
  apiEndpoint?: string;
  features?: string[];
  capabilities?: string[];
  input_example?: string;
  inputExample?: string;
  output_example?: string;
  outputExample?: string;
  status?: 'active' | 'inactive' | 'deprecated';
  product_line?: 'short_drama' | 'general' | 'shared';
}

interface RecommendedModelResponse {
  model_id: string;
  model_name: string;
  provider: string;
  reason: string;
}

interface ModelsByTypeResponse {
  text: ModelInfo[];
  vision: ModelInfo[];
  image_generation: ModelInfo[];
  video_generation: ModelInfo[];
}

interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  type: string;
  context_length?: number;
}

interface SearchResult {
  id: string;
  name: string;
  description: string;
  category: string;
  relevance_score: number;
}

/**
 * 将后端蛇形命名转换为前端驼峰命名
 */
function mapBackendAgentToAgent(backendAgent: BackendAgent): Agent {
  return {
    id: backendAgent.id || backendAgent.type || '',
    name: backendAgent.name,
    displayName: backendAgent.display_name || backendAgent.displayName || backendAgent.name,
    description: backendAgent.description || '',
    category: backendAgent.category as Agent['category'],
    icon: backendAgent.icon || '',
    model: backendAgent.model || '',
    apiEndpoint: backendAgent.api_endpoint || backendAgent.apiEndpoint || '',
    features: backendAgent.features || [],
    capabilities: backendAgent.capabilities || [],
    inputExample: backendAgent.input_example || backendAgent.inputExample || '',
    outputExample: backendAgent.output_example || backendAgent.outputExample || '',
    status: (backendAgent.status || 'active') as Agent['status'],
    productLine: backendAgent.product_line,
  };
}

/**
 * 合并后端目录与本地 AGENTS_CONFIG：后端优先覆盖同 id，本地补齐缺失专家。
 * 避免后端目录不全时把剧本评估 / IP 评估等冲掉。
 */
async function mergeWithLocalCatalog(remote: Agent[]): Promise<Agent[]> {
  const { AGENTS_CONFIG } = await import('@/config/agents');
  const byId = new Map<string, Agent>();
  for (const local of AGENTS_CONFIG) {
    byId.set(local.id, { ...local });
  }
  for (const agent of remote) {
    const prev = byId.get(agent.id);
    byId.set(agent.id, {
      ...prev,
      ...agent,
      // 后端 core/agent_routes 的 name 是中文明，本地才是英文类名，优先本地
      name: prev?.name || agent.name,
      displayName: agent.displayName || prev?.displayName || agent.name,
      features: agent.features?.length ? agent.features : prev?.features || [],
      capabilities: agent.capabilities?.length ? agent.capabilities : prev?.capabilities || [],
      inputExample: agent.inputExample || prev?.inputExample || '',
      outputExample: agent.outputExample || prev?.outputExample || '',
      icon: agent.icon || prev?.icon || '',
      model: agent.model || prev?.model || '',
      apiEndpoint: agent.apiEndpoint || prev?.apiEndpoint || '',
      status: agent.status || prev?.status || 'active',
      category: agent.category || prev?.category || 'utility',
      productLine: agent.productLine || prev?.productLine,
    });
  }
  // 保持本地目录顺序，再追加仅后端有的项
  const ordered: Agent[] = [];
  const seen = new Set<string>();
  for (const local of AGENTS_CONFIG) {
    const merged = byId.get(local.id);
    if (merged) {
      ordered.push(merged);
      seen.add(local.id);
    }
  }
  for (const [id, agent] of byId) {
    if (!seen.has(id)) ordered.push(agent);
  }
  return ordered;
}

/**
 * 获取所有可用的 Agents（从后端API，并与本地目录合并）
 */
export async function getAgents(): Promise<Agent[]> {
  try {
    // 优先从后端API获取
    const response = await api.get<{ success: boolean; agents?: BackendAgent[]; total?: number }>('/juben/agents/list');

    if (response.success && response.agents) {
      return mergeWithLocalCatalog(response.agents.map(mapBackendAgentToAgent));
    }

    // 如果API失败，回退到本地配置
    const { AGENTS_CONFIG } = await import('@/config/agents');
    return AGENTS_CONFIG;
  } catch (error) {
    console.error('Failed to load agents from API, using local config:', error);
    // 回退到本地配置
    try {
      const { AGENTS_CONFIG } = await import('@/config/agents');
      return AGENTS_CONFIG;
    } catch {
      return [];
    }
  }
}

/**
 * 获取 Agent 信息（从后端API）
 */
export async function getAgentInfo(agentId: string): Promise<Agent | null> {
  try {
    // 优先从后端API获取
    const response = await api.get<any>(`/juben/agents/${agentId}`);
    if (response) {
      const agentData = response.agent || response.data || response;
      return mapBackendAgentToAgent(agentData);
    }
    return null;
  } catch (error) {
    console.error('Failed to get agent info from API:', error);
    // 回退到本地配置
    try {
      const agents = await getAgents();
      return agents.find(a => a.id === agentId) || null;
    } catch {
      return null;
    }
  }
}

/**
 * 获取可用模型列表
 */
export async function getModels(provider: string = 'deepseek'): Promise<ModelListResponse> {
  try {
    return await api.get<ModelListResponse>('/juben/models', { provider });
  } catch (error) {
    console.error('Failed to get models:', error);
    return {
      success: false,
      provider,
      models: [],
      default_model: 'deepseek-flash',
      purpose_models: {},
      total_count: 0,
    };
  }
}

/**
 * 获取推荐模型
 */
export async function getRecommendedModel(purpose: string): Promise<string> {
  try {
    const response = await api.get<{ success: boolean; recommended_model?: RecommendedModelResponse }>(
      '/juben/models/recommend',
      { purpose }
    );
    return response.recommended_model?.model_id || response.recommended_model?.model_name || 'deepseek-flash';
  } catch (error) {
    console.error('Failed to get recommended model:', error);
    return 'deepseek-flash';
  }
}

/**
 * 按类型获取模型
 */
export async function getModelsByType(): Promise<ModelsByTypeResponse> {
  try {
    const response = await api.get<{ success: boolean; models?: ModelsByTypeResponse }>(
      '/juben/models/types'
    );
    // 后端返回格式: { success: true, models: { text: [], vision: [], ... } }
    return response.models || {
      text: [],
      vision: [],
      image_generation: [],
      video_generation: [],
    };
  } catch (error) {
    console.error('Failed to get models by type:', error);
    return {
      text: [],
      vision: [],
      image_generation: [],
      video_generation: [],
    };
  }
}

/**
 * 搜索 Agents（从后端API）
 */
export async function searchAgents(query: string): Promise<Agent[]> {
  try {
    // 从后端API搜索
    const response = await api.get<{ success: boolean; results?: BackendAgent[] }>('/juben/agents/search', { query });
    if (response.success && response.results) {
      return response.results.map(mapBackendAgentToAgent);
    }
    return [];
  } catch (error) {
    console.error('Failed to search agents from API:', error);
    // 回退到本地配置
    try {
      const { searchAgents: search } = await import('@/config/agents');
      return search(query);
    } catch {
      return [];
    }
  }
}

/**
 * 按分类获取 Agents（从后端API）
 */
export async function getAgentsByCategory(category: string): Promise<Agent[]> {
  try {
    // 从后端API获取
    const response = await api.get<{ success: boolean; agents?: BackendAgent[] }>('/juben/agents/list', { category });
    if (response.success && response.agents) {
      return response.agents.map(mapBackendAgentToAgent);
    }
    return [];
  } catch (error) {
    console.error('Failed to get agents by category from API:', error);
    // 回退到本地配置
    try {
      const { getAgentsByCategory: getByCategory } = await import('@/config/agents');
      return getByCategory(category as Agent['category']);
    } catch {
      return [];
    }
  }
}

/**
 * 获取Agent分类列表（从后端API）
 */
export async function getAgentCategories(): Promise<{
  categories: Record<string, { name: string; icon: string; description: string }>;
  counts: Record<string, number>;
  total: number;
}> {
  try {
    const response = await api.get<any>('/juben/agents/categories');
    return {
      categories: response.categories || {},
      counts: response.counts || {},
      total: response.total || 0,
    };
  } catch (error) {
    console.error('Failed to get agent categories:', error);
    return {
      categories: {},
      counts: {},
      total: 0,
    };
  }
}
