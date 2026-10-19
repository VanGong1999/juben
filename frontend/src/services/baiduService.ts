/**
 * 百度 API 服务
 * 提供四个百度服务的前端调用接口：
 * 1. 百度搜索
 * 2. 百科词条
 * 3. 百度百科
 * 4. 秒懂百科
 */

import { api } from './api';

// ==================== 类型定义 ====================

export interface WebSearchParams {
  query: string;
  edition?: 'standard' | 'lite';
  top_k?: number;
  search_recency_filter?: 'week' | 'month' | 'semiyear' | 'year';
}

export interface WebSearchResult {
  id: number;
  title: string;
  url: string;
  content: string;
  date?: string;
  type?: string;
  web_anchor?: string;
}

export interface LemmaListParams {
  lemma_title: string;
  top_k?: number;
}

export interface LemmaItem {
  lemma_id: number;
  lemma_title: string;
  lemma_desc: string;
  is_default: number;
  url: string;
}

export interface LemmaContentParams {
  search_key: string;
  search_type?: 'lemmaTitle' | 'lemmaId';
}

export interface LemmaContent {
  lemma_id: number;
  lemma_title: string;
  lemma_desc: string;
  url: string;
  summary: string;
  abstract_plain: string;
  abstract_html: string;
  pic_url: string;
  square_pic_url: string;
  card?: Record<string, any>[];
  classify?: string[];
  relations?: LemmaRelation[];
  videos?: LemmaVideo[];
}

export interface LemmaRelation {
  lemma_id: number;
  lemma_title: string;
  relation_name: string;
  square_pic_url: string;
}

export interface LemmaVideo {
  second_id: number;
  second_title: string;
  cover_pic_url: string;
  page_url: string;
}

export interface SecondKnowParams {
  search_key: string;
  search_type?: 'lemmaTitle' | 'lemmaId';
  limit?: number;
  video_type?: 0 | 1;
  platform?: 'user' | 'app' | 'partner' | 'pgc';
}

export interface SecondKnowVideo {
  lemma_id: number;
  lemma_title: string;
  lemma_desc: string;
  second_id: number;
  second_title: string;
  cover_pic_url: string;
  forever_play_url_mp4: string;
  play_time: number;
  second_type: number;
  is_vertical: number;
}

export interface ComprehensiveParams {
  keyword: string;
  max_videos?: number;
}

export interface ComprehensiveResult {
  baike: LemmaContent | null;
  videos: SecondKnowVideo[];
}

// ==================== API 响应类型 ====================

interface ApiResponse<T> {
  success: boolean;
  data: T;
  request_id?: string;
  total?: number;
  error?: string;
}

// ==================== 百度搜索 API ====================

/**
 * 百度搜索 - 搜索全网实时信息
 * 免费额度: 每日 100 次
 */
export async function webSearch(params: WebSearchParams): Promise<ApiResponse<WebSearchResult[]>> {
  try {
    const response = await api.post<ApiResponse<WebSearchResult[]>>('/baidu/web_search', {
      query: params.query,
      edition: params.edition || 'standard',
      top_k: params.top_k || 10,
      search_recency_filter: params.search_recency_filter
    });
    return response;
  } catch (error) {
    console.error('[百度搜索] 请求失败:', error);
    throw error;
  }
}

/**
 * 快速搜索 - GET 方式
 */
export async function quickSearch(query: string, top_k: number = 10): Promise<ApiResponse<WebSearchResult[]>> {
  try {
    const response = await api.get<ApiResponse<WebSearchResult[]>>(`/baidu/search/${encodeURIComponent(query)}`, {
      top_k
    });
    return response;
  } catch (error) {
    console.error('[快速搜索] 请求失败:', error);
    throw error;
  }
}

// ==================== 百科词条 API ====================

/**
 * 百科词条 - 查询相关百科词条列表
 */
export async function getLemmaList(params: LemmaListParams): Promise<ApiResponse<LemmaItem[]>> {
  try {
    const response = await api.post<ApiResponse<LemmaItem[]>>('/baidu/lemma_list', {
      lemma_title: params.lemma_title,
      top_k: params.top_k || 5
    });
    return response;
  } catch (error) {
    console.error('[百科词条] 请求失败:', error);
    throw error;
  }
}

// ==================== 百度百科 API ====================

/**
 * 百度百科 - 查询词条详细内容
 */
export async function getLemmaContent(params: LemmaContentParams): Promise<ApiResponse<LemmaContent>> {
  try {
    const response = await api.post<ApiResponse<LemmaContent>>('/baidu/lemma_content', {
      search_key: params.search_key,
      search_type: params.search_type || 'lemmaTitle'
    });
    return response;
  } catch (error) {
    console.error('[百度百科] 请求失败:', error);
    throw error;
  }
}

// ==================== 秒懂百科 API ====================

/**
 * 秒懂百科 - 查询百科视频内容
 */
export async function searchSecondKnow(params: SecondKnowParams): Promise<ApiResponse<SecondKnowVideo[]>> {
  try {
    const response = await api.post<ApiResponse<SecondKnowVideo[]>>('/baidu/second_know', {
      search_key: params.search_key,
      search_type: params.search_type || 'lemmaTitle',
      limit: params.limit || 3,
      video_type: params.video_type || 0,
      platform: params.platform || 'user'
    });
    return response;
  } catch (error) {
    console.error('[秒懂百科] 请求失败:', error);
    throw error;
  }
}

// ==================== 组合查询 API ====================

/**
 * 组合查询 - 同时查询百科内容和秒懂视频
 */
export async function comprehensiveSearch(params: ComprehensiveParams): Promise<ApiResponse<ComprehensiveResult>> {
  try {
    const response = await api.post<ApiResponse<ComprehensiveResult>>('/baidu/comprehensive', {
      keyword: params.keyword,
      max_videos: params.max_videos || 3
    });
    return response;
  } catch (error) {
    console.error('[组合查询] 请求失败:', error);
    throw error;
  }
}

/**
 * 快速百科查询 - GET 方式
 */
export async function quickBaike(keyword: string, includeVideos: boolean = true): Promise<ApiResponse<ComprehensiveResult>> {
  try {
    const response = await api.get<ApiResponse<ComprehensiveResult>>(`/baidu/baike/${encodeURIComponent(keyword)}`, {
      include_videos: includeVideos
    });
    return response;
  } catch (error) {
    console.error('[快速百科] 请求失败:', error);
    throw error;
  }
}

// ==================== 健康检查 ====================

/**
 * 百度 API 健康检查
 */
export async function healthCheck(): Promise<{
  status: string;
  api_key_configured: boolean;
  services: Array<{ name: string; status: string }>;
}> {
  try {
    const response = await api.get<{
      status: string;
      api_key_configured: boolean;
      services: Array<{ name: string; status: string }>;
    }>('/baidu/health');
    return response;
  } catch (error) {
    console.error('[健康检查] 请求失败:', error);
    throw error;
  }
}

// ==================== 导出 ====================

const baiduService = {
  // 搜索
  webSearch,
  quickSearch,

  // 百科
  getLemmaList,
  getLemmaContent,

  // 视频
  searchSecondKnow,

  // 组合
  comprehensiveSearch,
  quickBaike,

  // 工具
  healthCheck
};

export default baiduService;
