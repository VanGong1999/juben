"""
单集剧本 → 豆包 Seedance 视频生成提示词（Subagent）
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Optional

logger = logging.getLogger("VideoPromptWriterAgent")


def _load_prompt() -> str:
    path = Path(__file__).resolve().parent.parent / "prompts" / "video_prompt_writer_system.txt"
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return (
            "你是短剧分集转豆包 Seedance 视频提示词专家。"
            "输出含视觉锚点、分镜表与逐镜可复制提示词的 Markdown。"
        )


class VideoPromptWriterAgent:
    """单集视频提示词子专家。"""

    def __init__(
        self,
        model_provider: str = "deepseek",
        model: Optional[str] = None,
    ):
        self.agent_name = "video_prompt_writer"
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
            "display_name": "单集视频提示词",
            "capabilities": ["script_to_seedance", "shot_breakdown", "copyable_prompts"],
        }

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
        ep_n = int(
            context.get("episode_number")
            or request_data.get("episode_number")
            or 0
        )
        script = (
            context.get("episode_script")
            or request_data.get("episode_script")
            or ""
        )
        visual_bible = (
            context.get("visual_continuity")
            or request_data.get("visual_continuity")
            or ""
        )
        bible = context.get("bible_excerpt") or request_data.get("bible_excerpt") or ""
        user_req = (
            context.get("user_requirements")
            or request_data.get("user_requirements")
            or ""
        )
        target_model = (
            context.get("target_model")
            or request_data.get("target_model")
            or "豆包 Seedance 2.5"
        )

        # 若未注入剧本但有 drama_id，尝试读取
        drama_id = context.get("drama_id") or request_data.get("drama_id")
        if not script and drama_id and ep_n:
            try:
                from utils.drama_manager import get_drama_manager

                ep = await get_drama_manager().get_episode(drama_id, ep_n)
                script = ep.get("content") or ""
            except Exception:
                logger.exception("load episode script failed")

        label = f"第{ep_n}集" if ep_n else "本集"
        yield self._event(
            "system",
            f"🎥 视频提示词专家启动：{label} → {target_model}",
            metadata={"episode_number": ep_n, "subagent_role": "video_prompt_writer"},
        )

        if not (script or "").strip():
            yield self._event("error", f"{label} 剧本为空，无法转换", metadata={"episode_number": ep_n})
            yield self._event(
                "complete",
                {"success": False, "error": "empty script", "episode_number": ep_n},
            )
            return

        yield self._event(
            "thinking",
            "拆分镜、锁定视觉锚点、按 Seedance 方言写可复制提示词…",
            metadata={"episode_number": ep_n},
        )

        user_prompt = f"""请将以下 {label} 剧本转为豆包 Seedance 视频提示词文档。

## 目标模型
{target_model}

## 用户要求（最高优先级）
{user_req or "竖屏短剧、不要字幕、无BGM只保留环境音与动作音、偏电影级写实光影"}

## 跨集视觉连贯性（必须遵守）
{visual_bible[:3500] if visual_bible else "（无；请从剧本与人物设定自行锁定外貌/服装）"}

## 人物/世界观摘录
{bible[:2500] if bible else "（无）"}

## {label} 剧本正文
{script[:8000]}

## 任务原文
{query}

请按系统提示的 Markdown 结构完整输出，逐镜「可复制提示词」必须可直接粘贴到豆包视频生成框。
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
            logger.exception("video_prompt_writer LLM failed")
            yield self._event("error", str(e), metadata={"episode_number": ep_n})
            yield self._event(
                "complete",
                {"success": False, "error": str(e), "episode_number": ep_n},
            )
            return

        text = (content or "").strip()
        if ep_n and not re.search(rf"第\s*{ep_n}\s*集", text[:120]):
            if not text.startswith("#"):
                text = f"# 第{ep_n}集 · Seedance 视频提示词\n\n{text}"

        # 可选落盘（单集直调时）
        save = bool(context.get("save") or request_data.get("save") or drama_id)
        saved = None
        if save and drama_id and ep_n and text:
            try:
                from utils.drama_manager import get_drama_manager

                title = f"第{ep_n}集 · 视频提示词"
                for line in text.splitlines():
                    if line.startswith("#"):
                        title = line.lstrip("# ").strip() or title
                        break
                saved = await get_drama_manager().save_video_prompt(
                    drama_id, ep_n, title, text
                )
            except Exception as e:
                logger.exception("save video prompt failed")
                yield self._event(
                    "system",
                    f"落盘失败（仍返回正文）：{e}",
                    metadata={"episode_number": ep_n},
                )

        chunk = 140
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
                "word_count": len(text),
                "saved": bool(saved),
                "path": (saved or {}).get("path"),
            },
            metadata={"episode_number": ep_n},
        )
