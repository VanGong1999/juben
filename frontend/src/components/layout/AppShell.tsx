/**
 * AI影视 — 杂志编辑风产品壳
 */

import { ReactNode, useState } from 'react';
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom';
import {
  Home,
  Clapperboard,
  Brain,
  Sparkles,
  Wrench,
  Settings,
  Search,
  LogOut,
  Menu,
  X,
  ChevronDown,
  PenLine,
  Users,
  Film,
  MoreHorizontal,
  Globe,
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { useUIStore } from '@/store/uiStore';
import { useNotificationStore } from '@/store/notificationStore';
import { useSettingsStore } from '@/store/settingsStore';
import { useI18n } from '@/i18n';
import clsx from 'clsx';

const PRIMARY_NAV = [
  { to: '/', labelKey: 'nav.home', icon: Home, end: true },
  { to: '/dramas', labelKey: 'nav.works', icon: Clapperboard },
  { to: '/studio', labelKey: 'nav.studio', icon: PenLine },
  { to: '/experts', labelKey: 'nav.experts', icon: Users },
];

const MORE_LINKS = [
  { to: '/memory', labelKey: 'nav.memory', icon: Brain },
  { to: '/skills', labelKey: 'nav.skills', icon: Sparkles },
  { to: '/toolbox', labelKey: 'nav.toolbox', icon: Wrench },
];

type AppShellProps = {
  children: ReactNode;
  title?: string;
  subtitle?: string;
  actions?: ReactNode;
};

export default function AppShell({ children, title, subtitle, actions }: AppShellProps) {
  const { user, logout, isAdmin } = useAuthStore();
  const { setSearchOpen } = useUIStore();
  const { success } = useNotificationStore();
  const { setLanguage } = useSettingsStore();
  const { t, language } = useI18n();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const moreActive =
    location.pathname.startsWith('/toolbox') ||
    location.pathname.startsWith('/memory') ||
    location.pathname.startsWith('/skills');
  const [moreOpen, setMoreOpen] = useState(moreActive);
  const showAdmin = isAdmin();

  const handleLogout = async () => {
    await logout();
    success(t('toast.signedOut'), t('toast.welcomeBack'));
    navigate('/login');
  };

  const NavItems = ({ onNavigate }: { onNavigate?: () => void }) => (
    <nav className="flex flex-col gap-0.5 px-3">
      {PRIMARY_NAV.map(({ to, labelKey, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          onClick={onNavigate}
          className={({ isActive }) =>
            clsx(
              'group flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-[12px] font-medium transition-colors',
              isActive
                ? 'bg-atelier-teal text-white'
                : 'text-ink-muted hover:bg-pearl-soft hover:text-ink'
            )
          }
        >
          <Icon className="w-3.5 h-3.5 shrink-0 opacity-90" />
          <span>{t(labelKey)}</span>
        </NavLink>
      ))}

      <button
        type="button"
        onClick={() => setMoreOpen((v) => !v)}
        className={clsx(
          'flex items-center justify-between px-2.5 py-2 mt-3 rounded-lg text-[12px] font-medium transition-colors',
          moreActive ? 'text-atelier-teal bg-atelier-teal-soft/60' : 'text-ink-muted hover:bg-pearl-soft hover:text-ink'
        )}
      >
        <span className="inline-flex items-center gap-3">
          <MoreHorizontal className="w-4 h-4" />
          {t('nav.more')}
        </span>
        <ChevronDown className={clsx('w-3.5 h-3.5 transition-transform', moreOpen && 'rotate-180')} />
      </button>
      {moreOpen && (
        <div className="ml-3 pl-3 border-l border-pearl-line space-y-0.5 mb-2">
          {MORE_LINKS.map(({ to, labelKey, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/toolbox'}
              onClick={onNavigate}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-2 px-2 py-1.5 rounded-md text-xs transition-colors',
                  isActive ? 'text-atelier-teal font-semibold bg-atelier-teal-soft' : 'text-ink-muted hover:text-ink'
                )
              }
            >
              <Icon className="w-3.5 h-3.5" />
              {t(labelKey)}
            </NavLink>
          ))}
        </div>
      )}

      <NavLink
        to="/settings"
        onClick={onNavigate}
        className={({ isActive }) =>
          clsx(
            'flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-[12px] font-medium transition-colors mt-2',
            isActive ? 'bg-atelier-teal text-white' : 'text-ink-muted hover:bg-pearl-soft hover:text-ink'
          )
        }
      >
        <Settings className="w-3.5 h-3.5" />
        {t('nav.settings')}
      </NavLink>
      {showAdmin && (
        <NavLink
          to="/admin"
          onClick={onNavigate}
          className={({ isActive }) =>
            clsx(
              'flex items-center gap-3 px-3 py-2.5 rounded-lg text-[13px] font-medium',
              isActive ? 'bg-atelier-teal text-white' : 'text-ink-muted hover:bg-pearl-soft'
            )
          }
        >
          {t('nav.admin')}
        </NavLink>
      )}
    </nav>
  );

  return (
    <div className="min-h-screen flex relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 -z-0">
        <div className="absolute -top-32 -left-24 w-[480px] h-[480px] rounded-full bg-atelier-teal/10 blur-3xl" />
        <div className="absolute top-1/4 -right-20 w-[420px] h-[420px] rounded-full bg-atelier-gold/10 blur-3xl" />
      </div>
      <aside className="hidden lg:flex w-[172px] shrink-0 flex-col border-r border-white/50 bg-white/55 backdrop-blur-xl backdrop-saturate-150 relative z-10">
        <Link to="/" className="flex items-center gap-2.5 px-4 py-4 group">
          <div className="relative w-8 h-8 rounded-lg bg-atelier-teal flex items-center justify-center shadow-atelier group-hover:shadow-atelier-lg transition-shadow duration-300">
            <Film className="w-4 h-4 text-white" />
          </div>
          <div>
            <div className="font-display text-[1.15rem] font-semibold text-ink leading-none tracking-tight">
              AI影视
            </div>
            <div className="text-[9px] text-ink-faint tracking-[0.14em] uppercase mt-0.5">Editorial</div>
          </div>
        </Link>

        <div className="flex-1 overflow-y-auto pb-4">
          <NavItems />
        </div>

        <div className="mx-3 mb-3 px-3 py-2.5 border-t border-pearl-line">
          <div className="text-[11px] text-ink-faint leading-relaxed tracking-wide">
            {t('nav.tagline')}
          </div>
        </div>

        <div className="px-4 py-4 border-t border-pearl-line">
          <div className="text-xs text-ink-faint truncate">{user?.username || t('nav.creator')}</div>
          <button
            type="button"
            onClick={handleLogout}
            className="mt-2 flex items-center gap-2 text-xs text-ink-muted hover:text-atelier-teal transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
            {t('nav.signOut')}
          </button>
        </div>
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-ink/30" onClick={() => setMobileOpen(false)} />
          <aside className="absolute left-0 top-0 h-full w-72 bg-pearl-card shadow-atelier-lg flex flex-col animate-slide-up">
            <div className="flex items-center justify-between px-4 py-4 border-b border-pearl-line">
              <span className="font-display text-xl font-semibold text-ink">AI影视</span>
              <button type="button" onClick={() => setMobileOpen(false)} className="p-2 rounded-lg hover:bg-pearl-soft">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="pt-2">
              <NavItems onNavigate={() => setMobileOpen(false)} />
            </div>
          </aside>
        </div>
      )}

      <div className="flex-1 flex flex-col min-w-0 relative z-10">
        <header className="sticky top-0 z-30 flex items-center justify-between gap-4 px-4 sm:px-6 py-2.5 border-b border-white/50 bg-white/60 backdrop-blur-xl backdrop-saturate-150">
          <div className="flex items-center gap-3 min-w-0">
            <button
              type="button"
              className="lg:hidden p-2 rounded-lg hover:bg-pearl-soft"
              onClick={() => setMobileOpen(true)}
            >
              <Menu className="w-5 h-5 text-ink" />
            </button>
            <div className="min-w-0">
              {title ? (
                <>
                  <h1 className="font-display text-[1.4rem] font-semibold text-ink truncate leading-none">
                    {title}
                  </h1>
                  {subtitle && <p className="text-[11px] text-ink-muted truncate mt-1">{subtitle}</p>}
                </>
              ) : (
                <h1 className="font-display text-[1.75rem] font-semibold text-ink leading-none">AI影视</h1>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {actions}
            <button
              type="button"
              onClick={() => setLanguage(language === 'zh' ? 'en' : 'zh')}
              title={t('settings.language')}
              className="hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-pearl-line text-xs text-ink-muted hover:border-atelier-teal/40 hover:text-atelier-teal bg-white"
            >
              <Globe className="w-3.5 h-3.5" />
              {language === 'zh' ? 'EN' : '中'}
            </button>
            <button
              type="button"
              onClick={() => setSearchOpen(true)}
              className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg border border-pearl-line text-xs text-ink-muted hover:border-atelier-teal/40 hover:text-atelier-teal bg-white"
            >
              <Search className="w-3.5 h-3.5" />
              {t('nav.search')}
              <kbd className="ml-0.5 px-1.5 py-0.5 rounded bg-pearl-soft font-mono text-[10px]">⌘K</kbd>
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto animate-fade-in">{children}</main>
      </div>
    </div>
  );
}
