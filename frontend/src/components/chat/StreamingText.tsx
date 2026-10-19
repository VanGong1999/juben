/**
 * 流式文本 — 直接渲染，避免过度缓冲导致「只显示一个字符」
 * 流式中用不完整 Markdown 友好策略；结束后完整 GFM 渲染
 * 进度短句（开始…/正在…）竖排展示，前缀「、」
 */

import { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github.css';
import clsx from 'clsx';
import { useI18n } from '@/i18n';
import { splitProgressPrefix } from '@/utils/splitProgressContent';

interface StreamingTextProps {
  content: string;
  isStreaming?: boolean;
  className?: string;
  /** 更紧凑的工作室对话样式 */
  compact?: boolean;
}

function ProgressList({ lines, compact }: { lines: string[]; compact?: boolean }) {
  if (lines.length === 0) return null;
  return (
    <ul
      className={clsx(
        'mb-2 space-y-0.5 text-ink-muted list-none pl-0',
        compact ? 'text-[12px] leading-snug' : 'text-[13px] leading-relaxed'
      )}
    >
      {lines.map((line, i) => (
        <li key={`${i}-${line.slice(0, 12)}`} className="flex gap-0.5">
          <span className="shrink-0 select-none text-ink-faint">、</span>
          <span className="min-w-0 break-words">{line}</span>
        </li>
      ))}
    </ul>
  );
}

export default function StreamingText({
  content,
  isStreaming = false,
  className,
  compact = false,
}: StreamingTextProps) {
  const { t } = useI18n();
  const text = content || '';
  const { progressLines, body } = useMemo(() => splitProgressPrefix(text), [text]);
  const displayBody = body || (progressLines.length === 0 ? text : '');
  const looksLikeMd = useMemo(
    () => /(^#{1,6}\s)|(\*\*|__)|(`{1,3})|(\n[-*+]\s)|(\[[^\]]+\]\()/.test(displayBody),
    [displayBody]
  );

  // 流式且尚未形成可读内容
  if (isStreaming && text.trim().length === 0) {
    return (
      <div className={clsx('flex items-center gap-1 text-[11px] text-ink-faint', className)}>
        <span className="w-1 h-1 rounded-full bg-atelier-teal animate-pulse" />
        <span className="w-1 h-1 rounded-full bg-atelier-teal animate-pulse [animation-delay:120ms]" />
        <span className="w-1 h-1 rounded-full bg-atelier-teal animate-pulse [animation-delay:240ms]" />
        <span className="ml-1">{t('chatGraph.streaming.generating')}</span>
      </div>
    );
  }

  // 流式过程中：优先纯文本，避免半截 Markdown 炸版
  if (isStreaming && !looksLikeMd) {
    return (
      <div className={clsx(className)}>
        <ProgressList lines={progressLines} compact={compact} />
        {displayBody ? (
          <p
            className={clsx(
              'whitespace-pre-wrap break-words text-ink leading-relaxed',
              compact ? 'text-[12.5px]' : 'text-sm'
            )}
          >
            {displayBody}
            <span className="inline-block w-[2px] h-[0.9em] ml-0.5 align-[-1px] bg-atelier-teal animate-pulse" />
          </p>
        ) : (
          progressLines.length > 0 && (
            <span className="inline-block w-[2px] h-[0.9em] ml-0.5 align-[-1px] bg-atelier-teal animate-pulse" />
          )
        )}
      </div>
    );
  }

  return (
    <div className={clsx(className)}>
      <ProgressList lines={progressLines} compact={compact} />
      {displayBody ? (
        <div
          className={clsx(
            'markdown max-w-none text-ink',
            compact
              ? 'prose prose-sm prose-neutral [&_p]:my-1.5 [&_ul]:my-1.5 [&_ol]:my-1.5 [&_li]:my-0.5 [&_h1]:text-base [&_h2]:text-sm [&_h3]:text-[13px] [&_pre]:text-[11px] text-[12.5px] leading-relaxed'
              : 'prose prose-sm max-w-none'
          )}
        >
          <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
            {displayBody}
          </ReactMarkdown>
          {isStreaming && (
            <span className="inline-block w-[2px] h-[0.9em] ml-0.5 align-[-1px] bg-atelier-teal animate-pulse" />
          )}
        </div>
      ) : null}
    </div>
  );
}
