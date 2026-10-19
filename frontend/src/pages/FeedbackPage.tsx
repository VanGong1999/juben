/**
 * 反馈系统页面
 * 收集和查看用户反馈，管理黄金样本
 */

import React, { useEffect, useMemo, useState } from 'react';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import StatusBar from '@/components/layout/StatusBar';
import MobileMenu from '@/components/common/MobileMenu';
import SettingsModal from '@/components/modals/SettingsModal';
import {
  ThumbsUp,
  ThumbsDown,
  Star,
  MessageSquare,
  TrendingUp,
  Award,
  Download,
  Calendar,
  RefreshCw,
  Search,
} from 'lucide-react';
import { useNotificationStore } from '@/store/notificationStore';
import { getAgents } from '@/services/agentService';
import { getFeedbackList, getFeedbackStatistics, getGoldSamples } from '@/services/feedbackService';
import type { Agent } from '@/types';
import { useI18n } from '@/i18n';

interface FeedbackItem {
  trace_id: string;
  agent_name: string;
  user_input: string;
  ai_output: string;
  feedback_type: string;
  user_rating?: number;
  timestamp?: string;
  is_gold_sample?: boolean;
}

interface FeedbackStats {
  totalFeedback: number;
  positiveRate: number;
  avgRating: number;
  goldSamples: number;
  thisWeekFeedback: number;
}

const FeedbackPage: React.FC = () => {
  const { t, language } = useI18n();
  const { success, error } = useNotificationStore();
  const [activeTab, setActiveTab] = useState<'feedback' | 'samples' | 'analytics'>('feedback');
  const [selectedType, setSelectedType] = useState<'all' | 'like' | 'dislike' | 'rating' | 'refinement'>('all');
  const [selectedAgent, setSelectedAgent] = useState('');
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(false);
  const [statsLoading, setStatsLoading] = useState(false);
  const [goldLoading, setGoldLoading] = useState(false);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [feedback, setFeedback] = useState<FeedbackItem[]>([]);
  const [stats, setStats] = useState<FeedbackStats>({
    totalFeedback: 0,
    positiveRate: 0,
    avgRating: 0,
    goldSamples: 0,
    thisWeekFeedback: 0,
  });
  const [goldQuery, setGoldQuery] = useState('');
  const [goldSamples, setGoldSamples] = useState<any[]>([]);

  useEffect(() => {
    getAgents().then(setAgents).catch(() => setAgents([]));
  }, []);

  const loadFeedback = async () => {
    setLoading(true);
    try {
      const res = await getFeedbackList({ agent_name: selectedAgent || undefined, limit: 200 });
      setFeedback(res.data || []);
    } catch (err: any) {
      error(t('admin.feedback.toast.loadFailed'), err?.message || t('admin.feedback.toast.loadListFailed'));
      setFeedback([]);
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    setStatsLoading(true);
    try {
      const res = await getFeedbackStatistics({ agent_name: selectedAgent || undefined, days });
      const data = res.data || {};
      const totalFeedback = data.total_feedbacks || 0;
      const goldSamples = data.gold_samples || 0;
      setStats((prev) => ({
        ...prev,
        totalFeedback,
        goldSamples,
      }));
    } catch (err: any) {
      error(t('admin.feedback.toast.loadFailed'), err?.message || t('admin.feedback.toast.loadStatsFailed'));
    } finally {
      setStatsLoading(false);
    }
  };

  useEffect(() => {
    loadFeedback();
    loadStats();
  }, [selectedAgent, days]);

  const loadGoldSamples = async () => {
    setGoldLoading(true);
    try {
      const res = await getGoldSamples({
        agent_name: selectedAgent || undefined,
        query: goldQuery.trim() || undefined,
        top_k: 10,
      });
      setGoldSamples(res.data || []);
    } catch (err: any) {
      error(t('admin.feedback.toast.loadFailed'), err?.message || t('admin.feedback.toast.loadGoldFailed'));
      setGoldSamples([]);
    } finally {
      setGoldLoading(false);
    }
  };

  useEffect(() => {
    const totalRatings = feedback.filter((item) => typeof item.user_rating === 'number');
    const avgRating = totalRatings.length
      ? totalRatings.reduce((acc, item) => acc + (item.user_rating || 0), 0) / totalRatings.length
      : 0;

    const positiveCount = feedback.filter(
      (item) => item.feedback_type === 'like' || (item.user_rating || 0) >= 4
    ).length;
    const positiveRate = feedback.length ? (positiveCount / feedback.length) * 100 : 0;

    const now = new Date();
    const thisWeekFeedback = feedback.filter((item) => {
      if (!item.timestamp) return false;
      const time = new Date(item.timestamp).getTime();
      return now.getTime() - time <= 7 * 24 * 3600 * 1000;
    }).length;

    setStats((prev) => ({
      ...prev,
      avgRating,
      positiveRate,
      thisWeekFeedback,
    }));
  }, [feedback]);

  const filteredFeedback = useMemo(() => {
    if (selectedType === 'all') return feedback;
    return feedback.filter((item) => item.feedback_type === selectedType);
  }, [feedback, selectedType]);

  const handleExport = async () => {
    if (filteredFeedback.length === 0) {
      error(t('admin.feedback.toast.exportFailed'), t('admin.feedback.toast.noDataToExport'));
      return;
    }
    const rows = filteredFeedback.map((item) => [
      item.trace_id,
      item.agent_name,
      item.feedback_type,
      item.user_rating ?? '',
      item.user_input?.replace(/\n/g, ' '),
      item.ai_output?.replace(/\n/g, ' '),
      item.timestamp || '',
    ]);
    const header = ['trace_id', 'agent_name', 'feedback_type', 'user_rating', 'user_input', 'ai_output', 'timestamp'];
    const csv = [header, ...rows].map((row) => row.map((cell) => `"${String(cell ?? '').replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `feedback_export_${Date.now()}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    success(t('admin.feedback.toast.exported'), t('admin.feedback.toast.exportedDesc'));
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'like':
        return <ThumbsUp className="w-4 h-4 text-green-500" />;
      case 'dislike':
        return <ThumbsDown className="w-4 h-4 text-red-500" />;
      case 'rating':
        return <Star className="w-4 h-4 text-yellow-500" />;
      case 'refinement':
        return <MessageSquare className="w-4 h-4 text-blue-500" />;
      default:
        return null;
    }
  };

  const getTypeText = (type: string) => {
    switch (type) {
      case 'like':
        return t('admin.feedback.like');
      case 'dislike':
        return t('admin.feedback.dislike');
      case 'rating':
        return t('admin.feedback.rating');
      case 'refinement':
        return t('admin.feedback.refinement');
      default:
        return type;
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
                  <div className="w-12 h-12 bg-gradient-to-br from-green-500 to-teal-500 rounded-xl flex items-center justify-center">
                    <MessageSquare className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h1 className="text-2xl font-bold text-gray-900">{t('admin.feedback.title')}</h1>
                    <p className="text-sm text-gray-500 mt-1">{t('admin.feedback.subtitle')}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleExport}
                    className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
                  >
                    <Download className="w-4 h-4" />
                    {t('admin.feedback.exportData')}
                  </button>
                  <button
                    onClick={() => {
                      loadFeedback();
                      loadStats();
                    }}
                    className="flex items-center gap-2 px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm"
                  >
                    <RefreshCw className={loading ? 'w-4 h-4 animate-spin' : 'w-4 h-4'} />
                    {t('admin.refresh')}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div className="max-w-7xl mx-auto px-6 py-8">
            {/* 统计卡片 */}
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8">
              <div className="bg-white rounded-lg shadow p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">{t('admin.feedback.totalFeedback')}</p>
                    <p className="text-2xl font-bold text-gray-900 mt-1">{stats.totalFeedback}</p>
                  </div>
                  <MessageSquare className="w-8 h-8 text-blue-500" />
                </div>
              </div>
              <div className="bg-white rounded-lg shadow p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">{t('admin.feedback.positiveRate')}</p>
                    <p className="text-2xl font-bold text-gray-900 mt-1">{stats.positiveRate.toFixed(1)}%</p>
                  </div>
                  <TrendingUp className="w-8 h-8 text-green-500" />
                </div>
              </div>
              <div className="bg-white rounded-lg shadow p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">{t('admin.feedback.avgRating')}</p>
                    <p className="text-2xl font-bold text-gray-900 mt-1">{stats.avgRating.toFixed(2)}</p>
                  </div>
                  <Star className="w-8 h-8 text-yellow-500" />
                </div>
              </div>
              <div className="bg-white rounded-lg shadow p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">{t('admin.feedback.goldSamples')}</p>
                    <p className="text-2xl font-bold text-gray-900 mt-1">{stats.goldSamples}</p>
                  </div>
                  <Award className="w-8 h-8 text-purple-500" />
                </div>
              </div>
              <div className="bg-white rounded-lg shadow p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">{t('admin.feedback.thisWeek')}</p>
                    <p className="text-2xl font-bold text-gray-900 mt-1">{stats.thisWeekFeedback}</p>
                  </div>
                  <Calendar className="w-8 h-8 text-orange-500" />
                </div>
              </div>
            </div>

            {/* 筛选与 Tabs */}
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-6">
              <div className="flex gap-2">
                {[
                  { key: 'feedback', label: t('admin.feedback.tab.feedback') },
                  { key: 'samples', label: t('admin.feedback.tab.samples') },
                  { key: 'analytics', label: t('admin.feedback.tab.analytics') },
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
              <div className="flex flex-wrap items-center gap-2">
                <select
                  value={selectedAgent}
                  onChange={(e) => setSelectedAgent(e.target.value)}
                  className="text-sm border rounded px-2 py-1"
                >
                  <option value="">{t('admin.feedback.allAgents')}</option>
                  {agents.map((agent) => (
                    <option key={agent.id} value={agent.name}>
                      {agent.displayName || agent.name}
                    </option>
                  ))}
                </select>
                <select
                  value={days}
                  onChange={(e) => setDays(Number(e.target.value))}
                  className="text-sm border rounded px-2 py-1"
                >
                  <option value={7}>{t('admin.feedback.days7')}</option>
                  <option value={30}>{t('admin.feedback.days30')}</option>
                  <option value={90}>{t('admin.feedback.days90')}</option>
                </select>
                <select
                  value={selectedType}
                  onChange={(e) => setSelectedType(e.target.value as any)}
                  className="text-sm border rounded px-2 py-1"
                >
                  <option value="all">{t('admin.feedback.allTypes')}</option>
                  <option value="like">{t('admin.feedback.like')}</option>
                  <option value="dislike">{t('admin.feedback.dislike')}</option>
                  <option value="rating">{t('admin.feedback.rating')}</option>
                  <option value="refinement">{t('admin.feedback.refinement')}</option>
                </select>
              </div>
            </div>

            {activeTab === 'feedback' && (
              <div className="bg-white rounded-lg shadow">
                <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-gray-900">{t('admin.feedback.tab.feedback')}</h2>
                  <span className="text-xs text-gray-500">{t('admin.feedback.totalCount', { count: filteredFeedback.length })}</span>
                </div>
                <div className="divide-y divide-gray-100">
                  {loading ? (
                    <div className="p-6 text-sm text-gray-500">{t('admin.loading')}</div>
                  ) : filteredFeedback.length === 0 ? (
                    <div className="p-6 text-sm text-gray-500">{t('admin.feedback.noFeedback')}</div>
                  ) : (
                    filteredFeedback.map((item) => (
                      <div key={item.trace_id} className="px-6 py-4">
                        <div className="flex items-center gap-2 text-sm text-gray-700">
                          {getTypeIcon(item.feedback_type)}
                          <span className="font-medium">{agentNameMap(item.agent_name, agents)}</span>
                          <span className="text-xs text-gray-500">{getTypeText(item.feedback_type)}</span>
                          {item.user_rating && (
                            <span className="text-xs text-yellow-600">{t('admin.feedback.ratingLabel', { value: item.user_rating })}</span>
                          )}
                          {item.is_gold_sample && (
                            <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded">{t('admin.feedback.goldSamples')}</span>
                          )}
                        </div>
                        <div className="mt-2 text-xs text-gray-500">{item.timestamp ? new Date(item.timestamp).toLocaleString(language === 'zh' ? 'zh-CN' : 'en-US') : '—'}</div>
                        <div className="mt-3 text-sm text-gray-700">
                          <div className="font-medium text-gray-900">{t('admin.feedback.userInput')}</div>
                          <p className="text-xs text-gray-600 mt-1 line-clamp-3">{item.user_input}</p>
                        </div>
                        <div className="mt-3 text-sm text-gray-700">
                          <div className="font-medium text-gray-900">{t('admin.feedback.aiOutput')}</div>
                          <p className="text-xs text-gray-600 mt-1 line-clamp-3">{item.ai_output}</p>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}

            {activeTab === 'samples' && (
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-4">
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900">{t('admin.feedback.sampleSearch')}</h2>
                    <p className="text-sm text-gray-500">{t('admin.feedback.sampleSearchDesc')}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="relative">
                      <Search className="w-4 h-4 text-gray-400 absolute left-2 top-2.5" />
                      <input
                        value={goldQuery}
                        onChange={(e) => setGoldQuery(e.target.value)}
                        placeholder={t('admin.feedback.keyword')}
                        className="pl-8 pr-3 py-2 border rounded text-sm"
                      />
                    </div>
                    <button
                      onClick={loadGoldSamples}
                      className="px-3 py-2 text-sm bg-black text-white rounded hover:bg-gray-800"
                    >
                      {t('admin.feedback.searchSamples')}
                    </button>
                  </div>
                </div>

                {goldLoading ? (
                  <div className="text-sm text-gray-500">{t('admin.loading')}</div>
                ) : goldSamples.length === 0 ? (
                  <div className="text-sm text-gray-500">{t('admin.feedback.noMatch')}</div>
                ) : (
                  <div className="space-y-4">
                    {goldSamples.map((sample) => (
                      <div key={sample.sample_id} className="border rounded-lg p-4">
                        <div className="flex items-center gap-2 text-sm">
                          <Award className="w-4 h-4 text-yellow-500" />
                          <span className="font-medium">{agentNameMap(sample.agent_name, agents)}</span>
                          <span className="text-xs text-gray-500">{t('admin.feedback.similarity', { score: sample.score?.toFixed(2) ?? '-' })}</span>
                        </div>
                        <div className="mt-2 text-xs text-gray-600">{sample.gold_reason || t('admin.feedback.highQuality')}</div>
                        <div className="mt-3 text-sm text-gray-700">
                          <div className="font-medium text-gray-900">{t('admin.feedback.userInput')}</div>
                          <p className="text-xs text-gray-600 mt-1 line-clamp-2">{sample.user_input}</p>
                        </div>
                        <div className="mt-3 text-sm text-gray-700">
                          <div className="font-medium text-gray-900">{t('admin.feedback.aiOutput')}</div>
                          <p className="text-xs text-gray-600 mt-1 line-clamp-3">{sample.ai_output}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === 'analytics' && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold text-gray-900">{t('admin.feedback.analyticsTitle')}</h2>
                <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="border rounded-lg p-4">
                    <h3 className="text-sm font-semibold text-gray-900">{t('admin.feedback.byType')}</h3>
                    <div className="mt-3 text-xs text-gray-600 space-y-1">
                      <div>{t('admin.feedback.like')}: {feedback.filter((item) => item.feedback_type === 'like').length}</div>
                      <div>{t('admin.feedback.dislike')}: {feedback.filter((item) => item.feedback_type === 'dislike').length}</div>
                      <div>{t('admin.feedback.rating')}: {feedback.filter((item) => item.feedback_type === 'rating').length}</div>
                      <div>{t('admin.feedback.refinement')}: {feedback.filter((item) => item.feedback_type === 'refinement').length}</div>
                    </div>
                  </div>
                  <div className="border rounded-lg p-4">
                    <h3 className="text-sm font-semibold text-gray-900">{t('admin.feedback.dataHealth')}</h3>
                    <div className="mt-3 text-xs text-gray-600 space-y-1">
                      <div>{t('admin.feedback.positiveRateLabel', { rate: stats.positiveRate.toFixed(1) })}</div>
                      <div>{t('admin.feedback.avgRatingLabel', { score: stats.avgRating.toFixed(2) })}</div>
                      <div>{t('admin.feedback.goldRatio', { rate: stats.totalFeedback ? ((stats.goldSamples / stats.totalFeedback) * 100).toFixed(1) : '0' })}</div>
                    </div>
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

export default FeedbackPage;

function agentNameMap(agentName: string, agents: Agent[]) {
  const found = agents.find((agent) => agent.name === agentName);
  return found?.displayName || agentName;
}
