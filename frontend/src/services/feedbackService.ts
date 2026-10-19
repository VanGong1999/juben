/**
 * Feedback service
 */

import api from './api';

// ==================== 类型定义 ====================

export interface FeedbackItem {
  id: string;
  trace_id: string;
  agent_name: string;
  user_id?: string;
  session_id?: string;
  user_input: string;
  ai_output: string;
  feedback_type: string;
  user_rating?: number;
  is_gold_sample: boolean;
  gold_reason?: string;
  created_at: string;
}

export interface FeedbackStatistics {
  total_feedbacks: number;
  gold_samples?: number;
  avg_rating: number;
  by_agent: Array<{
    agent_name: string;
    count: number;
    avg_rating: number;
  }>;
  by_type: Record<string, number>;
  by_rating: Record<number, number>;
}

export interface GoldSample {
  trace_id: string;
  agent_name: string;
  user_input: string;
  ai_output: string;
  rating?: number;
  gold_reason?: string;
  created_at: string;
}

export interface FeedbackListResponse {
  success: boolean;
  total: number;
  data: FeedbackItem[];
  error?: string;
}

export interface FeedbackStatsResponse {
  success: boolean;
  data: FeedbackStatistics;
  error?: string;
}

export interface GoldSamplesResponse {
  success: boolean;
  data: GoldSample[];
  error?: string;
}

export interface FeedbackSubmitResponse {
  success: boolean;
  trace_id?: string;
  is_gold_sample?: boolean;
  gold_reason?: string;
  error?: string;
}

export async function getFeedbackList(params: {
  user_id?: string;
  agent_name?: string;
  trace_id?: string;
  is_gold_sample?: boolean;
  limit?: number;
}): Promise<FeedbackListResponse> {
  const query: Record<string, string> = {};
  if (params.user_id) query.user_id = params.user_id;
  if (params.agent_name) query.agent_name = params.agent_name;
  if (params.trace_id) query.trace_id = params.trace_id;
  if (typeof params.is_gold_sample === 'boolean') query.is_gold_sample = String(params.is_gold_sample);
  if (params.limit) query.limit = String(params.limit);
  return api.get<FeedbackListResponse>('/juben/feedback', query);
}

export async function getFeedbackStatistics(params: {
  agent_name?: string;
  days?: number;
}): Promise<FeedbackStatsResponse> {
  const query: Record<string, string> = {};
  if (params.agent_name) query.agent_name = params.agent_name;
  if (params.days) query.days = String(params.days);
  return api.get<FeedbackStatsResponse>('/juben/feedback/statistics', query);
}

export async function getGoldSamples(params: {
  agent_name?: string;
  query?: string;
  top_k?: number;
}): Promise<GoldSamplesResponse> {
  const query: Record<string, string> = {};
  if (params.agent_name) query.agent_name = params.agent_name;
  if (params.query) query.query = params.query;
  if (params.top_k) query.top_k = String(params.top_k);
  return api.get<GoldSamplesResponse>('/juben/feedback/gold', query);
}

export async function submitFeedback(payload: {
  trace_id?: string;
  agent_name: string;
  user_input: string;
  ai_output: string;
  feedback_type: string;
  user_rating?: number;
  user_id?: string;
  session_id?: string;
  metadata?: Record<string, any>;
}): Promise<FeedbackSubmitResponse> {
  return api.post<FeedbackSubmitResponse>('/juben/feedback', payload);
}

export async function submitRefinement(payload: {
  trace_id: string;
  agent_name: string;
  original_text: string;
  modified_text: string;
  user_id?: string;
  session_id?: string;
  context?: string;
}): Promise<FeedbackSubmitResponse> {
  return api.post<FeedbackSubmitResponse>('/juben/feedback/refinement', payload);
}
