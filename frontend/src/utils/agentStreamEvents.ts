/**
 * 将后端 SSE 事件转为 Cursor 风格 ProcessStep（支持嵌套 subagent）
 */

import type { ProcessStep } from '@/components/chat/AgentProcessTimeline';
import type { AgentStreamEvent } from '@/services/chatService';

let seq = 0;
function nid(prefix: string) {
  seq += 1;
  return `${prefix}-${Date.now()}-${seq}`;
}

function textOf(d: Record<string, any>, data: unknown): string {
  return String(
    d.content || d.message || d.summary || d.error || d.result || (typeof data === 'string' ? data : '')
  ).trim();
}

/**
 * 将过程事件合并进步骤列表：subagent_start 开卡，后续同 episode 的 chunk 挂到 children。
 */
export function mergeProcessStep(
  steps: ProcessStep[],
  ev: AgentStreamEvent
): ProcessStep[] {
  const step = streamEventToProcessStep(ev);
  if (!step) return steps;

  const d = (ev.data && typeof ev.data === 'object' ? ev.data : {}) as Record<string, any>;
  const meta = (d.metadata || {}) as Record<string, any>;
  const ep = meta.episode_number ?? d.episode_number;
  const fromSub = meta.from_subagent || d.agent_id;
  const event = String(ev.event || '');

  // 挂到对应子专家卡片
  if (fromSub && ep != null && event !== 'subagent_start' && event !== 'subagent_end') {
    const parentIdx = [...steps]
      .map((s, i) => ({ s, i }))
      .reverse()
      .find(({ s }) => s.kind === 'subagent' && String(s.agentId || '').includes(String(ep)))?.i;
    if (parentIdx != null && parentIdx >= 0) {
      const next = [...steps];
      const parent = { ...next[parentIdx] };
      const children = [...(parent.children || [])];
      children.push(step);
      // 累积正文预览到 detail
      if (event === 'llm_chunk' || event === 'message') {
        const chunk = textOf(d, ev.data);
        parent.detail = `${parent.detail || ''}${chunk}`.slice(-2000);
        parent.status = 'running';
      }
      parent.children = children;
      next[parentIdx] = parent;
      return next;
    }
  }

  if (event === 'subagent_end') {
    const idx = [...steps]
      .map((s, i) => ({ s, i }))
      .reverse()
      .find(
        ({ s }) =>
          s.kind === 'subagent' &&
          (ep == null || String(s.agentId || '').includes(String(ep))) &&
          s.status === 'running'
      )?.i;
    if (idx != null && idx >= 0) {
      const next = [...steps];
      const prev = next[idx];
      next[idx] = {
        ...prev,
        status: d.success === false || meta.success === false ? 'error' : 'done',
        detail:
          d.preview ||
          d.error ||
          prev.detail ||
          (d.word_count != null ? `${d.word_count} 字` : prev.detail),
        title: d.title
          ? `第${ep ?? ''}集 · ${d.title}`.replace(/第集/, '本集')
          : prev.title,
      };
      return next;
    }
  }

  return [...steps, step];
}

export function streamEventToProcessStep(ev: AgentStreamEvent): ProcessStep | null {
  const { event, data, timestamp } = ev;
  const d = data && typeof data === 'object' ? (data as Record<string, any>) : { content: data };
  const meta = (d.metadata || {}) as Record<string, any>;
  const text = textOf(d, data);

  if (event === 'thinking' || event === 'thought') {
    return {
      id: nid('think'),
      kind: 'thinking',
      title: text.slice(0, 160) || '思考中…',
      detail: text.length > 160 ? text : undefined,
      status: 'done',
      timestamp,
    };
  }

  if (event === 'system' || event === 'progress') {
    const title = text.slice(0, 160) || (event === 'progress' ? '进度更新' : '系统事件');
    // 进度短句：标题前加「、」，方便时间线里竖排一眼扫过
    const isProgressLine =
      /^(开始|正在)/.test(title.trim()) ||
      title.trim().endsWith('...') ||
      title.trim().endsWith('…') ||
      Boolean(d.metadata?.stage || meta.stage);
    return {
      id: nid(event === 'progress' ? 'prog' : 'sys'),
      kind: 'system',
      title: isProgressLine && !title.startsWith('、') ? `、${title}` : title,
      detail: text.length > 160 ? text : undefined,
      status: 'done',
      timestamp,
    };
  }

  if (event === 'tool_start' || event === 'tool_processing') {
    const tool = d.tool_name || d.name || d.tool || 'tool';
    return {
      id: nid('tool'),
      kind: 'tool',
      title: event === 'tool_start' ? `调用 ${tool}` : `${tool} 执行中…`,
      detail: d.tool_input ? JSON.stringify(d.tool_input, null, 2) : text || undefined,
      status: 'running',
      toolName: String(tool),
      timestamp,
    };
  }

  if (event === 'tool_complete' || event === 'tool_result' || event === 'tool' || event === 'tool_call' || event === 'tool_return') {
    const tool = d.tool_name || d.name || d.tool || meta.tool_name || 'tool';
    const out = d.tool_output || d.output || d.result || text;
    return {
      id: nid('toolr'),
      kind: event === 'tool_call' ? 'tool' : 'tool_result',
      title: event === 'tool_call' ? `调用 ${tool}` : `${tool} 完成`,
      detail: typeof out === 'string' ? out.slice(0, 2000) : JSON.stringify(out, null, 2).slice(0, 2000),
      status: d.error ? 'error' : event === 'tool_call' ? 'running' : 'done',
      toolName: String(tool),
      timestamp,
    };
  }

  if (event === 'subagent' || event === 'subagent_start') {
    const ep = d.episode_number ?? meta.episode_number;
    const agentId = d.agent_id || meta.agent_id || 'subagent';
    const title =
      d.title ||
      (ep != null ? `第${ep}集 · ${agentId}` : text.slice(0, 160)) ||
      `子专家 ${agentId}`;
    return {
      id: nid('sub'),
      kind: 'subagent',
      title: String(title),
      detail: d.task ? String(d.task) : text.length > 160 ? text : undefined,
      status: 'running',
      agentId: ep != null ? `${agentId}:ep${ep}` : String(agentId),
      timestamp,
      children: [],
    };
  }

  if (event === 'subagent_end') {
    const ep = d.episode_number ?? meta.episode_number;
    const agentId = d.agent_id || meta.agent_id || 'subagent';
    const ok = d.success !== false && meta.success !== false;
    return {
      id: nid('subend'),
      kind: 'subagent',
      title:
        ep != null
          ? `第${ep}集 ${ok ? '完成' : '失败'}${d.title ? ` · ${d.title}` : ''}`
          : text.slice(0, 160) || `子专家结束 · ${agentId}`,
      detail: d.preview || d.error || (d.word_count != null ? `${d.word_count} 字` : undefined),
      status: ok ? 'done' : 'error',
      agentId: ep != null ? `${agentId}:ep${ep}` : String(agentId),
      timestamp,
    };
  }

  if (event === 'handoff') {
    return {
      id: nid('ho'),
      kind: 'handoff',
      title: text.slice(0, 160) || `交接 → ${d.to || d.to_agent || d.agent_id || '专家'}`,
      detail: text.length > 160 ? text : undefined,
      status: 'done',
      agentId: d.to || d.to_agent || d.agent_id,
      timestamp,
    };
  }

  if (event === 'composition' || event === 'composition_progress' || event === 'agent_decision') {
    const msg =
      text ||
      d.message ||
      (typeof d === 'object' ? JSON.stringify(d, null, 2).slice(0, 800) : '');
    return {
      id: nid('comp'),
      kind: event === 'agent_decision' ? 'info' : 'composition',
      title: String(msg).slice(0, 160) || (event === 'composition' ? '组合专家' : '路由决策'),
      detail: String(msg).length > 160 ? String(msg) : undefined,
      status: 'done',
      timestamp,
    };
  }

  if (event === 'error') {
    return {
      id: nid('err'),
      kind: 'error',
      title: text.slice(0, 160) || '执行出错',
      detail: text.length > 160 ? text : undefined,
      status: 'error',
      timestamp,
    };
  }

  if (event === 'billing') {
    return {
      id: nid('bill'),
      kind: 'info',
      title: text || '计费',
      status: 'done',
      timestamp,
    };
  }

  // 子专家正文 chunk：作为独立 info（mergeProcessStep 会尝试挂到父卡）
  if (event === 'llm_chunk' && meta.from_subagent) {
    return {
      id: nid('subchunk'),
      kind: 'info',
      title: text.slice(0, 80) || '…',
      detail: text,
      status: 'running',
      agentId: meta.from_subagent,
      timestamp,
    };
  }

  if (text && !['llm_chunk', 'message', 'content', 'token', 'delta', 'complete', 'done', 'end'].includes(String(event))) {
    return {
      id: nid('info'),
      kind: 'info',
      title: text.slice(0, 160),
      detail: text.length > 160 ? text : undefined,
      status: 'done',
      timestamp,
    };
  }

  return null;
}
