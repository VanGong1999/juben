/**
 * 工作流服务
 * 提供工作流模板、执行、监控等API调用
 */

import { api } from './api';

// ==================== 类型定义 ====================

export interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
  category: 'creation' | 'evaluation' | 'analysis' | 'custom';
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  created_at: string;
  updated_at: string;
  created_by: string;
  tags: string[];
}

export interface WorkflowNode {
  id: string;
  type: 'input' | 'output' | 'processing' | 'parallel' | 'condition' | 'loop';
  label: string;
  description: string;
  position: { x: number; y: number };
  config: {
    agent_id?: string;
    parameters?: Record<string, unknown>;
    timeout?: number;
    retry_count?: number;
    condition?: string;
  };
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
  condition?: string;
}

export interface WorkflowExecution {
  execution_id: string;
  workflow_id: string;
  status: 'pending' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  current_stage: string;
  started_at: string;
  completed_at?: string;
  error?: string;
  results: Record<string, unknown>;
}

export interface WorkflowExecutionRequest {
  workflow_id: string;
  input: Record<string, unknown>;
  parameters?: Record<string, unknown>;
  options?: {
    timeout?: number;
    enable_pause?: boolean;
    save_results?: boolean;
  };
}

export interface WorkflowNodeEvent {
  event_type: 'workflow_initialized' | 'workflow_node_event' | 'workflow_completed' | 'workflow_paused' | 'workflow_error';
  workflow_id: string;
  timestamp: string;
  metadata?: {
    node_name?: string;
    status?: string;
    output_snapshot?: string;
    error?: string;
    progress?: number;
  };
}

// ==================== 工作流服务类 ====================

class WorkflowService {
  private basePath = '/juben/workflow';

  /**
   * 获取所有工作流模板
   */
  async getTemplates(category?: string): Promise<WorkflowTemplate[]> {
    const params = category ? `?category=${category}` : '';
    const response = await api.get<{ success: boolean; data: { templates: WorkflowTemplate[] } }>(
      `${this.basePath}/templates${params}`
    );
    return response.data?.templates || [];
  }

  /**
   * 获取工作流模板详情
   */
  async getTemplate(templateId: string): Promise<WorkflowTemplate> {
    const response = await api.get<{ success: boolean; data: WorkflowTemplate }>(
      `${this.basePath}/templates/${templateId}`
    );
    return response.data;
  }

  /**
   * 创建工作流模板
   */
  async createTemplate(template: Omit<WorkflowTemplate, 'id' | 'created_at' | 'updated_at'>): Promise<WorkflowTemplate> {
    const response = await api.post<{ success: boolean; data: WorkflowTemplate }>(
      `${this.basePath}/templates`,
      template
    );
    return response.data;
  }

  /**
   * 更新工作流模板
   */
  async updateTemplate(
    templateId: string,
    updates: Partial<WorkflowTemplate>
  ): Promise<WorkflowTemplate> {
    const response = await api.put<{ success: boolean; data: WorkflowTemplate }>(
      `${this.basePath}/templates/${templateId}`,
      updates
    );
    return response.data;
  }

  /**
   * 删除工作流模板
   */
  async deleteTemplate(templateId: string): Promise<{ success: boolean; message: string }> {
    return api.delete<{ success: boolean; message: string }>(
      `${this.basePath}/templates/${templateId}`
    );
  }

  /**
   * 执行工作流
   */
  async executeWorkflow(request: WorkflowExecutionRequest): Promise<{
    execution_id: string;
    status: string;
    message: string;
  }> {
    const response = await api.post<{
      success: boolean;
      data: { execution_id: string; status: string; message: string };
    }>(`${this.basePath}/execute`, request);
    return response.data;
  }

  /**
   * 获取执行状态
   */
  async getExecutionStatus(executionId: string): Promise<WorkflowExecution> {
    const response = await api.get<{ success: boolean; data: WorkflowExecution }>(
      `${this.basePath}/executions/${executionId}`
    );
    return response.data;
  }

  /**
   * 暂停工作流执行
   */
  async pauseExecution(executionId: string): Promise<{ success: boolean; message: string }> {
    return api.post<{ success: boolean; message: string }>(
      `${this.basePath}/executions/${executionId}/pause`,
      {}
    );
  }

  /**
   * 恢复工作流执行
   */
  async resumeExecution(executionId: string): Promise<{ success: boolean; message: string }> {
    return api.post<{ success: boolean; message: string }>(
      `${this.basePath}/executions/${executionId}/resume`,
      {}
    );
  }

  /**
   * 取消工作流执行
   */
  async cancelExecution(executionId: string): Promise<{ success: boolean; message: string }> {
    return api.post<{ success: boolean; message: string }>(
      `${this.basePath}/executions/${executionId}/cancel`,
      {}
    );
  }

  /**
   * 重试失败的工作流
   */
  async retryExecution(executionId: string): Promise<{
    execution_id: string;
    status: string;
    message: string;
  }> {
    const response = await api.post<{
      success: boolean;
      data: { execution_id: string; status: string; message: string };
    }>(`${this.basePath}/executions/${executionId}/retry`, {});
    return response.data;
  }

  /**
   * 获取执行历史
   */
  async getExecutionHistory(
    workflowId?: string,
    limit: number = 50
  ): Promise<WorkflowExecution[]> {
    const params = new URLSearchParams();
    if (workflowId) params.append('workflow_id', workflowId);
    params.append('limit', String(limit));

    const response = await api.get<{ success: boolean; data: WorkflowExecution[] }>(
      `${this.basePath}/executions?${params.toString()}`
    );
    return response.data || [];
  }

  /**
   * 获取执行结果
   */
  async getExecutionResults(executionId: string): Promise<Record<string, unknown>> {
    const response = await api.get<{ success: boolean; data: { results: Record<string, unknown> } }>(
      `${this.basePath}/executions/${executionId}/results`
    );
    return response.data?.results || {};
  }

  /**
   * 导出工作流模板
   */
  async exportTemplate(templateId: string, format: 'json' | 'yaml' = 'json'): Promise<Blob> {
    const authHeader = this.getAuthHeader();
    const url = `${api['baseURL'] || 'http://localhost:8000'}${this.basePath}/templates/${templateId}/export?format=${format}`;

    const response = await fetch(url, {
      headers: {
        ...(authHeader ? { Authorization: authHeader } : {}),
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${await response.text()}`);
    }

    return response.blob();
  }

  /**
   * 导入工作流模板
   */
  async importTemplate(file: File): Promise<WorkflowTemplate> {
    const formData = new FormData();
    formData.append('file', file);

    const authHeader = this.getAuthHeader();
    const url = `${api['baseURL'] || 'http://localhost:8000'}${this.basePath}/templates/import`;

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        ...(authHeader ? { Authorization: authHeader } : {}),
      },
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${await response.text()}`);
    }

    const result = await response.json();
    return result.data;
  }

  /**
   * 克隆工作流模板
   */
  async cloneTemplate(templateId: string, newName: string): Promise<WorkflowTemplate> {
    const response = await api.post<{ success: boolean; data: WorkflowTemplate }>(
      `${this.basePath}/templates/${templateId}/clone`,
      { name: newName }
    );
    return response.data;
  }

  /**
   * 验证工作流模板
   */
  async validateTemplate(template: Partial<WorkflowTemplate>): Promise<{
    valid: boolean;
    errors: string[];
    warnings: string[];
  }> {
    const response = await api.post<{
      success: boolean;
      data: { valid: boolean; errors: string[]; warnings: string[] };
    }>(`${this.basePath}/templates/validate`, template);
    return response.data;
  }

  /**
   * 获取工作流统计
   */
  async getStatistics(): Promise<{
    total_templates: number;
    total_executions: number;
    running_executions: number;
    success_rate: number;
    category_breakdown: Record<string, number>;
  }> {
    const response = await api.get<{
      success: boolean;
      data: {
        total_templates: number;
        total_executions: number;
        running_executions: number;
        success_rate: number;
        category_breakdown: Record<string, number>;
      };
    }>(`${this.basePath}/statistics`);
    return response.data || {
      total_templates: 0,
      total_executions: 0,
      running_executions: 0,
      success_rate: 0,
      category_breakdown: {}
    };
  }

  /**
   * 获取认证头
   */
  private getAuthHeader(): string | null {
    try {
      const raw = localStorage.getItem('auth-storage');
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      const token = parsed?.state?.tokens?.accessToken;
      return token ? `Bearer ${token}` : null;
    } catch {
      return null;
    }
  }
}

// 导出单例
export const workflowService = new WorkflowService();
export default workflowService;
