/**
 * 管道管理页面
 * 管理数据处理管道和工作流模板
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUIStore } from '@/store/uiStore';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import StatusBar from '@/components/layout/StatusBar';
import MobileMenu from '@/components/common/MobileMenu';
import SettingsModal from '@/components/modals/SettingsModal';
import {
  Workflow,
  Play,
  Square,
  Plus,
  Trash2,
  Edit,
  FileText,
  Settings,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  AlertTriangle
} from 'lucide-react';
import api from '@/services/api';
import { useI18n } from '@/i18n';

interface Pipeline {
  id: string;
  name: string;
  description: string;
  status: 'idle' | 'running' | 'completed' | 'failed';
  steps: PipelineStep[];
  created_at: string;
  updated_at: string;
}

interface PipelineStep {
  id: string;
  name: string;
  type: string;
  config: Record<string, any>;
  status?: 'pending' | 'running' | 'completed' | 'failed';
}

interface PipelineTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  steps: Omit<PipelineStep, 'status'>[];
  icon?: string;
}

interface PipelineRun {
  id: string;
  pipeline_id: string;
  status: 'running' | 'completed' | 'failed';
  started_at: string;
  completed_at?: string;
  result?: any;
  error?: string;
}

export default function PipelineManagementPage() {
  const { t, language } = useI18n();
  const { sidebarOpen, sidebarCollapsed } = useUIStore();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState<'templates' | 'runs' | 'create'>('templates');
  const [templates, setTemplates] = useState<PipelineTemplate[]>([]);
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<PipelineTemplate | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [runStatus, setRunStatus] = useState<Record<string, 'running' | 'completed' | 'failed'>>({});

  // 加载管道模板
  const loadTemplates = async () => {
    setIsLoading(true);
    try {
      const response = await api.get('/pipelines/templates');
      setTemplates(response.data?.templates || []);
    } catch (err) {
      console.error('加载管道模板失败:', err);
    } finally {
      setIsLoading(false);
    }
  };

  // 加载运行历史
  const loadRuns = async () => {
    try {
      const response = await api.get('/pipelines/runs');
      setRuns(response.data?.runs || []);
    } catch (err) {
      console.error('加载运行历史失败:', err);
    }
  };

  // 运行管道
  const runPipeline = async (templateId: string, inputData?: any) => {
    setRunStatus(prev => ({ ...prev, [templateId]: 'running' }));

    try {
      const response = await api.post('/pipelines/run', {
        template_id: templateId,
        input_data: inputData
      });

      setRunStatus(prev => ({ ...prev, [templateId]: 'completed' }));

      // 刷新运行列表
      if (activeTab === 'runs') {
        loadRuns();
      }

      return response.data;
    } catch (err) {
      console.error('运行管道失败:', err);
      setRunStatus(prev => ({ ...prev, [templateId]: 'failed' }));
      throw err;
    }
  };

  useEffect(() => {
    loadTemplates();
    if (activeTab === 'runs') {
      loadRuns();
    }
  }, [activeTab]);

  const getStatusIcon = (status?: string) => {
    switch (status) {
      case 'running':
        return <Loader2 className="w-5 h-5 animate-spin text-blue-500" />;
      case 'completed':
        return <CheckCircle2 className="w-5 h-5 text-green-500" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-500" />;
      default:
        return <div className="w-5 h-5 border-2 border-gray-300 rounded-full" />;
    }
  };

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'running':
        return 'bg-blue-100 text-blue-700';
      case 'completed':
        return 'bg-green-100 text-green-700';
      case 'failed':
        return 'bg-red-100 text-red-700';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  };

  // 管道分类
  const categories = Array.from(new Set(templates.map(t => t.category)));

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
              <div className="flex items-center gap-3 mb-6">
                <div className="w-12 h-12 bg-black rounded-xl flex items-center justify-center">
                  <Workflow className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-gray-900">{t('admin.pipeline.title')}</h1>
                  <p className="text-sm text-gray-500 mt-1">
                    {t('admin.pipeline.subtitle')}
                  </p>
                </div>
              </div>

              {/* 标签页 */}
              <div className="flex items-center gap-4">
                <button
                  onClick={() => setActiveTab('templates')}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    activeTab === 'templates'
                      ? 'bg-black text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {t('admin.pipeline.tab.templates')}
                </button>
                <button
                  onClick={() => setActiveTab('runs')}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    activeTab === 'runs'
                      ? 'bg-black text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {t('admin.pipeline.tab.runs')}
                </button>
              </div>
            </div>
          </div>

          {/* 主内容区 */}
          <div className="flex-1 overflow-y-auto p-6">
            <div className="max-w-7xl mx-auto">
              {activeTab === 'templates' && (
                <div className="space-y-6">
                  {/* 按分类展示管道模板 */}
                  {categories.map((category) => (
                    <div key={category}>
                      <h2 className="text-lg font-semibold text-gray-900 mb-4">
                        {category}
                      </h2>

                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {templates
                          .filter(t => t.category === category)
                          .map((template) => (
                            <div
                              key={template.id}
                              className="bg-white border border-gray-200 rounded-xl p-5 hover:shadow-lg transition-all"
                            >
                              <div className="flex items-start justify-between mb-4">
                                <div className="flex items-center gap-3">
                                  {template.icon ? (
                                    <span className="text-3xl">{template.icon}</span>
                                  ) : (
                                    <div className="w-12 h-12 bg-black rounded-xl flex items-center justify-center">
                                      <Workflow className="w-6 h-6 text-white" />
                                    </div>
                                  )}
                                  <div>
                                    <h3 className="font-semibold text-gray-900">{template.name}</h3>
                                    <p className="text-xs text-gray-500 mt-1">{template.category}</p>
                                  </div>
                                </div>

                                {getStatusIcon(runStatus[template.id])}
                              </div>

                              <p className="text-sm text-gray-600 mb-4 min-h-[40px]">
                                {template.description}
                              </p>

                              <div className="mb-4">
                                <p className="text-xs text-gray-500 mb-2">
                                  {t('admin.pipeline.stepsCount', { count: template.steps.length })}
                                </p>
                                <div className="flex flex-wrap gap-1">
                                  {template.steps.slice(0, 3).map((step, idx) => (
                                    <span
                                      key={idx}
                                      className="text-xs px-2 py-1 bg-gray-100 text-gray-700 rounded"
                                    >
                                      {step.name}
                                    </span>
                                  ))}
                                  {template.steps.length > 3 && (
                                    <span className="text-xs px-2 py-1 bg-gray-100 text-gray-700 rounded">
                                      +{template.steps.length - 3}
                                    </span>
                                  )}
                                </div>
                              </div>

                              <div className="flex items-center gap-2">
                                <button
                                  onClick={() => runPipeline(template.id)}
                                  disabled={runStatus[template.id] === 'running'}
                                  className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-black text-white rounded-lg hover:bg-gray-800 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors text-sm"
                                >
                                  {runStatus[template.id] === 'running' ? (
                                    <>
                                      <Loader2 className="w-4 h-4 animate-spin" />
                                      {t('admin.pipeline.running')}
                                    </>
                                  ) : (
                                    <>
                                      <Play className="w-4 h-4" />
                                      {t('admin.pipeline.run')}
                                    </>
                                  )}
                                </button>

                                <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
                                  <Edit className="w-4 h-4 text-gray-500" />
                                </button>
                              </div>
                            </div>
                          ))}
                      </div>
                    </div>
                  ))}

                  {templates.length === 0 && !isLoading && (
                    <div className="text-center py-12">
                      <Workflow className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                      <h3 className="text-lg font-semibold text-gray-900 mb-2">
                        {t('admin.pipeline.noTemplates')}
                      </h3>
                      <p className="text-gray-500">
                        {t('admin.pipeline.noTemplatesDesc')}
                      </p>
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'runs' && (
                <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
                  <div className="px-6 py-4 border-b border-gray-200">
                    <div className="flex items-center justify-between">
                      <h2 className="text-lg font-semibold text-gray-900">{t('admin.pipeline.tab.runs')}</h2>

                      <button
                        onClick={loadRuns}
                        className="flex items-center gap-2 px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors text-sm"
                      >
                        <Clock className="w-4 h-4" />
                        {t('admin.refresh')}
                      </button>
                    </div>
                  </div>

                  {runs.length === 0 ? (
                    <div className="p-12 text-center">
                      <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                      <h3 className="text-lg font-semibold text-gray-900 mb-2">
                        {t('admin.pipeline.noRuns')}
                      </h3>
                      <p className="text-gray-500">
                        {t('admin.pipeline.noRunsDesc')}
                      </p>
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                              {t('admin.pipeline.pipelineId')}
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                              {t('admin.status')}
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                              {t('admin.pipeline.startTime')}
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                              {t('admin.pipeline.endTime')}
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                              {t('admin.pipeline.duration')}
                            </th>
                            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                              {t('admin.actions')}
                            </th>
                          </tr>
                        </thead>

                        <tbody className="divide-y divide-gray-200">
                          {runs.map((run) => (
                            <tr key={run.id} className="hover:bg-gray-50 transition-colors">
                              <td className="px-6 py-4 text-sm font-medium text-gray-900">
                                {run.pipeline_id}
                              </td>

                              <td className="px-6 py-4">
                                <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(run.status)}`}>
                                  {getStatusIcon(run.status)}
                                  {run.status === 'running' && t('admin.pipeline.running')}
                                  {run.status === 'completed' && t('admin.pipeline.completed')}
                                  {run.status === 'failed' && t('admin.pipeline.failed')}
                                </span>
                              </td>

                              <td className="px-6 py-4 text-sm text-gray-600">
                                {new Date(run.started_at).toLocaleString(language === 'zh' ? 'zh-CN' : 'en-US')}
                              </td>

                              <td className="px-6 py-4 text-sm text-gray-600">
                                {run.completed_at
                                  ? new Date(run.completed_at).toLocaleString(language === 'zh' ? 'zh-CN' : 'en-US')
                                  : '-'}
                              </td>

                              <td className="px-6 py-4 text-sm text-gray-600">
                                {run.completed_at
                                  ? t('admin.pipeline.seconds', { n: Math.round((new Date(run.completed_at).getTime() - new Date(run.started_at).getTime()) / 1000) })
                                  : '-'}
                              </td>

                              <td className="px-6 py-4 text-right">
                                <button className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors">
                                  <FileText className="w-4 h-4 text-gray-500" />
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
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
