/**
 * 分屏布局组件 - 左文右聊 IDE 布局
 * 左侧 (60%): 工作区 - 显示 AI 生成的成果
 * 右侧 (40%): 聊天侧边栏 - 用户与 Agent 对话
 *
 * 响应式设计:
 * - 大屏 (>= 1024px): 60/40 分栏
 * - 中屏 (768px - 1023px): 50/50 分栏
 * - 小屏 (< 768px): 可切换的单栏视图
 */

import { ReactNode, useState } from 'react';
import { clsx } from 'clsx';
import { ChevronLeft, PanelLeftClose, PanelRightClose } from 'lucide-react';
import { useI18n } from '@/i18n';

interface SplitScreenLayoutProps {
  /** 左侧工作区内容 */
  workspace: ReactNode;
  /** 右侧聊天内容 */
  chat: ReactNode;
  /** 顶部导航栏内容 */
  header: ReactNode;
  /** 是否全屏模式 */
  fullscreen?: boolean;
  /** 初始视图模式 */
  defaultView?: 'both' | 'workspace' | 'chat';
  /** 是否显示切换按钮 */
  showToggleButtons?: boolean;
  /** 自定义类名 */
  className?: string;
}

export default function SplitScreenLayout({
  workspace,
  chat,
  header,
  fullscreen = false,
  defaultView = 'both',
  showToggleButtons = true,
  className = '',
}: SplitScreenLayoutProps) {
  const [view, setView] = useState<'both' | 'workspace' | 'chat'>(defaultView);
  const { t } = useI18n();

  const toggleView = () => {
    if (view === 'both') {
      setView('workspace');
    } else if (view === 'workspace') {
      setView('chat');
    } else {
      setView('both');
    }
  };

  const showWorkspace = view === 'both' || view === 'workspace';
  const showChat = view === 'both' || view === 'chat';

  return (
    <div
      className={clsx(
        'flex flex-col h-screen bg-gray-50',
        fullscreen && 'fixed inset-0 z-50',
        className
      )}
    >
      {/* 顶部导航栏 */}
      <header className="flex-shrink-0 bg-white border-b border-gray-200">
        {header}
      </header>

      {/* 视图切换按钮 - 仅在移动端显示 */}
      {showToggleButtons && (
        <div className="lg:hidden flex items-center justify-center gap-2 p-2 bg-white border-b border-gray-200">
          <button
            onClick={() => setView('workspace')}
            className={clsx(
              'flex-1 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
              view === 'workspace' || view === 'both'
                ? 'bg-black text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            )}
            aria-label={t('ui.showWorkspace')}
          >
            {t('studio.header.nav.workspace')}
          </button>
          <button
            onClick={() => setView('chat')}
            className={clsx(
              'flex-1 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
              view === 'chat' || view === 'both'
                ? 'bg-black text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            )}
            aria-label={t('ui.showChat')}
          >
            {t('studio.layout.chat')}
          </button>
        </div>
      )}

      {/* 主内容区 - 左右分栏 */}
      <div className="flex flex-1 overflow-hidden relative">
        {/* 左侧工作区 */}
        {showWorkspace && (
          <aside
            className={clsx(
              'relative h-full min-w-0 flex-shrink-0 border-r border-gray-200 bg-white transition-all duration-300',
              // 大屏: 60%
              'lg:w-[60%]',
              // 中屏: 50%
              'md:w-[50%]',
              // 小屏: 全宽
              'w-full'
            )}
            role="region"
            aria-label={t('studio.header.nav.workspace')}
          >
            {workspace}

            {/* 桌面端折叠按钮 */}
            {view === 'both' && (
              <button
                onClick={() => setView('chat')}
                className="hidden lg:flex absolute top-4 right-4 items-center gap-1 px-2 py-1 bg-white border border-gray-200 rounded-lg shadow-sm hover:bg-gray-50 text-xs"
                aria-label={t('ui.collapseWorkspace')}
              >
                <PanelLeftClose className="w-3 h-3" />
                {t('studio.collapse')}
              </button>
            )}
          </aside>
        )}

        {/* 右侧聊天区 */}
        {showChat && (
          <main
            className={clsx(
              'relative h-full min-w-0 flex-shrink-0 bg-gray-50 transition-all duration-300',
              // 大屏: 40%
              'lg:w-[40%]',
              // 中屏: 50%
              'md:w-[50%]',
              // 小屏: 全宽
              'w-full'
            )}
            role="region"
            aria-label={t('ui.chatRegion')}
          >
            {chat}

            {/* 桌面端展开按钮 */}
            {view === 'chat' && (
              <button
                onClick={() => setView('both')}
                className="hidden lg:flex absolute top-4 left-4 items-center gap-1 px-2 py-1 bg-white border border-gray-200 rounded-lg shadow-sm hover:bg-gray-50 text-xs"
                aria-label={t('ui.expandWorkspace')}
              >
                <ChevronLeft className="w-3 h-3" />
                {t('ui.expandWorkspace')}
              </button>
            )}

            {/* 桌面端折叠按钮 */}
            {view === 'both' && (
              <button
                onClick={() => setView('workspace')}
                className="hidden lg:flex absolute top-4 left-4 items-center gap-1 px-2 py-1 bg-white border border-gray-200 rounded-lg shadow-sm hover:bg-gray-50 text-xs"
                aria-label={t('ui.collapseChat')}
              >
                <PanelRightClose className="w-3 h-3" />
                {t('studio.collapse')}
              </button>
            )}
          </main>
        )}
      </div>
    </div>
  );
}

/**
 * 分屏布局的预设配置
 */
export const SplitScreenPresets = {
  /** 默认 IDE 布局 (60/40) */
  default: {
    defaultView: 'both' as const,
    showToggleButtons: true,
  },

  /** 专注工作区 */
  workspaceFocus: {
    defaultView: 'workspace' as const,
    showToggleButtons: true,
  },

  /** 专注对话 */
  chatFocus: {
    defaultView: 'chat' as const,
    showToggleButtons: true,
  },

  /** 仅显示工作区 (无切换按钮) */
  workspaceOnly: {
    defaultView: 'workspace' as const,
    showToggleButtons: false,
  },
};
