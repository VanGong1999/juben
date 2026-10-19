/**
 * 百度百科内容组件
 * 显示百科词条详细信息
 */

import { ExternalLink, Users, Film, Info } from 'lucide-react';
import { useI18n } from '@/i18n';
import { LemmaContent } from '@/services/baiduService';

interface BaiduBaikeContentProps {
  content: LemmaContent | null;
  loading?: boolean;
}

export default function BaiduBaikeContent({ content, loading }: BaiduBaikeContentProps) {
  const { t } = useI18n();
  if (loading) {
    return (
      <div className="animate-pulse">
        <div className="flex gap-4 mb-4">
          <div className="w-24 h-24 bg-gray-200 rounded-lg"></div>
          <div className="flex-1 space-y-2">
            <div className="h-6 bg-gray-200 rounded w-1/2"></div>
            <div className="h-4 bg-gray-200 rounded w-3/4"></div>
            <div className="h-4 bg-gray-200 rounded w-1/2"></div>
          </div>
        </div>
        <div className="space-y-2">
          <div className="h-4 bg-gray-200 rounded"></div>
          <div className="h-4 bg-gray-200 rounded"></div>
          <div className="h-4 bg-gray-200 rounded w-2/3"></div>
        </div>
      </div>
    );
  }

  if (!content) {
    return (
      <div className="text-center py-8 text-gray-500">
        <Info className="w-12 h-12 mx-auto mb-3 text-gray-300" />
        <p>{t('dataViews.baidu.baike.none')}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 头部信息 */}
      <div className="flex gap-4">
        {/* 图片 */}
        {content.pic_url && (
          <div className="flex-shrink-0">
            <img
              src={content.pic_url}
              alt={content.lemma_title}
              className="w-24 h-24 object-cover rounded-lg"
            />
          </div>
        )}

        {/* 标题和描述 */}
        <div className="flex-1 min-w-0">
          <h2 className="text-xl font-bold text-gray-900 mb-2">{content.lemma_title}</h2>
          <p className="text-sm text-gray-600 mb-1">{content.lemma_desc}</p>

          {/* 分类标签 */}
          {content.classify && content.classify.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-2">
              {content.classify.map((cat, index) => (
                <span
                  key={index}
                  className="px-2 py-1 text-xs bg-blue-50 text-blue-700 rounded"
                >
                  {cat}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* 外部链接 */}
        {content.url && (
          <a
            href={content.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-shrink-0 self-start px-3 py-2 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors flex items-center gap-2"
          >
            {t('dataViews.baidu.baike.viewDetail')}
            <ExternalLink className="w-4 h-4" />
          </a>
        )}
      </div>

      {/* 摘要 */}
      {content.summary && (
        <div className="p-4 bg-blue-50 rounded-lg">
          <h3 className="text-sm font-medium text-blue-900 mb-2">{t('dataViews.baidu.baike.summary')}</h3>
          <p className="text-sm text-blue-800">{content.summary}</p>
        </div>
      )}

      {/* 概述 */}
      {content.abstract_plain && (
        <div>
          <h3 className="text-sm font-medium text-gray-900 mb-2">{t('dataViews.baidu.baike.overview')}</h3>
          <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
            {content.abstract_plain}
          </p>
        </div>
      )}

      {/* 关系图谱 */}
      {content.relations && content.relations.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-900 mb-3 flex items-center gap-2">
            <Users className="w-4 h-4" />
            {t('dataViews.baidu.baike.relatedPeople')}
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
            {content.relations.slice(0, 8).map((relation) => (
              <div
                key={relation.lemma_id}
                className="flex items-center gap-2 p-2 bg-gray-50 rounded-lg"
              >
                {relation.square_pic_url && (
                  <img
                    src={relation.square_pic_url}
                    alt={relation.lemma_title}
                    className="w-10 h-10 object-cover rounded"
                  />
                )}
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium text-gray-900 truncate">
                    {relation.lemma_title}
                  </p>
                  <p className="text-xs text-gray-500 truncate">{relation.relation_name}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 视频 */}
      {content.videos && content.videos.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-900 mb-3 flex items-center gap-2">
            <Film className="w-4 h-4" />
            {t('dataViews.baidu.baike.relatedVideos')}
          </h3>
          <div className="space-y-2">
            {content.videos.map((video) => (
              <a
                key={video.second_id}
                href={video.page_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
              >
                {video.cover_pic_url && (
                  <img
                    src={video.cover_pic_url}
                    alt={video.second_title}
                    className="w-24 h-16 object-cover rounded"
                  />
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {video.second_title}
                  </p>
                </div>
                <ExternalLink className="w-4 h-4 text-gray-400 flex-shrink-0" />
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * 百科词条列表项
 */
interface LemmaListItemProps {
  item: {
    lemma_id: number;
    lemma_title: string;
    lemma_desc: string;
    url: string;
  };
  onClick?: () => void;
}

export function LemmaListItem({ item, onClick }: LemmaListItemProps) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left p-3 bg-white rounded-lg border border-gray-200 hover:border-blue-300 hover:shadow-sm transition-all"
    >
      <h4 className="text-sm font-medium text-gray-900 mb-1">{item.lemma_title}</h4>
      <p className="text-xs text-gray-600 line-clamp-2">{item.lemma_desc}</p>
    </button>
  );
}
