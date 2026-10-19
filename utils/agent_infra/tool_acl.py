"""
工具级 ACL — 结合 RBAC Permission 与 ToolDefinition.dangerous
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Set

from utils.rbac import Permission, Role, RBACChecker


@dataclass
class ToolAccessDecision:
    allowed: bool
    reason: str = ""
    require_confirm: bool = False


DANGEROUS_TOOLS = {"run_shell", "run_python", "write", "edit"}


def roles_from_user(user: Any) -> List[Role]:
    if user is None:
        return [Role.GUEST]
    raw = getattr(user, "roles", None) or (user.get("roles") if isinstance(user, dict) else None) or []
    role_name = getattr(user, "role", None) or (user.get("role") if isinstance(user, dict) else None)
    names = list(raw) if raw else ([role_name] if role_name else ["user"])
    roles: List[Role] = []
    for n in names:
        try:
            roles.append(Role(n) if not isinstance(n, Role) else n)
        except Exception:
            try:
                roles.append(Role(str(n).lower()))
            except Exception:
                continue
    return roles or [Role.USER]


def check_tool_access(
    *,
    tool_name: str,
    dangerous: bool = False,
    user: Any = None,
    allow_write: bool = False,
    confirm_dangerous: bool = False,
) -> ToolAccessDecision:
    roles = roles_from_user(user)
    if not RBACChecker.user_has_permission(roles, Permission.TOOL_EXECUTE):
        # 兼容：有 AGENT_USE 也可执行只读工具
        if not RBACChecker.user_has_permission(roles, Permission.AGENT_USE):
            return ToolAccessDecision(False, "缺少 TOOL_EXECUTE / AGENT_USE 权限")

    is_dangerous = dangerous or tool_name in DANGEROUS_TOOLS
    if is_dangerous:
        if not RBACChecker.user_has_permission(roles, Permission.TOOL_DANGEROUS):
            # admin / developer 有；普通 user 默认无写危险工具
            if not RBACChecker.user_has_permission(roles, Permission.SYSTEM_ADMIN):
                # USER 角色若未授 TOOL_DANGEROUS，拒绝
                has_dev = any(r in (Role.ADMIN, Role.DEVELOPER, Role.OPERATOR) for r in roles)
                if not has_dev:
                    return ToolAccessDecision(False, "危险工具需要 TOOL_DANGEROUS 权限")
        if not allow_write:
            return ToolAccessDecision(False, "危险工具需要 allow_write=true")
        if not confirm_dangerous:
            return ToolAccessDecision(
                False,
                "危险工具需要 confirm_dangerous=true",
                require_confirm=True,
            )
    return ToolAccessDecision(True, "ok")


def filter_tools_for_user(tools: List[Any], user: Any) -> List[Any]:
    """过滤 OpenAI schema 或 ToolDefinition 列表。"""
    roles = roles_from_user(user)
    can_dangerous = RBACChecker.user_has_permission(roles, Permission.TOOL_DANGEROUS) or any(
        r in (Role.ADMIN, Role.DEVELOPER) for r in roles
    )
    out = []
    for t in tools:
        if hasattr(t, "name"):
            name = t.name
            dangerous = bool(getattr(t, "dangerous", False))
        else:
            name = (t.get("function") or {}).get("name") or t.get("name") or ""
            dangerous = name in DANGEROUS_TOOLS
        if dangerous and not can_dangerous:
            continue
        out.append(t)
    return out
