/**
 * 发布管理页面
 * 提供发布前的检查清单、ROI计算等功能
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUIStore } from '@/store/uiStore';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import StatusBar from '@/components/layout/StatusBar';
import MobileMenu from '@/components/common/MobileMenu';
import SettingsModal from '@/components/modals/SettingsModal';
import {
  Rocket,
  CheckCircle2,
  Circle,
  Calculator,
  FileText,
  Download,
  Upload,
  Plus,
  Trash2,
  Edit
} from 'lucide-react';
import api from '@/services/api';
import { useI18n } from '@/i18n';

interface ChecklistItem {
  id: string;
  category: string;
  title: string;
  description: string;
  required: boolean;
  completed: boolean;
  notes?: string;
}

interface ReleaseTemplate {
  id: string;
  name: string;
  description: string;
  checklist_items: ChecklistItem[];
  created_at: string;
}

interface ROIInput {
  production_cost: number;
  marketing_cost: number;
  expected_viewers: number;
  expected_conversion_rate: number;
  avg_revenue_per_user: number;
}

interface ROIResult {
  total_investment: number;
  expected_revenue: number;
  expected_profit: number;
  roi_percentage: number;
  break_even_viewers: number;
  payback_period: string;
}

export default function ReleaseManagementPage() {
  const { t } = useI18n();
  const { sidebarOpen, sidebarCollapsed } = useUIStore();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState<'checklist' | 'roi' | 'templates'>('checklist');

  // 检查清单状态
  const [checklistItems, setChecklistItems] = useState<ChecklistItem[]>([
    {
      id: 'script_finalized',
      category: '剧本',
      title: '剧本定稿',
      description: '剧本已经过最终审核并定稿',
      required: true,
      completed: false
    },
    {
      id: 'characters_approved',
      category: '角色',
      title: '角色设计确认',
      description: '所有角色设计已获得确认',
      required: true,
      completed: false
    },
    {
      id: 'plot_checked',
      category: '情节',
      title: '情节逻辑检查',
      description: '情节逻辑已通过一致性检查',
      required: true,
      completed: false
    },
    {
      id: 'dialogue_reviewed',
      category: '对话',
      title: '对话审核',
      description: '对话内容已审核通过',
      required: true,
      completed: false
    },
    {
      id: 'format_ready',
      category: '格式',
      title: '格式准备就绪',
      description: '输出格式已准备完成',
      required: false,
      completed: false
    },
    {
      id: 'legal_clearance',
      category: '法务',
      title: '法务清审',
      description: '法务审核已完成',
      required: true,
      completed: false
    }
  ]);

  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
  const [templates, setTemplates] = useState<ReleaseTemplate[]>([]);

  // ROI计算状态
  const [roiInput, setRoiInput] = useState<ROIInput>({
    production_cost: 0,
    marketing_cost: 0,
    expected_viewers: 0,
    expected_conversion_rate: 5,
    avg_revenue_per_user: 10
  });
  const [roiResult, setRoiResult] = useState<ROIResult | null>(null);

  // 加载模板列表
  const loadTemplates = async () => {
    try {
      const response = await api.get('/release/templates');
      setTemplates(response.data?.templates || []);
    } catch (err) {
      console.error('加载模板失败:', err);
    }
  };

  // 计算ROI
  const calculateROI = async () => {
    try {
      const response = await api.post('/release/roi', roiInput);
      setRoiResult(response.data || response);
    } catch (err) {
      console.error('ROI计算失败:', err);
      // 前端计算作为后备
      const total_investment = roiInput.production_cost + roiInput.marketing_cost;
      const expected_revenue = roiInput.expected_viewers *
        (roiInput.expected_conversion_rate / 100) *
        roiInput.avg_revenue_per_user;
      const expected_profit = expected_revenue - total_investment;
      const roi_percentage = total_investment > 0 ? (expected_profit / total_investment) * 100 : 0;
      const break_even_viewers = roiInput.avg_revenue_per_user > 0
        ? total_investment / (roiInput.avg_revenue_per_user * roiInput.expected_conversion_rate / 100)
        : 0;

      setRoiResult({
        total_investment,
        expected_revenue,
        expected_profit,
        roi_percentage,
        break_even_viewers,
        payback_period: '预计3-6个月'
      });
    }
  };

  // 切换检查项状态
  const toggleChecklistItem = (itemId: string) => {
    setChecklistItems(items =>
      items.map(item =>
        item.id === itemId ? { ...item, completed: !item.completed } : item
      )
    );
  };

  // 获取检查项统计
  const getChecklistStats = () => {
    const required = checklistItems.filter(i => i.required);
    const requiredCompleted = required.filter(i => i.completed);
    const optional = checklistItems.filter(i => !i.required);
    const optionalCompleted = optional.filter(i => i.completed);

    return {
      required: { total: required.length, completed: requiredCompleted.length },
      optional: { total: optional.length, completed: optionalCompleted.length },
      all: { total: checklistItems.length, completed: checklistItems.filter(i => i.completed).length }
    };
  };

  const stats = getChecklistStats();
  const canRelease = stats.required.completed === stats.required.total;

  // 按分类分组
  const groupedItems = checklistItems.reduce((acc, item) => {
    if (!acc[item.category]) {
      acc[item.category] = [];
    }
    acc[item.category].push(item);
    return acc;
  }, {} as Record<string, ChecklistItem[]>);

  return (
    <div className="flex h-screen bg-white">
      <MobileMenu />
      <Sidebar />

      <div
        className={`flex flex-col flex-1 transition-all duration-300 ${
          !sidebarOpen ? 'ml-0' : sidebarCollapsed ? 'ml-16' : 'ml-80'
        }`}
      >
        <Header />
        <StatusBar />

        <div className="flex flex-col flex-1 overflow-hidden">
          {/* 页面头部 */}
          <div className="border-b border-gray-200 bg-white">
            <div className="max-w-7xl mx-auto px-6 py-6">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-black rounded-xl flex items-center justify-center">
                  <Rocket className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-gray-900">{t('admin.release.title')}</h1>
                  <p className="text-sm text-gray-500 mt-1">
                    {t('admin.release.subtitle')}
                  </p>
                </div>
              </div>

              {/* 标签页 */}
              <div className="flex items-center gap-4 mt-6">
                <button
                  onClick={() => setActiveTab('checklist')}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    activeTab === 'checklist'
                      ? 'bg-black text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {t('admin.release.tab.checklist')}
                </button>
                <button
                  onClick={() => setActiveTab('roi')}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    activeTab === 'roi'
                      ? 'bg-black text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {t('admin.release.tab.roi')}
                </button>
                <button
                  onClick={() => setActiveTab('templates')}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    activeTab === 'templates'
                      ? 'bg-black text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {t('admin.release.tab.templates')}
                </button>
              </div>
            </div>
          </div>

          {/* 主内容区 */}
          <div className="flex-1 overflow-y-auto p-6">
            <div className="max-w-7xl mx-auto">
              {activeTab === 'checklist' && (
                <div className="space-y-6">
                  {/* 统计概览 */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-white border border-gray-200 rounded-xl p-5">
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-sm text-gray-500">{t('admin.release.requiredItems')}</span>
                        <span className={`text-2xl font-bold ${
                          stats.required.completed === stats.required.total ? 'text-green-600' : 'text-orange-600'
                        }`}>
                          {stats.required.completed}/{stats.required.total}
                        </span>
                      </div>
                      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className={`h-full transition-all ${
                            stats.required.completed === stats.required.total ? 'bg-green-500' : 'bg-orange-500'
                          }`}
                          style={{ width: `${(stats.required.completed / stats.required.total) * 100}%` }}
                        />
                      </div>
                    </div>

                    <div className="bg-white border border-gray-200 rounded-xl p-5">
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-sm text-gray-500">{t('admin.release.optionalItems')}</span>
                        <span className="text-2xl font-bold text-gray-900">
                          {stats.optional.completed}/{stats.optional.total}
                        </span>
                      </div>
                      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-blue-500 transition-all"
                          style={{ width: `${stats.optional.total > 0 ? (stats.optional.completed / stats.optional.total) * 100 : 0}%` }}
                        />
                      </div>
                    </div>

                    <div className={`border rounded-xl p-5 ${
                      canRelease
                        ? 'bg-green-50 border-green-200'
                        : 'bg-orange-50 border-orange-200'
                    }`}>
                      <div className="flex items-center gap-2">
                        {canRelease ? (
                          <CheckCircle2 className="w-6 h-6 text-green-600" />
                        ) : (
                          <Circle className="w-6 h-6 text-orange-600" />
                        )}
                        <div>
                          <p className="font-semibold text-gray-900">
                            {canRelease ? t('admin.release.readyToRelease') : t('admin.release.notReady')}
                          </p>
                          <p className="text-xs text-gray-500 mt-1">
                            {canRelease
                              ? t('admin.release.allRequiredDone')
                              : t('admin.release.remainingRequired', { count: stats.required.total - stats.required.completed })
                            }
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* 检查清单 */}
                  <div className="bg-white border border-gray-200 rounded-xl p-6">
                    <div className="flex items-center justify-between mb-6">
                      <h2 className="text-lg font-semibold text-gray-900">{t('admin.release.tab.checklist')}</h2>

                      <button className="flex items-center gap-2 px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors text-sm">
                        <Download className="w-4 h-4" />
                        {t('admin.release.exportChecklist')}
                      </button>
                    </div>

                    <div className="space-y-6">
                      {Object.entries(groupedItems).map(([category, items]) => (
                        <div key={category}>
                          <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
                            {category}
                          </h3>

                          <div className="space-y-2">
                            {items.map((item) => (
                              <div
                                key={item.id}
                                className={`flex items-start gap-3 p-4 border rounded-lg transition-colors ${
                                  item.completed
                                    ? 'border-green-200 bg-green-50'
                                    : 'border-gray-200 hover:border-gray-300'
                                }`}
                              >
                                <button
                                  onClick={() => toggleChecklistItem(item.id)}
                                  className={`mt-0.5 flex-shrink-0 ${
                                    item.completed ? 'text-green-500' : 'text-gray-400 hover:text-gray-600'
                                  }`}
                                >
                                  {item.completed ? (
                                    <CheckCircle2 className="w-5 h-5" />
                                  ) : (
                                    <Circle className="w-5 h-5" />
                                  )}
                                </button>

                                <div className="flex-1 min-w-0">
                                  <div className="flex items-start justify-between">
                                    <div>
                                      <h4 className={`font-medium ${item.completed ? 'text-green-700' : 'text-gray-900'}`}>
                                        {item.title}
                                      </h4>
                                      <p className={`text-sm mt-1 ${item.completed ? 'text-green-600' : 'text-gray-500'}`}>
                                        {item.description}
                                      </p>
                                    </div>

                                    {item.required && (
                                      <span className="text-xs px-2 py-1 bg-red-100 text-red-700 rounded-full flex-shrink-0 ml-2">
                                        {t('admin.release.required')}
                                      </span>
                                    )}
                                  </div>

                                  {item.notes && (
                                    <div className="mt-2 p-2 bg-white rounded text-xs text-gray-600">
                                      {item.notes}
                                    </div>
                                  )}
                                </div>

                                <div className="flex items-center gap-1">
                                  <button className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors">
                                    <Edit className="w-4 h-4 text-gray-400" />
                                  </button>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'roi' && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* ROI输入 */}
                  <div className="bg-white border border-gray-200 rounded-xl p-6">
                    <h2 className="text-lg font-semibold text-gray-900 mb-6 flex items-center gap-2">
                      <Calculator className="w-5 h-5" />
                      {t('admin.release.roiCalculator')}
                    </h2>

                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          {t('admin.release.productionCost')}
                        </label>
                        <input
                          type="number"
                          value={roiInput.production_cost || ''}
                          onChange={(e) => setRoiInput({ ...roiInput, production_cost: Number(e.target.value) })}
                          placeholder="0"
                          className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-black"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          {t('admin.release.marketingCost')}
                        </label>
                        <input
                          type="number"
                          value={roiInput.marketing_cost || ''}
                          onChange={(e) => setRoiInput({ ...roiInput, marketing_cost: Number(e.target.value) })}
                          placeholder="0"
                          className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-black"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          {t('admin.release.expectedViewers')}
                        </label>
                        <input
                          type="number"
                          value={roiInput.expected_viewers || ''}
                          onChange={(e) => setRoiInput({ ...roiInput, expected_viewers: Number(e.target.value) })}
                          placeholder="0"
                          className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-black"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          {t('admin.release.expectedConversion')}
                        </label>
                        <input
                          type="number"
                          value={roiInput.expected_conversion_rate}
                          onChange={(e) => setRoiInput({ ...roiInput, expected_conversion_rate: Number(e.target.value) })}
                          className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-black"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          {t('admin.release.avgRevenue')}
                        </label>
                        <input
                          type="number"
                          value={roiInput.avg_revenue_per_user}
                          onChange={(e) => setRoiInput({ ...roiInput, avg_revenue_per_user: Number(e.target.value) })}
                          className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-black"
                        />
                      </div>

                      <button
                        onClick={calculateROI}
                        className="w-full px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 transition-colors"
                      >
                        {t('admin.release.calculateRoi')}
                      </button>
                    </div>
                  </div>

                  {/* ROI结果 */}
                  {roiResult && (
                    <div className="bg-white border border-gray-200 rounded-xl p-6">
                      <h2 className="text-lg font-semibold text-gray-900 mb-6">{t('admin.release.result')}</h2>

                      <div className="space-y-4">
                        <div className="p-4 bg-gray-50 rounded-lg">
                          <p className="text-sm text-gray-500 mb-1">{t('admin.release.totalInvestment')}</p>
                          <p className="text-2xl font-bold text-gray-900">
                            ¥{roiResult.total_investment.toLocaleString()}
                          </p>
                        </div>

                        <div className="p-4 bg-blue-50 rounded-lg">
                          <p className="text-sm text-blue-600 mb-1">{t('admin.release.expectedRevenue')}</p>
                          <p className="text-2xl font-bold text-blue-700">
                            ¥{roiResult.expected_revenue.toLocaleString()}
                          </p>
                        </div>

                        <div className={`p-4 rounded-lg ${
                          roiResult.expected_profit >= 0 ? 'bg-green-50' : 'bg-red-50'
                        }`}>
                          <p className={`text-sm mb-1 ${
                            roiResult.expected_profit >= 0 ? 'text-green-600' : 'text-red-600'
                          }`}>
                            {t('admin.release.expectedProfit')}
                          </p>
                          <p className={`text-2xl font-bold ${
                            roiResult.expected_profit >= 0 ? 'text-green-700' : 'text-red-700'
                          }`}>
                            ¥{roiResult.expected_profit.toLocaleString()}
                          </p>
                        </div>

                        <div className={`p-4 rounded-lg ${
                          roiResult.roi_percentage >= 0 ? 'bg-green-50' : 'bg-red-50'
                        }`}>
                          <p className={`text-sm mb-1 ${
                            roiResult.roi_percentage >= 0 ? 'text-green-600' : 'text-red-600'
                          }`}>
                            ROI
                          </p>
                          <p className={`text-2xl font-bold ${
                            roiResult.roi_percentage >= 0 ? 'text-green-700' : 'text-red-700'
                          }`}>
                            {roiResult.roi_percentage.toFixed(1)}%
                          </p>
                        </div>

                        <div className="p-4 bg-gray-50 rounded-lg">
                          <p className="text-sm text-gray-500 mb-1">{t('admin.release.breakEvenViewers')}</p>
                          <p className="text-2xl font-bold text-gray-900">
                            {Math.round(roiResult.break_even_viewers).toLocaleString()}
                          </p>
                        </div>

                        <div className="p-4 bg-gray-50 rounded-lg">
                          <p className="text-sm text-gray-500 mb-1">{t('admin.release.paybackPeriod')}</p>
                          <p className="text-lg font-semibold text-gray-900">
                            {roiResult.payback_period}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'templates' && (
                <div className="bg-white border border-gray-200 rounded-xl p-6">
                  <div className="flex items-center justify-between mb-6">
                    <h2 className="text-lg font-semibold text-gray-900">{t('admin.release.tab.templates')}</h2>

                    <button className="flex items-center gap-2 px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 transition-colors text-sm">
                      <Plus className="w-4 h-4" />
                      {t('admin.release.newTemplate')}
                    </button>
                  </div>

                  {templates.length === 0 ? (
                    <div className="text-center py-12">
                      <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                      <h3 className="text-lg font-semibold text-gray-900 mb-2">
                        {t('admin.release.noTemplates')}
                      </h3>
                      <p className="text-gray-500">
                        {t('admin.release.noTemplatesDesc')}
                      </p>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {templates.map((template) => (
                        <div
                          key={template.id}
                          className="border border-gray-200 rounded-lg p-4 hover:shadow-lg transition-all"
                        >
                          <h3 className="font-semibold text-gray-900 mb-2">{template.name}</h3>
                          <p className="text-sm text-gray-600 mb-4">{template.description}</p>

                          <div className="flex items-center justify-between text-sm text-gray-500">
                            <span>{t('admin.release.itemCount', { count: template.checklist_items.length })}</span>

                            <div className="flex items-center gap-1">
                              <button className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors">
                                <Edit className="w-4 h-4" />
                              </button>
                              <button className="p-1.5 hover:bg-red-100 rounded-lg transition-colors">
                                <Trash2 className="w-4 h-4 text-red-500" />
                              </button>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <SettingsModal />
    </div>
  );
}
