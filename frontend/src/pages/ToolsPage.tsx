/**
 * 工具管理页面
 * 支持工具列表、批量执行、工具搜索等功能
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUIStore } from '@/store/uiStore';
import { useAuthStore } from '@/store/authStore';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import StatusBar from '@/components/layout/StatusBar';
import MobileMenu from '@/components/common/MobileMenu';
import SettingsModal from '@/components/modals/SettingsModal';
import {
  Wrench,
  Play,
  Square,
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  Loader2,
  List,
  Layers,
  Code,
  FileText,
  Zap,
  Box,
  Upload,
  Download,
  Trash2
} from 'lucide-react';
import api from '@/services/api';
import { useI18n } from '@/i18n';

type ToolStatus = 'idle' | 'loading' | 'success' | 'error';

interface ToolSchema {
  tool_name: string;
  description: string;
  parameters: Array<{
    name: string;
    type: string;
    description: string;
    required: boolean;
  }>;
  returns: string;
}

interface ToolExecution {
  tool_name: string;
  parameters: Record<string, any>;
  status?: ToolStatus;
  result?: any;
  error?: string;
}

interface BatchExecutionResult {
  success: boolean;
  results: Array<{
    tool_name: string;
    success: boolean;
    result?: any;
    error?: string;
  }>;
}

export default function ToolsPage() {
  const { sidebarOpen, sidebarCollapsed } = useUIStore();
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const { t } = useI18n();

  const [tools, setTools] = useState<ToolSchema[]>([]);
  const [filteredTools, setFilteredTools] = useState<ToolSchema[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [executions, setExecutions] = useState<ToolExecution[]>([]);
  const [selectedTools, setSelectedTools] = useState<Set<string>>(new Set());
  const [isBatchMode, setIsBatchMode] = useState(false);

  // 加载工具列表
  const loadTools = async () => {
    try {
      const response = await api.get('/tools/list');
      if (response.data?.tools) {
        setTools(response.data.tools);
        setFilteredTools(response.data.tools);
      }
    } catch (err) {
      console.error('加载工具列表失败:', err);
    }
  };

  // 加载工具模式
  const loadToolSchemas = async () => {
    try {
      const response = await api.get('/tools/schemas');
      if (response.data?.schemas) {
        setTools(response.data.schemas);
        setFilteredTools(response.data.schemas);
      }
    } catch (err) {
      console.error('加载工具模式失败:', err);
    }
  };

  useEffect(() => {
    loadTools();
    loadToolSchemas();
  }, []);

  // 过滤工具
  useEffect(() => {
    let filtered = tools;

    // 搜索过滤
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(tool =>
        tool.tool_name.toLowerCase().includes(query) ||
        tool.description.toLowerCase().includes(query)
      );
    }

    // 分类过滤
    // 这里可以根据工具名称进行分类
    if (categoryFilter !== 'all') {
      // 实现分类过滤逻辑
    }

    setFilteredTools(filtered);
  }, [tools, searchQuery, categoryFilter]);

  // 执行单个工具
  const executeTool = async (toolName: string, parameters: Record<string, any> = {}) => {
    const execution: ToolExecution = {
      tool_name: toolName,
      parameters,
      status: 'loading'
    };

    setExecutions(prev => [{ ...execution }, ...prev.slice(0, 9)]);

    try {
      const response = await api.post('/tools/execute', {
        tool_name: toolName,
        parameters
      });

      setExecutions(prev => prev.map(e =>
        e.tool_name === toolName
          ? { ...e, status: 'success', result: response.data }
          : e
      ));
    } catch (err) {
      console.error('工具执行失败:', err);
      setExecutions(prev => prev.map(e =>
        e.tool_name === toolName
          ? { ...e, status: 'error', error: t('toolbox.toolsPage.execFailed') }
          : e
      ));
    }
  };

  // 批量执行工具
  const executeBatch = async () => {
    if (selectedTools.size === 0) {
      alert(t('toolbox.toolsPage.selectToolsFirst'));
      return;
    }

    const toolsToExecute = Array.from(selectedTools).map(toolName => ({
      tool_name: toolName,
      parameters: {}
    }));

    setIsBatchMode(true);

    try {
      const response = await api.post('/tools/batch_execute', {
        tools: toolsToExecute
      });

      if (response.data?.results) {
        // 添加批量执行结果到执行历史
        response.data.results.forEach((result: any) => {
          const execution: ToolExecution = {
            tool_name: result.tool_name,
            parameters: {},
            status: result.success ? 'success' : 'error',
            result: result.result,
            error: result.error
          };
          setExecutions(prev => [execution, ...prev.slice(0, 9)]);
        });

        setSelectedTools(new Set());
        setIsBatchMode(false);
      }
    } catch (err) {
      console.error('批量执行失败:', err);
      alert(t('toolbox.toolsPage.batchFailed'));
      setIsBatchMode(false);
    }
  };

  // 停止执行
  const stopExecution = (toolName: string) => {
    setExecutions(prev => prev.map(e =>
      e.tool_name === toolName
        ? { ...e, status: 'idle' }
        : e
    ));
  };

  // 清空执行历史
  const clearHistory = () => {
    if (confirm(t('toolbox.toolsPage.clearConfirm'))) {
      setExecutions([]);
    }
  };

  // 切换工具选择
  const toggleToolSelection = (toolName: string) => {
    const newSelected = new Set(selectedTools);
    if (newSelected.has(toolName)) {
      newSelected.delete(toolName);
    } else {
      newSelected.add(toolName);
    }
    setSelectedTools(newSelected);
  };

  // 全选
  const selectAllTools = () => {
    setSelectedTools(new Set(filteredTools.map(t => t.tool_name)));
  };

  // 取消全选
  const clearSelection = () => {
    setSelectedTools(new Set());
  };

  const getToolIcon = (toolName: string) => {
    if (toolName.includes('search')) return <Search className="w-5 h-5" />;
    if (toolName.includes('web')) return <Layers className="w-5 h-5" />;
    if (toolName.includes('file')) return <FileText className="w-5 h-5" />;
    if (toolName.includes('code')) return <Code className="w-5 h-5" />;
    if (toolName.includes('api')) return <Box className="w-5 h-5" />;
    return <Zap className="w-5 h-5" />;
  };

  const getStatusIcon = (status?: ToolStatus) => {
    switch (status) {
      case 'loading':
        return <Loader2 className="w-5 h-5 animate-spin text-blue-500" />;
      case 'success':
        return <CheckCircle2 className="w-5 h-5 text-green-500" />;
      case 'error':
        return <XCircle className="w-5 h-5 text-red-500" />;
      default:
        return <div className="w-5 h-5 border-2 border-gray-300 rounded-full" />;
    }
  };

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
                  <Wrench className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-gray-900">{t('toolbox.toolsPage.title')}</h1>
                  <p className="text-sm text-gray-500 mt-1">
                    {t('toolbox.toolsPage.subtitle')}
                  </p>
                </div>
              </div>

              {/* 工具栏 */}
              <div className="flex items-center gap-4">
                {/* 搜索框 */}
                <div className="relative flex-1 max-w-md">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder={t('toolbox.toolsPage.searchPlaceholder')}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-black text-sm"
                  />
                </div>

                {/* 分类过滤 */}
                <select
                  value={categoryFilter}
                  onChange={(e) => setCategoryFilter(e.target.value)}
                  className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:border-black"
                >
                  <option value="all">{t('toolbox.toolsPage.allTypes')}</option>
                  <option value="search">{t('toolbox.toolsPage.searchType')}</option>
                  <option value="api">{t('toolbox.toolsPage.apiType')}</option>
                  <option value="file">{t('toolbox.toolsPage.fileType')}</option>
                  <option value="analysis">{t('toolbox.toolsPage.analysisType')}</option>
                </select>

                {/* 批量模式 */}
                <button
                  onClick={() => {
                    if (isBatchMode) {
                      setIsBatchMode(false);
                      setSelectedTools(new Set());
                    } else {
                      setIsBatchMode(true);
                    }
                  }}
                  className={`flex items-center gap-2 px-4 py-2 border rounded-lg text-sm font-medium transition-colors ${
                    isBatchMode
                      ? 'bg-black text-white border-black'
                      : 'border-gray-200 hover:bg-gray-50'
                  }`}
                >
                  {isBatchMode ? (
                    <>
                      <Square className="w-4 h-4" />
                      {t('toolbox.toolsPage.exitBatch')}
                    </>
                  ) : (
                    <>
                      <Layers className="w-4 h-4" />
                      {t('toolbox.toolsPage.batchExec')}
                    </>
                  )}
                </button>

                {isBatchMode && (
                  <>
                    <button
                      onClick={selectAllTools}
                      className="px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 text-sm"
                    >
                      {t('toolbox.toolsPage.selectAll')}
                    </button>
                    <button
                      onClick={executeBatch}
                      disabled={selectedTools.size === 0}
                      className="flex items-center gap-2 px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 disabled:bg-gray-300 disabled:cursor-not-allowed text-sm"
                    >
                      <Play className="w-4 h-4" />
                      {t('toolbox.toolsPage.execSelected')} ({selectedTools.size})
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* 主内容区 */}
          <div className="flex-1 overflow-y-auto p-6">
            <div className="max-w-7xl mx-auto">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* 左侧：工具列表 */}
                <div className="lg:col-span-2 space-y-4">
                  {filteredTools.length === 0 ? (
                    <div className="text-center py-12">
                      <Wrench className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                      <h3 className="text-lg font-semibold text-gray-900 mb-2">
                        {t('toolbox.toolsPage.noTools')}
                      </h3>
                      <p className="text-gray-500">
                        {searchQuery ? t('toolbox.toolsPage.adjustSearch') : t('toolbox.toolsPage.noToolsHint')}
                      </p>
                    </div>
                  ) : (
                    filteredTools.map((tool) => (
                      <div
                        key={tool.tool_name}
                        className={`bg-white border rounded-xl p-5 transition-all hover:shadow-lg ${
                          selectedTools.has(tool.tool_name)
                            ? 'border-black bg-gray-50'
                            : 'border-gray-200'
                        }`}
                      >
                        <div className="flex items-start justify-between mb-4">
                          <div className="flex items-center gap-3">
                            <div className="p-2 bg-gray-100 rounded-lg">
                              {getToolIcon(tool.tool_name)}
                            </div>
                            <div>
                              <h3 className="font-semibold text-gray-900">{tool.tool_name}</h3>
                              <p className="text-xs text-gray-500 mt-1">
                                {tool.description}
                              </p>
                            </div>
                          </div>

                          {isBatchMode && (
                            <button
                              onClick={() => toggleToolSelection(tool.tool_name)}
                              className={`p-2 rounded-lg transition-colors ${
                                selectedTools.has(tool.tool_name)
                                  ? 'bg-black text-white'
                                  : 'bg-gray-100 hover:bg-gray-200'
                              }`}
                            >
                              {selectedTools.has(tool.tool_name) ? (
                                <CheckCircle2 className="w-5 h-5" />
                              ) : (
                                <div className="w-5 h-5 border-2 border-gray-400 rounded" />
                              )}
                            </button>
                          )}
                        </div>

                        {/* 参数列表 */}
                        {tool.parameters && tool.parameters.length > 0 && (
                          <div className="mb-4 p-3 bg-gray-50 rounded-lg">
                            <h4 className="text-xs font-medium text-gray-700 mb-2">{t('toolbox.toolsPage.params')}</h4>
                            <div className="space-y-1">
                              {tool.parameters.map((param, idx) => (
                                <div key={idx} className="text-xs text-gray-600">
                                  <span className="font-medium">{param.name}</span>
                                  {param.required && <span className="text-red-500 ml-1">*</span>}
                                  : {param.type}
                                  {param.description && ` - ${param.description}`}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* 返回值 */}
                        {tool.returns && (
                          <div className="mb-4 p-3 bg-blue-50 rounded-lg">
                            <h4 className="text-xs font-medium text-blue-700 mb-1">{t('toolbox.toolsPage.returns')}</h4>
                            <p className="text-xs text-blue-600">{tool.returns}</p>
                          </div>
                        )}

                        {/* 操作按钮 */}
                        <div className="flex items-center gap-2">
                          {!isBatchMode && (
                            <button
                              onClick={() => executeTool(tool.tool_name)}
                              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 text-sm font-medium"
                            >
                              <Play className="w-4 h-4" />
                              {t('toolbox.toolsPage.execute')}
                            </button>
                          )}

                          <button
                            onClick={() => executeTool(tool.tool_name)}
                            className="flex-1 flex items-center justify-center gap-2 px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 text-sm font-medium"
                          >
                            <Code className="w-4 h-4" />
                            {t('toolbox.toolsPage.viewCode')}
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>

                {/* 右侧：执行历史 */}
                <div className="lg:col-span-1">
                  <div className="bg-white border border-gray-200 rounded-xl p-5">
                    <div className="flex items-center justify-between mb-4">
                      <h2 className="text-lg font-semibold text-gray-900">{t('toolbox.toolsPage.execHistory')}</h2>
                      {executions.length > 0 && (
                        <button
                          onClick={clearHistory}
                          className="text-xs text-gray-500 hover:text-red-500 transition-colors"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      )}
                    </div>

                    {executions.length === 0 ? (
                      <div className="text-center py-8">
                        <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3">
                          <FileText className="w-6 h-6 text-gray-400" />
                        </div>
                        <p className="text-sm text-gray-500">{t('toolbox.toolsPage.noExecRecords')}</p>
                      </div>
                    ) : (
                      <div className="space-y-3 max-h-[600px] overflow-y-auto">
                        {executions.map((execution, idx) => (
                          <div
                            key={idx}
                            className="p-3 bg-gray-50 rounded-lg border border-gray-200"
                          >
                            <div className="flex items-start justify-between mb-2">
                              <div className="flex items-center gap-2">
                                {getToolIcon(execution.tool_name)}
                                <span className="text-sm font-medium text-gray-900">
                                  {execution.tool_name}
                                </span>
                              </div>
                              {getStatusIcon(execution.status)}
                            </div>

                            {execution.status === 'loading' && (
                              <button
                                onClick={() => stopExecution(execution.tool_name)}
                                className="w-full mt-2 flex items-center justify-center gap-2 px-3 py-2 bg-red-100 text-red-700 rounded-lg text-xs"
                              >
                                <Square className="w-3 h-3" />
                                {t('toolbox.toolsPage.stop')}
                              </button>
                            )}

                            {execution.result && (
                              <div className="mt-2 p-2 bg-white rounded border border-gray-200">
                                <pre className="text-xs text-gray-700 whitespace-pre-wrap overflow-auto max-h-32">
                                  {JSON.stringify(execution.result, null, 2)}
                                </pre>
                              </div>
                            )}

                            {execution.error && (
                              <div className="mt-2 p-2 bg-red-50 text-red-700 rounded-lg text-xs">
                                {execution.error}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <SettingsModal />
    </div>
  );
}
