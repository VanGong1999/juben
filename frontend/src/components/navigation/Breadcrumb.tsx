/**
 * 面包屑导航组件
 */

import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ChevronRight, Home } from 'lucide-react';
import { useI18n } from '@/i18n';

interface BreadcrumbItem {
  label: string;
  path?: string;
}

interface BreadcrumbProps {
  items?: BreadcrumbItem[];
  separator?: React.ReactNode;
  homePath?: string;
}

export const Breadcrumb: React.FC<BreadcrumbProps> = ({
  items,
  separator = <ChevronRight className="w-4 h-4" />,
  homePath = '/',
}) => {
  const location = useLocation();
  const { t } = useI18n();

  // 默认根据路径生成面包屑
  const defaultItems: BreadcrumbItem[] = React.useMemo(() => {
    if (items) return items;

    const pathSegments = location.pathname.split('/').filter(Boolean);
    const breadcrumbs: BreadcrumbItem[] = [];

    pathSegments.forEach((segment, index) => {
      const path = '/' + pathSegments.slice(0, index + 1).join('/');

      // 路径映射到显示名称
      const labelMap: Record<string, string> = {
        workspace: t('nav.studio'),
        studio: t('nav.studio'),
        experts: t('nav.experts'),
        dramas: t('nav.works'),
        chat: t('ui.breadcrumb.chat'),
        baidu: t('studio.header.nav.baidu'),
        tools: t('studio.header.nav.tools'),
        projects: t('studio.header.nav.projects'),
        ocr: t('ui.breadcrumb.ocr'),
        files: t('studio.header.nav.files'),
        graph: t('studio.header.nav.graph'),
        workflow: t('ui.breadcrumb.workflow'),
        statistics: t('studio.header.nav.statistics'),
        admin: t('studio.header.nav.admin'),
        login: t('ui.breadcrumb.login'),
        register: t('ui.breadcrumb.register'),
      };

      const label = labelMap[segment] || segment;

      breadcrumbs.push({
        label,
        path,
      });
    });

    return breadcrumbs;
  }, [location.pathname, items, t]);

  if (defaultItems.length === 0) {
    return null;
  }

  return (
    <nav className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
      {/* 首页 */}
      <Link
        to={homePath}
        className="flex items-center gap-1 hover:text-gray-900 dark:hover:text-white transition-colors"
      >
        <Home className="w-4 h-4" />
      </Link>

      {/* 分隔符 */}
      <span className="flex items-center">{separator}</span>

      {/* 面包屑项 */}
      {defaultItems.map((item, index) => (
        <React.Fragment key={index}>
          {index > 0 && <span className="flex items-center">{separator}</span>}
          {item.path ? (
            <Link
              to={item.path}
              className="hover:text-gray-900 dark:hover:text-white transition-colors"
            >
              {item.label}
            </Link>
          ) : (
            <span className="text-gray-900 dark:text-white font-medium">
              {item.label}
            </span>
          )}
        </React.Fragment>
      ))}
    </nav>
  );
};

export default Breadcrumb;
