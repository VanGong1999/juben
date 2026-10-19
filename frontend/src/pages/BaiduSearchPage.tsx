/**
 * 百度搜索页面
 * 集成百度搜索、百科词条、百度百科、秒懂百科四个服务
 */

import { useEffect, useState } from 'react';
import { Search, BookOpen, Video, Globe, Loader2 } from 'lucide-react';
import AppShell from '@/components/layout/AppShell';
import { BaiduSearchResult, BaiduBaikeContent, BaiduVideoList } from '@/components/baidu';
import baiduService, {
  WebSearchParams,
  LemmaContentParams,
  SecondKnowParams,
  ComprehensiveParams
} from '@/services/baiduService';
import { useI18n } from '@/i18n';

type TabType = 'search' | 'baike' | 'video' | 'comprehensive';

export default function BaiduSearchPage() {
  const { t } = useI18n();
  const [activeTab, setActiveTab] = useState<TabType>('search');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);

  // 搜索结果状态
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [baikeContent, setBaikeContent] = useState<any>(null);
  const [videos, setVideos] = useState<any[]>([]);
  const [history, setHistory] = useState<any[]>([]);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    try {
      const raw = localStorage.getItem('baidu_search_history');
      if (raw) setHistory(JSON.parse(raw));
    } catch {
      setHistory([]);
    }
  }, []);

  useEffect(() => {
    localStorage.setItem('baidu_search_history', JSON.stringify(history.slice(0, 20)));
  }, [history]);

  // 标签页配置
  const tabs = [
    { id: 'search' as TabType, name: t('toolbox.baidu.tab.search'), icon: Search },
    { id: 'baike' as TabType, name: t('toolbox.baidu.tab.baike'), icon: BookOpen },
    { id: 'video' as TabType, name: t('toolbox.baidu.tab.video'), icon: Video },
    { id: 'comprehensive' as TabType, name: t('toolbox.baidu.tab.comprehensive'), icon: Globe },
  ];

  // 执行搜索
  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setLoading(true);
    setErrorMessage('');
    try {
      switch (activeTab) {
        case 'search':
          await handleWebSearch();
          break;
        case 'baike':
          await handleBaikeContent();
          break;
        case 'video':
          await handleVideoSearch();
          break;
        case 'comprehensive':
          await handleComprehensiveSearch();
          break;
      }
      setHistory((prev) => [
        { query: searchQuery.trim(), tab: activeTab, timestamp: new Date().toISOString() },
        ...prev,
      ].slice(0, 20));
    } catch (error) {
      console.error('搜索失败:', error);
      setErrorMessage(t('toolbox.baidu.searchFailed'));
    } finally {
      setLoading(false);
    }
  };

  // 百度搜索
  const handleWebSearch = async () => {
    const params: WebSearchParams = {
      query: searchQuery,
      top_k: 10,
      search_recency_filter: 'month'
    };
    const response = await baiduService.webSearch(params);
    setSearchResults(response.data || []);
  };

  // 百度百科
  const handleBaikeContent = async () => {
    const params: LemmaContentParams = {
      search_key: searchQuery,
      search_type: 'lemmaTitle'
    };
    const response = await baiduService.getLemmaContent(params);
    setBaikeContent(response.data || null);
  };

  // 秒懂百科视频
  const handleVideoSearch = async () => {
    const params: SecondKnowParams = {
      search_key: searchQuery,
      search_type: 'lemmaTitle',
      limit: 6
    };
    const response = await baiduService.searchSecondKnow(params);
    setVideos(response.data || []);
  };

  // 组合查询
  const handleComprehensiveSearch = async () => {
    const params: ComprehensiveParams = {
      keyword: searchQuery,
      max_videos: 3
    };
    const response = await baiduService.comprehensiveSearch(params);

    if (response.data) {
      setBaikeContent(response.data.baike || null);
      setVideos(response.data.videos || []);
    }
  };

  // 按回车搜索
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <AppShell
      title={t('toolbox.baidu.title')}
      subtitle={t('toolbox.baidu.subtitle')}
    >
      <div className="px-4 sm:px-8 lg:px-10 py-6 sm:py-8 max-w-6xl mx-auto space-y-6 sm:space-y-8">
        {/* 标签页切换 */}
        <div className="flex gap-1 border-b border-pearl-line">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => {
                  setActiveTab(tab.id);
                  setSearchQuery('');
                  setSearchResults([]);
                  setBaikeContent(null);
                  setVideos([]);
                }}
                className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-atelier-teal text-atelier-teal'
                    : 'border-transparent text-ink-muted hover:text-ink'
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.name}
              </button>
            );
          })}
        </div>

        {/* 搜索框 */}
        <div className="glass-panel p-4 sm:p-5">
          <div className="flex gap-3">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={
                activeTab === 'search'
                  ? t('toolbox.baidu.placeholder.search')
                  : activeTab === 'baike'
                  ? t('toolbox.baidu.placeholder.baike')
                  : activeTab === 'video'
                  ? t('toolbox.baidu.placeholder.video')
                  : t('toolbox.baidu.placeholder.comprehensive')
              }
              className="flex-1 px-4 py-2.5 border border-pearl-line rounded-lg focus:outline-none focus:ring-2 focus:ring-atelier-teal/30 focus:border-transparent text-sm text-ink placeholder:text-ink-faint bg-white/70"
              disabled={loading}
            />
            <button
              onClick={handleSearch}
              disabled={loading || !searchQuery.trim()}
              className="px-5 py-2.5 bg-atelier-teal text-white rounded-lg hover:bg-atelier-teal-mid transition-colors disabled:bg-pearl-soft disabled:text-ink-faint disabled:cursor-not-allowed flex items-center gap-2 text-sm font-medium"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {t('toolbox.baidu.searching')}
                </>
              ) : (
                <>
                  <Search className="w-4 h-4" />
                  {t('nav.search')}
                </>
              )}
            </button>
          </div>

          {/* 搜索提示 */}
          {activeTab === 'search' && (
            <div className="mt-2 flex items-center gap-3 text-xs text-ink-muted">
              <span>{t('toolbox.baidu.dailyQuota')}</span>
              <span>•</span>
              <span>{t('toolbox.baidu.timeFilter')}</span>
            </div>
          )}
        </div>

        {history.length > 0 && (
          <div className="glass-panel p-4">
            <div className="text-xs text-ink-muted mb-2">{t('toolbox.baidu.recent')}</div>
            <div className="flex flex-wrap gap-2">
              {history.slice(0, 6).map((item, idx) => (
                <button
                  key={`${item.query}-${idx}`}
                  onClick={() => {
                    setSearchQuery(item.query);
                    setActiveTab(item.tab as TabType);
                  }}
                  className="px-2 py-1 text-xs bg-pearl-soft rounded hover:bg-atelier-teal-soft text-ink-muted"
                >
                  {item.query}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* 结果展示区 */}
        <div>
          {errorMessage && (
            <div className="mb-4 p-3 bg-red-50 text-red-700 text-sm rounded border border-red-100">
              {errorMessage}
            </div>
          )}
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-ink-faint" />
            </div>
          ) : (
            <>
              {/* 百度搜索结果 */}
              {activeTab === 'search' && (
                <>
                  {searchResults.length > 0 && (
                    <div className="mb-3 text-sm text-ink-muted">
                      {t('toolbox.baidu.foundResults', { count: searchResults.length })}
                    </div>
                  )}
                  <BaiduSearchResult results={searchResults} />
                </>
              )}

              {/* 百科内容 */}
              {activeTab === 'baike' && (
                <BaiduBaikeContent content={baikeContent} loading={loading} />
              )}

              {/* 视频列表 */}
              {activeTab === 'video' && (
                <>
                  {videos.length > 0 && (
                    <div className="mb-3 text-sm text-ink-muted">
                      {t('toolbox.baidu.foundVideos', { count: videos.length })}
                    </div>
                  )}
                  <BaiduVideoList videos={videos} loading={loading} />
                </>
              )}

              {/* 组合查询 */}
              {activeTab === 'comprehensive' && (
                <div className="space-y-6">
                  {/* 百科部分 */}
                  {baikeContent && (
                    <div>
                      <h2 className="text-base font-semibold text-ink mb-3">{t('toolbox.baidu.baikeContent')}</h2>
                      <BaiduBaikeContent content={baikeContent} />
                    </div>
                  )}

                  {/* 视频部分 */}
                  {videos.length > 0 && (
                    <div>
                      <h2 className="text-base font-semibold text-ink mb-3">{t('toolbox.baidu.relatedVideos')}</h2>
                      <BaiduVideoList videos={videos} />
                    </div>
                  )}

                  {!baikeContent && videos.length === 0 && (
                    <div className="text-center py-12 text-ink-muted text-sm">
                      {t('toolbox.baidu.enterKeyword')}
                    </div>
                  )}
                </div>
              )}

              {/* 空状态 */}
              {!loading && searchResults.length === 0 && !baikeContent && videos.length === 0 && (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <div className="w-14 h-14 bg-pearl-soft rounded-full flex items-center justify-center mb-3">
                    <Search className="w-7 h-7 text-ink-faint" />
                  </div>
                  <h3 className="text-base font-medium text-ink mb-2">{t('toolbox.baidu.startSearch')}</h3>
                  <p className="text-sm text-ink-muted max-w-md">
                    {t('toolbox.baidu.startSearchDesc')}
                  </p>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </AppShell>
  );
}
