"""
作品级剧本库 — 上传 / 分块 / grep / 本地向量检索

不依赖 Milvus：向量用哈希词袋（可叠加外部 embedding）。
存储：projects/{drama_id}/scripts/{doc_id}/
"""

from __future__ import annotations

import json
import logging
import math
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiofiles

logger = logging.getLogger(__name__)

ALLOWED_EXT = {".txt", ".md", ".markdown", ".json", ".csv", ".srt", ".fountain"}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
CHUNK_SIZE = 700
CHUNK_OVERLAP = 100
EMBED_DIM = 384


class ScriptLibrary:
    def __init__(self, base_dir: str = "projects"):
        self.base_dir = Path(base_dir)

    def _drama_root(self, drama_id: str) -> Path:
        return self.base_dir / drama_id

    def _scripts_root(self, drama_id: str) -> Path:
        return self._drama_root(drama_id) / "scripts"

    def _doc_dir(self, drama_id: str, doc_id: str) -> Path:
        return self._scripts_root(drama_id) / doc_id

    async def _ensure_drama(self, drama_id: str) -> None:
        root = self._drama_root(drama_id)
        if not root.exists() or not (root / "drama.json").exists():
            # allow legacy project.json
            if not (root / "project.json").exists():
                raise ValueError("短剧不存在")
        self._scripts_root(drama_id).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _decode_bytes(raw: bytes) -> str:
        for enc in ("utf-8", "utf-8-sig", "gb18030", "gbk", "latin-1"):
            try:
                return raw.decode(enc)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="ignore")

    @staticmethod
    def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[Dict[str, Any]]:
        text = (text or "").strip()
        if not text:
            return []
        chunks: List[Dict[str, Any]] = []
        start = 0
        idx = 0
        n = len(text)
        while start < n:
            end = min(n, start + size)
            # prefer break at paragraph/sentence
            if end < n:
                window = text[start:end]
                br = max(window.rfind("\n\n"), window.rfind("。"), window.rfind("\n"))
                if br > size // 3:
                    end = start + br + 1
            piece = text[start:end].strip()
            if piece:
                chunks.append(
                    {
                        "chunk_id": f"c{idx:04d}",
                        "index": idx,
                        "start": start,
                        "end": end,
                        "content": piece,
                    }
                )
                idx += 1
            if end >= n:
                break
            start = max(end - overlap, start + 1)
        return chunks

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return re.findall(r"[\u4e00-\u9fff]|[a-zA-Z0-9_]+", (text or "").lower())

    @classmethod
    def local_embed(cls, text: str, dim: int = EMBED_DIM) -> List[float]:
        vec = [0.0] * dim
        toks = cls._tokenize(text)
        if not toks:
            return vec
        for t in toks:
            h = hash(t) % dim
            vec[h] += 1.0
            # bigram boost for Chinese chars
            if len(t) == 1:
                continue
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    @staticmethod
    def cosine(a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        return float(sum(x * y for x, y in zip(a, b)))

    async def _try_external_embed(self, text: str) -> Optional[List[float]]:
        try:
            from utils.aliyun_embedding_client import aliyun_embedding_client

            emb = aliyun_embedding_client.embed_text(text[:2000])
            if emb and isinstance(emb, list) and len(emb) > 8:
                # normalize
                norm = math.sqrt(sum(v * v for v in emb)) or 1.0
                return [float(v) / norm for v in emb]
        except Exception:
            logger.debug("外部 embedding 不可用，回退本地向量", exc_info=True)
        return None

    async def _embed(self, text: str) -> Tuple[List[float], str]:
        ext = await self._try_external_embed(text)
        if ext:
            return ext, "external"
        return self.local_embed(text), "local"

    async def save_upload(
        self,
        drama_id: str,
        *,
        filename: str,
        raw: bytes,
        title: Optional[str] = None,
        tags: Optional[List[str]] = None,
        user_id: str = "default_user",
    ) -> Dict[str, Any]:
        await self._ensure_drama(drama_id)
        if len(raw) > MAX_UPLOAD_BYTES:
            raise ValueError(f"文件过大，上限 {MAX_UPLOAD_BYTES // (1024 * 1024)}MB")

        suffix = Path(filename or "script.txt").suffix.lower() or ".txt"
        if suffix not in ALLOWED_EXT:
            raise ValueError(f"不支持的格式 {suffix}，请上传: {', '.join(sorted(ALLOWED_EXT))}")

        text = self._decode_bytes(raw).strip()
        if not text:
            raise ValueError("文档内容为空")

        doc_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        doc_dir = self._doc_dir(drama_id, doc_id)
        doc_dir.mkdir(parents=True, exist_ok=True)

        chunks = self.chunk_text(text)
        indexed_chunks: List[Dict[str, Any]] = []
        embed_backend = "local"
        for ch in chunks:
            vec, backend = await self._embed(ch["content"])
            embed_backend = backend
            indexed_chunks.append({**ch, "embedding": vec, "embed_backend": backend})

        meta = {
            "id": doc_id,
            "drama_id": drama_id,
            "title": (title or Path(filename).stem or "未命名剧本").strip(),
            "filename": filename,
            "tags": tags or ["script", "upload"],
            "user_id": user_id,
            "char_count": len(text),
            "chunk_count": len(indexed_chunks),
            "embed_backend": embed_backend,
            "created_at": now,
            "updated_at": now,
            "preview": text[:240].replace("\n", " "),
        }

        async with aiofiles.open(doc_dir / "content.md", "w", encoding="utf-8") as f:
            await f.write(text)
        async with aiofiles.open(doc_dir / "meta.json", "w", encoding="utf-8") as f:
            await f.write(json.dumps(meta, ensure_ascii=False, indent=2))
        async with aiofiles.open(doc_dir / "chunks.json", "w", encoding="utf-8") as f:
            await f.write(json.dumps(indexed_chunks, ensure_ascii=False))

        logger.info(
            "剧本入库 %s/%s chunks=%s backend=%s",
            drama_id,
            doc_id,
            len(indexed_chunks),
            embed_backend,
        )
        return meta

    async def list_docs(self, drama_id: str) -> List[Dict[str, Any]]:
        await self._ensure_drama(drama_id)
        root = self._scripts_root(drama_id)
        items: List[Dict[str, Any]] = []
        if not root.exists():
            return items
        for d in sorted(root.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if not d.is_dir():
                continue
            meta_path = d / "meta.json"
            if not meta_path.exists():
                continue
            try:
                async with aiofiles.open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.loads(await f.read())
                items.append(meta)
            except Exception:
                logger.exception("读取剧本 meta 失败: %s", meta_path)
        return items

    async def get_doc(self, drama_id: str, doc_id: str, *, include_content: bool = True) -> Dict[str, Any]:
        await self._ensure_drama(drama_id)
        doc_dir = self._doc_dir(drama_id, doc_id)
        meta_path = doc_dir / "meta.json"
        if not meta_path.exists():
            raise ValueError("文档不存在")
        async with aiofiles.open(meta_path, "r", encoding="utf-8") as f:
            meta = json.loads(await f.read())
        if include_content:
            content_path = doc_dir / "content.md"
            content = ""
            if content_path.exists():
                async with aiofiles.open(content_path, "r", encoding="utf-8") as f:
                    content = await f.read()
            meta["content"] = content
        return meta

    async def delete_doc(self, drama_id: str, doc_id: str) -> bool:
        await self._ensure_drama(drama_id)
        doc_dir = self._doc_dir(drama_id, doc_id)
        if not doc_dir.exists():
            return False
        import shutil

        shutil.rmtree(doc_dir, ignore_errors=True)
        return True

    async def grep(
        self,
        drama_id: str,
        pattern: str,
        *,
        doc_id: Optional[str] = None,
        case_insensitive: bool = True,
        max_hits: int = 50,
    ) -> Dict[str, Any]:
        await self._ensure_drama(drama_id)
        flags = re.IGNORECASE if case_insensitive else 0
        try:
            rx = re.compile(pattern, flags)
        except re.error as e:
            raise ValueError(f"正则无效: {e}") from e

        docs = await self.list_docs(drama_id)
        if doc_id:
            docs = [d for d in docs if d.get("id") == doc_id]
        hits: List[Dict[str, Any]] = []
        for meta in docs:
            did = meta["id"]
            path = self._doc_dir(drama_id, did) / "content.md"
            if not path.exists():
                continue
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                text = await f.read()
            for i, line in enumerate(text.splitlines(), 1):
                if rx.search(line):
                    hits.append(
                        {
                            "doc_id": did,
                            "title": meta.get("title"),
                            "line": i,
                            "text": line.strip()[:300],
                            "mode": "grep",
                        }
                    )
                    if len(hits) >= max_hits:
                        return {"mode": "grep", "query": pattern, "total": len(hits), "hits": hits}
        return {"mode": "grep", "query": pattern, "total": len(hits), "hits": hits}

    async def vector_search(
        self,
        drama_id: str,
        query: str,
        *,
        doc_id: Optional[str] = None,
        top_k: int = 8,
    ) -> Dict[str, Any]:
        await self._ensure_drama(drama_id)
        q = (query or "").strip()
        if not q:
            raise ValueError("query 不能为空")
        q_vec, backend = await self._embed(q)

        docs = await self.list_docs(drama_id)
        if doc_id:
            docs = [d for d in docs if d.get("id") == doc_id]

        scored: List[Dict[str, Any]] = []
        for meta in docs:
            did = meta["id"]
            chunks_path = self._doc_dir(drama_id, did) / "chunks.json"
            if not chunks_path.exists():
                continue
            async with aiofiles.open(chunks_path, "r", encoding="utf-8") as f:
                chunks = json.loads(await f.read())
            for ch in chunks:
                emb = ch.get("embedding") or []
                # dimension mismatch → re-embed with local
                if len(emb) != len(q_vec):
                    emb = self.local_embed(ch.get("content") or "")
                    score = self.cosine(self.local_embed(q), emb)
                else:
                    score = self.cosine(q_vec, emb)
                if score <= 0:
                    continue
                scored.append(
                    {
                        "doc_id": did,
                        "title": meta.get("title"),
                        "chunk_id": ch.get("chunk_id"),
                        "score": round(score, 4),
                        "text": (ch.get("content") or "")[:500],
                        "mode": "vector",
                        "embed_backend": backend,
                    }
                )

        scored.sort(key=lambda x: x["score"], reverse=True)
        hits = scored[: max(1, min(top_k, 50))]
        return {
            "mode": "vector",
            "query": q,
            "total": len(hits),
            "embed_backend": backend,
            "hits": hits,
        }

    async def search(
        self,
        drama_id: str,
        query: str,
        *,
        mode: str = "hybrid",
        doc_id: Optional[str] = None,
        top_k: int = 10,
        case_insensitive: bool = True,
    ) -> Dict[str, Any]:
        mode = (mode or "hybrid").lower()
        if mode == "grep":
            return await self.grep(
                drama_id, query, doc_id=doc_id, case_insensitive=case_insensitive, max_hits=top_k
            )
        if mode == "vector":
            return await self.vector_search(drama_id, query, doc_id=doc_id, top_k=top_k)

        # hybrid: merge grep + vector
        g = await self.grep(
            drama_id, re.escape(query) if query else "", doc_id=doc_id, max_hits=top_k
        )
        # if query looks like regex intent, also try raw
        if not g["hits"] and any(c in query for c in ".*+?[]()"):
            try:
                g = await self.grep(drama_id, query, doc_id=doc_id, max_hits=top_k)
            except ValueError:
                pass
        v = await self.vector_search(drama_id, query, doc_id=doc_id, top_k=top_k)

        seen = set()
        merged: List[Dict[str, Any]] = []
        for hit in v.get("hits", []) + g.get("hits", []):
            key = (hit.get("doc_id"), hit.get("text", "")[:80])
            if key in seen:
                continue
            seen.add(key)
            merged.append(hit)
            if len(merged) >= top_k:
                break
        return {
            "mode": "hybrid",
            "query": query,
            "total": len(merged),
            "embed_backend": v.get("embed_backend"),
            "hits": merged,
            "grep_total": g.get("total", 0),
            "vector_total": v.get("total", 0),
        }


_lib: Optional[ScriptLibrary] = None


def get_script_library() -> ScriptLibrary:
    global _lib
    if _lib is None:
        _lib = ScriptLibrary()
    return _lib
