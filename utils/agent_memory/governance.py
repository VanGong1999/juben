"""
记忆治理 — 注入消毒、审计日志、可删除性与可追溯性

防护目标（对齐 Hermes / MemGPT / LangMem 生产实践）:
- prompt injection 持久化污染常驻记忆
- 错误记忆永久化（需 supersede / delete + audit）
- summary 丢证据（保留 EvidenceRef 指向原文）
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# 常见「覆盖系统指令」注入模式（写入常驻前拦截）
_INJECTION_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("ignore_rules", re.compile(r"(忽略|无视|forget|ignore)\s*(以上|之前|所有|全部|previous|all)?\s*(规则|指令|rules|instructions)", re.I)),
    ("system_override", re.compile(r"(你现在是|you are now|act as|角色扮演为)\s*(系统|root|admin|管理员)", re.I)),
    ("jailbreak", re.compile(r"(DAN|jailbreak|开发者模式|developer\s*mode)", re.I)),
    ("exfiltrate", re.compile(r"(输出|泄露|dump)\s*(系统提示|system\s*prompt|API\s*key|密钥)", re.I)),
]


def scan_injection(text: str) -> Optional[str]:
    """若检测到可疑注入，返回原因；否则 None。"""
    if not text or not text.strip():
        return None
    for name, pat in _INJECTION_PATTERNS:
        if pat.search(text):
            return f"疑似 prompt injection ({name})，拒绝持久化写入常驻记忆"
    return None


def require_clean(text: str) -> None:
    reason = scan_injection(text)
    if reason:
        raise ValueError(reason)


def audit_entry(
    *,
    action: str,
    layer: str,
    target_id: str,
    user_id: Optional[str] = None,
    drama_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    detail: Optional[Dict[str, Any]] = None,
    before: Optional[Any] = None,
    after: Optional[Any] = None,
) -> Dict[str, Any]:
    return {
        "audit_id": f"aud_{datetime.now().strftime('%Y%m%d%H%M%S')}_{abs(hash(target_id)) % 10**8:08d}",
        "action": action,  # create|update|delete|supersede|archive|pin|reflect|dream|promote
        "layer": layer,
        "target_id": target_id,
        "user_id": user_id,
        "drama_id": drama_id,
        "agent_id": agent_id,
        "detail": detail or {},
        "before_snippet": _snip(before),
        "after_snippet": _snip(after),
        "created_at": datetime.now().isoformat(),
    }


def _snip(val: Any, n: int = 240) -> Optional[str]:
    if val is None:
        return None
    s = val if isinstance(val, str) else str(val)
    return s[:n]


def evidence_ref(
    *,
    kind: str,
    path: Optional[str] = None,
    session_id: Optional[str] = None,
    episode_id: Optional[str] = None,
    commit: Optional[str] = None,
    offset: Optional[int] = None,
    length: Optional[int] = None,
    quote: Optional[str] = None,
) -> Dict[str, Any]:
    """可追溯证据指针 — 优先存指针，不全文塞进常驻。"""
    return {
        "kind": kind,  # session|file|episode|bible|commit|user_edit
        "path": path,
        "session_id": session_id,
        "episode_id": episode_id,
        "commit": commit,
        "offset": offset,
        "length": length,
        "quote": (quote or "")[:200] or None,
    }
