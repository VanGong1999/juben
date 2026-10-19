/**
 * 自定义工作流节点组件
 * 支持动态状态显示、图标、动画效果
 */

import React, { memo } from 'react';
import { Handle, Position, NodeProps, Node } from '@xyflow/react';
import { clsx } from 'clsx';
import { NodeStatus, WorkflowNodeData } from './types';
import {
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  AlertCircle,
  ChevronRight,
  FileText,
  Settings,
  GitBranch,
  Database
} from 'lucide-react';

// 节点状态图标映射
const StatusIcon: Record<NodeStatus, React.ElementType> = {
  [NodeStatus.IDLE]: Clock,
  [NodeStatus.WAITING]: Clock,
  [NodeStatus.PROCESSING]: Loader2,
  [NodeStatus.SUCCESS]: CheckCircle2,
  [NodeStatus.FAILED]: XCircle,
  [NodeStatus.SKIPPED]: AlertCircle,
};

// 节点类型图标映射
const NodeTypeIcon: Record<string, React.ElementType> = {
  input: FileText,
  preprocessing: Settings,
  parallel: GitBranch,
  output: Database,
  aggregator: ChevronRight,
};

// 节点状态颜色映射
const statusColors = {
  [NodeStatus.IDLE]: {
    bg: 'bg-gray-50 dark:bg-gray-800',
    border: 'border-gray-300 dark:border-gray-600',
    text: 'text-gray-600 dark:text-gray-400',
    icon: 'text-gray-400'
  },
  [NodeStatus.WAITING]: {
    bg: 'bg-blue-50 dark:bg-blue-900/20',
    border: 'border-blue-300 dark:border-blue-600',
    text: 'text-blue-600 dark:text-blue-400',
    icon: 'text-blue-500'
  },
  [NodeStatus.PROCESSING]: {
    bg: 'bg-yellow-50 dark:bg-yellow-900/20',
    border: 'border-yellow-400 dark:border-yellow-500',
    text: 'text-yellow-700 dark:text-yellow-300',
    icon: 'text-yellow-500'
  },
  [NodeStatus.SUCCESS]: {
    bg: 'bg-green-50 dark:bg-green-900/20',
    border: 'border-green-400 dark:border-green-500',
    text: 'text-green-700 dark:text-green-300',
    icon: 'text-green-500'
  },
  [NodeStatus.FAILED]: {
    bg: 'bg-red-50 dark:bg-red-900/20',
    border: 'border-red-400 dark:border-red-500',
    text: 'text-red-700 dark:text-red-300',
    icon: 'text-red-500'
  },
  [NodeStatus.SKIPPED]: {
    bg: 'bg-gray-100 dark:bg-gray-700',
    border: 'border-gray-400 dark:border-gray-500',
    text: 'text-gray-500 dark:text-gray-400',
    icon: 'text-gray-400'
  },
};

export const WorkflowNode = memo(({ data, selected }: NodeProps<Node<WorkflowNodeData>>) => {
  const StatusIconComponent = StatusIcon[data.status];
  const TypeIconComponent = NodeTypeIcon[data.nodeType] || FileText;
  const colors = statusColors[data.status];

  const isProcessing = data.status === NodeStatus.PROCESSING;

  return (
    <div
      className={clsx(
        'px-4 py-3 rounded-lg border-2 min-w-[200px] max-w-[280px] transition-all duration-300',
        colors.bg,
        colors.border,
        selected && 'ring-2 ring-offset-2 ring-blue-400',
        isProcessing && 'animate-pulse'
      )}
    >
      {/* 输入连接点 */}
      <Handle
        type="target"
        position={Position.Top}
        className={clsx(
          'w-3 h-3 !bg-gray-400 !border-2 !border-white dark:!border-gray-700',
          data.status !== NodeStatus.IDLE && '!bg-blue-400'
        )}
      />

      {/* 节点内容 */}
      <div className="flex items-start gap-3">
        {/* 类型图标 */}
        <div className={clsx('mt-0.5', colors.icon)}>
          <TypeIconComponent className="w-5 h-5" />
        </div>

        {/* 主要内容 */}
        <div className="flex-1 min-w-0">
          {/* 标签 */}
          <div className={clsx('font-semibold text-sm truncate', colors.text)}>
            {data.label}
          </div>

          {/* 描述 */}
          {data.description && (
            <div className="text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5">
              {data.description}
            </div>
          )}

          {/* 输出摘要 */}
          {data.outputSnapshot && data.status === NodeStatus.SUCCESS && (
            <div className="text-xs text-gray-600 dark:text-gray-300 mt-1 line-clamp-2">
              {data.outputSnapshot}
            </div>
          )}

          {/* 错误信息 */}
          {data.error && data.status === NodeStatus.FAILED && (
            <div className="text-xs text-red-600 dark:text-red-400 mt-1 line-clamp-2">
              {data.error}
            </div>
          )}

          {/* 执行时间 */}
          {data.duration !== undefined && (
            <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {data.duration > 1000
                ? `${(data.duration / 1000).toFixed(1)}s`
                : `${data.duration}ms`}
            </div>
          )}
        </div>

        {/* 状态图标 */}
        <div className={clsx(isProcessing && 'animate-spin', colors.icon)}>
          <StatusIconComponent className="w-5 h-5" />
        </div>
      </div>

      {/* 输出连接点 */}
      <Handle
        type="source"
        position={Position.Bottom}
        className={clsx(
          'w-3 h-3 !bg-gray-400 !border-2 !border-white dark:!border-gray-700',
          data.status === NodeStatus.SUCCESS && '!bg-green-400'
        )}
      />
    </div>
  );
});

WorkflowNode.displayName = 'WorkflowNode';
