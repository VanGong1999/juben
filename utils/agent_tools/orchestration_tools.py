"""
多智能体编排工具：spawn_subagent / transfer_to / compose_agents / return_to_conductor
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Set

from .types import ToolCategory, ToolContext, ToolDefinition, ToolResult, ToolUpdateCallback


def _allowed_from_ctx(ctx: ToolContext) -> Optional[Set[str]]:
    raw = (ctx.metadata or {}).get("allowed_subagents")
    if raw is None:
        return None
    if isinstance(raw, (list, set, tuple)):
        return set(str(x) for x in raw)
    return None


def _tool_spawn_subagent() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        from utils.agent_infra.subagents import SubagentRunner, SubagentSpec

        ctx = ctx or ToolContext()
        agent_id = str(params.get("agent_id") or "").strip()
        task = str(params.get("task") or "").strip()
        if not agent_id or not task:
            return ToolResult.fail("agent_id 与 task 均为必填")

        keys = params.get("context_keys")
        if isinstance(keys, str):
            keys = [k.strip() for k in keys.split(",") if k.strip()]
        context_keys = list(keys or [])

        timeout = float(params.get("timeout") or 120)
        parent = ctx.agent_id or "unknown"
        context = {
            "user_id": ctx.user_id,
            "session_id": ctx.session_id,
            "drama_id": ctx.drama_id,
            "project_id": ctx.drama_id,
            **dict(ctx.metadata.get("parent_context") or {}),
        }
        depth = int(ctx.metadata.get("subagent_depth") or 0)

        if on_update:
            await on_update({"status": "running", "agent_id": agent_id, "phase": "subagent_start"})

        runner = SubagentRunner()
        result = await runner.spawn(
            SubagentSpec(
                agent_id=agent_id,
                task=task,
                context_keys=context_keys,
                timeout=timeout,
            ),
            parent_agent_id=parent,
            context=context,
            depth=depth,
            allowed_subagents=_allowed_from_ctx(ctx),
        )

        if on_update:
            await on_update(
                {
                    "status": "done" if result.success else "error",
                    "agent_id": agent_id,
                    "phase": "subagent_end",
                    "success": result.success,
                }
            )

        text = result.to_llm_text()
        if result.success:
            return ToolResult.text(text, details=result.to_dict())
        return ToolResult.fail(result.error or "subagent failed", details=result.to_dict())

    return ToolDefinition(
        name="spawn_subagent",
        label="调用子专家",
        description=(
            "将一个有界子任务交给专业 Agent 执行，结果返回给你继续合成回复。"
            "父 Agent 仍对用户负责。适用于策划后请创作/评估等专家帮忙，而不移交整段对话。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": (
                        "专家 id，如 short_drama_planner / short_drama_creator / "
                        "short_drama_evaluation / story_five_elements / character_profile_generator"
                    ),
                },
                "task": {"type": "string", "description": "交给子专家的具体任务描述"},
                "context_keys": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "可选：从会话上下文透传的键名",
                },
                "timeout": {"type": "number", "description": "超时秒数", "default": 120},
            },
            "required": ["agent_id", "task"],
        },
        execute=execute,
        category=ToolCategory.PREBUILT,
        tags=["orchestration", "subagent"],
    )


def _tool_transfer_to() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        from utils.agent_infra.handoffs import apply_handoff, make_handoff_event
        from utils.agent_infra.orchestration import HandoffSpec
        from utils.agent_infra.subagents import normalize_agent_id

        ctx = ctx or ToolContext()
        to_agent = normalize_agent_id(str(params.get("agent_id") or "").strip())
        reason = str(params.get("reason") or "specialist takeover").strip()
        if not to_agent:
            return ToolResult.fail("agent_id 必填")

        keys = params.get("context_keys")
        if isinstance(keys, str):
            keys = [k.strip() for k in keys.split(",") if k.strip()]

        spec = HandoffSpec(
            from_agent=ctx.agent_id or "unknown",
            to_agent=to_agent,
            reason=reason,
            context_keys=list(keys or []),
            payload_ref=str(params.get("payload_ref") or ""),
        )
        state = apply_handoff(ctx.session_id or "default", spec)

        if on_update:
            await on_update(make_handoff_event(spec, agent_source=ctx.agent_id or ""))

        msg = (
            f"已交接给 {to_agent}。下一轮用户消息将由该专家直接回复。"
            f" reason={reason}"
        )
        return ToolResult.text(
            msg,
            details={"handoff": spec.to_dict(), "session": state.to_dict()},
        )

    return ToolDefinition(
        name="transfer_to",
        label="交接对话",
        description=(
            "将本会话的对话所有权移交给指定专家；之后用户消息由该专家直接回答。"
            "仅在用户需要与某专家持续深入协作时使用；有界子任务请用 spawn_subagent。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "目标专家 id"},
                "reason": {"type": "string", "description": "交接原因（简短）"},
                "context_keys": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "建议透传的上下文键",
                },
                "payload_ref": {"type": "string", "description": "可选 artifact/checkpoint 引用"},
            },
            "required": ["agent_id"],
        },
        execute=execute,
        category=ToolCategory.PREBUILT,
        tags=["orchestration", "handoff"],
    )


def _tool_compose_agents() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        from utils.agent_infra.swarm import CompositionPlan, SwarmRunner, make_composition_event

        ctx = ctx or ToolContext()
        plan_raw = params.get("plan") or params
        if isinstance(plan_raw, str):
            try:
                plan_raw = json.loads(plan_raw)
            except json.JSONDecodeError:
                return ToolResult.fail("plan 不是合法 JSON")

        # 允许简化：agents + task + mode
        if isinstance(plan_raw, dict) and "nodes" not in plan_raw and params.get("agents"):
            agents = params.get("agents") or []
            plan_raw = {
                "mode": params.get("mode") or "parallel",
                "shared_task": params.get("task") or "",
                "nodes": [{"agent_id": a} for a in agents],
            }

        plan = CompositionPlan.from_dict(plan_raw if isinstance(plan_raw, dict) else {})
        if params.get("task") and not plan.shared_task:
            plan.shared_task = str(params["task"])
            for n in plan.nodes:
                if not n.task:
                    n.task = plan.shared_task

        if on_update:
            await on_update(
                make_composition_event(
                    "composition_progress",
                    {"phase": "start", "plan": plan.to_dict()},
                    agent_source=ctx.agent_id or "",
                )
            )

        context = {
            "user_id": ctx.user_id,
            "session_id": ctx.session_id,
            "drama_id": ctx.drama_id,
            "project_id": ctx.drama_id,
            **dict(ctx.metadata.get("parent_context") or {}),
        }
        depth = int(ctx.metadata.get("subagent_depth") or 0)
        result = await SwarmRunner().run(
            plan,
            parent_agent_id=ctx.agent_id or "unknown",
            context=context,
            allowed_subagents=_allowed_from_ctx(ctx),
            depth=depth,
        )

        if on_update:
            await on_update(
                make_composition_event(
                    "composition_progress",
                    {"phase": "end", "result": result.to_dict()},
                    agent_source=ctx.agent_id or "",
                )
            )

        text = result.to_llm_text()
        if result.success:
            return ToolResult.text(text, details=result.to_dict())
        return ToolResult.fail(result.error or "composition failed", details=result.to_dict())

    return ToolDefinition(
        name="compose_agents",
        label="组合多个专家",
        description=(
            "并行或按流水线组合调用多个专家，汇总结果后由你回复用户。"
            "适合「同时要策划要点和人物小传」这类可拆分任务。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "共享任务描述"},
                "mode": {
                    "type": "string",
                    "enum": ["parallel", "pipeline", "dag"],
                    "description": "parallel=并行, pipeline=顺序, dag=按 depends_on",
                    "default": "parallel",
                },
                "agents": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "简化写法：专家 id 列表（配合 task/mode）",
                },
                "plan": {
                    "type": "object",
                    "description": "完整计划 {mode, shared_task, nodes:[{node_id,agent_id,task,depends_on}]}",
                },
            },
            "required": [],
        },
        execute=execute,
        category=ToolCategory.PREBUILT,
        tags=["orchestration", "swarm"],
    )


def _tool_return_to_conductor() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        from utils.agent_infra.handoffs import CONDUCTOR_AGENT_ID, make_handoff_event, return_to_conductor
        from utils.agent_infra.orchestration import HandoffSpec

        ctx = ctx or ToolContext()
        reason = str(params.get("reason") or "return to conductor").strip()
        state = return_to_conductor(
            ctx.session_id or "default",
            reason=reason,
            from_agent=ctx.agent_id,
        )
        spec = HandoffSpec(
            from_agent=ctx.agent_id or "unknown",
            to_agent=CONDUCTOR_AGENT_ID,
            reason=reason,
        )
        if on_update:
            await on_update(make_handoff_event(spec, agent_source=ctx.agent_id or ""))
        return ToolResult.text(
            f"已交回总控（{CONDUCTOR_AGENT_ID}）。下一轮由编排助手接管。",
            details={"session": state.to_dict()},
        )

    return ToolDefinition(
        name="return_to_conductor",
        label="交回总控",
        description="将对话所有权交回编排助手（Conductor），用于结束与当前专家的持续协作。",
        parameters={
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "交回原因"},
            },
            "required": [],
        },
        execute=execute,
        category=ToolCategory.PREBUILT,
        tags=["orchestration", "handoff"],
    )


def get_orchestration_tools() -> List[ToolDefinition]:
    return [
        _tool_spawn_subagent(),
        _tool_transfer_to(),
        _tool_compose_agents(),
        _tool_return_to_conductor(),
    ]
