/**
 * 短剧工作室 API
 */

import api from './api';

export type EpisodeStatus = 'draft' | 'writing' | 'done' | 'error';

export interface DramaEpisode {
  number: number;
  title: string;
  status: EpisodeStatus;
  word_count?: number;
  updated_at?: string;
  summary?: string;
}

export type DramaType = 'short_drama' | 'long_drama' | 'script_analysis';

export interface DramaMeta {
  id: string;
  title: string;
  description?: string;
  genre?: string;
  total_episodes: number;
  current_episode: number;
  status: string;
  model?: string;
  created_at?: string;
  updated_at?: string;
  completed_episodes?: number;
  tags?: string[];
  type?: DramaType;
}

export interface DramaDetail extends DramaMeta {
  episodes: DramaEpisode[];
  bible?: { characters?: string; world?: string; constraints?: any };
  outline?: string;
}

export async function listDramas(params?: { page?: number; page_size?: number; type?: DramaType }) {
  return api.get<{ success: boolean; dramas: DramaMeta[]; total: number }>(
    '/juben/dramas',
    {
      page: String(params?.page || 1),
      page_size: String(params?.page_size || 50),
      ...(params?.type ? { type: params.type } : {}),
    }
  );
}

export async function getDrama(dramaId: string) {
  return api.get<{ success: boolean; drama: DramaDetail }>(`/juben/dramas/${dramaId}`);
}

export async function updateDrama(
  dramaId: string,
  payload: { title?: string; description?: string; genre?: string; total_episodes?: number; type?: DramaType }
) {
  return api.put<{ success: boolean; drama: DramaMeta }>(`/juben/dramas/${dramaId}`, payload);
}

export async function deleteDrama(dramaId: string) {
  return api.delete<{ success: boolean }>(`/juben/dramas/${dramaId}`);
}

export async function saveBible(
  dramaId: string,
  payload: { world?: string; characters?: string }
) {
  return api.put<{ success: boolean }>(`/juben/dramas/${dramaId}/bible`, payload);
}

export async function deleteEpisode(dramaId: string, episodeNumber: number) {
  return api.delete<{ success: boolean }>(
    `/juben/dramas/${dramaId}/episodes/${episodeNumber}`
  );
}

export async function createDrama(payload: {
  title: string;
  description?: string;
  genre?: string;
  total_episodes?: number;
  tags?: string[];
  type?: DramaType;
}) {
  return api.post<{ success: boolean; drama: DramaMeta }>('/juben/dramas', payload);
}

export async function getEpisode(dramaId: string, episodeNumber: number) {
  return api.get<{
    success: boolean;
    episode: DramaEpisode & { content?: string };
  }>(`/juben/dramas/${dramaId}/episodes/${episodeNumber}`);
}

export async function writeEpisode(
  dramaId: string,
  episodeNumber: number,
  instruction?: string,
  targetWords?: number
) {
  return api.post<{ success: boolean; episode: DramaEpisode; content?: string }>(
    `/juben/dramas/${dramaId}/episodes/${episodeNumber}/write`,
    { instruction, target_words: targetWords }
  );
}

export async function generateOutline(dramaId: string, premise?: string) {
  return api.post<{ success: boolean; outline?: string; beats?: any }>(
    `/juben/dramas/${dramaId}/outline`,
    { premise }
  );
}

export async function startAutoWrite(
  dramaId: string,
  payload: { from_episode?: number; to_episode?: number }
) {
  return api.post<{ success: boolean; job_id: string }>(
    `/juben/dramas/${dramaId}/auto-write`,
    payload
  );
}

export async function getAutoWriteStatus(dramaId: string, jobId: string) {
  return api.get<{
    success: boolean;
    job: {
      status: string;
      current: number;
      total: number;
      message?: string;
      mode?: string;
      events?: Array<{ event_type?: string; data?: any; metadata?: any }>;
    };
  }>(`/juben/dramas/${dramaId}/auto-write/${jobId}`);
}

export async function listVideoPrompts(dramaId: string) {
  return api.get<{
    success: boolean;
    video_prompts: Array<{
      number: number;
      title: string;
      status: string;
      word_count: number;
      path?: string;
    }>;
  }>(`/juben/dramas/${dramaId}/video-prompts`);
}

export async function getVideoPrompt(dramaId: string, episodeNumber: number) {
  return api.get<{
    success: boolean;
    video_prompt: {
      number: number;
      title: string;
      status: string;
      content: string;
      word_count: number;
      path?: string;
    };
  }>(`/juben/dramas/${dramaId}/video-prompts/${episodeNumber}`);
}

/** SSE 分集并行写作（连贯性草稿 + 单集 subagents） */
export async function startBatchWriteStream(
  dramaId: string,
  payload: {
    from_episode?: number;
    to_episode?: number;
    instruction?: string;
    target_words?: number;
  },
  onEvent: (ev: { event: string; data: any; timestamp?: string }) => void
): Promise<void> {
  const { default: api } = await import('./api');
  await new Promise<void>((resolve, reject) => {
    let settled = false;
    const finish = () => {
      if (settled) return;
      settled = true;
      resolve();
    };
    api.connectSSE(
      `/juben/dramas/${dramaId}/batch-write`,
      {
        from_episode: payload.from_episode ?? 1,
        to_episode: payload.to_episode,
        instruction: payload.instruction,
        target_words: payload.target_words ?? 800,
        user_id: localStorage.getItem('userId') || 'default_user',
      },
      (event) => {
        try {
          const data = JSON.parse(event.data);
          const eventType = String(data.event || data.event_type || '');
          if (!eventType || eventType === 'heartbeat') return;
          if (eventType === 'done' || eventType === 'end') {
            finish();
            return;
          }
          onEvent({
            event: eventType,
            data: data.data ?? {},
            timestamp: data.timestamp || new Date().toISOString(),
          });
          if (eventType === 'complete' || eventType === 'error') {
            // complete 后再等 done；error 直接结束
            if (eventType === 'error') finish();
          }
        } catch (e) {
          reject(e instanceof Error ? e : new Error(String(e)));
        }
      },
      (err) => reject(err instanceof Error ? err : new Error(String(err))),
      () => finish()
    );
  });
}

/** SSE：剧本 → 豆包 Seedance 视频提示词批量转换 */
export async function startVideoPromptBatchStream(
  dramaId: string,
  payload: {
    from_episode?: number;
    to_episode?: number;
    instruction?: string;
    target_model?: string;
  },
  onEvent: (ev: { event: string; data: any; timestamp?: string }) => void
): Promise<void> {
  const { default: api } = await import('./api');
  await new Promise<void>((resolve, reject) => {
    let settled = false;
    const finish = () => {
      if (settled) return;
      settled = true;
      resolve();
    };
    api.connectSSE(
      `/juben/dramas/${dramaId}/video-prompts/batch-write`,
      {
        from_episode: payload.from_episode ?? 1,
        to_episode: payload.to_episode,
        instruction: payload.instruction,
        target_model: payload.target_model || '豆包 Seedance 2.5',
        user_id: localStorage.getItem('userId') || 'default_user',
      },
      (event) => {
        try {
          const data = JSON.parse(event.data);
          const eventType = String(data.event || data.event_type || '');
          if (!eventType || eventType === 'heartbeat') return;
          if (eventType === 'done' || eventType === 'end') {
            finish();
            return;
          }
          onEvent({
            event: eventType,
            data: data.data ?? {},
            timestamp: data.timestamp || new Date().toISOString(),
          });
          if (eventType === 'error') finish();
        } catch (e) {
          reject(e instanceof Error ? e : new Error(String(e)));
        }
      },
      (err) => reject(err instanceof Error ? err : new Error(String(err))),
      () => finish()
    );
  });
}

export async function listSkills() {
  return api.get<{ success: boolean; skills: Array<{ id: string; name: string; description: string; enabled?: boolean }> }>(
    '/juben/skills'
  );
}

export async function getSkill(skillId: string) {
  return api.get<{
    success: boolean;
    skill: {
      id: string;
      name: string;
      description?: string;
      summary?: string;
      category?: string;
      priority?: number;
      enabled?: boolean;
      body?: string;
      source?: string;
    };
  }>(`/juben/skills/${skillId}`);
}

export type ArtifactKind =
  | 'planning'
  | 'story'
  | 'plot'
  | 'character'
  | 'evaluation'
  | 'creation'
  | 'analysis'
  | 'other';

export interface DramaArtifactMeta {
  id: string;
  drama_id: string;
  kind: ArtifactKind | string;
  kind_label?: string;
  title: string;
  agent_id?: string;
  agent_name?: string;
  preview?: string;
  word_count?: number;
  created_at?: string;
  updated_at?: string;
  virtual?: boolean;
}

export interface DramaArtifact extends DramaArtifactMeta {
  content?: string;
  user_prompt?: string;
  category?: string;
}

export async function listDramaArtifacts(
  dramaId: string,
  params?: { kind?: string; limit?: number }
) {
  const q: Record<string, string> = {};
  if (params?.kind) q.kind = params.kind;
  if (params?.limit) q.limit = String(params.limit);
  return api.get<{
    success: boolean;
    artifacts: DramaArtifactMeta[];
    total: number;
    counts: Record<string, number>;
    kinds: Array<{ id: string; label: string }>;
  }>(`/juben/dramas/${dramaId}/artifacts`, q);
}

export async function getDramaArtifact(dramaId: string, artifactId: string) {
  return api.get<{ success: boolean; artifact: DramaArtifact }>(
    `/juben/dramas/${dramaId}/artifacts/${artifactId}`
  );
}

export async function saveDramaArtifact(
  dramaId: string,
  payload: {
    content: string;
    agent_id?: string;
    agent_name?: string;
    category?: string;
    kind?: string;
    title?: string;
    user_prompt?: string;
    sync_bible?: boolean;
  }
) {
  return api.post<{ success: boolean; artifact: DramaArtifact }>(
    `/juben/dramas/${dramaId}/artifacts`,
    payload
  );
}

export async function deleteDramaArtifact(dramaId: string, artifactId: string) {
  return api.delete<{ success: boolean }>(`/juben/dramas/${dramaId}/artifacts/${artifactId}`);
}

// ---------------------------------------------------------------------------
// 版本化写回（对话内直接改 小传/大纲/剧本，带版本号 + diff + 冲突保护）
// ---------------------------------------------------------------------------

export type DramaPartTarget = 'world' | 'characters' | 'outline' | 'episode';

export interface DramaPart {
  target: DramaPartTarget;
  episode_number?: number | null;
  content: string;
  version_id?: string | null;
  hash?: string;
  path?: string;
}

export interface DramaVersion {
  version_id: string;
  target: DramaPartTarget;
  episode_number?: number | null;
  parent_version_id?: string | null;
  before_hash?: string;
  after_hash?: string;
  agent_id?: string;
  agent_name?: string;
  session_id?: string;
  title?: string;
  word_count?: number;
  created_at?: string;
  target_label?: string;
  before?: string;
  after?: string;
  diff?: string;
}

export async function readDramaPart(
  dramaId: string,
  target: DramaPartTarget,
  episodeNumber?: number
) {
  const q: Record<string, string> = {};
  if (episodeNumber != null) q.episode_number = String(episodeNumber);
  return api.get<{ success: boolean; part: DramaPart }>(
    `/juben/dramas/${dramaId}/parts/${target}`,
    q
  );
}

export async function writeDramaPart(
  dramaId: string,
  target: DramaPartTarget,
  payload: {
    content: string;
    agent_id?: string;
    agent_name?: string;
    session_id?: string;
    expected_version?: string | null;
    episode_number?: number | null;
    title?: string;
  }
) {
  return api.post<{ success: boolean; conflict: boolean; result: any }>(
    `/juben/dramas/${dramaId}/parts/${target}`,
    payload
  );
}

export async function listDramaVersions(dramaId: string, target?: DramaPartTarget) {
  const q: Record<string, string> = {};
  if (target) q.target = target;
  return api.get<{
    success: boolean;
    versions: DramaVersion[];
    total: number;
    targets: Array<{ id: string; label: string }>;
  }>(`/juben/dramas/${dramaId}/versions`, q);
}

export async function getDramaVersion(dramaId: string, versionId: string) {
  return api.get<{ success: boolean; version: DramaVersion }>(
    `/juben/dramas/${dramaId}/versions/${versionId}`
  );
}

export async function rollbackDramaVersion(
  dramaId: string,
  versionId: string,
  payload: { agent_id?: string; agent_name?: string; session_id?: string }
) {
  return api.post<{ success: boolean; result: any }>(
    `/juben/dramas/${dramaId}/versions/${versionId}/rollback`,
    payload
  );
}
