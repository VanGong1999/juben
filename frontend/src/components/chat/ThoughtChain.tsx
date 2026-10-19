/**
 * 思考链组件
 */

import { useState } from 'react';
import { ChevronDown, ChevronRight, Brain } from 'lucide-react';
import type { Thought } from '@/types';
import { useI18n } from '@/i18n';

interface ThoughtChainProps {
  thoughts: Thought[];
}

export default function ThoughtChain({ thoughts }: ThoughtChainProps) {
  const { t } = useI18n();
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="mb-3 border border-gray-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-3 py-2 text-sm bg-gray-50 hover:bg-gray-100 transition-colors"
      >
        {expanded ? (
          <ChevronDown className="w-4 h-4 text-gray-500" />
        ) : (
          <ChevronRight className="w-4 h-4 text-gray-500" />
        )}
        <Brain className="w-4 h-4 text-gray-600" />
        <span className="font-medium text-gray-700">{t('chatGraph.thoughtChain.title')}</span>
        <span className="text-xs text-gray-400">{t('chatGraph.thoughtChain.steps', { count: thoughts.length })}</span>
      </button>

      {expanded && (
        <div className="p-3 space-y-2 bg-gray-50 border-t border-gray-200">
          {thoughts.map((thought, index) => (
            <div key={index} className="flex gap-3 text-sm">
              <span className="flex-shrink-0 w-5 h-5 rounded-full bg-black text-white text-xs flex items-center justify-center">
                {thought.step}
              </span>
              <p className="text-gray-700 flex-1">{thought.content}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
