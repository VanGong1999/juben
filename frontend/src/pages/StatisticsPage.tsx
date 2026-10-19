/**
 * 统计分析页面
 * 展示系统使用统计、性能分析等信息
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  TrendingUp,
  Users,
  MessageSquare,
  Activity,
  Clock,
  Zap,
  BarChart3,
  PieChart,
  Calendar,
  Download,
  Filter,
} from 'lucide-react';
import AppShell from '@/components/layout/AppShell';
import { useNotificationStore } from '@/store/notificationStore';
import { useI18n } from '@/i18n';
import { statisticsService, SystemStats, DailyStats, SystemHealth, ResponseTimeDistribution, AgentUsageStats } from '@/services/statisticsService';

interface StatCard {
  title: string;
  value: string | number;
  change: string;
  changeType: 'increase' | 'decrease';
  icon: React.ElementType;
}

interface UsageData {
  date: string;
  users: number;
  messages: number;
  tokens: number;
  avgResponseTime?: number;
}

export const StatisticsPage: React.FC = () => {
  const { success, error } = useNotificationStore();
  const { t, language } = useI18n();
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('7d');
  const [isLoading, setIsLoading] = useState(false);
  const [statsData, setStatsData] = useState<SystemStats>({
    total_access: 0,
    today_access: 0,
    today_unique_users: 0,
    status: 'unknown',
  });
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);
  const [responseTimeDist, setResponseTimeDist] = useState<ResponseTimeDistribution | null>(null);
  const [agentUsage, setAgentUsage] = useState<AgentUsageStats[]>([]);
  const [usageData, setUsageData] = useState<UsageData[]>([]);

  // 使用 ref 来追踪实时更新订阅
  const realTimeUnsubscribeRef = useRef<(() => void) | null>(null);

  // 加载统计数据
  const loadStats = useCallback(async () => {
    setIsLoading(true);
    try {
      // 并行加载所有统计数据
      const [systemStats, health, responseDist, agentStats, dailyStats] = await Promise.all([
        statisticsService.getSystemStats(),
        statisticsService.getSystemHealth(),
        statisticsService.getResponseTimeDistribution(),
        statisticsService.getAgentUsageStats(timeRange),
        statisticsService.getDailyStats(timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90),
      ]);

      setStatsData(systemStats);
      setSystemHealth(health);
      setResponseTimeDist(responseDist);
      setAgentUsage(agentStats);

      // 转换每日数据
      const data: UsageData[] = dailyStats.map((stat) => ({
        date: new Date(stat.date).toLocaleDateString(language === 'zh' ? 'zh-CN' : 'en-US', { month: 'short', day: 'numeric' }),
        users: stat.unique_users,
        messages: stat.access_count,
        tokens: 0, // 暂无token数据
        avgResponseTime: stat.avg_response_time,
      }));
      setUsageData(data);
    } catch (err: any) {
      error(t('toolbox.statistics.toast.loadFailed'), err?.message || t('toolbox.statistics.toast.loadFailedDesc'));
    } finally {
      setIsLoading(false);
    }
  }, [timeRange, error]);

  useEffect(() => {
    loadStats();

    // 订阅实时统计数据
    realTimeUnsubscribeRef.current = statisticsService.subscribeToRealTimeStats(
      (realTimeStats) => {
        // 实时更新部分数据
        if (realTimeStats.requests) {
          // 可以在这里更新实时数据
        }
      },
      (err) => {
        console.error('Real-time stats error:', err);
      }
    );

    return () => {
      // 清理订阅
      if (realTimeUnsubscribeRef.current) {
        realTimeUnsubscribeRef.current();
      }
    };
  }, [loadStats]);

  const statCards: StatCard[] = [
    {
      title: t('toolbox.statistics.card.totalAccess'),
      value: statsData.total_access,
      change: '',
      changeType: 'increase',
      icon: Users,
    },
    {
      title: t('toolbox.statistics.card.todayAccess'),
      value: statsData.today_access,
      change: '',
      changeType: 'increase',
      icon: MessageSquare,
    },
    {
      title: t('toolbox.statistics.card.todayUsers'),
      value: statsData.today_unique_users,
      change: '',
      changeType: 'increase',
      icon: Activity,
    },
    {
      title: t('toolbox.statistics.card.systemStatus'),
      value: statsData.status === 'healthy' ? t('toolbox.statistics.status.healthy') : statsData.status === 'degraded' ? t('toolbox.statistics.status.degraded') : t('toolbox.statistics.status.error'),
      change: '',
      changeType: statsData.status === 'healthy' ? 'increase' : 'decrease',
      icon: Zap,
    },
  ];

  const handleExport = async () => {
    setIsLoading(true);
    try {
      const blob = await statisticsService.exportStatistics('json', timeRange);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `statistics_${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      success(t('toolbox.statistics.toast.exportSuccess'), t('toolbox.statistics.toast.exported'));
    } catch (err) {
      error(t('toolbox.statistics.toast.exportFailed'), t('toolbox.statistics.toast.retryLater'));
    } finally {
      setIsLoading(false);
    }
  };

  // 计算Agent使用分布百分比
  const totalAgentUsage = agentUsage.reduce((sum, agent) => sum + agent.usage_count, 0);
  const agentUsageDistribution = agentUsage.map((agent) => ({
    name: agent.agent_name,
    usage: totalAgentUsage > 0 ? Math.round((agent.usage_count / totalAgentUsage) * 100) : 0,
    color: 'bg-atelier-teal',
  }));

  return (
    <AppShell
      title={t('toolbox.statistics.title')}
      subtitle={t('toolbox.statistics.subtitle')}
      actions={
        <div className="flex items-center gap-2">
          {/* 时间范围选择器 */}
          <div className="flex items-center bg-pearl-soft rounded-lg p-1">
            {(['7d', '30d', '90d'] as const).map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  timeRange === range
                    ? 'bg-white text-ink shadow-sm'
                    : 'text-ink-muted hover:text-ink'
                }`}
              >
                {range === '7d' ? t('toolbox.statistics.range.d7') : range === '30d' ? t('toolbox.statistics.range.d30') : t('toolbox.statistics.range.d90')}
              </button>
            ))}
          </div>
          <button
            onClick={handleExport}
            disabled={isLoading}
            className="btn btn-primary btn-sm disabled:opacity-50"
          >
            <Download className="w-4 h-4" />
            {isLoading ? t('toolbox.statistics.exporting') : t('toolbox.statistics.exportReport')}
          </button>
        </div>
      }
    >
      <div className="px-4 sm:px-8 lg:px-10 py-6 sm:py-8 max-w-6xl mx-auto space-y-6 sm:space-y-8">
        {/* 统计卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {statCards.map((card, index) => (
            <div
              key={index}
              className="glass-panel p-6"
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <p className="text-sm text-ink-muted">
                    {card.title}
                  </p>
                  <p className="text-2xl font-bold text-ink mt-2">
                    {card.value}
                  </p>
                  <div className="flex items-center mt-2">
                    <TrendingUp
                      className={`w-4 h-4 mr-1 ${
                        card.changeType === 'increase'
                          ? 'text-green-500'
                          : 'text-red-500'
                      }`}
                    />
                    <span
                      className={`text-sm font-medium ${
                        card.changeType === 'increase'
                          ? 'text-green-600'
                          : 'text-red-600'
                      }`}
                    >
                      {card.change}
                    </span>
                    <span className="text-sm text-ink-muted ml-1">
                      {t('toolbox.statistics.vsLast')}
                    </span>
                  </div>
                </div>
                <div className="ml-4">
                  <card.icon className="w-8 h-8 text-atelier-teal" />
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* 图表区域 */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 使用趋势图 */}
          <div className="lg:col-span-2 glass-panel p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold text-ink">
                {t('toolbox.statistics.trend')}
              </h2>
              <div className="flex items-center gap-4 text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-blue-500" />
                  <span className="text-ink-muted">{t('toolbox.statistics.messages')}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-green-500" />
                  <span className="text-ink-muted">{t('toolbox.statistics.users')}</span>
                </div>
              </div>
            </div>

            {/* 简化的图表展示 */}
            <div className="h-64 flex items-end gap-2">
              {usageData.map((item, index) => (
                <div
                  key={index}
                  className="flex-1 flex flex-col items-center gap-1"
                >
                  <div className="w-full flex gap-1 items-end h-full">
                    <div
                      className="flex-1 bg-blue-500 rounded-t transition-all hover:bg-blue-600"
                      style={{
                        height: `${(item.messages / 700) * 100}%`,
                        minHeight: '4px',
                      }}
                      title={`${t('toolbox.statistics.messages')}: ${item.messages}`}
                    />
                    <div
                      className="flex-1 bg-green-500 rounded-t transition-all hover:bg-green-600"
                      style={{
                        height: `${(item.users / 150) * 100}%`,
                        minHeight: '4px',
                      }}
                      title={`${t('toolbox.statistics.users')}: ${item.users}`}
                    />
                  </div>
                  {index % Math.ceil(usageData.length / 7) === 0 && (
                    <span className="text-xs text-ink-muted transform -rotate-45 origin-top-left">
                      {item.date}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Agent使用分布 */}
          <div className="glass-panel p-6">
            <h2 className="text-lg font-semibold text-ink mb-6">
              {t('toolbox.statistics.agentDist')}
            </h2>
            <div className="space-y-4">
              {agentUsageDistribution.map((agent) => (
                <div key={agent.name}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-ink-muted">
                      {agent.name}
                    </span>
                    <span className="text-sm font-medium text-ink">
                      {agent.usage}%
                    </span>
                  </div>
                  <div className="w-full bg-pearl-soft rounded-full h-2">
                    <div
                      className={`${agent.color} h-2 rounded-full transition-all`}
                      style={{ width: `${agent.usage}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 详细数据表格 */}
        <div className="glass-panel overflow-hidden">
          <div className="px-6 py-4 border-b border-pearl-line">
            <h2 className="text-lg font-semibold text-ink">
              {t('toolbox.statistics.detail')}
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-pearl-line">
              <thead className="bg-pearl-soft">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-ink-muted uppercase tracking-wider">
                    {t('toolbox.statistics.table.date')}
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-ink-muted uppercase tracking-wider">
                    {t('toolbox.statistics.table.activeUsers')}
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-ink-muted uppercase tracking-wider">
                    {t('toolbox.statistics.table.messages')}
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-ink-muted uppercase tracking-wider">
                    {t('toolbox.statistics.table.token')}
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-ink-muted uppercase tracking-wider">
                    {t('toolbox.statistics.table.avgResp')}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-pearl-line">
                {usageData.slice(-7).map((item, index) => (
                  <tr key={index}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-ink">
                      {item.date}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-ink">
                      {item.users}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-ink">
                      {item.messages.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-ink">
                      {item.tokens.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-ink">
                      {item.avgResponseTime ? `${item.avgResponseTime.toFixed(2)}s` : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* 性能指标 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="glass-panel p-6">
            <div className="flex items-center gap-3 mb-4">
              <Clock className="w-5 h-5 text-atelier-teal" />
              <h3 className="text-lg font-semibold text-ink">
                {t('toolbox.statistics.respDist')}
              </h3>
            </div>
            <div className="space-y-3">
              {responseTimeDist ? [
                { label: t('toolbox.statistics.fast'), value: responseTimeDist.fast, color: 'bg-green-500' },
                { label: t('toolbox.statistics.normal'), value: responseTimeDist.normal, color: 'bg-blue-500' },
                { label: t('toolbox.statistics.slow'), value: responseTimeDist.slow, color: 'bg-yellow-500' },
                { label: t('toolbox.statistics.verySlow'), value: responseTimeDist.very_slow, color: 'bg-red-500' },
              ].map((item) => (
                <div key={item.label}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-ink-muted">
                      {item.label}
                    </span>
                    <span className="text-sm font-medium text-ink">
                      {item.value}%
                    </span>
                  </div>
                  <div className="w-full bg-pearl-soft rounded-full h-2">
                    <div
                      className={`${item.color} h-2 rounded-full`}
                      style={{ width: `${item.value}%` }}
                    />
                  </div>
                </div>
              )) : (
                <div className="text-sm text-ink-muted">{t('toolbox.statistics.loading')}</div>
              )}
            </div>
          </div>

          <div className="glass-panel p-6">
            <div className="flex items-center gap-3 mb-4">
              <Activity className="w-5 h-5 text-purple-500" />
              <h3 className="text-lg font-semibold text-ink">
                {t('toolbox.statistics.health')}
              </h3>
            </div>
            <div className="space-y-4">
              {systemHealth ? (
                <>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-ink-muted">
                      {t('toolbox.statistics.apiAvail')}
                    </span>
                    <span className="text-lg font-bold text-green-600">
                      {systemHealth.api_availability.toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-ink-muted">
                      {t('toolbox.statistics.errorRate')}
                    </span>
                    <span className="text-lg font-bold text-green-600">
                      {systemHealth.error_rate.toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-ink-muted">
                      {t('toolbox.statistics.cpu')}
                    </span>
                    <span className="text-lg font-bold text-blue-600">
                      {systemHealth.cpu_usage.toFixed(0)}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-ink-muted">
                      {t('toolbox.statistics.memory')}
                    </span>
                    <span className="text-lg font-bold text-yellow-600">
                      {systemHealth.memory_usage.toFixed(0)}%
                    </span>
                  </div>
                </>
              ) : (
                <div className="text-sm text-ink-muted">{t('toolbox.statistics.loading')}</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
};

export default StatisticsPage;
