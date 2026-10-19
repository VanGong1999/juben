import { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react';
import mermaid from 'mermaid';
import { Transformer } from 'markmap-lib';
import { Markmap, loadCSS, loadJS } from 'markmap-view';
import type { MindMapData } from '@/utils/mindMap';
import { toMarkmapMarkdown, toMermaidMindMap } from '@/utils/mindMap';
import { createProjectFile } from '@/services/projectService';
import { createArtifact } from '@/services/artifactService';
import { createNote } from '@/services/noteService';
import { useI18n } from '@/i18n';

type ViewMode = 'tree' | 'mermaid' | 'markmap';

type MindMapViewerProps = {
  data: MindMapData;
  agentSource?: string;
};

export default function MindMapViewer({ data, agentSource }: MindMapViewerProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('markmap');
  const [zoom, setZoom] = useState(1);
  const [status, setStatus] = useState<string | null>(null);
  const { t } = useI18n();
  const mermaidId = useId();
  const mermaidContainerRef = useRef<HTMLDivElement | null>(null);
  const markmapSvgRef = useRef<SVGSVGElement | null>(null);
  const markmapRef = useRef<Markmap | null>(null);
  const assetsLoadedRef = useRef(false);

  const mermaidCode = useMemo(() => toMermaidMindMap(data), [data]);
  const markmapMarkdown = useMemo(() => toMarkmapMarkdown(data), [data]);
  const transformer = useMemo(() => new Transformer(), []);

  useEffect(() => {
    if (viewMode !== 'mermaid' || !mermaidContainerRef.current) return;
    let cancelled = false;
    mermaid.initialize({ startOnLoad: false, securityLevel: 'strict' });
    mermaid.render(`mindmap-${mermaidId}`, mermaidCode).then(({ svg, bindFunctions }) => {
      if (cancelled || !mermaidContainerRef.current) return;
      mermaidContainerRef.current.innerHTML = svg;
      if (bindFunctions) {
        bindFunctions(mermaidContainerRef.current);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [viewMode, mermaidCode, mermaidId]);

  useEffect(() => {
    if (viewMode !== 'markmap' || !markmapSvgRef.current) return;
    if (!assetsLoadedRef.current) {
      const assets = transformer.getUsedAssets(markmapMarkdown as any);
      if (assets?.styles) {
        loadCSS(assets.styles);
      }
      if (assets?.scripts) {
        loadJS(assets.scripts, { takeOver: true });
      }
      assetsLoadedRef.current = true;
    }
    const { root } = transformer.transform(markmapMarkdown);
    if (!markmapRef.current) {
      markmapRef.current = Markmap.create(markmapSvgRef.current, { autoFit: true }, root);
    } else {
      markmapRef.current.setData(root);
      markmapRef.current.fit();
    }
  }, [viewMode, markmapMarkdown, transformer]);

  const clampZoom = (value: number) => Math.max(0.5, Math.min(2.5, value));
  const zoomIn = () => setZoom((z) => clampZoom(z + 0.1));
  const zoomOut = () => setZoom((z) => clampZoom(z - 0.1));
  const resetZoom = () => setZoom(1);

  const getSvgElement = useCallback(() => {
    if (viewMode === 'markmap' && markmapSvgRef.current) {
      return markmapSvgRef.current;
    }
    if (viewMode === 'mermaid' && mermaidContainerRef.current) {
      return mermaidContainerRef.current.querySelector('svg');
    }
    return null;
  }, [viewMode]);

  const serializeSvg = useCallback(() => {
    const svgEl = getSvgElement();
    if (!svgEl) return null;
    const clone = svgEl.cloneNode(true) as SVGSVGElement;
    if (!clone.getAttribute('xmlns')) {
      clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    }
    const serializer = new XMLSerializer();
    return serializer.serializeToString(clone);
  }, [getSvgElement]);

  const exportSvg = useCallback(async () => {
    const svgText = serializeSvg();
    if (!svgText) {
      setStatus(t('ui.exportSvgFailed'));
      return;
    }
    const blob = new Blob([svgText], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `mindmap_${Date.now()}.svg`;
    link.click();
    URL.revokeObjectURL(url);
    setStatus(t('ui.svgExported'));
  }, [serializeSvg, t]);

  const exportPng = useCallback(async () => {
    const svgText = serializeSvg();
    if (!svgText) {
      setStatus(t('ui.exportPngFailed'));
      return;
    }
    const svgEl = getSvgElement();
    if (!svgEl) {
      setStatus(t('ui.exportSvgNotFound'));
      return;
    }
    const rect = svgEl.getBoundingClientRect();
    const viewBox = svgEl.viewBox?.baseVal;
    const width = Math.max(1, Math.round(rect.width || viewBox?.width || 1200));
    const height = Math.max(1, Math.round(rect.height || viewBox?.height || 800));
    const svgBlob = new Blob([svgText], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(svgBlob);
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.drawImage(img, 0, 0, width, height);
        const pngUrl = canvas.toDataURL('image/png');
        const link = document.createElement('a');
        link.href = pngUrl;
        link.download = `mindmap_${Date.now()}.png`;
        link.click();
        setStatus(t('ui.pngExported'));
      } else {
        setStatus(t('ui.exportCanvasFailed'));
      }
      URL.revokeObjectURL(url);
    };
    img.onerror = () => {
      setStatus(t('ui.exportRenderFailed'));
      URL.revokeObjectURL(url);
    };
    img.src = url;
  }, [serializeSvg, getSvgElement, t]);

  const saveSnapshot = useCallback(async (fileType: 'note' | 'export') => {
    const projectId = localStorage.getItem('projectId');
    const userId = localStorage.getItem('userId') || 'default_user';
    const sessionId = localStorage.getItem('sessionId') || 'default_session';
    if (!projectId) {
      setStatus(t('ui.noProjectSave'));
      return;
    }
    const svgText = serializeSvg();
    const payload = {
      title: data.title,
      nodes: data.nodes,
      viewMode,
      mermaid: mermaidCode,
      markmap: markmapMarkdown,
      svg: svgText,
      createdAt: new Date().toISOString()
    };
    const filename = `${data.title || 'mindmap'}_${Date.now()}.${fileType === 'note' ? 'note.json' : 'export.json'}`;
    const response = await createProjectFile(projectId, {
      filename,
      file_type: fileType,
      content: payload,
      agent_source: agentSource,
      tags: ['mind_map', viewMode, fileType]
    });
    if (!response.success) {
      setStatus(response.message || t('studio.toast.saveFailed'));
      return;
    }

    if (fileType === 'note') {
      await createNote({
        user_id: userId,
        session_id: sessionId,
        action: 'mind_map',
        name: `mindmap_${Date.now()}`,
        title: data.title,
        context: `思维导图: ${data.title}`,
        content_type: 'mind_map',
        metadata: {
          content_type: 'mind_map',
          project_id: projectId,
          mind_map: payload
        }
      });
      setStatus(t('ui.savedToNotes'));
      return;
    }

    const artifactPayload = {
      content: JSON.stringify(payload),
      filename: `${data.title || 'mindmap'}_${Date.now()}.json`,
      file_type: 'mind_map',
      agent_source: agentSource || 'mind_map',
      user_id: userId,
      session_id: sessionId,
      project_id: projectId,
      description: 'Mindmap snapshot',
      tags: ['mind_map', viewMode, 'export'],
      metadata: {
        mind_map: payload
      }
    };
    await createArtifact(artifactPayload);
    setStatus(t('ui.savedToFiles'));
  }, [agentSource, data, markmapMarkdown, mermaidCode, serializeSvg, viewMode, t]);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-1 rounded-full bg-white px-2 py-1 text-xs text-gray-600 border">
          {t('ui.view')}
          <button
            className={`px-2 py-0.5 rounded ${viewMode === 'tree' ? 'bg-black text-white' : 'hover:bg-gray-100'}`}
            onClick={() => setViewMode('tree')}
          >
            {t('ui.tree')}
          </button>
          <button
            className={`px-2 py-0.5 rounded ${viewMode === 'mermaid' ? 'bg-black text-white' : 'hover:bg-gray-100'}`}
            onClick={() => setViewMode('mermaid')}
          >
            Mermaid
          </button>
          <button
            className={`px-2 py-0.5 rounded ${viewMode === 'markmap' ? 'bg-black text-white' : 'hover:bg-gray-100'}`}
            onClick={() => setViewMode('markmap')}
          >
            Markmap
          </button>
        </div>

        <div className="flex items-center gap-1 rounded-full bg-white px-2 py-1 text-xs text-gray-600 border">
          {t('ui.zoom')}
          <button className="px-2 py-0.5 rounded hover:bg-gray-100" onClick={zoomOut}>-</button>
          <span className="min-w-[42px] text-center">{Math.round(zoom * 100)}%</span>
          <button className="px-2 py-0.5 rounded hover:bg-gray-100" onClick={zoomIn}>+</button>
          <button className="px-2 py-0.5 rounded hover:bg-gray-100" onClick={resetZoom}>{t('common.reset')}</button>
        </div>

        <div className="flex items-center gap-1 rounded-full bg-white px-2 py-1 text-xs text-gray-600 border">
          {t('ui.export')}
          <button className="px-2 py-0.5 rounded hover:bg-gray-100" onClick={exportSvg}>SVG</button>
          <button className="px-2 py-0.5 rounded hover:bg-gray-100" onClick={exportPng}>PNG</button>
        </div>

        <div className="flex items-center gap-1 rounded-full bg-white px-2 py-1 text-xs text-gray-600 border">
          {t('ui.save')}
          <button className="px-2 py-0.5 rounded hover:bg-gray-100" onClick={() => saveSnapshot('note')}>{t('ui.toNotes')}</button>
          <button className="px-2 py-0.5 rounded hover:bg-gray-100" onClick={() => saveSnapshot('export')}>{t('ui.toFiles')}</button>
        </div>
      </div>

      {status && (
        <div className="text-xs text-gray-500">{status}</div>
      )}

      {viewMode === 'tree' && (
        <MindMapTree nodes={data.nodes} />
      )}

      {viewMode === 'mermaid' && (
        <div className="border rounded-lg bg-white p-3 overflow-auto">
          <div
            className="inline-block origin-top-left"
            style={{ transform: `scale(${zoom})` }}
            ref={mermaidContainerRef}
          />
        </div>
      )}

      {viewMode === 'markmap' && (
        <div className="border rounded-lg bg-white p-3 overflow-auto">
          <div className="inline-block origin-top-left" style={{ transform: `scale(${zoom})` }}>
            <svg ref={markmapSvgRef} style={{ width: 900, height: 500 }} />
          </div>
        </div>
      )}
    </div>
  );
}

function MindMapTree({ nodes }: { nodes: MindMapData['nodes'] }) {
  const { t } = useI18n();
  if (!nodes || nodes.length === 0) {
    return <div className="text-sm text-gray-500">{t('ui.noNodes')}</div>;
  }
  return (
    <ul className="pl-4 space-y-2">
      {nodes.map((node, idx) => (
        <li key={`${node.name}-${idx}`}>
          <div className="text-sm text-gray-800 font-medium">{node.name}</div>
          {node.children && node.children.length > 0 && (
            <div className="ml-4 mt-1 border-l border-gray-200 pl-3">
              <MindMapTree nodes={node.children} />
            </div>
          )}
        </li>
      ))}
    </ul>
  );
}
