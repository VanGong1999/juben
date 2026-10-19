/**
 * A/B 测试管理页面
 * 用于配置和管理 Agent 的 A/B 测试
 */

import React, { useEffect, useMemo, useState } from 'react';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import StatusBar from '@/components/layout/StatusBar';
import MobileMenu from '@/components/common/MobileMenu';
import SettingsModal from '@/components/modals/SettingsModal';
import {
  GitCompare,
  Plus,
  Clock,
  TrendingUp,
  Users,
  RefreshCw,
  Trophy,
} from 'lucide-react';
import { useNotificationStore } from '@/store/notificationStore';
import { getAgents } from '@/services/agentService';
import { getEvolutionStatus, getABTestStatus, promoteVersion } from '@/services/evolutionService';
import type { Agent } from '@/types';
import { useI18n } from '@/i18n';

interface ABTestSummary {
  agent_name: string;
  config?: any;
  traffic_stats?: any;
  performance_comparison?: any;
}

const ABTestPage: React.FC = () => {
  const { t, language } = useI18n();
  const { success, error } = useNotificationStore();
  const [activeTab, setActiveTab] = useState<'tests' | 'create' | 'results'>('tests');
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState('');
  const [tests, setTests] = useState<ABTestSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [detail, setDetail] = useState<ABTestSummary | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string>('');

  useEffect(() => {
    const init = async () => {
      try {
        const list = await getAgents();
        setAgents(list);
        if (!selectedAgent && list.length > 0) {
          setSelectedAgent(list[0].name);
        }
      } catch {
        setAgents([]);
      }
    };
    init();
  }, []);

  const loadTests = async () => {
    setIsLoading(true);
    try {
      const response = await getEvolutionStatus();
      const abTests = (response.data?.active_ab_tests || []) as ABTestSummary[];
      setTests(abTests);
      setLastUpdated(new Date().toLocaleString(language === 'zh' ? 'zh-CN' : 'en-US'));
    } catch (err: any) {
      error(t('admin.abTest.toast.loadFailed'), err?.message || t('admin.abTest.toast.loadTestsFailed'));
      setTests([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadTests();
  }, []);

  useEffect(() => {
    const loadDetail = async () => {
      if (!selectedAgent) return;
      setIsDetailLoading(true);
      try {
        const res = await getABTestStatus(selectedAgent);
        if (res.success) {
          setDetail(res.data as ABTestSummary);
        } else {
          setDetail(null);
        }
      } catch (err: any) {
        setDetail(null);
        error(t('admin.abTest.toast.loadFailed'), err?.message || t('admin.abTest.toast.loadDetailFailed'));
      } finally {
        setIsDetailLoading(false);
      }
    };
    loadDetail();
  }, [selectedAgent]);

  const agentNameMap = useMemo(() => {
    const map = new Map<string, string>();
    agents.forEach((agent) => map.set(agent.name, agent.displayName || agent.name));
    return map;
  }, [agents]);

  const totalTests = tests.length;
  const totalTraffic = tests.reduce((acc, item) => acc + (item.traffic_stats?.total_requests || 0), 0);
  const avgLift = tests.length
    ? tests.reduce((acc, item) => acc + (item.performance_comparison?.comparison?.rating_diff || 0), 0) / tests.length
    : 0;

  const handlePromote = async (agentName: string, versionId?: string) => {
    if (!versionId) {
      error(t('admin.abTest.toast.promoteFailed'), t('admin.abTest.toast.noVersion'));
      return;
    }
    try {
      await promoteVersion(agentName, versionId);
      success(t('admin.abTest.toast.promoted'), t('admin.abTest.toast.promotedDesc'));
      loadTests();
      if (selectedAgent === agentName) {
        const res = await getABTestStatus(agentName);
        setDetail(res.data as ABTestSummary);
      }
    } catch (err: any) {
      error(t('admin.abTest.toast.promoteFailed'), err?.message || t('admin.abTest.toast.promoteError'));
    }
  };

  const renderStatusBadge = (comparison?: any) => {
    if (!comparison) return <span className="text-xs text-gray-500">{t('admin.abTest.noData')}</span>;
    if (comparison?.significant_improvement) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded bg-green-100 text-green-700">
          <Trophy className="w-3 h-3" />
          {t('admin.abTest.significant')}
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded bg-gray-100 text-gray-600">
        <Clock className="w-3 h-3" />
        {t('admin.abTest.waitingData')}
      </span>
    );
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
                  <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-xl flex items-center justify-center">
                    <GitCompare className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h1 className="text-2xl font-bold text-gray-900">{t('admin.abTest.title')}</h1>
                    <p className="text-sm text-gray-500 mt-1">{t('admin.abTest.subtitle')}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={loadTests}
                    className="flex items-center gap-2 px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm"
                  >
                    <RefreshCw className={isLoading ? 'w-4 h-4 animate-spin' : 'w-4 h-4'} />
                    {t('admin.refresh')}
                  </button>
                  <button
                    onClick={() => setActiveTab('create')}
                    className="flex items-center gap-2 px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 transition-all"
                  >
                    <Plus className="w-4 h-4" />
                    {t('admin.abTest.configGuide')}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div className="max-w-7xl mx-auto px-6 py-8">
            {/* Tabs */}
            <div className="flex gap-2 mb-6">
              {[
                { key: 'tests', label: t('admin.abTest.tab.tests') },
                { key: 'results', label: t('admin.abTest.tab.results') },
                { key: 'create', label: t('admin.abTest.tab.create') },
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

            {activeTab === 'tests' && (
              <>
                {/* 统计卡片 */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
                  <div className="bg-white rounded-lg shadow p-5">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-500">{t('admin.abTest.activeTests')}</p>
                        <p className="text-2xl font-bold text-gray-900 mt-1">{totalTests}</p>
                      </div>
                      <GitCompare className="w-8 h-8 text-blue-500" />
                    </div>
                  </div>
                  <div className="bg-white rounded-lg shadow p-5">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-500">{t('admin.abTest.totalRequests')}</p>
                        <p className="text-2xl font-bold text-gray-900 mt-1">{totalTraffic}</p>
                      </div>
                      <Users className="w-8 h-8 text-green-500" />
                    </div>
                  </div>
                  <div className="bg-white rounded-lg shadow p-5">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-500">{t('admin.abTest.avgLift')}</p>
                        <p className="text-2xl font-bold text-gray-900 mt-1">
                          {avgLift >= 0 ? '+' : ''}{avgLift.toFixed(2)}
                        </p>
                      </div>
                      <TrendingUp className="w-8 h-8 text-purple-500" />
                    </div>
                  </div>
                  <div className="bg-white rounded-lg shadow p-5">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-500">{t('admin.abTest.lastUpdated')}</p>
                        <p className="text-sm font-medium text-gray-900 mt-2">{lastUpdated || '—'}</p>
                      </div>
                      <Clock className="w-8 h-8 text-gray-400" />
                    </div>
                  </div>
                </div>

                {/* 测试列表 */}
                <div className="bg-white rounded-lg shadow">
                  <div className="px-6 py-4 border-b border-gray-200">
                    <h2 className="text-lg font-semibold text-gray-900">{t('admin.abTest.testList')}</h2>
                  </div>
                  <div className="divide-y divide-gray-100">
                    {tests.length === 0 ? (
                      <div className="p-8 text-center text-sm text-gray-500">
                        {t('admin.abTest.noTests')}
                      </div>
                    ) : (
                      tests.map((test) => {
                        const comparison = test.performance_comparison || {};
                        const config = test.config || {};
                        const traffic = test.traffic_stats || {};
                        return (
                          <div key={test.agent_name} className="px-6 py-4 flex items-center justify-between">
                            <div>
                              <div className="flex items-center gap-3">
                                <h3 className="text-sm font-semibold text-gray-900">
                                  {agentNameMap.get(test.agent_name) || test.agent_name}
                                </h3>
                                {renderStatusBadge(comparison?.comparison)}
                              </div>
                              <div className="mt-2 text-xs text-gray-500 space-x-4">
                                <span>{t('admin.abTest.traffic', { rate: config.traffic_percentage ?? 0 })}</span>
                                <span>{t('admin.abTest.requests', { count: traffic.total_requests ?? 0 })}</span>
                                <span>{t('admin.abTest.ratingLift', { lift: (comparison?.comparison?.rating_diff ?? 0).toFixed(2) })}</span>
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => {
                                  setSelectedAgent(test.agent_name);
                                  setActiveTab('results');
                                }}
                                className="px-3 py-1.5 text-xs bg-gray-100 hover:bg-gray-200 rounded"
                              >
                                {t('admin.abTest.viewDetail')}
                              </button>
                              {comparison?.comparison?.significant_improvement && config.treatment_version_id && (
                                <button
                                  onClick={() => handlePromote(test.agent_name, config.treatment_version_id)}
                                  className="px-3 py-1.5 text-xs bg-green-600 text-white rounded hover:bg-green-700"
                                >
                                  {t('admin.abTest.promoteVersion')}
                                </button>
                              )}
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              </>
            )}

            {activeTab === 'results' && (
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900">{t('admin.abTest.resultDetail')}</h2>
                    <p className="text-sm text-gray-500">{t('admin.abTest.resultDetailDesc')}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <select
                      value={selectedAgent}
                      onChange={(e) => setSelectedAgent(e.target.value)}
                      className="text-sm border rounded px-2 py-1"
                    >
                      {agents.map((agent) => (
                        <option key={agent.id} value={agent.name}>
                          {agent.displayName || agent.name}
                        </option>
                      ))}
                    </select>
                    <button
                      onClick={() => selectedAgent && getABTestStatus(selectedAgent).then((res) => setDetail(res.data))}
                      className="px-3 py-1.5 text-xs bg-gray-100 rounded hover:bg-gray-200"
                    >
                      {t('admin.abTest.refreshDetail')}
                    </button>
                  </div>
                </div>

                {isDetailLoading ? (
                  <div className="text-sm text-gray-500">{t('admin.loading')}</div>
                ) : !detail?.config ? (
                  <div className="text-sm text-gray-500">{t('admin.abTest.noConfig')}</div>
                ) : (
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <div className="lg:col-span-2">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="border rounded-lg p-4">
                          <h3 className="text-sm font-semibold text-gray-900">{t('admin.abTest.controlGroup')}</h3>
                          <p className="text-xs text-gray-500 mt-1">{t('admin.abTest.versionLabel', { version: detail?.performance_comparison?.control?.version || '—' })}</p>
                          <div className="mt-3 text-xs text-gray-600 space-y-1">
                            <div>{t('admin.abTest.avgRatingLabel', { score: detail?.performance_comparison?.control?.avg_rating ?? 0 })}</div>
                            <div>{t('admin.abTest.feedbackLabel', { count: detail?.performance_comparison?.control?.total_feedbacks ?? 0 })}</div>
                            <div>{t('admin.abTest.editRatioLabel', { ratio: detail?.performance_comparison?.control?.edit_ratio_avg ?? 0 })}</div>
                          </div>
                        </div>
                        <div className="border rounded-lg p-4">
                          <h3 className="text-sm font-semibold text-gray-900">{t('admin.abTest.treatmentGroup')}</h3>
                          <p className="text-xs text-gray-500 mt-1">{t('admin.abTest.versionLabel', { version: detail?.performance_comparison?.treatment?.version || '—' })}</p>
                          <div className="mt-3 text-xs text-gray-600 space-y-1">
                            <div>{t('admin.abTest.avgRatingLabel', { score: detail?.performance_comparison?.treatment?.avg_rating ?? 0 })}</div>
                            <div>{t('admin.abTest.feedbackLabel', { count: detail?.performance_comparison?.treatment?.total_feedbacks ?? 0 })}</div>
                            <div>{t('admin.abTest.editRatioLabel', { ratio: detail?.performance_comparison?.treatment?.edit_ratio_avg ?? 0 })}</div>
                          </div>
                        </div>
                      </div>

                      <div className="mt-6 border rounded-lg p-4">
                        <h3 className="text-sm font-semibold text-gray-900">{t('admin.abTest.conclusion')}</h3>
                        <div className="mt-3 text-xs text-gray-600 space-y-1">
                          <div>{t('admin.abTest.ratingDiff', { diff: detail?.performance_comparison?.comparison?.rating_diff ?? 0 })}</div>
                          <div>{t('admin.abTest.editRatioDiff', { diff: detail?.performance_comparison?.comparison?.edit_ratio_diff ?? 0 })}</div>
                          <div>
                            {t('admin.abTest.significantImprovement', { value: detail?.performance_comparison?.comparison?.significant_improvement ? t('admin.abTest.yes') : t('admin.abTest.no') })}
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="border rounded-lg p-4">
                      <h3 className="text-sm font-semibold text-gray-900">{t('admin.abTest.trafficConfig')}</h3>
                      <div className="mt-3 text-xs text-gray-600 space-y-2">
                        <div>{t('admin.abTest.traffic', { rate: detail?.config?.traffic_percentage ?? 0 })}</div>
                        <div>{t('admin.abTest.controlVersion', { version: detail?.config?.control_version_id || '—' })}</div>
                        <div>{t('admin.abTest.treatmentVersion', { version: detail?.config?.treatment_version_id || '—' })}</div>
                        <div>{t('admin.abTest.totalRequest', { count: detail?.traffic_stats?.total_requests ?? 0 })}</div>
                        <div>{t('admin.abTest.treatmentRatio', { ratio: ((detail?.traffic_stats?.treatment_ratio ?? 0) * 100).toFixed(1) })}</div>
                      </div>
                      {detail?.performance_comparison?.comparison?.significant_improvement && detail?.config?.treatment_version_id && (
                        <button
                          onClick={() => handlePromote(selectedAgent, detail?.config?.treatment_version_id)}
                          className="mt-4 w-full px-3 py-2 text-xs bg-green-600 text-white rounded hover:bg-green-700"
                        >
                          {t('admin.abTest.promoteTreatment')}
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'create' && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold text-gray-900">{t('admin.abTest.configTitle')}</h2>
                <p className="text-sm text-gray-500 mt-2">
                  {t('admin.abTest.configDesc')}
                </p>
                <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="border rounded-lg p-4">
                    <h3 className="text-sm font-semibold text-gray-900">{t('admin.abTest.startupFlow')}</h3>
                    <ol className="mt-3 text-xs text-gray-600 space-y-1 list-decimal list-inside">
                      <li>{t('admin.abTest.step1')}</li>
                      <li>{t('admin.abTest.step2')}</li>
                      <li>{t('admin.abTest.step3')}</li>
                    </ol>
                  </div>
                  <div className="border rounded-lg p-4">
                    <h3 className="text-sm font-semibold text-gray-900">{t('admin.abTest.faq')}</h3>
                    <p className="mt-3 text-xs text-gray-600">
                      {t('admin.abTest.faqDesc')}
                    </p>
                  </div>
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

export default ABTestPage;