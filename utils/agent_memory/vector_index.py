"""
轻量向量索引 — 情节 / 语义记忆 ANN 召回

设计:
- 默认零外部依赖：字符 n-gram 哈希嵌入 + 余弦相似度（生产可用）
- 若环境装了 chromadb，则优先走 Chroma 持久化集合
- 与关键词检索并联：assemble / search 取融合排序

对齐图示: Episodic + Semantic → Embedding → Vector Index → ANN → Working Memory
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_DIM = 256
_NGRAM = 3


def _tokenize(text: str) -> List[str]:
    t = re.sub(r"\s+", " ", (text or "").lower()).strip()
    if not t:
        return []
    # CJK 按字 + 英文按词
    parts = re.findall(r"[\u4e00-\u9fff]|[a-z0-9_]+", t)
    grams: List[str] = []
    joined = "".join(parts)
    for i in range(max(0, len(joined) - _NGRAM + 1)):
        grams.append(joined[i : i + _NGRAM])
    grams.extend(parts)
    return grams


def embed_text(text: str, dim: int = _DIM) -> List[float]:
    """确定性哈希嵌入（无需模型下载）。"""
    vec = [0.0] * dim
    grams = _tokenize(text)
    if not grams:
        return vec
    for g in grams:
        h = int(hashlib.md5(g.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if (h >> 8) & 1 else -1.0
        vec[idx] += sign
    # L2 normalize
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))


class MemoryVectorIndex:
    """作品级向量索引（落盘 JSON，可换 Chroma）。"""

    def __init__(self, drama_memory_dir: Path):
        self.dir = Path(drama_memory_dir)
        self.path = self.dir / "vector_index.json"
        self._chroma = None

    def _load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {"dim": _DIM, "items": []}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("vector_index load failed: %s", e)
            return {"dim": _DIM, "items": []}

    def _save(self, data: Dict[str, Any]) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def upsert(
        self,
        *,
        doc_id: str,
        text: str,
        layer: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        data = self._load()
        items: List[Dict[str, Any]] = data.get("items") or []
        emb = embed_text(text)
        entry = {
            "id": doc_id,
            "layer": layer,
            "text": (text or "")[:800],
            "embedding": emb,
            "metadata": metadata or {},
        }
        items = [i for i in items if i.get("id") != doc_id]
        items.append(entry)
        # 硬上限，防止无限膨胀
        if len(items) > 5000:
            items = items[-5000:]
        data["items"] = items
        self._save(data)
        self._chroma_upsert(entry)

    def delete(self, doc_id: str) -> bool:
        data = self._load()
        before = len(data.get("items") or [])
        data["items"] = [i for i in (data.get("items") or []) if i.get("id") != doc_id]
        self._save(data)
        return len(data["items"]) < before

    def search(
        self,
        query: str,
        *,
        top_k: int = 8,
        layer: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        q = (query or "").strip()
        if not q:
            return []
        # 优先 Chroma
        chroma_hits = self._chroma_search(q, top_k=top_k, layer=layer)
        if chroma_hits:
            return chroma_hits

        qv = embed_text(q)
        data = self._load()
        scored: List[Tuple[float, Dict[str, Any]]] = []
        for item in data.get("items") or []:
            if layer and item.get("layer") != layer:
                continue
            emb = item.get("embedding") or []
            s = cosine(qv, emb)
            # 关键词加成
            blob = (item.get("text") or "").lower()
            for tok in re.split(r"[\s,，。]+", q.lower()):
                if tok and tok in blob:
                    s += 0.05
            scored.append((s, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        out = []
        for s, item in scored[:top_k]:
            if s <= 0:
                continue
            out.append(
                {
                    "id": item.get("id"),
                    "layer": item.get("layer"),
                    "text": item.get("text"),
                    "score": round(s, 4),
                    "metadata": item.get("metadata") or {},
                }
            )
        return out

    def rebuild_from_rows(
        self,
        *,
        episodes: List[Dict[str, Any]],
        facts: List[Dict[str, Any]],
    ) -> Dict[str, int]:
        data = {"dim": _DIM, "items": []}
        for ep in episodes:
            eid = ep.get("episode_id") or ""
            text = " ".join(
                [
                    str(ep.get("task_description") or ""),
                    str(ep.get("approach") or ""),
                    str(ep.get("resolution") or ""),
                    " ".join(ep.get("tags") or []),
                    " ".join(ep.get("key_decisions") or []),
                    " ".join(ep.get("errors") or []),
                ]
            )
            data["items"].append(
                {
                    "id": f"ep:{eid}",
                    "layer": "episodic",
                    "text": text[:800],
                    "embedding": embed_text(text),
                    "metadata": {
                        "outcome": ep.get("outcome"),
                        "agent_id": ep.get("agent_id"),
                        "session_id": ep.get("session_id"),
                    },
                }
            )
        for f in facts:
            if f.get("status") and f.get("status") != "active":
                continue
            fid = f.get("fact_id") or ""
            text = f"{f.get('entity_type')}:{f.get('entity_id')} {f.get('predicate')}={f.get('value')}"
            data["items"].append(
                {
                    "id": f"fact:{fid}",
                    "layer": "semantic",
                    "text": text[:800],
                    "embedding": embed_text(text),
                    "metadata": {
                        "confidence": f.get("confidence"),
                        "predicate": f.get("predicate"),
                    },
                }
            )
        self._save(data)
        return {"episodic": len(episodes), "semantic": len([f for f in facts if f.get("status", "active") == "active"])}

    # ---------- optional Chroma ----------
    def _chroma_collection(self):
        if self._chroma is not None:
            return self._chroma
        try:
            import chromadb  # type: ignore

            client = chromadb.PersistentClient(path=str(self.dir / "chroma"))
            self._chroma = client.get_or_create_collection(
                name="agent_memory",
                metadata={"hnsw:space": "cosine"},
            )
            return self._chroma
        except Exception:
            self._chroma = False
            return None

    def _chroma_upsert(self, entry: Dict[str, Any]) -> None:
        col = self._chroma_collection()
        if not col:
            return
        try:
            col.upsert(
                ids=[entry["id"]],
                documents=[entry.get("text") or ""],
                metadatas=[{"layer": entry.get("layer") or "", **(entry.get("metadata") or {})}],
                embeddings=[entry.get("embedding")],
            )
        except Exception as e:
            logger.debug("chroma upsert skip: %s", e)

    def _chroma_search(self, query: str, *, top_k: int, layer: Optional[str]) -> List[Dict[str, Any]]:
        col = self._chroma_collection()
        if not col:
            return []
        try:
            qemb = embed_text(query)
            where = {"layer": layer} if layer else None
            kwargs: Dict[str, Any] = {"query_embeddings": [qemb], "n_results": top_k}
            if where:
                kwargs["where"] = where
            res = col.query(**kwargs)
            out = []
            ids = (res.get("ids") or [[]])[0]
            docs = (res.get("documents") or [[]])[0]
            metas = (res.get("metadatas") or [[]])[0]
            dists = (res.get("distances") or [[]])[0]
            for i, doc_id in enumerate(ids):
                dist = dists[i] if i < len(dists) else 1.0
                score = 1.0 - float(dist)  # cosine distance → similarity
                out.append(
                    {
                        "id": doc_id,
                        "layer": (metas[i] or {}).get("layer") if i < len(metas) else None,
                        "text": docs[i] if i < len(docs) else "",
                        "score": round(score, 4),
                        "metadata": metas[i] if i < len(metas) else {},
                    }
                )
            return out
        except Exception as e:
            logger.debug("chroma search skip: %s", e)
            return []
