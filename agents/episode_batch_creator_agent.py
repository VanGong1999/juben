"""
分集连载编排 Agent

流程（借鉴 Anthropic multi-agent + structured-state handoff）：
1. 加载前置产物（策划/故事/人物/情节点 + bible/outline）
2. LLM 生成连贯性草稿（continuity draft）— 共享结构化状态
3. 并行 spawn episode_writer 子专家（一集一个），透传裁剪后的手递上下文
4. 落盘分集 + 保存草稿；父 Agent 对用户合成最终回复

子专家事件以 subagent_start / nested chunks / subagent_end 流式输出，供前端 Cursor 风格展示。
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

logger = logging.getLogger("EpisodeBatchCreatorAgent")

CONTINUITY_SCHEMA_HINT = """
请严格输出一个 JSON 对象（不要 markdown 围栏），字段：
{
  "series_logline": "一句话卖点",
  "character_arcs": [
    {"name": "角色名", "checkpoints": {"1": "第1集状态", "2": "..."}}
  ],
  "episodes": [
    {
      "n": 1,
      "title": "集标题",
      "beat": "本集节拍一句话",
      "hook": "开场钩子",
      "mid_turn": "中段反转",
      "cliffhanger": "结尾卡点",
      "must_include": ["必须出现的点"],
      "must_not_repeat": ["本集禁止复用的桥段"],
      "carry_in": ["从上集承接"],
      "carry_out": ["留给下集"]
    }
  ],
  "forbidden_repeats": ["全局禁止重复的桥段/打脸方式"],
  "open_threads": ["跨集悬念"]
}
episodes 数组长度必须等于要求的集数；n 从 from_episode 连续递增。
"""


def _load_prompt() -> str:
    path = Path(__file__).resolve().parent.parent / "prompts" / "episode_batch_creator_system.txt"
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return "你是分集连载编排助手：先写连贯性草稿，再并行派出单集编剧。"


def _parse_json_loose(text: str) -> Optional[Dict[str, Any]]:
    raw = (text or "").strip()
    if not raw:
        return None
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if fence:
        raw = fence.group(1).strip()
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(raw[start : end + 1])
                return data if isinstance(data, dict) else None
            except json.JSONDecodeError:
                return None
    return None


def _fallback_continuity(
    *,
    title: str,
    from_ep: int,
    to_ep: int,
    genre: str,
    outline: str,
) -> Dict[str, Any]:
    episodes = []
    for n in range(from_ep, to_ep + 1):
        episodes.append(
            {
                "n": n,
                "title": f"第{n}集",
                "beat": f"推进主线冲突 · 第{n}节拍",
                "hook": "开场即冲突或悬念",
                "mid_turn": "信息反转或压迫升级",
                "cliffhanger": "未兑现承诺或新威胁",
                "must_include": [],
                "must_not_repeat": [],
                "carry_in": [] if n == from_ep else [f"承接第{n - 1}集卡点"],
                "carry_out": [f"抛给第{n + 1}集的钩子"] if n < to_ep else ["本季收束或更大悬念"],
            }
        )
    return {
        "series_logline": f"《{title}》{genre}短剧主线",
        "character_arcs": [],
        "episodes": episodes,
        "forbidden_repeats": ["同一打脸台词复读", "同一反派嚣张桥段无升级"],
        "open_threads": [],
        "_source": "fallback",
        "_outline_hint": (outline or "")[:500],
    }


def _render_field(val: Any) -> str:
    """把单个字段渲染成可读文本；list 用顿号连接，空值返回空串。"""
    if val is None:
        return ""
    if isinstance(val, str):
        return val.strip()
    if isinstance(val, list):
        items = [str(x).strip() for x in val if str(x).strip()]
        return "、".join(items)
    return str(val).strip()


def _checkpoint_key(k: Any) -> int:
    try:
        return int(k)
    except (TypeError, ValueError):
        return 0


class EpisodeBatchCreatorAgent:
    """分集连载编排：连贯性草稿 → 并行单集 subagents → 落盘。"""

    def __init__(
        self,
        model_provider: str = "deepseek",
        model: Optional[str] = None,
    ):
        self.agent_name = "episode_batch_creator"
        self.model_provider = model_provider
        self.model = model or "deepseek-flash"
        self.system_prompt = _load_prompt()
        self.llm_client = None
        self.allowed_subagents = ["episode_writer"]
        self.max_parallel = 5

    def _ensure_client(self):
        if self.llm_client is None:
            from utils.llm_client import get_llm_client

            self.llm_client = get_llm_client(provider=self.model_provider, model=self.model)
        return self.llm_client

    def _event(
        self,
        event_type: str,
        data: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return {
            "event_type": event_type,
            "agent_source": self.agent_name,
            "timestamp": datetime.now().isoformat(),
            "data": data,
            "metadata": metadata or {},
        }

    def get_agent_info(self) -> Dict[str, Any]:
        return {
            "name": self.agent_name,
            "agent_name": self.agent_name,
            "display_name": "分集连载编排",
            "capabilities": [
                "continuity_draft",
                "parallel_episode_subagents",
                "structured_handoff",
                "drama_writeback",
            ],
            "allowed_subagents": list(self.allowed_subagents),
        }

    async def _load_preflight_bundle(self, drama_id: str) -> Dict[str, Any]:
        from utils.drama_manager import get_drama_manager

        mgr = get_drama_manager()
        meta = await mgr._load_meta(drama_id) or {}
        root = mgr._dir(drama_id)
        parts: Dict[str, str] = {}

        for rel, key in (
            ("bible/characters.md", "characters"),
            ("bible/world.md", "world"),
            ("outline/series_outline.md", "outline"),
            ("outline/agent_appendix.md", "appendix"),
        ):
            p = root / rel
            if p.exists():
                parts[key] = p.read_text(encoding="utf-8")[:6000]

        try:
            arts = await mgr.list_artifacts(drama_id, limit=20)
            snippets = []
            for a in arts[:8]:
                full = await mgr.get_artifact(drama_id, a["id"])
                if full and full.get("content"):
                    snippets.append(
                        f"### [{full.get('kind_label')}] {full.get('title')}\n"
                        f"{(full.get('content') or '')[:1500]}"
                    )
            if snippets:
                parts["artifacts"] = "\n\n".join(snippets)
        except Exception:
            logger.exception("load artifacts failed")

        return {"meta": meta, "parts": parts, "bible_excerpt": self._bible_join(parts)}

    @staticmethod
    def _bible_join(parts: Dict[str, str]) -> str:
        order = ["characters", "world", "outline", "appendix", "artifacts"]
        chunks = []
        for k in order:
            if parts.get(k):
                chunks.append(f"## {k}\n{parts[k]}")
        return "\n\n".join(chunks)

    def _resolve_range(
        self,
        request_data: Dict[str, Any],
        context: Dict[str, Any],
        meta: Dict[str, Any],
    ) -> Tuple[int, int]:
        total = int(meta.get("total_episodes") or 80)
        from_ep = int(
            request_data.get("from_episode")
            or context.get("from_episode")
            or 1
        )
        to_ep = request_data.get("to_episode") or context.get("to_episode")
        if to_ep is None:
            # 从用户话里抽「写N集 / 第1-5集」
            text = str(
                request_data.get("input")
                or request_data.get("query")
                or ""
            )
            m = re.search(r"第\s*(\d+)\s*[-–—~到至]\s*(\d+)\s*集", text)
            if m:
                from_ep, to_ep = int(m.group(1)), int(m.group(2))
            else:
                m2 = re.search(r"(\d+)\s*集", text)
                if m2:
                    n = int(m2.group(1))
                    if 1 <= n <= 30:
                        to_ep = from_ep + n - 1
        to_ep = int(to_ep or min(total, from_ep + 4))
        from_ep = max(1, from_ep)
        to_ep = min(max(from_ep, to_ep), total)
        return from_ep, to_ep

    async def _build_continuity_draft(
        self,
        *,
        meta: Dict[str, Any],
        parts: Dict[str, str],
        from_ep: int,
        to_ep: int,
        user_requirements: str,
    ) -> Dict[str, Any]:
        client = self._ensure_client()
        title = meta.get("title") or "未命名短剧"
        genre = meta.get("genre") or ""
        prompt = f"""为短剧《{title}》生成第 {from_ep}–{to_ep} 集的连贯性草稿 JSON。

类型：{genre}
简介：{meta.get("description") or ""}
用户要求：{user_requirements or "无"}

## 前置产物摘录
人物：
{(parts.get("characters") or "")[:2500]}

世界观：
{(parts.get("world") or "")[:1500]}

大纲：
{(parts.get("outline") or "")[:2500]}

其他专家产物：
{(parts.get("artifacts") or "")[:3000]}

{CONTINUITY_SCHEMA_HINT}
"""
        try:
            raw = await client.chat(
                [
                    {
                        "role": "system",
                        "content": (
                            "你是短剧连载主编。只输出合法 JSON 连贯性草稿，"
                            "确保集与集不重复、悬念有接力、人物弧线可检查。"
                        ),
                    },
                    {"role": "user", "content": prompt},
                ]
            )
            draft = _parse_json_loose(raw or "")
            if not draft or not isinstance(draft.get("episodes"), list):
                raise ValueError("continuity draft missing episodes")
            # 规范化集号
            by_n = {int(e.get("n")): e for e in draft["episodes"] if e.get("n") is not None}
            fixed = []
            for n in range(from_ep, to_ep + 1):
                slot = by_n.get(n) or {
                    "n": n,
                    "title": f"第{n}集",
                    "beat": f"第{n}集节拍",
                    "hook": "",
                    "mid_turn": "",
                    "cliffhanger": "",
                    "must_include": [],
                    "must_not_repeat": list(draft.get("forbidden_repeats") or [])[:3],
                    "carry_in": [],
                    "carry_out": [],
                }
                slot["n"] = n
                fixed.append(slot)
            draft["episodes"] = fixed
            return draft
        except Exception:
            logger.exception("continuity draft LLM failed, using fallback")
            return _fallback_continuity(
                title=title,
                from_ep=from_ep,
                to_ep=to_ep,
                genre=genre,
                outline=parts.get("outline") or "",
            )

    @staticmethod
    def _render_continuity_markdown(
        draft: Dict[str, Any],
        *,
        title: str,
        genre: str,
        from_ep: int,
        to_ep: int,
    ) -> str:
        """把连贯性草稿 JSON 渲染成人类可读的 Markdown（供创作图展示）。"""
        lines: List[str] = [f"# 连贯性草稿 · 《{title}》"]

        meta_bits = [f"第 {from_ep}–{to_ep} 集"]
        if genre:
            meta_bits.append(genre)
        lines.append(" · ".join(meta_bits))

        logline = (draft.get("series_logline") or "").strip()
        if logline:
            lines.append("")
            lines.append("## 一句话卖点")
            lines.append("")
            lines.append(logline)

        arcs = draft.get("character_arcs") or []
        if arcs:
            lines.append("")
            lines.append("## 人物弧线")
            lines.append("")
            for arc in arcs:
                if not isinstance(arc, dict):
                    continue
                name = (arc.get("name") or "角色").strip()
                cps = arc.get("checkpoints") or {}
                if isinstance(cps, dict) and cps:
                    trail = " → ".join(
                        f"第{k}集 {_render_field(v)}"
                        for k, v in sorted(cps.items(), key=lambda kv: _checkpoint_key(kv[0]))
                    )
                    lines.append(f"- **{name}**：{trail}")
                else:
                    lines.append(f"- **{name}**")

        episodes = draft.get("episodes") or []
        if episodes:
            lines.append("")
            lines.append("## 分集节拍")
            for ep in episodes:
                if not isinstance(ep, dict):
                    continue
                n = ep.get("n")
                ep_title = (ep.get("title") or "").strip() or f"第{n}集"
                lines.append("")
                lines.append(f"### 第{n}集 · {ep_title}")
                for label, val in (
                    ("节拍", ep.get("beat")),
                    ("开场钩子", ep.get("hook")),
                    ("中段反转", ep.get("mid_turn")),
                    ("结尾卡点", ep.get("cliffhanger")),
                    ("必含", ep.get("must_include")),
                    ("禁重复", ep.get("must_not_repeat")),
                    ("承接上集", ep.get("carry_in")),
                    ("留给下集", ep.get("carry_out")),
                ):
                    rendered = _render_field(val)
                    if rendered:
                        lines.append(f"- **{label}**：{rendered}")

        forbidden = draft.get("forbidden_repeats") or []
        if forbidden:
            lines.append("")
            lines.append("## 全局禁止重复")
            lines.append("")
            for item in forbidden:
                lines.append(f"- {_render_field(item)}")

        open_threads = draft.get("open_threads") or []
        if open_threads:
            lines.append("")
            lines.append("## 跨集悬念")
            lines.append("")
            for item in open_threads:
                lines.append(f"- {_render_field(item)}")

        return "\n".join(lines)

    async def _save_continuity(
        self,
        drama_id: str,
        draft: Dict[str, Any],
        *,
        title: str,
        genre: str,
        from_ep: int,
        to_ep: int,
    ) -> None:
        from utils.drama_manager import get_drama_manager
        from utils.atomic_write import atomic_write_text_async

        mgr = get_drama_manager()
        path = mgr._dir(drama_id) / "outline" / "continuity_draft.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        await atomic_write_text_async(path, json.dumps(draft, ensure_ascii=False, indent=2))
        try:
            await mgr.save_artifact(
                drama_id,
                content=self._render_continuity_markdown(
                    draft,
                    title=title,
                    genre=genre,
                    from_ep=from_ep,
                    to_ep=to_ep,
                ),
                agent_id=self.agent_name,
                agent_name="分集连载编排",
                category="creation",
                kind="creation",
                title="连贯性草稿 Continuity Draft",
                sync_bible=False,
            )
        except Exception:
            logger.exception("save continuity artifact failed")

    async def _spawn_episode_writers(
        self,
        *,
        drama_id: str,
        draft: Dict[str, Any],
        bible_excerpt: str,
        user_requirements: str,
        target_words: int,
        context: Dict[str, Any],
        event_queue: asyncio.Queue,
    ) -> List[Dict[str, Any]]:
        from utils.agent_infra.subagents import SubagentRunner, SubagentSpec
        from utils.drama_manager import get_drama_manager

        episodes = list(draft.get("episodes") or [])
        runner = SubagentRunner(max_parallel=self.max_parallel)
        mgr = get_drama_manager()
        results: List[Dict[str, Any]] = []

        async def _one(slot: Dict[str, Any]) -> Dict[str, Any]:
            n = int(slot["n"])
            neighbors = [
                {
                    "n": e.get("n"),
                    "title": e.get("title"),
                    "beat": e.get("beat"),
                    "cliffhanger": e.get("cliffhanger"),
                }
                for e in episodes
                if abs(int(e.get("n") or 0) - n) == 1
            ]
            child_ctx = {
                "user_id": context.get("user_id"),
                "session_id": context.get("session_id"),
                "drama_id": drama_id,
                "project_id": drama_id,
                "episode_number": n,
                "episode_slot": slot,
                "continuity_draft": draft,
                "neighbor_beats": neighbors,
                "bible_excerpt": bible_excerpt[:4000],
                "user_requirements": user_requirements,
                "target_words": target_words,
                "parent_agent": self.agent_name,
            }
            await event_queue.put(
                self._event(
                    "subagent_start",
                    {
                        "agent_id": "episode_writer",
                        "episode_number": n,
                        "task": f"撰写第{n}集《{slot.get('title') or ''}》：{slot.get('beat') or ''}",
                        "title": f"第{n}集编剧",
                    },
                    metadata={
                        "agent_id": "episode_writer",
                        "episode_number": n,
                        "parent_id": self.agent_name,
                    },
                )
            )

            chunks: List[str] = []

            async def _on_event(ev: Dict[str, Any]) -> None:
                meta = dict(ev.get("metadata") or {})
                meta["from_subagent"] = "episode_writer"
                meta["episode_number"] = n
                meta["parent_id"] = self.agent_name
                wrapped = {**ev, "metadata": meta}
                et = ev.get("event_type") or ev.get("type")
                data = ev.get("data")
                if et in ("llm_chunk", "message", "content") and isinstance(data, str):
                    chunks.append(data)
                await event_queue.put(wrapped)

            result = await runner.spawn(
                SubagentSpec(
                    agent_id="episode_writer",
                    task=(
                        f"撰写第{n}集完整剧本。"
                        f"节拍：{slot.get('beat') or ''}。"
                        f"钩子：{slot.get('hook') or ''}。"
                        f"卡点：{slot.get('cliffhanger') or ''}。"
                        f"用户要求：{user_requirements or '无'}。"
                    ),
                    context_keys=[
                        "episode_number",
                        "episode_slot",
                        "continuity_draft",
                        "neighbor_beats",
                        "bible_excerpt",
                        "user_requirements",
                        "target_words",
                    ],
                    timeout=180,
                    metadata={"episode_number": n},
                ),
                parent_agent_id=self.agent_name,
                context=child_ctx,
                depth=0,
                allowed_subagents=set(self.allowed_subagents),
                on_event=_on_event,
            )

            content = (result.content or "").strip() or "".join(chunks).strip()
            title = str(slot.get("title") or f"第 {n} 集")
            saved = None
            err = result.error
            if result.success and content:
                try:
                    saved = await mgr.save_episode(drama_id, n, title, content)
                except Exception as e:
                    err = str(e)
                    logger.exception("save episode %s failed", n)

            payload = {
                "agent_id": "episode_writer",
                "episode_number": n,
                "success": bool(result.success and content and not err),
                "title": title,
                "word_count": len(content or ""),
                "preview": (content or "")[:240],
                "error": err,
                "duration_ms": result.duration_ms,
                "content": content,
            }
            await event_queue.put(
                self._event(
                    "subagent_end",
                    payload,
                    metadata={
                        "agent_id": "episode_writer",
                        "episode_number": n,
                        "success": payload["success"],
                        "parent_id": self.agent_name,
                    },
                )
            )
            return payload

        tasks = [asyncio.create_task(_one(s)) for s in episodes]
        for t in asyncio.as_completed(tasks):
            results.append(await t)
        results.sort(key=lambda r: int(r.get("episode_number") or 0))
        return results

    async def process_request(
        self,
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        context = dict(context or {})
        user_id = context.get("user_id") or request_data.get("user_id") or "default_user"
        session_id = context.get("session_id") or request_data.get("session_id") or "default"
        drama_id = (
            context.get("drama_id")
            or request_data.get("drama_id")
            or context.get("project_id")
            or request_data.get("project_id")
        )
        query = (
            request_data.get("input")
            or request_data.get("query")
            or request_data.get("message")
            or ""
        )
        user_requirements = str(
            request_data.get("user_requirements")
            or context.get("user_requirements")
            or query
        ).strip()
        target_words = int(
            request_data.get("target_words") or context.get("target_words") or 800
        )

        yield self._event(
            "agent_decision",
            {"mode": "episode_batch", "message": "分集连载编排启动：连贯性草稿 → 并行单集编剧"},
            metadata={"active_agent": self.agent_name},
        )
        yield self._event("system", "🎬 分集连载编排助手已就绪")

        if not drama_id:
            yield self._event(
                "error",
                "缺少 drama_id：请在作品工作室中发起，或在请求里绑定作品。",
            )
            yield self._event("complete", {"success": False, "error": "missing drama_id"})
            return

        context["user_id"] = user_id
        context["session_id"] = session_id
        context["drama_id"] = drama_id

        yield self._event("thinking", "读取前置产物（策划/人物/大纲/情节点）…")
        bundle = await self._load_preflight_bundle(drama_id)
        meta = bundle["meta"]
        if not meta:
            yield self._event("error", "短剧不存在")
            yield self._event("complete", {"success": False, "error": "drama not found"})
            return

        from_ep, to_ep = self._resolve_range(request_data, context, meta)
        count = to_ep - from_ep + 1
        yield self._event(
            "system",
            f"将撰写第 {from_ep}–{to_ep} 集（共 {count} 集），先生成连贯性草稿…",
            metadata={"from_episode": from_ep, "to_episode": to_ep},
        )

        yield self._event("thinking", "编写连贯性草稿：节拍 / 弧线 / 禁止重复 / 悬念接力…")
        draft = await self._build_continuity_draft(
            meta=meta,
            parts=bundle["parts"],
            from_ep=from_ep,
            to_ep=to_ep,
            user_requirements=user_requirements,
        )
        await self._save_continuity(
            drama_id,
            draft,
            title=meta.get("title") or "未命名短剧",
            genre=meta.get("genre") or "",
            from_ep=from_ep,
            to_ep=to_ep,
        )
        ep_titles = "、".join(
            f"第{e.get('n')}集《{e.get('title') or ''}》" for e in draft.get("episodes") or []
        )
        yield self._event(
            "system",
            f"✅ 连贯性草稿已就绪：{ep_titles}",
            metadata={"continuity": True, "episode_count": count},
        )
        yield self._event(
            "composition",
            {
                "phase": "parallel_spawn",
                "agents": ["episode_writer"] * count,
                "message": f"并行启动 {count} 个单集编剧 subagents",
            },
            metadata={"from_episode": from_ep, "to_episode": to_ep},
        )

        queue: asyncio.Queue = asyncio.Queue()

        async def _run() -> List[Dict[str, Any]]:
            try:
                return await self._spawn_episode_writers(
                    drama_id=drama_id,
                    draft=draft,
                    bible_excerpt=bundle["bible_excerpt"],
                    user_requirements=user_requirements,
                    target_words=target_words,
                    context=context,
                    event_queue=queue,
                )
            finally:
                await queue.put(None)

        task = asyncio.create_task(_run())
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item

        results = await task
        ok = [r for r in results if r.get("success")]
        fail = [r for r in results if not r.get("success")]

        summary_lines = [
            f"## 分集连载完成 · 《{meta.get('title')}》",
            f"- 范围：第 {from_ep}–{to_ep} 集",
            f"- 成功：{len(ok)} / {count}",
        ]
        if fail:
            summary_lines.append(
                "- 失败："
                + "、".join(
                    f"第{r.get('episode_number')}集({r.get('error') or 'unknown'})" for r in fail
                )
            )
        summary_lines.append("")
        summary_lines.append("### 各集预览")
        for r in results:
            summary_lines.append(
                f"**第{r.get('episode_number')}集 · {r.get('title')}** "
                f"({'✅' if r.get('success') else '❌'} · {r.get('word_count') or 0}字)\n"
                f"{(r.get('preview') or '')[:180]}…"
            )
        summary_lines.append("")
        summary_lines.append(
            "连贯性草稿已写入 `outline/continuity_draft.json`。"
            "可在工作室分集页查看正文；如需按你的新要求改某一集，直接说明集号与修改点。"
        )
        summary = "\n".join(summary_lines)

        chunk = 100
        for i in range(0, len(summary), chunk):
            yield self._event("llm_chunk", summary[i : i + chunk])

        yield self._event(
            "complete",
            {
                "success": len(fail) == 0,
                "drama_id": drama_id,
                "from_episode": from_ep,
                "to_episode": to_ep,
                "results": [
                    {k: v for k, v in r.items() if k != "content"} for r in results
                ],
                "content": summary,
            },
            metadata={"success": len(fail) == 0},
        )
