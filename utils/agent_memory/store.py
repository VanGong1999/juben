"""
Markdown-as-SoT 文件系统存储
作品级: projects/{drama_id}/memory/
用户级: data/users/{user_id}/memory/
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .types import SCHEMA_VERSION
from utils.atomic_write import atomic_write_text

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

DEFAULT_DRAMA_RULES = """# 作品规则（RULES）— 必须遵守

## 平台与格式
- 竖屏短剧：对白驱动，动作提示简洁，单集信息密度高。
- 黄金三秒内建立冲突或期待；集末必须留商业化卡点。

## 连续性
- 人物性格、称呼、已公开设定不得无故推翻（除非标注「反转计划」）。
- 未回收的悬念记入语义事实 `open_thread`，写下一集前必须检索。

## 治理红线
- 不擅自改动已定台词风格偏好（以 USER / MEMORY 为准）。
- Bible 与语义事实冲突时：以更新时间更新的为准，并写入 superseded。
- 涉及人物死亡 / 重大人设崩坏：标记 `must_confirm`，需用户确认。

## 写入规范
- 只把「长期稳定」写入 RULES / MEMORY；过程细节写入 episodes。
- 事实必须带 provenance（来源 session / bible / 用户修正）。
"""

DEFAULT_USER_MD = """# USER — 用户常驻画像

> 只放身份、偏好、不变量。历史细节不要写在这里。

## 偏好题材
（待补充）

## 回避桥段
（待补充）

## 语言风格
（待补充）

## 沟通期待
- 先给可拍的结构，再展开对白。
"""

DEFAULT_MEMORY_MD = """# MEMORY — Agent 常驻笔记

> 短、硬、高密度。超长请拆到 topics/。

## 作品阶段
（策划 / 大纲 / 连载 / 评估）

## 当前不变量
-

## 已知坑
-

## 下一轮接着做
-
"""

DEFAULT_ORG_MD = """# ORG — 组织级共享记忆

> 跨智能体共同维护的工作室级共识：平台规则、最佳实践、跨作品教训。
> 只放长期稳定、可复用的内容；单作品细节放各自 memory/。

## 平台规则
（待补充）

## 最佳实践
（待补充）

## 跨作品教训
（待补充）
"""


class MemoryStore:
    def __init__(self, workspace_root: Optional[Path] = None):
        self.root = Path(workspace_root or REPO_ROOT)
        # 每作品/用户/org 一把进程内重入锁：串行化「读→写→快照→索引」整段，
        # 避免多 Agent 并发写同一文件互相覆盖（同步文件 I/O 场景）。
        self._locks: Dict[str, threading.RLock] = {}
        self._locks_guard = threading.Lock()

    # ---------- locks ----------
    def lock_for(self, key: str) -> threading.RLock:
        with self._locks_guard:
            lock = self._locks.get(key)
            if lock is None:
                lock = threading.RLock()
                self._locks[key] = lock
            return lock

    # ---------- paths ----------
    def drama_memory_dir(self, drama_id: str) -> Path:
        p = self.root / "projects" / drama_id / "memory"
        p.mkdir(parents=True, exist_ok=True)
        (p / "episodes").mkdir(exist_ok=True)
        (p / "topics").mkdir(exist_ok=True)
        return p

    def user_memory_dir(self, user_id: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in user_id)[:64]
        p = self.root / "data" / "users" / safe / "memory"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def org_memory_dir(self) -> Path:
        p = self.root / "data" / "org" / "memory"
        p.mkdir(parents=True, exist_ok=True)
        (p / "episodes").mkdir(exist_ok=True)
        (p / "versions").mkdir(exist_ok=True)
        return p

    def ensure_org_scaffold(self) -> Path:
        d = self.org_memory_dir()
        org_md = d / "ORG.md"
        semantic = d / "semantic.json"
        skills = d / "skills.json"
        audit = d / "audit.jsonl"
        reflections = d / "reflections.jsonl"
        if not org_md.exists():
            org_md.write_text(DEFAULT_ORG_MD, encoding="utf-8")
        if not semantic.exists():
            semantic.write_text(
                json.dumps({"schema_version": SCHEMA_VERSION, "facts": []}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        if not skills.exists():
            skills.write_text(
                json.dumps({"schema_version": SCHEMA_VERSION, "skills": []}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        if not audit.exists():
            audit.write_text("", encoding="utf-8")
        if not reflections.exists():
            reflections.write_text("", encoding="utf-8")
        return d

    def meta_path(self, drama_id: str) -> Path:
        return self.drama_memory_dir(drama_id) / "memory_meta.json"

    def read_meta(self, drama_id: str) -> Dict[str, Any]:
        return self.read_json(self.meta_path(drama_id), default={}) or {}

    def write_meta(self, drama_id: str, meta: Dict[str, Any]) -> None:
        self.write_json(self.meta_path(drama_id), meta)

    def versions_dir(self, drama_id: str) -> Path:
        p = self.drama_memory_dir(drama_id) / "versions"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def ensure_drama_scaffold(self, drama_id: str) -> Path:
        d = self.drama_memory_dir(drama_id)
        rules = d / "RULES.md"
        mem = d / "MEMORY.md"
        semantic = d / "semantic.json"
        skills = d / "skills.json"
        index = d / "index.md"
        reflections = d / "reflections.jsonl"
        audit = d / "audit.jsonl"
        (d / "evidence").mkdir(exist_ok=True)
        if not rules.exists():
            rules.write_text(DEFAULT_DRAMA_RULES, encoding="utf-8")
        if not mem.exists():
            mem.write_text(DEFAULT_MEMORY_MD, encoding="utf-8")
        if not semantic.exists():
            semantic.write_text(
                json.dumps({"schema_version": SCHEMA_VERSION, "facts": []}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        if not skills.exists():
            skills.write_text(
                json.dumps({"schema_version": SCHEMA_VERSION, "skills": []}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        meta = self.meta_path(drama_id)
        if not meta.exists():
            self.write_meta(
                drama_id,
                {
                    "schema_version": SCHEMA_VERSION,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "head_version": 0,
                },
            )
        if not index.exists():
            index.write_text(
                "# Memory Index\n\n"
                "- RULES.md — 常驻规则（短）\n"
                "- MEMORY.md — 常驻索引页（短）\n"
                "- semantic.json — 语义事实+证据\n"
                "- episodes/ — 情节（可搜、可归档）\n"
                "- reflections.jsonl — 成败归因\n"
                "- skills.json — 晋升程序记忆\n"
                "- vector_index.json — ANN 召回\n"
                "- audit.jsonl — 变更审计\n"
                "- topics/ — 超长细节拆页\n"
                "- evidence/ — 原文指针落盘\n",
                encoding="utf-8",
            )
        if not reflections.exists():
            reflections.write_text("", encoding="utf-8")
        if not audit.exists():
            audit.write_text("", encoding="utf-8")
        # 幂等迁移旧文件到当前 schema（缺字段走默认值）
        self.migrate(drama_id)
        return d

    def migrate(self, drama_id: str) -> Dict[str, Any]:
        """幂等升级旧文件到当前 schema（裸 facts / 缺双时态与强度字段）。"""
        d = self.drama_memory_dir(drama_id)
        changed = False

        meta = self.read_meta(drama_id)
        if meta.get("schema_version") != SCHEMA_VERSION:
            meta["schema_version"] = SCHEMA_VERSION
            changed = True
        if "head_version" not in meta:
            meta["head_version"] = 0
            changed = True
        meta.setdefault("created_at", datetime.now().isoformat())
        meta["updated_at"] = datetime.now().isoformat()
        self.write_meta(drama_id, meta)

        sp = d / "semantic.json"
        data = self.read_json(sp, {"facts": []})
        if data.get("schema_version") != SCHEMA_VERSION:
            data["schema_version"] = SCHEMA_VERSION
            changed = True
        facts = data.get("facts") or []
        for f in facts:
            if "valid_from" not in f:
                f["valid_from"] = f.get("created_at") or datetime.now().isoformat()
                changed = True
            for k, default in (("valid_until", None), ("access_count", 0), ("last_access", None), ("strength", 1.0)):
                if k not in f:
                    f[k] = default
                    changed = True
        self.write_json(sp, data)

        sk = d / "skills.json"
        sdata = self.read_json(sk, {"skills": []})
        if sdata.get("schema_version") != SCHEMA_VERSION:
            sdata["schema_version"] = SCHEMA_VERSION
            changed = True
        self.write_json(sk, sdata)

        return {"drama_id": drama_id, "migrated": changed, "schema_version": SCHEMA_VERSION}

    def ensure_user_scaffold(self, user_id: str) -> Path:
        d = self.user_memory_dir(user_id)
        user_md = d / "USER.md"
        if not user_md.exists():
            user_md.write_text(DEFAULT_USER_MD, encoding="utf-8")
        return d

    # ---------- text files ----------
    def read_text(self, path: Path, default: str = "") -> str:
        try:
            if path.exists():
                return path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning("read_text failed %s: %s", path, e)
        return default

    def write_text(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(path, content)

    # ---------- json ----------
    def read_json(self, path: Path, default: Any = None) -> Any:
        if default is None:
            default = {}
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("read_json failed %s: %s", path, e)
        return default

    def write_json(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=2))

    # ---------- jsonl episodes ----------
    def append_jsonl(self, path: Path, record: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def read_jsonl(self, path: Path, limit: int = 500) -> List[Dict[str, Any]]:
        if not path.exists():
            return []
        rows: List[Dict[str, Any]] = []
        try:
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.warning("read_jsonl failed %s: %s", path, e)
        return rows[-limit:]

    def episode_day_path(self, drama_id: str, day: Optional[str] = None) -> Path:
        day = day or datetime.now().strftime("%Y-%m-%d")
        return self.drama_memory_dir(drama_id) / "episodes" / f"{day}.jsonl"

    def list_episode_files(self, drama_id: str) -> List[Path]:
        ep_dir = self.drama_memory_dir(drama_id) / "episodes"
        return sorted(p for p in ep_dir.glob("*.jsonl") if not p.name.startswith("_"))

    def audit_path(self, drama_id: str) -> Path:
        return self.drama_memory_dir(drama_id) / "audit.jsonl"

    def reflections_path(self, drama_id: str) -> Path:
        return self.drama_memory_dir(drama_id) / "reflections.jsonl"

    def evidence_path(self, drama_id: str, evidence_id: str) -> Path:
        return self.drama_memory_dir(drama_id) / "evidence" / f"{evidence_id}.md"

    def read_slice(self, path: Path, *, offset: int = 0, length: int = 2000) -> str:
        """局部读取文件切片 — 历史记忆不全量进上下文。"""
        text = self.read_text(path)
        if not text:
            return ""
        offset = max(0, offset)
        length = max(1, min(length, 20000))
        return text[offset : offset + length]
