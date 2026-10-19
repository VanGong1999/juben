"""
工具注册表 + Harness 执行器
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .types import (
    ToolCategory,
    ToolContext,
    ToolDefinition,
    ToolResult,
    ToolUpdateCallback,
    new_tool_call_id,
)

logger = logging.getLogger(__name__)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        if not tool.name:
            raise ValueError("tool.name required")
        self._tools[tool.name] = tool
        logger.info("[agent_tools] registered %s (%s)", tool.name, tool.category.value)

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list(
        self,
        *,
        category: Optional[ToolCategory] = None,
        enabled_only: bool = True,
    ) -> List[ToolDefinition]:
        items = list(self._tools.values())
        if enabled_only:
            items = [t for t in items if t.enabled]
        if category:
            items = [t for t in items if t.category == category]
        return sorted(items, key=lambda t: (t.category.value, t.name))

    def openai_tools(
        self,
        *,
        names: Optional[List[str]] = None,
        category: Optional[ToolCategory] = None,
    ) -> List[Dict[str, Any]]:
        tools = self.list(category=category)
        if names:
            allow = set(names)
            tools = [t for t in tools if t.name in allow]
        return [t.openai_schema() for t in tools]

    def ui_catalog(self) -> List[Dict[str, Any]]:
        return [t.ui_schema() for t in self.list(enabled_only=False)]


class ToolHarness:
    """
    Harness 工具执行入口：编排执行与审计。

    访问策略（谁能调什么、外网/凭据）走 EgressGateway，不把平台规则写死在业务 Agent。
    对齐: Harness 聚焦模型与工具成效；Gateway 管进出。
    """

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry
        self.history: List[Dict[str, Any]] = []

    async def execute(
        self,
        tool_name: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        tool_call_id: Optional[str] = None,
        ctx: Optional[ToolContext] = None,
        on_update: Optional[ToolUpdateCallback] = None,
        skip_egress: bool = False,
    ) -> Dict[str, Any]:
        from .bootstrap import resolve_tool_name

        call_id = tool_call_id or new_tool_call_id()
        params = params or {}
        ctx = ctx or ToolContext()
        tool_name = resolve_tool_name(tool_name)
        tool = self.registry.get(tool_name)
        started = datetime.now().isoformat()

        if not tool:
            result = ToolResult.fail(f"工具不存在: {tool_name}")
            return self._pack(call_id, tool_name, params, result, started)

        if not tool.enabled:
            result = ToolResult.fail(f"工具已禁用: {tool_name}")
            return self._pack(call_id, tool_name, params, result, started)

        try:
            ctx.check_aborted()

            # Egress：工具 ACL / 白名单（改 Harness 不必重建这些规则）
            if not skip_egress:
                try:
                    from utils.agent_infra.gateway import get_egress_gateway

                    eg = get_egress_gateway()
                    decision = eg.check_tool(
                        tool_name,
                        dangerous=bool(getattr(tool, "dangerous", False)),
                        user=getattr(ctx, "user", None),
                        allow_write=bool(getattr(ctx, "allow_write", False)),
                        confirm_dangerous=bool(getattr(ctx, "confirm_dangerous", False)),
                    )
                    if not decision.allowed:
                        result = ToolResult.fail(decision.reason)
                        packed = self._pack(call_id, tool_name, params, result, started)
                        packed["egress_denied"] = True
                        self.history.append(packed)
                        return packed
                    # shell 网络预检
                    if tool_name == "run_shell" and params.get("command"):
                        shell_dec = eg.check_shell_command(str(params.get("command") or ""))
                        if not shell_dec.allowed:
                            result = ToolResult.fail(shell_dec.reason)
                            return self._pack(call_id, tool_name, params, result, started)
                except Exception as e:
                    logger.exception("egress check failed (fail-closed)")
                    result = ToolResult.fail(f"egress 策略检查失败: {e}")
                    packed = self._pack(call_id, tool_name, params, result, started)
                    packed["egress_denied"] = True
                    self.history.append(packed)
                    return packed

            # 轻量 required 校验
            required = (tool.parameters or {}).get("required") or []
            missing = [k for k in required if k not in params or params[k] is None]
            if missing:
                result = ToolResult.fail(f"缺少参数: {', '.join(missing)}")
                return self._pack(call_id, tool_name, params, result, started)

            result = await tool.execute(call_id, params, ctx, on_update)
            if not isinstance(result, ToolResult):
                result = ToolResult.text(str(result), details={"raw": True})
        except InterruptedError as e:
            result = ToolResult.fail(str(e) or "aborted")
        except PermissionError as e:
            result = ToolResult.fail(f"权限拒绝: {e}")
        except Exception as e:
            logger.exception("[agent_tools] execute failed: %s", tool_name)
            result = ToolResult.fail(str(e))

        packed = self._pack(call_id, tool_name, params, result, started)
        self.history.append(packed)
        if len(self.history) > 200:
            self.history = self.history[-200:]

        # Agent Infra：metrics + 审计（失败不影响主路径）
        try:
            from utils.agent_infra.observability import get_agent_metrics

            metrics = get_agent_metrics()
            metrics.inc(
                "tool_calls_total",
                labels={"tool": tool_name, "success": str(bool(result.ok)).lower()},
            )
            started_ts = packed.get("started_at")
            finished_ts = packed.get("finished_at")
            if started_ts and finished_ts:
                try:
                    dt0 = datetime.fromisoformat(started_ts)
                    dt1 = datetime.fromisoformat(finished_ts)
                    metrics.record_latency(
                        "agent_loop_tool",
                        (dt1 - dt0).total_seconds(),
                        labels={"tool": tool_name},
                    )
                except Exception:
                    pass
        except Exception:
            pass

        try:
            if tool and getattr(tool, "dangerous", False):
                from utils.audit_service import AuditEventType, AuditLevel, get_audit_logger

                audit = get_audit_logger()
                audit.log(
                    event_type=AuditEventType.UPDATE,
                    user_id=getattr(ctx, "user_id", None),
                    session_id=getattr(ctx, "session_id", None),
                    action=f"tool:{tool_name}",
                    resource_type="tool",
                    resource_id=tool_name,
                    details={
                        "tool": tool_name,
                        "drama_id": getattr(ctx, "drama_id", None),
                        "agent_id": getattr(ctx, "agent_id", None),
                        "tool_call_id": call_id,
                    },
                    success=bool(result.ok),
                    error_message=result.error,
                    level=AuditLevel.WARNING if not result.ok else AuditLevel.INFO,
                )
        except Exception:
            logger.debug("tool audit skipped", exc_info=True)

        return packed

    def _pack(
        self,
        call_id: str,
        tool_name: str,
        params: Dict[str, Any],
        result: ToolResult,
        started: str,
    ) -> Dict[str, Any]:
        return {
            "tool_call_id": call_id,
            "tool_name": tool_name,
            "parameters": params,
            "success": result.ok,
            "error": result.error,
            "result": result.to_dict(),
            "llm_text": result.to_llm_text(),
            "started_at": started,
            "finished_at": datetime.now().isoformat(),
        }

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self.history[-limit:]


_registry: Optional[ToolRegistry] = None
_harness: Optional[ToolHarness] = None


def get_agent_tool_registry() -> ToolRegistry:
    global _registry, _harness
    if _registry is None:
        from .bootstrap import register_all_tools

        _registry = ToolRegistry()
        register_all_tools(_registry)
        _harness = ToolHarness(_registry)
    return _registry


def get_tool_harness() -> ToolHarness:
    get_agent_tool_registry()
    assert _harness is not None
    return _harness
