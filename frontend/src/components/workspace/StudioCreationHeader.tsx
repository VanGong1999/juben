/**
 * 工作室顶栏 — 品牌、当前作品、专家、作品库
 */

import { Link, useNavigate } from 'react-router-dom';
import {
  Film,
  Search,
  Settings,
  HelpCircle,
  LogOut,
  Clapperboard,
  Home,
  Square,
  ChevronRight,
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { useUIStore } from '@/store/uiStore';
import { useChat } from '@/hooks/useChat';
import { useAgents } from '@/hooks/useAgents';
import { useNotificationStore } from '@/store/notificationStore';
import { useSettingsStore } from '@/store/settingsStore';
import { ReactNode, useState } from 'react';
import { useI18n } from '@/i18n';

type Props = {
  onHelpClick?: () => void;
  dramaTitle?: string;
  dramaId?: string;
  extraActions?: ReactNode;
};

export default function StudioCreationHeader({
  onHelpClick,
  dramaTitle,
  dramaId,
  extraActions,
}: Props) {
  const { t } = useI18n();
  const { user, logout } = useAuthStore();
  const { setSettingsModalOpen, setSearchOpen } = useUIStore();
  const { isStreaming, stopStreaming } = useChat();
  const { activeAgentData } = useAgents();
  const { success } = useNotificationStore();
  const { model, modelProvider, apiKey } = useSettingsStore();
  const navigate = useNavigate();
  const [userOpen, setUserOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    success(t('toast.signedOut'), '');
    navigate('/login');
  };

  return (
    <div className="flex items-center justify-between gap-3 px-4 sm:px-5 py-2.5 bg-transparent">
      <div className="flex items-center gap-3 min-w-0">
        <Link to="/" className="flex items-center gap-2.5 shrink-0 group">
          <div className="w-9 h-9 rounded-lg bg-atelier-teal flex items-center justify-center shadow-atelier group-hover:scale-[1.03] transition-transform duration-200">
            <Film className="w-4 h-4 text-white" />
          </div>
          <div className="hidden md:block">
            <div className="font-display text-lg font-semibold text-ink leading-tight">AI影视</div>
            <div className="text-[10px] text-ink-faint tracking-[0.14em] uppercase">Studio</div>
          </div>
        </Link>

        <div className="hidden sm:flex items-center gap-1 text-xs text-ink-faint min-w-0">
          <ChevronRight className="w-3.5 h-3.5 shrink-0" />
          {dramaTitle ? (
            <span className="text-ink truncate max-w-[140px] font-medium">{dramaTitle}</span>
          ) : (
            <span className="text-ink-muted">{t('nav.studio')}</span>
          )}
          <ChevronRight className="w-3.5 h-3.5 shrink-0" />
          <span className="text-ink-muted truncate max-w-[140px]">
            {activeAgentData?.displayName || t('workspace.chooseExpert')}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
        {extraActions}
        <Link
          to="/"
          className="hidden lg:inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs text-ink-muted hover:bg-pearl-soft hover:text-ink"
          title={t('nav.home')}
        >
          <Home className="w-3.5 h-3.5" />
          {t('nav.home')}
        </Link>
        <Link
          to="/dramas"
          className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold text-atelier-teal bg-atelier-teal-soft border border-atelier-teal/15"
        >
          <Clapperboard className="w-3.5 h-3.5" />
          {t('studio.rail.worksLibrary')}
        </Link>
        {dramaId && (
          <Link
            to={`/studio/${dramaId}`}
            className="hidden xl:inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs text-ink-muted hover:bg-pearl-soft"
          >
            {t('studio.header.currentWork')}
          </Link>
        )}

        {isStreaming && (
          <button
            type="button"
            onClick={stopStreaming}
            className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs bg-atelier-gold-soft text-atelier-gold"
          >
            <Square className="w-3 h-3 fill-current" />
            {t('studio.stop')}
          </button>
        )}

        <button
          type="button"
          onClick={() => setSearchOpen(true)}
          className="p-2 rounded-lg text-ink-muted hover:bg-pearl-soft"
          title={t('studio.header.searchCmd')}
        >
          <Search className="w-4 h-4" />
        </button>
        <button
          type="button"
          onClick={onHelpClick}
          className="hidden sm:inline-flex p-2 rounded-lg text-ink-muted hover:bg-pearl-soft"
          title={t('studio.help')}
        >
          <HelpCircle className="w-4 h-4" />
        </button>
        <button
          type="button"
          onClick={() => setSettingsModalOpen(true)}
          className="hidden md:inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] text-ink-muted hover:bg-pearl-soft hover:text-ink max-w-[160px]"
          title={t('studio.header.modelSettings')}
        >
          <Settings className="w-3.5 h-3.5 shrink-0" />
          <span className="truncate font-mono">
            {modelProvider}/{model}
            {apiKey ? ' · Key' : ''}
          </span>
        </button>
        <button
          type="button"
          onClick={() => setSettingsModalOpen(true)}
          className="md:hidden p-2 rounded-lg text-ink-muted hover:bg-pearl-soft"
          title={t('nav.settings')}
        >
          <Settings className="w-4 h-4" />
        </button>

        <div className="relative">
          <button
            type="button"
            onClick={() => setUserOpen((v) => !v)}
            className="w-8 h-8 rounded-full bg-atelier-teal text-white text-xs font-semibold flex items-center justify-center"
          >
            {(user?.username || 'U')[0].toUpperCase()}
          </button>
          {userOpen && (
            <div className="absolute right-0 mt-2 w-44 rounded-lg border border-pearl-line bg-white shadow-atelier-lg py-1 z-50">
              <div className="px-3 py-2 text-xs text-ink-faint truncate border-b border-pearl-line">
                {user?.username || t('nav.creator')}
              </div>
              <button
                type="button"
                onClick={handleLogout}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-ink-muted hover:bg-pearl-soft"
              >
                <LogOut className="w-3.5 h-3.5" />
                {t('studio.header.logout')}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
