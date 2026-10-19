/**
 * Agent 选择器组件
 * 顶部下拉菜单：默认「自动编排」，也可手动指定专家
 */

import { useState, useRef, useEffect } from 'react';
import { ChevronDown, Bot, RotateCcw } from 'lucide-react';
import { clsx } from 'clsx';
import { useAgentStore } from '@/store/agentStore';
import { getAgentById } from '@/config/agents';
import { useI18n } from '@/i18n';

interface AgentSelectorProps {
  /** 当前选中的 Agent ID */
  value: string;
  /** 选择变更回调 */
  onChange: (agentId: string) => void;
  /** 是否禁用 */
  disabled?: boolean;
}

const AUTO_OPTION = {
  id: 'auto',
  displayName: '自动编排',
  description: '不指定专家，由总控按需调用/交接/组合',
  icon: '🧭',
  category: 'orchestration',
};

export default function AgentSelector({
  value,
  onChange,
  disabled = false,
}: AgentSelectorProps) {
  const { t } = useI18n();
  const { agents, returnToConductor } = useAgentStore();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const configFallback = value === 'auto' ? AUTO_OPTION : getAgentById(value);
  const currentAgent =
    value === 'auto'
      ? agents.find((a) => a.id === 'auto') || AUTO_OPTION
      : agents.find((a) => a.id === value) || configFallback;

  const isHandedOff = value !== 'auto' && value !== 'juben_conductor';

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (agentId: string) => {
    onChange(agentId);
    setIsOpen(false);
  };

  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      orchestration: 'bg-teal-100 text-teal-700',
      planning: 'bg-blue-100 text-blue-700',
      creation: 'bg-purple-100 text-purple-700',
      evaluation: 'bg-orange-100 text-orange-700',
      analysis: 'bg-green-100 text-green-700',
      workflow: 'bg-cyan-100 text-cyan-700',
      character: 'bg-pink-100 text-pink-700',
      story: 'bg-indigo-100 text-indigo-700',
      utility: 'bg-gray-100 text-gray-700',
    };
    return colors[category] || 'bg-gray-100 text-gray-700';
  };

  // 列表置顶自动编排，去重 juben_conductor（与 auto 同实现）
  const listAgents = [
    AUTO_OPTION,
    ...agents.filter((a) => a.id !== 'auto' && a.id !== 'juben_conductor'),
  ];

  return (
    <div ref={dropdownRef} className="relative flex items-center gap-1">
      <button
        type="button"
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
        className={clsx(
          'flex items-center gap-2 px-4 py-2 rounded-lg',
          'bg-white border border-gray-200',
          'hover:border-gray-300 hover:shadow-sm',
          'transition-all duration-200',
          disabled && 'opacity-50 cursor-not-allowed'
        )}
      >
        <span className="text-lg">
          {currentAgent?.icon || <Bot className="w-5 h-5 text-blue-600" />}
        </span>
        <span className="font-medium text-gray-900">
          {currentAgent?.displayName || '自动编排'}
        </span>
        <ChevronDown
          className={clsx(
            'w-4 h-4 text-gray-400 transition-transform',
            isOpen && 'transform rotate-180'
          )}
        />
      </button>

      {isHandedOff && (
        <button
          type="button"
          title={t('studio.agentSelector.returnToAuto')}
          disabled={disabled}
          onClick={() => {
            returnToConductor();
            onChange('auto');
          }}
          className="p-2 rounded-lg border border-gray-200 text-gray-600 hover:bg-teal-50 hover:text-teal-700 hover:border-teal-200 transition-colors"
        >
          <RotateCcw className="w-4 h-4" />
        </button>
      )}

      {isOpen && (
        <div className="absolute top-full left-0 mt-2 w-80 bg-white rounded-lg shadow-lg border border-gray-200 z-50">
          <div className="max-h-96 overflow-y-auto py-2">
            {listAgents.map((agent) => (
              <button
                key={agent.id}
                type="button"
                onClick={() => handleSelect(agent.id)}
                className={clsx(
                  'w-full flex items-start gap-3 px-4 py-3',
                  'hover:bg-gray-50 transition-colors',
                  'text-left'
                )}
              >
                <span className="text-2xl flex-shrink-0">{agent.icon}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-900 text-sm">
                      {agent.displayName}
                    </span>
                    {agent.id === value && (
                      <span className="px-1.5 py-0.5 text-xs bg-teal-100 text-teal-700 rounded-full">
                        {t('studio.current')}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5 line-clamp-1">
                    {agent.description}
                  </p>
                  <span
                    className={clsx(
                      'inline-block mt-1 px-2 py-0.5 text-xs rounded',
                      getCategoryColor(agent.category)
                    )}
                  >
                    {agent.category}
                  </span>
                </div>
              </button>
            ))}

            {listAgents.length === 0 && (
              <div className="px-4 py-8 text-center text-gray-400 text-sm">
                {t('studio.agentSelector.noAgents')}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
