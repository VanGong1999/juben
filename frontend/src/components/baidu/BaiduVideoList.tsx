/**
 * 秒懂百科视频列表组件
 * 显示百科视频内容
 */

import { Play, Clock, ExternalLink } from 'lucide-react';
import { useI18n } from '@/i18n';
import { SecondKnowVideo } from '@/services/baiduService';

interface BaiduVideoListProps {
  videos: SecondKnowVideo[];
  loading?: boolean;
}

export default function BaiduVideoList({ videos, loading }: BaiduVideoListProps) {
  const { t } = useI18n();
  if (loading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {[...Array(2)].map((_, i) => (
          <div key={i} className="animate-pulse">
            <div className="aspect-video bg-gray-200 rounded-lg mb-2"></div>
            <div className="h-4 bg-gray-200 rounded w-3/4 mb-1"></div>
            <div className="h-3 bg-gray-200 rounded w-1/2"></div>
          </div>
        ))}
      </div>
    );
  }

  if (videos.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <Play className="w-12 h-12 mx-auto mb-3 text-gray-300" />
        <p>{t('dataViews.baidu.video.none')}</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {videos.map((video) => (
        <VideoCard key={video.second_id} video={video} />
      ))}
    </div>
  );
}

/**
 * 视频卡片
 */
interface VideoCardProps {
  video: SecondKnowVideo;
}

function VideoCard({ video }: VideoCardProps) {
  const { t } = useI18n();
  // 格式化时长
  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // 视频类型标签
  const getVideoTypeLabel = (type: number) => {
    switch (type) {
      case 1:
        return t('dataViews.baidu.video.overview');
      case 2:
        return t('dataViews.baidu.video.explain');
      case 3:
        return t('dataViews.baidu.video.extend');
      default:
        return '';
    }
  };

  return (
    <div className="group">
      {/* 视频封面 */}
      <div className="relative aspect-video bg-gray-900 rounded-lg overflow-hidden mb-2">
        {/* 封面图 */}
        {video.cover_pic_url ? (
          <img
            src={video.cover_pic_url}
            alt={video.second_title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-gray-800">
            <Play className="w-12 h-12 text-gray-600" />
          </div>
        )}

        {/* 播放按钮 */}
        <a
          href={video.forever_play_url_mp4}
          target="_blank"
          rel="noopener noreferrer"
          className="absolute inset-0 flex items-center justify-center bg-black/0 group-hover:bg-black/30 transition-colors"
          onClick={(e) => e.preventDefault()}
        >
          <div className="w-12 h-12 bg-white/90 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
            <Play className="w-5 h-5 text-gray-900 ml-1" />
          </div>
        </a>

        {/* 时长 */}
        <div className="absolute bottom-2 right-2 px-2 py-1 bg-black/70 text-white text-xs rounded flex items-center gap-1">
          <Clock className="w-3 h-3" />
          {formatDuration(video.play_time)}
        </div>

        {/* 视频类型 */}
        {video.second_type > 0 && (
          <div className="absolute top-2 left-2 px-2 py-1 bg-blue-600/90 text-white text-xs rounded">
            {getVideoTypeLabel(video.second_type)}
          </div>
        )}

        {/* 竖屏标记 */}
        {video.is_vertical === 1 && (
          <div className="absolute top-2 right-2 px-2 py-1 bg-purple-600/90 text-white text-xs rounded">
            {t('dataViews.baidu.video.vertical')}
          </div>
        )}
      </div>

      {/* 视频信息 */}
      <div className="space-y-1">
        <h4 className="text-sm font-medium text-gray-900 line-clamp-2 group-hover:text-blue-600 transition-colors">
          {video.second_title}
        </h4>

        {video.lemma_desc && (
          <p className="text-xs text-gray-500 line-clamp-1">{video.lemma_desc}</p>
        )}

        <div className="flex items-center gap-2 text-xs text-gray-400">
          <span>{video.lemma_title}</span>
        </div>
      </div>

      {/* 操作按钮 */}
      <div className="mt-2 flex gap-2">
        <a
          href={video.forever_play_url_mp4}
          target="_blank"
          rel="noopener noreferrer"
          className="flex-1 px-3 py-2 text-sm bg-black text-white rounded-lg hover:bg-gray-800 transition-colors flex items-center justify-center gap-2"
        >
          <Play className="w-4 h-4" />
          {t('dataViews.baidu.video.play')}
        </a>
        {video.cover_pic_url && (
          <button
            onClick={() => {
              // 可以实现下载功能
              window.open(video.forever_play_url_mp4, '_blank');
            }}
            className="px-3 py-2 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
          >
            <ExternalLink className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
}

/**
 * 视频列表项 - 紧凑版
 */
interface VideoListItemProps {
  video: SecondKnowVideo;
}

export function VideoListItem({ video }: VideoListItemProps) {
  const { t } = useI18n();
  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="flex gap-3 p-3 bg-white rounded-lg border border-gray-200 hover:border-gray-300 transition-all">
      {/* 缩略图 */}
      <div className="relative flex-shrink-0 w-32 aspect-video bg-gray-900 rounded overflow-hidden">
        {video.cover_pic_url ? (
          <img
            src={video.cover_pic_url}
            alt={video.second_title}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-gray-800">
            <Play className="w-8 h-8 text-gray-600" />
          </div>
        )}
        <div className="absolute bottom-1 right-1 px-1.5 py-0.5 bg-black/70 text-white text-xs rounded">
          {formatDuration(video.play_time)}
        </div>
      </div>

      {/* 视频信息 */}
      <div className="flex-1 min-w-0">
        <h4 className="text-sm font-medium text-gray-900 line-clamp-2 mb-1">
          {video.second_title}
        </h4>
        <p className="text-xs text-gray-500 line-clamp-1">{video.lemma_desc}</p>
      </div>

      {/* 播放按钮 */}
      <a
        href={video.forever_play_url_mp4}
        target="_blank"
        rel="noopener noreferrer"
        className="flex-shrink-0 self-center px-3 py-2 text-sm bg-black text-white rounded-lg hover:bg-gray-800 transition-colors"
      >
        {t('dataViews.baidu.video.play')}
      </a>
    </div>
  );
}
