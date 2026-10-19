/**
 * 通知容器组件
 * 显示所有通知消息
 */

import React from 'react';
import { useNotificationStore } from '@/store/notificationStore';
import { CheckCircle, AlertCircle, AlertTriangle, Info, X } from 'lucide-react';
import { useI18n } from '@/i18n';

export const NotificationContainer: React.FC = () => {
  const { notifications, clearAll } = useNotificationStore();
  const { t } = useI18n();

  // 按时间排序，最新的在前面
  const sortedNotifications = [...notifications].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );

  if (sortedNotifications.length === 0) {
    return null;
  }

  return (
    <div className="fixed top-4 right-4 z-[9999] flex flex-col gap-2 max-w-md w-full">
      {/* 清除所有按钮 */}
      {notifications.length > 1 && (
        <button
          onClick={clearAll}
          className="self-end mb-2 px-3 py-1 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
        >
          {t('ui.clearAll')}
        </button>
      )}

      {sortedNotifications.map((notification) => (
        <NotificationItem
          key={notification.id}
          notification={notification}
        />
      ))}
    </div>
  );
};

/**
 * 单个通知项组件
 */
interface NotificationItemProps {
  notification: {
    id: string;
    type: 'success' | 'error' | 'warning' | 'info';
    title: string;
    message: string;
    timestamp: string;
    actions?: Array<{
      label: string;
      onClick: () => void;
      primary?: boolean;
    }>;
  };
}

const NotificationItem: React.FC<NotificationItemProps> = ({ notification }) => {
  const { removeNotification } = useNotificationStore();
  const { t } = useI18n();

  const icons = {
    success: <CheckCircle className="w-5 h-5" />,
    error: <AlertCircle className="w-5 h-5" />,
    warning: <AlertTriangle className="w-5 h-5" />,
    info: <Info className="w-5 h-5" />,
  };

  const styles = {
    success: {
      bg: 'bg-green-50 dark:bg-green-900/30',
      border: 'border-green-200 dark:border-green-800',
      icon: 'text-green-500',
      title: 'text-green-800 dark:text-green-200',
    },
    error: {
      bg: 'bg-red-50 dark:bg-red-900/30',
      border: 'border-red-200 dark:border-red-800',
      icon: 'text-red-500',
      title: 'text-red-800 dark:text-red-200',
    },
    warning: {
      bg: 'bg-yellow-50 dark:bg-yellow-900/30',
      border: 'border-yellow-200 dark:border-yellow-800',
      icon: 'text-yellow-500',
      title: 'text-yellow-800 dark:text-yellow-200',
    },
    info: {
      bg: 'bg-blue-50 dark:bg-blue-900/30',
      border: 'border-blue-200 dark:border-blue-800',
      icon: 'text-blue-500',
      title: 'text-blue-800 dark:text-blue-200',
    },
  };

  const style = styles[notification.type];

  return (
    <div
      className={`${style.bg} ${style.border} border rounded-lg shadow-lg p-4 animate-in slide-in-from-right-full duration-300`}
      role="alert"
    >
      <div className="flex items-start gap-3">
        {/* 图标 */}
        <div className={`flex-shrink-0 ${style.icon}`}>
          {icons[notification.type]}
        </div>

        {/* 内容 */}
        <div className="flex-1 min-w-0">
          <h4 className={`font-medium ${style.title} text-sm`}>
            {notification.title}
          </h4>
          <p className="mt-1 text-sm text-gray-700 dark:text-gray-300">
            {notification.message}
          </p>

          {/* 操作按钮 */}
          {notification.actions && notification.actions.length > 0 && (
            <div className="mt-3 flex gap-2">
              {notification.actions.map((action, index) => (
                <button
                  key={index}
                  onClick={() => {
                    action.onClick();
                    removeNotification(notification.id);
                  }}
                  className={`px-3 py-1 text-xs rounded transition-colors ${
                    action.primary
                      ? 'bg-blue-500 text-white hover:bg-blue-600'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-300'
                  }`}
                >
                  {action.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* 关闭按钮 */}
        <button
          onClick={() => removeNotification(notification.id)}
          className="flex-shrink-0 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
          aria-label={t('ui.closeNotification')}
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

export default NotificationContainer;
