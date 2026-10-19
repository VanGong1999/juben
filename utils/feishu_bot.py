"""
飞书机器人核心：WebSocket 长连接 + 消息路由 + Agent 调度 + 文档产出

职责（业务层，依赖 utils/feishu_client.py 做底层 API）：
  - 通过 lark-oapi 的 WebSocket 长连接接收 im.message.receive_v1 事件
  - 解析用户命令，路由到现有 Agent（复用 utils.agent_runtime / utils.agent_dispatch）
  - 把 Agent 产出回复到飞书，或按 /doc 命令写入飞书云文档

设计要点：
  - 事件回调是同步的（飞书要求 3 秒内返回），因此回调只把任务入队立即返回；
    真正的 Agent 调用在独立 worker 线程 + 独立 asyncio loop 里异步执行。
  - 默认走 JubenConductor 自动编排（与网页端一致）；用户可用 /agent <id> 指定专家。
  - 完全独立于 chat_routes：不修改任何现有请求处理路径。
"""
from __future__ import annotations

import asyncio
import json
import logging
import queue
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from utils import feishu_client as fc

logger = logging.getLogger("FeishuBot")

# Agent 调用产生的最终内容事件类型（与 chat_routes 收集逻辑对齐）
_CONTENT_EVENT_TYPES = {"llm_chunk", "final_result", "content", "message"}

# 飞书 text 消息单段最大字符（超长分段发送）
_MAX_REPLY_CHARS = 3500


@dataclass
class SessionState:
    """单个飞书会话（chat）的状态。"""

    session_id: str
    agent_id: Optional[str] = None  # None 表示自动编排（conductor）
    transcript: List[Dict[str, str]] = field(default_factory=list)


def _now() -> str:
    from datetime import datetime
    return datetime.now().isoformat()


class FeishuBot:
    """飞书机器人单例。"""

    _instance: Optional["FeishuBot"] = None

    def __init__(self) -> None:
        self._ws_client: Any = None
        self._ws_thread: Optional[threading.Thread] = None
        self._worker_thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._task_queue: "queue.Queue[Optional[tuple]]" = queue.Queue()
        self._sessions: Dict[str, SessionState] = {}
        self._running = False
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # 单例与生命周期
    # ------------------------------------------------------------------
    @classmethod
    def get_instance(cls) -> "FeishuBot":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        """启动：后台 worker 线程 + WebSocket 长连接线程。"""
        if not fc.feishu_enabled():
            logger.info("飞书集成未启用（FEISHU_ENABLED != true），跳过启动")
            return

        with self._lock:
            if self._running:
                logger.info("飞书机器人已在运行")
                return
            self._running = True

        # 1) worker 线程：独立 asyncio loop 消费任务队列
        self._worker_thread = threading.Thread(
            target=self._run_worker, name="feishu-worker", daemon=True
        )
        self._worker_thread.start()

        # 2) ws 长连接线程（阻塞在 client.start()）
        self._ws_thread = threading.Thread(
            target=self._run_ws, name="feishu-ws", daemon=True
        )
        self._ws_thread.start()
        logger.info("✅ 飞书机器人已启动（WebSocket 长连接）")

    def stop(self) -> None:
        """停止 worker 与 ws 连接。"""
        with self._lock:
            if not self._running:
                return
            self._running = False

        # 停止 ws
        ws = self._ws_client
        if ws is not None:
            try:
                ws._disconnect()
            except Exception:
                logger.warning("飞书 ws 断开失败", exc_info=True)

        # 停止 worker：塞入哨兵
        self._task_queue.put(None)
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5)
        logger.info("飞书机器人已停止")

    # ------------------------------------------------------------------
    # WebSocket 连接
    # ------------------------------------------------------------------
    def _run_ws(self) -> None:
        lark = fc._ensure_sdk()
        from lark_oapi.api.im.v1 import P2ImMessageReceiveV1

        # 事件分发器：builder 两个参数必须填空字符串
        def on_message(data: P2ImMessageReceiveV1) -> None:
            self._on_message(data)

        event_handler = (
            lark.EventDispatcherHandler.builder("", "")
            .register_p2_im_message_receive_v1(on_message)
            .build()
        )

        app_id, app_secret = fc._app_credentials()
        client = lark.ws.Client(
            app_id,
            app_secret,
            event_handler=event_handler,
            log_level=lark.LogLevel.INFO,
        )
        self._ws_client = client
        try:
            client.start()
        except Exception:
            logger.error("飞书 WebSocket 长连接异常退出", exc_info=True)

    # ------------------------------------------------------------------
    # 事件回调（同步，快速入队）
    # ------------------------------------------------------------------
    def _on_message(self, data: Any) -> None:
        try:
            event = data.event
            message = event.message
            chat_id = getattr(message, "chat_id", None)
            message_id = getattr(message, "message_id", None)
            message_type = getattr(message, "message_type", "text")

            # 只处理文本消息；其余类型忽略（图片/文件/富文本暂不支持）
            if message_type != "text":
                logger.info("飞书忽略非文本消息 type=%s", message_type)
                return

            content = getattr(message, "content", "") or ""
            text = self._extract_text(content)
            if not text:
                return

            sender_id = ""
            sender = getattr(event, "sender", None)
            if sender is not None:
                sid = getattr(sender, "sender_id", None)
                sender_id = (
                    getattr(sid, "open_id", None)
                    or getattr(sid, "user_id", None)
                    or str(sid)
                )

            self._task_queue.put((chat_id, text, message_id, sender_id))
        except Exception:
            logger.error("飞书事件解析失败", exc_info=True)

    @staticmethod
    def _extract_text(content: str) -> str:
        """解析 text 消息 content（JSON 字符串，形如 {"text":"..."}）。"""
        try:
            obj = json.loads(content)
            if isinstance(obj, dict):
                return obj.get("text", "") or ""
        except Exception:
            pass
        return content

    # ------------------------------------------------------------------
    # Worker：独立 asyncio loop
    # ------------------------------------------------------------------
    def _run_worker(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._consume_tasks())
        except Exception:
            logger.error("飞书 worker 异常退出", exc_info=True)

    async def _consume_tasks(self) -> None:
        loop = asyncio.get_event_loop()
        while True:
            task = await loop.run_in_executor(None, self._task_queue.get)
            if task is None:  # 哨兵，退出
                break
            chat_id, text, message_id, sender_id = task
            try:
                await self._handle_task(chat_id, text, message_id, sender_id)
            except Exception:
                logger.error("飞书消息处理失败", exc_info=True)
                fc.reply_message(message_id, "处理你的消息时出错了，请稍后重试。")

    # ------------------------------------------------------------------
    # 消息处理（命令解析 + Agent 调用）
    # ------------------------------------------------------------------
    async def _handle_task(
        self,
        chat_id: str,
        text: str,
        message_id: str,
        sender_id: str,
    ) -> None:
        state = self._get_session(chat_id)
        text = text.strip()

        # 命令分派（均同步返回，不调用 Agent）
        lower = text.lower()
        if lower in ("/help", "帮助", "help"):
            fc.reply_message(message_id, self._help_text())
            return
        if lower in ("/lists", "/agents", "agent列表"):
            fc.reply_message(message_id, self._agents_list_text())
            return
        if lower in ("/skills", "skill列表"):
            fc.reply_message(message_id, self._skills_list_text())
            return
        if lower in ("/done", "/auto"):
            state.agent_id = None
            fc.reply_message(message_id, "已回到自由编排（JubenConductor 自动编排）。")
            return
        if lower in ("/reset", "重置"):
            state.transcript.clear()
            state.agent_id = None
            fc.reply_message(message_id, "会话已重置，回到自由编排。")
            return
        if lower.startswith("/agent"):
            self._handle_agent_command(state, text, message_id)
            return
        if lower.endswith("-agents"):
            self._handle_agent_suffix_command(state, text, message_id)
            return
        if lower.startswith("/doc"):
            self._handle_doc_command(state, text, message_id)
            return

        # 普通消息：路由到 Agent 并异步生成回复
        await self._run_agent_and_reply(state, text, message_id, sender_id)

    # ------------------------------------------------------------------
    # 命令实现
    # ------------------------------------------------------------------
    def _switch_agent(
        self, state: SessionState, target: str, message_id: str
    ) -> None:
        """切换当前会话的 Agent（target 为空/auto/conductor 则回到自由编排）。"""
        from utils.agent_runtime import normalize_agent_id
        from config.agents import get_agent_config

        target = (target or "").strip().lower()
        if target in ("", "auto", "conductor", "juben_conductor"):
            state.agent_id = None
            fc.reply_message(message_id, "已回到自由编排（JubenConductor 自动编排）。")
            return

        normalized = normalize_agent_id(target)
        cfg = get_agent_config(normalized)
        if cfg is None:
            fc.reply_message(
                message_id,
                f"未找到 Agent `{target}`。发送 `/lists` 查看可用列表。",
            )
            return

        state.agent_id = normalized
        fc.reply_message(
            message_id,
            f"已切换到 {cfg.get('display_name', normalized)}，"
            f"后续消息将由该专家处理。发送 `/done` 回到自由编排。",
        )

    def _handle_agent_command(
        self, state: SessionState, text: str, message_id: str
    ) -> None:
        """处理 /agent <id> 命令（兼容旧写法）。"""
        rest = text.split(None, 1)
        arg = rest[1].strip() if len(rest) > 1 else ""
        if not arg:
            current = state.agent_id or "auto"
            fc.reply_message(
                message_id,
                f"当前 Agent：{current}\n"
                f"发送 `/lists` 查看全部 Agent，`/done` 回到自由编排。",
            )
            return
        self._switch_agent(state, arg.split(None, 1)[0], message_id)

    def _handle_agent_suffix_command(
        self, state: SessionState, text: str, message_id: str
    ) -> None:
        """处理 /<agent_id>-agents 命令（如 /short_drama_planner-agents）。"""
        raw = text.strip()
        if raw.startswith("/"):
            raw = raw[1:]
        target = raw[: -len("-agents")].strip() if raw.endswith("-agents") else raw
        self._switch_agent(state, target, message_id)

    def _handle_doc_command(
        self, state: SessionState, text: str, message_id: str
    ) -> None:
        """处理 /doc 命令：把当前会话内容写入飞书云文档。"""
        title = text.split(None, 1)[1].strip() if len(text.split(None, 1)) > 1 else ""
        if not title:
            title = f"剧本创作会话 {_now()[:10]}"

        if not state.transcript:
            fc.reply_message(message_id, "当前会话还没有可导出的内容。")
            return

        try:
            markdown = self._transcript_to_markdown(state, title)
            document_id = fc.create_document(title)
            if not document_id:
                fc.reply_message(message_id, "创建飞书文档失败，请稍后重试。")
                return
            if not fc.append_document_markdown(document_id, markdown):
                fc.reply_message(message_id, "写入飞书文档失败，请稍后重试。")
                return

            url = fc.document_url(document_id)
            fc.reply_message(
                message_id,
                f"已导出当前会话内容到飞书文档：\n{url}",
            )
        except Exception:
            logger.error("飞书 /doc 处理失败", exc_info=True)
            fc.reply_message(message_id, "导出文档时出错，请稍后重试。")

    # ------------------------------------------------------------------
    # Agent 调用（复用现有运行时）
    # ------------------------------------------------------------------
    async def _run_agent_and_reply(
        self,
        state: SessionState,
        text: str,
        message_id: str,
        sender_id: str,
    ) -> None:
        from utils.agent_runtime import load_agent
        from utils.agent_dispatch import build_agent_generator
        from utils.agent_infra.handoffs import resolve_turn_agent

        # 先回复一个"正在处理"，避免用户以为没反应（飞书 3 秒超时约束）
        fc.reply_message(message_id, "正在处理，请稍候…")

        # 解析本轮实际 agent
        resolved = resolve_turn_agent(
            agent_id=state.agent_id,
            session_id=state.session_id,
        )
        agent_id = resolved["agent_id"]

        try:
            agent = load_agent(agent_id, fresh=True)
        except Exception as e:
            logger.error("飞书加载 Agent 失败 agent_id=%s err=%s", agent_id, e)
            fc.reply_message(message_id, f"加载 Agent `{agent_id}` 失败。")
            return

        # 记录用户消息
        state.transcript.append({"role": "user", "content": text})

        request_data = {
            "input": text,
            "query": text,
            "user_id": sender_id or f"feishu_{state.session_id}",
            "session_id": state.session_id,
            "file_ids": [],
            "auto_mode": True,
            "user_selections": [],
            "stream_mode": True,
            "resolved_agent_id": agent_id,
            "agent_route_source": resolved.get("source"),
        }
        context = {
            "user_id": sender_id or f"feishu_{state.session_id}",
            "session_id": state.session_id,
            "resolved_agent_id": agent_id,
            "agent_route_source": resolved.get("source"),
        }

        # 收集最终内容
        collected: List[str] = []
        try:
            async for ev in build_agent_generator(agent, request_data, context):
                et = ev.get("event_type") or ev.get("type") or ""
                data = ev.get("data")
                if et in _CONTENT_EVENT_TYPES and isinstance(data, str):
                    collected.append(data)
        except Exception as e:
            logger.error("飞书 Agent 生成失败 agent_id=%s err=%s", agent_id, e)
            fc.reply_message(message_id, f"Agent `{agent_id}` 生成内容时出错。")
            return

        reply = "".join(collected).strip()
        if not reply:
            reply = "（本次没有产生文本内容）"

        # 记录助手消息
        state.transcript.append({"role": "assistant", "content": reply})

        # 分段回复
        for chunk in self._split_reply(reply):
            fc.reply_message(message_id, chunk)

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------
    def _get_session(self, chat_id: str) -> SessionState:
        with self._lock:
            state = self._sessions.get(chat_id)
            if state is None:
                state = SessionState(session_id=f"feishu_{chat_id}")
                self._sessions[chat_id] = state
            return state

    @staticmethod
    def _split_reply(text: str, max_chars: int = _MAX_REPLY_CHARS) -> List[str]:
        """把长回复按段落拆成多段（每段不超过 max_chars）。"""
        if len(text) <= max_chars:
            return [text]
        parts: List[str] = []
        buf = ""
        for line in text.split("\n"):
            if len(buf) + len(line) + 1 > max_chars:
                if buf:
                    parts.append(buf)
                buf = line
            else:
                buf = f"{buf}\n{line}" if buf else line
        if buf:
            parts.append(buf)
        return parts

    @staticmethod
    def _help_text() -> str:
        return (
            "我是剧本创作助手，你可以直接跟我对话，我会自动调用合适的专家 Agent。\n\n"
            "可用命令：\n"
            "· /lists — 列出所有 Agent\n"
            "· /skills — 列出所有创作技法 Skill\n"
            "· /<agent_id>-agents — 与指定专家对话（如 /short_drama_planner-agents）\n"
            "· /done — 回到自由编排\n"
            "· /doc [标题] — 把当前会话内容导出到飞书文档\n"
            "· /reset — 重置当前会话\n"
            "· /help — 显示本帮助"
        )

    @staticmethod
    def _agents_list_text() -> str:
        from config.agents import get_all_agents_config

        configs = get_all_agents_config(include_utility=True)
        lines = ["可用 Agent（发送 /<id>-agents 切换，/done 回到自由编排）："]
        for cfg in configs:
            aid = cfg.get("id", "")
            if aid == "auto":
                continue
            name = cfg.get("display_name", aid)
            lines.append(f"· /{aid}-agents — {name}")
        return "\n".join(lines)

    @staticmethod
    def _skills_list_text() -> str:
        from utils.skill_loader import list_skills

        skills = list_skills()
        lines = ["可用创作技法 Skill："]
        for s in skills:
            sid = s.get("id", "")
            name = s.get("name", "")
            lines.append(f"· {sid} — {name}")
        return "\n".join(lines)

    @staticmethod
    def _transcript_to_markdown(state: SessionState, title: str) -> str:
        lines = [f"# {title}", ""]
        for item in state.transcript:
            role = item.get("role")
            content = item.get("content", "")
            if role == "user":
                lines.append(f"## 用户\n\n{content}\n")
            else:
                lines.append(f"## 助手\n\n{content}\n")
        return "\n".join(lines)


def get_feishu_bot() -> FeishuBot:
    """获取飞书机器人单例。"""
    return FeishuBot.get_instance()


__all__ = ["FeishuBot", "get_feishu_bot"]
