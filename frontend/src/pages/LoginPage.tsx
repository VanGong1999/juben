/**
 * 登录 — Atelier Cinema
 */

import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import { useNotificationStore } from '@/store/notificationStore';
import { Lock, User, Eye, EyeOff, Film } from 'lucide-react';
import { useI18n } from '@/i18n';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuthStore();
  const { success, error } = useNotificationStore();
  const { t } = useI18n();
  const [formData, setFormData] = useState({ username: '', password: '' });
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.username || !formData.password) {
      error(t('login.toast.inputError'), t('login.toast.fillCredentials'));
      return;
    }
    setIsLoading(true);
    try {
      await login(formData.username, formData.password);
      success(t('login.toast.success'), t('login.toast.welcomeBack'));
      navigate('/');
    } catch (err) {
      error(t('login.toast.failed'), err instanceof Error ? err.message : t('login.toast.checkCredentials'));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-pearl flex">
      <div className="hidden lg:flex flex-1 flex-col justify-between p-14 relative overflow-hidden">
        <div
          className="absolute inset-0 opacity-[0.04] pointer-events-none"
          style={{
            backgroundImage:
              'repeating-linear-gradient(0deg,#14181F 0,#14181F 1px,transparent 1px,transparent 56px),repeating-linear-gradient(90deg,#14181F 0,#14181F 1px,transparent 1px,transparent 56px)',
          }}
        />
        <div className="relative z-10 flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-atelier-teal to-atelier-teal-mid flex items-center justify-center shadow-atelier-lg">
            <Film className="w-6 h-6 text-white" />
          </div>
          <div>
            <div className="font-display text-2xl font-semibold text-ink">AI影视</div>
            <div className="text-[10px] text-ink-faint tracking-[0.2em] uppercase">Creation Atelier</div>
          </div>
        </div>
        <div className="relative z-10 max-w-md">
          <p className="atelier-chip mb-4">{t('login.heroChip')}</p>
          <h1 className="font-display text-5xl font-semibold text-ink leading-[1.12]">
            {t('login.heroTitle1')}
            <br />
            <span className="italic text-atelier-teal">{t('login.heroTitle2')}</span>
          </h1>
          <p className="mt-5 text-ink-muted leading-relaxed">
            {t('login.heroDesc')}
          </p>
        </div>
        <p className="relative z-10 text-xs text-ink-faint">Powered by GLM-4.7-Flash</p>
      </div>

      <div className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md">
          <div className="lg:hidden text-center mb-8">
            <div className="inline-flex w-14 h-14 rounded-2xl bg-atelier-teal items-center justify-center mb-3 shadow-atelier">
              <Film className="w-7 h-7 text-white" />
            </div>
            <h1 className="font-display text-3xl font-semibold text-ink">AI影视创作</h1>
          </div>

          <div className="surface-panel p-8 animate-fade-in">
            <h2 className="font-display text-2xl font-semibold text-ink mb-1">{t('login.welcomeBack')}</h2>
            <p className="text-sm text-ink-muted mb-7">{t('login.subtitle')}</p>
            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label htmlFor="username" className="block text-sm font-medium text-ink mb-2">
                  {t('login.username')}
                </label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-ink-faint" />
                  <input
                    id="username"
                    type="text"
                    className="input pl-10"
                    value={formData.username}
                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                    placeholder={t('login.usernamePlaceholder')}
                    autoComplete="username"
                  />
                </div>
              </div>
              <div>
                <label htmlFor="password" className="block text-sm font-medium text-ink mb-2">
                  {t('login.password')}
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-ink-faint" />
                  <input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    className="input pl-10 pr-10"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    placeholder={t('login.passwordPlaceholder')}
                    autoComplete="current-password"
                  />
                  <button
                    type="button"
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-faint"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                  </button>
                </div>
              </div>
              <button type="submit" className="btn btn-primary w-full py-2.5" disabled={isLoading}>
                {isLoading ? t('login.loading') : t('login.submit')}
              </button>
            </form>
            <p className="mt-6 text-center text-sm text-ink-muted">
              {t('login.noAccount')}{' '}
              <Link to="/register" className="text-atelier-teal font-semibold hover:underline">
                {t('login.register')}
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
