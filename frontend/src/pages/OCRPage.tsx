/**
 * OCR 功能页面
 * 完整的 OCR 识别界面
 */

import React, { useState } from 'react';
import { FileText, Sparkles, Info } from 'lucide-react';
import AppShell from '@/components/layout/AppShell';
import { OCRUploader, OCRResult } from '@/components/ocr';
import { useI18n } from '@/i18n';

export default function OCRPage() {
  const { t } = useI18n();
  const [showInfo, setShowInfo] = useState(false);

  const handleUploadComplete = (result: OCRResult) => {
    console.log('OCR 完成:', result);
  };

  const handleError = (error: string) => {
    console.error('OCR 错误:', error);
  };

  return (
    <AppShell
      title={t('toolbox.ocr.title')}
      subtitle={t('toolbox.ocr.subtitle')}
    >
      <div className="px-4 sm:px-8 lg:px-10 py-6 sm:py-8 max-w-6xl mx-auto space-y-6 sm:space-y-8">
        {/* 功能说明开关 */}
        <div className="flex justify-end">
          <button
            onClick={() => setShowInfo(!showInfo)}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-pearl-soft transition-colors text-sm text-ink-muted"
          >
            <Info className="w-4 h-4" />
            {t('toolbox.ocr.info')}
          </button>
        </div>

        {/* 功能说明 */}
        {showInfo && (
          <div className="glass-panel p-4 sm:p-5">
            <h3 className="font-display font-semibold text-ink mb-2">{t('toolbox.ocr.info')}</h3>
            <ul className="space-y-1 text-sm text-ink-muted">
              <li>• {t('toolbox.ocr.supportsMixed')}</li>
              <li>• {t('toolbox.ocr.supportsTable')}</li>
              <li>• {t('toolbox.ocr.supportsFormula')}</li>
              <li>• {t('toolbox.ocr.formats')}</li>
              <li>• {t('toolbox.ocr.gpu')}</li>
            </ul>
          </div>
        )}

        {/* OCR 上传组件 */}
        <OCRUploader
          onUploadComplete={handleUploadComplete}
          onError={handleError}
        />

        {/* 功能特性 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="glass-panel p-6">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-atelier-teal-soft rounded-lg">
                <Sparkles className="w-5 h-5 text-atelier-teal" />
              </div>
              <h3 className="font-semibold text-ink">{t('toolbox.ocr.highPrecision')}</h3>
            </div>
            <p className="text-sm text-ink-muted">
              {t('toolbox.ocr.highPrecisionDesc')}
            </p>
          </div>

          <div className="glass-panel p-6">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-atelier-gold-soft rounded-lg">
                <FileText className="w-5 h-5 text-atelier-gold" />
              </div>
              <h3 className="font-semibold text-ink">{t('toolbox.ocr.structuredOutput')}</h3>
            </div>
            <p className="text-sm text-ink-muted">
              {t('toolbox.ocr.structuredOutputDesc')}
            </p>
          </div>

          <div className="glass-panel p-6">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-pearl-soft rounded-lg">
                <FileText className="w-5 h-5 text-atelier-slate" />
              </div>
              <h3 className="font-semibold text-ink">{t('toolbox.ocr.localProcess')}</h3>
            </div>
            <p className="text-sm text-ink-muted">
              {t('toolbox.ocr.localProcessDesc')}
            </p>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
