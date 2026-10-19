"""
Agent Infra — 运行时 / 队列 / 编排 / 持久执行 / 可观测 / 评测 / MCP / ACL
"""

from .runtime import AgentLoopResult, run_tool_loop
from .checkpoint import AgentCheckpoint, CheckpointStore
from .queue import Job, JobPriority, TaskQueue, WorkerPool, get_task_queue, get_worker_pool
from .orchestration import (
    ApprovalGate,
    DAGScheduler,
    HandoffSpec,
    OrchestrationNode,
    OrchestrationPlan,
)
from .subagents import (
    SubagentResult,
    SubagentRunner,
    SubagentSpec,
    normalize_agent_id,
)
from .handoffs import (
    CONDUCTOR_AGENT_ID,
    SessionOrchestrationState,
    SessionOrchestrationStore,
    apply_handoff,
    get_session_orchestration_store,
    resolve_turn_agent,
    return_to_conductor,
)
from .swarm import CompositionPlan, CompositionResult, SwarmRunner
from .team import AgentTeam, DEFAULT_LEAD_AGENT_ID, TeamDefinition, TeamResult, TeamTask
from .durable import DurableRunStore, reclaim_stale_runs
from .retry import IdempotencyStore, RetryPolicy, with_retry_timeout
from .lease import JobLease, LeaseManager
from .observability import AgentMetrics, get_agent_metrics, traced
from .eval_runner import EvalCase, EvalReport, EvalRunner
from .mcp_bridge import McpToolBridge, get_mcp_bridge
from .context_budget import ContextBudget, assemble_budgeted_messages, assemble_prompt_bundle
from .prompt_cache import (
    CACHE_BOUNDARY_MARKER,
    AssembledPrompt,
    CacheSessionState,
    PromptCacheConfig,
    SystemPromptParts,
    assemble_system_parts,
    get_cache_session,
    load_prompt_cache_config,
    normalize_cache_usage,
    sort_tools_for_cache,
)
from .prompt_hooks import PromptHookRegistry, get_prompt_hooks, run_prompt_pipeline
from .cache_compaction import CompactionResult, compact_messages, prune_tool_results
from .tool_acl import check_tool_access, filter_tools_for_user
from .otel import otel_span, configure_otel_from_env
from .gateway import (
    EgressGateway,
    EgressPolicy,
    GatewayDecision,
    IngressGateway,
    IngressPolicy,
    get_egress_gateway,
    get_ingress_gateway,
)
from .substrate import AgentSubstrate, WorkloadSnapshot, get_agent_substrate
from .disclosure import (
    DisclosureBundle,
    META_TOOLS,
    DEFAULT_CORE_TOOLS,
    activate_tools_from_result,
    prepare_disclosure,
    build_skills_catalog,
    build_agents_catalog,
    build_tools_catalog,
)

__all__ = [
    "AgentLoopResult",
    "run_tool_loop",
    "AgentCheckpoint",
    "CheckpointStore",
    "Job",
    "JobPriority",
    "TaskQueue",
    "WorkerPool",
    "get_task_queue",
    "get_worker_pool",
    "ApprovalGate",
    "DAGScheduler",
    "HandoffSpec",
    "OrchestrationNode",
    "OrchestrationPlan",
    "SubagentResult",
    "SubagentRunner",
    "SubagentSpec",
    "normalize_agent_id",
    "CONDUCTOR_AGENT_ID",
    "SessionOrchestrationState",
    "SessionOrchestrationStore",
    "apply_handoff",
    "get_session_orchestration_store",
    "resolve_turn_agent",
    "return_to_conductor",
    "CompositionPlan",
    "CompositionResult",
    "SwarmRunner",
    "AgentTeam",
    "DEFAULT_LEAD_AGENT_ID",
    "TeamDefinition",
    "TeamResult",
    "TeamTask",
    "DurableRunStore",
    "reclaim_stale_runs",
    "IdempotencyStore",
    "RetryPolicy",
    "with_retry_timeout",
    "JobLease",
    "LeaseManager",
    "AgentMetrics",
    "get_agent_metrics",
    "traced",
    "EvalCase",
    "EvalReport",
    "EvalRunner",
    "McpToolBridge",
    "get_mcp_bridge",
    "ContextBudget",
    "assemble_budgeted_messages",
    "assemble_prompt_bundle",
    "CACHE_BOUNDARY_MARKER",
    "AssembledPrompt",
    "CacheSessionState",
    "PromptCacheConfig",
    "SystemPromptParts",
    "assemble_system_parts",
    "get_cache_session",
    "load_prompt_cache_config",
    "normalize_cache_usage",
    "sort_tools_for_cache",
    "PromptHookRegistry",
    "get_prompt_hooks",
    "run_prompt_pipeline",
    "CompactionResult",
    "compact_messages",
    "prune_tool_results",
    "check_tool_access",
    "filter_tools_for_user",
    "otel_span",
    "configure_otel_from_env",
    "EgressGateway",
    "EgressPolicy",
    "GatewayDecision",
    "IngressGateway",
    "IngressPolicy",
    "get_egress_gateway",
    "get_ingress_gateway",
    "AgentSubstrate",
    "WorkloadSnapshot",
    "get_agent_substrate",
    "DisclosureBundle",
    "META_TOOLS",
    "DEFAULT_CORE_TOOLS",
    "activate_tools_from_result",
    "prepare_disclosure",
    "build_skills_catalog",
    "build_agents_catalog",
    "build_tools_catalog",
]
