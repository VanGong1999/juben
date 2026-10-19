/**
 * 统计服务
 * 获取系统统计数据、性能指标等
 */

import { api } from './api';

// ==================== 类型定义 ====================

export interface SystemStats {
  total_access: number;
  today_access: number;
  today_unique_users: number;
  status: 'healthy' | 'degraded' | 'down' | 'unknown';
}

export interface DailyStats {
  date: string;
  access_count: number;
  unique_users: number;
  error_count: number;
  avg_response_time: number;
}

export interface PerformanceMetrics {
  endpoint: string;
  count: number;
  duration: {
    avg: number;
    min: number;
    max: number;
    p50: number;
    p95: number;
    p99: number;
  };
  success_rate: number;
  status_codes: Record<number, number>;
}

export interface AgentUsageStats {
  agent_id: string;
  agent_name: string;
  usage_count: number;
  token_usage: number;
  avg_duration: number;
}

export interface ResponseTimeDistribution {
  fast: number;    // < 1s
  normal: number;  // 1-2s
  slow: number;    // 2-5s
  very_slow: number; // > 5s
}

export interface SystemHealth {
  api_availability: number;
  error_rate: number;
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  active_connections: number;
  queue_length: number;
}

export interface WorkflowStats {
  total_templates: number;
  total_executions: number;
  running_executions: number;
  success_rate: number;
  category_breakdown: Record<string, number>;
}

// ==================== 性能指标相关类型 ====================

export interface MetricsSnapshot {
  metrics: Record<string, MetricPoint>;
  counters: Record<string, number>;
  gauges: Record<string, number>;
  requests: {
    total: number;
    last_minute: number;
  };
}

export interface MetricPoint {
  count: number;
  latest: number | null;
}

// ==================== 统计服务类 ====================

class StatisticsService {
  private basePath = '/juben/statistics';

  /**
   * 获取系统访问统计
   */
  async getSystemStats(): Promise<SystemStats> {
    const response = await api.get<{ success: boolean; data: SystemStats }>(
      '/juben/system/access-stats'
    );
    return response.data || {
      total_access: 0,
      today_access: 0,
      today_unique_users: 0,
      status: 'unknown' as any
    };
  }

  /**
   * 获取每日统计数据
   */
  async getDailyStats(days: number = 7): Promise<DailyStats[]> {
    const response = await api.get<{ success: boolean; data: { daily_stats: Record<string, DailyStats> } }>(
      `/juben/system/access-stats/daily?days=${days}`
    );

    const dailyStats = response.data?.daily_stats || {};
    return Object.keys(dailyStats)
      .sort()
      .map((date) => ({
        ...dailyStats[date],
        date
      }));
  }

  /**
   * 获取性能指标
   */
  async getPerformanceMetrics(
    endpoint?: string,
    timeRange: string = '1h'
  ): Promise<PerformanceMetrics[]> {
    const params = new URLSearchParams();
    if (endpoint) params.append('endpoint', endpoint);
    params.append('time_range', timeRange);

    const response = await api.get<{ success: boolean; data: PerformanceMetrics[] }>(
      `${this.basePath}/performance?${params.toString()}`
    );
    return response.data || [];
  }

  /**
   * 获取Agent使用统计
   */
  async getAgentUsageStats(
    timeRange: string = '7d'
  ): Promise<AgentUsageStats[]> {
    const response = await api.get<{ success: boolean; data: AgentUsageStats[] }>(
      `${this.basePath}/agent-usage?time_range=${timeRange}`
    );
    return response.data || [];
  }

  /**
   * 获取系统健康状态
   */
  async getSystemHealth(): Promise<SystemHealth> {
    const response = await api.get<{ success: boolean; data: SystemHealth }>(
      `${this.basePath}/health`
    );
    return response.data || {
      api_availability: 99.9,
      error_rate: 0.1,
      cpu_usage: 0,
      memory_usage: 0,
      disk_usage: 0,
      active_connections: 0,
      queue_length: 0
    };
  }

  /**
   * 获取工作流统计
   */
  async getWorkflowStats(): Promise<WorkflowStats> {
    const response = await api.get<{ success: boolean; data: WorkflowStats }>(
      '/juben/workflow/statistics'
    );
    return response.data || {
      total_templates: 0,
      total_executions: 0,
      running_executions: 0,
      success_rate: 0,
      category_breakdown: {}
    };
  }

  /**
   * 获取响应时间分布
   */
  async getResponseTimeDistribution(
    timeRange: string = '24h'
  ): Promise<{
    fast: number;    // < 1s
    normal: number;  // 1-2s
    slow: number;    // 2-5s
    very_slow: number; // > 5s
  }> {
    const response = await api.get<{
      success: boolean;
      data: { fast: number; normal: number; slow: number; very_slow: number }
    }>(
      `${this.basePath}/response-time-distribution?time_range=${timeRange}`
    );
    return response.data || { fast: 0, normal: 0, slow: 0, very_slow: 0 };
  }

  /**
   * 获取所有指标摘要
   */
  async getAllMetrics(): Promise<MetricsSnapshot> {
    const response = await api.get<{ success: boolean; data: MetricsSnapshot }>(
      `${this.basePath}/metrics`
    );
    return response.data || {
      metrics: {},
      counters: {},
      gauges: {},
      requests: { total: 0, last_minute: 0 }
    };
  }

  /**
   * 导出统计数据
   */
  async exportStatistics(
    format: 'json' | 'csv' = 'json',
    timeRange: string = '7d'
  ): Promise<Blob> {
    const authHeader = this.getAuthHeader();
    const url = `${api['baseURL'] || 'http://localhost:8000'}${this.basePath}/export?format=${format}&time_range=${timeRange}`;

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
   * 获取实时统计数据（WebSocket/SSE）
   */
  subscribeToRealTimeStats(
    callback: (stats: MetricsSnapshot) => void,
    onError?: (error: Error) => void
  ): () => void {
    const authHeader = this.getAuthHeader();
    const url = `${api['baseURL'] || 'http://localhost:8000'}${this.basePath}/stream`;

    const eventSource = new EventSource(url, {
      withCredentials: true
    });

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        callback(data);
      } catch (e) {
        console.error('Failed to parse SSE data:', e);
      }
    };

    eventSource.onerror = (error) => {
      console.error('SSE error:', error);
      onError?.(new Error('Real-time stats connection failed'));
    };

    // 返回清理函数
    return () => {
      eventSource.close();
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
export const statisticsService = new StatisticsService();
export default statisticsService;
