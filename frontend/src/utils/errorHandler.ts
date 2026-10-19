/**
 * 全局错误处理器
 */

import { APIError } from '@/services/api';
import { useNotificationStore } from '@/store/notificationStore';

/**
 * 错误类型枚举
 */
export enum ErrorType {
  NETWORK = 'network',
  API = 'api',
  VALIDATION = 'validation',
  AUTHENTICATION = 'authentication',
  AUTHORIZATION = 'authorization',
  NOT_FOUND = 'not_found',
  SERVER = 'server',
  UNKNOWN = 'unknown',
}

/**
 * 应用错误类
 */
export class AppError extends Error {
  constructor(
    message: string,
    public type: ErrorType = ErrorType.UNKNOWN,
    public code?: string,
    public details?: any
  ) {
    super(message);
    this.name = 'AppError';
  }
}

/**
 * 错误详情接口
 */
export interface ErrorDetails {
  message: string;
  type: ErrorType;
  code?: string;
  stack?: string;
  context?: Record<string, any>;
}

/**
 * 解析错误信息
 */
export const parseError = (error: unknown): ErrorDetails => {
  // API 错误（自定义 APIError，来自 fetch 客户端）
  if (error instanceof APIError) {
    const status = error.status;

    if (status === 401) {
      return {
        message: error.message || '认证失败，请重新登录',
        type: ErrorType.AUTHENTICATION,
        code: '401',
      };
    }

    if (status === 403) {
      return {
        message: error.message || '没有权限执行此操作',
        type: ErrorType.AUTHORIZATION,
        code: '403',
      };
    }

    if (status === 404) {
      return {
        message: error.message || '请求的资源不存在',
        type: ErrorType.NOT_FOUND,
        code: '404',
      };
    }

    if (status === 422) {
      return {
        message: error.message || '请求数据验证失败',
        type: ErrorType.VALIDATION,
        code: '422',
      };
    }

    if (status && status >= 500) {
      return {
        message: error.message || '服务器错误，请稍后重试',
        type: ErrorType.SERVER,
        code: String(status),
      };
    }

    return {
      message: error.message || '请求失败',
      type: ErrorType.API,
      code: String(status),
    };
  }

  // 网络错误（fetch 连接失败抛出 TypeError）
  if (error instanceof TypeError) {
    return {
      message: '网络连接失败，请检查网络设置',
      type: ErrorType.NETWORK,
    };
  }

  // AppError
  if (error instanceof AppError) {
    return {
      message: error.message,
      type: error.type,
      code: error.code,
      context: error.details,
    };
  }

  // 标准Error
  if (error instanceof Error) {
    return {
      message: error.message,
      type: ErrorType.UNKNOWN,
      stack: error.stack,
    };
  }

  // 字符串错误
  if (typeof error === 'string') {
    return {
      message: error,
      type: ErrorType.UNKNOWN,
    };
  }

  // 未知错误
  return {
    message: '发生未知错误',
    type: ErrorType.UNKNOWN,
  };
};

/**
 * 显示错误通知
 */
export const showErrorNotification = (error: unknown) => {
  const { error: showError } = useNotificationStore.getState();
  const details = parseError(error);

  // 根据错误类型显示不同的标题
  const titles: Record<ErrorType, string> = {
    [ErrorType.NETWORK]: '网络错误',
    [ErrorType.API]: '请求失败',
    [ErrorType.VALIDATION]: '输入验证失败',
    [ErrorType.AUTHENTICATION]: '认证失败',
    [ErrorType.AUTHORIZATION]: '权限不足',
    [ErrorType.NOT_FOUND]: '未找到',
    [ErrorType.SERVER]: '服务器错误',
    [ErrorType.UNKNOWN]: '错误',
  };

  showError(titles[details.type], details.message, 8000);

  // 记录错误到控制台
  console.error('[Error Handler]', {
    ...details,
    originalError: error,
  });

  return details;
};

/**
 * 异步错误包装器
 * 自动捕获并显示错误
 */
export const withErrorHandling = async <T>(
  promise: Promise<T>,
  context?: string
): Promise<T | null> => {
  try {
    return await promise;
  } catch (error) {
    if (context) {
      console.error(`[Error in ${context}]`, error);
    }
    showErrorNotification(error);
    return null;
  }
};

/**
 * 同步错误包装器
 */
export const withSyncErrorHandling = <T>(
  fn: () => T,
  context?: string
): T | null => {
  try {
    return fn();
  } catch (error) {
    if (context) {
      console.error(`[Error in ${context}]`, error);
    }
    showErrorNotification(error);
    return null;
  }
};

/**
 * 重试装饰器
 * 自动重试失败的操作
 */
export const withRetry = async <T>(
  fn: () => Promise<T>,
  options: {
    maxRetries?: number;
    delay?: number;
    backoff?: boolean;
    onRetry?: (attempt: number, error: unknown) => void;
  } = {}
): Promise<T> => {
  const {
    maxRetries = 3,
    delay = 1000,
    backoff = true,
    onRetry,
  } = options;

  let lastError: unknown;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;

      if (attempt === maxRetries) {
        break;
      }

      const currentDelay = backoff ? delay * Math.pow(2, attempt) : delay;

      onRetry?.(attempt + 1, error);

      await new Promise((resolve) => setTimeout(resolve, currentDelay));
    }
  }

  throw lastError;
};

/**
 * 错误边界处理函数
 */
export const handleComponentError = (error: Error, errorInfo: any) => {
  const details = parseError(error);

  console.error('[Component Error]', {
    ...details,
    componentStack: errorInfo.componentStack,
  });

  // 显示用户友好的错误通知
  const { error: showError } = useNotificationStore.getState();
  showError('组件错误', '应用程序遇到错误，请刷新页面', 0); // 持久显示
};
