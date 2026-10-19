import api from './api';

export async function getMemorySettings(params: { user_id: string; project_id?: string }) {
  return api.get<{ success: boolean; data: any }>(`/juben/user/memory/settings`, params);
}

export async function updateMemorySettings(payload: {
  user_id: string;
  project_id?: string;
  user_enabled?: boolean;
  project_enabled?: boolean;
}) {
  return api.post<{ success: boolean; data: any }>(`/juben/user/memory/settings`, payload);
}

export async function getMemoryMetrics(params: { user_id: string; session_id: string; query?: string }) {
  return api.get<{ success: boolean; data: any }>(`/juben/user/memory/metrics`, params);
}

export async function getMemoryQuality(params: { user_id: string; session_id: string; query?: string }) {
  return api.get<{ success: boolean; data: any }>(`/juben/user/memory/quality`, params);
}

export async function listMemorySnapshots(params: { user_id: string; session_id: string; project_id?: string }) {
  return api.get<{ success: boolean; data: any[] }>(`/juben/user/memory/snapshots`, params);
}

export async function createMemorySnapshot(payload: {
  user_id: string;
  session_id: string;
  project_id?: string;
  label?: string;
}) {
  return api.post<{ success: boolean; data: any }>(`/juben/user/memory/snapshots`, payload);
}

export async function restoreMemorySnapshot(snapshotId: string, payload: { user_id: string; session_id: string }) {
  return api.post<{ success: boolean; data: any }>(`/juben/user/memory/snapshots/${snapshotId}/restore`, payload);
}

function qs(params: Record<string, string | number | boolean | undefined | null>): Record<string, string> {
  const out: Record<string, string> = {};
  Object.entries(params).forEach(([k, v]) => {
    if (v === undefined || v === null || v === '') return;
    out[k] = String(v);
  });
  return out;
}

/** 五层 Agent Memory */
export async function getAgentMemoryOverview(params: { user_id: string; drama_id?: string }) {
  return api.get<{ success: boolean; data: any }>(`/juben/user/agent-memory/overview`, qs(params));
}

export async function assembleAgentMemory(payload: {
  user_id: string;
  drama_id?: string;
  query?: string;
  budget_chars?: number;
}) {
  return api.post<{ success: boolean; data: any }>(`/juben/user/agent-memory/assemble`, payload);
}

export async function getAgentMemoryResident(params: { user_id: string; drama_id?: string }) {
  return api.get<{ success: boolean; data: { user_md: string; memory_md: string } }>(
    `/juben/user/agent-memory/resident`,
    qs(params)
  );
}

export async function putAgentMemoryRules(dramaId: string, content: string) {
  return api.put<{ success: boolean }>(`/juben/user/agent-memory/rules/${dramaId}`, { content });
}

export async function putUserResident(userId: string, content: string) {
  return api.put<{ success: boolean }>(`/juben/user/agent-memory/resident/user/${userId}`, { content });
}

export async function putDramaResident(dramaId: string, content: string) {
  return api.put<{ success: boolean }>(`/juben/user/agent-memory/resident/drama/${dramaId}`, { content });
}

export async function listAgentMemoryFacts(
  dramaId: string,
  params?: { q?: string; active_only?: boolean }
) {
  return api.get<{ success: boolean; data: any[]; total: number }>(
    `/juben/user/agent-memory/facts/${dramaId}`,
    qs(params || {})
  );
}

export async function upsertAgentMemoryFact(payload: {
  drama_id: string;
  entity_type: string;
  entity_id: string;
  predicate: string;
  value: string;
  confidence?: string;
  user_id?: string;
  pinned?: boolean;
}) {
  return api.post<{ success: boolean; data: any }>(`/juben/user/agent-memory/facts`, payload);
}

export async function patchAgentMemoryFact(
  dramaId: string,
  factId: string,
  payload: { value?: string; confidence?: string; pinned?: boolean; status?: string; user_id?: string }
) {
  return api.patch<{ success: boolean; data: any }>(
    `/juben/user/agent-memory/facts/${dramaId}/${factId}`,
    payload
  );
}

export async function deleteAgentMemoryFact(dramaId: string, factId: string, params?: { user_id?: string; hard?: boolean }) {
  return api.delete<{ success: boolean }>(
    `/juben/user/agent-memory/facts/${dramaId}/${factId}`,
    qs(params || {})
  );
}

export async function listAgentMemoryEpisodes(dramaId: string, params?: { limit?: number; q?: string }) {
  return api.get<{ success: boolean; data: any[]; total: number }>(
    `/juben/user/agent-memory/episodes/${dramaId}`,
    qs(params || {})
  );
}

export async function getAgentMemoryEpisode(dramaId: string, episodeId: string) {
  return api.get<{ success: boolean; data: any }>(
    `/juben/user/agent-memory/episodes/${dramaId}/${episodeId}`
  );
}

export async function deleteAgentMemoryEpisode(dramaId: string, episodeId: string, userId?: string) {
  return api.delete<{ success: boolean }>(
    `/juben/user/agent-memory/episodes/${dramaId}/${episodeId}`,
    qs({ user_id: userId })
  );
}

export async function pinAgentMemoryEpisode(dramaId: string, episodeId: string, pinned = true) {
  return api.post<{ success: boolean }>(
    `/juben/user/agent-memory/episodes/${dramaId}/${episodeId}/pin`,
    { pinned }
  );
}

export async function reflectAgentMemoryEpisode(dramaId: string, episodeId: string, userId?: string) {
  return api.post<{ success: boolean; data: any }>(
    `/juben/user/agent-memory/episodes/${dramaId}/${episodeId}/reflect${userId ? `?user_id=${encodeURIComponent(userId)}` : ''}`,
    {}
  );
}

export async function runAgentMemoryForget(dramaId: string) {
  return api.post<{ success: boolean; data: any }>(`/juben/user/agent-memory/forget/${dramaId}`, {});
}

export async function runAgentMemoryDream(
  dramaId: string,
  params?: { user_id?: string; auto_promote?: boolean; compress_resident?: boolean }
) {
  const q = new URLSearchParams(qs(params || {})).toString();
  return api.post<{ success: boolean; data: any }>(
    `/juben/user/agent-memory/dream/${dramaId}${q ? `?${q}` : ''}`,
    {}
  );
}

export async function getAgentMemoryRules(dramaId: string) {
  return api.get<{ success: boolean; data: { content: string } }>(
    `/juben/user/agent-memory/rules/${dramaId}`
  );
}

export async function listAgentMemorySkills(dramaId: string, enabledOnly = false) {
  return api.get<{ success: boolean; data: any[]; total: number }>(
    `/juben/user/agent-memory/skills/${dramaId}`,
    qs({ enabled_only: enabledOnly })
  );
}

export async function promoteAgentMemorySkill(
  dramaId: string,
  params: { name: string; trigger: string; min_success?: number }
) {
  const q = new URLSearchParams(qs(params)).toString();
  return api.post<{ success: boolean; data?: any; error?: string }>(
    `/juben/user/agent-memory/promote-skill/${dramaId}?${q}`,
    {}
  );
}

export async function toggleAgentMemorySkill(
  dramaId: string,
  skillId: string,
  enabled: boolean,
  userId?: string
) {
  return api.patch<{ success: boolean }>(`/juben/user/agent-memory/skills/${dramaId}/${skillId}`, {
    enabled,
    user_id: userId,
  });
}

export async function deleteAgentMemorySkill(dramaId: string, skillId: string, userId?: string) {
  return api.delete<{ success: boolean }>(
    `/juben/user/agent-memory/skills/${dramaId}/${skillId}`,
    qs({ user_id: userId })
  );
}

export async function listAgentMemoryReflections(dramaId: string, limit = 50) {
  return api.get<{ success: boolean; data: any[]; total: number }>(
    `/juben/user/agent-memory/reflections/${dramaId}`,
    qs({ limit })
  );
}

export async function listAgentMemoryAudit(dramaId: string, limit = 100) {
  return api.get<{ success: boolean; data: any[]; total: number }>(
    `/juben/user/agent-memory/audit/${dramaId}`,
    qs({ limit })
  );
}

export async function searchAgentMemory(dramaId: string, q: string, topK = 8) {
  return api.get<{ success: boolean; data: any }>(
    `/juben/user/agent-memory/search/${dramaId}`,
    qs({ q, top_k: topK })
  );
}

export async function reindexAgentMemory(dramaId: string) {
  return api.post<{ success: boolean; data: any }>(`/juben/user/agent-memory/reindex/${dramaId}`, {});
}

// ==================== 版本链 / 导出 / 脱敏 / Org ====================

export async function listMemoryVersions(dramaId: string, target?: string) {
  return api.get<{ success: boolean; data: any[]; total: number }>(
    `/juben/user/agent-memory/versions/${dramaId}`,
    qs({ target })
  );
}

export async function getMemoryVersion(dramaId: string, versionId: string) {
  return api.get<{ success: boolean; data: any }>(
    `/juben/user/agent-memory/versions/${dramaId}/${versionId}`
  );
}

export async function diffMemoryVersion(dramaId: string, versionId: string) {
  return api.get<{ success: boolean; data: { version_id: string; diff: string } }>(
    `/juben/user/agent-memory/versions/${dramaId}/${versionId}/diff`
  );
}

export async function rollbackMemoryVersion(dramaId: string, versionId: string) {
  return api.post<{ success: boolean; data: any }>(
    `/juben/user/agent-memory/versions/${dramaId}/${versionId}/rollback`,
    {}
  );
}

export async function exportMemory(dramaId: string) {
  return api.get<{ success: boolean; data: any }>(`/juben/user/agent-memory/export/${dramaId}`);
}

export async function redactMemory(dramaId: string, preview = true) {
  return api.post<{ success: boolean; data: any }>(`/juben/user/agent-memory/redact/${dramaId}`, {
    preview,
  });
}

export async function getOrgMemory() {
  return api.get<{ success: boolean; data: { resident: string; facts: any[]; versions: any[] } }>(
    `/juben/user/agent-memory/org`
  );
}

export async function setOrgResident(content: string, expectedVersion?: string) {
  return api.post<{ success: boolean; data: any }>(`/juben/user/agent-memory/org/resident`, {
    content,
    expected_version: expectedVersion,
  });
}

export async function upsertOrgFact(payload: {
  entity_type: string;
  entity_id: string;
  predicate: string;
  value: string;
  confidence?: string;
  pinned?: boolean;
}) {
  return api.post<{ success: boolean; data: any }>(`/juben/user/agent-memory/org/facts`, payload);
}

export async function runOrgDream() {
  return api.post<{ success: boolean; data: any }>(`/juben/user/agent-memory/org/dream`, {});
}
