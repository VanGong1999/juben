/**
 * 简单的输入区域组件
 * 用于 ChatPanel，接受外部回调函数
 */

import { useState, useRef, useEffect, KeyboardEvent, useMemo, DragEvent } from 'react';
import { Send, Layers, FileText, Mic, Paperclip, Loader2, X } from 'lucide-react';
import { useWorkspaceStore, type Note } from '@/store/workspaceStore';
import { AGENTS_CONFIG } from '@/config/agents';
import { uploadScript, getScript } from '@/services/scriptService';
import { clsx } from 'clsx';
import { useI18n } from '@/i18n';
import {
  DRAMA_REF_MIME,
  dramaRefLabel,
  formatDramaRef,
  parseDramaRefDragData,
  type DramaRefPayload,
} from '@/utils/dramaRefs';

interface ChatInputAreaProps {
  onSend: (content: string) => void | Promise<void>;
  disabled?: boolean;
  placeholder?: string;
  suggestions?: string[];
  compact?: boolean;
}

export default function ChatInputArea({
  onSend,
  disabled = false,
  placeholder,
  suggestions = [],
  compact = false,
}: ChatInputAreaProps) {
  const { t } = useI18n();
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const [speechSupported, setSpeechSupported] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [dramaRefs, setDramaRefs] = useState<DramaRefPayload[]>([]);
  const { notes, setViewMode } = useWorkspaceStore();
  const dramaId =
    typeof window !== 'undefined'
      ? localStorage.getItem('dramaId') || localStorage.getItem('projectId') || ''
      : '';

  const attachDramaRef = (ref: DramaRefPayload) => {
    const token = formatDramaRef(ref);
    if (!token) return;
    setDramaRefs((prev) => {
      if (prev.some((r) => formatDramaRef(r) === token)) return prev;
      return [...prev, ref];
    });
    setInput((prev) => {
      if (prev.includes(token)) return prev;
      const sep = prev.trim() ? (prev.endsWith(' ') ? '' : ' ') : '';
      return `${prev}${sep}${token} `;
    });
  };

  const removeDramaRef = (ref: DramaRefPayload) => {
    const token = formatDramaRef(ref);
    setDramaRefs((prev) => prev.filter((r) => formatDramaRef(r) !== token));
    setInput((prev) =>
      prev
        .replace(new RegExp(`${token.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*`, 'g'), '')
        .replace(/\s{2,}/g, ' ')
        .trimStart()
    );
  };

  const handleDramaDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const ref = parseDramaRefDragData(e);
    if (ref) {
      attachDramaRef(ref);
      return;
    }
    // 普通文件仍走剧本上传
    if (e.dataTransfer.files?.length) {
      void handleAttachScript(e.dataTransfer.files);
    }
  };

  const selectedNotes = useMemo(() => notes.filter((n) => n.select_status === 1), [notes]);

  // 🆕 创建 agent action 到 displayName 的映射
  const agentDisplayNameMap = useMemo(() => {
    const map = new Map<string, string>();
    AGENTS_CONFIG.forEach(agent => {
      map.set(agent.id, agent.displayName);
      map.set(agent.name, agent.displayName);
      map.set(agent.id.replace('_', '_'), agent.displayName);
      map.set(agent.name.toLowerCase(), agent.displayName);
    });
    return map;
  }, []);

  // 🆕 生成笔记引用名称（与 InputArea.tsx 保持一致）
  const generateNoteReference = (note: Note): string => {
    // 获取 agent 的显示名称
    const agentDisplayName = agentDisplayNameMap.get(note.action || '') || 
                            note.metadata?.agent_name || 
                            note.action?.replace(/_agent$/, '').replace(/_/g, ' ') ||
                            'note';
    
    // 将显示名称转换为适合引用的格式（去除空格，使用下划线）
    const agentNameForRef = agentDisplayName
      .replace(/\s+/g, '_')
      .replace(/[^\w\u4e00-\u9fa5_]/g, '') // 保留中文、英文、数字和下划线
      .toLowerCase();

    // 计算该 agent 下的笔记索引（按创建时间排序）
    const sameActionNotes = notes
      .filter(n => n.action === note.action)
      .sort((a, b) => {
        // 按创建时间排序
        const timeA = new Date(a.created_at || 0).getTime();
        const timeB = new Date(b.created_at || 0).getTime();
        return timeA - timeB;
      });
    
    const noteIndex = sameActionNotes.findIndex(n => n.id === note.id) + 1;

    return `${agentNameForRef}_${noteIndex}`;
  };

  // 🆕 解析笔记引用名称，找到对应的笔记
  const findNoteByReference = (refName: string): Note | null => {
    // 尝试匹配所有笔记的引用名称
    for (const note of notes) {
      const noteRef = generateNoteReference(note);
      if (noteRef === refName) {
        return note;
      }
    }
    return null;
  };

  // 🆕 解析输入内容中的 @笔记名称，替换为完整笔记内容
  const expandNoteReferences = (text: string): string => {
    // 匹配 @笔记名称 格式（支持 @笔记名 或 @笔记名_数字）
    const noteRefPattern = /@([a-z0-9_\u4e00-\u9fa5]+(?:_\d+)?)/g;
    let expandedText = text;
    const foundRefs = new Set<string>();

    // 收集所有笔记引用
    let match;
    while ((match = noteRefPattern.exec(text)) !== null) {
      const refName = match[1];
      if (!foundRefs.has(refName)) {
        foundRefs.add(refName);
        const note = findNoteByReference(refName);
        if (note) {
          // 替换为完整笔记内容
          const noteContent = [
            `【${note.title || note.name || '笔记'}】`,
            note.context || '',
            note.metadata?.agent_name ? `\n来源：${note.metadata.agent_name}` : ''
          ].filter(Boolean).join('\n');
          
          expandedText = expandedText.replace(
            new RegExp(`@${refName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}`, 'g'),
            noteContent
          );
        }
      }
    }

    return expandedText;
  };

  // 自动调整高度
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px';
    }
  }, [input]);

  // 语音输入初始化
  useEffect(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setSpeechSupported(false);
      return;
    }
    setSpeechSupported(true);
    const recognition: SpeechRecognition = new SpeechRecognition();
    recognition.lang = 'zh-CN';
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const lastResult = event.results[event.results.length - 1];
      if (lastResult && lastResult.isFinal) {
        const transcript = lastResult[0].transcript.trim();
        setInput((prev) => (prev ? `${prev} ${transcript}` : transcript));
      }
    };
    recognition.onend = () => {
      setIsRecording(false);
    };
    recognition.onerror = () => {
      setIsRecording(false);
    };
    recognitionRef.current = recognition;
  }, []);

  const handleSend = async () => {
    if (!input.trim() || disabled) return;
    
    // 🆕 解析笔记引用，将 @笔记名称 替换为完整内容
    const expandedContent = expandNoteReferences(input.trim());
    
    console.log('[ChatInputArea] 发送消息:', {
      original: input.trim(),
      expanded: expandedContent.substring(0, 200) + (expandedContent.length > 200 ? '...' : '')
    });
    
    await onSend(expandedContent);
    setInput('');
    setDramaRefs([]);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInsertNotes = () => {
    if (selectedNotes.length === 0) return;
    
    // 🆕 插入 @笔记名称 格式，而不是完整内容
    const noteRefs = selectedNotes.map(note => `@${generateNoteReference(note)}`).join(' ');
    const separator = input.trim() ? ' ' : '';
    setInput((prev) => prev ? `${prev}${separator}${noteRefs} ` : `${noteRefs} `);
    
    // 设置光标位置到末尾
    setTimeout(() => {
      if (textareaRef.current) {
        const newLength = textareaRef.current.value.length;
        textareaRef.current.setSelectionRange(newLength, newLength);
        textareaRef.current.focus();
      }
    }, 0);
  };

  const toggleRecording = () => {
    if (!speechSupported || !recognitionRef.current) return;
    if (isRecording) {
      recognitionRef.current.stop();
      setIsRecording(false);
    } else {
      recognitionRef.current.start();
      setIsRecording(true);
    }
  };

  const handleAttachScript = async (files: FileList | null) => {
    if (!files?.length) return;
    if (!dramaId) {
      setInput(
        (prev) =>
          prev ||
          t('workspace.openDramaFirst')
      );
      return;
    }
    setUploading(true);
    try {
      const parts: string[] = [];
      for (const file of Array.from(files)) {
        const up = await uploadScript(dramaId, file, {
          title: file.name.replace(/\.[^.]+$/, ''),
        });
        const docId = up.script?.id;
        if (!docId) continue;
        const full = await getScript(dramaId, docId, true);
        const clip = (full.script?.content || '').slice(0, 8000);
        parts.push(
          `【${t('workspace.uploadScriptLabel')}：${full.script?.title || file.name}】\n${clip}${
            (full.script?.content || '').length > 8000 ? `\n…(${t('workspace.truncated')})` : ''
          }`
        );
      }
      if (parts.length) {
        setInput((prev) => (prev ? `${prev}\n\n${parts.join('\n\n')}` : parts.join('\n\n')));
      }
    } catch (e) {
      console.error(e);
      setInput(
        (prev) => prev || `${t('workspace.uploadFailed')}：${e instanceof Error ? e.message : t('workspace.unknownError')}`
      );
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  };

  return (
    <div className="relative group/input">
      {suggestions.length > 0 && (
        <div className={clsx('flex flex-wrap gap-1', compact ? 'mb-1.5' : 'mb-3 gap-1.5')}>
          {suggestions.slice(0, compact ? 2 : 3).map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              onClick={() => setInput(suggestion)}
              className={clsx(
                'font-medium rounded-full border border-pearl-line/80 bg-white/50 backdrop-blur-sm text-ink-muted hover:border-atelier-teal/40 hover:text-atelier-teal hover:bg-atelier-teal-soft/80 transition-all duration-200',
                compact ? 'px-2 py-1 text-[10px] max-w-full truncate' : 'px-3 py-1.5 text-[11px]'
              )}
              disabled={disabled}
            >
              {suggestion}
            </button>
          ))}
        </div>
      )}

      <div
        onDragOver={(e) => {
          if (
            e.dataTransfer.types.includes(DRAMA_REF_MIME) ||
            e.dataTransfer.types.includes('Files') ||
            e.dataTransfer.types.includes('text/plain')
          ) {
            e.preventDefault();
            setDragOver(true);
          }
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDramaDrop}
        className={clsx(
          'relative border bg-white/55 backdrop-blur-xl shadow-atelier focus-within:border-atelier-teal/40 focus-within:ring-2 focus-within:ring-atelier-teal/10 transition-all duration-300',
          dragOver ? 'border-atelier-teal/60 ring-2 ring-atelier-teal/20' : 'border-white/60',
          compact ? 'rounded-xl' : 'rounded-2xl focus-within:ring-4'
        )}
      >
        {dramaRefs.length > 0 && (
          <div className="flex flex-wrap gap-1 px-3 pt-2.5">
            {dramaRefs.map((ref) => {
              const token = formatDramaRef(ref);
              return (
                <span
                  key={token}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] bg-atelier-teal-soft text-atelier-teal border border-atelier-teal/25"
                  title={token}
                >
                  <FileText className="w-3 h-3" />
                  {dramaRefLabel(ref)}
                  <button
                    type="button"
                    onClick={() => removeDramaRef(ref)}
                    className="p-0.5 rounded hover:bg-white/60"
                    aria-label={t('common.remove')}
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              );
            })}
          </div>
        )}
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            dragOver
              ? t('workspace.dropDramaRef')
              : placeholder ?? t('workspace.sendMessage')
          }
          disabled={disabled}
          rows={compact ? 2 : 3}
          className={clsx(
            'w-full bg-transparent border-0 outline-none resize-none text-ink placeholder:text-ink-faint',
            compact
              ? 'px-3 pt-2.5 pb-10 pr-20 rounded-xl text-[12.5px] leading-snug'
              : 'px-4 pt-3.5 pb-12 pr-24 rounded-2xl text-sm',
            disabled && 'opacity-50 cursor-not-allowed'
          )}
        />

        <input
          ref={fileRef}
          type="file"
          accept=".txt,.md,.markdown,.json,.csv,.srt,.fountain,text/plain"
          multiple
          className="hidden"
          onChange={(e) => void handleAttachScript(e.target.files)}
        />

        <div className="absolute right-2 bottom-2 flex items-center gap-1">
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            disabled={disabled || uploading}
            className="p-2.5 rounded-xl text-ink-faint hover:bg-pearl-soft hover:text-atelier-teal transition-colors disabled:opacity-40"
            title={dramaId ? t('workspace.uploadTitle') : t('workspace.openDramaToUpload')}
          >
            {uploading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Paperclip className="w-4 h-4" />
            )}
          </button>
          {speechSupported && (
            <button
              type="button"
              onClick={toggleRecording}
              className={clsx(
                'p-2.5 rounded-xl transition-colors',
                isRecording
                  ? 'bg-red-50 text-red-600'
                  : 'text-ink-faint hover:bg-pearl-soft hover:text-ink-muted'
              )}
              title={isRecording ? t('workspace.stopVoice') : t('workspace.voiceInput')}
            >
              <Mic className="w-4 h-4" />
            </button>
          )}
          <button
            onClick={handleSend}
            disabled={disabled || !input.trim() || uploading}
            className={clsx(
              'p-2.5 rounded-xl transition-all shadow-atelier',
              'bg-atelier-teal text-white hover:bg-atelier-teal-deep',
              'disabled:opacity-35 disabled:cursor-not-allowed disabled:shadow-none'
            )}
            title={t('workspace.sendEnter')}
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>

      {(notes.length > 0 || dramaId) && (
        <div
          className={clsx(
            'flex items-center gap-2 mt-2.5 text-[11px] text-ink-faint flex-wrap',
            'opacity-0 translate-y-1 pointer-events-none',
            'group-hover/input:opacity-100 group-hover/input:translate-y-0 group-hover/input:pointer-events-auto',
            'focus-within:opacity-100 focus-within:translate-y-0 focus-within:pointer-events-auto',
            'transition-all duration-200 ease-out'
          )}
        >
          {dramaId && (
            <>
              {(
                [
                  { kind: 'characters' as const, label: t('studio.bible.characters') },
                  { kind: 'outline' as const, label: t('studio.bible.seriesOutline') },
                  { kind: 'world' as const, label: t('studio.bible.world') },
                ] as const
              ).map((item) => (
                <button
                  key={item.kind}
                  type="button"
                  disabled={disabled}
                  onClick={() => attachDramaRef({ kind: item.kind, dramaId })}
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full border border-pearl-line/80 text-ink-muted bg-white/40 hover:border-atelier-teal/30 hover:text-atelier-teal hover:bg-atelier-teal-soft backdrop-blur-sm transition-colors"
                  title={t('workspace.insertDramaRef')}
                >
                  <FileText className="w-3.5 h-3.5" />
                  {item.label}
                </button>
              ))}
            </>
          )}
          {notes.length > 0 && (
            <>
              <button
                type="button"
                onClick={handleInsertNotes}
                disabled={selectedNotes.length === 0 || disabled}
                className={clsx(
                  'inline-flex items-center gap-1 px-2.5 py-1 rounded-full border transition-colors backdrop-blur-sm',
                  selectedNotes.length > 0
                    ? 'border-atelier-teal/30 text-atelier-teal bg-white/40 hover:bg-atelier-teal-soft'
                    : 'border-pearl-line text-ink-faint cursor-not-allowed bg-white/30'
                )}
              >
                <Layers className="w-3.5 h-3.5" />
                {t('workspace.insertNotes')}
                {selectedNotes.length > 0 && (
                  <span className="tabular-nums opacity-70">{selectedNotes.length}</span>
                )}
              </button>
              <button
                type="button"
                onClick={() => setViewMode('notes')}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full border border-pearl-line/80 text-ink-muted bg-white/40 hover:bg-pearl-soft backdrop-blur-sm transition-colors"
              >
                <FileText className="w-3.5 h-3.5" />
                {t('workspace.view')}
              </button>
            </>
          )}
          <span className="ml-auto hidden sm:inline opacity-60">{t('workspace.enterToSend')}</span>
        </div>
      )}
    </div>
  );
}
