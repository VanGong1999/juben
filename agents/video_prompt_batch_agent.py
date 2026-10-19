"""
分集剧本 → 豆包视频提示词批量编排

1. 读取已完成分集剧本 + bible
2. 生成视觉连贯性草稿（人物/场景/风格跨集锁定）
3. 并行 spawn video_prompt_writer（一集一个）
4. 落盘到 video_prompts/ep_XXX.md
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

logger = logging.getLogger("VideoPromptBatchAgent")

VISUAL_SCHEMA_HINT = """
请输出 JSON（不要 markdown 围栏）：
{
  "style": "都市写实短剧，电影级光影，竖屏9:16",
  "characters": [
    {"name": "林晚", "look": "28岁东亚女性…", "costume_by_ep": {"1": "婚纱", "2": "…"}}
  ],
  "locations": [
    {"name": "婚礼宴会厅", "look": "水晶灯、长桌、冷暖对比光…"}
  ],
  "props": ["假合同", "戒指"],
  "global_rules": [
    "不要字幕",
    "无BGM，只保留环境音与动作音",
    "人物外貌仅用本草稿锚定，逐镜不重描五官",
    "禁止连续同景别超过2镜"
  ],
  "episode_notes": [
    {"n": 1, "hook_visual": "抽回手的特写", "key_shots": ["退婚", "假合同"]}
  ]
}
"""


def _load_prompt() -> str:
    path = Path(__file__).resolve().parent.parent / "prompts" / "video_prompt_batch_system.txt"
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return "你是短剧视频提示词批量编排助手。"


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


class VideoPromptBatchAgent:
    """批量：视觉连贯性草稿 → 并行单集视频提示词。"""

    def __init__(
        self,
        model_provider: str = "deepseek",
        model: Optional[str] = None,
    ):
        self.agent_name = "video_prompt_batch"
        self.model_provider = model_provider
        self.model = model or "deepseek-flash"
        self.system_prompt = _load_prompt()
        self.llm_client = None
        self.allowed_subagents = ["video_prompt_writer"]
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
            "display_name": "视频提示词批量编排",
            "capabilities": [
                "visual_continuity_draft",
                "parallel_video_prompt_subagents",
                "seedance_dialect",
                "video_prompt_writeback",
            ],
            "allowed_subagents": list(self.allowed_subagents),
        }

    def _resolve_range(
        self,
        request_data: Dict[str, Any],
        context: Dict[str, Any],
        meta: Dict[str, Any],
        available: List[int],
    ) -> Tuple[int, int]:
        total = int(meta.get("total_episodes") or 80)
        from_ep = int(request_data.get("from_episode") or context.get("from_episode") or 0)
        to_ep = request_data.get("to_episode") or context.get("to_episode")
        text = str(request_data.get("input") or request_data.get("query") or "")
        if not from_ep:
            m = re.search(r"第\s*(\d+)\s*[-–—~到至]\s*(\d+)\s*集", text)
            if m:
                from_ep, to_ep = int(m.group(1)), int(m.group(2))
            else:
                m1 = re.search(r"第\s*(\d+)\s*集", text)
                if m1 and "批量" not in text and "全部" not in text:
                    from_ep = to_ep = int(m1.group(1))
                elif available:
                    from_ep = min(available)
                    to_ep = max(available)
                else:
                    from_ep, to_ep = 1, min(5, total)
        to_ep = int(to_ep or from_ep)
        from_ep = max(1, from_ep)
        to_ep = min(max(from_ep, to_ep), total)
        return from_ep, to_ep

    async def _build_visual_draft(
        self,
        *,
        meta: Dict[str, Any],
        bible: str,
        scripts_preview: str,
        from_ep: int,
        to_ep: int,
        user_requirements: str,
    ) -> Dict[str, Any]:
        client = self._ensure_client()
        prompt = f"""为短剧《{meta.get('title')}》第{from_ep}–{to_ep}集生成「视觉连贯性草稿」JSON，供 Seedance 视频提示词使用。

类型：{meta.get('genre') or ''}
用户要求：{user_requirements or '竖屏、不要字幕、无BGM'}

## 人物/世界观
{bible[:3000]}

## 各集剧本摘录
{scripts_preview[:6000]}

{VISUAL_SCHEMA_HINT}
episode_notes 必须覆盖第{from_ep}到第{to_ep}集。
"""
        try:
            raw = await client.chat(
                [
                    {
                        "role": "system",
                        "content": "你是短剧视效统筹。只输出合法 JSON 视觉连贯性草稿。",
                    },
                    {"role": "user", "content": prompt},
                ]
            )
            draft = _parse_json_loose(raw or "")
            if not draft:
                raise ValueError("empty visual draft")
            return draft
        except Exception:
            logger.exception("visual draft failed, fallback")
            return {
                "style": "都市写实短剧，电影级光影，竖屏9:16",
                "characters": [],
                "locations": [],
                "props": [],
                "global_rules": [
                    "不要字幕",
                    "无BGM，只保留环境音与动作音",
                    "人物外貌跨集一致",
                ],
                "episode_notes": [{"n": n, "hook_visual": "", "key_shots": []} for n in range(from_ep, to_ep + 1)],
                "_source": "fallback",
            }

    async def _spawn_writers(
        self,
        *,
        drama_id: str,
        episodes: List[Dict[str, Any]],
        visual_text: str,
        bible: str,
        user_requirements: str,
        target_model: str,
        context: Dict[str, Any],
        event_queue: asyncio.Queue,
    ) -> List[Dict[str, Any]]:
        from utils.agent_infra.subagents import SubagentRunner, SubagentSpec
        from utils.drama_manager import get_drama_manager

        runner = SubagentRunner(max_parallel=self.max_parallel)
        mgr = get_drama_manager()
        results: List[Dict[str, Any]] = []

        async def _one(ep: Dict[str, Any]) -> Dict[str, Any]:
            n = int(ep["number"])
            script = ep.get("content") or ""
            child_ctx = {
                "user_id": context.get("user_id"),
                "session_id": context.get("session_id"),
                "drama_id": drama_id,
                "project_id": drama_id,
                "episode_number": n,
                "episode_script": script,
                "visual_continuity": visual_text,
                "bible_excerpt": bible[:4000],
                "user_requirements": user_requirements,
                "target_model": target_model,
                "save": False,  # 父级统一落盘
                "parent_agent": self.agent_name,
            }
            await event_queue.put(
                self._event(
                    "subagent_start",
                    {
                        "agent_id": "video_prompt_writer",
                        "episode_number": n,
                        "task": f"将第{n}集剧本转为 Seedance 视频提示词",
                        "title": f"第{n}集视频提示词",
                    },
                    metadata={
                        "agent_id": "video_prompt_writer",
                        "episode_number": n,
                        "parent_id": self.agent_name,
                    },
                )
            )

            chunks: List[str] = []

            async def _on_event(ev: Dict[str, Any]) -> None:
                meta = dict(ev.get("metadata") or {})
                meta["from_subagent"] = "video_prompt_writer"
                meta["episode_number"] = n
                meta["parent_id"] = self.agent_name
                et = ev.get("event_type") or ""
                data = ev.get("data")
                if et in ("llm_chunk", "message", "content") and isinstance(data, str):
                    chunks.append(data)
                await event_queue.put({**ev, "metadata": meta})

            result = await runner.spawn(
                SubagentSpec(
                    agent_id="video_prompt_writer",
                    task=(
                        f"将第{n}集剧本转为豆包 Seedance 视频提示词。"
                        f"用户要求：{user_requirements or '竖屏短剧、不要字幕'}。"
                    ),
                    context_keys=[
                        "episode_number",
                        "episode_script",
                        "visual_continuity",
                        "bible_excerpt",
                        "user_requirements",
                        "target_model",
                        "save",
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
            title = f"第{n}集 · 视频提示词"
            for line in (content or "").splitlines():
                if line.startswith("#"):
                    title = line.lstrip("# ").strip() or title
                    break
            err = result.error
            saved = None
            if result.success and content:
                try:
                    saved = await mgr.save_video_prompt(drama_id, n, title, content)
                except Exception as e:
                    err = str(e)
                    logger.exception("save video prompt ep%s failed", n)

            payload = {
                "agent_id": "video_prompt_writer",
                "episode_number": n,
                "success": bool(result.success and content and not err),
                "title": title,
                "word_count": len(content or ""),
                "preview": (content or "")[:240],
                "error": err,
                "duration_ms": result.duration_ms,
                "path": (saved or {}).get("path"),
            }
            await event_queue.put(
                self._event(
                    "subagent_end",
                    payload,
                    metadata={
                        "agent_id": "video_prompt_writer",
                        "episode_number": n,
                        "success": payload["success"],
                        "parent_id": self.agent_name,
                    },
                )
            )
            return payload

        tasks = [asyncio.create_task(_one(e)) for e in episodes]
        for t in asyncio.as_completed(tasks):
            results.append(await t)
        results.sort(key=lambda r: int(r.get("episode_number") or 0))
        return results

    async def process_request(
        self,
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        from utils.drama_manager import get_drama_manager
        from utils.atomic_write import atomic_write_text_async

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
            request_data.get("user_requirements") or context.get("user_requirements") or query
        ).strip()
        target_model = str(
            request_data.get("target_model")
            or context.get("target_model")
            or "豆包 Seedance 2.5"
        )

        yield self._event(
            "agent_decision",
            {"mode": "video_prompt_batch", "message": "视频提示词批量编排：视觉草稿 → 并行转换"},
            metadata={"active_agent": self.agent_name},
        )
        yield self._event("system", "🎞️ 视频提示词批量编排已启动")

        if not drama_id:
            yield self._event("error", "缺少 drama_id")
            yield self._event("complete", {"success": False, "error": "missing drama_id"})
            return

        mgr = get_drama_manager()
        meta = await mgr._load_meta(drama_id)
        if not meta:
            yield self._event("error", "短剧不存在")
            yield self._event("complete", {"success": False, "error": "drama not found"})
            return

        # 找出已完成剧本
        total = int(meta.get("total_episodes") or 80)
        available: List[int] = []
        for n in range(1, total + 1):
            ep = await mgr.get_episode(drama_id, n)
            if ep.get("status") == "done" and (ep.get("content") or "").strip():
                available.append(n)

        from_ep, to_ep = self._resolve_range(request_data, context, meta, available)
        targets = [n for n in available if from_ep <= n <= to_ep]
        if not targets:
            yield self._event(
                "error",
                f"第{from_ep}–{to_ep}集尚无已完成剧本，请先分集创作",
            )
            yield self._event("complete", {"success": False, "error": "no scripts"})
            return

        yield self._event(
            "system",
            f"将转换第 {targets[0]}–{targets[-1]} 集剧本 → {target_model}（共 {len(targets)} 集）",
            metadata={"from_episode": targets[0], "to_episode": targets[-1]},
        )

        bible = mgr._bible_text(drama_id)
        outline_path = mgr._dir(drama_id) / "outline" / "series_outline.md"
        if outline_path.exists():
            bible = (bible + "\n\n" + outline_path.read_text(encoding="utf-8")[:2000]).strip()

        scripts_preview_parts = []
        episode_payloads = []
        for n in targets:
            ep = await mgr.get_episode(drama_id, n)
            episode_payloads.append(ep)
            scripts_preview_parts.append(
                f"### 第{n}集 {ep.get('title')}\n{(ep.get('content') or '')[:900]}"
            )

        yield self._event("thinking", "编写视觉连贯性草稿（人物/场景/风格跨集锁定）…")
        visual = await self._build_visual_draft(
            meta=meta,
            bible=bible,
            scripts_preview="\n\n".join(scripts_preview_parts),
            from_ep=targets[0],
            to_ep=targets[-1],
            user_requirements=user_requirements,
        )
        visual_text = json.dumps(visual, ensure_ascii=False, indent=2)
        vpath = mgr._dir(drama_id) / "video_prompts" / "visual_continuity.json"
        vpath.parent.mkdir(parents=True, exist_ok=True)
        await atomic_write_text_async(vpath, visual_text)
        yield self._event(
            "system",
            f"✅ 视觉连贯性草稿已就绪（人物 {len(visual.get('characters') or [])} · 场景 {len(visual.get('locations') or [])}）",
            metadata={"visual_continuity": True},
        )
        yield self._event(
            "composition",
            {
                "phase": "parallel_spawn",
                "agents": ["video_prompt_writer"] * len(targets),
                "message": f"并行启动 {len(targets)} 个视频提示词 subagents",
            },
        )

        context.update(
            {
                "user_id": user_id,
                "session_id": session_id,
                "drama_id": drama_id,
            }
        )
        queue: asyncio.Queue = asyncio.Queue()

        async def _run() -> List[Dict[str, Any]]:
            try:
                return await self._spawn_writers(
                    drama_id=drama_id,
                    episodes=episode_payloads,
                    visual_text=visual_text,
                    bible=bible,
                    user_requirements=user_requirements,
                    target_model=target_model,
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

        lines = [
            f"## 视频提示词批量完成 · 《{meta.get('title')}》",
            f"- 目标模型：{target_model}",
            f"- 范围：第 {targets[0]}–{targets[-1]} 集",
            f"- 成功：{len(ok)} / {len(targets)}",
            f"- 落盘目录：`video_prompts/ep_XXX.md`",
            "",
            "### 各集",
        ]
        for r in results:
            lines.append(
                f"- **第{r.get('episode_number')}集** "
                f"{'✅' if r.get('success') else '❌'} · {r.get('word_count') or 0}字"
                f"{(' · `' + str(r.get('path')) + '`') if r.get('path') else ''}"
            )
        if fail:
            lines.append(
                "\n失败："
                + "、".join(f"第{r.get('episode_number')}集({r.get('error')})" for r in fail)
            )
        lines.append("\n可复制各集「可复制提示词」块粘贴到豆包/即梦视频生成。")
        summary = "\n".join(lines)

        for i in range(0, len(summary), 100):
            yield self._event("llm_chunk", summary[i : i + 100])

        yield self._event(
            "complete",
            {
                "success": len(fail) == 0,
                "drama_id": drama_id,
                "from_episode": targets[0],
                "to_episode": targets[-1],
                "results": results,
                "content": summary,
            },
            metadata={"success": len(fail) == 0},
        )
