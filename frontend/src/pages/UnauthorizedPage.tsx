/**
 * 未授权页面
 */

import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { ShieldX, Home, ArrowLeft } from 'lucide-react';
import { useI18n } from '@/i18n';

export const UnauthorizedPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useI18n();
  const message = (location.state as any)?.message || t('unauthorized.message');

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center px-4">
      <div className="max-w-md w-full text-center">
        {/* 图标 */}
        <div className="inline-flex items-center justify-center w-20 h-20 bg-orange-100 dark:bg-orange-900/30 rounded-full mb-6">
          <ShieldX className="w-10 h-10 text-orange-600 dark:text-orange-400" />
        </div>

        {/* 标题 */}
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
          {t('unauthorized.title')}
        </h1>

        {/* 描述 */}
        <p className="text-gray-600 dark:text-gray-400 mb-8">{message}</p>

        {/* 操作按钮 */}
        <div className="flex gap-3 justify-center">
          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-2 px-6 py-3 bg-gray-200 text-gray-700 rounded-xl hover:bg-gray-300 transition-colors font-medium"
          >
            <ArrowLeft className="w-4 h-4" />
            {t('unauthorized.back')}
          </button>
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 px-6 py-3 bg-atelier-teal text-white rounded-xl hover:bg-atelier-teal-mid transition-colors font-medium"
          >
            <Home className="w-4 h-4" />
            {t('unauthorized.home')}
          </button>
        </div>
      </div>
    </div>
  );
};

export default UnauthorizedPage;
