"""
可观测性 — Agent/Tool Metrics + 简易 Trace span
"""

from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional

logger = logging.getLogger(__name__)

try:
    from prometheus_client import Counter, Histogram

    TOOL_CALLS = Counter(
        "juben_agent_tool_calls_total",
        "Agent tool calls",
        ["tool", "success"],
    )
    TOOL_LATENCY = Histogram(
        "juben_agent_tool_duration_seconds",
        "Agent tool latency",
        ["tool"],
    )
    LLM_TOKENS = Counter(
        "juben_agent_llm_tokens_total",
        "LLM tokens",
        ["kind"],  # prompt | completion
    )
    AGENT_LOOP_LATENCY = Histogram(
        "juben_agent_loop_duration_seconds",
        "Agent loop phase latency",
        ["phase"],
    )
    _PROM = True
except Exception:
    _PROM = False
    TOOL_CALLS = TOOL_LATENCY = LLM_TOKENS = AGENT_LOOP_LATENCY = None  # type: ignore


@dataclass
class Span:
    name: str
    trace_id: str
    span_id: str
    started_at: float
    ended_at: Optional[float] = None
    labels: Dict[str, str] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "duration_ms": ((self.ended_at or time.time()) - self.started_at) * 1000,
            "labels": self.labels,
            "error": self.error,
        }


class AgentMetrics:
    def __init__(self) -> None:
        self.counters: Dict[str, int] = defaultdict(int)
        self.latencies: Dict[str, List[float]] = defaultdict(list)
        self.tokens_prompt = 0
        self.tokens_completion = 0
        self.spans: List[Span] = []
        self._max_spans = 500

    def inc(self, name: str, value: int = 1, labels: Optional[Dict[str, str]] = None) -> None:
        key = name
        if labels:
            key = f"{name}|" + ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        self.counters[key] += value
        if _PROM and name == "tool_calls_total" and labels:
            try:
                TOOL_CALLS.labels(
                    tool=labels.get("tool", "unknown"),
                    success=labels.get("success", "false"),
                ).inc(value)
            except Exception:
                pass

    def record_latency(self, name: str, seconds: float, labels: Optional[Dict[str, str]] = None) -> None:
        key = name
        if labels:
            key = f"{name}|" + ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        self.latencies[key].append(seconds)
        if len(self.latencies[key]) > 200:
            self.latencies[key] = self.latencies[key][-200:]
        if _PROM:
            try:
                if name.startswith("agent_loop"):
                    AGENT_LOOP_LATENCY.labels(phase=labels.get("phase", name) if labels else name).observe(seconds)
                elif name.startswith("agent_loop_tool") or (labels and "tool" in labels):
                    TOOL_LATENCY.labels(tool=(labels or {}).get("tool", "unknown")).observe(seconds)
            except Exception:
                pass

    def record_tokens(self, *, prompt: int = 0, completion: int = 0) -> None:
        self.tokens_prompt += prompt
        self.tokens_completion += completion
        if _PROM:
            try:
                if prompt:
                    LLM_TOKENS.labels(kind="prompt").inc(prompt)
                if completion:
                    LLM_TOKENS.labels(kind="completion").inc(completion)
            except Exception:
                pass

    @contextmanager
    def timer(self, name: str, labels: Optional[Dict[str, str]] = None) -> Iterator[None]:
        t0 = time.time()
        try:
            yield
        finally:
            self.record_latency(name, time.time() - t0, labels)

    def start_span(self, name: str, *, trace_id: Optional[str] = None, labels: Optional[Dict[str, str]] = None) -> Span:
        span = Span(
            name=name,
            trace_id=trace_id or f"trace_{uuid.uuid4().hex[:12]}",
            span_id=f"span_{uuid.uuid4().hex[:10]}",
            started_at=time.time(),
            labels=dict(labels or {}),
        )
        self.spans.append(span)
        if len(self.spans) > self._max_spans:
            self.spans = self.spans[-self._max_spans :]
        return span

    def end_span(self, span: Span, *, error: Optional[str] = None) -> None:
        span.ended_at = time.time()
        span.error = error
        self.record_latency(span.name, span.ended_at - span.started_at, span.labels)

    def snapshot(self) -> Dict[str, Any]:
        latency_summary = {}
        for k, vals in self.latencies.items():
            if not vals:
                continue
            latency_summary[k] = {
                "count": len(vals),
                "avg_ms": (sum(vals) / len(vals)) * 1000,
                "p95_ms": sorted(vals)[max(0, int(len(vals) * 0.95) - 1)] * 1000,
            }
        return {
            "counters": dict(self.counters),
            "latency": latency_summary,
            "tokens": {
                "prompt": self.tokens_prompt,
                "completion": self.tokens_completion,
                "total": self.tokens_prompt + self.tokens_completion,
            },
            "recent_spans": [s.to_dict() for s in self.spans[-20:]],
        }


_metrics: Optional[AgentMetrics] = None


def get_agent_metrics() -> AgentMetrics:
    global _metrics
    if _metrics is None:
        _metrics = AgentMetrics()
    return _metrics


@contextmanager
def traced(name: str, *, trace_id: Optional[str] = None, labels: Optional[Dict[str, str]] = None) -> Iterator[Span]:
    m = get_agent_metrics()
    span = m.start_span(name, trace_id=trace_id, labels=labels)
    try:
        yield span
        m.end_span(span)
    except Exception as e:
        m.end_span(span, error=str(e))
        raise
