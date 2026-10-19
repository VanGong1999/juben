"""
Agent Gateway — Ingress / Egress（对齐「AI Agents Are Having Their Kubernetes Moment」）

职责分层:
  Ingress  — 谁能进来、带什么指令/数据进 Harness（鉴权、授权、输入过滤、策略）
  Egress   — Harness 能调用哪些模型/工具、凭据挂载、数据能发往何处
  Harness  — 规划、agent loop、上下文、评估、护栏（不持有平台凭据策略）
  Substrate— 沙箱、持久化、checkpoint、suspend/resume（见 substrate.py）

换 Harness 不应重建访问规则；规则住在 Gateway。
参考: https://x.com/bibryam/status/2111175619719610728
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# ---------- 策略配置（可被 env / 调用方覆盖） ----------

DEFAULT_MODEL_ALLOWLIST = frozenset(
    {
        "glm-4-flash",
        "glm-4.7-flash",
        "glm-4.1v-thinking-flash",
        "gpt-4o-mini",
        "gpt-4o",
        "claude-3-5-sonnet",
        "claude-sonnet-4",
    }
)

# 默认禁止沙箱进程访问的外网目的地（egress host 黑名单关键词）
DEFAULT_EGRESS_HOST_DENY = frozenset(
    {
        "metadata.google.internal",
        "169.254.169.254",  # cloud metadata
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
    }
)

# 敏感 env 键：不得透传进进程沙箱（凭据由 egress 侧按需注入）
SENSITIVE_ENV_KEYS = frozenset(
    {
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "ZHIPUAI_API_KEY",
        "ZHIPU_API_KEY",
        "DASHSCOPE_API_KEY",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_ACCESS_KEY_ID",
        "GITHUB_TOKEN",
        "DATABASE_URL",
        "REDIS_URL",
        "SECRET_KEY",
        "JWT_SECRET",
    }
)

_URL_IN_SHELL = re.compile(
    r"(https?://[^\s'\"|;&]+)|(\bcurl\b|\bwget\b|\bnc\b|\bncat\b|\bsocat\b)",
    re.I,
)


@dataclass
class GatewayDecision:
    allowed: bool
    reason: str = "ok"
    require_confirm: bool = False
    filtered_payload: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "require_confirm": self.require_confirm,
            "metadata": self.metadata,
        }


@dataclass
class EgressPolicy:
    """出站策略 — 与 Harness 解耦，改 Harness 不必重建。"""

    allowed_tools: Optional[Set[str]] = None  # None = 不限制名，仍过 ACL
    denied_tools: Set[str] = field(default_factory=set)
    allowed_models: Optional[Set[str]] = None
    allow_network_in_sandbox: bool = False
    allowed_egress_hosts: Set[str] = field(default_factory=set)
    denied_egress_hosts: Set[str] = field(default_factory=lambda: set(DEFAULT_EGRESS_HOST_DENY))
    max_tool_result_chars: int = 8000
    attach_credentials: bool = False  # True 时才允许注入白名单凭据键

    @classmethod
    def from_env(cls) -> "EgressPolicy":
        allow_net = os.getenv("AGENT_EGRESS_ALLOW_NETWORK", "").lower() in ("1", "true", "yes")
        hosts = {
            h.strip()
            for h in (os.getenv("AGENT_EGRESS_ALLOWED_HOSTS") or "").split(",")
            if h.strip()
        }
        models_raw = os.getenv("AGENT_EGRESS_ALLOWED_MODELS") or ""
        models = {m.strip() for m in models_raw.split(",") if m.strip()} or None
        return cls(
            allow_network_in_sandbox=allow_net,
            allowed_egress_hosts=hosts,
            allowed_models=models,
        )


@dataclass
class IngressPolicy:
    """入站策略。"""

    max_message_chars: int = 100_000
    max_messages: int = 200
    block_injection: bool = True  # 对 *用户输入* 标记，不硬拒（避免误杀创作）；对 system 硬拒
    require_user_id: bool = True
    allowed_agent_ids: Optional[Set[str]] = None

    @classmethod
    def from_env(cls) -> "IngressPolicy":
        return cls(
            max_message_chars=int(os.getenv("AGENT_INGRESS_MAX_CHARS") or 100_000),
            block_injection=os.getenv("AGENT_INGRESS_BLOCK_INJECTION", "true").lower()
            not in ("0", "false", "no"),
        )


class IngressGateway:
    """进入 Harness 之前：鉴权上下文、输入过滤、策略检查。"""

    def __init__(self, policy: Optional[IngressPolicy] = None):
        self.policy = policy or IngressPolicy.from_env()

    def authorize_request(
        self,
        *,
        user: Any = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> GatewayDecision:
        uid = user_id or getattr(user, "id", None) or (user.get("id") if isinstance(user, dict) else None)
        if self.policy.require_user_id and not uid:
            return GatewayDecision(False, "ingress: 缺少 user_id")

        if self.policy.allowed_agent_ids is not None and agent_id:
            if agent_id not in self.policy.allowed_agent_ids:
                return GatewayDecision(False, f"ingress: agent_id 不在白名单: {agent_id}")

        # RBAC：需要 AGENT_USE（失败关闭：策略异常不得放行）
        try:
            from utils.agent_infra.tool_acl import roles_from_user
            from utils.rbac import Permission, RBACChecker

            roles = roles_from_user(user) if user is not None else None
            if roles is not None and not RBACChecker.user_has_permission(roles, Permission.AGENT_USE):
                if not RBACChecker.user_has_permission(roles, Permission.TOOL_EXECUTE):
                    return GatewayDecision(False, "ingress: 缺少 AGENT_USE 权限")
        except Exception as e:
            logger.exception("ingress rbac check failed (fail-closed)")
            return GatewayDecision(False, "ingress: RBAC 检查失败")

        return GatewayDecision(
            True,
            "ok",
            metadata={"user_id": uid, "agent_id": agent_id, "session_id": session_id},
        )

    def filter_messages(
        self,
        messages: List[Dict[str, Any]],
        *,
        hard_block_system_injection: bool = True,
    ) -> GatewayDecision:
        if len(messages) > self.policy.max_messages:
            return GatewayDecision(
                False,
                f"ingress: 消息条数超限 ({len(messages)} > {self.policy.max_messages})",
            )

        filtered: List[Dict[str, Any]] = []
        flags: List[str] = []
        try:
            from utils.agent_memory.governance import scan_injection
        except Exception:
            scan_injection = lambda _t: None  # type: ignore

        for msg in messages:
            m = dict(msg)
            content = m.get("content")
            if isinstance(content, str):
                if len(content) > self.policy.max_message_chars:
                    content = content[: self.policy.max_message_chars] + "\n...[ingress truncated]..."
                    m["content"] = content
                    flags.append("truncated")
                if self.policy.block_injection and content:
                    hit = scan_injection(content)
                    if hit:
                        role = (m.get("role") or "").lower()
                        if role == "system" and hard_block_system_injection:
                            return GatewayDecision(False, f"ingress: system 消息 {hit}")
                        # user 消息：标注但不阻断（创作场景常有「忽略」措辞）
                        m["_ingress_flags"] = list(m.get("_ingress_flags") or []) + ["injection_suspect"]
                        flags.append("injection_suspect")
            filtered.append(m)

        return GatewayDecision(
            True,
            "ok",
            filtered_payload=filtered,
            metadata={"flags": flags},
        )

    def prepare(
        self,
        *,
        messages: List[Dict[str, Any]],
        user: Any = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> GatewayDecision:
        auth = self.authorize_request(
            user=user, user_id=user_id, agent_id=agent_id, session_id=session_id
        )
        if not auth.allowed:
            return auth
        filt = self.filter_messages(messages)
        if not filt.allowed:
            return filt
        return GatewayDecision(
            True,
            "ok",
            filtered_payload=filt.filtered_payload,
            metadata={**auth.metadata, **filt.metadata},
        )


class EgressGateway:
    """离开 Harness 时：工具/模型/网络/凭据。"""

    def __init__(self, policy: Optional[EgressPolicy] = None):
        self.policy = policy or EgressPolicy.from_env()

    def check_model(self, model: Optional[str]) -> GatewayDecision:
        if not model:
            return GatewayDecision(True, "ok")
        allow = self.policy.allowed_models
        if allow is None:
            # 无显式白名单时用默认宽松集 + 任意 glm-/gpt-/claude- 前缀
            if model in DEFAULT_MODEL_ALLOWLIST:
                return GatewayDecision(True, "ok")
            if model.startswith(("glm-", "gpt-", "claude-", "qwen-", "deepseek-")):
                return GatewayDecision(True, "ok")
            return GatewayDecision(False, f"egress: 模型不在允许列表: {model}")
        if model not in allow:
            return GatewayDecision(False, f"egress: 模型不在允许列表: {model}")
        return GatewayDecision(True, "ok")

    def check_tool(
        self,
        tool_name: str,
        *,
        dangerous: bool = False,
        user: Any = None,
        allow_write: bool = False,
        confirm_dangerous: bool = False,
    ) -> GatewayDecision:
        if tool_name in self.policy.denied_tools:
            return GatewayDecision(False, f"egress: 工具被策略拒绝: {tool_name}")
        if self.policy.allowed_tools is not None and tool_name not in self.policy.allowed_tools:
            return GatewayDecision(False, f"egress: 工具不在白名单: {tool_name}")

        # 无 user 对象：内部/系统调用 — 非危险工具放行；危险工具仍要 allow_write+confirm
        if user is None:
            if dangerous or tool_name in ("run_shell", "run_python", "write", "edit"):
                if not allow_write:
                    return GatewayDecision(False, "egress: 危险工具需要 allow_write=true")
                if not confirm_dangerous:
                    return GatewayDecision(
                        False,
                        "egress: 危险工具需要 confirm_dangerous=true",
                        require_confirm=True,
                    )
            return GatewayDecision(True, "ok")

        from utils.agent_infra.tool_acl import check_tool_access

        acl = check_tool_access(
            tool_name=tool_name,
            dangerous=dangerous,
            user=user,
            allow_write=allow_write,
            confirm_dangerous=confirm_dangerous,
        )
        if not acl.allowed:
            return GatewayDecision(
                False,
                f"egress: {acl.reason}",
                require_confirm=acl.require_confirm,
            )
        return GatewayDecision(True, "ok")

    def check_network_destination(self, host_or_url: str) -> GatewayDecision:
        raw = (host_or_url or "").lower().strip()
        if not raw:
            return GatewayDecision(True, "ok")
        for deny in self.policy.denied_egress_hosts:
            if deny.lower() in raw:
                return GatewayDecision(False, f"egress: 禁止访问目的地含 {deny}")
        if not self.policy.allow_network_in_sandbox:
            # 沙箱默认无网：任何 URL / curl 模式拒绝在 shell 侧落地
            if _URL_IN_SHELL.search(raw) or "://" in raw:
                if self.policy.allowed_egress_hosts:
                    if any(h.lower() in raw for h in self.policy.allowed_egress_hosts):
                        return GatewayDecision(True, "ok", metadata={"allowlisted": True})
                return GatewayDecision(
                    False,
                    "egress: 沙箱默认禁止外网；设置 AGENT_EGRESS_ALLOW_NETWORK=1 或白名单 hosts",
                )
        return GatewayDecision(True, "ok")

    def check_shell_command(self, command: str) -> GatewayDecision:
        """Shell 出站：危险模式 + 网络目的地。"""
        from utils.agent_tools.process_sandbox import assert_safe_shell_command
        from utils.agent_tools.sandbox import SandboxError

        try:
            assert_safe_shell_command(command)
        except SandboxError as e:
            return GatewayDecision(False, f"egress: {e}")
        return self.check_network_destination(command)

    def sandbox_env(
        self,
        *,
        base_allowlist: Optional[List[str]] = None,
        inject_keys: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """
        构造进程沙箱环境：默认剥离密钥。
        凭据挂载在 Gateway 侧完成，Harness 不持有密钥选择逻辑。
        """
        allowed = set(base_allowlist or ["PATH", "LANG", "LC_ALL", "HOME", "TMPDIR"])
        clean = {k: v for k, v in os.environ.items() if k in allowed and k not in SENSITIVE_ENV_KEYS}
        clean["PYTHONDONTWRITEBYTECODE"] = "1"
        # 明确切断常见代理/云 metadata 诱导
        clean["NO_PROXY"] = "*"
        clean["no_proxy"] = "*"
        if self.policy.attach_credentials and inject_keys:
            for k in inject_keys:
                if k in os.environ and k not in SENSITIVE_ENV_KEYS:
                    clean[k] = os.environ[k]
                # 敏感键仅当显式 inject 且 attach_credentials
                elif k in os.environ and self.policy.attach_credentials:
                    clean[k] = os.environ[k]
        return clean

    def filter_tools_schema(
        self,
        tools: List[Dict[str, Any]],
        *,
        user: Any = None,
    ) -> List[Dict[str, Any]]:
        from utils.agent_infra.tool_acl import filter_tools_for_user

        filtered = filter_tools_for_user(tools, user)
        out = []
        for t in filtered:
            name = (t.get("function") or {}).get("name") or t.get("name") or ""
            if name in self.policy.denied_tools:
                continue
            if self.policy.allowed_tools is not None and name not in self.policy.allowed_tools:
                continue
            out.append(t)
        return out


_ingress: Optional[IngressGateway] = None
_egress: Optional[EgressGateway] = None


def get_ingress_gateway() -> IngressGateway:
    global _ingress
    if _ingress is None:
        _ingress = IngressGateway()
    return _ingress


def get_egress_gateway() -> EgressGateway:
    global _egress
    if _egress is None:
        _egress = EgressGateway()
    return _egress


def reset_gateways_for_tests() -> None:
    global _ingress, _egress
    _ingress = None
    _egress = None
