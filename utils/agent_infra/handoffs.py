"""
Handoff 执行器 — 会话 active_agent 所有权转移。

借鉴 OpenAI Handoffs / LangGraph Swarm：下一轮由专家直接对用户说话。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .orchestration import HandoffSpec
from .subagents import normalize_agent_id
from utils.atomic_write import atomic_write_text

logger = logging.getLogger(__name__)

CONDUCTOR_AGENT_ID = "juben_conductor"
AUTO_ALIASES = frozenset({"", "auto", "juben_conductor", "conductor"})


@dataclass
class SessionOrchestrationState:
    session_id: str
    active_agent_id: str = CONDUCTOR_AGENT_ID
    conductor_id: str = CONDUCTOR_AGENT_ID
    handoff_history: List[Dict[str, Any]] = field(default_factory=list)
    updated_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "active_agent_id": self.active_agent_id,
            "conductor_id": self.conductor_id,
            "handoff_history": list(self.handoff_history),
            "updated_at": self.updated_at or datetime.now().isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionOrchestrationState":
        return cls(
            session_id=str(data.get("session_id") or ""),
            active_agent_id=str(data.get("active_agent_id") or CONDUCTOR_AGENT_ID),
            conductor_id=str(data.get("conductor_id") or CONDUCTOR_AGENT_ID),
            handoff_history=list(data.get("handoff_history") or []),
            updated_at=str(data.get("updated_at") or ""),
            metadata=dict(data.get("metadata") or {}),
        )


class SessionOrchestrationStore:
    """会话编排态：默认落盘 data/session_orchestration/{session_id}.json"""

    def __init__(self, root: Optional[str] = None) -> None:
        self.root = Path(root or "data/session_orchestration")
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, session_id: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in (session_id or "default"))
        return self.root / f"{safe}.json"

    def load(self, session_id: str) -> SessionOrchestrationState:
        path = self._path(session_id)
        if not path.exists():
            return SessionOrchestrationState(session_id=session_id or "default")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            state = SessionOrchestrationState.from_dict(data)
            state.session_id = session_id or state.session_id
            return state
        except Exception as e:
            logger.warning("load session orchestration failed: %s (%s)", session_id, e)
            return SessionOrchestrationState(session_id=session_id or "default")

    def save(self, state: SessionOrchestrationState) -> None:
        state.updated_at = datetime.now().isoformat()
        path = self._path(state.session_id)
        atomic_write_text(path, json.dumps(state.to_dict(), ensure_ascii=False, indent=2))


_store: Optional[SessionOrchestrationStore] = None


def get_session_orchestration_store() -> SessionOrchestrationStore:
    global _store
    if _store is None:
        _store = SessionOrchestrationStore()
    return _store


def apply_handoff(
    session_id: str,
    spec: HandoffSpec,
    *,
    store: Optional[SessionOrchestrationStore] = None,
) -> SessionOrchestrationState:
    """执行交接：更新 active_agent，追加 history。"""
    store = store or get_session_orchestration_store()
    state = store.load(session_id or "default")
    to_agent = normalize_agent_id(spec.to_agent)
    from_agent = normalize_agent_id(spec.from_agent) or state.active_agent_id

    entry = {
        **spec.to_dict(),
        "from_agent": from_agent,
        "to_agent": to_agent,
        "at": datetime.now().isoformat(),
    }
    state.handoff_history.append(entry)
    # 保留最近 50 条
    if len(state.handoff_history) > 50:
        state.handoff_history = state.handoff_history[-50:]
    state.active_agent_id = to_agent
    store.save(state)
    logger.info("handoff %s → %s (session=%s)", from_agent, to_agent, session_id)
    return state


def return_to_conductor(
    session_id: str,
    *,
    reason: str = "user or agent returned",
    from_agent: Optional[str] = None,
    store: Optional[SessionOrchestrationStore] = None,
) -> SessionOrchestrationState:
    store = store or get_session_orchestration_store()
    state = store.load(session_id or "default")
    spec = HandoffSpec(
        from_agent=from_agent or state.active_agent_id,
        to_agent=state.conductor_id or CONDUCTOR_AGENT_ID,
        reason=reason,
    )
    return apply_handoff(session_id, spec, store=store)


def resolve_turn_agent(
    *,
    agent_id: Optional[str] = None,
    session_id: Optional[str] = None,
    store: Optional[SessionOrchestrationStore] = None,
) -> Dict[str, Any]:
    """
    解析本轮实际路由的 agent_id。

    优先级：
    1. 显式 agent_id（非 auto）→ 直接用（并可选同步 session active）
    2. session.active_agent（若非 conductor 且存在历史 handoff）
    3. 默认 conductor
    """
    store = store or get_session_orchestration_store()
    sid = session_id or "default"
    state = store.load(sid)
    raw = (agent_id or "").strip().lower() if agent_id else ""

    # 显式专家（非 auto）
    if raw and raw not in AUTO_ALIASES:
        resolved = normalize_agent_id(raw)
        return {
            "agent_id": resolved,
            "source": "explicit",
            "session_active": state.active_agent_id,
            "is_conductor": resolved == CONDUCTOR_AGENT_ID,
        }

    # auto：尊重会话 active（handoff 后）
    active = normalize_agent_id(state.active_agent_id or CONDUCTOR_AGENT_ID)
    if active and active not in AUTO_ALIASES:
        return {
            "agent_id": active,
            "source": "session_handoff",
            "session_active": active,
            "is_conductor": False,
        }

    return {
        "agent_id": CONDUCTOR_AGENT_ID,
        "source": "conductor_default",
        "session_active": state.active_agent_id,
        "is_conductor": True,
    }


def make_handoff_event(
    spec: HandoffSpec,
    *,
    agent_source: str = "",
) -> Dict[str, Any]:
    return {
        "event_type": "handoff",
        "agent_source": agent_source or spec.from_agent,
        "timestamp": datetime.now().isoformat(),
        "data": spec.to_dict(),
        "metadata": {
            "from_agent": spec.from_agent,
            "to_agent": spec.to_agent,
            "reason": spec.reason,
        },
    }
