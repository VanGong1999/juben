/**
 * 系统管理页面
 * 包含用户管理、权限管理、系统配置等功能
 */

import React, { useState, useEffect } from 'react';
import {
  Users,
  Settings,
  Shield,
  Activity,
  Database,
  Bell,
  Lock,
  Server,
  FileText,
  Trash2,
  Edit,
  Plus,
  Search,
  Filter,
  Download,
  Upload,
  RefreshCw,
  Bot,
  Zap,
  TrendingUp,
  CheckCircle2,
  XCircle,
  AlertCircle,
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { useNotificationStore } from '@/store/notificationStore';
import { Loading } from '@/components/common';
import { getAgents } from '@/services/agentService';
import { api } from '@/services/api';
import { useI18n } from '@/i18n';

type AdminTab = 'users' | 'agents' | 'permissions' | 'settings' | 'logs' | 'system';

interface SystemUser {
  id: string;
  username: string;
  email: string;
  displayName: string;
  role: 'admin' | 'user' | 'guest';
  status: 'active' | 'inactive' | 'suspended';
  createdAt: string;
  lastLoginAt: string;
  permissions: string[];
}

interface SystemLog {
  id: string;
  level: 'info' | 'warning' | 'error';
  message: string;
  timestamp: string;
  userId?: string;
  username?: string;
}

interface AgentConfig {
  id: string;
  name: string;
  displayName: string;
  description: string;
  category: string;
  status: 'active' | 'inactive' | 'beta';
  model: string;
  apiEndpoint: string;
  maxTokens: number;
  temperature: number;
  enableStreaming: boolean;
  enableRAG: boolean;
  totalCalls: number;
  successRate: number;
  avgResponseTime: number;
  lastUsedAt: string;
  createdAt: string;
}

export const AdminPage: React.FC = () => {
  const { user: currentUser } = useAuthStore();
  const { t } = useI18n();
  const { success, error } = useNotificationStore();
  const [activeTab, setActiveTab] = useState<AdminTab>('users');
  const [isLoading, setIsLoading] = useState(false);
  const [showAddUser, setShowAddUser] = useState(false);
  const [newUserForm, setNewUserForm] = useState({
    username: '',
    email: '',
    displayName: '',
    role: 'user' as SystemUser['role'],
  });
  const [systemStats, setSystemStats] = useState({
    totalAccess: 0,
    todayAccess: 0,
    todayUsers: 0,
    todayTokens: 0,
  });

  const [users, setUsers] = useState<SystemUser[]>([]);
  const [logs, setLogs] = useState<SystemLog[]>([]);
  const [agents, setAgents] = useState<AgentConfig[]>([]);
 
  useEffect(() => {
    try {
      const rawUsers = localStorage.getItem('admin_users');
      const rawLogs = localStorage.getItem('admin_logs');
      if (rawUsers) setUsers(JSON.parse(rawUsers));
      if (rawLogs) setLogs(JSON.parse(rawLogs));
    } catch {
      setUsers([]);
      setLogs([]);
    }
  }, []);

  useEffect(() => {
    localStorage.setItem('admin_users', JSON.stringify(users));
  }, [users]);

  useEffect(() => {
    localStorage.setItem('admin_logs', JSON.stringify(logs));
  }, [logs]);

  useEffect(() => {
    const loadAgents = async () => {
      try {
        const list = await getAgents();
        const mapped: AgentConfig[] = list.map((agent) => ({
          id: agent.id,
          name: agent.name,
          displayName: agent.displayName,
          description: agent.description,
          category: agent.category,
          status: agent.status === 'active' ? 'active' : agent.status === 'beta' ? 'beta' : 'inactive',
          model: agent.model,
          apiEndpoint: agent.apiEndpoint,
          maxTokens: 0,
          temperature: 0.7,
          enableStreaming: true,
          enableRAG: true,
          totalCalls: 0,
          successRate: 0,
          avgResponseTime: 0,
          lastUsedAt: '',
          createdAt: '',
        }));
        setAgents(mapped);
      } catch {
        setAgents([]);
      }
    };
    loadAgents();
  }, []);

  const [searchQuery, setSearchQuery] = useState('');

  // 筛选用户
  const filteredUsers = users.filter(
    (u) =>
      u.username.toLowerCase().includes(searchQuery.toLowerCase()) ||
      u.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      u.displayName.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // 删除用户
  const handleDeleteUser = (userId: string) => {
    if (userId === currentUser?.id) {
      error(t('admin.adminPage.toast.opFailed'), t('admin.adminPage.toast.cannotDeleteSelf'));
      return;
    }

    if (window.confirm(t('admin.adminPage.toast.deleteConfirm'))) {
      setUsers(users.filter((u) => u.id !== userId));
      success(t('admin.adminPage.toast.deleted'), t('admin.adminPage.toast.userDeleted'));
    }
  };

  const handleAddUser = () => {
    if (!newUserForm.username.trim() || !newUserForm.email.trim() || !newUserForm.displayName.trim()) {
      error(t('admin.adminPage.toast.createFailed'), t('admin.adminPage.toast.fillAll'));
      return;
    }
    const user: SystemUser = {
      id: `user_${Date.now()}`,
      username: newUserForm.username.trim(),
      email: newUserForm.email.trim(),
      displayName: newUserForm.displayName.trim(),
      role: newUserForm.role,
      status: 'active',
      createdAt: new Date().toISOString(),
      lastLoginAt: new Date().toISOString(),
      permissions: newUserForm.role === 'admin' ? ['*'] : ['read', 'write'],
    };
    setUsers((prev) => [user, ...prev]);
    setShowAddUser(false);
    setNewUserForm({ username: '', email: '', displayName: '', role: 'user' });
    success(t('admin.adminPage.toast.created'), t('admin.adminPage.toast.userAdded'));
  };

  // 更改用户角色
  const handleChangeRole = (userId: string, newRole: string) => {
    setUsers(
      users.map((u) => (u.id === userId ? { ...u, role: newRole as any } : u))
    );
    success(t('admin.adminPage.toast.updated'), t('admin.adminPage.toast.roleUpdated'));
  };

  // 刷新系统状态
  const handleRefresh = async () => {
    setIsLoading(true);
    try {
      const access = await api.get<any>('/juben/system/access-stats');
      const dashboard = await api.get<any>('/juben/system/token-dashboard');
      setSystemStats({
        totalAccess: access?.data?.total_access || 0,
        todayAccess: access?.data?.today_access || 0,
        todayUsers: access?.data?.today_unique_users || 0,
        todayTokens: dashboard?.data?.summary?.today_tokens || 0,
      });
    } catch {
      setSystemStats({
        totalAccess: 0,
        todayAccess: 0,
        todayUsers: 0,
        todayTokens: 0,
      });
    }
    setIsLoading(false);
    success(t('admin.adminPage.toast.refreshed'), t('admin.adminPage.toast.statusUpdated'));
  };

  const tabs = [
    { id: 'users' as AdminTab, label: t('admin.adminPage.tab.users'), icon: Users },
    { id: 'agents' as AdminTab, label: t('admin.adminPage.tab.agents'), icon: Bot },
    { id: 'permissions' as AdminTab, label: t('admin.adminPage.tab.permissions'), icon: Shield },
    { id: 'settings' as AdminTab, label: t('admin.adminPage.tab.settings'), icon: Settings },
    { id: 'logs' as AdminTab, label: t('admin.adminPage.tab.logs'), icon: FileText },
    { id: 'system' as AdminTab, label: t('admin.adminPage.tab.system'), icon: Activity },
  ];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* 头部 */}
      <div className="bg-white dark:bg-gray-800 shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-6">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                  {t('admin.adminPage.title')}
                </h1>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  {t('admin.adminPage.subtitle')}
                </p>
              </div>
              <button
                onClick={handleRefresh}
                disabled={isLoading}
                className="flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
              >
                <RefreshCw
                  className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`}
                />
                {t('admin.refresh')}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Tab导航 */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow mb-6">
          <div className="border-b border-gray-200 dark:border-gray-700">
            <nav className="flex -mb-px">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-6 py-4 border-b-2 font-medium text-sm transition-colors ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                  }`}
                >
                  <tab.icon className="w-4 h-4" />
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>
        </div>

        {/* 内容区域 */}
        {activeTab === 'users' && (
          <div className="space-y-6">
            {/* 工具栏 */}
            <div className="flex items-center justify-between">
              <div className="relative flex-1 max-w-md">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                <input
                  type="text"
                  placeholder={t('admin.adminPage.searchUsers')}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                />
              </div>
              <button
                onClick={() => setShowAddUser(true)}
                className="flex items-center gap-2 px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 transition-colors"
              >
                <Plus className="w-4 h-4" />
                {t('admin.adminPage.addUser')}
              </button>
            </div>

            {/* 用户表格 */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-700">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      {t('admin.adminPage.user')}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      {t('admin.adminPage.role')}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      {t('admin.status')}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      {t('admin.adminPage.lastLogin')}
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      {t('admin.actions')}
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  {filteredUsers.map((user) => (
                    <tr key={user.id}>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <div className="flex-shrink-0 h-10 w-10">
                            <div className="h-10 w-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-medium">
                              {user.displayName.charAt(0).toUpperCase()}
                            </div>
                          </div>
                          <div className="ml-4">
                            <div className="text-sm font-medium text-gray-900 dark:text-white">
                              {user.displayName}
                            </div>
                            <div className="text-sm text-gray-500 dark:text-gray-400">
                              {user.email}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <select
                          value={user.role}
                          onChange={(e) =>
                            handleChangeRole(user.id, e.target.value)
                          }
                          disabled={user.id === currentUser?.id}
                          className="text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1 dark:bg-gray-700 dark:text-white"
                        >
                          <option value="admin">{t('admin.adminPage.roleAdmin')}</option>
                          <option value="user">{t('admin.adminPage.roleUser')}</option>
                          <option value="guest">{t('admin.adminPage.roleGuest')}</option>
                        </select>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                            user.status === 'active'
                              ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                              : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                          }`}
                        >
                          {user.status === 'active' ? t('admin.adminPage.active') : t('admin.adminPage.inactive')}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {new Date(user.lastLoginAt).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button
                          onClick={() => handleDeleteUser(user.id)}
                          disabled={user.id === currentUser?.id}
                          className="text-red-600 hover:text-red-900 dark:text-red-400 dark:hover:text-red-300 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'agents' && (
          <div className="space-y-6">
            {/* 统计卡片 */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">{t('admin.adminPage.totalAgents')}</p>
                    <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                      {agents.length}
                    </p>
                  </div>
                  <Bot className="w-8 h-8 text-blue-500" />
                </div>
              </div>

              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">{t('admin.adminPage.activeAgents')}</p>
                    <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                      {agents.filter((a) => a.status === 'active').length}
                    </p>
                  </div>
                  <CheckCircle2 className="w-8 h-8 text-green-500" />
                </div>
              </div>

              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">{t('admin.adminPage.beta')}</p>
                    <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                      {agents.filter((a) => a.status === 'beta').length}
                    </p>
                  </div>
                  <Zap className="w-8 h-8 text-yellow-500" />
                </div>
              </div>

              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">{t('admin.adminPage.avgSuccessRate')}</p>
                    <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                      {(agents.reduce((sum, a) => sum + a.successRate, 0) / agents.length).toFixed(1)}%
                    </p>
                  </div>
                  <TrendingUp className="w-8 h-8 text-purple-500" />
                </div>
              </div>
            </div>

            {/* Agent 列表 */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                  {t('admin.adminPage.agentList')}
                </h2>
                <button className="flex items-center gap-2 px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 transition-colors text-sm">
                  <Plus className="w-4 h-4" />
                  {t('admin.adminPage.addAgent')}
                </button>
              </div>

              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                  <thead className="bg-gray-50 dark:bg-gray-700">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                        Agent
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                        {t('admin.category')}
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                        {t('admin.status')}
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                        {t('admin.model')}
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                        {t('admin.adminPage.calls')}
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                        {t('admin.adminPage.successRate')}
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                        {t('admin.adminPage.responseTime')}
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                        {t('admin.actions')}
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                    {agents.map((agent) => (
                      <tr key={agent.id} className="hover:bg-gray-50 dark:hover:bg-gray-750">
                        <td className="px-6 py-4">
                          <div>
                            <div className="text-sm font-medium text-gray-900 dark:text-white">
                              {agent.displayName}
                            </div>
                            <div className="text-xs text-gray-500 dark:text-gray-400">
                              {agent.id}
                            </div>
                            <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                              {agent.description}
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <span className="inline-flex px-2 py-1 text-xs font-medium bg-purple-100 text-purple-700 rounded">
                            {agent.category}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <span
                            className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                              agent.status === 'active'
                                ? 'bg-green-100 text-green-800'
                                : agent.status === 'beta'
                                ? 'bg-yellow-100 text-yellow-800'
                                : 'bg-gray-100 text-gray-800'
                            }`}
                          >
                            {agent.status === 'active' ? t('admin.adminPage.active') : agent.status === 'beta' ? t('admin.adminPage.testing') : t('admin.adminPage.inactive')}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">
                          {agent.model}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-900 dark:text-white font-medium">
                          {agent.totalCalls.toLocaleString()}
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-2">
                            <div className="flex-1 bg-gray-200 rounded-full h-2 w-16">
                              <div
                                className={`h-2 rounded-full ${
                                  agent.successRate >= 90
                                    ? 'bg-green-500'
                                    : agent.successRate >= 70
                                    ? 'bg-yellow-500'
                                    : 'bg-red-500'
                                }`}
                                style={{ width: `${agent.successRate}%` }}
                              />
                            </div>
                            <span className="text-sm text-gray-900 dark:text-white">
                              {agent.successRate}%
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">
                          {agent.avgResponseTime}s
                        </td>
                        <td className="px-6 py-4 text-right">
                          <div className="flex items-center justify-end gap-1">
                            <button
                              className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                              title={t('admin.adminPage.configure')}
                            >
                              <Settings className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                            </button>
                            <button
                              className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                              title={t('admin.adminPage.edit')}
                            >
                              <Edit className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                            </button>
                            <button
                              className="p-1.5 hover:bg-red-100 dark:hover:bg-red-900/30 rounded"
                              title={t('common.delete')}
                            >
                              <Trash2 className="w-4 h-4 text-red-600 dark:text-red-400" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'permissions' && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              {t('admin.adminPage.tab.permissions')}
            </h2>
            <p className="text-gray-600 dark:text-gray-400">
              {t('admin.adminPage.permissionsDesc')}
            </p>
          </div>
        )}

        {activeTab === 'settings' && (
          <div className="space-y-6">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                {t('admin.adminPage.tab.settings')}
              </h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    {t('admin.adminPage.systemName')}
                  </label>
                  <input
                    type="text"
                    defaultValue="短剧策划助手"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    {t('admin.adminPage.maxConcurrentUsers')}
                  </label>
                  <input
                    type="number"
                    defaultValue={100}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 dark:text-white"
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'logs' && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                {t('admin.adminPage.systemLogs')}
              </h2>
            </div>
            <div className="divide-y divide-gray-200 dark:divide-gray-700">
              {logs.map((log) => (
                <div key={log.id} className="px-6 py-4">
                  <div className="flex items-start gap-3">
                    <div
                      className={`flex-shrink-0 w-2 h-2 rounded-full mt-2 ${
                        log.level === 'error'
                          ? 'bg-red-500'
                          : log.level === 'warning'
                          ? 'bg-yellow-500'
                          : 'bg-blue-500'
                      }`}
                    />
                    <div className="flex-1">
                      <p className="text-sm text-gray-900 dark:text-white">
                        {log.message}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        {new Date(log.timestamp).toLocaleString()}{' '}
                        {log.username && `- ${log.username}`}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'system' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {t('admin.adminPage.todayUsers')}
                  </p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                    {systemStats.todayUsers}
                  </p>
                </div>
                <Users className="w-8 h-8 text-blue-500" />
              </div>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {t('admin.adminPage.todayAccess')}
                  </p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                    {systemStats.todayAccess}
                  </p>
                </div>
                <Server className="w-8 h-8 text-green-500" />
              </div>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {t('admin.adminPage.todayTokens')}
                  </p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                    {systemStats.todayTokens}
                  </p>
                </div>
                <Database className="w-8 h-8 text-purple-500" />
              </div>
            </div>
          </div>
        )}
      </div>

      {showAddUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{t('admin.adminPage.addUser')}</h3>
              <button
                onClick={() => setShowAddUser(false)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>
            <div className="space-y-3">
              <input
                type="text"
                placeholder={t('admin.adminPage.username')}
                value={newUserForm.username}
                onChange={(e) => setNewUserForm({ ...newUserForm, username: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 dark:text-white"
              />
              <input
                type="email"
                placeholder={t('admin.adminPage.email')}
                value={newUserForm.email}
                onChange={(e) => setNewUserForm({ ...newUserForm, email: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 dark:text-white"
              />
              <input
                type="text"
                placeholder={t('admin.adminPage.displayName')}
                value={newUserForm.displayName}
                onChange={(e) => setNewUserForm({ ...newUserForm, displayName: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 dark:text-white"
              />
              <select
                value={newUserForm.role}
                onChange={(e) => setNewUserForm({ ...newUserForm, role: e.target.value as SystemUser['role'] })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 dark:text-white"
              >
                <option value="admin">管理员</option>
                <option value="user">用户</option>
                <option value="guest">访客</option>
              </select>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => setShowAddUser(false)}
                className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg"
              >
                {t('common.cancel')}
              </button>
              <button
                onClick={handleAddUser}
                className="px-4 py-2 bg-black text-white rounded-lg"
              >
                {t('common.save')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminPage;
