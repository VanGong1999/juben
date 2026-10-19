/**
 * 创作台作品文件引用 — 对齐 Cursor @file 的薄指针体验。
 * 拖到聊天框后以 @drama[...] 形式插入；后端展开正文或由 agent 工具按需读取。
 */

export const DRAMA_REF_MIME = 'application/x-juben-drama-ref';

export type DramaRefKind = 'episode' | 'characters' | 'outline' | 'world' | 'artifact';

export type DramaRefPayload = {
  kind: DramaRefKind;
  dramaId?: string;
  episodeNumber?: number;
  artifactId?: string;
  label?: string;
};

export function formatDramaRef(ref: DramaRefPayload): string {
  switch (ref.kind) {
    case 'episode':
      return `@drama[episode:${ref.episodeNumber ?? 1}]`;
    case 'characters':
      return '@drama[characters]';
    case 'outline':
      return '@drama[outline]';
    case 'world':
      return '@drama[world]';
    case 'artifact':
      return `@drama[artifact:${ref.artifactId || ''}]`;
    default:
      return '';
  }
}

export function dramaRefLabel(ref: DramaRefPayload): string {
  if (ref.label) return ref.label;
  switch (ref.kind) {
    case 'episode':
      return `第${ref.episodeNumber ?? 1}集`;
    case 'characters':
      return '人物小传';
    case 'outline':
      return '故事大纲';
    case 'world':
      return '世界观';
    case 'artifact':
      return ref.artifactId || '产物';
    default:
      return '作品文件';
  }
}

type DragLike = { dataTransfer: DataTransfer };

export function setDramaRefDragData(e: DragLike, ref: DramaRefPayload) {
  const payload = JSON.stringify(ref);
  const text = formatDramaRef(ref);
  e.dataTransfer.setData(DRAMA_REF_MIME, payload);
  e.dataTransfer.setData('text/plain', text);
  e.dataTransfer.effectAllowed = 'copy';
}

export function parseDramaRefDragData(e: DragLike): DramaRefPayload | null {
  const raw = e.dataTransfer.getData(DRAMA_REF_MIME);
  if (raw) {
    try {
      return JSON.parse(raw) as DramaRefPayload;
    } catch {
      /* fall through */
    }
  }
  const plain = (e.dataTransfer.getData('text/plain') || '').trim();
  const m = plain.match(
    /^@drama\[\s*(episode\s*:\s*(\d+)|characters|outline|world|artifact\s*:\s*(.+))\s*\]$/i
  );
  if (!m) return null;
  const body = m[1].toLowerCase().replace(/\s+/g, '');
  if (body.startsWith('episode:')) {
    return { kind: 'episode', episodeNumber: Number(m[2]) };
  }
  if (body === 'characters') return { kind: 'characters' };
  if (body === 'outline') return { kind: 'outline' };
  if (body === 'world') return { kind: 'world' };
  if (body.startsWith('artifact:')) {
    return { kind: 'artifact', artifactId: m[3]?.trim() };
  }
  return null;
}
