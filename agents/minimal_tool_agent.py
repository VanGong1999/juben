"""
MinimalToolAgent — 独立最小 Agent Runtime（不继承重型 BaseJubenAgent，避免循环导入）

system_prompt + tool 名列表 → context budget → run_tool_loop → 事件流
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

logger = logging.getLogger("MinimalToolAgent")


class MinimalToolAgent:
    """声明式工具 Agent：LLM-native tool loop。"""

    # 核心常驻；web_search / knowledge_query 等走 tool_search 激活
    DEFAULT_TOOLS = ["tool_search", "skill_search", "load_skill", "date", "ls", "read", "grep"]

    def __init__(
        self,
        agent_name: str = "minimal_tool_agent",
        *,
        system_prompt: Optional[str] = None,
        tool_names: Optional[List[str]] = None,
        max_steps: int = 8,
        model_provider: str = "deepseek",
        model: Optional[str] = None,
    ):
        self.agent_name = agent_name
        self._tool_names = list(tool_names or self.DEFAULT_TOOLS)
        self._max_tool_steps = max_steps
        self.model_provider = model_provider
        self.model = model
        self.system_prompt = system_prompt or (
            "你是一个会调用工具的助手。核心工具可直接用；"
            "Deferred Tools 名录里的低频工具需先 tool_search 激活再调用。"
            "不要编造工具结果。"
        )
        self.llm_client = None

    def _ensure_client(self):
        if self.llm_client is None:
            from utils.llm_client import get_llm_client

            self.llm_client = get_llm_client(provider=self.model_provider, model=self.model)
        return self.llm_client

    def _event(self, event_type: str, data: Any, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {
            "event_type": event_type,
            "agent_source": self.agent_name,
            "timestamp": datetime.now().isoformat(),
            "data": data,
            "metadata": metadata or {},
        }

    async def process_request(
        self,
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        from utils.agent_infra.checkpoint import CheckpointStore
        from utils.agent_infra.context_budget import assemble_budgeted_prompt
        from utils.agent_infra.prompt_cache import strip_internal_fields
        from utils.agent_infra.runtime import run_tool_loop
        from utils.agent_tools import ToolContext, get_agent_tool_registry, get_tool_harness

        context = context or {}
        user_id = context.get("user_id") or request_data.get("user_id") or "default_user"
        session_id = context.get("session_id") or request_data.get("session_id") or "default"
        drama_id = context.get("drama_id") or request_data.get("drama_id")
        allow_write = bool(context.get("allow_write") or request_data.get("allow_write"))
        query = (
            request_data.get("input")
            or request_data.get("query")
            or request_data.get("message")
            or ""
        )

        yield self._event("system", "MinimalToolAgent 启动 tool loop…")

        from utils.agent_infra.disclosure import prepare_disclosure

        registry = get_agent_tool_registry()
        disclosure = prepare_disclosure(
            registry,
            extra_core=list(self._tool_names),
            include_meta=True,
            include_skills_catalog=True,
            include_agents_catalog=False,
            allow_write=allow_write,
        )
        assembled = await assemble_budgeted_prompt(
            system_prompt=self.system_prompt + "\n\n" + disclosure.prompt_append,
            user_messages=[{"role": "user", "content": query}],
            drama_id=drama_id,
            user_id=user_id,
            query=query,
            session_id=session_id,
            agent_id=self.agent_name,
            tools=disclosure.tools,
        )
        messages = strip_internal_fields(assembled.messages)
        tools = disclosure.tools

        async def on_step(ev: Dict[str, Any]) -> None:
            # on_step 不能直接 yield；结果经 queue 由外层消费不方便，
            # 此处仅打日志；关键 tool 事件在结果 history 里。
            if ev.get("type") == "tool":
                logger.info("tool step: %s", (ev.get("result") or {}).get("tool_name"))

        client = self._ensure_client()
        checkpoint_id = f"{session_id}:{self.agent_name}"
        result = await run_tool_loop(
            client=client,
            messages=messages,
            tools=tools,
            harness=get_tool_harness(),
            tool_ctx=ToolContext(
                user_id=user_id,
                session_id=session_id,
                drama_id=drama_id,
                agent_id=self.agent_name,
                allow_write=allow_write,
                metadata={"activated_tools": sorted(disclosure.activated)},
            ),
            max_steps=self._max_tool_steps,
            checkpoint_store=CheckpointStore(),
            checkpoint_id=checkpoint_id,
            on_step=on_step,
            prompt_cache_extra=assembled.extra_body,
        )

        for th in result.tool_history or []:
            yield self._event(
                "tool_call",
                th.get("tool_name") or "",
                metadata={"parameters": th.get("parameters"), "tool_call_id": th.get("tool_call_id")},
            )
            yield self._event(
                "tool_return",
                th.get("llm_text") or th.get("error") or "",
                metadata={"success": th.get("success"), "tool_name": th.get("tool_name")},
            )

        content = result.content or ""
        chunk_size = 80
        for i in range(0, len(content), chunk_size):
            yield self._event("llm_chunk", content[i : i + chunk_size])

        yield self._event(
            "complete",
            {
                "content": content,
                "trace_id": result.trace_id,
                "steps": result.steps,
                "checkpoint_id": checkpoint_id,
            },
        )
