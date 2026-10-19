"""
Evaluation & Replay — Dataset / Rubric / Success Rate / LLM-as-Judge
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

import aiofiles

logger = logging.getLogger(__name__)

AgentCallable = Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]


@dataclass
class EvalCase:
    case_id: str
    input: Dict[str, Any]
    checks: List[Dict[str, Any]] = field(default_factory=list)
    # checks 示例:
    # {"type": "contains", "field": "content", "value": "钩子"}
    # {"type": "regex", "field": "content", "pattern": r"^#"}
    # {"type": "tool_called", "tool": "read"}
    # {"type": "min_score", "field": "score", "value": 70}
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvalCase":
        return cls(
            case_id=str(data.get("case_id") or data.get("id") or ""),
            input=dict(data.get("input") or {}),
            checks=list(data.get("checks") or []),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class EvalCaseResult:
    case_id: str
    passed: bool
    score: float
    details: List[Dict[str, Any]] = field(default_factory=list)
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "passed": self.passed,
            "score": self.score,
            "details": self.details,
            "error": self.error,
        }


@dataclass
class EvalReport:
    suite_id: str
    results: List[EvalCaseResult]
    started_at: str
    finished_at: str

    @property
    def success_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.passed) / len(self.results)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suite_id": self.suite_id,
            "success_rate": self.success_rate,
            "passed": sum(1 for r in self.results if r.passed),
            "total": len(self.results),
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "results": [r.to_dict() for r in self.results],
        }


def _get_field(output: Dict[str, Any], field_path: str) -> Any:
    cur: Any = output
    for part in field_path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def run_checks(output: Dict[str, Any], checks: List[Dict[str, Any]]) -> EvalCaseResult:
    details: List[Dict[str, Any]] = []
    passed_n = 0
    for c in checks:
        ctype = c.get("type")
        ok = False
        msg = ""
        if ctype == "contains":
            val = str(_get_field(output, c.get("field", "content")) or "")
            needle = str(c.get("value") or "")
            ok = needle in val
            msg = f"contains {needle!r}: {ok}"
        elif ctype == "not_contains":
            val = str(_get_field(output, c.get("field", "content")) or "")
            needle = str(c.get("value") or "")
            ok = needle not in val
            msg = f"not_contains {needle!r}: {ok}"
        elif ctype == "regex":
            val = str(_get_field(output, c.get("field", "content")) or "")
            pat = c.get("pattern") or ""
            ok = bool(re.search(pat, val, re.MULTILINE))
            msg = f"regex {pat!r}: {ok}"
        elif ctype == "tool_called":
            history = output.get("tool_history") or []
            tool = c.get("tool")
            ok = any(h.get("tool_name") == tool for h in history)
            msg = f"tool_called {tool}: {ok}"
        elif ctype == "min_score":
            score = float(_get_field(output, c.get("field", "score")) or 0)
            thr = float(c.get("value") or 0)
            ok = score >= thr
            msg = f"min_score {score}>={thr}: {ok}"
        elif ctype == "equals":
            val = _get_field(output, c.get("field", "content"))
            ok = val == c.get("value")
            msg = f"equals: {ok}"
        else:
            msg = f"unknown check type: {ctype}"
            ok = False
        details.append({"check": c, "ok": ok, "message": msg})
        if ok:
            passed_n += 1

    total = max(len(checks), 1)
    score = passed_n / total
    return EvalCaseResult(
        case_id="",
        passed=passed_n == len(checks) and len(checks) > 0,
        score=score,
        details=details,
        output=output,
    )


class EvalRunner:
    def __init__(self, agent_fn: Optional[AgentCallable] = None) -> None:
        self.agent_fn = agent_fn

    @staticmethod
    async def load_dataset(path: str) -> List[EvalCase]:
        p = Path(path)
        cases: List[EvalCase] = []
        async with aiofiles.open(p, "r", encoding="utf-8") as f:
            async for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                cases.append(EvalCase.from_dict(json.loads(line)))
        return cases

    async def run_suite(
        self,
        cases: List[EvalCase],
        *,
        suite_id: str = "default",
        agent_fn: Optional[AgentCallable] = None,
        judge_fn: Optional[Callable[[Dict[str, Any], EvalCase], Awaitable[Dict[str, Any]]]] = None,
    ) -> EvalReport:
        fn = agent_fn or self.agent_fn
        if fn is None:
            raise ValueError("agent_fn required")

        started = datetime.now().isoformat()
        results: List[EvalCaseResult] = []
        for case in cases:
            try:
                output = await fn(case.input)
                if judge_fn:
                    judge = await judge_fn(output, case)
                    output = {**output, **judge}
                cr = run_checks(output, case.checks)
                cr.case_id = case.case_id
                cr.output = output
                results.append(cr)
            except Exception as e:
                logger.exception("eval case failed: %s", case.case_id)
                results.append(
                    EvalCaseResult(
                        case_id=case.case_id,
                        passed=False,
                        score=0.0,
                        error=str(e),
                    )
                )

        return EvalReport(
            suite_id=suite_id,
            results=results,
            started_at=started,
            finished_at=datetime.now().isoformat(),
        )

    async def replay_trajectory(
        self,
        messages: List[Dict[str, Any]],
        tool_results: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        """
        Offline replay：用缓存的 tool 结果替换真实执行，重建对话轨迹。
        tool_results: tool_call_id -> llm_text
        """
        replayed: List[Dict[str, Any]] = []
        for msg in messages:
            m = dict(msg)
            if m.get("role") == "tool":
                tcid = m.get("tool_call_id")
                if tcid and tcid in tool_results:
                    m["content"] = tool_results[tcid]
                    m["replayed"] = True
            replayed.append(m)
        return replayed


async def simple_llm_judge(
    client: Any,
    output: Dict[str, Any],
    case: EvalCase,
    *,
    rubric: str = "判断任务是否成功完成，给出 0-100 分与简短理由。",
) -> Dict[str, Any]:
    """轻量 LLM-as-Judge：面向 agent 输出，不是内容剧本评测。"""
    content = output.get("content") or json.dumps(output, ensure_ascii=False)[:4000]
    prompt = (
        f"【Rubric】\n{rubric}\n\n"
        f"【任务输入】\n{json.dumps(case.input, ensure_ascii=False)}\n\n"
        f"【Agent 输出】\n{content}\n\n"
        "请只返回 JSON：{\"score\": number, \"passed\": bool, \"reason\": string}"
    )
    raw = await client.chat([{"role": "user", "content": prompt}])
    try:
        m = re.search(r"\{.*\}", raw or "", re.DOTALL)
        data = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        data = {"score": 0, "passed": False, "reason": raw}
    return {
        "score": float(data.get("score") or 0),
        "judge_passed": bool(data.get("passed")),
        "judge_reason": data.get("reason") or "",
    }
