/**
 * Skills 管理
 */

import { useEffect, useState } from 'react';
import { Sparkles, ToggleLeft, ToggleRight, X, FileText } from 'lucide-react';
import AppShell from '@/components/layout/AppShell';
import StreamingText from '@/components/chat/StreamingText';
import { listSkills, getSkill } from '@/services/dramaService';
import clsx from 'clsx';
import { useI18n } from '@/i18n';

type Skill = { id: string; name: string; description: string; enabled?: boolean; category?: string };

type SkillDetail = Omit<Skill, 'description'> & {
  description?: string;
  summary?: string;
  body?: string;
  source?: string;
  priority?: number;
};

const FALLBACK: Skill[] = [
  {
    id: 'hook-3s',
    name: '黄金三秒 / 冷开场',
    description: '1–3 秒硬钩 + 前 30 秒建冲突；每集当第一集写。',
    enabled: true,
    category: '节奏',
  },
  {
    id: 'emotion-first',
    name: '情绪价值第一',
    description: '每集认领主情绪；压抑→释放；信息为情绪服务。',
    enabled: true,
    category: '叙事',
  },
  {
    id: 'satisfaction-payoff',
    name: '爽点矩阵',
    description: '身份碾压 / 打脸 / 逆袭 / 情感爆发 / 智斗，按强度投放。',
    enabled: true,
    category: '叙事',
  },
  {
    id: 'cliffhanger',
    name: '集末钩子与付费卡点',
    description: '五种集末钩 + 情绪峰值卡点，驱动续看与付费。',
    enabled: true,
    category: '商业',
  },
  {
    id: 'episode-rhythm',
    name: '单集节奏与全剧波形',
    description: '微型三幕 + 起势/攀升/风暴/决战四段波形。',
    enabled: true,
    category: '节奏',
  },
  {
    id: 'character-voice',
    name: '人设语气一致',
    description: '语域/口头禅/禁语；单句口语化；禁止 OOC。',
    enabled: true,
    category: '人物',
  },
  {
    id: 'beat-dialogue',
    name: '节拍流写戏',
    description: '动作⇄台词交替；前 3 拍冷开场；爽点必须有戏认领。',
    enabled: true,
    category: '叙事',
  },
  {
    id: 'villain-ladder',
    name: '四层反派阶梯',
    description: '炮灰→中反派→大 Boss→隐藏反派递进设计。',
    enabled: true,
    category: '人物',
  },
];

export default function SkillsPage() {
  const { t } = useI18n();
  const [skills, setSkills] = useState<Skill[]>(FALLBACK);
  const [enabled, setEnabled] = useState<Record<string, boolean>>({});
  const [activeSkill, setActiveSkill] = useState<SkillDetail | null>(null);
  const [loadingSkill, setLoadingSkill] = useState(false);

  useEffect(() => {
    listSkills()
      .then((res) => {
        if (res.skills?.length) {
          setSkills(res.skills);
          const map: Record<string, boolean> = {};
          res.skills.forEach((s) => {
            map[s.id] = s.enabled !== false;
          });
          setEnabled(map);
        } else {
          const map: Record<string, boolean> = {};
          FALLBACK.forEach((s) => {
            map[s.id] = true;
          });
          setEnabled(map);
        }
      })
      .catch(() => {
        const map: Record<string, boolean> = {};
        FALLBACK.forEach((s) => {
          map[s.id] = true;
        });
        setEnabled(map);
      });
  }, []);

  const toggle = (id: string) => {
    setEnabled((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const openSkill = async (id: string) => {
    setLoadingSkill(true);
    setActiveSkill(null);
    try {
      const res = await getSkill(id);
      if (res.success && res.skill) setActiveSkill(res.skill);
    } catch {
      setActiveSkill(null);
    } finally {
      setLoadingSkill(false);
    }
  };

  return (
    <AppShell title="Skills" subtitle={t('admin.skills.subtitle')}>
      <div className="p-4 sm:p-8 max-w-5xl mx-auto space-y-6">
        <div className="atelier-hero p-6 flex items-start gap-4">
          <div className="w-12 h-12 rounded-2xl bg-atelier-gold-soft flex items-center justify-center shrink-0">
            <Sparkles className="w-6 h-6 text-atelier-gold" />
          </div>
          <div>
            <h2 className="font-display text-2xl font-semibold text-ink">{t('admin.skills.heroTitle')}</h2>
            <p className="text-sm text-ink-muted mt-1 leading-relaxed">
              {t('admin.skills.heroDesc')}
            </p>
          </div>
        </div>

        <div className="grid sm:grid-cols-2 gap-4">
          {skills.map((s, i) => {
            const on = enabled[s.id] !== false;
            return (
              <div
                key={s.id}
                className="card group p-5 animate-stagger-in cursor-pointer hover:border-studio-teal/40 transition-colors"
                style={{ animationDelay: `${i * 50}ms` }}
                onClick={() => openSkill(s.id)}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    {(s as any).category && (
                      <span className="badge badge-default mb-2">{(s as any).category}</span>
                    )}
                    <h3 className="font-display font-semibold text-ink">{s.name}</h3>
                    <p className="mt-2 text-sm text-ink-muted leading-relaxed">{s.description}</p>
                  </div>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      toggle(s.id);
                    }}
                    className={clsx('shrink-0 transition-colors', on ? 'text-studio-teal' : 'text-ink-faint')}
                    title={on ? t('admin.skills.enabled') : t('admin.skills.disabled')}
                  >
                    {on ? <ToggleRight className="w-8 h-8" /> : <ToggleLeft className="w-8 h-8" />}
                  </button>
                </div>
                <div className="mt-3 flex items-center gap-1 text-xs text-studio-teal opacity-0 group-hover:opacity-100 transition-opacity">
                  <FileText className="w-3.5 h-3.5" />
                  {t('admin.skills.viewFull')}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {(activeSkill || loadingSkill) && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-ink/25 backdrop-blur-[2px]" onClick={() => setActiveSkill(null)} />
          <aside className="relative w-full max-w-xl h-full bg-white border-l border-pearl-line shadow-atelier-lg flex flex-col animate-slide-up overflow-hidden">
            <div className="flex items-start justify-between gap-3 px-5 py-4 border-b border-pearl-line">
              <div className="min-w-0">
                {activeSkill?.category && (
                  <span className="badge badge-default mb-1">{activeSkill.category}</span>
                )}
                <h3 className="font-display text-xl font-semibold text-ink mt-1 truncate">
                  {loadingSkill ? t('admin.skills.loading') : activeSkill?.name}
                </h3>
                {activeSkill?.source && (
                  <p className="text-[11px] text-ink-muted mt-1 line-clamp-2">{activeSkill.source}</p>
                )}
              </div>
              <button
                type="button"
                className="p-2 rounded-lg hover:bg-pearl-soft text-ink-muted shrink-0"
                onClick={() => setActiveSkill(null)}
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto px-5 py-4">
              {loadingSkill ? (
                <div className="space-y-2">
                  <div className="h-4 bg-pearl-soft animate-pulse rounded w-3/4" />
                  <div className="h-4 bg-pearl-soft animate-pulse rounded w-full" />
                  <div className="h-4 bg-pearl-soft animate-pulse rounded w-5/6" />
                </div>
              ) : (
                <StreamingText content={activeSkill?.body || activeSkill?.description || ''} />
              )}
            </div>
          </aside>
        </div>
      )}
    </AppShell>
  );
}
