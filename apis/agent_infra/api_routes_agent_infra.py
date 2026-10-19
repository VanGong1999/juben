"""
Agent Infra API — Runtime / Queue / Durable / Eval / Metrics
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent-infra", tags=["Agent Infra"])


class ToolLoopRequest(BaseModel):
    messages: List[Dict[str, Any]]
    tool_names: Optional[List[str]] = None
    max_steps: int = 8
    drama_id: Optional[str] = None
    user_id: str = "default_user"
    allow_write: bool = False
    confirm_dangerous: bool = False
    checkpoint_id: Optional[str] = None
    workload_id: Optional[str] = None
    create_workload: bool = False
    sandbox_profile: str = "drama"
    model_provider: Optional[str] = None
    model: Optional[str] = None
    suspend_on_complete: bool = False


class EnqueueRequest(BaseModel):
    kind: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    priority: int = 20
    max_attempts: int = 3
    idempotency_key: Optional[str] = None


class EvalRunRequest(BaseModel):
    dataset_path: str = "evals/agent_smoke.jsonl"
    suite_id: str = "smoke"


class ReclaimRequest(BaseModel):
    stale_after_seconds: int = 1800


class AutoAdvanceRequest(BaseModel):
    run_id: str
    drama_id: Optional[str] = None
    user_id: Optional[str] = None
    enqueue: bool = True
    max_parallel: int = 2


class ApprovalRequest(BaseModel):
    run_id: str
    step_id: str
    approve: bool = True
    comment: str = ""
    drama_id: Optional[str] = None
    decided_by: Optional[str] = None


class McpConnectRequest(BaseModel):
    command: str
    args: List[str] = Field(default_factory=list)
    register: bool = True
    bridge_name: str = "default"


class ContextPreviewRequest(BaseModel):
    agent_id: str
    drama_id: Optional[str] = None
    session_id: Optional[str] = None
    query: str = ""
    user_id: str = "default_user"
    model: Optional[str] = None
    tool_names: Optional[List[str]] = None


@router.post("/context/preview")
async def context_preview(body: ContextPreviewRequest):
    """只读离线组装「真正发给 LLM 的完整上下文」——不调 LLM、不写 session、不产生费用。"""
    from config.agents import get_agent_config
    from utils.agent_infra.cache_compaction import estimate_chars
    from utils.agent_infra.context_budget import ContextBudget, assemble_budgeted_prompt
    from utils.agent_infra.disclosure import prepare_disclosure
    from utils.agent_infra.prompt_cache import (
        load_prompt_cache_config,
        sort_tools_for_cache,
        strip_internal_fields,
    )
    from utils.agent_runtime import load_agent, normalize_agent_id
    from utils.agent_tools import get_agent_tool_registry
    from utils.drama_context import build_drama_context_block

    aid = normalize_agent_id(body.agent_id)
    cfg = get_agent_config(aid) or {}
    model = body.model or cfg.get("model", "")

    agent = None
    try:
        agent = load_agent(aid)
    except Exception:
        agent = None

    system_prompt = ""
    default_tools = None
    model_provider = ""
    if agent is not None:
        system_prompt = getattr(agent, "system_prompt", "") or ""
        default_tools = getattr(agent, "_tool_names", None)
        model_provider = getattr(agent, "model_provider", "") or ""
    if not system_prompt:
        system_prompt = cfg.get("description", "")

    registry = get_agent_tool_registry()
    extra_core = list(body.tool_names) if body.tool_names else None
    if extra_core is None and default_tools:
        try:
            extra_core = list(default_tools)
        except TypeError:
            extra_core = None

    disclosure = prepare_disclosure(
        registry,
        extra_core=extra_core,
        include_meta=True,
        include_skills_catalog=True,
        include_agents_catalog=(aid == "juben_conductor"),
        allow_write=False,
    )
    tools = sort_tools_for_cache(disclosure.tools)
    if disclosure.prompt_append:
        system_prompt = (system_prompt + "\n\n" + disclosure.prompt_append) if system_prompt else disclosure.prompt_append

    session_id = body.session_id or f"preview-{aid}"
    assembled = await assemble_budgeted_prompt(
        system_prompt=system_prompt,
        user_messages=[{"role": "user", "content": body.query}],
        drama_id=body.drama_id,
        user_id=body.user_id,
        query=body.query,
        session_id=session_id,
        agent_id=aid,
        tools=tools,
        run_hooks=False,
        model=model,
    )

    drama_block = ""
    if body.drama_id:
        try:
            drama_block = await build_drama_context_block(
                body.drama_id, budget_chars=ContextBudget().drama_chars
            )
        except Exception:
            drama_block = ""

    messages = strip_internal_fields(assembled.messages)
    total_chars = estimate_chars(messages)
    stable_prefix = assembled.parts.stable_prefix
    dynamic_suffix = assembled.parts.dynamic_suffix

    cache_cfg = load_prompt_cache_config()
    return {
        "success": True,
        "data": {
            "agent_id": aid,
            "agent_name": cfg.get("display_name") or cfg.get("name") or aid,
            "model": model,
            "model_provider": model_provider,
            "drama_id": body.drama_id,
            "session_id": session_id,
            "query": body.query,
            "stable_prefix": stable_prefix,
            "dynamic_suffix": dynamic_suffix,
            "messages": messages,
            "tools": tools,
            "drama_context_block": drama_block,
            "cache": {
                "prompt_cache_key": assembled.prompt_cache_key,
                "prefix_fingerprint": assembled.prefix_fingerprint,
                "extra_body": assembled.extra_body,
                "config": {
                    "enabled": cache_cfg.enabled,
                    "cache_retention": cache_cfg.cache_retention,
                    "keep_recent_messages": cache_cfg.keep_recent_messages,
                    "compact_threshold_chars": cache_cfg.compact_threshold_chars,
                    "auto_compact": cache_cfg.auto_compact,
                    "pruning_mode": cache_cfg.pruning_mode,
                    "tool_result_max_chars": cache_cfg.tool_result_max_chars,
                },
            },
            "stats": {
                "stable_chars": len(stable_prefix),
                "dynamic_chars": len(dynamic_suffix),
                "total_chars": total_chars,
                "message_count": len(messages),
                "tool_count": len(tools),
            },
        },
    }


@router.get("/capabilities")
async def capabilities():
    """对照 12 项 Agent Infra 能力的当前覆盖情况。"""
    mcp_ok = False
    try:
        import mcp  # noqa: F401

        mcp_ok = True
    except ImportError:
        pass
    otel_ok = False
    try:
        import opentelemetry  # noqa: F401

        otel_ok = True
    except ImportError:
        pass
    return {
        "success": True,
        "data": {
            "1_runtime": {"status": "ok", "api": "POST /agent-infra/runtime/tool-loop", "agent": "MinimalToolAgent"},
            "2_context_checkpoint": {
                "status": "ok",
                "store": "data/agent_checkpoints",
                "budget": "context_budget",
                "prompt_cache": {
                    "boundary": "stable_prefix | dynamic_suffix",
                    "hooks": ["agent_turn_prepare", "before_prompt_build"],
                    "compaction": "cache_preserving + self_compact",
                    "pruning": "cache-ttl",
                },
            },
            "3_queue_workers": {
                "status": "ok",
                "memory": "POST /agent-infra/queue/enqueue",
                "redis": "POST /agent-infra/queue/redis/enqueue",
            },
            "4_orchestration_dag": {
                "status": "ok",
                "auto_advance": "POST /agent-infra/atelier/auto-advance",
                "approval": "POST /agent-infra/atelier/approve",
                "subagent": "spawn_subagent tool + SubagentRunner",
                "handoff": "transfer_to / return_to_conductor + SessionOrchestrationState",
                "swarm": "compose_agents + SwarmRunner",
                "conductor": "juben_conductor (default /chat when agent_id empty|auto)",
                "demo": ["POST /agent-infra/handoff", "POST /agent-infra/spawn"],
            },
            "5_durable": {"status": "ok", "api": "POST /agent-infra/durable/reclaim", "wal": True},
            "6_retry_idempotency": {"status": "ok", "module": "utils.agent_infra.retry"},
            "7_lease": {"status": "ok", "module": "utils.agent_infra.lease", "redis_claim": True},
            "8_sandbox_substrate": {
                "status": "ok",
                "sandbox": ["PathSandbox", "SandboxProfile", "process_sandbox"],
                "substrate": "POST /agent-infra/substrate/workloads + suspend/resume/reclaim",
                "ref": "https://x.com/bibryam/status/2111175619719610728",
            },
            "8b_gateway": {
                "status": "ok",
                "ingress": "auth + input filter + injection flags",
                "egress": "tool/model allowlist + sandbox network + credential attach",
                "api": "GET /agent-infra/gateway/policy",
            },
            "9_mcp": {"status": "ok" if mcp_ok else "optional", "api": "POST /agent-infra/mcp/connect", "installed": mcp_ok},
            "10_security_audit": {"status": "ok", "acl": "tool_acl + egress", "permissions": ["tool:execute", "tool:dangerous"]},
            "11_observability": {
                "status": "ok",
                "api": "GET /agent-infra/metrics",
                "otel": otel_ok,
            },
            "12_eval_replay": {"status": "ok", "api": "POST /agent-infra/eval/run", "ci": "scripts/run_agent_evals.py"},
        },
    }


@router.post("/runtime/tool-loop")
async def run_tool_loop_api(body: ToolLoopRequest):
    """最小可用 Agent Loop（LLM + ToolHarness）。"""
    try:
        from utils.agent_infra.checkpoint import CheckpointStore
        from utils.agent_infra.runtime import run_tool_loop
        from utils.agent_tools import ToolContext, get_agent_tool_registry, get_tool_harness
        from utils.llm_client import get_llm_client

        client = get_llm_client(
            provider=body.model_provider or "zhipu",
            model=body.model,
        )
        registry = get_agent_tool_registry()
        from utils.agent_infra.disclosure import prepare_disclosure

        # Deferred Tool Loading：未显式点名时只用核心 + 名录，避免一次塞 50+ schema
        disclosure = prepare_disclosure(
            registry,
            extra_core=list(body.tool_names) if body.tool_names else None,
            include_meta=True,
            include_skills_catalog=True,
            allow_write=bool(body.allow_write),
        )
        tools = disclosure.tools
        messages = list(body.messages or [])
        if disclosure.prompt_append:
            if messages and messages[0].get("role") == "system":
                messages[0] = {
                    **messages[0],
                    "content": (messages[0].get("content") or "") + "\n\n" + disclosure.prompt_append,
                }
            else:
                messages.insert(0, {"role": "system", "content": disclosure.prompt_append})
        harness = get_tool_harness()
        # Egress：过滤工具 schema（平台规则与 Harness 解耦）
        from utils.agent_infra.gateway import get_egress_gateway

        tools = get_egress_gateway().filter_tools_schema(tools)

        workload_id = body.workload_id
        if body.create_workload and not workload_id:
            from utils.agent_infra.substrate import get_agent_substrate

            snap = await get_agent_substrate().create_workload(
                user_id=body.user_id,
                drama_id=body.drama_id,
                sandbox_profile=body.sandbox_profile,
                messages=messages,
            )
            workload_id = snap.workload_id

        ctx = ToolContext(
            user_id=body.user_id,
            drama_id=body.drama_id,
            allow_write=body.allow_write,
            confirm_dangerous=body.confirm_dangerous,
            sandbox_profile=body.sandbox_profile,
            workload_id=workload_id,
            metadata={"activated_tools": sorted(disclosure.activated)},
        )
        store = CheckpointStore() if (body.checkpoint_id or workload_id) else None
        result = await run_tool_loop(
            client=client,
            messages=messages,
            tools=tools,
            harness=harness,
            tool_ctx=ctx,
            max_steps=body.max_steps,
            checkpoint_store=store,
            checkpoint_id=body.checkpoint_id,
            workload_id=workload_id,
            suspend_on_complete=body.suspend_on_complete,
            model=body.model,
        )
        out = result.to_dict()
        out["workload_id"] = workload_id
        return {"success": True, "data": out}
    except Exception as e:
        logger.exception("tool-loop failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/checkpoints/{checkpoint_id}")
async def get_checkpoint(checkpoint_id: str):
    from utils.agent_infra.checkpoint import CheckpointStore

    cp = await CheckpointStore().load(checkpoint_id)
    if not cp:
        raise HTTPException(status_code=404, detail="checkpoint not found")
    return {"success": True, "data": cp.to_dict()}


# ---------- Gateway / Substrate（Kubernetes Moment 分层） ----------


@router.get("/gateway/policy")
async def gateway_policy():
    from utils.agent_infra.gateway import get_egress_gateway, get_ingress_gateway

    ingress = get_ingress_gateway().policy
    egress = get_egress_gateway().policy
    return {
        "success": True,
        "data": {
            "architecture": {
                "ingress": "auth / authorize / input filter → harness",
                "harness": "plan / agent loop / context / eval / guardrails",
                "egress": "tools / models / credentials / destinations",
                "substrate": "sandbox / checkpoint / suspend-resume / lifecycle",
            },
            "ingress": {
                "max_message_chars": ingress.max_message_chars,
                "max_messages": ingress.max_messages,
                "block_injection": ingress.block_injection,
            },
            "egress": {
                "allow_network_in_sandbox": egress.allow_network_in_sandbox,
                "allowed_egress_hosts": sorted(egress.allowed_egress_hosts),
                "denied_egress_hosts": sorted(egress.denied_egress_hosts),
                "attach_credentials": egress.attach_credentials,
                "allowed_models": sorted(egress.allowed_models) if egress.allowed_models else None,
            },
        },
    }


class WorkloadCreateRequest(BaseModel):
    session_id: Optional[str] = None
    agent_id: Optional[str] = None
    user_id: Optional[str] = None
    drama_id: Optional[str] = None
    sandbox_profile: str = "drama"
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    idle_timeout_s: int = 900
    workload_id: Optional[str] = None


@router.post("/substrate/workloads")
async def create_workload(body: WorkloadCreateRequest):
    from utils.agent_infra.substrate import get_agent_substrate

    snap = await get_agent_substrate().create_workload(
        session_id=body.session_id,
        agent_id=body.agent_id,
        user_id=body.user_id,
        drama_id=body.drama_id,
        sandbox_profile=body.sandbox_profile,
        messages=body.messages,
        idle_timeout_s=body.idle_timeout_s,
        workload_id=body.workload_id,
    )
    return {"success": True, "data": snap.to_dict()}


@router.get("/substrate/workloads/{workload_id}")
async def get_workload(workload_id: str):
    from utils.agent_infra.substrate import get_agent_substrate

    snap = await get_agent_substrate().load(workload_id)
    if not snap:
        raise HTTPException(status_code=404, detail="workload not found")
    return {"success": True, "data": snap.to_dict()}


@router.post("/substrate/workloads/{workload_id}/suspend")
async def suspend_workload(workload_id: str, reason: str = "manual"):
    from utils.agent_infra.substrate import get_agent_substrate

    try:
        snap = await get_agent_substrate().suspend(workload_id, reason=reason)
        return {"success": True, "data": snap.to_dict()}
    except KeyError:
        raise HTTPException(status_code=404, detail="workload not found")


@router.post("/substrate/workloads/{workload_id}/resume")
async def resume_workload(workload_id: str, owner: Optional[str] = None):
    from utils.agent_infra.substrate import get_agent_substrate

    try:
        snap = await get_agent_substrate().resume(workload_id, owner=owner)
        return {"success": True, "data": snap.to_dict()}
    except KeyError:
        raise HTTPException(status_code=404, detail="workload not found")


@router.post("/substrate/reclaim")
async def reclaim_idle_workloads(limit: int = 50):
    from utils.agent_infra.substrate import get_agent_substrate

    data = await get_agent_substrate().reclaim_idle(limit=limit)
    return {"success": True, "data": data, "count": len(data)}


@router.post("/queue/enqueue")
async def enqueue_job(body: EnqueueRequest):
    from utils.agent_infra.queue import JobPriority, get_task_queue, get_worker_pool

    q = get_task_queue()
    pool = await get_worker_pool()

    async def _echo_handler(job):
        return {"echo": job.payload, "kind": job.kind}

    if "echo" not in pool.handlers:
        pool.register("echo", _echo_handler)
        pool.set_default(_echo_handler)

    try:
        priority = JobPriority(body.priority) if body.priority in (0, 10, 20, 30) else JobPriority.NORMAL
        job = await q.enqueue(
            body.kind,
            body.payload,
            priority=priority,
            max_attempts=body.max_attempts,
            idempotency_key=body.idempotency_key,
        )
        return {"success": True, "data": job.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=429 if "full" in str(e).lower() else 500, detail=str(e)) from e


@router.get("/queue/stats")
async def queue_stats():
    from utils.agent_infra.queue import get_task_queue

    return {"success": True, "data": get_task_queue().stats()}


@router.get("/queue/jobs")
async def queue_jobs(limit: int = 50):
    from utils.agent_infra.queue import get_task_queue

    return {"success": True, "data": get_task_queue().list_jobs(limit=limit)}


@router.post("/durable/reclaim")
async def durable_reclaim(body: ReclaimRequest = ReclaimRequest()):
    from utils.agent_infra.durable import reclaim_stale_runs

    items = await reclaim_stale_runs(stale_after_seconds=body.stale_after_seconds)
    return {"success": True, "data": {"reclaimed": items, "count": len(items)}}


@router.get("/metrics")
async def agent_metrics():
    from utils.agent_infra.observability import get_agent_metrics

    return {"success": True, "data": get_agent_metrics().snapshot()}


@router.post("/eval/run")
async def eval_run(body: EvalRunRequest):
    """跑 JSONL 评测集。默认 smoke：不调 LLM，用 rule checks 验证 harness 就绪。"""
    from utils.agent_infra.eval_runner import EvalRunner

    async def smoke_agent(inp: Dict[str, Any]) -> Dict[str, Any]:
        # 轻量 smoke：检查工具注册与可选 echo
        from utils.agent_tools import get_agent_tool_registry

        registry = get_agent_tool_registry()
        names = [t.name for t in registry.list()]
        content = inp.get("echo") or inp.get("query") or ""
        return {
            "content": content,
            "tool_names": names,
            "score": 100 if "read" in names and "date" in names else 0,
            "tool_history": [{"tool_name": "date"}] if "date" in names else [],
        }

    runner = EvalRunner(agent_fn=smoke_agent)
    cases = await EvalRunner.load_dataset(body.dataset_path)
    report = await runner.run_suite(cases, suite_id=body.suite_id)
    return {"success": True, "data": report.to_dict()}


@router.get("/orchestration/demo-dag")
async def demo_dag():
    """演示 Atelier 步骤转 DAG 就绪集。"""
    from utils.agent_infra.orchestration import DAGScheduler
    from utils.atelier_pipeline import STEP_CATALOG

    steps = [
        {
            "id": f"step_{i+1}_{s['module']}",
            "agent_id": s["agent_id"],
            "title": s["title"],
            "enabled": True,
            "depends_on": list(s.get("depends_on") or []),
            "is_reviewer": s.get("is_reviewer"),
        }
        for i, s in enumerate(STEP_CATALOG)
    ]
    # 把 module 依赖转成 step id
    mod_to_id = {s["module"]: f"step_{i+1}_{s['module']}" for i, s in enumerate(STEP_CATALOG)}
    for st in steps:
        st["depends_on"] = [mod_to_id[m] for m in st["depends_on"] if m in mod_to_id]

    sched = DAGScheduler.from_linear_steps(steps)
    # from_linear_steps 会覆盖 depends_on；改用手动 plan
    from utils.agent_infra.orchestration import OrchestrationNode, OrchestrationPlan

    nodes = []
    for st in steps:
        nodes.append(
            OrchestrationNode(
                node_id=st["id"],
                agent_id=st["agent_id"],
                title=st["title"],
                depends_on=st["depends_on"],
                is_reviewer=bool(st.get("is_reviewer")),
            )
        )
    plan = OrchestrationPlan(plan_id="demo_atelier", nodes=nodes)
    sched = DAGScheduler(plan)
    errors = sched.validate()
    ready = [n.to_dict() for n in sched.ready_nodes()]
    return {
        "success": True,
        "data": {
            "errors": errors,
            "ready": ready,
            "plan": plan.to_dict(),
        },
    }


@router.post("/queue/redis/enqueue")
async def redis_enqueue(body: EnqueueRequest):
    from utils.agent_infra.queue import JobPriority
    from utils.agent_infra.redis_queue import get_redis_task_queue, get_redis_worker_pool

    try:
        await get_redis_worker_pool()
        q = await get_redis_task_queue()
        priority = JobPriority(body.priority) if body.priority in (0, 10, 20, 30) else JobPriority.NORMAL
        job = await q.enqueue(
            body.kind,
            body.payload,
            priority=priority,
            max_attempts=body.max_attempts,
            idempotency_key=body.idempotency_key,
        )
        return {"success": True, "data": job.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.get("/queue/redis/stats")
async def redis_queue_stats():
    from utils.agent_infra.redis_queue import get_redis_task_queue

    q = await get_redis_task_queue()
    return {"success": True, "data": await q.stats()}


@router.post("/atelier/auto-advance")
async def atelier_auto_advance(body: AutoAdvanceRequest):
    from utils.atelier_pipeline import auto_advance

    try:
        data = await auto_advance(
            body.run_id,
            drama_id=body.drama_id,
            user_id=body.user_id,
            enqueue=body.enqueue,
            max_parallel=body.max_parallel,
        )
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/atelier/{run_id}/ready")
async def atelier_ready(run_id: str, drama_id: Optional[str] = None):
    from utils.atelier_pipeline import list_ready_steps

    return {"success": True, "data": await list_ready_steps(run_id, drama_id=drama_id)}


@router.post("/atelier/approve")
async def atelier_approve(body: ApprovalRequest):
    from utils.atelier_pipeline import decide_step_approval

    try:
        run = await decide_step_approval(
            body.run_id,
            body.step_id,
            approve=body.approve,
            comment=body.comment,
            drama_id=body.drama_id,
            decided_by=body.decided_by,
        )
        return {"success": True, "data": run}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/durable/{run_id}/events")
async def durable_events(run_id: str):
    from utils.agent_infra.durable import DurableRunStore

    events = await DurableRunStore().load_events(run_id)
    return {"success": True, "data": events, "total": len(events)}


@router.post("/mcp/connect")
async def mcp_connect(body: McpConnectRequest):
    from utils.agent_infra.mcp_bridge import get_mcp_bridge

    bridge = await get_mcp_bridge(body.bridge_name)
    ok = await bridge.connect_stdio(body.command, body.args)
    if not ok:
        raise HTTPException(status_code=503, detail="MCP connect failed (install mcp? check command)")
    registered = []
    if body.register:
        from utils.agent_tools import get_agent_tool_registry

        registry = get_agent_tool_registry()
        for t in bridge.as_tool_definitions():
            registry.register(t)
            registered.append(t.name)
    return {
        "success": True,
        "data": {
            "connected": bridge.connected,
            "tools": [m.get("name") for m in bridge._tools_meta],
            "registered": registered,
        },
    }


class HandoffRequest(BaseModel):
    session_id: str = "default"
    from_agent: str = "juben_conductor"
    to_agent: str
    reason: str = ""
    context_keys: List[str] = Field(default_factory=list)


class SpawnRequest(BaseModel):
    agent_id: str
    task: str
    user_id: str = "default_user"
    session_id: str = "default"
    drama_id: Optional[str] = None
    timeout: float = 60


@router.post("/handoff")
async def handoff_demo(body: HandoffRequest):
    """会话级交接演示：更新 active_agent，供下一轮 /chat 路由。"""
    from utils.agent_infra.handoffs import apply_handoff, resolve_turn_agent
    from utils.agent_infra.orchestration import HandoffSpec

    state = apply_handoff(
        body.session_id,
        HandoffSpec(
            from_agent=body.from_agent,
            to_agent=body.to_agent,
            reason=body.reason,
            context_keys=list(body.context_keys or []),
        ),
    )
    resolved = resolve_turn_agent(agent_id="auto", session_id=body.session_id)
    return {"success": True, "data": {"session": state.to_dict(), "resolved": resolved}}


@router.post("/spawn")
async def spawn_demo(body: SpawnRequest):
    """子专家 spawn 演示（同步聚合结果，供联调）。"""
    from utils.agent_infra.subagents import SubagentRunner, SubagentSpec

    result = await SubagentRunner().spawn(
        SubagentSpec(agent_id=body.agent_id, task=body.task, timeout=body.timeout),
        parent_agent_id="agent_infra_demo",
        context={
            "user_id": body.user_id,
            "session_id": body.session_id,
            "drama_id": body.drama_id,
        },
    )
    return {"success": result.success, "data": result.to_dict()}


@router.get("/secrets/check")
async def secrets_check():
    """Secrets 体检：只报告是否配置，不回显密钥内容。"""
    import os

    keys = [
        "JWT_SECRET_KEY",
        "ZHIPU_API_KEY",
        "DASHSCOPE_API_KEY",
        "OPENAI_API_KEY",
        "OPENROUTER_API_KEY",
        "REDIS_URL",
    ]
    report = {}
    for k in keys:
        v = os.getenv(k)
        report[k] = {"configured": bool(v), "length": len(v) if v else 0}
    return {"success": True, "data": report}
