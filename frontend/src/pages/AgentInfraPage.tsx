/**
 * Agent Infra 控制台 — 能力矩阵 / 队列 / Metrics / Eval
 */

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Activity, Play, RefreshCw } from 'lucide-react';
import AppShell from '@/components/layout/AppShell';
import {
  fetchCapabilities,
  fetchAgentMetrics,
  fetchQueueStats,
  fetchRedisQueueStats,
  fetchSecretsCheck,
  fetchDemoDag,
  runEvalSuite,
} from '@/services/agentInfraService';
import clsx from 'clsx';
import { useI18n } from '@/i18n';

export default function AgentInfraPage() {
  const { t } = useI18n();
  const [caps, setCaps] = useState<Record<string, { status: string }> | null>(null);
  const [metrics, setMetrics] = useState<Record<string, unknown> | null>(null);
  const [queue, setQueue] = useState<Record<string, unknown> | null>(null);
  const [redisQ, setRedisQ] = useState<Record<string, unknown> | null>(null);
  const [secrets, setSecrets] = useState<Record<string, unknown> | null>(null);
  const [dag, setDag] = useState<Record<string, unknown> | null>(null);
  const [evalResult, setEvalResult] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const refresh = async () => {
    setLoading(true);
    setError('');
    try {
      const [c, m, q, rq, s, d] = await Promise.all([
        fetchCapabilities(),
        fetchAgentMetrics(),
        fetchQueueStats(),
        fetchRedisQueueStats().catch(() => ({ available: false })),
        fetchSecretsCheck(),
        fetchDemoDag(),
      ]);
      setCaps(c);
      setMetrics(m);
      setQueue(q);
      setRedisQ(rq);
      setSecrets(s);
      setDag(d);
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const runEval = async () => {
    setLoading(true);
    try {
      const r = await runEvalSuite();
      setEvalResult(r);
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell
      title={t('toolbox.agentInfra.title')}
      subtitle={t('toolbox.agentInfra.subtitle')}
      actions={
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={refresh}
            className="inline-flex items-center gap-1.5 rounded-md border border-stone-300 bg-white px-3 py-1.5 text-sm text-stone-700 hover:bg-stone-50"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            {t('toolbox.refresh')}
          </button>
          <button
            type="button"
            onClick={runEval}
            className="inline-flex items-center gap-1.5 rounded-md bg-stone-900 px-3 py-1.5 text-sm text-white hover:bg-stone-800"
          >
            <Play className="h-3.5 w-3.5" />
            {t('toolbox.agentInfra.runEval')}
          </button>
        </div>
      }
    >
      <div className="mx-auto max-w-5xl space-y-8 px-4 py-6">
        <Link
          to="/toolbox/agent-tools"
          className="inline-flex items-center gap-1 text-sm text-stone-500 hover:text-stone-800"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          {t('toolbox.agentInfra.agentTools')}
        </Link>

        {error && (
          <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        )}

        <section>
          <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold text-stone-900">
            <Activity className="h-4 w-4" />
            {t('toolbox.agentInfra.capabilities')}
            {loading && <span className="text-xs font-normal text-stone-400">{t('toolbox.agentInfra.loading')}</span>}
          </h2>
          <div className="grid gap-2 sm:grid-cols-2">
            {caps &&
              Object.entries(caps).map(([key, val]) => (
                <div
                  key={key}
                  className="flex items-start justify-between gap-3 border-b border-stone-200 py-2"
                >
                  <div>
                    <div className="font-mono text-xs text-stone-500">{key}</div>
                    <div className="text-sm text-stone-800">
                      {typeof val === 'object' ? JSON.stringify(val).slice(0, 120) : String(val)}
                    </div>
                  </div>
                  <span
                    className={clsx(
                      'shrink-0 rounded px-2 py-0.5 text-xs font-medium',
                      val?.status === 'ok'
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-amber-100 text-amber-800'
                    )}
                  >
                    {val?.status || '—'}
                  </span>
                </div>
              ))}
          </div>
        </section>

        <section className="grid gap-6 md:grid-cols-2">
          <div>
            <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-stone-500">
              {t('toolbox.agentInfra.memoryQueue')}
            </h3>
            <pre className="overflow-auto rounded-md bg-stone-950 p-3 text-xs text-stone-100">
              {JSON.stringify(queue, null, 2)}
            </pre>
          </div>
          <div>
            <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-stone-500">
              Redis Streams
            </h3>
            <pre className="overflow-auto rounded-md bg-stone-950 p-3 text-xs text-stone-100">
              {JSON.stringify(redisQ, null, 2)}
            </pre>
          </div>
          <div>
            <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-stone-500">
              Metrics
            </h3>
            <pre className="overflow-auto rounded-md bg-stone-950 p-3 text-xs text-stone-100">
              {JSON.stringify(metrics, null, 2)}
            </pre>
          </div>
          <div>
            <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-stone-500">
              {t('toolbox.agentInfra.secrets')}
            </h3>
            <pre className="overflow-auto rounded-md bg-stone-950 p-3 text-xs text-stone-100">
              {JSON.stringify(secrets, null, 2)}
            </pre>
          </div>
        </section>

        <section>
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-stone-500">
            {t('toolbox.agentInfra.dag')}
          </h3>
          <pre className="overflow-auto rounded-md bg-stone-950 p-3 text-xs text-stone-100">
            {JSON.stringify(dag, null, 2)}
          </pre>
        </section>

        {evalResult && (
          <section>
            <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-stone-500">
              {t('toolbox.agentInfra.evalResult')}
            </h3>
            <pre className="overflow-auto rounded-md bg-stone-950 p-3 text-xs text-stone-100">
              {JSON.stringify(evalResult, null, 2)}
            </pre>
          </section>
        )}
      </div>
    </AppShell>
  );
}
