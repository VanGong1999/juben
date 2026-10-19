"""
LLM Wiki 文件系统存储

目录：
  data/knowledge/
    raw/                 # L3 原文（immutable）
    wiki/
      index.md           # L1 目录
      log.md             # 追加日志
      overview.md
      concepts|entities|sources|craft|…
    SCHEMA.md
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = PROJECT_ROOT / "data" / "knowledge"

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


@dataclass
class WikiPageMeta:
    slug: str
    title: str
    summary: str
    category: str = "concepts"
    cache_tier: str = "L3"  # L1|L2|L3|L4
    tags: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)  # relative raw paths
    path: str = ""  # relative to wiki/

    def index_line(self) -> str:
        link = f"[[{self.path or self.slug}]]"
        return f"- {link} — {self.summary or self.title}"


def _parse_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    m = FRONTMATTER_RE.match(text.strip())
    if not m:
        return {}, text
    meta: Dict[str, Any] = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        key = k.strip()
        val = v.strip().strip('"').strip("'")
        if key in ("tags", "sources") and val.startswith("["):
            inner = val.strip("[]")
            meta[key] = [x.strip().strip('"').strip("'") for x in inner.split(",") if x.strip()]
        else:
            meta[key] = val
    return meta, m.group(2).strip()


def _dump_frontmatter(meta: Dict[str, Any], body: str) -> str:
    lines = ["---"]
    for k, v in meta.items():
        if isinstance(v, list):
            lines.append(f"{k}: [{', '.join(str(x) for x in v)}]")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append("")
    lines.append(body.rstrip() + "\n")
    return "\n".join(lines)


class LlmWikiStore:
    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = Path(root) if root else DEFAULT_ROOT
        self.raw_dir = self.root / "raw"
        self.wiki_dir = self.root / "wiki"
        self.schema_path = self.root / "SCHEMA.md"
        self.index_path = self.wiki_dir / "index.md"
        self.log_path = self.wiki_dir / "log.md"
        self.overview_path = self.wiki_dir / "overview.md"

    def _mkdirs(self) -> None:
        for d in (
            self.raw_dir,
            self.wiki_dir,
            self.wiki_dir / "concepts",
            self.wiki_dir / "entities",
            self.wiki_dir / "sources",
            self.wiki_dir / "craft",
        ):
            d.mkdir(parents=True, exist_ok=True)

    def ensure_layout(self) -> None:
        self._mkdirs()
        if not self.schema_path.exists():
            self.schema_path.write_text(_SCHEMA_TEMPLATE, encoding="utf-8")
        if not self.overview_path.exists():
            self.overview_path.write_text(_OVERVIEW_TEMPLATE, encoding="utf-8")
        if not self.log_path.exists():
            self.log_path.write_text("# Wiki Log\n\n", encoding="utf-8")
        if not self.index_path.exists():
            self.rebuild_index()

    def append_log(self, message: str) -> None:
        self._mkdirs()
        if not self.log_path.exists():
            self.log_path.write_text("# Wiki Log\n\n", encoding="utf-8")
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(f"- [{ts}] {message}\n")

    def list_wiki_pages(self) -> List[WikiPageMeta]:
        self._mkdirs()
        pages: List[WikiPageMeta] = []
        skip = {"index.md", "log.md"}
        for path in sorted(self.wiki_dir.rglob("*.md")):
            if path.name in skip:
                continue
            rel = path.relative_to(self.wiki_dir).as_posix()
            try:
                text = path.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning("read wiki page failed %s: %s", path, e)
                continue
            fm, body = _parse_frontmatter(text)
            slug = str(fm.get("slug") or path.stem)
            title = str(fm.get("title") or path.stem)
            summary = str(fm.get("summary") or "").strip()
            if not summary:
                # 取正文首句
                for line in body.splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and not line.startswith(">"):
                        summary = line[:120]
                        break
            if not summary:
                summary = title
            category = str(fm.get("category") or path.parent.name if path.parent != self.wiki_dir else "general")
            tags = fm.get("tags") if isinstance(fm.get("tags"), list) else []
            sources = fm.get("sources") if isinstance(fm.get("sources"), list) else []
            pages.append(
                WikiPageMeta(
                    slug=slug,
                    title=title,
                    summary=summary,
                    category=category,
                    cache_tier=str(fm.get("cache_tier") or "L3"),
                    tags=[str(t) for t in tags],
                    sources=[str(s) for s in sources],
                    path=rel,
                )
            )
        return pages

    def rebuild_index(self) -> str:
        """从各页 frontmatter 重建 index.md（cache，非真相源）。"""
        self._mkdirs()
        pages = self.list_wiki_pages()
        by_cat: Dict[str, List[WikiPageMeta]] = {}
        for p in pages:
            by_cat.setdefault(p.category or "general", []).append(p)

        lines = [
            "---",
            "cache_tier: L1",
            "title: Wiki Index",
            "summary: 知识库目录——每页一行链接与摘要；Agent 每次会话先读此文件",
            "---",
            "",
            "# Wiki Index",
            "",
            "本文件是知识库 **L1 目录**（常驻 prompt）。",
            "每行：`[[相对路径]]` — 一句话摘要。",
            "需要细节时用工具 `wiki_read(path=...)` 打开对应 wiki 页；",
            "wiki 仍不够时再用 `raw_read(path=...)` 读 `raw/` 原文。",
            "",
            f"_pages: {len(pages)} · rebuilt: {datetime.now().isoformat(timespec='seconds')}_",
            "",
        ]
        order = ["craft", "concepts", "entities", "sources", "general"]
        cats = list(dict.fromkeys([*order, *sorted(by_cat.keys())]))
        for cat in cats:
            items = by_cat.get(cat) or []
            if not items:
                continue
            lines.append(f"## {cat}")
            lines.append("")
            for p in items:
                lines.append(p.index_line())
            lines.append("")

        if not pages:
            lines.extend(
                [
                    "## craft",
                    "",
                    "- （空）请先 ingest 原文或创建 wiki 页",
                    "",
                ]
            )

        text = "\n".join(lines).rstrip() + "\n"
        self.index_path.write_text(text, encoding="utf-8")
        self.append_log(f"rebuild_index pages={len(pages)}")
        return text

    def read_index(self, *, max_chars: int = 8000) -> str:
        self._mkdirs()
        if not self.index_path.exists():
            self.rebuild_index()
        text = self.index_path.read_text(encoding="utf-8")
        if len(text) > max_chars:
            return text[: max_chars - 40] + "\n\n...[index truncated]...\n"
        return text

    def resolve_wiki_path(self, path_or_slug: str) -> Optional[Path]:
        raw = (path_or_slug or "").strip().strip("[]")
        if not raw:
            return None
        raw = raw.replace("wiki/", "", 1)
        candidates = [
            self.wiki_dir / raw,
            self.wiki_dir / f"{raw}.md",
        ]
        # slug search
        for p in self.wiki_dir.rglob("*.md"):
            if p.stem == raw or p.relative_to(self.wiki_dir).as_posix() == raw:
                candidates.append(p)
        for c in candidates:
            if c.exists() and c.is_file():
                return c
        return None

    def read_wiki_page(self, path_or_slug: str, *, max_chars: int = 20000) -> Dict[str, Any]:
        path = self.resolve_wiki_path(path_or_slug)
        if not path:
            return {"ok": False, "error": f"wiki 页不存在: {path_or_slug}"}
        text = path.read_text(encoding="utf-8")
        fm, body = _parse_frontmatter(text)
        rel = path.relative_to(self.wiki_dir).as_posix()
        truncated = False
        if len(text) > max_chars:
            text = text[: max_chars - 40] + "\n\n...[truncated]...\n"
            truncated = True
        return {
            "ok": True,
            "path": rel,
            "frontmatter": fm,
            "body": body,
            "content": text,
            "sources": fm.get("sources") or [],
            "truncated": truncated,
        }

    def write_wiki_page(
        self,
        *,
        category: str,
        slug: str,
        title: str,
        summary: str,
        body: str,
        tags: Optional[List[str]] = None,
        sources: Optional[List[str]] = None,
        cache_tier: str = "L3",
        rebuild_index: bool = True,
    ) -> Dict[str, Any]:
        self._mkdirs()
        cat = (category or "concepts").strip().strip("/")
        safe_slug = re.sub(r"[^\w\-]+", "-", slug.strip(), flags=re.UNICODE).strip("-").lower()
        if not safe_slug:
            return {"ok": False, "error": "slug 无效"}
        dest_dir = self.wiki_dir / cat
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{safe_slug}.md"
        meta = {
            "slug": safe_slug,
            "title": title,
            "summary": summary,
            "category": cat,
            "cache_tier": cache_tier or "L3",
            "tags": tags or [],
            "sources": sources or [],
            "updated": datetime.now().isoformat(timespec="seconds"),
        }
        dest.write_text(_dump_frontmatter(meta, body), encoding="utf-8")
        rel = dest.relative_to(self.wiki_dir).as_posix()
        self.append_log(f"write_wiki {rel}")
        if rebuild_index:
            self.rebuild_index()
        return {"ok": True, "path": rel, "meta": meta}

    def list_raw(self) -> List[Dict[str, str]]:
        self._mkdirs()
        items = []
        for p in sorted(self.raw_dir.rglob("*")):
            if p.is_file() and p.suffix.lower() in {".md", ".txt", ".json", ".csv"}:
                items.append(
                    {
                        "path": p.relative_to(self.raw_dir).as_posix(),
                        "size": str(p.stat().st_size),
                    }
                )
        return items

    def resolve_raw_path(self, path: str) -> Optional[Path]:
        raw = (path or "").strip().lstrip("/")
        raw = raw.replace("raw/", "", 1)
        candidate = (self.raw_dir / raw).resolve()
        try:
            candidate.relative_to(self.raw_dir.resolve())
        except ValueError:
            return None
        return candidate if candidate.exists() and candidate.is_file() else None

    def read_raw(self, path: str, *, max_chars: int = 30000) -> Dict[str, Any]:
        p = self.resolve_raw_path(path)
        if not p:
            return {"ok": False, "error": f"原文不存在: {path}"}
        text = p.read_text(encoding="utf-8", errors="replace")
        truncated = False
        if len(text) > max_chars:
            text = text[: max_chars - 40] + "\n\n...[truncated]...\n"
            truncated = True
        return {
            "ok": True,
            "path": p.relative_to(self.raw_dir).as_posix(),
            "content": text,
            "truncated": truncated,
        }

    def write_raw(self, relative_path: str, content: str, *, overwrite: bool = False) -> Dict[str, Any]:
        """写入原文（ingest 用）。默认不覆盖。"""
        self._mkdirs()
        rel = relative_path.strip().lstrip("/").replace("raw/", "", 1)
        dest = (self.raw_dir / rel).resolve()
        try:
            dest.relative_to(self.raw_dir.resolve())
        except ValueError:
            return {"ok": False, "error": "路径越界"}
        if dest.exists() and not overwrite:
            return {"ok": False, "error": f"原文已存在: {rel}"}
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        self.append_log(f"write_raw {rel}")
        return {"ok": True, "path": rel}

    def search_index(self, query: str, *, limit: int = 10) -> List[WikiPageMeta]:
        q = (query or "").strip().lower()
        pages = self.list_wiki_pages()
        if not q:
            return pages[:limit]
        tokens = [t for t in re.split(r"[\s,;/|]+", q) if t]
        scored: List[Tuple[int, WikiPageMeta]] = []
        for p in pages:
            blob = f"{p.slug} {p.title} {p.summary} {p.category} {' '.join(p.tags)}".lower()
            score = sum(1 for t in tokens if t in blob)
            if score:
                scored.append((score, p))
        scored.sort(key=lambda x: (-x[0], x[1].path))
        return [p for _, p in scored[:limit]]

    def stats(self) -> Dict[str, Any]:
        self._mkdirs()
        pages = self.list_wiki_pages()
        return {
            "root": str(self.root),
            "wiki_pages": len(pages),
            "raw_files": len(self.list_raw()),
            "index_chars": self.index_path.stat().st_size if self.index_path.exists() else 0,
            "categories": sorted({p.category for p in pages}),
        }


_SCHEMA_TEMPLATE = """# LLM Wiki Schema（剧本工坊）

## 三级缓存

| 层 | 路径 | 何时加载 |
|----|------|----------|
| L1 | `wiki/index.md` | **每次会话常驻 prompt**（目录：链接 + 一句话摘要） |
| L2 | `wiki/**/*.md` | Agent 从 index 定位后 `wiki_read` 按需读取 |
| L3 | `raw/**` | 仅当 wiki 页信息不够时 `raw_read` |

## 页面约定

- frontmatter 必填：`slug`, `title`, `summary`, `category`, `cache_tier`
- `sources:` 列出对应 `raw/` 相对路径
- 正文用 Markdown；互相引用写成 `[[craft/hook-3s.md]]`

## 操作

1. **查询**：先看 session 里的 index → `wiki_read` →（可选）`raw_read`
2. **入库**：`raw` 写入原文 → 生成/更新 wiki 页 → `rebuild_index`
3. **勿**把整库或全量 raw 灌进 prompt
"""

_OVERVIEW_TEMPLATE = """---
slug: overview
title: 知识库总览
summary: 剧本工坊 LLM Wiki 总览：短剧技法、桥段、评估标准与来源摘要
category: general
cache_tier: L1
tags: [overview]
---

# 知识库总览

本知识库采用 **llm-wiki 三级缓存**：

1. **index.md**（你已在 system 中看到）— 目录
2. **wiki 页** — 整理后的可引用知识
3. **raw/** — 原始资料，按需下钻

优先阅读 `craft/` 下的短剧技法页；评估类见 `concepts/`。
"""


_store: Optional[LlmWikiStore] = None


def get_llm_wiki_store(root: Optional[Path] = None) -> LlmWikiStore:
    global _store
    if root is not None:
        return LlmWikiStore(root)
    if _store is None:
        _store = LlmWikiStore()
        _store.ensure_layout()
    return _store
