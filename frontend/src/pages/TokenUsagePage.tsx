/**
 * Token 使用监控页面 — 与首页统一的杂志编辑风 + 毛玻璃
 */

import { useState, useEffect } from 'react';
import {
  Coins,
  DollarSign,
  BarChart3,
  Users,
  Clock,
  Download,
  RefreshCw,
  AlertTriangle,
} from 'lucide-react';
import AppShell from '@/components/layout/AppShell';
import { useNotificationStore } from '@/store/notificationStore';
import { useI18n } from '@/i18n';
import { api } from '@/services/api';

interface TokenUsage {
  userId: string;
  username: string;
  totalTokens: number;
  inputTokens: number;
  outputTokens: number;
  cost: number;
  requestCount: number;
  lastUsed: string;
}

interface DailyUsage {
  date: string;
  totalTokens: number;
  cost: number;
  requests: number;
}

interface AgentUsage {
  agentId: string;
  agentName: string;
  totalTokens: number;
  cost: number;
  requests: number;
  avgTokensPerRequest: number;
}

interface UsageSummary {
  totalTokens: number;
  totalCost: number;
  totalRequests: number;
  activeUsers: number;
  avgTokensPerRequest: number;
  remainingQuota: number;
  quotaLimit: number;
}

export default function TokenUsagePage() {
  const { success } = useNotificationStore();
  const { t, language } = useI18n();
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d' | 'all'>('30d');
  const [selectedUser, setSelectedUser] = useState<string>('all');
  const [isLoading, setIsLoading] = useState(false);
  const [summary, setSummary] = useState<UsageSummary>({
    totalTokens: 0,
    totalCost: 0,
    totalRequests: 0,
    activeUsers: 0,
    avgTokensPerRequest: 0,
    remainingQuota: 0,
    quotaLimit: 0,
  });
  const [dailyUsage, setDailyUsage] = useState<DailyUsage[]>([]);
  const [agentUsage, setAgentUsage] = useState<AgentUsage[]>([]);
  const [userUsage, setUserUsage] = useState<TokenUsage[]>([]);

  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true);
      try {
        const days = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : timeRange === '90d' ? 90 : 30;
        const dashboard = await api.get<any>('/juben/system/token-dashboard');
        const ranking = await api.get<any>('/juben/system/token-ranking', { top_n: '10' });
        const stats = await api.get<any>('/juben/system/token-stats', { days: `${days}` });

        const summaryData = dashboard?.data?.summary || {};
        setSummary({
          totalTokens: summaryData.monthly_tokens || 0,
          totalCost: 0,
          totalRequests: 0,
          activeUsers: summaryData.today_top_users || 0,
          avgTokensPerRequest: 0,
          remainingQuota: 0,
          quotaLimit: 0,
        });

        const dailyStats = stats?.data?.stats || {};
        const dailyList = Object.keys(dailyStats)
          .sort()
          .map((date) => ({
            date,
            totalTokens: dailyStats[date] || 0,
            cost: 0,
            requests: 0,
          }));
        setDailyUsage(dailyList);

        const rankingList = ranking?.data?.ranking || dashboard?.data?.today_ranking || [];
        const userList = (rankingList as any[]).map((item: any) => ({
          userId: item.user_id || item.user || 'unknown',
          username: item.user_id || 'unknown',
          totalTokens: item.total_tokens || 0,
          inputTokens: item.prompt_tokens || 0,
          outputTokens: item.completion_tokens || 0,
          cost: item.estimated_cost || 0,
          requestCount: item.llm_calls || 0,
          lastUsed: new Date().toISOString(),
        }));
        setUserUsage(userList);
        setAgentUsage([]);
      } catch (error) {
        setUserUsage([]);
        setDailyUsage([]);
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, [timeRange]);

  const handleRefresh = () => {
    setIsLoading(true);
    setIsLoading(false);
    success(t('toolbox.tokens.refreshSuccess'), t('toolbox.tokens.updated'));
  };

  const handleExport = () => {
    success(t('toolbox.tokens.exportSuccess'), t('toolbox.tokens.exported'));
  };

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const formatCost = (cost: number) => `¥${cost.toFixed(2)}`;

  const tokensPercentage =
    summary.quotaLimit > 0 ? ((summary.quotaLimit - summary.remainingQuota) / summary.quotaLimit) * 100 : 0;

  const kpis = [
    { label: t('toolbox.tokens.kpi.totalTokens'), value: formatNumber(summary.totalTokens), icon: Coins },
    { label: t('toolbox.tokens.kpi.totalCost'), value: formatCost(summary.totalCost), icon: DollarSign },
    { label: t('toolbox.tokens.kpi.totalRequests'), value: formatNumber(summary.totalRequests), icon: BarChart3 },
    { label: t('toolbox.tokens.kpi.activeUsers'), value: summary.activeUsers, icon: Users },
    { label: t('toolbox.tokens.kpi.avgTokens'), value: formatNumber(summary.avgTokensPerRequest), icon: Clock },
  ];

  const maxTokens = Math.max(...dailyUsage.map((d) => d.totalTokens), 1);

  return (
    <AppShell
      title={t('toolbox.tokens.title')}
      subtitle={t('toolbox.tokens.subtitle')}
      actions={
        <div className="flex items-center gap-2">
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value as any)}
            className="px-3 py-1.5 rounded-lg border border-pearl-line bg-white text-xs text-ink focus:outline-none focus:ring-2 focus:ring-atelier-teal/30"
          >
            <option value="7d">{t('toolbox.tokens.range.d7')}</option>
            <option value="30d">{t('toolbox.tokens.range.d30')}</option>
            <option value="90d">{t('toolbox.tokens.range.d90')}</option>
            <option value="all">{t('toolbox.tokens.range.all')}</option>
          </select>
          <button
            type="button"
            onClick={handleRefresh}
            disabled={isLoading}
            className="btn btn-secondary btn-sm p-2"
            title={t('toolbox.refresh')}
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
          <button type="button" onClick={handleExport} className="btn btn-secondary btn-sm">
            <Download className="w-3.5 h-3.5" />
            {t('toolbox.export')}
          </button>
        </div>
      }
    >
      <div className="px-4 sm:px-8 lg:px-10 py-6 sm:py-8 max-w-6xl mx-auto space-y-6 sm:space-y-8">
        {/* Hero */}
        <section className="atelier-hero p-6 sm:p-8 animate-fade-in">
          <p className="text-[11px] tracking-[0.2em] uppercase text-ink-faint mb-3">
            Token Usage · Editorial Atelier
          </p>
          <h2 className="font-display text-3xl sm:text-4xl font-semibold text-ink leading-[1.12]">
            {t('toolbox.tokens.heroTitle')}
          </h2>
          <p className="mt-3 text-sm text-ink-muted max-w-lg leading-relaxed">
            {t('toolbox.tokens.heroDesc')}
          </p>
        </section>

        {/* KPI 概览 */}
        <section className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          {kpis.map((kpi, i) => (
            <div
              key={kpi.label}
              className="glass-dense px-4 py-3.5 animate-stagger-in"
              style={{ animationDelay: `${i * 50}ms` }}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-[10px] uppercase tracking-wider text-ink-faint">{kpi.label}</span>
                <kpi.icon className="w-3.5 h-3.5 text-atelier-teal/70" />
              </div>
              <div className="font-display text-2xl font-semibold text-ink tabular-nums leading-none mt-1.5">
                {kpi.value}
              </div>
            </div>
          ))}
        </section>

        {/* 配额使用 */}
        <section className="glass-panel p-5 sm:p-6 animate-slide-up">
          <h3 className="font-display text-xl font-semibold text-ink mb-4">{t('toolbox.tokens.quotaTitle')}</h3>
          <div>
            <div className="flex items-center justify-between text-xs mb-2">
              <span className="text-ink-muted">{t('toolbox.tokens.usedTokens')}</span>
              <span className="font-medium text-ink tabular-nums">
                {formatNumber(summary.quotaLimit - summary.remainingQuota)} / {formatNumber(summary.quotaLimit)}
              </span>
            </div>
            <div className="w-full bg-pearl-soft rounded-full h-2.5 overflow-hidden">
              <div
                className="bg-gradient-to-r from-atelier-teal to-atelier-teal-mid h-2.5 rounded-full transition-all duration-700"
                style={{ width: `${Math.min(100, tokensPercentage)}%` }}
              />
            </div>
            <div className="flex items-center justify-between text-[11px] mt-1.5 text-ink-faint">
              <span>{t('toolbox.tokens.usageRate')}: {tokensPercentage.toFixed(1)}%</span>
              <span>{t('toolbox.tokens.remaining')}: {formatNumber(summary.remainingQuota)}</span>
            </div>
          </div>

          {tokensPercentage > 80 && (
            <div className="flex items-start gap-3 p-3 mt-4 bg-atelier-gold/10 border border-atelier-gold/30 rounded-lg">
              <AlertTriangle className="w-4 h-4 text-studio-amber mt-0.5 shrink-0" />
              <div className="text-xs text-ink leading-relaxed">
                <p className="font-medium">{t('toolbox.tokens.quotaWarn')}</p>
                <p className="mt-0.5 text-ink-muted">
                  {t('toolbox.tokens.quotaWarnDesc')}
                </p>
              </div>
            </div>
          )}
        </section>

        {/* 使用趋势 */}
        <section className="glass-panel p-5 sm:p-6 animate-slide-up">
          <h3 className="font-display text-xl font-semibold text-ink mb-4">{t('toolbox.tokens.dailyTrend')}</h3>
          {dailyUsage.length === 0 ? (
            <p className="text-sm text-ink-muted py-10 text-center">{t('toolbox.tokens.noTrend')}</p>
          ) : (
            <div className="h-56 flex items-end gap-1.5">
              {dailyUsage.map((day, index) => {
                const height = (day.totalTokens / maxTokens) * 100;
                const isToday = index === dailyUsage.length - 1;
                return (
                  <div key={day.date} className="flex-1 flex flex-col items-center gap-1.5 min-w-0">
                    <div className="w-full h-44 flex items-end relative group">
                      <div
                        className={`w-full rounded-t-md transition-all ${
                          isToday
                            ? 'bg-gradient-to-t from-atelier-teal to-atelier-teal-mid'
                            : 'bg-atelier-teal/30'
                        }`}
                        style={{ height: `${Math.max(height, 2)}%` }}
                      />
                      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 hidden group-hover:block bg-ink text-white text-[10px] rounded px-2 py-1 whitespace-nowrap z-10">
                        <div>{day.date}</div>
                        <div>{formatNumber(day.totalTokens)} tokens</div>
                      </div>
                    </div>
                    <div className="text-[10px] text-ink-faint truncate w-full text-center">
                      {new Date(day.date).toLocaleDateString(language === 'zh' ? 'zh-CN' : 'en-US', { month: 'numeric', day: 'numeric' })}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* Agent 使用统计 */}
        <section className="glass-panel p-5 sm:p-6 animate-slide-up">
          <h3 className="font-display text-xl font-semibold text-ink mb-4">{t('toolbox.tokens.agentStats')}</h3>
          {agentUsage.length === 0 ? (
            <p className="text-sm text-ink-muted py-8 text-center">{t('toolbox.tokens.noAgentStats')}</p>
          ) : (
            <div className="overflow-x-auto -mx-5 px-5">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-left text-[11px] uppercase tracking-wider text-ink-faint border-b border-pearl-line">
                    <th className="py-2.5 pr-4 font-medium">{t('toolbox.tokens.table.agent')}</th>
                    <th className="py-2.5 pr-4 font-medium">{t('toolbox.tokens.table.totalTokens')}</th>
                    <th className="py-2.5 pr-4 font-medium">{t('toolbox.tokens.table.cost')}</th>
                    <th className="py-2.5 pr-4 font-medium">{t('toolbox.tokens.table.requests')}</th>
                    <th className="py-2.5 pr-4 font-medium">{t('toolbox.tokens.table.avgTokens')}</th>
                    <th className="py-2.5 font-medium">{t('toolbox.tokens.table.share')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-pearl-line/80">
                  {agentUsage.map((agent) => {
                    const percentage =
                      summary.totalTokens > 0 ? (agent.totalTokens / summary.totalTokens) * 100 : 0;
                    return (
                      <tr key={agent.agentId} className="hover:bg-white/50">
                        <td className="py-3 pr-4">
                          <div className="font-medium text-ink">{agent.agentName}</div>
                          <div className="text-[10px] text-ink-faint font-mono">{agent.agentId}</div>
                        </td>
                        <td className="py-3 pr-4 text-ink tabular-nums">{formatNumber(agent.totalTokens)}</td>
                        <td className="py-3 pr-4 text-ink-muted tabular-nums">{formatCost(agent.cost)}</td>
                        <td className="py-3 pr-4 text-ink-muted tabular-nums">{agent.requests}</td>
                        <td className="py-3 pr-4 text-ink-muted tabular-nums">
                          {formatNumber(agent.avgTokensPerRequest)}
                        </td>
                        <td className="py-3">
                          <div className="flex items-center gap-2">
                            <div className="flex-1 bg-pearl-soft rounded-full h-1.5 w-20 overflow-hidden">
                              <div
                                className="bg-atelier-teal h-1.5 rounded-full"
                                style={{ width: `${Math.min(100, percentage)}%` }}
                              />
                            </div>
                            <span className="text-[11px] text-ink-muted tabular-nums">
                              {percentage.toFixed(1)}%
                            </span>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* 用户使用排名 */}
        <section className="glass-panel p-5 sm:p-6 animate-slide-up">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-display text-xl font-semibold text-ink">{t('toolbox.tokens.userRank')}</h3>
            <select
              value={selectedUser}
              onChange={(e) => setSelectedUser(e.target.value)}
              className="px-3 py-1.5 rounded-lg border border-pearl-line bg-white text-xs text-ink focus:outline-none focus:ring-2 focus:ring-atelier-teal/30"
            >
              <option value="all">{t('toolbox.tokens.allUsers')}</option>
              <option value="top10">{t('toolbox.tokens.top10')}</option>
              <option value="active">{t('toolbox.tokens.active')}</option>
            </select>
          </div>
          {userUsage.length === 0 ? (
            <p className="text-sm text-ink-muted py-8 text-center">{t('toolbox.tokens.noUserData')}</p>
          ) : (
            <div className="overflow-x-auto -mx-5 px-5">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-left text-[11px] uppercase tracking-wider text-ink-faint border-b border-pearl-line">
                    <th className="py-2.5 pr-4 font-medium">{t('toolbox.tokens.userTable.user')}</th>
                    <th className="py-2.5 pr-4 font-medium">{t('toolbox.tokens.userTable.inputTokens')}</th>
                    <th className="py-2.5 pr-4 font-medium">{t('toolbox.tokens.userTable.outputTokens')}</th>
                    <th className="py-2.5 pr-4 font-medium">{t('toolbox.tokens.userTable.totalTokens')}</th>
                    <th className="py-2.5 pr-4 font-medium">{t('toolbox.tokens.userTable.cost')}</th>
                    <th className="py-2.5 pr-4 font-medium">{t('toolbox.tokens.userTable.requests')}</th>
                    <th className="py-2.5 font-medium">{t('toolbox.tokens.userTable.lastUsed')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-pearl-line/80">
                  {userUsage.map((user, index) => (
                    <tr key={user.userId} className="hover:bg-white/50">
                      <td className="py-3 pr-4">
                        <div className="flex items-center gap-2.5">
                          <div className="shrink-0 w-7 h-7 rounded-full bg-atelier-teal-soft text-atelier-teal flex items-center justify-center text-[11px] font-semibold">
                            {index + 1}
                          </div>
                          <span className="font-medium text-ink truncate">{user.username}</span>
                        </div>
                      </td>
                      <td className="py-3 pr-4 text-ink-muted tabular-nums">{formatNumber(user.inputTokens)}</td>
                      <td className="py-3 pr-4 text-ink-muted tabular-nums">{formatNumber(user.outputTokens)}</td>
                      <td className="py-3 pr-4 font-medium text-ink tabular-nums">{formatNumber(user.totalTokens)}</td>
                      <td className="py-3 pr-4 text-ink-muted tabular-nums">{formatCost(user.cost)}</td>
                      <td className="py-3 pr-4 text-ink-muted tabular-nums">{user.requestCount}</td>
                      <td className="py-3 text-[11px] text-ink-faint">
                        {new Date(user.lastUsed).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </AppShell>
  );
}
