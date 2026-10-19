/**
 * 注册 — 与登录同品牌左右分栏
 */

import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import { useNotificationStore } from '@/store/notificationStore';
import { Lock, User, Mail, Eye, EyeOff, Check, Film } from 'lucide-react';
import { useI18n } from '@/i18n';

interface FormData {
  username: string;
  email: string;
  displayName: string;
  password: string;
  confirmPassword: string;
}

export const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const { register } = useAuthStore();
  const { success, error } = useNotificationStore();
  const { t } = useI18n();

  const [formData, setFormData] = useState<FormData>({
    username: '',
    email: '',
    displayName: '',
    password: '',
    confirmPassword: '',
  });

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const getPasswordStrength = (password: string) => {
    let strength = 0;
    if (password.length >= 8) strength++;
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++;
    if (/\d/.test(password)) strength++;
    if (/[^a-zA-Z0-9]/.test(password)) strength++;
    return strength;
  };

  const passwordStrength = getPasswordStrength(formData.password);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.username || !formData.email || !formData.password) {
      error(t('register.toast.inputError'), t('register.toast.fillRequired'));
      return;
    }

    if (formData.password !== formData.confirmPassword) {
      error(t('register.toast.inputError'), t('register.toast.pwMismatch'));
      return;
    }

    if (formData.password.length < 6) {
      error(t('register.toast.inputError'), t('register.toast.pwTooShort'));
      return;
    }

    setIsLoading(true);

    try {
      await register({
        username: formData.username,
        email: formData.email,
        displayName: formData.displayName || formData.username,
        password: formData.password,
      });

      success(t('register.toast.success'), t('register.toast.welcome'));
      navigate('/');
    } catch (err) {
      error(t('register.toast.failed'), err instanceof Error ? err.message : t('register.toast.retryLater'));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-pearl flex">
      <div className="hidden lg:flex flex-1 flex-col justify-between p-14 relative overflow-hidden border-r border-pearl-line">
        <div className="relative z-10 flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-atelier-teal flex items-center justify-center">
            <Film className="w-6 h-6 text-white" />
          </div>
          <div>
            <div className="font-display text-2xl font-semibold text-ink">AI影视</div>
            <div className="text-[10px] text-ink-faint tracking-[0.2em] uppercase">Editorial</div>
          </div>
        </div>
        <div className="relative z-10 max-w-md">
          <p className="text-[11px] tracking-[0.16em] uppercase text-ink-faint mb-4">
            {t('register.heroChip')}
          </p>
          <h1 className="font-display text-5xl font-semibold text-ink leading-[1.12]">
            {t('register.heroTitle1')}
            <br />
            <span className="italic text-atelier-teal">{t('register.heroTitle2')}</span>
          </h1>
          <p className="mt-5 text-ink-muted leading-relaxed">
            {t('register.heroDesc')}
          </p>
        </div>
        <p className="relative z-10 text-xs text-ink-faint">Powered by GLM-4.7-Flash</p>
      </div>

      <div className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md">
          <div className="lg:hidden text-center mb-8">
            <div className="inline-flex w-14 h-14 rounded-xl bg-atelier-teal items-center justify-center mb-3">
              <Film className="w-7 h-7 text-white" />
            </div>
            <h1 className="font-display text-3xl font-semibold text-ink">AI影视</h1>
          </div>

          <div className="surface-panel p-8 animate-fade-in">
            <h2 className="font-display text-2xl font-semibold text-ink mb-1">{t('register.createAccount')}</h2>
            <p className="text-sm text-ink-muted mb-7">{t('register.subtitle')}</p>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="username" className="block text-sm font-medium text-ink mb-1.5">
                  {t('register.username')} <span className="text-atelier-gold">*</span>
                </label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-ink-faint" />
                  <input
                    id="username"
                    type="text"
                    className="input pl-10"
                    value={formData.username}
                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                    placeholder={t('register.usernamePlaceholder')}
                    autoComplete="username"
                    disabled={isLoading}
                    required
                  />
                </div>
              </div>

              <div>
                <label htmlFor="email" className="block text-sm font-medium text-ink mb-1.5">
                  {t('register.email')} <span className="text-atelier-gold">*</span>
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-ink-faint" />
                  <input
                    id="email"
                    type="email"
                    className="input pl-10"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    placeholder="your@email.com"
                    autoComplete="email"
                    disabled={isLoading}
                    required
                  />
                </div>
              </div>

              <div>
                <label htmlFor="displayName" className="block text-sm font-medium text-ink mb-1.5">
                  {t('register.displayName')}
                </label>
                <input
                  id="displayName"
                  type="text"
                  className="input"
                  value={formData.displayName}
                  onChange={(e) => setFormData({ ...formData, displayName: e.target.value })}
                  placeholder={t('register.displayNamePlaceholder')}
                  disabled={isLoading}
                />
              </div>

              <div>
                <label htmlFor="password" className="block text-sm font-medium text-ink mb-1.5">
                  {t('register.password')} <span className="text-atelier-gold">*</span>
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-ink-faint" />
                  <input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    className="input pl-10 pr-10"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    placeholder={t('register.passwordPlaceholder')}
                    autoComplete="new-password"
                    disabled={isLoading}
                    required
                  />
                  <button
                    type="button"
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-faint"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                {formData.password && (
                  <div className="mt-2 flex gap-1">
                    {[1, 2, 3, 4].map((level) => (
                      <div
                        key={level}
                        className={`h-1 flex-1 rounded ${
                          passwordStrength >= level ? 'bg-atelier-teal' : 'bg-pearl-soft'
                        }`}
                      />
                    ))}
                  </div>
                )}
              </div>

              <div>
                <label htmlFor="confirmPassword" className="block text-sm font-medium text-ink mb-1.5">
                  {t('register.confirmPassword')} <span className="text-atelier-gold">*</span>
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-ink-faint" />
                  <input
                    id="confirmPassword"
                    type={showConfirmPassword ? 'text' : 'password'}
                    className="input pl-10 pr-10"
                    value={formData.confirmPassword}
                    onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                    placeholder={t('register.confirmPlaceholder')}
                    autoComplete="new-password"
                    disabled={isLoading}
                    required
                  />
                  <button
                    type="button"
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-faint"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  >
                    {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                {formData.confirmPassword && formData.password === formData.confirmPassword && (
                  <div className="mt-1 flex items-center gap-1 text-xs text-atelier-teal">
                    <Check className="h-3.5 w-3.5" />
                    {t('register.passwordMatch')}
                  </div>
                )}
              </div>

              <button type="submit" className="btn btn-primary w-full py-2.5 mt-2" disabled={isLoading}>
                {isLoading ? t('register.loading') : t('register.createAccount')}
              </button>
            </form>

            <p className="mt-6 text-center text-sm text-ink-muted">
              {t('register.hasAccount')}{' '}
              <Link to="/login" className="text-atelier-teal font-semibold hover:underline">
                {t('register.login')}
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;
