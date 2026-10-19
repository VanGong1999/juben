/**
 * 百度搜索结果组件
 * 显示网页搜索结果
 */

import { ExternalLink, Calendar, Globe } from 'lucide-react';
import { useI18n } from '@/i18n';
import { WebSearchResult } from '@/services/baiduService';

interface BaiduSearchResultProps {
  results: WebSearchResult[];
  loading?: boolean;
}

export default function BaiduSearchResult({ results, loading }: BaiduSearchResultProps) {
  const { t } = useI18n();
  if (loading) {
    return (
      <div className="space-y-3">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="p-4 bg-gray-50 rounded-lg animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
            <div className="h-3 bg-gray-200 rounded w-full mb-1"></div>
            <div className="h-3 bg-gray-200 rounded w-2/3"></div>
          </div>
        ))}
      </div>
    );
  }

  if (results.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <Globe className="w-12 h-12 mx-auto mb-3 text-gray-300" />
        <p>{t('dataViews.baidu.search.none')}</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {results.map((result) => (
        <div
          key={result.id}
          className="p-4 bg-white rounded-lg border border-gray-200 hover:border-gray-300 hover:shadow-md transition-all"
        >
          {/* 标题和链接 */}
          <div className="flex items-start gap-3 mb-2">
            <a
              href={result.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-1 group"
            >
              <h3 className="text-lg font-medium text-blue-600 group-hover:underline flex items-center gap-2">
                {result.title}
                <ExternalLink className="w-4 h-4 flex-shrink-0" />
              </h3>
            </a>
          </div>

          {/* 网站来源 */}
          {result.web_anchor && (
            <div className="flex items-center gap-2 text-xs text-gray-500 mb-2">
              <Globe className="w-3 h-3" />
              <span>{result.web_anchor}</span>
            </div>
          )}

          {/* 内容摘要 */}
          <p className="text-sm text-gray-700 line-clamp-2 mb-2">
            {result.content}
          </p>

          {/* 日期 */}
          {result.date && (
            <div className="flex items-center gap-1 text-xs text-gray-400">
              <Calendar className="w-3 h-3" />
              <span>{result.date}</span>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

/**
 * 搜索结果卡片 - 紧凑版
 */
interface SearchResultCardProps {
  result: WebSearchResult;
}

export function SearchResultCard({ result }: SearchResultCardProps) {
  return (
    <a
      href={result.url}
      target="_blank"
      rel="noopener noreferrer"
      className="block p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
    >
      <h4 className="text-sm font-medium text-blue-600 hover:underline line-clamp-1 mb-1">
        {result.title}
      </h4>
      <p className="text-xs text-gray-600 line-clamp-2">{result.content}</p>
    </a>
  );
}
