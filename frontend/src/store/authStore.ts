/**
 * 认证状态管理 Store
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import api from '@/services/api';

export interface User {
  id: string;
  username: string;
  email: string;
  displayName: string;
  avatar?: string;
  role: 'admin' | 'user' | 'guest';
  permissions: string[];
  createdAt: string;
  lastLoginAt?: string;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
  expiresAt: number;
}

interface AuthState {
  // 状态
  user: User | null;
  tokens: AuthTokens | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  // Actions
  setUser: (user: User | null) => void;
  setTokens: (tokens: AuthTokens | null) => void;
  setLoading: (loading: boolean) => void;

  // 认证操作
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  refreshToken: () => Promise<void>;
  checkAuth: () => Promise<void>;

  // 权限检查
  hasPermission: (permission: string) => boolean;
  hasRole: (role: string) => boolean;
  isAdmin: () => boolean;

  // 清除
  clearAuth: () => void;
}

export interface RegisterData {
  username: string;
  email: string;
  password: string;
  displayName?: string;
}

export interface RegisterResponse {
  id: string;
  username: string;
  email: string;
  displayName: string;
  roles: string[];
  permissions: string[];
  createdAt: string;
}

export const useAuthStore = create<AuthState>()(
  devtools(
    persist(
      (set, get) => ({
        // 初始状态
        user: null,
        tokens: null,
        isAuthenticated: false,
        isLoading: false,

        // Setters
        setUser: (user) => {
          set({ user });
          set({ isAuthenticated: !!user });
        },

        setTokens: (tokens) => set({ tokens }),

        setLoading: (isLoading) => set({ isLoading }),

        // 登录
        login: async (username, password) => {
          set({ isLoading: true });
          try {
            const response = await api.post<{ user: User; tokens: AuthTokens }>(
              '/auth/login',
              { username, password }
            );

            set({
              user: response.user,
              tokens: response.tokens,
              isAuthenticated: true,
              isLoading: false,
            });

            // 存储token到localStorage（persist中间件会自动处理）
          } catch (error) {
            set({ isLoading: false });
            throw error;
          }
        },

        // 登出
        logout: async () => {
          set({ isLoading: true });
          try {
            // 调用后端登出API
            // await authApi.logout();

            get().clearAuth();
          } catch (error) {
            console.error('Logout error:', error);
            get().clearAuth();
          }
        },

        // 注册
        register: async (data) => {
          set({ isLoading: true });
          try {
            const response = await api.post<{ user: User; tokens: AuthTokens }>('/auth/register', data);
            set({
              user: response.user,
              tokens: response.tokens,
              isLoading: false,
              isAuthenticated: true,
            });
          } catch (error) {
            set({ isLoading: false });
            throw error;
          }
        },

        // 刷新token
        refreshToken: async () => {
          const { tokens } = get();
          if (!tokens) {
            throw new Error('No refresh token available');
          }

          try {
            const newTokens = await api.post<AuthTokens>('/auth/refresh', {
              refresh_token: tokens.refreshToken,
            });

            set({ tokens: newTokens });
          } catch (error) {
            get().clearAuth();
            throw error;
          }
        },

        // 检查认证状态
        checkAuth: async () => {
          const { tokens, user } = get();

          if (!tokens || !user) {
            get().clearAuth();
            return;
          }

          // 检查token是否过期
          if (Date.now() > tokens.expiresAt) {
            try {
              await get().refreshToken();
            } catch (error) {
              get().clearAuth();
              return;
            }
          }

          set({ isAuthenticated: true });
        },

        // 权限检查
        hasPermission: (permission) => {
          const { user } = get();
          if (!user) return false;
          return user.permissions.includes(permission) || user.role === 'admin';
        },

        hasRole: (role) => {
          const { user } = get();
          if (!user) return false;
          return user.role === role;
        },

        isAdmin: () => {
          const { user } = get();
          return user?.role === 'admin';
        },

        // 清除认证信息
        clearAuth: () => {
          set({
            user: null,
            tokens: null,
            isAuthenticated: false,
            isLoading: false,
          });
        },
      }),
      {
        name: 'auth-storage',
        // 只持久化必要的信息
        partialize: (state) => ({
          user: state.user,
          tokens: state.tokens,
          isAuthenticated: state.isAuthenticated,
        }),
      }
    ),
    { name: 'AuthStore' }
  )
);
