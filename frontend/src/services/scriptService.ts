/**
 * 作品剧本库 — 上传 / 检索
 */

import api, { API_BASE_URL, getAuthHeaderValue } from './api';

export interface ScriptMeta {
  id: string;
  drama_id: string;
  title: string;
  filename?: string;
  tags?: string[];
  char_count?: number;
  chunk_count?: number;
  embed_backend?: string;
  preview?: string;
  created_at?: string;
  content?: string;
}

export type ScriptSearchMode = 'grep' | 'vector' | 'hybrid';

export interface ScriptSearchHit {
  doc_id: string;
  title?: string;
  line?: number;
  chunk_id?: string;
  score?: number;
  text: string;
  mode?: string;
}

export async function listScripts(dramaId: string) {
  return api.get<{ success: boolean; scripts: ScriptMeta[]; total: number }>(
    `/juben/dramas/${dramaId}/scripts`
  );
}

export async function getScript(dramaId: string, docId: string, includeContent = true) {
  return api.get<{ success: boolean; script: ScriptMeta }>(
    `/juben/dramas/${dramaId}/scripts/${docId}`,
    { include_content: String(includeContent) }
  );
}

export async function deleteScript(dramaId: string, docId: string) {
  return api.delete<{ success: boolean }>(`/juben/dramas/${dramaId}/scripts/${docId}`);
}

export async function uploadScript(
  dramaId: string,
  file: File,
  options?: { title?: string; tags?: string; user_id?: string }
) {
  const form = new FormData();
  form.append('file', file);
  if (options?.title) form.append('title', options.title);
  if (options?.tags) form.append('tags', options.tags);
  form.append('user_id', options?.user_id || localStorage.getItem('userId') || 'default_user');

  const auth = getAuthHeaderValue();
  const res = await fetch(`${API_BASE_URL}/juben/dramas/${dramaId}/scripts/upload`, {
    method: 'POST',
    headers: {
      ...(auth ? { Authorization: auth } : {}),
    },
    body: form,
  });
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return res.json() as Promise<{
    success: boolean;
    script: ScriptMeta;
    message?: string;
  }>;
}

export async function searchScripts(
  dramaId: string,
  payload: {
    query: string;
    mode?: ScriptSearchMode;
    doc_id?: string;
    top_k?: number;
  }
) {
  return api.post<{
    success: boolean;
    mode: string;
    query: string;
    total: number;
    hits: ScriptSearchHit[];
    embed_backend?: string;
    grep_total?: number;
    vector_total?: number;
  }>(`/juben/dramas/${dramaId}/scripts/search`, payload);
}
