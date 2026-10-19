/**
 * 侧边栏组件 - 增强版
 * 支持折叠/展开，分类展开显示agents
 */

import { useUIStore } from '@/store/uiStore';
import { useAgentStore } from '@/store/agentStore';
import { getAgentCategories, AGENTS_CONFIG } from '@/config/agents';
import type { Agent } from '@/types';
import { X, Search, ChevronDown, ChevronLeft, ChevronRight } from 'lucide-react';
import { useState, useMemo } from 'react';
import { useI18n } from '@/i18n';

export default function Sidebar() {
  const { sidebarOpen, sidebarCollapsed, setSidebarOpen } = useUIStore();
  const { t } = useI18n();
  const { agents: loadedAgents, activeAgent, setActiveAgent, searchQuery, setSearchQuery } = useAgentStore();
  const categories = getAgentCategories();
  const agents = loadedAgents.length > 0 ? loadedAgents : AGENTS_CONFIG;

  const [hoveredAgent, setHoveredAgent] = useState<string | null>(null);
  // 默认展开所有分类，让用户能看到所有agents
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    new Set(['planning', 'creation', 'evaluation', 'analysis', 'workflow', 'character', 'story', 'utility'])
  );

  // 过滤agents（用于搜索）
  const filteredAgentsByCategory = useMemo(() => {
    const result: Record<string, Agent[]> = {};

    // 先按分类分组
    agents.forEach(agent => {
      if (!result[agent.category]) {
        result[agent.category] = [];
      }
      result[agent.category].push(agent);
    });

    // 如果有搜索词，过滤
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      Object.keys(result).forEach(category => {
        result[category] = result[category].filter(agent =>
          agent.displayName.toLowerCase().includes(query) ||
          agent.description.toLowerCase().includes(query) ||
          agent.features.some(f => f.toLowerCase().includes(query))
        );
      });
    }

    return result;
  }, [searchQuery, agents]);

  // 切换类别展开状态
  const toggleCategory = (category: string) => {
    setExpandedCategories(prev => {
      const newSet = new Set(prev);
      if (newSet.has(category)) {
        newSet.delete(category);
      } else {
        newSet.add(category);
      }
      return newSet;
    });
  };

  // 展开所有类别
  const expandAllCategories = () => {
    setExpandedCategories(new Set(categories.map(c => c.category)));
  };

  // 折叠所有类别
  const collapseAllCategories = () => {
    setExpandedCategories(new Set());
  };

  // 检查是否有搜索结果
  const hasSearchResults = Object.values(filteredAgentsByCategory).some(agents => agents.length > 0);

  // 侧边栏关闭时不渲染任何内容
  if (!sidebarOpen) return null;

  return (
    <>
      {/* 遮罩层 (移动端) */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* 侧边栏 */}
      <aside
        className={`fixed left-0 top-0 h-full bg-white border-r border-gray-200 z-50 flex flex-col animate-slide-left transition-all duration-300 ${
          sidebarCollapsed ? 'w-16' : 'w-80'
        }`}
      >
        {/* 头部 */}
        <div className="flex items-center justify-between px-4 py-4 border-b border-gray-200">
          {!sidebarCollapsed && <h2 className="text-lg font-semibold">Agents</h2>}
          <div className="flex items-center gap-1 ml-auto">
            {/* 折叠/展开按钮 */}
            <button
              onClick={() => {
                const { toggleSidebarCollapsed } = useUIStore.getState();
                toggleSidebarCollapsed();
              }}
              className="p-1.5 rounded-lg hover:bg-gray-100 transition-all hover-scale"
              title={sidebarCollapsed ? t('ui.expandSidebar') : t('ui.collapseSidebar')}
            >
              {sidebarCollapsed ? (
                <ChevronRight className="w-4 h-4" />
              ) : (
                <ChevronLeft className="w-4 h-4" />
              )}
            </button>
            {/* 关闭按钮 (移动端) */}
            <button
              onClick={() => setSidebarOpen(false)}
              className="p-1 rounded-lg hover:bg-gray-100 lg:hidden hover-scale icon-rotate"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* 搜索框 */}
        {!sidebarCollapsed && (
          <div className="px-4 py-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder={t('ui.searchAgents')}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:border-black input-focus-effect transition-all"
              />
            </div>
            {/* 展开/折叠所有按钮 */}
            <div className="flex gap-2 mt-2">
              <button
                onClick={expandAllCategories}
                className="flex-1 text-xs px-2 py-1 text-gray-600 bg-gray-100 rounded hover:bg-gray-200 transition-colors"
              >
                {t('ui.expandAll')}
              </button>
              <button
                onClick={collapseAllCategories}
                className="flex-1 text-xs px-2 py-1 text-gray-600 bg-gray-100 rounded hover:bg-gray-200 transition-colors"
              >
                {t('ui.collapseAll')}
              </button>
            </div>
          </div>
        )}

        {/* 分类和Agent列表 */}
        <div className="flex-1 overflow-y-auto scrollbar px-4 py-2">
          {!sidebarCollapsed ? (
            <div className="space-y-1">
              {categories.map((cat) => {
                const categoryAgents = filteredAgentsByCategory[cat.category] || [];
                const isExpanded = expandedCategories.has(cat.category);
                const hasAgents = categoryAgents.length > 0;

                if (!hasAgents && searchQuery) {
                  // 搜索时隐藏没有结果的分类
                  return null;
                }

                return (
                  <div key={cat.category} className="mb-1">
                    {/* 分类按钮 */}
                    <button
                      onClick={() => toggleCategory(cat.category)}
                      className={`w-full flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg transition-all hover-scale ${
                        isExpanded
                          ? 'bg-gray-100 text-gray-900'
                          : 'text-gray-600 hover:bg-gray-50'
                      }`}
                    >
                      <ChevronDown
                        className={`w-4 h-4 transition-transform flex-shrink-0 ${
                          isExpanded ? 'rotate-180' : ''
                        }`}
                      />
                      <span className="text-base">{cat.icon}</span>
                      <span className="flex-1 text-left">{cat.name}</span>
                      <span className={`text-xs flex-shrink-0 ${
                        searchQuery ? 'text-gray-400' : 'text-gray-400'
                      }`}>
                        ({categoryAgents.length})
                      </span>
                    </button>

                    {/* 该分类下的 Agents */}
                    {isExpanded && hasAgents && (
                      <div className="ml-4 mt-1 space-y-1 animate-slide-down">
                        {categoryAgents.map((agent) => (
                          <div
                            key={agent.id}
                            className="relative"
                            onMouseEnter={() => setHoveredAgent(agent.id)}
                            onMouseLeave={() => setHoveredAgent(null)}
                          >
                            <button
                              onClick={() => setActiveAgent(agent.id)}
                              className={`w-full flex items-start gap-2 px-3 py-2 rounded-lg transition-all text-left hover-scale ${
                                activeAgent === agent.id
                                  ? 'bg-gray-900 text-white shadow-md'
                                  : 'hover:bg-gray-50 border border-transparent hover:border-gray-200'
                              }`}
                            >
                              <span className="text-base flex-shrink-0 mt-0.5">{agent.icon}</span>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-1.5">
                                  <span className={`font-medium text-sm truncate ${
                                    activeAgent === agent.id ? 'text-white' : 'text-gray-900'
                                  }`}>
                                    {agent.displayName}
                                  </span>
                                  {agent.status === 'beta' && (
                                    <span className={`text-xs px-1 py-0.5 rounded flex-shrink-0 ${
                                      activeAgent === agent.id
                                        ? 'bg-white/20 text-white'
                                        : 'bg-gray-200 text-gray-600'
                                    }`}>
                                      Beta
                                    </span>
                                  )}
                                </div>
                                <p className={`text-xs truncate mt-0.5 ${
                                  activeAgent === agent.id ? 'text-gray-300' : 'text-gray-500'
                                }`}>
                                  {agent.description}
                                </p>
                              </div>
                            </button>

                            {/* 悬停详情 */}
                            {!searchQuery && hoveredAgent === agent.id && activeAgent !== agent.id && (
                              <div className="absolute left-full top-0 ml-2 w-72 bg-white rounded-lg shadow-xl border border-gray-200 p-3 z-50 animate-fade-in">
                                <div className="flex items-start gap-3">
                                  <span className="text-3xl">{agent.icon}</span>
                                  <div className="flex-1 min-w-0">
                                    <h4 className="font-semibold text-sm text-gray-900">{agent.displayName}</h4>
                                    <p className="text-xs text-gray-500 mt-1 line-clamp-2">{agent.description}</p>
                                    <div className="mt-2 flex flex-wrap gap-1">
                                      {agent.features.slice(0, 4).map((feature) => (
                                        <span
                                          key={feature}
                                          className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded"
                                        >
                                          {feature}
                                        </span>
                                      ))}
                                    </div>
                                    <div className="mt-2 text-xs text-gray-400">
                                      {t('studio.header.agent.model')}: {agent.model}
                                    </div>
                                  </div>
                                </div>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}

              {/* 无搜索结果 */}
              {searchQuery && !hasSearchResults && (
                <div className="text-center py-8 text-gray-400">
                  <p className="text-sm">{t('ui.noMatchAgents')}</p>
                </div>
              )}
            </div>
          ) : (
            /* 折叠状态：显示所有agents的图标 */
            <div className="space-y-2">
              {agents.map((agent) => (
                <button
                  key={agent.id}
                  onClick={() => setActiveAgent(agent.id)}
                  className={`w-full flex justify-center p-2 rounded-lg transition-all hover-scale ${
                    activeAgent === agent.id
                      ? 'bg-gray-900 text-white shadow-md'
                      : 'hover:bg-gray-50'
                  }`}
                  title={agent.displayName}
                >
                  <span className="text-lg">{agent.icon}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* 底部统计 */}
        {!sidebarCollapsed && (
          <div className="px-4 py-3 border-t border-gray-200 text-xs text-gray-500">
            <p>{t('ui.totalAgents', { count: agents.length })}</p>
            {searchQuery && hasSearchResults && (
              <p className="mt-1">{t('ui.foundResults', { count: Object.values(filteredAgentsByCategory).flat().length })}</p>
            )}
          </div>
        )}
      </aside>
    </>
  );
}
