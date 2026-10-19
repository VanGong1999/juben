"""
JubenConductor — 默认对话大脑

用户可不指定 Agent；Conductor 按需 spawn_subagent / transfer_to / compose_agents。
独立于重型 BaseJubenAgent，避免循环导入（同 MinimalToolAgent 模式）。
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

logger = logging.getLogger("JubenConductor")

# 核心常驻；web_search / knowledge_query / 其它专家详情走 Deferred 名录 + tool_search / agent_search
DEFAULT_ORCHESTRATION_TOOLS = [
    "tool_search",
    "skill_search",
    "load_skill",
    "agent_search",
    "wiki_read",
    "wiki_search",
    "spawn_subagent",
    "transfer_to",
    "compose_agents",
    "return_to_conductor",
    "read_drama_part",
    "save_drama_part",
    "list_drama_artifacts",
    "search_drama_content",
    "date",
    "ls",
    "read",
]

CONDUCTOR_SYSTEM_PROMPT = """你是「剧本工坊」总控编排助手（Conductor）。

职责：理解用户创作/分析意图，决定何时自己回答、何时调用专家、何时移交对话。

决策规则（严格遵守）：
1. 简单问答、澄清需求、总结进度 → 直接回答，不调用工具。
2. 有界子任务（写一版大纲要点、评估某段剧情、生成人物小传）→ 用 spawn_subagent，你保留对用户的最终回复权并合成结果。
3. 用户明确要与某专家持续深入协作（如「帮我写完整剧本」「接下来只跟创作助手聊」）→ 用 transfer_to。
4. 可并行拆分的多专家任务 → 用 compose_agents（mode=parallel 或 pipeline）。
5. 用户要求「写多集 / 自动连载 / 第1–N集 / 并行分集创作」且已有作品（drama_id）→ 优先 spawn_subagent(agent_id=episode_batch_creator)，在 task 中写清集数范围与用户全部要求（语气、禁忌、必须桥段等）；由它先写连贯性草稿再并行单集编剧。
6. 用户要求「剧本转视频提示词 / 豆包 / 即梦 / Seedance / 分镜提示词」→ 单集用 video_prompt_writer，多集用 video_prompt_batch；在 task 写清集数与风格要求。
7. 与专家对话时必须按用户最新要求行动：改某一集就 save_drama_part；改人设/大纲先 read 再 save；不要只口头答应。
8. 仅在专家指令/工具/政策真正不同时才拆分；不要为拆而拆。

渐进式披露（Deferred Loading）：
- 专家与低频工具只在名录中出现；需要详情时先 `agent_search` / `tool_search`，再调用。
- 写作规范用 `skill_search` / `load_skill` 按需加载，不要假设已注入全文。
- 知识库：system 中有 Wiki Index（L1）。需要细节 → `wiki_read`；wiki 不够 → `raw_read`；勿一次装全文。
- 联网检索：先 `tool_search(names=["web_search"])` 再调用 `web_search`。

回复要求：用中文；调用工具后务必基于工具结果给用户清晰结论；交接时简短说明已交给谁。

作品上下文（动态发现，节约 token）：
- 系统会注入「作品文件索引」薄指针；不要假设分集/小传全文已在上下文中。
- 用户点名某集、或消息里有 `@drama[episode:N]` / `@drama[characters]` 等引用时：先 `list_drama_artifacts` 确认，再 `read_drama_part` 读全文；核对人设/桥段用 `search_drama_content`（grep）。
- 写大纲/情节点前必须先确认人物小传已存在：有则 `read_drama_part(target=characters)` 并沿用已有人名，禁止杜撰未出现的角色。
- 评估某一集：必须 `read_drama_part(target=episode, episode_number=N)` 读该集正文后再评，不能只凭大纲/情节点臆测。

写回作品（重要）：
- 用户要求「修改/调整/重写 小传/大纲/世界观/某一集」时，不要只在对话里给文字，而要真正写回作品文件。
- 流程：先 `read_drama_part(target=...)` 读当前内容拿 version → 修改 → `save_drama_part(target=..., content=..., expected_version=刚读到的version)`。
- target 含义：characters=人物小传、outline=大纲、world=世界观、episode=剧本分集（需 episode_number）。
- 若 save 返回「写入冲突」，说明别人改过，重新 read 后基于最新内容再改再 save，不要覆盖。
- 完成后在回复里附上产生的版本号与 diff 摘要。
"""


class JubenConductor:
    """会话级编排 Agent：LLM-native tool loop + 多智能体原语。"""

    def __init__(
        self,
        agent_name: str = "juben_conductor",
        *,
        system_prompt: Optional[str] = None,
        tool_names: Optional[List[str]] = None,
        max_steps: int = 10,
        model_provider: str = "deepseek",
        model: Optional[str] = None,
    ):
        self.agent_name = agent_name
        self._tool_names = list(tool_names or DEFAULT_ORCHESTRATION_TOOLS)
        self._max_tool_steps = max_steps
        self.model_provider = model_provider
        self.model = model
        self.system_prompt = system_prompt or CONDUCTOR_SYSTEM_PROMPT
        self.llm_client = None
        # 可 spawn 的专家池（详情靠 agent_search 渐进披露，不全量塞进 system）
        self.allowed_subagents = [
            "short_drama_planner",
            "short_drama_creator",
            "episode_batch_creator",
            "episode_writer",
            "video_prompt_writer",
            "video_prompt_batch",
            "short_drama_evaluation",
            "script_evaluation",
            "ip_evaluation",
            "story_evaluation",
            "story_outline_evaluation",
            "novel_screening_evaluation",
            "story_five_elements",
            "story_summary_generator",
            "story_type_analyzer",
            "character_profile_generator",
            "character_relationship_analyzer",
            "major_plot_points",
            "detailed_plot_points",
            "plot_points_analyzer",
            "plot_points_workflow",
            "drama_workflow",
            "drama_analysis",
            "series_analysis",
            "mind_map",
            "minimal_tool_agent",
        ]

    def _ensure_client(self):
        if self.llm_client is None:
            from utils.llm_client import get_llm_client

            self.llm_client = get_llm_client(provider=self.model_provider, model=self.model)
        return self.llm_client

    def apply_llm_overrides(
        self,
        *,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        if provider:
            self.model_provider = provider
        if model:
            self.model = model
        # 强制重建客户端
        self.llm_client = None
        if api_key or base_url or provider or model:
            from utils.llm_client import get_llm_client

            kwargs: Dict[str, Any] = {"provider": self.model_provider, "model": self.model}
            # 多数 get_llm_client 实现忽略多余 kwargs；有则传入
            try:
                self.llm_client = get_llm_client(**kwargs)
            except TypeError:
                self.llm_client = get_llm_client(provider=self.model_provider, model=self.model)

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
            "agent_type": "juben_conductor",
            "capabilities": [
                "auto_route",
                "spawn_subagent",
                "handoff",
                "compose_agents",
            ],
            "tools": list(self._tool_names),
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
        drama_id = context.get("drama_id") or request_data.get("drama_id") or context.get("project_id")
        # 绑定作品（drama_id）时允许写回（改小传/大纲/剧本），否则只读
        allow_write = bool(context.get("allow_write") or request_data.get("allow_write") or drama_id)
        query = (
            request_data.get("input")
            or request_data.get("query")
            or request_data.get("message")
            or ""
        )

        yield self._event(
            "agent_decision",
            {"mode": "conductor", "message": "总控编排助手分析需求…"},
            metadata={"active_agent": self.agent_name},
        )
        yield self._event("system", "JubenConductor 启动编排 tool loop…")

        from utils.agent_infra.disclosure import prepare_disclosure

        registry = get_agent_tool_registry()
        disclosure = prepare_disclosure(
            registry,
            extra_core=list(self._tool_names),
            include_meta=True,
            include_orchestration=True,
            include_skills_catalog=True,
            include_agents_catalog=True,
            allowed_agent_ids=list(self.allowed_subagents),
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

        tool_ctx = ToolContext(
            user_id=user_id,
            session_id=session_id,
            drama_id=drama_id,
            agent_id=self.agent_name,
            allow_write=allow_write,
            metadata={
                "allowed_subagents": list(self.allowed_subagents),
                "activated_tools": sorted(disclosure.activated),
                "parent_context": {
                    "user_id": user_id,
                    "session_id": session_id,
                    "drama_id": drama_id,
                    "project_id": drama_id,
                },
                "subagent_depth": 0,
            },
        )

        async def on_step(ev: Dict[str, Any]) -> None:
            if ev.get("type") == "tool":
                logger.info("conductor tool: %s", (ev.get("result") or {}).get("tool_name"))

        client = self._ensure_client()
        checkpoint_id = f"{session_id}:{self.agent_name}"
        result = await run_tool_loop(
            client=client,
            messages=messages,
            tools=tools,
            harness=get_tool_harness(),
            tool_ctx=tool_ctx,
            max_steps=self._max_tool_steps,
            checkpoint_store=CheckpointStore(),
            checkpoint_id=checkpoint_id,
            on_step=on_step,
            prompt_cache_extra=assembled.extra_body,
        )

        for th in result.tool_history or []:
            name = th.get("tool_name") or ""
            yield self._event(
                "tool_call",
                name,
                metadata={"parameters": th.get("parameters"), "tool_call_id": th.get("tool_call_id")},
            )
            # 编排相关事件
            if name == "spawn_subagent":
                params = th.get("parameters") or {}
                yield self._event(
                    "subagent_start",
                    {"agent_id": params.get("agent_id"), "task": (params.get("task") or "")[:200]},
                    metadata={"agent_id": params.get("agent_id")},
                )
                yield self._event(
                    "subagent_end",
                    {"agent_id": params.get("agent_id"), "success": th.get("success")},
                    metadata={"agent_id": params.get("agent_id"), "success": th.get("success")},
                )
            elif name == "transfer_to":
                params = th.get("parameters") or {}
                yield self._event(
                    "handoff",
                    {
                        "from_agent": self.agent_name,
                        "to_agent": params.get("agent_id"),
                        "reason": params.get("reason") or "",
                    },
                    metadata={
                        "from_agent": self.agent_name,
                        "to_agent": params.get("agent_id"),
                    },
                )
            elif name == "compose_agents":
                yield self._event(
                    "composition_progress",
                    {"phase": "done", "success": th.get("success")},
                    metadata={"tool": name},
                )
            elif name == "return_to_conductor":
                yield self._event(
                    "handoff",
                    {"from_agent": self.agent_name, "to_agent": self.agent_name, "reason": "return"},
                    metadata={"to_agent": self.agent_name},
                )

            yield self._event(
                "tool_return",
                th.get("llm_text") or th.get("error") or "",
                metadata={"success": th.get("success"), "tool_name": name},
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
                "active_agent": self.agent_name,
            },
        )
