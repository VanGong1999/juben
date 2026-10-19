"""
短剧文件夹管理器 — 一剧一文件夹 · 分集连载
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles

from utils.atomic_write import atomic_write_text_async

logger = logging.getLogger(__name__)

AUTO_WRITE_JOBS: Dict[str, Dict[str, Any]] = {}

# 作品/run id 只允许安全字符，防御路径穿越（../、绝对路径等）
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")


def _safe_id(id_value: str) -> str:
    if not id_value or not _ID_RE.match(id_value):
        raise ValueError(f"非法 ID: {id_value!r}")
    return id_value


class DramaManager:
    """管理 projects/{id}/ 下的 drama 骨架与分集文件"""

    def __init__(self, base_dir: str = "projects"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)

    def _dir(self, drama_id: str) -> Path:
        return self.base_dir / _safe_id(drama_id)

    def _drama_json(self, drama_id: str) -> Path:
        return self._dir(drama_id) / "drama.json"

    async def create_drama(
        self,
        title: str,
        description: str = "",
        genre: str = "都市情感",
        total_episodes: int = 80,
        tags: Optional[List[str]] = None,
        user_id: str = "default_user",
        type: str = "short_drama",
    ) -> Dict[str, Any]:
        drama_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        root = self._dir(drama_id)
        for sub in (
            "bible",
            "outline",
            "episodes",
            "video_prompts",
            "memory",
            "exports",
            "agent_outputs",
        ):
            (root / sub).mkdir(parents=True, exist_ok=True)

        meta = {
            "id": drama_id,
            "title": title,
            "description": description,
            "genre": genre,
            "total_episodes": int(total_episodes) or 80,
            "current_episode": 0,
            "completed_episodes": 0,
            "status": "draft",
            "model": "deepseek-flash",
            "tags": tags or [],
            "user_id": user_id,
            "type": type or "short_drama",
            "created_at": now,
            "updated_at": now,
        }

        async with aiofiles.open(self._drama_json(drama_id), "w", encoding="utf-8") as f:
            await f.write(json.dumps(meta, ensure_ascii=False, indent=2))

        # Also write legacy project.json for compatibility
        project = {
            "id": drama_id,
            "name": title,
            "description": description,
            "user_id": user_id,
            "created_at": now,
            "updated_at": now,
            "status": "active",
            "tags": tags or ["drama"],
            "metadata": {
                "total_episodes": meta["total_episodes"],
                "genre": genre,
                "kind": type or "short_drama",
            },
            "file_count": 0,
        }
        async with aiofiles.open(root / "project.json", "w", encoding="utf-8") as f:
            await f.write(json.dumps(project, ensure_ascii=False, indent=2))

        async with aiofiles.open(root / "bible" / "characters.md", "w", encoding="utf-8") as f:
            await f.write(f"# {title} · 人物设定\n\n")
        async with aiofiles.open(root / "bible" / "world.md", "w", encoding="utf-8") as f:
            await f.write(f"# {title} · 世界观\n\n")
        async with aiofiles.open(root / "bible" / "constraints.json", "w", encoding="utf-8") as f:
            await f.write(json.dumps({"constraints": []}, ensure_ascii=False, indent=2))
        async with aiofiles.open(root / "outline" / "series_outline.md", "w", encoding="utf-8") as f:
            await f.write("")
        async with aiofiles.open(root / "outline" / "episode_beats.json", "w", encoding="utf-8") as f:
            await f.write(json.dumps({"episodes": []}, ensure_ascii=False, indent=2))

        # 五层记忆脚手架（RULES / MEMORY / semantic / episodes）
        try:
            from utils.agent_memory import get_agent_memory_service

            get_agent_memory_service().ensure(user_id=user_id, drama_id=drama_id)
        except Exception:
            logger.exception("初始化作品记忆失败")

        # Placeholder episode index files are virtual; status derived from disk
        logger.info("创建短剧文件夹: %s (%s)", title, drama_id)
        return meta

    async def list_dramas(
        self,
        type_filter: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        dramas: List[Dict[str, Any]] = []
        if not self.base_dir.exists():
            return dramas
        for path in sorted(self.base_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if not path.is_dir():
                continue
            try:
                meta = await self._load_meta(path.name)
            except ValueError:
                logger.warning("跳过非法作品目录: %s", path.name)
                continue
            if not meta:
                continue
            if type_filter and meta.get("type", "short_drama") != type_filter:
                continue
            if user_id and meta.get("user_id") != user_id:
                continue
            dramas.append(meta)
        return dramas

    async def _load_meta(self, drama_id: str) -> Optional[Dict[str, Any]]:
        dj = self._drama_json(drama_id)
        if dj.exists():
            async with aiofiles.open(dj, "r", encoding="utf-8") as f:
                meta = json.loads(await f.read())
        else:
            # Migrate from project.json if tagged as drama or any project
            pj = self._dir(drama_id) / "project.json"
            if not pj.exists():
                return None
            async with aiofiles.open(pj, "r", encoding="utf-8") as f:
                raw = (await f.read()).strip()
                if not raw:
                    return None
                project = json.loads(raw)
            md = project.get("metadata") or {}
            meta = {
                "id": drama_id,
                "title": project.get("name") or "未命名短剧",
                "description": project.get("description") or "",
                "genre": md.get("genre") or "短剧",
                "total_episodes": int(md.get("total_episodes") or md.get("episodes") or 30),
                "current_episode": int(md.get("current_episode") or 0),
                "completed_episodes": 0,
                "status": project.get("status") or "draft",
                "model": "deepseek-flash",
                "tags": project.get("tags") or [],
                "type": md.get("kind") or "short_drama",
                "user_id": project.get("user_id") or "default_user",
                "created_at": project.get("created_at"),
                "updated_at": project.get("updated_at"),
            }
            # Ensure folder skeleton for legacy projects
            for sub in ("bible", "outline", "episodes", "video_prompts", "memory", "exports"):
                (self._dir(drama_id) / sub).mkdir(parents=True, exist_ok=True)

        meta.setdefault("type", "short_drama")

        episodes = await self.list_episodes(drama_id, meta.get("total_episodes", 30))
        done = sum(1 for e in episodes if e["status"] == "done")
        meta["completed_episodes"] = done
        meta["current_episode"] = done
        return meta

    async def get_drama(self, drama_id: str) -> Optional[Dict[str, Any]]:
        meta = await self._load_meta(drama_id)
        if not meta:
            return None
        total = meta.get("total_episodes", 30)
        episodes = await self.list_episodes(drama_id, total)
        outline_path = self._dir(drama_id) / "outline" / "series_outline.md"
        outline = ""
        if outline_path.exists():
            async with aiofiles.open(outline_path, "r", encoding="utf-8") as f:
                outline = await f.read()
        chars = ""
        world = ""
        cp = self._dir(drama_id) / "bible" / "characters.md"
        wp = self._dir(drama_id) / "bible" / "world.md"
        if cp.exists():
            async with aiofiles.open(cp, "r", encoding="utf-8") as f:
                chars = await f.read()
        if wp.exists():
            async with aiofiles.open(wp, "r", encoding="utf-8") as f:
                world = await f.read()
        return {
            **meta,
            "episodes": episodes,
            "outline": outline,
            "bible": {"characters": chars, "world": world},
        }

    async def update_drama(
        self,
        drama_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        genre: Optional[str] = None,
        total_episodes: Optional[int] = None,
        type: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """更新剧名 / 简介 / 题材 / 总集数等元数据"""
        meta = await self._load_meta(drama_id)
        if not meta:
            return None
        if title is not None and title.strip():
            meta["title"] = title.strip()
        if description is not None:
            meta["description"] = description
        if genre is not None and genre.strip():
            meta["genre"] = genre.strip()
        if total_episodes is not None and total_episodes > 0:
            meta["total_episodes"] = int(total_episodes)
        if type is not None and type.strip():
            meta["type"] = type.strip()
        meta["updated_at"] = datetime.now().isoformat()
        dj = self._drama_json(drama_id)
        async with aiofiles.open(dj, "w", encoding="utf-8") as f:
            await f.write(json.dumps(meta, ensure_ascii=False, indent=2))
        return meta

    async def delete_drama(self, drama_id: str) -> bool:
        """删除整个作品目录（drama.json + bible/outline/episodes/versions 等）。"""
        meta = await self._load_meta(drama_id)
        if not meta:
            return False
        try:
            import shutil

            shutil.rmtree(self._dir(drama_id), ignore_errors=True)
            logger.info("删除作品: %s", drama_id)
            return True
        except Exception as e:
            logger.exception("删除作品失败: %s", drama_id)
            return False

    async def delete_episode(self, drama_id: str, n: int) -> Dict[str, Any]:
        """删除某集正文（回退为待写草稿）"""
        meta = await self._load_meta(drama_id)
        if not meta:
            raise ValueError("短剧不存在")
        path = self._episode_path(drama_id, n)
        if path.exists():
            path.unlink()
        meta_path = self._drama_json(drama_id)
        meta["updated_at"] = datetime.now().isoformat()
        async with aiofiles.open(meta_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(meta, ensure_ascii=False, indent=2))
        return {"success": True, "number": n}

    async def save_bible(
        self,
        drama_id: str,
        world: Optional[str] = None,
        characters: Optional[str] = None,
    ) -> Dict[str, Any]:
        """保存世界观 / 人物设定（bible 文件）"""
        meta = await self._load_meta(drama_id)
        if not meta:
            raise ValueError("短剧不存在")
        if world is not None:
            wp = self._dir(drama_id) / "bible" / "world.md"
            await atomic_write_text_async(wp, world)
        if characters is not None:
            cp = self._dir(drama_id) / "bible" / "characters.md"
            await atomic_write_text_async(cp, characters)
        return {"success": True}

    def _episode_path(self, drama_id: str, n: int) -> Path:
        return self._dir(drama_id) / "episodes" / f"ep_{n:03d}.md"

    async def list_episodes(self, drama_id: str, total: int) -> List[Dict[str, Any]]:
        result = []
        for n in range(1, int(total) + 1):
            path = self._episode_path(drama_id, n)
            if path.exists():
                content = path.read_text(encoding="utf-8")
                title_line = content.split("\n", 1)[0].lstrip("# ").strip() or f"第 {n} 集"
                result.append(
                    {
                        "number": n,
                        "title": title_line,
                        "status": "done",
                        "word_count": len(content),
                        "updated_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
                    }
                )
            else:
                result.append(
                    {
                        "number": n,
                        "title": f"第 {n} 集",
                        "status": "draft",
                        "word_count": 0,
                    }
                )
        return result

    async def get_episode(self, drama_id: str, n: int) -> Dict[str, Any]:
        path = self._episode_path(drama_id, n)
        if path.exists():
            content = path.read_text(encoding="utf-8")
            title_line = content.split("\n", 1)[0].lstrip("# ").strip() or f"第 {n} 集"
            return {
                "number": n,
                "title": title_line,
                "status": "done",
                "content": content,
                "word_count": len(content),
            }
        return {"number": n, "title": f"第 {n} 集", "status": "draft", "content": "", "word_count": 0}

    async def save_episode(self, drama_id: str, n: int, title: str, content: str) -> Dict[str, Any]:
        root = self._dir(drama_id) / "episodes"
        root.mkdir(parents=True, exist_ok=True)
        body = content if content.lstrip().startswith("#") else f"# {title}\n\n{content}"
        path = self._episode_path(drama_id, n)
        await atomic_write_text_async(path, body)
        # Update meta
        meta_path = self._drama_json(drama_id)
        if meta_path.exists():
            async with aiofiles.open(meta_path, "r", encoding="utf-8") as f:
                meta = json.loads(await f.read())
            meta["updated_at"] = datetime.now().isoformat()
            meta["status"] = "writing"
            await atomic_write_text_async(meta_path, json.dumps(meta, ensure_ascii=False, indent=2))
        return await self.get_episode(drama_id, n)

    # ---------- 视频提示词（豆包 Seedance，与分集剧本并列） ----------

    def _video_prompt_path(self, drama_id: str, n: int) -> Path:
        return self._dir(drama_id) / "video_prompts" / f"ep_{n:03d}.md"

    async def list_video_prompts(self, drama_id: str, total: Optional[int] = None) -> List[Dict[str, Any]]:
        meta = await self._load_meta(drama_id)
        if not meta:
            raise ValueError("短剧不存在")
        total_n = int(total or meta.get("total_episodes") or 80)
        result = []
        for n in range(1, total_n + 1):
            path = self._video_prompt_path(drama_id, n)
            if path.exists():
                content = path.read_text(encoding="utf-8")
                title_line = content.split("\n", 1)[0].lstrip("# ").strip() or f"第 {n} 集视频提示词"
                result.append(
                    {
                        "number": n,
                        "title": title_line,
                        "status": "done",
                        "word_count": len(content),
                        "path": str(path.relative_to(self._dir(drama_id))),
                        "updated_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
                    }
                )
            else:
                result.append(
                    {
                        "number": n,
                        "title": f"第 {n} 集视频提示词",
                        "status": "draft",
                        "word_count": 0,
                        "path": f"video_prompts/ep_{n:03d}.md",
                    }
                )
        return result

    async def get_video_prompt(self, drama_id: str, n: int) -> Dict[str, Any]:
        path = self._video_prompt_path(drama_id, n)
        if path.exists():
            content = path.read_text(encoding="utf-8")
            title_line = content.split("\n", 1)[0].lstrip("# ").strip() or f"第 {n} 集视频提示词"
            return {
                "number": n,
                "title": title_line,
                "status": "done",
                "content": content,
                "word_count": len(content),
                "path": str(path.relative_to(self._dir(drama_id))),
            }
        return {
            "number": n,
            "title": f"第 {n} 集视频提示词",
            "status": "draft",
            "content": "",
            "word_count": 0,
            "path": f"video_prompts/ep_{n:03d}.md",
        }

    async def save_video_prompt(
        self,
        drama_id: str,
        n: int,
        title: str,
        content: str,
    ) -> Dict[str, Any]:
        if not await self._load_meta(drama_id):
            raise ValueError("短剧不存在")
        root = self._dir(drama_id) / "video_prompts"
        root.mkdir(parents=True, exist_ok=True)
        body = content if content.lstrip().startswith("#") else f"# {title}\n\n{content}"
        path = self._video_prompt_path(drama_id, n)
        await atomic_write_text_async(path, body)
        meta_path = self._drama_json(drama_id)
        if meta_path.exists():
            async with aiofiles.open(meta_path, "r", encoding="utf-8") as f:
                meta = json.loads(await f.read())
            meta["updated_at"] = datetime.now().isoformat()
            await atomic_write_text_async(meta_path, json.dumps(meta, ensure_ascii=False, indent=2))
        item = await self.get_video_prompt(drama_id, n)
        item["path"] = str(path.relative_to(self._dir(drama_id)))
        return item

    def _recent_summaries(self, drama_id: str, before: int, limit: int = 2) -> str:
        chunks = []
        for n in range(max(1, before - limit), before):
            path = self._episode_path(drama_id, n)
            if path.exists():
                text = path.read_text(encoding="utf-8")
                chunks.append(f"### 第{n}集摘要\n{text[:800]}")
        return "\n\n".join(chunks)

    def _bible_text(self, drama_id: str) -> str:
        parts = []
        for name in ("characters.md", "world.md"):
            p = self._dir(drama_id) / "bible" / name
            if p.exists():
                parts.append(p.read_text(encoding="utf-8")[:2000])
        return "\n\n".join(parts)

    async def write_episode_with_llm(
        self,
        drama_id: str,
        n: int,
        instruction: Optional[str] = None,
        target_words: Optional[int] = None,
    ) -> Dict[str, Any]:
        meta = await self._load_meta(drama_id)
        if not meta:
            raise ValueError("短剧不存在")

        from utils.llm_client import get_llm_client
        from utils.context_assembler import assemble_with_agent_memory
        from utils.agent_memory import get_agent_memory_service, EpisodeOutcome

        bible = self._bible_text(drama_id)
        prev = self._recent_summaries(drama_id, n)
        user_id = str(meta.get("owner_id") or meta.get("user_id") or "default_user")
        context = assemble_with_agent_memory(
            user_id=user_id,
            drama_id=drama_id,
            title=meta["title"],
            episode_number=n,
            total_episodes=meta.get("total_episodes", 80),
            genre=meta.get("genre", ""),
            description=meta.get("description", ""),
            bible=bible,
            previous_summaries=prev,
            instruction=instruction or "",
            query=f"{meta['title']} ep{n} {instruction or ''}",
        )

        client = get_llm_client("deepseek", model="deepseek-flash")
        word_hint = (
            f"单集控制在 {target_words} 字左右"
            if target_words
            else "单集控制在 600–1200 字"
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "你是竖屏短剧编剧。你有持久记忆：规则、画像、语义事实与历史情节。"
                    "写作前必须遵守 RULES 与未回收悬念；请只输出第 N 集完整剧本正文（Markdown），"
                    f"含场景、动作、对白。{word_hint}，开场有钩子，结尾有卡点。"
                ),
            },
            {"role": "user", "content": context},
        ]
        content = await client.chat(messages)
        title = f"第 {n} 集"
        for line in (content or "").splitlines():
            if line.startswith("#"):
                title = line.lstrip("# ").strip() or title
                break
        episode = await self.save_episode(drama_id, n, title, content or "")

        # 情节记忆 + 语义悬念沉淀
        try:
            mem = get_agent_memory_service()
            mem.ensure(user_id=user_id, drama_id=drama_id)
            mem.record_agent_turn(
                user_id=user_id,
                drama_id=drama_id,
                agent_id="short_drama_creator",
                task_description=f"撰写《{meta['title']}》第{n}集",
                outcome=EpisodeOutcome.SUCCESS.value if content else EpisodeOutcome.FAILURE.value,
                approach="五层记忆注入 + LLM 成稿",
                key_decisions=[f"episode={n}", title],
                resolution=(content or "")[:200],
                tags=["write_episode", f"ep{n}", meta.get("genre") or ""],
            )
            # 集末卡点记为 open_thread / cliffhanger（取文末 120 字）
            tail = (content or "").strip()[-120:]
            if tail:
                mem.upsert_fact(
                    drama_id=drama_id,
                    entity_type="episode",
                    entity_id=f"ep{n}",
                    predicate="cliffhanger",
                    value=tail,
                    confidence="inference",
                    user_id=user_id,
                    provenance={"source": "episode", "source_id": f"ep{n}", "agent_id": "short_drama_creator"},
                )
                mem.upsert_fact(
                    drama_id=drama_id,
                    entity_type="plot_thread",
                    entity_id=f"after_ep{n}",
                    predicate="open_thread",
                    value=f"第{n}集末未兑现：{tail[:80]}",
                    confidence="inference",
                    user_id=user_id,
                    provenance={"source": "episode", "source_id": f"ep{n}"},
                )
        except Exception:
            logger.exception("写入 Agent Memory 失败（不影响成稿）")

        char_path = self._dir(drama_id) / "bible" / "characters.md"
        if char_path.exists() and len(char_path.read_text(encoding="utf-8")) < 80:
            note = f"\n- 第{n}集出现角色线索（待人工确认）\n"
            async with aiofiles.open(char_path, "a", encoding="utf-8") as f:
                await f.write(note)
        return {"episode": episode, "content": content}

    async def generate_outline(self, drama_id: str, premise: Optional[str] = None) -> Dict[str, Any]:
        meta = await self._load_meta(drama_id)
        if not meta:
            raise ValueError("短剧不存在")
        from utils.llm_client import get_llm_client
        from utils.skill_loader import build_skills_prompt

        # 大纲生成是专项写作：显式拉全文 skills（非 Agent loop 的 deferred 路径）
        skills = build_skills_prompt(enabled_only=True, mode="full", include_body=True, max_chars=8000)
        client = get_llm_client("deepseek", model="deepseek-flash")
        total = meta.get("total_episodes", 80)
        prompt = f"""为竖屏短剧《{meta['title']}》写总纲与分集节拍。
类型：{meta.get('genre')}
简介：{premise or meta.get('description') or '未提供'}
总集数：{total}

{skills}

请输出 Markdown：
1) 故事一句话卖点
2) 三幕结构
3) 主要人物
4) 分集节拍表（至少列出前 20 集与每 10 集关键节点，格式：第N集 | 节拍 | 情绪）
"""
        outline = await client.chat(
            [
                {"role": "system", "content": "你是短剧策划主编，输出结构清晰的中文大纲。"},
                {"role": "user", "content": prompt},
            ]
        )
        path = self._dir(drama_id) / "outline" / "series_outline.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(path, "w", encoding="utf-8") as f:
            await f.write(outline or "")
        # crude beats json
        beats = {"episodes": [{"number": i, "beat": ""} for i in range(1, min(total, 20) + 1)]}
        async with aiofiles.open(self._dir(drama_id) / "outline" / "episode_beats.json", "w", encoding="utf-8") as f:
            await f.write(json.dumps(beats, ensure_ascii=False, indent=2))
        return {"outline": outline, "beats": beats}

    def start_auto_write(self, drama_id: str, from_ep: int, to_ep: int) -> str:
        job_id = str(uuid.uuid4())
        AUTO_WRITE_JOBS[job_id] = {
            "job_id": job_id,
            "drama_id": drama_id,
            "status": "running",
            "current": from_ep - 1,
            "total": to_ep - from_ep + 1,
            "from_episode": from_ep,
            "to_episode": to_ep,
            "message": "排队中",
            "started_at": datetime.now().isoformat(),
        }
        asyncio.create_task(self._run_auto_write(job_id, drama_id, from_ep, to_ep))
        return job_id

    async def _run_auto_write(self, job_id: str, drama_id: str, from_ep: int, to_ep: int) -> None:
        """自动连载：优先走分集编排 Agent（连贯性草稿 + 并行单集 subagents）。"""
        job = AUTO_WRITE_JOBS[job_id]
        try:
            job["message"] = "生成连贯性草稿并并行派出单集编剧…"
            job["mode"] = "episode_batch_creator"
            from utils.agent_runtime import load_agent

            agent = load_agent("episode_batch_creator", fresh=True)
            request_data = {
                "input": f"请并行撰写第{from_ep}–{to_ep}集，确保前后连贯、不重复桥段",
                "query": f"写第{from_ep}到第{to_ep}集",
                "from_episode": from_ep,
                "to_episode": to_ep,
                "drama_id": drama_id,
            }
            context = {
                "drama_id": drama_id,
                "project_id": drama_id,
                "user_id": "default_user",
                "session_id": f"auto_write_{job_id}",
                "from_episode": from_ep,
                "to_episode": to_ep,
            }
            events: list = []
            async for ev in agent.process_request(request_data, context):
                events.append(ev)
                et = ev.get("event_type") or ""
                data = ev.get("data")
                meta = ev.get("metadata") or {}
                if et == "subagent_start":
                    ep = meta.get("episode_number") or (data or {}).get("episode_number")
                    job["message"] = f"子专家写作第 {ep} 集…"
                    job["current"] = max(job.get("current") or 0, int(ep or 0) - from_ep + 1)
                elif et == "subagent_end":
                    ep = meta.get("episode_number") or (data or {}).get("episode_number")
                    ok = meta.get("success", True)
                    job["message"] = f"第 {ep} 集{'完成' if ok else '失败'}"
                    job["current"] = max(job.get("current") or 0, int(ep or 0) - from_ep + 1)
                elif et == "system" and isinstance(data, str):
                    job["message"] = data[:120]
            job["events"] = [
                {
                    "event_type": e.get("event_type"),
                    "data": e.get("data") if not isinstance(e.get("data"), str) or len(str(e.get("data"))) < 500 else str(e.get("data"))[:500],
                    "metadata": e.get("metadata"),
                }
                for e in events
                if e.get("event_type") in (
                    "system",
                    "subagent_start",
                    "subagent_end",
                    "composition",
                    "error",
                    "complete",
                )
            ]
            complete = next((e for e in reversed(events) if e.get("event_type") == "complete"), None)
            ok = bool((complete or {}).get("data", {}).get("success", True)) if complete else True
            job["status"] = "done" if ok else "error"
            job["message"] = (
                f"已完成第 {from_ep}–{to_ep} 集（并行 subagents）"
                if ok
                else str((complete or {}).get("data", {}).get("error") or "部分集失败")
            )
        except Exception as e:
            logger.exception("自动连载失败，回退顺序写作")
            try:
                for n in range(from_ep, to_ep + 1):
                    job["current"] = n - from_ep + 1
                    job["message"] = f"回退顺序写作第 {n} 集"
                    await self.write_episode_with_llm(drama_id, n)
                job["status"] = "done"
                job["message"] = f"已完成第 {from_ep}–{to_ep} 集（顺序回退）"
                job["mode"] = "sequential_fallback"
            except Exception as e2:
                logger.exception("顺序回退也失败")
                job["status"] = "error"
                job["message"] = str(e2) or str(e)

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return AUTO_WRITE_JOBS.get(job_id)

    # ---------- Agent Artifacts（策划 / 人物 / 情节点 / 评估等） ----------

    ARTIFACT_KINDS = (
        "planning",
        "story",
        "plot",
        "character",
        "evaluation",
        "creation",
        "analysis",
        "other",
    )

    KIND_LABELS = {
        "planning": "策划",
        "story": "故事",
        "plot": "情节点",
        "character": "人物",
        "evaluation": "评估",
        "creation": "创作",
        "analysis": "分析",
        "other": "其他",
    }

    def _artifacts_root(self, drama_id: str) -> Path:
        root = self._dir(drama_id) / "agent_outputs"
        root.mkdir(parents=True, exist_ok=True)
        return root

    @staticmethod
    def resolve_artifact_kind(agent_id: str = "", category: str = "", kind: str = "") -> str:
        if kind and kind in DramaManager.ARTIFACT_KINDS:
            return kind
        by_id = {
            "short_drama_planner": "planning",
            "drama_workflow": "planning",
            "story_five_elements": "story",
            "story_summary_generator": "story",
            "mind_map": "story",
            "story_type_analyzer": "story",
            "major_plot_points": "plot",
            "detailed_plot_points": "plot",
            "plot_points_analyzer": "plot",
            "plot_points_workflow": "plot",
            "character_profile_generator": "character",
            "character_relationship_analyzer": "character",
            "short_drama_evaluation": "evaluation",
            "script_evaluation": "evaluation",
            "story_evaluation": "evaluation",
            "story_outline_evaluation": "evaluation",
            "novel_screening_evaluation": "evaluation",
            "ip_evaluation": "evaluation",
            "score_analyzer": "evaluation",
            "result_analyzer_evaluation": "evaluation",
            "short_drama_creator": "creation",
            "episode_batch_creator": "creation",
            "episode_writer": "creation",
            "video_prompt_writer": "creation",
            "video_prompt_batch": "creation",
            "series_analysis": "analysis",
            "drama_analysis": "analysis",
        }
        if agent_id in by_id:
            return by_id[agent_id]
        by_cat = {
            "planning": "planning",
            "story": "story",
            "character": "character",
            "evaluation": "evaluation",
            "creation": "creation",
            "analysis": "plot",
            "workflow": "plot",
        }
        return by_cat.get(category or "", "other")

    async def save_artifact(
        self,
        drama_id: str,
        *,
        content: str,
        agent_id: str = "",
        agent_name: str = "",
        category: str = "",
        kind: str = "",
        title: str = "",
        user_prompt: str = "",
        sync_bible: bool = True,
    ) -> Dict[str, Any]:
        meta = await self._load_meta(drama_id)
        if not meta:
            raise ValueError("短剧不存在")
        text = (content or "").strip()
        if not text:
            raise ValueError("内容为空")

        resolved = self.resolve_artifact_kind(agent_id, category, kind)
        artifact_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        kind_dir = self._artifacts_root(drama_id) / resolved
        kind_dir.mkdir(parents=True, exist_ok=True)

        preview = text.replace("\n", " ").strip()
        if len(preview) > 160:
            preview = preview[:157] + "…"

        display_title = (title or "").strip() or (
            f"{agent_name or agent_id or self.KIND_LABELS.get(resolved, resolved)} · "
            f"{datetime.now().strftime('%m-%d %H:%M')}"
        )

        record = {
            "id": artifact_id,
            "drama_id": drama_id,
            "kind": resolved,
            "kind_label": self.KIND_LABELS.get(resolved, resolved),
            "title": display_title,
            "agent_id": agent_id,
            "agent_name": agent_name,
            "category": category,
            "user_prompt": (user_prompt or "")[:2000],
            "content": text,
            "preview": preview,
            "word_count": len(text),
            "created_at": now,
            "updated_at": now,
        }

        path = kind_dir / f"{artifact_id}.json"
        await atomic_write_text_async(path, json.dumps(record, ensure_ascii=False, indent=2))

        # 人物类结果同步进 bible，便于写作注入
        if sync_bible and resolved == "character" and text:
            char_path = self._dir(drama_id) / "bible" / "characters.md"
            try:
                existing = ""
                if char_path.exists():
                    async with aiofiles.open(char_path, "r", encoding="utf-8") as f:
                        existing = await f.read()
                stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                block = f"\n\n## {display_title}\n\n> 来自专家 · {stamp}\n\n{text}\n"
                async with aiofiles.open(char_path, "w", encoding="utf-8") as f:
                    await f.write((existing or f"# {meta.get('title', '')} · 人物设定\n") + block)
            except Exception:
                logger.exception("同步人物 bible 失败")

        # 策划/故事类可追加到 outline 附录（不覆盖主大纲）
        if sync_bible and resolved in ("planning", "story") and text:
            try:
                appendix = self._dir(drama_id) / "outline" / "agent_appendix.md"
                stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                async with aiofiles.open(appendix, "a", encoding="utf-8") as f:
                    await f.write(f"\n\n## {display_title}\n\n> {stamp} · {agent_name or agent_id}\n\n{text}\n")
            except Exception:
                logger.exception("同步 outline 附录失败")

        meta["updated_at"] = now
        async with aiofiles.open(self._drama_json(drama_id), "w", encoding="utf-8") as f:
            await f.write(json.dumps(meta, ensure_ascii=False, indent=2))

        return record

    async def list_artifacts(
        self,
        drama_id: str,
        kind: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        if not await self._load_meta(drama_id):
            raise ValueError("短剧不存在")
        root = self._artifacts_root(drama_id)
        items: List[Dict[str, Any]] = []
        kinds = [kind] if kind and kind in self.ARTIFACT_KINDS else list(self.ARTIFACT_KINDS)
        for k in kinds:
            kdir = root / k
            if not kdir.is_dir():
                continue
            for path in kdir.glob("*.json"):
                try:
                    async with aiofiles.open(path, "r", encoding="utf-8") as f:
                        data = json.loads(await f.read())
                    items.append(
                        {
                            "id": data.get("id") or path.stem,
                            "drama_id": drama_id,
                            "kind": data.get("kind") or k,
                            "kind_label": data.get("kind_label")
                            or self.KIND_LABELS.get(k, k),
                            "title": data.get("title") or path.stem,
                            "agent_id": data.get("agent_id") or "",
                            "agent_name": data.get("agent_name") or "",
                            "preview": data.get("preview")
                            or (data.get("content") or "")[:160],
                            "word_count": data.get("word_count")
                            or len(data.get("content") or ""),
                            "created_at": data.get("created_at") or "",
                            "updated_at": data.get("updated_at") or "",
                        }
                    )
                except Exception:
                    logger.exception("读取 artifact 失败: %s", path)

        # 把系列大纲也作为只读「故事」资产露出
        outline_path = self._dir(drama_id) / "outline" / "series_outline.md"
        if outline_path.exists() and (not kind or kind == "story"):
            try:
                async with aiofiles.open(outline_path, "r", encoding="utf-8") as f:
                    outline = (await f.read()).strip()
                if outline:
                    items.append(
                        {
                            "id": "outline-series",
                            "drama_id": drama_id,
                            "kind": "story",
                            "kind_label": "故事",
                            "title": "系列大纲",
                            "agent_id": "outline",
                            "agent_name": "大纲生成",
                            "preview": outline[:160] + ("…" if len(outline) > 160 else ""),
                            "word_count": len(outline),
                            "created_at": "",
                            "updated_at": "",
                            "virtual": True,
                        }
                    )
            except Exception:
                pass

        items.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        return items[: max(1, min(limit, 200))]

    async def get_artifact(self, drama_id: str, artifact_id: str) -> Optional[Dict[str, Any]]:
        if not await self._load_meta(drama_id):
            raise ValueError("短剧不存在")

        if artifact_id == "outline-series":
            outline_path = self._dir(drama_id) / "outline" / "series_outline.md"
            if not outline_path.exists():
                return None
            async with aiofiles.open(outline_path, "r", encoding="utf-8") as f:
                outline = await f.read()
            return {
                "id": "outline-series",
                "drama_id": drama_id,
                "kind": "story",
                "kind_label": "故事",
                "title": "系列大纲",
                "agent_id": "outline",
                "agent_name": "大纲生成",
                "content": outline,
                "preview": outline[:160],
                "word_count": len(outline),
                "virtual": True,
            }

        root = self._artifacts_root(drama_id)
        for k in self.ARTIFACT_KINDS:
            path = root / k / f"{artifact_id}.json"
            if path.exists():
                async with aiofiles.open(path, "r", encoding="utf-8") as f:
                    return json.loads(await f.read())
        return None

    async def delete_artifact(self, drama_id: str, artifact_id: str) -> bool:
        if artifact_id == "outline-series":
            return False
        if not await self._load_meta(drama_id):
            raise ValueError("短剧不存在")
        root = self._artifacts_root(drama_id)
        for k in self.ARTIFACT_KINDS:
            path = root / k / f"{artifact_id}.json"
            if path.exists():
                path.unlink()
                return True
        return False


_drama_manager: Optional[DramaManager] = None


def get_drama_manager() -> DramaManager:
    global _drama_manager
    if _drama_manager is None:
        _drama_manager = DramaManager()
    return _drama_manager
