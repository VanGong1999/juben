/**
 * 工作流监控页面
 * 集成工作流可视化、模板管理和执行历史
 */

import React, { useState, useRef, useEffect } from 'react';
import { Play, RotateCcw, Download, FileText, Clock, Layers, History } from 'lucide-react';
import AppShell from '@/components/layout/AppShell';
import { WorkflowVisualizer, WorkflowEvent, NodeStatus, WorkflowTemplateManager, WorkflowHistory } from '@/components/workflow';
import { API_BASE_URL, getAuthHeaderValue } from '@/services/api';
import { useI18n } from '@/i18n';

interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
  nodes: any[];
  variables: Record<string, any>;
  createdAt: string;
  updatedAt: string;
}

interface WorkflowExecution {
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

type TabType = 'monitor' | 'templates' | 'history';

export default function WorkflowMonitorPage() {
  const { t } = useI18n();
  const [activeTab, setActiveTab] = useState<TabType>('monitor');
  const [workflowId, setWorkflowId] = useState<string>('');
  const [isRunning, setIsRunning] = useState(false);
  const [inputText, setInputText] = useState('');
  const [templateManagerOpen, setTemplateManagerOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([]);
  const [executions, setExecutions] = useState<WorkflowExecution[]>([]);
  const [workflowEvents, setWorkflowEvents] = useState<WorkflowEvent[]>([]);
  const [executionDetailOpen, setExecutionDetailOpen] = useState(false);
  const [selectedExecution, setSelectedExecution] = useState<WorkflowExecution | null>(null);
  const eventLogRef = useRef<HTMLDivElement>(null);
  const currentExecutionRef = useRef<WorkflowExecution | null>(null);

  useEffect(() => {
    try {
      const rawTemplates = localStorage.getItem('workflow_templates');
      const rawExecutions = localStorage.getItem('workflow_executions');
      if (rawTemplates) setTemplates(JSON.parse(rawTemplates));
      if (rawExecutions) setExecutions(JSON.parse(rawExecutions));
    } catch {
      setTemplates([]);
      setExecutions([]);
    }
  }, []);

  useEffect(() => {
    localStorage.setItem('workflow_templates', JSON.stringify(templates));
  }, [templates]);

  useEffect(() => {
    localStorage.setItem('workflow_executions', JSON.stringify(executions));
  }, [executions]);

  // 启动工作流
  const handleStartWorkflow = async () => {
    try {
      setIsRunning(true);
      setWorkflowEvents([]);
      if (eventLogRef.current) {
        eventLogRef.current.innerHTML = '';
      }
      const executionId = `exec_${Date.now()}`;
      const executionRecord: WorkflowExecution = {
        id: executionId,
        workflowId: workflowId || 'plot_points_workflow',
        workflowName: '情节点工作流',
        status: 'running',
        startTime: new Date().toISOString(),
        input: { text: inputText || '请生成一个现代都市言情短剧的故事大纲' },
        nodesExecuted: 0,
        nodesTotal: 8,
      };
      currentExecutionRef.current = executionRecord;
      setExecutions((prev) => [executionRecord, ...prev]);

      const response = await fetch(`${API_BASE_URL}/juben/plot-points-workflow/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(getAuthHeaderValue() ? { Authorization: getAuthHeaderValue() as string } : {}),
        },
        body: JSON.stringify({
          input: inputText || '请生成一个现代都市言情短剧的故事大纲',
          user_id: 'demo_user',
          session_id: `session_${Date.now()}`,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to start workflow');
      }

      // 处理 SSE 响应
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                handleWorkflowEvent(data);
              } catch (e) {
                console.error('Failed to parse event:', e);
              }
            }
          }
        }
      }

      setExecutions((prev) =>
        prev.map((execution) =>
          execution.id === executionId
            ? {
                ...execution,
                status: 'success',
                endTime: new Date().toISOString(),
                duration: Date.now() - new Date(execution.startTime).getTime(),
              }
            : execution
        )
      );
    } catch (error) {
      console.error('Workflow error:', error);
      if (currentExecutionRef.current) {
        setExecutions((prev) =>
          prev.map((execution) =>
            execution.id === currentExecutionRef.current!.id
              ? {
                  ...execution,
                  status: 'failed',
                  endTime: new Date().toISOString(),
                  duration: Date.now() - new Date(execution.startTime).getTime(),
                  errorMessage: error instanceof Error ? error.message : t('admin.workflow.workflowFailed'),
                }
              : execution
          )
        );
      }
    } finally {
      setIsRunning(false);
    }
  };

  // 处理工作流事件
  const handleWorkflowEvent = (event: WorkflowEvent | any) => {
    const eventType = event.event_type || event.event;
    const metadata = event.metadata || event.data?.metadata || {};
    // 更新 workflowId
    if (metadata?.workflow_id) {
      setWorkflowId(metadata.workflow_id);
    }

    // 记录事件日志
    if (eventLogRef.current) {
      const logEntry = document.createElement('div');
      logEntry.className = 'text-xs font-mono mb-1';
      logEntry.textContent = `[${new Date().toLocaleTimeString()}] ${JSON.stringify(event)}`;
      eventLogRef.current.appendChild(logEntry);
      eventLogRef.current.scrollTop = eventLogRef.current.scrollHeight;
    }
    setWorkflowEvents((prev) => [...prev, event]);

    if (eventType === 'workflow_node_event' && currentExecutionRef.current) {
      setExecutions((prev) =>
        prev.map((execution) =>
          execution.id === currentExecutionRef.current!.id
            ? {
                ...execution,
                nodesExecuted: Math.min(
                  execution.nodesExecuted + (metadata?.status === NodeStatus.SUCCESS ? 1 : 0),
                  execution.nodesTotal
                ),
              }
            : execution
        )
      );
    }
  };

  // 重置工作流
  const handleReset = () => {
    setWorkflowId('');
    setInputText('');
    setIsRunning(false);
    setWorkflowEvents([]);
    if (eventLogRef.current) {
      eventLogRef.current.innerHTML = '';
    }
  };

  const handleDownloadLog = () => {
    if (workflowEvents.length === 0) return;
    const content = workflowEvents.map((event) => JSON.stringify(event)).join('\n');
    const blob = new Blob([content], { type: 'application/json;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `workflow_events_${Date.now()}.jsonl`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // 模板管理 handlers
  const handleLoadTemplate = (templateId: string) => {
    const template = templates.find((t) => t.id === templateId);
    if (template) {
      setWorkflowId(template.id);
      setInputText(template.description || '');
      setTemplateManagerOpen(false);
    }
  };

  const handleSaveTemplate = async (template: Omit<WorkflowTemplate, 'id' | 'createdAt' | 'updatedAt'>) => {
    const newTemplate: WorkflowTemplate = {
      ...template,
      id: `template_${Date.now()}`,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    setTemplates([...templates, newTemplate]);
  };

  const handleDeleteTemplate = async (templateId: string) => {
    setTemplates(templates.filter((t) => t.id !== templateId));
  };

  // 历史记录 handlers
  const handleRerunExecution = async (executionId: string) => {
    const execution = executions.find((e) => e.id === executionId);
    if (execution) {
      setInputText(JSON.stringify(execution.input));
      setActiveTab('monitor');
      await handleStartWorkflow();
    }
  };

  const handleViewExecutionDetails = (executionId: string) => {
    const execution = executions.find((e) => e.id === executionId) || null;
    setSelectedExecution(execution);
    setExecutionDetailOpen(true);
  };

  const tabs: { key: TabType; label: string; icon: React.ElementType }[] = [
    { key: 'monitor', label: t('admin.workflow.tab.monitor'), icon: FileText },
    { key: 'templates', label: t('admin.workflow.tab.templates'), icon: Layers },
    { key: 'history', label: t('admin.workflow.tab.history'), icon: Clock },
  ];

  const renderTabContent = () => {
    switch (activeTab) {
      case 'monitor':
        return (
          <div className="glass-panel overflow-hidden h-[65vh] min-h-[480px] flex">
            {/* 工作流可视化 */}
            <div className="flex-1">
              <WorkflowVisualizer
                workflowId={workflowId}
                onEvent={handleWorkflowEvent}
                externalEvents={workflowEvents}
                className="h-full"
              />
            </div>

            {/* 事件日志侧边栏 */}
            <aside className="w-80 bg-white/50 border-l border-pearl-line flex flex-col">
              <div className="px-4 py-3 border-b border-pearl-line flex items-center justify-between">
                <h2 className="font-semibold text-ink">{t('admin.workflow.eventLog')}</h2>
                <button
                  onClick={handleDownloadLog}
                  className="p-1 hover:bg-pearl-soft rounded"
                >
                  <Download className="w-4 h-4 text-ink-muted" />
                </button>
              </div>
              <div
                ref={eventLogRef}
                className="flex-1 p-4 overflow-y-auto text-xs font-mono space-y-1"
              />
            </aside>
          </div>
        );

      case 'templates':
        return (
          <div className="glass-panel flex items-center justify-center min-h-[320px]">
            <div className="text-center">
              <Layers className="w-16 h-16 mx-auto mb-4 text-ink-faint" />
              <h3 className="text-lg font-semibold text-ink mb-2">
                {t('admin.workflow.templateManager')}
              </h3>
              <p className="text-ink-muted mb-4">
                {t('admin.workflow.templateManagerDesc')}
              </p>
              <button
                onClick={() => setTemplateManagerOpen(true)}
                className="btn btn-primary"
              >
                {t('admin.workflow.openTemplateManager')}
              </button>
            </div>
          </div>
        );

      case 'history':
        return (
          <div className="glass-panel flex items-center justify-center min-h-[320px]">
            <div className="text-center">
              <History className="w-16 h-16 mx-auto mb-4 text-ink-faint" />
              <h3 className="text-lg font-semibold text-ink mb-2">
                {t('admin.workflow.executionHistory')}
              </h3>
              <p className="text-ink-muted mb-4">
                {t('admin.workflow.executionHistoryDesc')}
              </p>
              <button
                onClick={() => setHistoryOpen(true)}
                className="btn btn-primary"
              >
                {t('admin.workflow.viewHistory')}
              </button>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <AppShell
      title={t('admin.workflow.title')}
      subtitle={t('admin.workflow.subtitle')}
      actions={
        activeTab === 'monitor' ? (
          <div className="flex gap-2">
            <button
              onClick={handleStartWorkflow}
              disabled={isRunning}
              className="btn btn-primary btn-sm"
            >
              <Play className="w-4 h-4" />
              {t('admin.workflow.start')}
            </button>
            <button
              onClick={handleReset}
              className="btn btn-secondary btn-sm"
            >
              <RotateCcw className="w-4 h-4" />
              {t('admin.workflow.reset')}
            </button>
          </div>
        ) : undefined
      }
    >
      <div className="px-4 sm:px-8 lg:px-10 py-6 sm:py-8 max-w-6xl mx-auto space-y-6">
        {/* 控制栏 */}
        <div className="glass-panel p-4 sm:p-5 space-y-4">
          {/* 标签页导航 */}
          <div className="flex items-center gap-1 flex-wrap">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                  activeTab === tab.key
                    ? 'bg-atelier-teal text-white'
                    : 'bg-pearl-soft text-ink-muted hover:bg-pearl-soft/70'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </div>

          {/* 输入区域 - 仅在监控标签显示 */}
          {activeTab === 'monitor' && (
            <div>
              <label className="block text-sm font-medium text-ink mb-2">
                {t('admin.workflow.inputText')}
              </label>
              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder={t('admin.workflow.inputPlaceholder')}
                rows={3}
                className="w-full px-4 py-2 border border-pearl-line rounded-lg bg-white/60 focus:outline-none focus:ring-2 focus:ring-atelier-teal/30 focus:border-transparent text-ink"
              />
            </div>
          )}
        </div>

        {/* 主内容区 */}
        {renderTabContent()}
      </div>

      {/* 模板管理器弹窗 */}
      <WorkflowTemplateManager
        isOpen={templateManagerOpen}
        onClose={() => setTemplateManagerOpen(false)}
        templates={templates}
        onLoad={handleLoadTemplate}
        onSave={handleSaveTemplate}
        onDelete={handleDeleteTemplate}
      />

      {/* 执行历史弹窗 */}
      <WorkflowHistory
        isOpen={historyOpen}
        onClose={() => setHistoryOpen(false)}
        executions={executions}
        onRerun={handleRerunExecution}
        onViewDetails={handleViewExecutionDetails}
      />

      {executionDetailOpen && selectedExecution && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="glass-dense rounded-2xl shadow-atelier-lg max-w-3xl w-full max-h-[90vh] overflow-hidden">
            <div className="p-6 border-b border-pearl-line flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-ink">
                  {t('admin.workflow.detail')}
                </h3>
                <p className="text-xs text-ink-muted mt-1">
                  {selectedExecution.workflowName} · {selectedExecution.id}
                </p>
              </div>
              <button
                onClick={() => setExecutionDetailOpen(false)}
                className="p-2 hover:bg-pearl-soft rounded-lg"
              >
                ✕
              </button>
            </div>
            <div className="p-6 overflow-y-auto max-h-[70vh] space-y-4 text-sm">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-xs text-ink-muted">{t('admin.status')}</div>
                  <div className="font-medium text-ink">{selectedExecution.status}</div>
                </div>
                <div>
                  <div className="text-xs text-ink-muted">{t('admin.workflow.nodeProgress')}</div>
                  <div className="font-medium text-ink">
                    {selectedExecution.nodesExecuted} / {selectedExecution.nodesTotal}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-ink-muted">{t('admin.workflow.startTime')}</div>
                  <div className="font-medium text-ink">
                    {new Date(selectedExecution.startTime).toLocaleString()}
                  </div>
                </div>
                {selectedExecution.endTime && (
                  <div>
                    <div className="text-xs text-ink-muted">{t('admin.workflow.endTime')}</div>
                    <div className="font-medium text-ink">
                      {new Date(selectedExecution.endTime).toLocaleString()}
                    </div>
                  </div>
                )}
              </div>

              {selectedExecution.errorMessage && (
                <div className="p-3 bg-red-50 rounded-lg text-red-700">
                  {selectedExecution.errorMessage}
                </div>
              )}

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div>
                  <div className="text-xs text-ink-muted mb-2">{t('admin.workflow.input')}</div>
                  <pre className="text-xs bg-pearl-soft p-3 rounded-lg overflow-auto">
                    {JSON.stringify(selectedExecution.input, null, 2)}
                  </pre>
                </div>
                <div>
                  <div className="text-xs text-ink-muted mb-2">{t('admin.workflow.output')}</div>
                  <pre className="text-xs bg-pearl-soft p-3 rounded-lg overflow-auto">
                    {selectedExecution.output ? JSON.stringify(selectedExecution.output, null, 2) : t('admin.workflow.noOutput')}
                  </pre>
                </div>
              </div>
            </div>
            <div className="p-6 border-t border-pearl-line flex justify-end">
              <button
                onClick={() => setExecutionDetailOpen(false)}
                className="btn btn-secondary"
              >
                {t('admin.close')}
              </button>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}
