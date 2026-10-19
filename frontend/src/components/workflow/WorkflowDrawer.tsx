/**
 * 工作流节点详情抽屉组件
 * 点击节点时显示详细信息
 */

import React, { useState } from 'react';
import { X, Copy, Download, ChevronDown, ChevronUp } from 'lucide-react';
import { clsx } from 'clsx';
import { NodeStatus, NodeDetails } from './types';
import { useI18n } from '@/i18n';

interface WorkflowDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  details: NodeDetails | null;
}

// 状态标签组件
const STATUS_LABEL_KEYS: Record<NodeStatus, string> = {
  [NodeStatus.IDLE]: 'chatGraph.workflow.status.idle',
  [NodeStatus.WAITING]: 'chatGraph.workflow.status.waiting',
  [NodeStatus.PROCESSING]: 'chatGraph.workflow.status.processing',
  [NodeStatus.SUCCESS]: 'chatGraph.workflow.status.success',
  [NodeStatus.FAILED]: 'chatGraph.workflow.status.failed',
  [NodeStatus.SKIPPED]: 'chatGraph.workflow.status.skipped',
};

const StatusBadge: React.FC<{ status: NodeStatus }> = ({ status }) => {
  const { t } = useI18n();
  const styles = {
    [NodeStatus.IDLE]: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
    [NodeStatus.WAITING]: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
    [NodeStatus.PROCESSING]: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
    [NodeStatus.SUCCESS]: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
    [NodeStatus.FAILED]: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
    [NodeStatus.SKIPPED]: 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400',
  };

  return (
    <span className={clsx('px-2 py-1 rounded-md text-xs font-medium', styles[status])}>
      {t(STATUS_LABEL_KEYS[status])}
    </span>
  );
};

// 可折叠面板组件
const CollapsibleSection: React.FC<{
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}> = ({ title, defaultOpen = true, children }) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-800 flex items-center justify-between hover:bg-gray-100 dark:hover:bg-gray-750 transition-colors"
      >
        <span className="font-medium text-sm">{title}</span>
        {isOpen ? (
          <ChevronUp className="w-4 h-4 text-gray-500" />
        ) : (
          <ChevronDown className="w-4 h-4 text-gray-500" />
        )}
      </button>
      {isOpen && <div className="p-4">{children}</div>}
    </div>
  );
};

// JSON 代码显示组件
const CodeBlock: React.FC<{ code: any; language?: string }> = ({ code, language = 'json' }) => {
  const { t } = useI18n();
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    const text = typeof code === 'string' ? code : JSON.stringify(code, null, 2);
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const codeString = typeof code === 'string' ? code : JSON.stringify(code, null, 2);

  return (
    <div className="relative group">
      <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg text-xs overflow-x-auto">
        <code>{codeString}</code>
      </pre>
      <button
        onClick={handleCopy}
        className="absolute top-2 right-2 p-2 bg-gray-700 rounded-md opacity-0 group-hover:opacity-100 transition-opacity"
        title={t('studio.copy')}
      >
        {copied ? (
          <Check className="w-4 h-4 text-green-400" />
        ) : (
          <Copy className="w-4 h-4 text-gray-300" />
        )}
      </button>
    </div>
  );
};

const Check = ({ className }: { className?: string }) => (
  <svg
    className={className}
    fill="none"
    stroke="currentColor"
    viewBox="0 0 24 24"
  >
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
  </svg>
);

export const WorkflowDrawer: React.FC<WorkflowDrawerProps> = ({
  isOpen,
  onClose,
  details
}) => {
  const { t } = useI18n();
  if (!isOpen || !details) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* 背景遮罩 */}
      <div
        className="absolute inset-0 bg-black/30 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* 抽屉主体 */}
      <div className="relative w-full max-w-lg bg-white dark:bg-gray-900 shadow-xl h-full overflow-y-auto">
        {/* 头部 */}
        <div className="sticky top-0 z-10 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                {details.label}
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                {t('chatGraph.workflow.nodeId')} {details.nodeId}
              </p>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-gray-500" />
            </button>
          </div>

          {/* 状态徽章 */}
          <div className="mt-3">
            <StatusBadge status={details.status} />
          </div>
        </div>

        {/* 内容区域 */}
        <div className="px-6 py-4 space-y-4">
          {/* 执行信息 */}
          {(details.duration !== undefined || details.error) && (
            <CollapsibleSection title={t('chatGraph.workflow.execInfo')}>
              <dl className="space-y-2 text-sm">
                {details.duration !== undefined && (
                  <div className="flex justify-between">
                    <dt className="text-gray-500 dark:text-gray-400">{t('chatGraph.workflow.duration')}</dt>
                    <dd className="text-gray-900 dark:text-white font-medium">
                      {details.duration > 1000
                        ? t('chatGraph.workflow.seconds', { n: (details.duration / 1000).toFixed(2) })
                        : t('chatGraph.workflow.milliseconds', { n: details.duration })}
                    </dd>
                  </div>
                )}
                {details.error && (
                  <div className="flex flex-col gap-1">
                    <dt className="text-gray-500 dark:text-gray-400">{t('chatGraph.workflow.errorInfo')}</dt>
                    <dd className="text-red-600 dark:text-red-400 font-medium">
                      {details.error}
                    </dd>
                  </div>
                )}
              </dl>
            </CollapsibleSection>
          )}

          {/* 输入数据 */}
          {details.input && (
            <CollapsibleSection title={t('chatGraph.workflow.inputData')}>
              <CodeBlock code={details.input} />
            </CollapsibleSection>
          )}

          {/* 输出数据 */}
          {details.output && (
            <CollapsibleSection title={t('chatGraph.workflow.outputData')}>
              <CodeBlock code={details.output} />
            </CollapsibleSection>
          )}

          {/* 中间变量 */}
          {details.intermediateVariables && Object.keys(details.intermediateVariables).length > 0 && (
            <CollapsibleSection title={t('chatGraph.workflow.intermediateVars')}>
              <CodeBlock code={details.intermediateVariables} />
            </CollapsibleSection>
          )}

          {/* 执行日志 */}
          {details.logs && details.logs.length > 0 && (
            <CollapsibleSection title={t('chatGraph.workflow.execLogs')} defaultOpen={false}>
              <div className="space-y-1">
                {details.logs.map((log, index) => (
                  <div
                    key={index}
                    className="text-xs font-mono bg-gray-50 dark:bg-gray-800 px-3 py-2 rounded"
                  >
                    {log}
                  </div>
                ))}
              </div>
            </CollapsibleSection>
          )}
        </div>

        {/* 底部操作栏 */}
        <div className="sticky bottom-0 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700 px-6 py-4">
          <div className="flex gap-3">
            <button className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors">
              {t('chatGraph.workflow.exportDetail')}
            </button>
            <button className="flex-1 px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-900 dark:text-white rounded-lg font-medium transition-colors">
              {t('chatGraph.workflow.viewLogs')}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
