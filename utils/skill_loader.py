"""
Skills 加载器 — Claude Code 风格 Markdown Skill 包

注入策略（渐进式披露 / prompt-cache 友好）：
- 默认 catalog：只注入 id/name/summary 名录（Deferred Skills）
- 需要正文时用 load_skill / skill_search，或 include_body=True / mode="full"
- 优先使用 frontmatter summary，控制动态后缀体积
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"


def _parse_frontmatter(text: str) -> tuple[Dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta: Dict[str, Any] = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta, parts[2].strip()


def _as_bool(val: Any, default: bool = True) -> bool:
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    return str(val).strip().lower() not in {"false", "0", "no", "off"}


def _as_int(val: Any, default: int = 50) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _parse_bind(val: Any) -> List[str]:
    """解析 frontmatter 里的 bind（[a, b] / 'a, b' / 'a b'）。"""
    if not val:
        return []
    if isinstance(val, (list, tuple)):
        return [str(x).strip() for x in val if str(x).strip()]
    text = str(val).strip().strip("[]")
    return [p.strip() for p in re.split(r"[, ]+", text) if p.strip()]


def list_skills(skills_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    root = skills_dir or SKILLS_DIR
    root.mkdir(parents=True, exist_ok=True)
    skills: List[Dict[str, Any]] = []
    # Claude Code 风格：skills/<name>/SKILL.md（每个技能一个目录）
    for path in sorted(root.glob("*/SKILL.md")):
        try:
            text = path.read_text(encoding="utf-8")
            meta, body = _parse_frontmatter(text)
            skills.append(
                {
                    "id": meta.get("id") or path.parent.name,
                    "name": meta.get("name") or path.parent.name,
                    "description": meta.get("description") or body[:120].replace("\n", " "),
                    "summary": meta.get("summary") or meta.get("description") or "",
                    "category": meta.get("category") or "general",
                    "priority": _as_int(meta.get("priority"), 50),
                    "enabled": _as_bool(meta.get("enabled"), True),
                    "bind": _parse_bind(meta.get("bind")),
                    "body": body,
                    "path": str(path),
                    "source": meta.get("source") or "",
                }
            )
        except Exception as e:
            logger.warning("加载 skill 失败 %s: %s", path, e)
    skills.sort(key=lambda s: (-int(s.get("priority") or 0), str(s.get("id") or "")))
    return skills


def skills_for_agent(agent_id: str, skills_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """返回绑定到指定 agent 的 skills（按 priority 降序）。"""
    from utils.agent_runtime import normalize_agent_id

    aid = normalize_agent_id(agent_id or "")
    if not aid:
        return []
    hits: List[Dict[str, Any]] = []
    for s in list_skills(skills_dir):
        if not s.get("enabled"):
            continue
        binds = {normalize_agent_id(b) for b in (s.get("bind") or [])}
        if aid in binds:
            hits.append(s)
    return hits


def get_skill(skill_id: str, skills_dir: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    for s in list_skills(skills_dir):
        if s.get("id") == skill_id:
            return s
    return None


def build_skills_prompt(
    enabled_only: bool = True,
    max_chars: int = 6000,
    *,
    include_body: bool = False,
    compact: bool = True,
    ids: Optional[List[str]] = None,
    mode: str = "catalog",
) -> str:
    """
    组装 Skills 提示块。

    mode:
      - catalog（默认）：只注入名录，完整正文靠 skill_search / load_skill
      - full：注入正文（专项写作 / 显式 opt-in）
    compact=True：id/name/summary 一行
    include_body=True：等价于 mode=full（兼容旧调用）
    """
    if include_body or mode == "full":
        compact = False
        include_body = True
    else:
        # 默认渐进式披露
        compact = True
        include_body = False

    skills = list_skills()
    if enabled_only:
        skills = [s for s in skills if s.get("enabled")]
    if ids:
        allow = set(ids)
        skills = [s for s in skills if s.get("id") in allow]
    if not skills:
        return ""

    if compact and not include_body:
        chunks = [
            "## Deferred Skills（名录）",
            "完整 checklist 请调用工具 `skill_search` 或 `load_skill(skill_id=...)`。",
        ]
        used = sum(len(c) + 1 for c in chunks)
        for s in skills:
            block = f"- **{s['name']}** (`{s['id']}`): {s.get('summary') or s.get('description')}\n"
            if used + len(block) > max_chars:
                break
            chunks.append(block)
            used += len(block)
        return "\n".join(chunks)

    chunks = ["## Active Skills"]
    used = len(chunks[0])
    for s in skills:
        if include_body:
            body = (s.get("body") or "").strip()
            block = f"### {s['name']}\n{body}\n"
        else:
            block = f"### {s['name']}\n{s.get('summary') or s.get('description')}\n"

        if used + len(block) > max_chars:
            short = f"- **{s['name']}**: {s.get('summary') or s.get('description')}\n"
            if used + len(short) <= max_chars:
                chunks.append(short)
                used += len(short)
            break
        chunks.append(block)
        used += len(block)
    return "\n".join(chunks)
