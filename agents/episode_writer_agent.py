"""
单集编剧 Subagent — 每实例只写一集，依赖父编排下发的连贯性草稿。
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Optional

logger = logging.getLogger("EpisodeWriterAgent")


def _load_prompt() -> str:
    path = Path(__file__).resolve().parent.parent / "prompts" / "episode_writer_system.txt"
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return (
            "你是竖屏短剧单集编剧。只输出指定一集的完整剧本 Markdown，"
            "遵守连贯性草稿与禁止重复清单。"
        )


class EpisodeWriterAgent:
    """单集写作子专家：上下文隔离，不继承重型 BaseJubenAgent。"""

    def __init__(
        self,
        model_provider: str = "deepseek",
        model: Optional[str] = None,
    ):
        self.agent_name = "episode_writer"
        self.model_provider = model_provider
        self.model = model or "deepseek-flash"
        self.system_prompt = _load_prompt()
        self.llm_client = None

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
            "display_name": "单集编剧",
            "capabilities": ["single_episode_write", "continuity_aware"],
        }

    @staticmethod
    def _extract_episode_slot(context: Dict[str, Any], request_data: Dict[str, Any]) -> Dict[str, Any]:
        slot = context.get("episode_slot") or request_data.get("episode_slot") or {}
        if isinstance(slot, str):
            try:
                slot = json.loads(slot)
            except json.JSONDecodeError:
                slot = {}
        return dict(slot) if isinstance(slot, dict) else {}

    async def process_request(
        self,
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        context = context or {}
        query = (
            request_data.get("input")
            or request_data.get("query")
            or request_data.get("message")
            or ""
        )
        slot = self._extract_episode_slot(context, request_data)
        ep_n = int(slot.get("n") or context.get("episode_number") or request_data.get("episode_number") or 0)
        target_words = int(context.get("target_words") or request_data.get("target_words") or 800)
        continuity = context.get("continuity_draft") or request_data.get("continuity_draft") or {}
        bible = context.get("bible_excerpt") or request_data.get("bible_excerpt") or ""
        user_req = context.get("user_requirements") or request_data.get("user_requirements") or ""
        neighbors = context.get("neighbor_beats") or request_data.get("neighbor_beats") or []

        label = f"第{ep_n}集" if ep_n else "本集"
        yield self._event(
            "system",
            f"✍️ 单集编剧启动：{label}",
            metadata={"episode_number": ep_n, "subagent_role": "episode_writer"},
        )
        yield self._event(
            "thinking",
            f"核对连贯性草稿、禁止重复与 carry_in/out…（目标约 {target_words} 字）",
            metadata={"episode_number": ep_n},
        )

        slot_json = json.dumps(slot, ensure_ascii=False, indent=2)
        continuity_brief = {
            "series_logline": continuity.get("series_logline"),
            "forbidden_repeats": continuity.get("forbidden_repeats") or [],
            "open_threads": continuity.get("open_threads") or [],
            "character_arcs": continuity.get("character_arcs") or [],
        }
        user_prompt = f"""请撰写 {label} 完整剧本。

## 用户要求（最高优先级）
{user_req or "（无额外要求）"}

## 本集槽位（必须遵守）
{slot_json}

## 邻集节拍（仅作边界，勿写成邻集正文）
{json.dumps(neighbors, ensure_ascii=False, indent=2)}

## 全局连贯性摘要
{json.dumps(continuity_brief, ensure_ascii=False, indent=2)}

## 人物/世界观摘录
{bible[:3500] if bible else "（无）"}

## 任务原文
{query}

只输出 {label} 剧本 Markdown，约 {target_words} 字。
"""

        client = self._ensure_client()
        try:
            content = await client.chat(
                [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
            )
        except Exception as e:
            logger.exception("episode_writer LLM failed")
            yield self._event("error", str(e), metadata={"episode_number": ep_n})
            yield self._event(
                "complete",
                {"success": False, "error": str(e), "episode_number": ep_n},
            )
            return

        text = (content or "").strip()
        if ep_n and not re.search(rf"第\s*{ep_n}\s*集", text[:80]):
            title = str(slot.get("title") or f"第 {ep_n} 集")
            if not text.startswith("#"):
                text = f"# 第{ep_n}集 · {title}\n\n{text}"

        chunk = 120
        for i in range(0, len(text), chunk):
            yield self._event(
                "llm_chunk",
                text[i : i + chunk],
                metadata={"episode_number": ep_n, "from_subagent": self.agent_name},
            )

        yield self._event(
            "complete",
            {
                "success": True,
                "content": text,
                "episode_number": ep_n,
                "title": str(slot.get("title") or f"第 {ep_n} 集"),
                "word_count": len(text),
            },
            metadata={"episode_number": ep_n},
        )
