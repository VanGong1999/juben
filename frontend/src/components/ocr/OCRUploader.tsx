/**
 * OCR 文件上传组件
 * 支持拖拽上传、进度显示、结果预览
 */

import React, { useState, useCallback, useEffect, useRef } from 'react';
import { Upload, Download, Copy, Check, X, Loader2 } from 'lucide-react';
import { clsx } from 'clsx';
import { useI18n } from '@/i18n';
import { API_BASE_URL, getAuthHeaderValue } from '@/services/api';
import { getProjects } from '@/services/projectService';
import type { Project } from '@/types';

interface OCRUploaderProps {
  onUploadStart?: () => void;
  onUploadProgress?: (progress: number) => void;
  onUploadComplete?: (result: OCRResult) => void;
  onError?: (error: string) => void;
  className?: string;
}

export interface OCRResult {
  text: string;
  metadata: {
    processing_time: number;
    text_box_count: number;
    table_count: number;
    formula_count: number;
  };
  saved_paths?: Record<string, string>;
}

export type OutputFormat = 'text' | 'markdown' | 'json' | 'structured';

export const OCRUploader: React.FC<OCRUploaderProps> = ({
  onUploadStart,
  onUploadProgress,
  onUploadComplete,
  onError,
  className = '',
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string>('');
  const [isUploading, setIsUploading] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState<OCRResult | null>(null);
  const [outputFormat, setOutputFormat] = useState<OutputFormat>('text');
  const [useStructure, setUseStructure] = useState(false);
  const [copied, setCopied] = useState(false);
  const [events, setEvents] = useState<string[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [savingNote, setSavingNote] = useState(false);
  const [savingFile, setSavingFile] = useState(false);
  const [saveNoteMessage, setSaveNoteMessage] = useState<string>('');
  const [saveFileMessage, setSaveFileMessage] = useState<string>('');

  const fileInputRef = useRef<HTMLInputElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const { t } = useI18n();

  useEffect(() => {
    const loadProjectOptions = async () => {
      try {
        const { projects: list } = await getProjects({ page: 1, page_size: 100 });
        setProjects(list || []);
        const stored = localStorage.getItem('projectId');
        if (stored && (list || []).some((p) => p.id === stored)) {
          setSelectedProjectId(stored);
        }
      } catch {
        setProjects([]);
      }
    };
    loadProjectOptions();
  }, []);

  // 处理文件选择
  const handleFileSelect = useCallback((selectedFile: File) => {
    // 验证文件类型
    const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/bmp', 'image/tiff', 'application/pdf'];
    if (!validTypes.includes(selectedFile.type) && !selectedFile.name.match(/\.(jpg|jpeg|png|bmp|tiff|pdf)$/i)) {
      onError?.(t('dataViews.ocr.unsupportedFormat'));
      return;
    }

    // 验证文件大小（限制 20MB）
    if (selectedFile.size > 20 * 1024 * 1024) {
      onError?.(t('dataViews.ocr.fileTooLarge'));
      return;
    }

    setFile(selectedFile);
    setResult(null);
    setEvents([]);

    // 生成预览
    if (selectedFile.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (e) => {
        setPreview(e.target?.result as string);
      };
      reader.readAsDataURL(selectedFile);
    } else {
      setPreview('');
    }
  }, [onError, t]);

  // 处理拖放
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      handleFileSelect(droppedFile);
    }
  }, [handleFileSelect]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
  }, []);

  // 处理文件输入
  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      handleFileSelect(selectedFile);
    }
  }, [handleFileSelect]);

  // 上传并处理文件
  const handleUpload = useCallback(async () => {
    if (!file) return;

    setIsUploading(true);
    setIsProcessing(true);
    setEvents([t('dataViews.ocr.uploading')]);
    onUploadStart?.();

    abortControllerRef.current = new AbortController();

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('output_format', outputFormat);
      formData.append('use_structure', useStructure.toString());
      formData.append('save_result', 'true');

      setEvents(prev => [...prev, t('dataViews.ocr.recognizing')]);

      const response = await fetch(`${API_BASE_URL}/juben/ocr/upload`, {
        method: 'POST',
        body: formData,
        signal: abortControllerRef.current.signal,
        headers: {
          ...(getAuthHeaderValue() ? { Authorization: getAuthHeaderValue() as string } : {}),
        },
      });

      if (!response.ok) {
        throw new Error(`${t('dataViews.ocr.uploadFailed')}: ${response.statusText}`);
      }

      // 处理 SSE 响应
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error(t('dataViews.ocr.noStream'));
      }

      let currentText = '';
      let currentMetadata: any = {};

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              const eventType = data.event;
              const eventData = data.data;

              // 更新事件日志
              setEvents(prev => {
                const newEvents = [...prev];
                if (eventType === 'system') {
                  newEvents[newEvents.length - 1] = eventData.content || eventData;
                } else if (eventType === 'content') {
                  currentText = eventData.content;
                  currentMetadata = eventData.metadata || {};
                } else if (eventType === 'complete') {
                  setIsProcessing(false);
                } else if (eventType === 'error') {
                  onError?.(eventData.error || eventData.content || t('dataViews.ocr.unknownError'));
                  setIsProcessing(false);
                }
                return newEvents;
              });

              // 更新进度
              if (eventData.metadata?.processing_time) {
                onUploadProgress?.(100);
              }

            } catch (e) {
              console.error('解析 SSE 事件失败:', e);
            }
          }
        }
      }

      // 获取最终结果
      if (currentText) {
        const ocrResult: OCRResult = {
          text: currentText,
          metadata: {
            processing_time: currentMetadata.processing_time || 0,
            text_box_count: currentMetadata.text_box_count || 0,
            table_count: currentMetadata.table_count || 0,
            formula_count: currentMetadata.formula_count || 0,
          },
          saved_paths: currentMetadata.saved_paths || undefined,
        };

        setResult(ocrResult);
        onUploadComplete?.(ocrResult);
      }

      setIsProcessing(false);
      setIsUploading(false);
      setEvents(prev => [...prev, `✅ ${t('dataViews.ocr.done')}`]);

    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        setEvents(prev => [...prev, `❌ ${t('dataViews.ocr.canceled')}`]);
      } else {
        onError?.(error instanceof Error ? error.message : t('dataViews.ocr.uploadFailed'));
        setEvents(prev => [...prev, `❌ ${t('dataViews.ocr.error')}: ${error}`]);
      }
      setIsProcessing(false);
      setIsUploading(false);
    }
  }, [file, outputFormat, useStructure, onUploadStart, onUploadProgress, onUploadComplete, onError, t]);

  // 取消上传
  const handleCancel = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsUploading(false);
    setIsProcessing(false);
  }, []);

  // 复制结果
  const handleCopy = useCallback(async () => {
    if (result?.text) {
      await navigator.clipboard.writeText(result.text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [result]);

  // 下载结果
  const handleDownload = useCallback(() => {
    if (!result) return;

    const blob = new Blob([result.text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ocr_result_${Date.now()}.${outputFormat === 'json' ? 'json' : outputFormat === 'markdown' ? 'md' : 'txt'}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [result, outputFormat]);

  // 重置
  const handleReset = useCallback(() => {
    setFile(null);
    setPreview('');
    setResult(null);
    setEvents([]);
    setCopied(false);
    setSaveNoteMessage('');
    setSaveFileMessage('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, []);

  const handleSaveToNotes = useCallback(async () => {
    if (!result?.text) return;
    setSavingNote(true);
    setSaveNoteMessage('');
    try {
      const userId = localStorage.getItem('userId') || 'default_user';
      const sessionId = localStorage.getItem('sessionId') || 'default_session';
      const response = await fetch(`${API_BASE_URL}/notes/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(getAuthHeaderValue() ? { Authorization: getAuthHeaderValue() as string } : {}),
        },
        body: JSON.stringify({
          user_id: userId,
          session_id: sessionId,
          action: 'ocr',
          name: `ocr_${Date.now()}`,
          title: file?.name || t('dataViews.ocr.resultTitle'),
          context: result.text,
          cover_title: t('dataViews.ocr.coverTitle'),
          metadata: {
            output_format: outputFormat,
            use_structure: useStructure,
            source_file: file?.name || '',
            saved_paths: result.saved_paths || {},
          },
        }),
      });
      if (!response.ok) {
        throw new Error(t('dataViews.ocr.saveFailed'));
      }
      setSaveNoteMessage(t('dataViews.ocr.savedToNotes'));
    } catch (error) {
      setSaveNoteMessage(t('dataViews.ocr.saveNotesFailed'));
    } finally {
      setSavingNote(false);
    }
  }, [result, outputFormat, useStructure, file, t]);

  const handleSaveToFiles = useCallback(async () => {
    if (!result?.text) return;
    setSavingFile(true);
    setSaveFileMessage('');
    try {
      const userId = localStorage.getItem('userId') || 'default_user';
      const sessionId = localStorage.getItem('sessionId') || `ocr_${Date.now()}`;
      const projectId = selectedProjectId || localStorage.getItem('projectId') || 'default_project';
      const filename = file?.name
        ? `${file.name.replace(/\.[^/.]+$/, '')}_ocr.${outputFormat === 'markdown' ? 'md' : outputFormat === 'json' ? 'json' : 'txt'}`
        : `ocr_result_${Date.now()}.${outputFormat === 'markdown' ? 'md' : outputFormat === 'json' ? 'json' : 'txt'}`;

      const response = await fetch(`${API_BASE_URL}/juben/files/artifacts`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(getAuthHeaderValue() ? { Authorization: getAuthHeaderValue() as string } : {}),
        },
        body: JSON.stringify({
          filename,
          file_type: 'ocr_result',
          content: result.text,
          agent_source: 'ocr_agent',
          user_id: userId,
          session_id: sessionId,
          project_id: projectId,
          description: t('dataViews.ocr.resultTitle'),
          tags: ['ocr', outputFormat, useStructure ? 'structured' : 'plain'],
          metadata: {
            output_format: outputFormat,
            use_structure: useStructure,
            source_file: file?.name || '',
            saved_paths: result.saved_paths || {},
          },
        }),
      });
      if (!response.ok) {
        throw new Error(t('dataViews.ocr.saveFailed'));
      }
      if (selectedProjectId) {
        localStorage.setItem('projectId', selectedProjectId);
      }
      setSaveFileMessage(t('dataViews.ocr.savedToFiles'));
    } catch (error) {
      setSaveFileMessage(t('dataViews.ocr.saveFilesFailed'));
    } finally {
      setSavingFile(false);
    }
  }, [result, selectedProjectId, outputFormat, useStructure, file, t]);

  return (
    <div className={clsx('bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden', className)}>
      {/* 上传区域 */}
      {!result ? (
        <div className="p-6">
          {/* 拖放上传区域 */}
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onClick={() => fileInputRef.current?.click()}
            className={clsx(
              'border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors',
              'border-gray-300 dark:border-gray-600 hover:border-blue-400 dark:hover:border-blue-500',
              'bg-gray-50 dark:bg-gray-900/50'
            )}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*,.pdf"
              onChange={handleFileInput}
              className="hidden"
            />

            <div className="flex flex-col items-center gap-4">
              {preview ? (
                <>
                  <img src={preview} alt="Preview" className="max-h-64 rounded-lg shadow" />
                  <p className="text-sm text-gray-600 dark:text-gray-400">{file?.name}</p>
                </>
              ) : (
                <>
                  <div className="p-4 bg-blue-100 dark:bg-blue-900/30 rounded-full">
                    <Upload className="w-8 h-8 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div>
                    <p className="text-lg font-medium text-gray-900 dark:text-white">
                      {t('dataViews.ocr.dragTitle')}
                    </p>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                      {t('dataViews.ocr.dragHint')}
                    </p>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* 配置选项 */}
          {file && !result && (
            <div className="mt-6 space-y-4">
              {/* 输出格式选择 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  {t('dataViews.ocr.outputFormat')}
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {(['text', 'markdown', 'json', 'structured'] as OutputFormat[]).map((format) => (
                    <button
                      key={format}
                      onClick={() => setOutputFormat(format)}
                      className={clsx(
                        'px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                        outputFormat === format
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
                      )}
                    >
                      {format.charAt(0).toUpperCase() + format.slice(1)}
                    </button>
                  ))}
                </div>
              </div>

              {/* 结构化识别选项 */}
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={useStructure}
                  onChange={(e) => setUseStructure(e.target.checked)}
                  className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">
                  {t('dataViews.ocr.useStructure')}
                </span>
              </label>

              {/* 操作按钮 */}
              <div className="flex gap-3">
                <button
                  onClick={handleUpload}
                  disabled={isUploading}
                  className={clsx(
                    'flex-1 flex items-center justify-center gap-2 px-6 py-3 rounded-lg font-medium text-white transition-colors',
                    isUploading
                      ? 'bg-gray-400 cursor-not-allowed'
                      : 'bg-blue-600 hover:bg-blue-700'
                  )}
                >
                  {isProcessing ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      {t('dataViews.ocr.processing')}
                    </>
                  ) : (
                    <>
                      <Upload className="w-5 h-5" />
                      {t('dataViews.ocr.start')}
                    </>
                  )}
                </button>
                {isUploading && (
                  <button
                    onClick={handleCancel}
                    className="px-6 py-3 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors"
                  >
                    {t('common.cancel')}
                  </button>
                )}
              </div>
            </div>
          )}

          {/* 事件日志 */}
          {events.length > 0 && (
            <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  {t('dataViews.ocr.log')}
                </span>
              </div>
              <div className="space-y-1">
                {events.map((event, index) => (
                  <div key={index} className="text-xs font-mono text-gray-600 dark:text-gray-400">
                    {event}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        /* 结果显示 */
        <div className="p-6">
          {/* 结果头部 */}
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              {t('dataViews.ocr.result')}
            </h3>
            <div className="flex gap-2">
              <button
                onClick={handleCopy}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                title={t('dataViews.ocr.copy')}
              >
                {copied ? (
                  <Check className="w-5 h-5 text-green-500" />
                ) : (
                  <Copy className="w-5 h-5 text-gray-500" />
                )}
              </button>
              <button
                onClick={handleDownload}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                title={t('dataViews.ocr.download')}
              >
                <Download className="w-5 h-5 text-gray-500" />
              </button>
              <button
                onClick={handleReset}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                title={t('dataViews.ocr.reupload')}
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
          </div>

          {/* 保存到 Notes/Files */}
          <div className="mb-4 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="flex flex-wrap items-center gap-3">
              <button
                onClick={handleSaveToNotes}
                disabled={savingNote}
                className={clsx(
                  'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                  savingNote
                    ? 'bg-gray-300 text-gray-600 cursor-not-allowed'
                    : 'bg-black text-white hover:bg-gray-800'
                )}
              >
                {savingNote ? t('dataViews.ocr.saving') : t('dataViews.ocr.saveToNotes')}
              </button>

              <div className="flex items-center gap-2">
                <select
                  value={selectedProjectId}
                  onChange={(e) => setSelectedProjectId(e.target.value)}
                  className="px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg text-sm"
                >
                  <option value="">{t('dataViews.ocr.selectProject')}</option>
                  {projects.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.name}
                    </option>
                  ))}
                </select>
                <button
                  onClick={handleSaveToFiles}
                  disabled={savingFile}
                  className={clsx(
                    'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                    savingFile
                      ? 'bg-gray-300 text-gray-600 cursor-not-allowed'
                      : 'bg-blue-600 text-white hover:bg-blue-700'
                  )}
                >
                  {savingFile ? t('dataViews.ocr.saving') : t('dataViews.ocr.saveToFiles')}
                </button>
              </div>
            </div>
            {(saveNoteMessage || saveFileMessage) && (
              <div className="mt-2 text-xs text-gray-500">
                {saveNoteMessage && <div>{saveNoteMessage}</div>}
                {saveFileMessage && <div>{saveFileMessage}</div>}
              </div>
            )}
          </div>

          {/* 元数据 */}
          {result.metadata && (
            <div className="grid grid-cols-4 gap-4 mb-4 p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {result.metadata.processing_time?.toFixed(2) || '0'}s
                </div>
                <div className="text-xs text-gray-500">{t('dataViews.ocr.processingTime')}</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {result.metadata.text_box_count || 0}
                </div>
                <div className="text-xs text-gray-500">{t('dataViews.ocr.textBoxes')}</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">
                  {result.metadata.table_count || 0}
                </div>
                <div className="text-xs text-gray-500">{t('dataViews.ocr.tables')}</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-orange-600">
                  {result.metadata.formula_count || 0}
                </div>
                <div className="text-xs text-gray-500">{t('dataViews.ocr.formulas')}</div>
              </div>
            </div>
          )}

          {/* 文本内容 */}
          <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg max-h-96 overflow-y-auto">
            <pre className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
              {result.text}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
};
