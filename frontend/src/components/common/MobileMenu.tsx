/**
 * 移动端菜单组件
 */

import { useUIStore } from '@/store/uiStore';
import { useAgentStore } from '@/store/agentStore';
import { useAgents } from '@/hooks/useAgents';
import { X, Home, Settings, Info, ScanText, HardDrive } from 'lucide-react';
import { getAgentCategories } from '@/config/agents';
import { Link } from 'react-router-dom';
import { useI18n } from '@/i18n';

export default function MobileMenu() {
  const { mobileMenuOpen, setMobileMenuOpen, setSidebarOpen } = useUIStore();
  const { agents, activeAgent, setActiveAgent } = useAgentStore();
  const { filteredAgents } = useAgents();
  const { t } = useI18n();
  const categories = getAgentCategories().filter((cat) =>
    agents.some((agent) => agent.category === cat.category)
  );

  if (!mobileMenuOpen) return null;

  return (
    <>
      {/* 遮罩 */}
      <div
        className="fixed inset-0 bg-black/50 z-50"
        onClick={() => setMobileMenuOpen(false)}
      />

      {/* 菜单 */}
      <div className="fixed left-0 top-0 bottom-0 w-80 max-w-[85vw] bg-white z-50 flex flex-col animate-slide-up">
        {/* 头部 */}
        <div className="flex items-center justify-between px-4 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold">{t('ui.menu')}</h2>
          <button
            onClick={() => setMobileMenuOpen(false)}
            className="p-2 rounded-lg hover:bg-gray-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 内容 */}
        <div className="flex-1 overflow-y-auto scrollbar p-4">
          {/* 快捷操作 */}
          <div className="space-y-2 mb-6">
            <button
              onClick={() => {
                setMobileMenuOpen(false);
                setSidebarOpen(true);
              }}
              className="w-full flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-gray-100 transition-colors"
            >
              <Home className="w-5 h-5 text-gray-600" />
              <span className="font-medium text-gray-900">{t('ui.agentList')}</span>
            </button>
            <Link
              to="/ocr"
              onClick={() => setMobileMenuOpen(false)}
              className="w-full flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-gray-100 transition-colors"
            >
              <ScanText className="w-5 h-5 text-gray-600" />
              <span className="font-medium text-gray-900">{t('studio.header.nav.ocr')}</span>
            </Link>
            <Link
              to="/files"
              onClick={() => setMobileMenuOpen(false)}
              className="w-full flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-gray-100 transition-colors"
            >
              <HardDrive className="w-5 h-5 text-gray-600" />
              <span className="font-medium text-gray-900">{t('studio.header.nav.files')}</span>
            </Link>
            <button
              className="w-full flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-gray-100 transition-colors"
            >
              <Settings className="w-5 h-5 text-gray-600" />
              <span className="font-medium text-gray-900">{t('nav.settings')}</span>
            </button>
            <button
              className="w-full flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-gray-100 transition-colors"
            >
              <Info className="w-5 h-5 text-gray-600" />
              <span className="font-medium text-gray-900">{t('ui.about')}</span>
            </button>
          </div>

          {/* Agent 分类 */}
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-3 px-2">Agents</h3>
            <div className="space-y-1">
              {categories.map((cat) => (
                <div key={cat.category}>
                  <div className="flex items-center gap-2 px-2 py-2 text-sm text-gray-700">
                    <span>{cat.icon}</span>
                    <span>{cat.name}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 快速 Agent 切换 */}
          <div>
            <h3 className="text-sm font-semibold text-gray-900 mb-3 px-2">{t('ui.quickSwitch')}</h3>
            <div className="space-y-1">
              {filteredAgents.slice(0, 5).map((agent) => (
                <button
                  key={agent.id}
                  onClick={() => {
                    setActiveAgent(agent.id);
                    setMobileMenuOpen(false);
                  }}
                  className={`w-full flex items-center gap-3 px-4 py-2 rounded-lg transition-colors text-left ${
                    activeAgent === agent.id
                      ? 'bg-black text-white'
                      : 'hover:bg-gray-100'
                  }`}
                >
                  <span className="text-xl">{agent.icon}</span>
                  <div className="flex-1 min-w-0">
                    <div className={`font-medium text-sm truncate ${activeAgent === agent.id ? 'text-white' : 'text-gray-900'}`}>
                      {agent.displayName}
                    </div>
                    <div className={`text-xs truncate ${activeAgent === agent.id ? 'text-gray-300' : 'text-gray-500'}`}>
                      {agent.description}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
