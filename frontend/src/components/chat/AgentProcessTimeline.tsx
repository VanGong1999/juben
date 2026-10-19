/**
 * Cursor 风格 Agent 工作过程时间线
 * 思考 / 系统 / 工具 / 子专家 / 交接 — 不同类型不同视觉
 */

import { useState, type Dispatch, type SetStateAction } from 'react';
import clsx from 'clsx';
import { useI18n } from '@/i18n';
import {
  Brain,
  Wrench,
  Bot,
  ArrowRightLeft,
  Settings,
  AlertCircle,
  CheckCircle2,
  Loader2,
  ChevronDown,
  ChevronRight,
  Sparkles,
} from 'lucide-react';

export type ProcessStepKind =
  | 'thinking'
  | 'system'
  | 'tool'
  | 'tool_result'
  | 'subagent'
  | 'handoff'
  | 'composition'
  | 'error'
  | 'info';

export interface ProcessStep {
  id: string;
  kind: ProcessStepKind;
  title: string;
  detail?: string;
  status?: 'running' | 'done' | 'error';
  toolName?: string;
  agentId?: string;
  timestamp?: string;
  /** Cursor 风格：子专家嵌套过程 */
  children?: ProcessStep[];
}

const KIND_UI: Record<
  ProcessStepKind,
  { icon: typeof Brain; labelKey: string; accent: string; bg: string; border: string }
> = {
  thinking: {
    icon: Brain,
    labelKey: 'chatGraph.timeline.kind.thinking',
    accent: 'text-violet-700',
    bg: 'bg-violet-50/80',
    border: 'border-violet-200/80',
  },
  system: {
    icon: Settings,
    labelKey: 'chatGraph.timeline.kind.system',
    accent: 'text-sky-700',
    bg: 'bg-sky-50/80',
    border: 'border-sky-200/80',
  },
  tool: {
    icon: Wrench,
    labelKey: 'chatGraph.timeline.kind.tool',
    accent: 'text-amber-800',
    bg: 'bg-amber-50/80',
    border: 'border-amber-200/80',
  },
  tool_result: {
    icon: CheckCircle2,
    labelKey: 'chatGraph.timeline.kind.toolResult',
    accent: 'text-emerald-700',
    bg: 'bg-emerald-50/70',
    border: 'border-emerald-200/80',
  },
  subagent: {
    icon: Bot,
    labelKey: 'chatGraph.timeline.kind.subagent',
    accent: 'text-atelier-teal',
    bg: 'bg-atelier-teal-soft/60',
    border: 'border-atelier-teal/25',
  },
  handoff: {
    icon: ArrowRightLeft,
    labelKey: 'chatGraph.timeline.kind.handoff',
    accent: 'text-orange-700',
    bg: 'bg-orange-50/80',
    border: 'border-orange-200/80',
  },
  composition: {
    icon: Sparkles,
    labelKey: 'chatGraph.timeline.kind.composition',
    accent: 'text-fuchsia-700',
    bg: 'bg-fuchsia-50/80',
    border: 'border-fuchsia-200/80',
  },
  error: {
    icon: AlertCircle,
    labelKey: 'chatGraph.timeline.kind.error',
    accent: 'text-rose-700',
    bg: 'bg-rose-50/80',
    border: 'border-rose-200/80',
  },
  info: {
    icon: Settings,
    labelKey: 'chatGraph.timeline.kind.info',
    accent: 'text-ink-muted',
    bg: 'bg-pearl-soft/80',
    border: 'border-pearl-line',
  },
};

type Props = {
  steps: ProcessStep[];
  isStreaming?: boolean;
  defaultExpanded?: boolean;
  className?: string;
};

export default function AgentProcessTimeline({
  steps,
  isStreaming = false,
  defaultExpanded = true,
  className,
}: Props) {
  const { t } = useI18n();
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [openIds, setOpenIds] = useState<Record<string, boolean>>({});

  if (steps.length === 0 && !isStreaming) return null;

  const running = steps.filter((s) => s.status === 'running').length;
  const done = steps.filter((s) => s.status === 'done').length;

  return (
    <div className={clsx('rounded-lg border border-pearl-line/90 bg-white/70 overflow-hidden', className)}>
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center justify-between gap-2 px-2.5 py-1.5 hover:bg-pearl-soft/60 transition-colors"
      >
        <div className="flex items-center gap-1.5 min-w-0">
          {isStreaming ? (
            <Loader2 className="w-3 h-3 animate-spin text-atelier-teal shrink-0" />
          ) : (
            <Sparkles className="w-3 h-3 text-atelier-teal shrink-0" />
          )}
          <span className="text-[11px] font-semibold text-ink truncate">{t('chatGraph.timeline.title')}</span>
          <span className="text-[10px] text-ink-faint tabular-nums">
            {t('chatGraph.timeline.steps', { count: steps.length })}
            {running > 0 ? ` · ${running} ${t('chatGraph.timeline.running')}` : done > 0 ? ` · ${done} ${t('common.done')}` : ''}
          </span>
        </div>
        {expanded ? (
          <ChevronDown className="w-3.5 h-3.5 text-ink-faint" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5 text-ink-faint" />
        )}
      </button>

      {expanded && (
        <div className="px-2 pb-2 space-y-1 max-h-80 overflow-y-auto">
          {steps.length === 0 && isStreaming && (
            <div className="flex items-center gap-1.5 px-2 py-1.5 text-[11px] text-ink-muted">
              <Loader2 className="w-3 h-3 animate-spin" />
              {t('chatGraph.timeline.orchestrating')}
            </div>
          )}
          {steps.map((step) => (
            <ProcessStepRow
              key={step.id}
              step={step}
              openIds={openIds}
              setOpenIds={setOpenIds}
              depth={0}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function ProcessStepRow({
  step,
  openIds,
  setOpenIds,
  depth,
}: {
  step: ProcessStep;
  openIds: Record<string, boolean>;
  setOpenIds: Dispatch<SetStateAction<Record<string, boolean>>>;
  depth: number;
}) {
  const { t } = useI18n();
  const ui = KIND_UI[step.kind] || KIND_UI.info;
  const Icon = ui.icon;
  const hasDetail = Boolean(step.detail && step.detail.trim());
  const hasChildren = Boolean(step.children && step.children.length > 0);
  const open =
    openIds[step.id] ??
    (step.status === 'running' || step.kind === 'error' || (step.kind === 'subagent' && hasChildren));
  const expandable = hasDetail || hasChildren;

  return (
    <div
      className={clsx('rounded-md border px-2 py-1.5', ui.bg, ui.border)}
      style={{ marginLeft: depth > 0 ? Math.min(depth, 3) * 10 : 0 }}
    >
      <button
        type="button"
        className="w-full flex items-start gap-1.5 text-left"
        onClick={() => {
          if (!expandable) return;
          setOpenIds((m) => ({ ...m, [step.id]: !open }));
        }}
      >
        <Icon className={clsx('w-3 h-3 mt-0.5 shrink-0', ui.accent)} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className={clsx('text-[10px] font-semibold uppercase tracking-wide', ui.accent)}>
              {t(ui.labelKey)}
            </span>
            {step.toolName && (
              <code className="text-[10px] px-1 rounded bg-white/70 text-ink-muted font-mono">
                {step.toolName}
              </code>
            )}
            {step.agentId && (
              <span className="text-[10px] text-ink-faint font-mono">{step.agentId}</span>
            )}
            {step.status === 'running' && (
              <Loader2 className="w-2.5 h-2.5 animate-spin text-atelier-teal" />
            )}
            {step.status === 'done' && <CheckCircle2 className="w-2.5 h-2.5 text-emerald-600" />}
            {step.status === 'error' && <AlertCircle className="w-2.5 h-2.5 text-rose-600" />}
          </div>
                    <p className="text-[11px] text-ink leading-snug mt-0.5 break-words whitespace-pre-wrap">
                      {step.title}
                    </p>
        </div>
        {expandable &&
          (open ? (
            <ChevronDown className="w-3 h-3 text-ink-faint shrink-0 mt-0.5" />
          ) : (
            <ChevronRight className="w-3 h-3 text-ink-faint shrink-0 mt-0.5" />
          ))}
      </button>
      {hasDetail && open && (
        <pre className="mt-1.5 max-h-28 overflow-auto rounded bg-ink/[0.04] px-2 py-1.5 text-[10px] leading-relaxed text-ink-muted whitespace-pre-wrap font-mono">
          {step.detail}
        </pre>
      )}
      {hasChildren && open && (
        <div className="mt-1.5 space-y-1 border-l-2 border-atelier-teal/25 pl-2">
          {step.children!.slice(-8).map((child) => (
            <ProcessStepRow
              key={child.id}
              step={child}
              openIds={openIds}
              setOpenIds={setOpenIds}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/** 将 Thought[] / 原始事件粗转为 ProcessStep */
export function thoughtsToProcessSteps(
  thoughts: Array<{ step: number; content: string; timestamp?: string; type?: string }>
): ProcessStep[] {
  return thoughts.map((t, i) => {
    const kind = inferKind(t.type, t.content);
    return {
      id: `thought-${t.step || i}`,
      kind,
      title: t.content.slice(0, 200),
      detail: t.content.length > 200 ? t.content : undefined,
      status: 'done' as const,
      timestamp: t.timestamp,
    };
  });
}

function inferKind(type: string | undefined, content: string): ProcessStepKind {
  const t = (type || '').toLowerCase();
  const c = content.toLowerCase();
  if (t === 'tool' || c.includes('工具') || c.includes('tool')) return 'tool';
  if (t === 'handoff' || c.includes('交接') || c.includes('handoff')) return 'handoff';
  if (t === 'subagent' || c.includes('子专家') || c.includes('spawn')) return 'subagent';
  if (t === 'error') return 'error';
  if (t === 'system') return 'system';
  if (t === 'thinking' || t === 'reasoning' || c.includes('思考')) return 'thinking';
  return 'info';
}
