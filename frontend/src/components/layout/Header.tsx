/**
 * Header 组件 - 增强版
 * 显示当前Agent信息和更多控制
 */

import { useUIStore } from '@/store/uiStore';
import { useChat } from '@/hooks/useChat';
import { useAgents } from '@/hooks/useAgents';
import { useAuthStore } from '@/store/authStore';
import { Menu, Settings, Square, PanelLeftOpen, PanelLeftClose, Info, MessageSquare, Search, Wrench, FolderOpen, ScanText, HardDrive, Network, ClipboardCheck, User, LogOut, BarChart3, Activity, Sparkles, ThumbsUp, GitCompare, Database, Coins, Shield, BookOpen, Rocket, Workflow, FileText } from 'lucide-react';
import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useNotificationStore } from '@/store/notificationStore';
import { useI18n } from '@/i18n';

export default function Header() {
  const { toggleMobileMenu, setSettingsModalOpen, setSidebarOpen, sidebarOpen, sidebarCollapsed, toggleSidebarCollapsed, setSearchOpen } = useUIStore();
  const { isStreaming, stopStreaming } = useChat();
  const { activeAgentData } = useAgents();
  const { user, logout, isAdmin } = useAuthStore();
  const { success } = useNotificationStore();
  const { t } = useI18n();
  const navigate = useNavigate();
  const [showAgentInfo, setShowAgentInfo] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const location = useLocation();

  // 判断当前页面
  const isChatPage = location.pathname === '/chat' || location.pathname === '/';
  const isWorkspacePage = location.pathname === '/workspace';
  const isBaiduPage = location.pathname === '/baidu';
  const isToolsPage = location.pathname === '/tools';
  const isProjectsPage = location.pathname === '/projects';
  const isOCRPage = location.pathname === '/ocr';
  const isFilesPage = location.pathname === '/files';
  const isGraphPage = location.pathname === '/graph';
  const isGraphReviewPage = location.pathname === '/graph/review';
  const isKnowledgePage = location.pathname === '/knowledge';
  const isWorkflowPage = location.pathname === '/workflow';
  const isStatisticsPage = location.pathname === '/statistics';
  const isTokensPage = location.pathname === '/tokens';
  const isEvolutionPage = location.pathname === '/evolution';
  const isFeedbackPage = location.pathname === '/feedback';
  const isABTestPage = location.pathname === '/abtest';
  const isAdminPage = location.pathname === '/admin';
  const isMemorySettingsPage = location.pathname === '/memory-settings';
  const isMemoryManagementPage = location.pathname === '/memory-management';
  const isNotesPage = location.pathname === '/notes';
  const isQualityPage = location.pathname === '/quality';
  const isNovelScreeningPage = location.pathname === '/novel-screening';
  const isReleasePage = location.pathname === '/release';
  const isPipelinesPage = location.pathname === '/pipelines';

  const handleLogout = async () => {
    await logout();
    success(t('studio.toast.logout'), t('studio.toast.logoutHint'));
    navigate('/login');
  };

  return (
    <header className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-white animate-slide-down">
      {/* 左侧 */}
      <div className="flex items-center gap-4">
        {/* 移动端菜单按钮 */}
        <button
          onClick={toggleMobileMenu}
          className="p-2 rounded-lg hover:bg-gray-100 lg:hidden hover-scale icon-bounce transition-all"
          aria-label={t('ui.openMenu')}
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* 侧边栏切换按钮 (桌面端) */}
        {sidebarOpen ? (
          <button
            onClick={toggleSidebarCollapsed}
            className="hidden lg:block p-2 rounded-lg hover:bg-gray-100 hover-scale icon-bounce transition-all"
            aria-label={sidebarCollapsed ? t('ui.expandSidebar') : t('ui.collapseSidebar')}
            title={sidebarCollapsed ? t('ui.expandSidebar') : t('ui.collapseSidebar')}
          >
            {sidebarCollapsed ? (
              <PanelLeftOpen className="w-5 h-5" />
            ) : (
              <PanelLeftClose className="w-5 h-5" />
            )}
          </button>
        ) : (
          <button
            onClick={() => setSidebarOpen(true)}
            className="hidden lg:block p-2 rounded-lg hover:bg-gray-100 hover-scale icon-bounce transition-all"
            aria-label={t('ui.openSidebar')}
            title={t('ui.openSidebar')}
          >
            <PanelLeftOpen className="w-5 h-5" />
          </button>
        )}

        {/* Logo */}
        <div className="flex items-center gap-2 group cursor-pointer">
          <div className="w-8 h-8 bg-black rounded-lg flex items-center justify-center group-hover:shadow-lg transition-shadow">
            <span className="text-white text-sm font-bold">剧</span>
          </div>
          <h1 className="text-lg font-semibold hidden sm:block group-hover:underline-animated">{t('main.title')}</h1>
        </div>

        {/* 页面导航按钮 */}
        <nav className="hidden md:flex items-center gap-1 ml-4">
          <Link
            to="/workspace"
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
              isWorkspacePage || isChatPage
                ? 'bg-black text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <MessageSquare className="w-4 h-4" />
            {t('studio.header.nav.workspace')}
          </Link>
          <Link
            to="/baidu"
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
              isBaiduPage
                ? 'bg-black text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <Search className="w-4 h-4" />
            {t('studio.header.nav.baidu')}
          </Link>
          <Link
            to="/tools"
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
              isToolsPage
                ? 'bg-black text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <Wrench className="w-4 h-4" />
            {t('studio.header.nav.tools')}
          </Link>
          <Link
            to="/projects"
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
              isProjectsPage
                ? 'bg-black text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <FolderOpen className="w-4 h-4" />
            {t('studio.header.nav.projects')}
          </Link>
          <Link
            to="/ocr"
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
              isOCRPage
                ? 'bg-black text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <ScanText className="w-4 h-4" />
            {t('studio.header.nav.ocr')}
          </Link>
          <Link
            to="/files"
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
              isFilesPage
                ? 'bg-black text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <HardDrive className="w-4 h-4" />
            {t('studio.header.nav.files')}
          </Link>
          <Link
            to="/graph"
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
              isGraphPage
                ? 'bg-black text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <Network className="w-4 h-4" />
            {t('studio.header.nav.graph')}
          </Link>
          <Link
            to="/graph/review"
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
              isGraphReviewPage
                ? 'bg-black text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <ClipboardCheck className="w-4 h-4" />
            {t('ui.nav.reviewCenter')}
          </Link>
          <Link
            to="/knowledge"
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
              isKnowledgePage
                ? 'bg-black text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <Database className="w-4 h-4" />
            {t('studio.header.nav.knowledge')}
          </Link>
          <Link
            to="/workflow"
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
              isWorkflowPage
                ? 'bg-black text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <Activity className="w-4 h-4" />
            {t('studio.header.nav.workflow')}
          </Link>
          <Link
            to="/statistics"
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
              isStatisticsPage
                ? 'bg-black text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <BarChart3 className="w-4 h-4" />
            {t('studio.header.nav.statistics')}
          </Link>
          <Link
            to="/tokens"
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
              isTokensPage
                ? 'bg-black text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <Coins className="w-4 h-4" />
            {t('ui.nav.tokens')}
          </Link>
          <Link
            to="/memory-management"
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
              isMemoryManagementPage
                ? 'bg-black text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <Database className="w-4 h-4" />
            {t('ui.nav.memory')}
          </Link>
          <Link
            to="/evolution"
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
              isEvolutionPage
                ? 'bg-black text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <Sparkles className="w-4 h-4" />
            {t('ui.nav.evolution')}
          </Link>
          <Link
            to="/feedback"
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
              isFeedbackPage
                ? 'bg-black text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <ThumbsUp className="w-4 h-4" />
            {t('ui.nav.feedback')}
          </Link>
          <Link
            to="/abtest"
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
              isABTestPage
                ? 'bg-black text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <GitCompare className="w-4 h-4" />
            {t('ui.nav.abtest')}
          </Link>
          <Link
            to="/notes"
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
              isNotesPage
                ? 'bg-black text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <FileText className="w-4 h-4" />
            {t('studio.header.nav.notes')}
          </Link>
          <Link
            to="/quality"
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
              isQualityPage
                ? 'bg-black text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <Shield className="w-4 h-4" />
            {t('admin.quality.title')}
          </Link>
          <Link
            to="/novel-screening"
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
              isNovelScreeningPage
                ? 'bg-black text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <BookOpen className="w-4 h-4" />
            {t('ui.nav.novelScreening')}
          </Link>
          <Link
            to="/release"
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
              isReleasePage
                ? 'bg-black text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <Rocket className="w-4 h-4" />
            {t('admin.release.title')}
          </Link>
          <Link
            to="/pipelines"
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
              isPipelinesPage
                ? 'bg-black text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <Workflow className="w-4 h-4" />
            {t('admin.pipeline.title')}
          </Link>
          {isAdmin() && (
            <Link
              to="/admin"
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                isAdminPage
                  ? 'bg-black text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              <Settings className="w-4 h-4" />
              {t('studio.header.nav.admin')}
            </Link>
          )}
        </nav>

        {/* 当前 Agent - 仅在聊天页面显示 */}
        {isChatPage && activeAgentData && (
          <div
            className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-gray-50 rounded-lg hover:bg-gray-100 transition-all hover-scale cursor-pointer relative"
            onClick={() => setShowAgentInfo(!showAgentInfo)}
          >
            <span className="text-lg">{activeAgentData.icon}</span>
            <div className="flex flex-col">
              <span className="text-sm font-medium text-gray-900">{activeAgentData.displayName}</span>
              <span className="text-xs text-gray-500 flex items-center gap-1">
                {activeAgentData.model}
                <Info className="w-3 h-3" />
              </span>
            </div>
            {activeAgentData.status === 'beta' && (
              <span className="text-xs px-1.5 py-0.5 bg-gray-200 text-gray-600 rounded ml-1">Beta</span>
            )}

            {/* Agent 详情悬浮 */}
            {showAgentInfo && (
              <div className="absolute top-full left-0 mt-2 w-72 bg-white rounded-lg shadow-xl border border-gray-200 p-4 z-50 animate-fade-in">
                <div className="flex items-start gap-3">
                  <span className="text-4xl">{activeAgentData.icon}</span>
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900">{activeAgentData.displayName}</h3>
                    <p className="text-sm text-gray-500 mt-1">{activeAgentData.description}</p>
                    <div className="mt-3 space-y-2">
                      <div className="flex items-center gap-2 text-xs text-gray-600">
                        <span className="font-medium">{t('studio.header.agent.category')}:</span>
                        <span className="px-2 py-0.5 bg-gray-100 rounded">{activeAgentData.category}</span>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-gray-600">
                        <span className="font-medium">{t('studio.header.agent.model')}:</span>
                        <span className="px-2 py-0.5 bg-gray-100 rounded">{activeAgentData.model}</span>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-gray-600">
                        <span className="font-medium">{t('studio.header.agent.endpoint')}:</span>
                        <span className="px-2 py-0.5 bg-gray-100 rounded font-mono">{activeAgentData.apiEndpoint}</span>
                      </div>
                    </div>
                    <div className="mt-3">
                      <div className="text-xs font-medium text-gray-600 mb-1">{t('studio.header.agent.features')}:</div>
                      <div className="flex flex-wrap gap-1">
                        {activeAgentData.features.slice(0, 4).map((feature: string) => (
                          <span
                            key={feature}
                            className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded"
                          >
                            {feature}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 右侧 */}
      <div className="flex items-center gap-2">
        {/* 全局搜索按钮 */}
        <button
          onClick={() => {
            setShowUserMenu(false);
            setSearchOpen(true);
          }}
          className="hidden sm:flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 rounded-lg transition-colors"
        >
          <Search className="w-4 h-4" />
          <span>{t('studio.header.search')}</span>
          <kbd className="hidden md:inline-flex items-center px-1.5 py-0.5 bg-gray-200 dark:bg-gray-600 rounded text-xs">
            ⌘K
          </kbd>
        </button>

        {/* 停止流式响应按钮 - 仅在聊天页面显示 */}
        {(isChatPage || isWorkspacePage) && isStreaming && (
          <button
            onClick={stopStreaming}
            className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 hover:shadow-lg transition-all hover-scale animate-pulse-slow"
          >
            <Square className="w-4 h-4" />
            <span className="hidden sm:inline">{t('studio.header.stopGenerate')}</span>
          </button>
        )}

        {/* 用户菜单 */}
        <div className="relative">
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="flex items-center gap-2 p-2 rounded-lg hover:bg-gray-100 transition-all"
          >
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-medium text-sm">
                {user?.displayName?.charAt(0).toUpperCase() || user?.username?.charAt(0).toUpperCase() || 'U'}
              </div>
              <div className="hidden md:block text-left">
                <p className="text-sm font-medium text-gray-900 dark:text-white">
                  {user?.displayName || user?.username || t('studio.header.role.user')}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {user?.role === 'admin' ? t('studio.header.role.admin') : user?.role === 'user' ? t('studio.header.role.user') : t('studio.header.role.guest')}
                </p>
              </div>
            </div>
          </button>

          {/* 用户下拉菜单 */}
          {showUserMenu && (
            <div className="absolute right-0 mt-2 w-56 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 py-2 z-50 animate-fade-in">
              <div className="px-4 py-2 border-b border-gray-200 dark:border-gray-700">
                <p className="text-sm font-medium text-gray-900 dark:text-white">
                  {user?.displayName || user?.username}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {user?.email}
                </p>
              </div>

              <div className="py-2">
                <Link
                  to="/statistics"
                  className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                  onClick={() => setShowUserMenu(false)}
                >
                  <BarChart3 className="w-4 h-4" />
                  {t('studio.header.nav.statistics')}
                </Link>
                {isAdmin() && (
                  <Link
                    to="/admin"
                    className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                    onClick={() => setShowUserMenu(false)}
                  >
                    <Settings className="w-4 h-4" />
                    {t('studio.header.nav.admin')}
                  </Link>
                )}
              </div>

              <div className="border-t border-gray-200 dark:border-gray-700 pt-2">
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-2 w-full px-4 py-2 text-sm text-red-600 hover:bg-gray-100 dark:hover:bg-gray-700"
                >
                  <LogOut className="w-4 h-4" />
                  {t('nav.signOut')}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* 设置按钮 */}
        <button
          onClick={() => setSettingsModalOpen(true)}
          className="p-2 rounded-lg hover:bg-gray-100 hover-scale icon-rotate transition-all"
          aria-label={t('nav.settings')}
        >
          <Settings className="w-5 h-5 text-gray-600" />
        </button>
      </div>
    </header>
  );
}
