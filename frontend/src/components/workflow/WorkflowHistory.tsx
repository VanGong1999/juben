/**
 * 工作流历史记录组件
 */

import React, { useState } from 'react';
import { History, Clock, CheckCircle2, XCircle, AlertCircle, Eye, ChevronDown, ChevronUp, X } from 'lucide-react';
import { useI18n } from '@/i18n';

export interface WorkflowExecution {
  id: string;
  workflowId: string;
  workflowName: string;
  status: 'success' | 'failed' | 'running' | 'paused';
  startTime: string;
  endTime?: string;
  duration?: number;
  input: any;
  output?: any;
  errorMessage?: string;
  nodesExecuted: number;
  nodesTotal: number;
}

interface WorkflowHistoryProps {
  isOpen: boolean;
  onClose: () => void;
  executions: WorkflowExecution[];
  onRerun: (executionId: string) => Promise<void>;
  onViewDetails: (executionId: string) => void;
}

export const WorkflowHistory: React.FC<WorkflowHistoryProps> = ({
  isOpen,
  onClose,
  executions,
  onRerun,
  onViewDetails,
}) => {
  const { t, language } = useI18n();
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [statusFilter, setStatusFilter] = useState<'all' | 'success' | 'failed' | 'running' | 'paused'>('all');

  if (!isOpen) return null;

  const toggleExpand = (id: string) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedRows(newExpanded);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle2 className="w-5 h-5 text-green-500" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-500" />;
      case 'running':
        return <Clock className="w-5 h-5 text-blue-500 animate-spin" />;
      case 'paused':
        return <AlertCircle className="w-5 h-5 text-yellow-500" />;
      default:
        return null;
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'success':
        return t('chatGraph.workflow.status.success');
      case 'failed':
        return t('chatGraph.workflow.status.failed');
      case 'running':
        return t('chatGraph.workflow.running');
      case 'paused':
        return t('chatGraph.workflow.paused');
      default:
        return status;
    }
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  };

  const filteredExecutions = executions.filter((e) =>
    statusFilter === 'all' || e.status === statusFilter
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-5xl w-full max-h-[90vh] overflow-hidden mx-4">
        {/* 头部 */}
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <History className="w-6 h-6 text-purple-500" />
              <div>
                <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                  {t('chatGraph.workflow.historyTitle')}
                </h2>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  {t('chatGraph.workflow.historyCount', { count: executions.length })}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* 状态过滤器 */}
          <div className="flex items-center gap-2 mt-4">
            <span className="text-sm text-gray-600 dark:text-gray-400">{t('chatGraph.workflow.statusFilter')}</span>
            <div className="flex gap-1">
              {(['all', 'success', 'failed', 'running', 'paused'] as const).map((status) => (
                <button
                  key={status}
                  onClick={() => setStatusFilter(status)}
                  className={`px-3 py-1 text-xs rounded transition-colors ${
                    statusFilter === status
                      ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 font-medium'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600'
                  }`}
                >
                  {status === 'all' ? t('common.all') : getStatusText(status)}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* 内容 */}
        <div className="overflow-y-auto max-h-[60vh]">
          {filteredExecutions.length === 0 ? (
            <div className="p-12 text-center text-gray-500 dark:text-gray-400">
              <History className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>{t('chatGraph.workflow.noExecutions')}</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-200 dark:divide-gray-700">
              {filteredExecutions.map((execution) => (
                <div key={execution.id} className="p-4 hover:bg-gray-50 dark:hover:bg-gray-750">
                  <div className="flex items-start gap-4">
                    {/* 状态图标 */}
                    <div className="mt-1">{getStatusIcon(execution.status)}</div>

                    {/* 主要信息 */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-3">
                          <h3 className="font-medium text-gray-900 dark:text-white">
                            {execution.workflowName}
                          </h3>
                          <span className={`px-2 py-1 text-xs rounded ${
                            execution.status === 'success'
                              ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
                              : execution.status === 'failed'
                              ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300'
                              : execution.status === 'running'
                              ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                              : 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300'
                          }`}>
                            {getStatusText(execution.status)}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => toggleExpand(execution.id)}
                            className="p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded"
                          >
                            {expandedRows.has(execution.id) ? (
                              <ChevronUp className="w-4 h-4" />
                            ) : (
                              <ChevronDown className="w-4 h-4" />
                            )}
                          </button>
                        </div>
                      </div>

                      {/* 基本信息 */}
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm mb-2">
                        <div>
                          <span className="text-gray-500 dark:text-gray-400">{t('chatGraph.workflow.startTime')}</span>
                          <span className="ml-2 text-gray-900 dark:text-white">
                            {new Date(execution.startTime).toLocaleString(language === 'zh' ? 'zh-CN' : 'en-US')}
                          </span>
                        </div>
                        {execution.endTime && (
                          <div>
                            <span className="text-gray-500 dark:text-gray-400">{t('chatGraph.workflow.endTime')}</span>
                            <span className="ml-2 text-gray-900 dark:text-white">
                              {new Date(execution.endTime).toLocaleString(language === 'zh' ? 'zh-CN' : 'en-US')}
                            </span>
                          </div>
                        )}
                        {execution.duration && (
                          <div>
                            <span className="text-gray-500 dark:text-gray-400">{t('chatGraph.workflow.duration')}</span>
                            <span className="ml-2 text-gray-900 dark:text-white">
                              {formatDuration(execution.duration)}
                            </span>
                          </div>
                        )}
                        <div>
                          <span className="text-gray-500 dark:text-gray-400">{t('chatGraph.workflow.nodeProgress')}</span>
                          <span className="ml-2 text-gray-900 dark:text-white">
                            {execution.nodesExecuted} / {execution.nodesTotal}
                          </span>
                        </div>
                      </div>

                      {/* 展开的详细信息 */}
                      {expandedRows.has(execution.id) && (
                        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 space-y-3">
                          {execution.errorMessage && (
                            <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
                              <p className="text-sm text-red-700 dark:text-red-300">
                                <span className="font-medium">{t('chatGraph.workflow.errorInfo')}</span>{' '}
                                {execution.errorMessage}
                              </p>
                            </div>
                          )}

                          <div className="grid grid-cols-2 gap-4">
                            <div>
                              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                                {t('chatGraph.workflow.input')}
                              </label>
                              <div className="p-2 bg-gray-50 dark:bg-gray-900 rounded text-xs">
                                <pre className="whitespace-pre-wrap">
                                  {JSON.stringify(execution.input, null, 2)}
                                </pre>
                              </div>
                            </div>

                            {execution.output && (
                              <div>
                                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                                  {t('chatGraph.workflow.output')}
                                </label>
                                <div className="p-2 bg-gray-50 dark:bg-gray-900 rounded text-xs max-h-40 overflow-y-auto">
                                  <pre className="whitespace-pre-wrap">
                                    {JSON.stringify(execution.output, null, 2)}
                                  </pre>
                                </div>
                              </div>
                            )}
                          </div>

                          <div className="flex items-center gap-2 pt-2">
                            <button
                              onClick={() => onViewDetails(execution.id)}
                              className="flex items-center gap-1 px-3 py-1.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded hover:bg-blue-200 dark:hover:bg-blue-900/50 text-sm"
                            >
                              <Eye className="w-3 h-3" />
                              {t('chatGraph.workflow.viewDetail')}
                            </button>
                            {execution.status === 'failed' && (
                              <button
                                onClick={() => onRerun(execution.id)}
                                className="flex items-center gap-1 px-3 py-1.5 bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 rounded hover:bg-orange-200 dark:hover:bg-orange-900/50 text-sm"
                              >
                                <Clock className="w-3 h-3" />
                                {t('chatGraph.workflow.rerun')}
                              </button>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 底部 */}
        <div className="p-6 border-t border-gray-200 dark:border-gray-700 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 rounded-lg font-medium transition-colors"
          >
            {t('project.close')}
          </button>
        </div>
      </div>
    </div>
  );
};
