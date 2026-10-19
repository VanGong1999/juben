/**
 * 错误边界组件
 * 捕获子组件中的错误并显示友好的错误信息
 * 增强版：支持路由懒加载错误处理
 */
import React, { Component, ErrorInfo, ReactNode } from 'react';
import { translate } from '@/i18n';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  // 新增：是否为路由错误边界
  forRoute?: boolean;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null
  };

  public static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
      errorInfo: null
    };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);

    // 检查是否为懒加载错误
    const isChunkError = error.name === 'ChunkLoadError' ||
                        error.message.includes('Loading chunk') ||
                        error.message.includes('chunk') ||
                        error.message.includes('Failed to fetch');

    if (isChunkError) {
      console.warn('Chunk loading error detected:', error.message);
      // 可以在这里触发自动刷新
    }

    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
    this.setState({
      error,
      errorInfo
    });
  }

  private handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null
    });
  };

  private isChunkLoadError(): boolean {
    if (!this.state.error) return false;
    return this.state.error.name === 'ChunkLoadError' ||
           this.state.error.message.includes('Loading chunk') ||
           this.state.error.message.includes('chunk');
  }

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // 处理懒加载错误
      if (this.props.forRoute && this.isChunkLoadError()) {
        return (
          <div className="min-h-screen flex items-center justify-center bg-gray-50">
            <div className="max-w-md w-full bg-white shadow-lg rounded-lg p-8">
              <div className="text-center">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-yellow-100 text-yellow-600 mb-4">
                  <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                </div>
                <h2 className="text-2xl font-bold text-gray-900 mb-2">{translate('ui.contentUpdating')}</h2>
                <p className="text-gray-600 mb-6">
                  {translate('ui.contentUpdated')}
                </p>
                <button
                  onClick={() => window.location.reload()}
                  className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  {translate('ui.refreshNow')}
                </button>
              </div>
            </div>
          </div>
        );
      }

      // 常规错误处理
      return (
        <div className="min-h-[400px] flex items-center justify-center p-4">
          <div className="max-w-md w-full bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
                <svg className="w-6 h-6 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.932-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.932 3z" />
                </svg>
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">{translate('ui.errorOccurred')}</h2>
                <p className="text-sm text-gray-500 dark:text-gray-400">{translate('ui.pageLoadFailed')}</p>
              </div>
            </div>
            <div className="bg-red-50 dark:bg-red-900/20 rounded-md p-3 mb-4">
              <p className="text-sm text-red-800 dark:text-red-200 font-mono break-all">
                {this.state.error?.message || translate('workspace.unknownError')}
              </p>
            </div>
            <div className="flex gap-2">
              <button onClick={this.handleReset} className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors text-sm">
                {translate('ui.reload')}
              </button>
              <button onClick={() => window.location.href = '/'} className="flex-1 px-4 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-800 dark:text-gray-200 rounded-md transition-colors text-sm">
                {translate('ui.backHome')}
              </button>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

/**
 * 路由错误边界 - 专门用于处理路由懒加载错误
 */
export const RouteErrorBoundary: React.FC<{
  children: ReactNode;
}> = ({ children }) => {
  return (
    <ErrorBoundary forRoute={true}>
      {children}
    </ErrorBoundary>
  );
};
