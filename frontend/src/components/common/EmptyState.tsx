/**
 * 空状态组件
 * 用于展示无数据、无搜索结果等场景
 */

import React from 'react';
import { LucideIcon, Database, Search, MousePointerClick, AlertCircle, MessageSquare, FolderOpen, FileText } from 'lucide-react';
import { useI18n } from '@/i18n';

interface EmptyStateProps {
  /** 图标组件 */
  icon?: LucideIcon;
  /** 标题 */
  title: string;
  /** 描述 */
  description?: string;
  /** 主要操作按钮文本 */
  actionText?: string;
  /** 主要操作回调 */
  onAction?: () => void;
  /** 次要操作按钮文本 */
  secondaryActionText?: string;
  /** 次要操作回调 */
  onSecondaryAction?: () => void;
  /** 自定义类名 */
  className?: string;
  /** 大小 */
  size?: 'sm' | 'md' | 'lg';
  /** 类型 */
  type?: 'default' | 'search' | 'error' | 'success';
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  actionText,
  onAction,
  secondaryActionText,
  onSecondaryAction,
  className = '',
  size = 'md',
  type = 'default',
}: EmptyStateProps) {
  const sizeClasses = {
    sm: 'p-6',
    md: 'p-8',
    lg: 'p-12',
  };

  const iconSizes = {
    sm: 'w-10 h-10',
    md: 'w-16 h-16',
    lg: 'w-24 h-24',
  };

  const typeStyles = {
    default: 'text-gray-400',
    search: 'text-blue-400',
    error: 'text-red-400',
    success: 'text-green-400',
  };

  return (
    <div className={`flex flex-col items-center justify-center text-center ${sizeClasses[size]} ${className}`}>
      {Icon && (
        <Icon className={`${iconSizes[size]} ${typeStyles[type]} mb-4 mx-auto`} />
      )}

      <h3 className={`font-semibold text-gray-900 mb-2 ${size === 'sm' ? 'text-base' : size === 'md' ? 'text-lg' : 'text-xl'}`}>
        {title}
      </h3>

      {description && (
        <p className={`text-gray-500 mb-6 max-w-sm ${size === 'sm' ? 'text-sm' : 'text-base'}`}>
          {description}
        </p>
      )}

      {(actionText || secondaryActionText) && (
        <div className="flex items-center gap-3">
          {actionText && (
            <button
              onClick={onAction}
              className="px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 transition-colors font-medium"
            >
              {actionText}
            </button>
          )}
          {secondaryActionText && (
            <button
              onClick={onSecondaryAction}
              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium"
            >
              {secondaryActionText}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * 预设的空状态变体
 */
export function EmptyStateNoData({ onAction }: { onAction?: () => void }) {
  const { t } = useI18n();
  return (
    <EmptyState
      icon={Database}
      title={t('empty.noData')}
      description={t('empty.noDataDesc')}
      actionText={t('empty.createData')}
      onAction={onAction}
    />
  );
}

export function EmptyStateNoResults({ onClear }: { onClear?: () => void }) {
  const { t } = useI18n();
  return (
    <EmptyState
      icon={Search}
      title={t('empty.noResults')}
      description={t('empty.noResultsDesc')}
      actionText={t('empty.clearFilter')}
      onAction={onClear}
      type="search"
    />
  );
}

export function EmptyStateNoSelection() {
  const { t } = useI18n();
  return (
    <EmptyState
      icon={MousePointerClick}
      title={t('empty.noSelection')}
      description={t('empty.noSelectionDesc')}
      size="sm"
    />
  );
}

export function EmptyStateError({ onRetry }: { onRetry?: () => void }) {
  const { t } = useI18n();
  return (
    <EmptyState
      icon={AlertCircle}
      title={t('empty.error')}
      description={t('empty.errorDesc')}
      actionText={t('empty.retry')}
      onAction={onRetry}
      type="error"
    />
  );
}

export function EmptyStateNoMessages({ onNewChat }: { onNewChat?: () => void }) {
  const { t } = useI18n();
  return (
    <EmptyState
      icon={MessageSquare}
      title={t('empty.newChat')}
      description={t('empty.newChatDesc')}
      actionText={t('empty.startChat')}
      onAction={onNewChat}
    />
  );
}

export function EmptyStateNoProjects({ onCreate }: { onCreate?: () => void }) {
  const { t } = useI18n();
  return (
    <EmptyState
      icon={FolderOpen}
      title={t('empty.noProjects')}
      description={t('empty.noProjectsDesc')}
      actionText={t('empty.createProject')}
      onAction={onCreate}
    />
  );
}

export function EmptyStateNoFiles({ onUpload }: { onUpload?: () => void }) {
  const { t } = useI18n();
  return (
    <EmptyState
      icon={FileText}
      title={t('empty.noFiles')}
      description={t('empty.noFilesDesc')}
      actionText={t('empty.uploadFile')}
      onAction={onUpload}
    />
  );
}
