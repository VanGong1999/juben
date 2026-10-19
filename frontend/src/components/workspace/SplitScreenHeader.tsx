/**
 * 分屏布局的顶部导航栏
 * 包含项目标题、Agent 选择器、页面导航链接和工具按钮
 * 🆕 整合了 Header.tsx 中的完整导航功能
 */

import { useAgentStore } from '@/store/agentStore';
import { useUIStore } from '@/store/uiStore';
import { useAuthStore } from '@/store/authStore';
import { useChat } from '@/hooks/useChat';
import { useAgents } from '@/hooks/useAgents';
import AgentSelector from './AgentSelector';
import { Settings, HelpCircle, Github, Menu, PanelLeftOpen, PanelLeftClose, MessageSquare, Search, Wrench, FolderOpen, ScanText, HardDrive, Network, ClipboardCheck, User, LogOut, BarChart3, Activity, Sparkles, ThumbsUp, GitCompare, Database, Coins, Shield, BookOpen, Rocket, Workflow, FileText, Square, Info } from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { LINKS } from '@/config/links';
import { useState } from 'react';
import { useNotificationStore } from '@/store/notificationStore';
import { useI18n } from '@/i18n';

interface SplitScreenHeaderProps {
  /** 项目名称 */
  projectName?: string;
  /** 帮助按钮点击 */
  onHelpClick?: () => void;
}

export default function SplitScreenHeader({
  projectName = '剧本创作 Agent 平台',
  onHelpClick,
}: SplitScreenHeaderProps) {
  const { t } = useI18n();
  const { activeAgent, setActiveAgent } = useAgentStore();
  const { setSettingsModalOpen, sidebarOpen, sidebarCollapsed, toggleSidebarCollapsed, setSidebarOpen, setSearchOpen } = useUIStore();
  const { user, logout, isAdmin } = useAuthStore();
  const { isStreaming, stopStreaming } = useChat();
  const { activeAgentData } = useAgents();
  const { success } = useNotificationStore();
  const navigate = useNavigate();
  const location = useLocation();
  const [showAgentInfo, setShowAgentInfo] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);

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

  const handleAgentChange = (agentId: string) => {
    setActiveAgent(agentId);
  };

  const handleSettingsClick = () => {
    setSettingsModalOpen(true);
  };

  const handleLogout = async () => {
    await logout();
    success(t('studio.toast.logout'), t('studio.toast.logoutHint'));
    navigate('/login');
  };

  return (
    <div className="flex flex-col">
      {/* 第一行：Logo、导航链接、Agent选择器、用户菜单 */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-gray-200">
        {/* 左侧：Logo 和导航链接 */}
        <div className="flex items-center gap-4 flex-1 min-w-0">
          {/* Logo */}
          <div className="flex items-center gap-2 group cursor-pointer flex-shrink-0">
            <div className="w-8 h-8 bg-black rounded-lg flex items-center justify-center group-hover:shadow-lg transition-shadow">
              <span className="text-white text-sm font-bold">剧</span>
            </div>
            <div className="hidden sm:block">
              <h1 className="text-lg font-semibold group-hover:underline-animated">{projectName}</h1>
              <p className="text-xs text-gray-500">{t('studio.header.tagline')}</p>
            </div>
          </div>

          {/* 页面导航按钮 */}
          <nav className="hidden lg:flex items-center gap-1 ml-4 overflow-x-auto flex-1 min-w-0">
            <Link
              to="/workspace"
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
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
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
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
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
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
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
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
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
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
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
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
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
                isGraphPage
                  ? 'bg-black text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              <Network className="w-4 h-4" />
              {t('studio.header.nav.graph')}
            </Link>
            <Link
              to="/knowledge"
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
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
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
                isWorkflowPage
                  ? 'bg-black text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              <Activity className="w-4 h-4" />
              {t('studio.header.nav.workflow')}
            </Link>
            <Link
              to="/notes"
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
                isNotesPage
                  ? 'bg-black text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              <FileText className="w-4 h-4" />
              {t('studio.header.nav.notes')}
            </Link>
          </nav>

          {/* Agent 选择器 */}
          <div className="hidden md:flex items-center gap-2 flex-shrink-0 ml-4">
            <div className="h-6 w-px bg-gray-200" />
            <AgentSelector
              value={activeAgent}
              onChange={handleAgentChange}
            />
          </div>
        </div>

        {/* 右侧：工具按钮和用户菜单 */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {/* 全局搜索按钮 */}
          <button
            onClick={() => {
              setShowUserMenu(false);
              setSearchOpen(true);
            }}
            className="hidden sm:flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
          >
            <Search className="w-4 h-4" />
            <span className="hidden md:inline">{t('studio.header.search')}</span>
            <kbd className="hidden lg:inline-flex items-center px-1.5 py-0.5 bg-gray-200 rounded text-xs">
              ⌘K
            </kbd>
          </button>

          {/* 停止流式响应按钮 */}
          {(isChatPage || isWorkspacePage) && isStreaming && (
            <button
              onClick={stopStreaming}
              className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-all animate-pulse-slow"
            >
              <Square className="w-4 h-4" />
              <span className="hidden sm:inline">{t('studio.header.stopGenerate')}</span>
            </button>
          )}

          {/* GitHub 链接 */}
          {LINKS.github && (
            <a
              href={LINKS.github}
              target="_blank"
              rel="noopener noreferrer"
              className="p-2 rounded-lg hover:bg-gray-100 text-gray-600 transition-colors"
              title="GitHub"
            >
              <Github className="w-5 h-5" />
            </a>
          )}

          {/* 帮助按钮 */}
          <button
            onClick={onHelpClick}
            className="p-2 rounded-lg hover:bg-gray-100 text-gray-600 transition-colors"
            title={t('studio.help')}
          >
            <HelpCircle className="w-5 h-5" />
          </button>

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
                  <p className="text-sm font-medium text-gray-900">
                    {user?.displayName || user?.username || t('studio.header.role.user')}
                  </p>
                  <p className="text-xs text-gray-500">
                    {user?.role === 'admin' ? t('studio.header.role.admin') : user?.role === 'user' ? t('studio.header.role.user') : t('studio.header.role.guest')}
                  </p>
                </div>
              </div>
            </button>

            {/* 用户下拉菜单 */}
            {showUserMenu && (
              <div className="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-xl border border-gray-200 py-2 z-50 animate-fade-in">
                <div className="px-4 py-2 border-b border-gray-200">
                  <p className="text-sm font-medium text-gray-900">
                    {user?.displayName || user?.username}
                  </p>
                  <p className="text-xs text-gray-500">
                    {user?.email}
                  </p>
                </div>

                <div className="py-2">
                  <Link
                    to="/statistics"
                    className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    onClick={() => setShowUserMenu(false)}
                  >
                    <BarChart3 className="w-4 h-4" />
                    {t('studio.header.nav.statistics')}
                  </Link>
                  {isAdmin() && (
                    <Link
                      to="/admin"
                      className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                      onClick={() => setShowUserMenu(false)}
                    >
                      <Settings className="w-4 h-4" />
                      {t('studio.header.nav.admin')}
                    </Link>
                  )}
                </div>

                <div className="border-t border-gray-200 pt-2">
                  <button
                    onClick={handleLogout}
                    className="flex items-center gap-2 w-full px-4 py-2 text-sm text-red-600 hover:bg-gray-100"
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
            onClick={handleSettingsClick}
            className="p-2 rounded-lg hover:bg-gray-100 text-gray-600 transition-colors"
            title={t('nav.settings')}
          >
            <Settings className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* 第二行：当前 Agent 信息（仅在聊天页面显示） */}
      {isChatPage && activeAgentData && (
        <div className="px-6 py-2 bg-gray-50 border-b border-gray-200">
          <div
            className="flex items-center gap-2 px-3 py-1.5 bg-white rounded-lg hover:bg-gray-100 transition-all cursor-pointer relative"
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
        </div>
      )}
    </div>
  );
}
