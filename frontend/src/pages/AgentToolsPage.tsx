/**
 * Agent 工具目录 — Prebuilt / External，可试跑简单参数
 */

import { useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowLeft, Play, Shield } from 'lucide-react';
import AppShell from '@/components/layout/AppShell';
import { groupToolsByCategory, getToolByName, type ToolDefinitionUI } from '@/config/tools';
import { executeTool } from '@/services/toolService';
import clsx from 'clsx';
import { useI18n } from '@/i18n';

export default function AgentToolsPage() {
  const [params] = useSearchParams();
  const { t } = useI18n();
  const focus = params.get('tool') || '';
  const groups = groupToolsByCategory();
  const [selected, setSelected] = useState<string>(focus || 'web_search');
  const [paramJson, setParamJson] = useState('{\n  "query": "2025短剧市场趋势"\n}');
  const [running, setRunning] = useState(false);
  const [output, setOutput] = useState<string>('');

  const tool = useMemo(() => getToolByName(selected), [selected]);

  const pick = (t: ToolDefinitionUI) => {
    setSelected(t.name);
    const props = t.parameters.properties || {};
    const sample: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(props)) {
      if (v.default !== undefined) sample[k] = v.default;
      else if (v.type === 'string') sample[k] = '';
      else if (v.type === 'integer') sample[k] = 0;
      else if (v.type === 'boolean') sample[k] = false;
    }
    if (t.name === 'web_search') sample.query = '2025短剧市场趋势';
    if (t.name === 'date') delete sample.timezone;
    setParamJson(JSON.stringify(sample, null, 2));
    setOutput('');
  };

  const run = async () => {
    if (!tool) return;
    setRunning(true);
    setOutput('');
    try {
      const parameters = JSON.parse(paramJson);
      const res = await executeTool({ tool_name: tool.name, parameters });
      const text =
        (res as any)?.result?.llm_text ||
        JSON.stringify(res, null, 2);
      setOutput(typeof text === 'string' ? text : JSON.stringify(text, null, 2));
    } catch (e: any) {
      setOutput(e?.message || String(e));
    } finally {
      setRunning(false);
    }
  };

  return (
    <AppShell
      title={t('toolbox.agentTools.title')}
      subtitle={t('toolbox.agentTools.subtitle')}
      actions={
        <Link to="/experts" className="btn btn-ghost btn-sm inline-flex items-center gap-1">
          <ArrowLeft className="w-3.5 h-3.5" />
          {t('toolbox.agentTools.experts')}
        </Link>
      }
    >
      <div className="px-4 sm:px-8 py-8 max-w-5xl mx-auto grid lg:grid-cols-[1fr_1.1fr] gap-8">
        <div className="space-y-8">
          {groups.map((g) => (
            <section key={g.category}>
              <h3 className="font-display text-lg font-semibold text-ink mb-1">{g.label}</h3>
              <p className="text-[11px] text-ink-faint mb-3 uppercase tracking-wider">
                {t('toolbox.agentTools.toolCount', { count: g.tools.length })}
              </p>
              <ul className="border-t border-pearl-line">
                {g.tools.map((tool) => (
                  <li key={tool.name}>
                    <button
                      type="button"
                      onClick={() => pick(tool)}
                      className={clsx(
                        'w-full text-left flex items-start gap-3 py-3 border-b border-pearl-line transition-colors',
                        selected === tool.name ? 'bg-paper-cool/60' : 'hover:bg-paper-cool/30'
                      )}
                    >
                      <span className="text-base w-7 shrink-0">{tool.icon}</span>
                      <div className="min-w-0 flex-1">
                        <div className="text-sm font-medium text-ink">{tool.label}</div>
                        <p className="text-xs text-ink-muted line-clamp-1">{tool.description}</p>
                        <code className="text-[10px] font-mono text-ink-faint">{tool.name}</code>
                      </div>
                      {tool.requiresSandbox && (
                        <Shield className="w-3.5 h-3.5 text-ink-faint shrink-0 mt-1" aria-label={t('toolbox.agentTools.sandbox')} />
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>

        <div className="lg:sticky lg:top-6 self-start space-y-4 border border-pearl-line rounded-xl p-5 bg-paper/80">
          {tool ? (
            <>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xl">{tool.icon}</span>
                  <h3 className="font-display text-xl font-semibold text-ink">{tool.label}</h3>
                </div>
                <p className="text-sm text-ink-muted mt-1">{tool.description}</p>
                <div className="mt-2 flex flex-wrap gap-2 text-[10px] uppercase tracking-wider text-ink-faint">
                  <span>{tool.category}</span>
                  {tool.requiresSandbox && <span>{t('toolbox.agentTools.sandbox')}</span>}
                  {tool.dangerous && <span className="text-studio-amber">{t('toolbox.agentTools.dangerous')}</span>}
                  {tool.legacyAgentId && <span>{t('toolbox.agentTools.legacy')}：{tool.legacyAgentId}</span>}
                </div>
              </div>
              <div>
                <label className="text-xs text-ink-muted">parameters (JSON)</label>
                <textarea
                  className="input mt-1 font-mono text-xs min-h-[140px]"
                  value={paramJson}
                  onChange={(e) => setParamJson(e.target.value)}
                />
              </div>
              <button
                type="button"
                className="btn btn-primary btn-sm inline-flex items-center gap-1.5"
                disabled={running}
                onClick={run}
              >
                <Play className="w-3.5 h-3.5" />
                {running ? t('toolbox.agentTools.running') : t('toolbox.agentTools.run')}
              </button>
              {output && (
                <pre className="text-xs whitespace-pre-wrap bg-ink/[0.03] rounded-lg p-3 max-h-80 overflow-auto text-ink-muted">
                  {output}
                </pre>
              )}
            </>
          ) : (
            <p className="text-sm text-ink-muted">{t('toolbox.agentTools.selectTool')}</p>
          )}
        </div>
      </div>
    </AppShell>
  );
}
