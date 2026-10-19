/**
 * 路由保护组件
 * 用于保护需要认证的路由
 */

import React, { useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import { Loading } from '@/components/common';
import { useI18n } from '@/i18n';

interface PrivateRouteProps {
  children: React.ReactNode;
  requireAdmin?: boolean;
  requiredPermission?: string;
}

export const PrivateRoute: React.FC<PrivateRouteProps> = ({
  children,
  requireAdmin = false,
  requiredPermission,
}) => {
  const { isAuthenticated, isLoading, checkAuth, isAdmin, hasPermission } =
    useAuthStore();
  const { t } = useI18n();
  const location = useLocation();
  const [isChecking, setIsChecking] = useState(true);

  // 检查认证状态 - 确保完成后再渲染
  useEffect(() => {
    let mounted = true;

    const performAuthCheck = async () => {
      setIsChecking(true);
      try {
        if (!isAuthenticated) {
          await checkAuth();
        }
      } catch (error) {
        console.error('Auth check failed:', error);
      } finally {
        if (mounted) {
          setIsChecking(false);
        }
      }
    };

    performAuthCheck();

    return () => {
      mounted = false;
    };
  }, []); // 只在组件挂载时执行一次

  // 加载中或正在检查认证
  if (isLoading || isChecking) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loading size="lg" />
      </div>
    );
  }

  // 未认证
  if (!isAuthenticated) {
    return (
      <Navigate
        to="/login"
        state={{ from: location }}
        replace
      />
    );
  }

  // 需要管理员权限
  if (requireAdmin && !isAdmin()) {
    return (
      <Navigate
        to="/unauthorized"
        state={{ message: t('unauthorized.adminRequired') }}
        replace
      />
    );
  }

  // 需要特定权限
  if (requiredPermission && !hasPermission(requiredPermission)) {
    return (
      <Navigate
        to="/unauthorized"
        state={{ message: t('unauthorized.permissionRequired') }}
        replace
      />
    );
  }

  return <>{children}</>;
};

/**
 * 公共路由组件
 * 已认证用户访问时重定向到工作区
 */
export const PublicRoute: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const { isAuthenticated, isLoading } = useAuthStore();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loading size="lg" />
      </div>
    );
  }

  if (isAuthenticated) {
    const redirectTo = (location.state as any)?.from?.pathname || '/';
    return <Navigate to={redirectTo} replace />;
  }

  return <>{children}</>;
};
