/**
 * 全局搜索组件
 * 支持搜索 Agents、项目、文件、消息等
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Search, X, FileText, MessageSquare, FolderOpen, User, Clock } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAgentStore } from '@/store/agentStore';
import { useProjectStore } from '@/store/projectStore';
import { useChatStore } from '@/store/chatStore';
import { useI18n } from '@/i18n';

interface SearchResult {
  id: string;
  type: 'agent' | 'project' | 'message' | 'file';
  title: string;
  description?: string;
  icon: React.ReactNode;
  route: string;
  timestamp?: string;
}

interface GlobalSearchProps {
  isOpen: boolean;
  onClose: () => void;
}

export const GlobalSearch: React.FC<GlobalSearchProps> = ({ isOpen, onClose }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const { agents } = useAgentStore();
  const { projects } = useProjectStore();
  const { messages } = useChatStore();
  const { t, language } = useI18n();

  // 聚焦输入框
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  // 执行搜索
  const performSearch = useCallback(
    (searchQuery: string) => {
      if (!searchQuery.trim()) {
        setResults([]);
        return;
      }

      const q = searchQuery.toLowerCase();
      const searchResults: SearchResult[] = [];

      // 搜索 Agents
      agents.forEach((agent) => {
        if (
          agent.name.toLowerCase().includes(q) ||
          agent.displayName.toLowerCase().includes(q) ||
          agent.description.toLowerCase().includes(q)
        ) {
          searchResults.push({
            id: `agent-${agent.id}`,
            type: 'agent',
            title: agent.displayName,
            description: agent.description,
            icon: <span className="text-xl">{agent.icon}</span>,
            route: `/studio?agent=${agent.id}`,
          });
        }
      });

      // 搜索项目
      Object.values(projects).forEach((project) => {
        if (
          project.name.toLowerCase().includes(q) ||
          project.description?.toLowerCase().includes(q)
        ) {
          searchResults.push({
            id: `project-${project.id}`,
            type: 'project',
            title: project.name,
            description: project.description,
            icon: <FolderOpen className="w-5 h-5" />,
            route: `/projects?id=${project.id}`,
            timestamp: project.updated_at,
          });
        }
      });

      // 搜索消息
      messages.forEach((message) => {
        if (
          message.content.toLowerCase().includes(q) ||
          message.metadata?.agent?.toLowerCase().includes(q)
        ) {
          searchResults.push({
            id: `message-${message.id}`,
            type: 'message',
            title:
              message.content.substring(0, 50) +
              (message.content.length > 50 ? '...' : ''),
            description: message.agentName || t('ui.globalSearch.systemMessage'),
            icon: <MessageSquare className="w-5 h-5" />,
            route: `/studio#message-${message.id}`,
            timestamp: message.timestamp,
          });
        }
      });

      // 限制结果数量
      setResults(searchResults.slice(0, 10));
      setSelectedIndex(0);
    },
    [agents, projects, messages]
  );

  // 防抖搜索
  useEffect(() => {
    const timer = setTimeout(() => {
      performSearch(query);
    }, 300);

    return () => clearTimeout(timer);
  }, [query, performSearch]);

  // 处理键盘导航
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && results.length > 0) {
      e.preventDefault();
      handleSelectResult(results[selectedIndex]);
    } else if (e.key === 'Escape') {
      onClose();
    }
  };

  // 选择搜索结果
  const handleSelectResult = (result: SearchResult) => {
    navigate(result.route);
    onClose();
    setQuery('');
    setResults([]);
  };

  // 获取类型标签
  const getTypeLabel = (type: SearchResult['type']) => {
    const labels = {
      agent: 'Agent',
      project: t('ui.globalSearch.type.project'),
      message: t('ui.globalSearch.type.message'),
      file: t('ui.globalSearch.type.file'),
    };
    return labels[type];
  };

  // 获取类型颜色
  const getTypeColor = (type: SearchResult['type']) => {
    const colors = {
      agent: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
      project: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
      message: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
      file: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
    };
    return colors[type];
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-24 px-4">
      {/* 背景遮罩 */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* 搜索框 */}
      <div className="relative w-full max-w-2xl bg-white dark:bg-gray-800 rounded-xl shadow-2xl overflow-hidden">
        {/* 搜索输入 */}
        <div className="flex items-center gap-3 px-4 py-4 border-b border-gray-200 dark:border-gray-700">
          <Search className="w-5 h-5 text-gray-400" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={t('ui.globalSearch.placeholder')}
            className="flex-1 bg-transparent border-none focus:outline-none text-gray-900 dark:text-white placeholder-gray-400"
          />
          {query && (
            <button
              onClick={() => {
                setQuery('');
                setResults([]);
                inputRef.current?.focus();
              }}
              className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              <X className="w-4 h-4 text-gray-400" />
            </button>
          )}
          <div className="flex items-center gap-1 text-xs text-gray-400">
            <kbd className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded">
              ↑↓
            </kbd>
            <span>{t('ui.globalSearch.navigate')}</span>
            <kbd className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded">
              Enter
            </kbd>
            <span>{t('ui.globalSearch.select')}</span>
            <kbd className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded">
              Esc
            </kbd>
            <span>{t('project.close')}</span>
          </div>
        </div>

        {/* 搜索结果 */}
        <div className="max-h-96 overflow-y-auto">
          {query && results.length === 0 && (
            <div className="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
              <Search className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>{t('ui.globalSearch.noResults')}</p>
              <p className="text-sm mt-1">{t('ui.globalSearch.tryOther')}</p>
            </div>
          )}

          {!query && (
            <div className="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
              <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>{t('ui.globalSearch.startTyping')}</p>
              <p className="text-sm mt-1">{t('ui.globalSearch.scope')}</p>
            </div>
          )}

          {results.length > 0 && (
            <div className="py-2">
              {results.map((result, index) => (
                <button
                  key={result.id}
                  onClick={() => handleSelectResult(result)}
                  className={`w-full flex items-start gap-3 px-4 py-3 transition-colors ${
                    index === selectedIndex
                      ? 'bg-blue-50 dark:bg-blue-900/30'
                      : 'hover:bg-gray-50 dark:hover:bg-gray-700/50'
                  }`}
                >
                  {/* 图标 */}
                  <div className="flex-shrink-0 text-gray-400">
                    {result.icon}
                  </div>

                  {/* 内容 */}
                  <div className="flex-1 min-w-0 text-left">
                    <div className="flex items-center gap-2">
                      <h4 className="font-medium text-gray-900 dark:text-white truncate">
                        {result.title}
                      </h4>
                      <span
                        className={`px-1.5 py-0.5 text-xs rounded ${getTypeColor(result.type)}`}
                      >
                        {getTypeLabel(result.type)}
                      </span>
                    </div>
                    {result.description && (
                      <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5 truncate">
                        {result.description}
                      </p>
                    )}
                    {result.timestamp && (
                      <div className="flex items-center gap-1 mt-1 text-xs text-gray-400">
                        <Clock className="w-3 h-3" />
                        <span>{new Date(result.timestamp).toLocaleString(language === 'zh' ? 'zh-CN' : 'en-US')}</span>
                      </div>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* 底部提示 */}
        {results.length > 0 && (
          <div className="px-4 py-2 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {t('ui.foundResults', { count: results.length })}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default GlobalSearch;
