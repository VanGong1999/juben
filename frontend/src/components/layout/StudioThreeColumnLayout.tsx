/**
 * 三栏毛玻璃工作室布局
 */

import { ReactNode, useState } from 'react';
import clsx from 'clsx';
import { PanelLeftClose, PanelLeftOpen, MessageSquare, FileText } from 'lucide-react';
import { useI18n } from '@/i18n';

type Props = {
  header: ReactNode;
  blueprint: ReactNode;
  workspace: ReactNode;
  chat: ReactNode;
};

export default function StudioThreeColumnLayout({ header, blueprint, workspace, chat }: Props) {
  const { t } = useI18n();
  const [leftOpen, setLeftOpen] = useState(true);
  const [mobileTab, setMobileTab] = useState<'blueprint' | 'workspace' | 'chat'>('workspace');

  return (
    <div className="flex flex-col h-screen relative overflow-hidden">
      {/* Ambient blobs for glass depth */}
      <div className="pointer-events-none absolute inset-0 -z-0">
        <div className="absolute -top-24 -left-20 w-[420px] h-[420px] rounded-full bg-atelier-teal/10 blur-3xl animate-float" />
        <div
          className="absolute top-1/3 -right-16 w-[380px] h-[380px] rounded-full bg-atelier-gold/12 blur-3xl animate-float"
          style={{ animationDelay: '1.2s' }}
        />
        <div className="absolute bottom-0 left-1/3 w-[320px] h-[320px] rounded-full bg-atelier-teal/6 blur-3xl" />
      </div>

      <header className="flex-shrink-0 z-20 glass-chrome border-b border-white/50">{header}</header>

      <div className="lg:hidden flex gap-1 p-2 border-b border-white/40 bg-white/50 backdrop-blur-xl z-10">
        {(
          [
            { id: 'blueprint' as const, label: t('studio.layout.blueprint'), icon: PanelLeftOpen },
            { id: 'workspace' as const, label: t('studio.layout.canvas'), icon: FileText },
            { id: 'chat' as const, label: t('studio.layout.chat'), icon: MessageSquare },
          ] as const
        ).map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => setMobileTab(id)}
            className={clsx(
              'flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl text-xs font-semibold transition-all duration-200',
              mobileTab === id
                ? 'bg-atelier-teal text-white shadow-atelier'
                : 'text-ink-muted hover:bg-white/70'
            )}
          >
            <Icon className="w-3.5 h-3.5" />
            {label}
          </button>
        ))}
      </div>

      <div className="relative z-10 flex flex-1 overflow-hidden gap-0 lg:gap-3 lg:p-3 lg:pt-2">
        <div
          className={clsx(
            'h-full flex-shrink-0 transition-all duration-300 ease-out overflow-hidden',
            'hidden lg:block',
            leftOpen ? 'w-[272px] xl:w-[292px]' : 'w-0',
            mobileTab === 'blueprint' && '!block w-full lg:w-[292px]',
            leftOpen &&
              'lg:rounded-2xl lg:border lg:border-white/55 lg:shadow-[0_8px_32px_rgba(20,24,31,0.06)] lg:bg-white/55 lg:backdrop-blur-xl lg:backdrop-saturate-150'
          )}
        >
          {leftOpen && <div className="h-full overflow-hidden animate-fade-in">{blueprint}</div>}
        </div>

        <main
          className={clsx(
            'relative h-full min-w-0 flex-1 overflow-hidden transition-all duration-300',
            'lg:rounded-2xl lg:border lg:border-white/55 lg:shadow-[0_8px_32px_rgba(20,24,31,0.06)] lg:bg-white/60 lg:backdrop-blur-xl lg:backdrop-saturate-150',
            mobileTab !== 'workspace' && 'hidden lg:block'
          )}
        >
          <button
            type="button"
            onClick={() => setLeftOpen((v) => !v)}
            className="hidden lg:flex absolute left-3 top-3.5 z-20 p-2 rounded-xl bg-white/70 border border-white/60 text-ink-muted hover:text-atelier-teal hover:border-atelier-teal/40 shadow-atelier backdrop-blur-md transition-all duration-200"
            title={leftOpen ? t('studio.layout.collapseBlueprint') : t('studio.layout.expandBlueprint')}
          >
            {leftOpen ? <PanelLeftClose className="w-4 h-4" /> : <PanelLeftOpen className="w-4 h-4" />}
          </button>
          <div className="h-full overflow-hidden">{workspace}</div>
        </main>

        <aside
          className={clsx(
            'h-full flex-shrink-0 overflow-hidden transition-all duration-300',
            'hidden lg:block w-[360px] xl:w-[400px]',
            'lg:rounded-2xl lg:border lg:border-white/55 lg:shadow-[0_8px_32px_rgba(20,24,31,0.06)] lg:bg-white/55 lg:backdrop-blur-xl lg:backdrop-saturate-150',
            mobileTab === 'chat' && '!block w-full lg:w-[400px]'
          )}
        >
          {chat}
        </aside>
      </div>
    </div>
  );
}
