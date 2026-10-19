/**
 * 帮助弹窗 - 快速指引
 */

import { X, Sparkles, Layers, FileText, MessageSquare } from 'lucide-react';
import { useI18n } from '@/i18n';

interface HelpModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function HelpModal({ isOpen, onClose }: HelpModalProps) {
  const { t } = useI18n();
  if (!isOpen) return null;

  return (
    <>
      <div
        className="fixed inset-0 bg-black/50 z-50 animate-fade-in"
        onClick={onClose}
      />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="w-full max-w-lg bg-white rounded-2xl shadow-xl overflow-hidden animate-scale-in">
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-gray-700" />
              <h2 className="text-lg font-semibold text-gray-900">{t('ui.quickStart')}</h2>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-gray-100"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="p-6 space-y-4 text-sm text-gray-700">
            <div className="flex items-start gap-3">
              <MessageSquare className="w-5 h-5 text-gray-500" />
              <div>
                <div className="font-medium text-gray-900">{t('ui.help.selectAgentTitle')}</div>
                <div>{t('ui.help.selectAgentDesc')}</div>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <FileText className="w-5 h-5 text-gray-500" />
              <div>
                <div className="font-medium text-gray-900">{t('ui.help.viewResultTitle')}</div>
                <div>{t('ui.help.viewResultDesc')}</div>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Layers className="w-5 h-5 text-gray-500" />
              <div>
                <div className="font-medium text-gray-900">{t('ui.help.notesTitle')}</div>
                <div>{t('ui.help.notesDesc')}</div>
              </div>
            </div>
          </div>

          <div className="px-6 py-4 bg-gray-50 text-xs text-gray-500">
            {t('ui.help.tip')}
          </div>
        </div>
      </div>
    </>
  );
}
