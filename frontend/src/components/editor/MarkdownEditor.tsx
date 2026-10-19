/**
 * Markdown 编辑器组件
 * 支持实时预览、语法高亮、快捷键等功能
 */

import React, { useState, useCallback, useRef, useEffect } from 'react';
import {
  Bold,
  Italic,
  List,
  ListOrdered,
  Heading1,
  Heading2,
  Heading3,
  Quote,
  Code,
  Link as LinkIcon,
  Image,
  Undo,
  Redo,
  Eye,
  EyeOff,
  Maximize2,
  Minimize2,
  Copy,
  Download,
  Upload,
} from 'lucide-react';
import { useNotificationStore } from '@/store/notificationStore';
import { useI18n } from '@/i18n';

interface MarkdownEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  height?: string;
  readOnly?: boolean;
  showPreview?: boolean;
  toolbar?: boolean;
}

export const MarkdownEditor: React.FC<MarkdownEditorProps> = ({
  value,
  onChange,
  placeholder,
  height = '500px',
  readOnly = false,
  showPreview = true,
  toolbar = true,
}) => {
  const [isPreviewMode, setIsPreviewMode] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { success, error } = useNotificationStore();
  const { t } = useI18n();

  // 插入 Markdown 语法
  const insertMarkdown = useCallback(
    (before: string, after: string = '', placeholder: string = '') => {
      const textarea = textareaRef.current;
      if (!textarea) return;

      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const selectedText = value.substring(start, end) || placeholder;

      const newValue =
        value.substring(0, start) + before + selectedText + after + value.substring(end);

      onChange(newValue);

      // 恢复焦点和选中状态
      setTimeout(() => {
        textarea.focus();
        textarea.setSelectionRange(
          start + before.length,
          start + before.length + selectedText.length
        );
      }, 0);
    },
    [value, onChange]
  );

  // 工具栏按钮配置
  const toolbarButtons = [
    {
      icon: <Undo className="w-4 h-4" />,
      title: t('studio.undo'),
      action: () => {
        // 撤销功能（简化实现）
        textareaRef.current?.focus();
        document.execCommand('undo');
      },
    },
    {
      icon: <Redo className="w-4 h-4" />,
      title: t('studio.redo'),
      action: () => {
        // 重做功能（简化实现）
        textareaRef.current?.focus();
        document.execCommand('redo');
      },
    },
    { divider: true },
    {
      icon: <Bold className="w-4 h-4" />,
      title: t('ui.bold'),
      action: () => insertMarkdown('**', '**', '粗体文本'),
    },
    {
      icon: <Italic className="w-4 h-4" />,
      title: t('ui.italic'),
      action: () => insertMarkdown('*', '*', '斜体文本'),
    },
    {
      icon: <Heading1 className="w-4 h-4" />,
      title: t('ui.heading1'),
      action: () => insertMarkdown('# ', '', '标题 1'),
    },
    {
      icon: <Heading2 className="w-4 h-4" />,
      title: t('ui.heading2'),
      action: () => insertMarkdown('## ', '', '标题 2'),
    },
    {
      icon: <Heading3 className="w-4 h-4" />,
      title: t('ui.heading3'),
      action: () => insertMarkdown('### ', '', '标题 3'),
    },
    { divider: true },
    {
      icon: <List className="w-4 h-4" />,
      title: t('ui.unorderedList'),
      action: () => insertMarkdown('- ', '', '列表项'),
    },
    {
      icon: <ListOrdered className="w-4 h-4" />,
      title: t('ui.orderedList'),
      action: () => insertMarkdown('1. ', '', '列表项'),
    },
    {
      icon: <Quote className="w-4 h-4" />,
      title: t('ui.quote'),
      action: () => insertMarkdown('> ', '', '引用内容'),
    },
    {
      icon: <Code className="w-4 h-4" />,
      title: t('ui.codeBlock'),
      action: () => insertMarkdown('```\n', '\n```', '代码'),
    },
    {
      icon: <LinkIcon className="w-4 h-4" />,
      title: t('ui.link'),
      action: () => insertMarkdown('[', '](url)', '链接文本'),
    },
    {
      icon: <Image className="w-4 h-4" />,
      title: t('ui.image'),
      action: () => insertMarkdown('![', '](url)', '图片描述'),
    },
  ];

  // 处理复制
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      success(t('ui.copySuccess'), t('ui.copySuccessDesc'));
    } catch {
      error(t('ui.copyFailed'), t('ui.copyFailedDesc'));
    }
  };

  // 处理下载
  const handleDownload = () => {
    const blob = new Blob([value], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `document-${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
    success(t('ui.downloadSuccess'), t('ui.downloadSuccessDesc'));
  };

  // 处理文件上传
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      onChange(content);
      success(t('ui.importSuccess'), t('ui.importSuccessDesc'));
    };
    reader.onerror = () => {
      error(t('ui.importFailed'), t('ui.importFailedDesc'));
    };
    reader.readAsText(file);
  };

  // 简单的 Markdown 渲染（实际应用中应该使用 markdown-it 或类似库）
  const renderMarkdown = (markdown: string) => {
    // 这是一个简化的实现，实际应用中应该使用专业的 Markdown 解析库
    let html = markdown
      // 标题
      .replace(/^### (.*$)/gim, '<h3>$1</h3>')
      .replace(/^## (.*$)/gim, '<h2>$1</h2>')
      .replace(/^# (.*$)/gim, '<h1>$1</h1>')
      // 粗体和斜体
      .replace(/\*\*\*(.*?)\*\*\*/gim, '<strong><em>$1</em></strong>')
      .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/gim, '<em>$1</em>')
      // 代码
      .replace(/```([\s\S]*?)```/gim, '<pre><code>$1</code></pre>')
      .replace(/`(.*?)`/gim, '<code>$1</code>')
      // 链接和图片
      .replace(/!\[(.*?)\]\((.*?)\)/gim, '<img alt="$1" src="$2" />')
      .replace(/\[(.*?)\]\((.*?)\)/gim, '<a href="$2" target="_blank">$1</a>')
      // 引用
      .replace(/^> (.*$)/gim, '<blockquote>$1</blockquote>')
      // 列表
      .replace(/^\d+\. (.*$)/gim, '<ol><li>$1</li></ol>')
      .replace(/^- (.*$)/gim, '<ul><li>$1</li></ul>')
      // 段落
      .replace(/\n\n/g, '</p><p>')
      .replace(/\n/g, '<br />');

    return `<div class="markdown prose max-w-none">${html}</div>`;
  };

  return (
    <div
      className={`markdown-editor border border-gray-300 dark:border-gray-600 rounded-lg overflow-hidden bg-white dark:bg-gray-800 ${
        isFullscreen ? 'fixed inset-4 z-50' : ''
      }`}
      style={{ height: isFullscreen ? 'auto' : height }}
    >
      {/* 工具栏 */}
      {toolbar && !readOnly && (
        <div className="flex items-center justify-between px-4 py-2 border-b border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700">
          <div className="flex items-center gap-1 flex-wrap">
            {toolbarButtons.map((button, index) =>
              button.divider ? (
                <div key={index} className="w-px h-6 bg-gray-300 dark:bg-gray-600 mx-1" />
              ) : (
                <button
                  key={index}
                  onClick={button.action}
                  className="p-2 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                  title={button.title}
                >
                  {button.icon}
                </button>
              )
            )}
          </div>

          <div className="flex items-center gap-2">
            {/* 切换预览 */}
            {showPreview && (
              <button
                onClick={() => setIsPreviewMode(!isPreviewMode)}
                className="p-2 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                title={isPreviewMode ? t('ui.showEditor') : t('ui.showPreview')}
              >
                {isPreviewMode ? (
                  <EyeOff className="w-4 h-4" />
                ) : (
                  <Eye className="w-4 h-4" />
                )}
              </button>
            )}

            {/* 复制 */}
            <button
              onClick={handleCopy}
              className="p-2 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
              title={t('ui.copyContent')}
            >
              <Copy className="w-4 h-4" />
            </button>

            {/* 下载 */}
            <button
              onClick={handleDownload}
              className="p-2 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
              title={t('ui.downloadMarkdown')}
            >
              <Download className="w-4 h-4" />
            </button>

            {/* 上传 */}
            <label className="p-2 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors cursor-pointer">
              <Upload className="w-4 h-4" />
              <input
                type="file"
                accept=".md,.markdown,.txt"
                onChange={handleFileUpload}
                className="hidden"
              />
            </label>

            {/* 全屏 */}
            <button
              onClick={() => setIsFullscreen(!isFullscreen)}
              className="p-2 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
              title={isFullscreen ? t('studio.exitFullscreen') : t('studio.fullscreen')}
            >
              {isFullscreen ? (
                <Minimize2 className="w-4 h-4" />
              ) : (
                <Maximize2 className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>
      )}

      {/* 编辑器和预览区域 */}
      <div className="flex h-full">
        {/* 编辑器 */}
        {!isPreviewMode && (
          <div className={showPreview && !isPreviewMode ? 'w-1/2' : 'w-full'}>
            <textarea
              ref={textareaRef}
              value={value}
              onChange={(e) => onChange(e.target.value)}
              placeholder={placeholder || t('ui.markdownPlaceholder')}
              readOnly={readOnly}
              className="w-full h-full p-4 resize-none focus:outline-none bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-mono text-sm"
              style={{ minHeight: height }}
            />
          </div>
        )}

        {/* 预览 */}
        {showPreview && isPreviewMode && (
          <div className="w-full h-full overflow-auto p-4 bg-white dark:bg-gray-800">
            <div
              className="markdown-body prose prose-sm max-w-none dark:prose-invert"
              dangerouslySetInnerHTML={{ __html: renderMarkdown(value) }}
            />
          </div>
        )}

        {/* 分屏预览 */}
        {showPreview && !isPreviewMode && (
          <div className="w-1/2 h-full overflow-auto p-4 border-l border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-900">
            <div
              className="markdown-body prose prose-sm max-w-none dark:prose-invert"
              dangerouslySetInnerHTML={{ __html: renderMarkdown(value) }}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default MarkdownEditor;
