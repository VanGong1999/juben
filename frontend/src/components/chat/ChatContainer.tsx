/**
 * 聊天容器组件
 */

import { useEffect, useRef } from 'react';
import { useChat } from '@/hooks/useChat';
import { useSettingsStore } from '@/store/settingsStore';
import { useUIStore } from '@/store/uiStore';
import ChatMessage from './ChatMessage';
import InputArea from './InputArea';
import { Loader2 } from 'lucide-react';
import { useState } from 'react';
import { useAgentStore } from '@/store/agentStore';
import type { Agent } from '@/types';
import { AGENTS_CONFIG } from '@/config/agents';
import { useI18n } from '@/i18n';

export default function ChatContainer() {
  const { messages, isStreaming } = useChat();
  const { autoScroll, showThoughtChain } = useSettingsStore();
  const { thoughtChainExpanded } = useUIStore();
  const { agents } = useAgentStore();
  const { t } = useI18n();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const availableAgents = agents.length > 0 ? agents : AGENTS_CONFIG;

  // 自动滚动到底部
  useEffect(() => {
    if (autoScroll) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, autoScroll]);

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto scrollbar p-6">
        {messages.length === 0 ? (
          <WelcomeState agents={availableAgents} />
        ) : (
          <div className="space-y-6 max-w-4xl mx-auto">
            {messages.map((message) => (
              <ChatMessage
                key={message.id}
                message={message}
                showThoughtChain={showThoughtChain && thoughtChainExpanded}
              />
            ))}

            {/* 流式响应占位 */}
            {isStreaming && (
              <div className="flex items-center gap-2 text-gray-400 text-sm py-4">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>{t('chat.generating')}</span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* 输入区域 */}
      <InputArea />
    </div>
  );
}

/**
 * 欢迎状态 - 展示所有Agents（无分类，一行四个）
 */
function WelcomeState({ agents }: { agents: Agent[] }) {
  const { t } = useI18n();
  return (
    <div className="h-full overflow-y-auto scrollbar p-6">
      <div className="max-w-7xl mx-auto">
        {/* 头部欢迎区域 */}
        <div className="text-center mb-8">
          <div className="w-20 h-20 bg-gradient-to-br from-black to-gray-800 rounded-3xl flex items-center justify-center mb-6 mx-auto shadow-lg">
            <span className="text-4xl text-white font-bold">剧</span>
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-3">
            {t('main.title')}
          </h1>
          <p className="text-gray-600 max-w-3xl mx-auto text-base leading-relaxed">
            {t('main.welcomeBefore')} <span className="font-semibold text-black">{agents.length}</span> {t('main.welcomeAfter')}
          </p>
        </div>

        {/* Agents网格展示 - 一行四个 */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pb-8">
          {agents.map((agent) => (
            <AgentCard key={agent.id} agent={agent} />
          ))}
        </div>

        {/* 底部统计 */}
        <div className="text-center py-6 border-t border-gray-200">
          <p className="text-sm text-gray-500">
            {t('main.countBefore')} <span className="font-semibold text-gray-900">{agents.length}</span> {t('main.countAfter')}
          </p>
        </div>
      </div>
    </div>
  );
}

/**
 * Agent卡片组件 - 详细介绍版
 */
function AgentCard({ agent }: { agent: Agent }) {
  const { sendMessage, setActiveAgent } = useChat();
  const { t } = useI18n();
  const [isHovered, setIsHovered] = useState(false);

  const handleClick = () => {
    // 先设置当前活跃的agent
    setActiveAgent(agent.id);
    // 使用agent的inputExample作为默认消息，并传递agent.id
    const message = agent.inputExample || t('main.useAgent', { name: agent.displayName });
    sendMessage(message, agent.id);
  };

  return (
    <button
      onClick={handleClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className={`p-5 border rounded-2xl text-left transition-all duration-300 h-full flex flex-col ${
        isHovered
          ? 'border-black shadow-2xl scale-[1.03] bg-gray-50'
          : 'border-gray-200 hover:border-gray-400 shadow-md bg-white'
      } ${agent.status === 'beta' ? 'opacity-90' : ''}`}
    >
      {/* 头部：图标、名称和状态 */}
      <div className="flex items-start gap-3 mb-4">
        <div className={`w-14 h-14 rounded-xl flex items-center justify-center flex-shrink-0 transition-all ${
          isHovered ? 'bg-black' : 'bg-gray-900'
        }`}>
          <span className="text-2xl">{agent.icon}</span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className={`font-bold text-base leading-tight ${isHovered ? 'text-black' : 'text-gray-900'}`}>
              {agent.displayName}
            </h3>
            {agent.status === 'beta' && (
              <span className="text-xs px-2 py-0.5 bg-amber-100 text-amber-700 rounded-full flex-shrink-0 font-medium">
                Beta
              </span>
            )}
          </div>
          {/* 分类标签 */}
          <span className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full inline-block">
            {agent.category}
          </span>
        </div>
      </div>

      {/* 描述 */}
      <p className="text-sm text-gray-700 mb-4 line-clamp-3 leading-relaxed flex-1">
        {agent.description}
      </p>

      {/* 详细介绍 - capabilities */}
      {agent.capabilities && agent.capabilities.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-medium text-gray-500 mb-2">{t('main.coreCapabilities')}</p>
          <ul className="space-y-1">
            {agent.capabilities.slice(0, 3).map((capability, idx) => (
              <li key={idx} className="text-xs text-gray-600 flex items-start gap-2">
                <span className="text-green-500 mt-0.5">✓</span>
                <span className="line-clamp-1">{capability}</span>
              </li>
            ))}
            {agent.capabilities.length > 3 && (
              <li className="text-xs text-gray-400 italic">
                {t('main.moreCapabilities', { count: agent.capabilities.length - 3 })}
              </li>
            )}
          </ul>
        </div>
      )}

      {/* 功能标签 */}
      <div className="flex flex-wrap gap-1.5 mb-4">
        {agent.features.slice(0, 4).map((feature) => (
          <span
            key={feature}
            className="text-xs px-2 py-1 bg-gray-100 text-gray-700 rounded-md"
          >
            {feature}
          </span>
        ))}
        {agent.features.length > 4 && (
          <span className="text-xs px-2 py-1 bg-gray-50 text-gray-500 rounded-md">
            +{agent.features.length - 4}
          </span>
        )}
      </div>

      {/* 底部信息栏 */}
      <div className="mt-auto pt-3 border-t border-gray-100">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-1.5 text-gray-500">
            <span className="font-medium">{t('main.model')}</span>
            <span className="font-mono bg-gray-100 px-1.5 py-0.5 rounded">{agent.model}</span>
          </div>
          <span className={`px-2.5 py-1 rounded-full font-medium ${
            agent.status === 'active'
              ? 'bg-green-100 text-green-700'
              : 'bg-amber-100 text-amber-700'
          }`}>
            {agent.status === 'active' ? t('main.available') : t('main.testing')}
          </span>
        </div>
        {/* 点击提示 */}
        {isHovered && (
          <p className="text-xs text-center text-gray-500 mt-2 animate-pulse">
            {t('main.clickToStart')}
          </p>
        )}
      </div>
    </button>
  );
}
