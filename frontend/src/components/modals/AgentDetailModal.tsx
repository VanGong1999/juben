/**
 * Agent 详情弹窗组件
 */

import { useUIStore } from '@/store/uiStore';
import { useAgentStore } from '@/store/agentStore';
import { X, Copy, Check, Sparkles, Zap } from 'lucide-react';
import { useState } from 'react';
import { useI18n } from '@/i18n';

export default function AgentDetailModal() {
  const { agentDetailModalOpen, setAgentDetailModalOpen, selectedAgentId } = useUIStore();
  const { agents, setActiveAgent } = useAgentStore();
  const [copied, setCopied] = useState(false);
  const { t } = useI18n();

  const agent = agents.find((a) => a.id === selectedAgentId);

  if (!agentDetailModalOpen || !agent) return null;

  const handleCopyExample = async () => {
    await navigator.clipboard.writeText(agent.inputExample);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <>
      {/* 遮罩 */}
      <div
        className="fixed inset-0 bg-black/50 z-50 animate-fade-in"
        onClick={() => setAgentDetailModalOpen(false)}
      />

      {/* 弹窗 */}
      <div className="fixed inset-0 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl animate-scale-in max-h-[90vh] overflow-y-auto">
          {/* 头部 */}
          <div className="flex items-start justify-between px-6 py-4 border-b border-gray-200">
            <div className="flex items-center gap-4">
              <div className="text-4xl">{agent.icon}</div>
              <div>
                <h2 className="text-xl font-semibold text-gray-900">{agent.displayName}</h2>
                <p className="text-sm text-gray-500">{agent.name}</p>
              </div>
            </div>
            <button
              onClick={() => setAgentDetailModalOpen(false)}
              className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* 内容 */}
          <div className="p-6 space-y-6">
            {/* 描述 */}
            <div>
              <h3 className="text-sm font-semibold text-gray-900 mb-2">{t('ui.description')}</h3>
              <p className="text-gray-700">{agent.description}</p>
            </div>

            {/* 特性 */}
            <div>
              <h3 className="text-sm font-semibold text-gray-900 mb-3">{t('studio.header.agent.features')}</h3>
              <div className="flex flex-wrap gap-2">
                {agent.features.map((feature, index) => (
                  <span
                    key={index}
                    className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-full text-sm"
                  >
                    {feature}
                  </span>
                ))}
              </div>
            </div>

            {/* 能力 */}
            <div>
              <h3 className="text-sm font-semibold text-gray-900 mb-3">{t('ui.coreCapabilities')}</h3>
              <ul className="space-y-2">
                {agent.capabilities.map((capability, index) => (
                  <li key={index} className="flex items-start gap-2 text-sm text-gray-700">
                    <Sparkles className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
                    <span>{capability}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* 配置 */}
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="text-xs text-gray-500 mb-1">{t('ui.model')}</div>
                <div className="font-medium text-gray-900">{agent.model}</div>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="text-xs text-gray-500 mb-1">{t('ui.status')}</div>
                <div className="flex items-center gap-2">
                  <div
                    className={`w-2 h-2 rounded-full ${
                      agent.status === 'active' ? 'bg-green-500' : 'bg-yellow-500'
                    }`}
                  />
                  <span className="font-medium text-gray-900 capitalize">{agent.status}</span>
                </div>
              </div>
            </div>

            {/* 示例 */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-gray-900">{t('ui.inputExample')}</h3>
                <button
                  onClick={handleCopyExample}
                  className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 transition-colors"
                >
                  {copied ? (
                    <>
                      <Check className="w-3.5 h-3.5" />
                      {t('ui.copied')}
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      {t('studio.copy')}
                    </>
                  )}
                </button>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                <p className="text-sm text-gray-700 italic">&quot;{agent.inputExample}&quot;</p>
              </div>
            </div>

            {/* 输出示例 */}
            <div>
              <h3 className="text-sm font-semibold text-gray-900 mb-3">{t('ui.outputExample')}</h3>
              <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                <p className="text-sm text-gray-700">{agent.outputExample}</p>
              </div>
            </div>
          </div>

          {/* 底部 */}
          <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200">
            <button
              onClick={() => {
                setActiveAgent(agent.id);
                setAgentDetailModalOpen(false);
              }}
              className="flex items-center gap-2 px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 transition-colors"
            >
              <Zap className="w-4 h-4" />
              {t('ui.useAgent')}
            </button>
            <button
              onClick={() => setAgentDetailModalOpen(false)}
              className="px-6 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
            >
              {t('project.close')}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
