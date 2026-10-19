/**
 * 进化/优化系统页面
 * 监控和管理 Agent 进化过程
 */

import React, { useEffect, useMemo, useState } from 'react';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import StatusBar from '@/components/layout/StatusBar';
import MobileMenu from '@/components/common/MobileMenu';
import SettingsModal from '@/components/modals/SettingsModal';
import {
  TrendingUp,
  GitBranch,
  RefreshCw,
  Sparkles,
  Target,
  CheckCircle2,
  XCircle,
  AlertCircle,
} from 'lucide-react';
import { useNotificationStore } from '@/store/notificationStore';
import { getAgents } from '@/services/agentService';
import { getEvolutionStatus, triggerEvolution, getVersions, getEvolutionReport } from '@/services/evolutionService';
import type { Agent } from '@/types';
import { useI18n } from '@/i18n';

interface AgentPerformance {
  agentId: string;
  agentName: string;
  score: number;
  totalFeedbacks: number;
  status: 'optimized' | 'needs_evolution' | 'testing';
  reason?: string;
}

const EvolutionPage: React.FC = () => {
  const { t, language } = useI18n();
  const { success, error } = useNotificationStore();
  const [activeTab, setActiveTab] = useState<'overview' | 'history' | 'settings'>('overview');
  const [isLoading, setIsLoading] = useState(false);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [agentPerformance, setAgentPerformance] = useState<AgentPerformance[]>([]);
  const [stats, setStats] = useState({
    totalAgents: 0,
    needEvolution: 0,
    activeABTests: 0,
    avgRating: 0,
  });
  const [optimizerRunning, setOptimizerRunning] = useState(false);
  const [lastUpdated, setLastUpdated] = useState('');

  const [selectedAgent, setSelectedAgent] = useState('');
  const [versions, setVersions] = useState<any[]>([]);
  const [versionStatus, setVersionStatus] = useState<'all' | 'active' | 'candidate' | 'archived'>('all');

  const [reportDate, setReportDate] = useState(() => {
    const now = new Date();
    return now.toISOString().slice(0, 10);
  });
  const [report, setReport] = useState<any | null>(null);
  const [reportError, setReportError] = useState('');

  useEffect(() => {
    getAgents().then(setAgents).catch(() => setAgents([]));
  }, []);

  const agentNameMap = useMemo(() => {
    const map = new Map<string, string>();
    agents.forEach((agent) => map.set(agent.name, agent.displayName || agent.name));
    return map;
  }, [agents]);

  const loadStatus = async () => {
    setIsLoading(true);
    try {
      const response = await getEvolutionStatus();
      const data = response.data || {};
      const triggers = data.evolution_triggers || [];
      const activeABTests = data.active_ab_tests || [];

      const totalAgents = triggers.length;
      const needEvolution = triggers.filter((t: any) => t.should_evolve).length;
      const avgRating = triggers.length
        ? triggers.reduce((acc: number, item: any) => acc + (item.avg_rating || 0), 0) / triggers.length
        : 0;

      setStats({
        totalAgents,
        needEvolution,
        activeABTests: activeABTests.length,
        avgRating,
      });

      setOptimizerRunning(Boolean(data.optimizer_running));
      setLastUpdated(new Date().toLocaleString(language === 'zh' ? 'zh-CN' : 'en-US'));

      const perf: AgentPerformance[] = triggers.map((item: any) => ({
        agentId: item.agent_name,
        agentName: agentNameMap.get(item.agent_name) || item.agent_name,
        score: item.avg_rating || 0,
        totalFeedbacks: item.total_feedbacks || 0,
        status: item.should_evolve ? 'needs_evolution' : 'optimized',
        reason: item.reason,
      }));

      setAgentPerformance(perf);
      if (!selectedAgent && perf.length > 0) {
        setSelectedAgent(perf[0].agentId);
      }
    } catch (err: any) {
      error(t('admin.evolution.toast.loadFailed'), err?.message || t('admin.evolution.toast.loadStatusFailed'));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadStatus();
  }, [agents.length]);

  useEffect(() => {
    const loadVersions = async () => {
      if (!selectedAgent) return;
      try {
        const response = await getVersions(selectedAgent, versionStatus === 'all' ? undefined : versionStatus);
        setVersions(response.data || []);
      } catch {
        setVersions([]);
      }
    };
    loadVersions();
  }, [selectedAgent, versionStatus]);

  const handleTriggerEvolution = async (agentId: string) => {
    setIsLoading(true);
    try {
      await triggerEvolution(agentId);
      success(t('admin.evolution.toast.evolutionStarted'), t('admin.evolution.toast.evolutionQueued'));
      loadStatus();
    } catch (err: any) {
      error(t('admin.evolution.toast.startFailed'), err?.message || t('admin.evolution.toast.startEvolutionFailed'));
    } finally {
      setIsLoading(false);
    }
  };

  const loadReport = async () => {
    setReport(null);
    setReportError('');
    try {
      const compactDate = reportDate.replace(/-/g, '');
      const response = await getEvolutionReport(compactDate);
      setReport(response.data || null);
      success(t('admin.evolution.toast.reportLoaded'), t('admin.evolution.toast.reportDate', { date: reportDate }));
    } catch (err: any) {
      setReportError(err?.message || t('admin.evolution.toast.reportFailed'));
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'optimized':
        return <CheckCircle2 className="w-5 h-5 text-green-500" />;
      case 'needs_evolution':
        return <AlertCircle className="w-5 h-5 text-yellow-500" />;
      case 'testing':
        return <RefreshCw className="w-5 h-5 text-blue-500 animate-spin" />;
      default:
        return <XCircle className="w-5 h-5 text-gray-400" />;
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'optimized':
        return '已优化';
      case 'needs_evolution':
        return '需要进化';
      case 'testing':
        return '测试中';
      default:
        return '未知';
    }
  };

  return (
    <div className="flex h-screen bg-gray-50">
      <MobileMenu />
      <Sidebar />

      <div className="flex flex-col flex-1 overflow-hidden">
        <Header />
        <StatusBar />

        <div className="flex-1 overflow-y-auto">
          {/* 页面头部 */}
          <div className="bg-white border-b border-gray-200">
            <div className="max-w-7xl mx-auto px-6 py-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-pink-500 rounded-xl flex items-center justify-center">
                    <Sparkles className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h1 className="text-2xl font-bold text-gray-900">{t('admin.evolution.title')}</h1>
                    <p className="text-sm text-gray-500 mt-1">{t('admin.evolution.subtitle')}</p>
                  </div>
                </div>
                <button
                  onClick={loadStatus}
                  className="flex items-center gap-2 px-3 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 text-sm"
                >
                  <RefreshCw className={isLoading ? 'w-4 h-4 animate-spin' : 'w-4 h-4'} />
                  {t('admin.refresh')}
                </button>
              </div>
            </div>
          </div>

          <div className="max-w-7xl mx-auto px-6 py-8">
            {/* Tabs */}
            <div className="flex gap-2 mb-6">
              {[
                { key: 'overview', label: t('admin.evolution.tab.overview') },
                { key: 'history', label: t('admin.evolution.tab.history') },
                { key: 'settings', label: t('admin.evolution.tab.settings') },
              ].map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key as any)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    activeTab === tab.key ? 'bg-black text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {activeTab === 'overview' && (
              <>
                {/* 统计卡片 */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
                  <div className="bg-white rounded-lg shadow p-5">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-500">{t('admin.evolution.agentCount')}</p>
                        <p className="text-2xl font-bold text-gray-900 mt-1">{stats.totalAgents}</p>
                      </div>
                      <Target className="w-8 h-8 text-blue-500" />
                    </div>
                  </div>
                  <div className="bg-white rounded-lg shadow p-5">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-500">{t('admin.evolution.pendingEvolution')}</p>
                        <p className="text-2xl font-bold text-gray-900 mt-1">{stats.needEvolution}</p>
                      </div>
                      <AlertCircle className="w-8 h-8 text-yellow-500" />
                    </div>
                  </div>
                  <div className="bg-white rounded-lg shadow p-5">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-500">{t('admin.evolution.abTests')}</p>
                        <p className="text-2xl font-bold text-gray-900 mt-1">{stats.activeABTests}</p>
                      </div>
                      <GitBranch className="w-8 h-8 text-purple-500" />
                    </div>
                  </div>
                  <div className="bg-white rounded-lg shadow p-5">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-500">{t('admin.evolution.avgRating')}</p>
                        <p className="text-2xl font-bold text-gray-900 mt-1">{stats.avgRating.toFixed(2)}</p>
                      </div>
                      <TrendingUp className="w-8 h-8 text-green-500" />
                    </div>
                  </div>
                </div>

                {/* Agent 表格 */}
                <div className="bg-white rounded-lg shadow">
                  <div className="px-6 py-4 border-b border-gray-200">
                    <h2 className="text-lg font-semibold text-gray-900">{t('admin.evolution.agentStatus')}</h2>
                  </div>
                  <div className="divide-y divide-gray-100">
                    {agentPerformance.length === 0 ? (
                      <div className="p-8 text-sm text-gray-500 text-center">{t('admin.evolution.noData')}</div>
                    ) : (
                      agentPerformance.map((agent) => (
                        <div key={agent.agentId} className="px-6 py-4 flex items-center justify-between">
                          <div>
                            <div className="flex items-center gap-2">
                              {getStatusIcon(agent.status)}
                              <span className="text-sm font-semibold text-gray-900">{agent.agentName}</span>
                              <span className="text-xs text-gray-500">({agent.agentId})</span>
                            </div>
                            <div className="mt-2 text-xs text-gray-500 space-x-4">
                              <span>{t('admin.evolution.rating', { score: agent.score.toFixed(2) })}</span>
                              <span>{t('admin.evolution.feedback', { count: agent.totalFeedbacks })}</span>
                              <span>{agent.reason || t('admin.evolution.statusNormal')}</span>
                            </div>
                          </div>
                          <div className="flex items-center gap-3">
                            {agent.status === 'needs_evolution' && (
                              <button
                                onClick={() => handleTriggerEvolution(agent.agentId)}
                                className="px-3 py-1.5 text-xs bg-black text-white rounded hover:bg-gray-800"
                              >
                                {t('admin.evolution.triggerEvolution')}
                              </button>
                            )}
                            <button
                              onClick={() => {
                                setSelectedAgent(agent.agentId);
                                setActiveTab('history');
                              }}
                              className="px-3 py-1.5 text-xs bg-gray-100 rounded hover:bg-gray-200"
                            >
                              {t('admin.evolution.viewVersions')}
                            </button>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                <div className="mt-4 text-xs text-gray-500">{t('admin.evolution.lastUpdated', { time: lastUpdated || '—' })}</div>
              </>
            )}

            {activeTab === 'history' && (
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-4">
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900">{t('admin.evolution.promptHistory')}</h2>
                    <p className="text-sm text-gray-500">{t('admin.evolution.promptHistoryDesc')}</p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <select
                      value={selectedAgent}
                      onChange={(e) => setSelectedAgent(e.target.value)}
                      className="text-sm border rounded px-2 py-1"
                    >
                      {agentPerformance.map((agent) => (
                        <option key={agent.agentId} value={agent.agentId}>
                          {agent.agentName}
                        </option>
                      ))}
                    </select>
                    <select
                      value={versionStatus}
                      onChange={(e) => setVersionStatus(e.target.value as any)}
                      className="text-sm border rounded px-2 py-1"
                    >
                      <option value="all">{t('admin.evolution.allStatus')}</option>
                      <option value="active">{t('admin.evolution.active')}</option>
                      <option value="candidate">{t('admin.evolution.candidate')}</option>
                      <option value="archived">{t('admin.evolution.archived')}</option>
                    </select>
                  </div>
                </div>

                {versions.length === 0 ? (
                  <div className="text-sm text-gray-500">{t('admin.evolution.noVersions')}</div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="min-w-full text-sm">
                      <thead>
                        <tr className="text-left text-gray-500">
                          <th className="px-4 py-2">{t('admin.evolution.version')}</th>
                          <th className="px-4 py-2">{t('admin.status')}</th>
                          <th className="px-4 py-2">{t('admin.evolution.score')}</th>
                          <th className="px-4 py-2">{t('admin.evolution.feedbackCount')}</th>
                          <th className="px-4 py-2">{t('admin.evolution.createdAt')}</th>
                          <th className="px-4 py-2">{t('admin.evolution.changeNote')}</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {versions.map((item: any) => (
                          <tr key={item.version_id} className="text-gray-700">
                            <td className="px-4 py-2 font-medium">{item.version}</td>
                            <td className="px-4 py-2">{item.status}</td>
                            <td className="px-4 py-2">{(item.avg_rating || 0).toFixed(2)}</td>
                            <td className="px-4 py-2">{item.total_feedbacks || 0}</td>
                            <td className="px-4 py-2">{item.created_at ? new Date(item.created_at).toLocaleString(language === 'zh' ? 'zh-CN' : 'en-US') : '-'}</td>
                            <td className="px-4 py-2 text-xs text-gray-500">{item.changelog || item.optimization_reason || '-'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'settings' && (
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900">{t('admin.evolution.systemStatus')}</h2>
                    <p className="text-sm text-gray-500">{t('admin.evolution.systemStatusDesc')}</p>
                  </div>
                  <div className="inline-flex items-center gap-2 text-sm">
                    <span>{t('admin.evolution.optimizer')}</span>
                    <span className={`px-2 py-1 rounded ${optimizerRunning ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>
                      {optimizerRunning ? t('admin.evolution.running') : t('admin.evolution.notStarted')}
                    </span>
                  </div>
                </div>

                <div className="border rounded-lg p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <input
                      type="date"
                      value={reportDate}
                      onChange={(e) => setReportDate(e.target.value)}
                      className="text-sm border rounded px-2 py-1"
                    />
                    <button
                      onClick={loadReport}
                      className="px-3 py-1.5 text-xs bg-black text-white rounded hover:bg-gray-800"
                    >
                      {t('admin.evolution.loadReport')}
                    </button>
                  </div>
                  {reportError && <div className="text-xs text-red-500 mt-3">{reportError}</div>}
                  {report && (
                    <pre className="mt-3 text-xs bg-gray-50 rounded p-3 overflow-auto max-h-64">
{JSON.stringify(report, null, 2)}
                    </pre>
                  )}
                  {!report && !reportError && (
                    <div className="text-xs text-gray-500 mt-3">{t('admin.evolution.selectDate')}</div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <SettingsModal />
    </div>
  );
};

export default EvolutionPage;