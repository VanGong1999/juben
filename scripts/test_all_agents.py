#!/usr/bin/env python3
"""全量 Agent Smoke Test — 加载所有 agent，验证可加载 + 处理入口存在。

用法：venv/bin/python scripts/test_all_agents.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# 抑制 agent 初始化日志，只保留 smoke test 的汇总输出
logging.disable(logging.CRITICAL)


def collect_agent_ids() -> list[str]:
    from config.agents import get_all_agents_config

    ids = [c["id"] for c in get_all_agents_config()]
    try:
        from utils.agent_registry import _LEGACY_AGENTS

        for aid in _LEGACY_AGENTS:
            if aid not in ids:
                ids.append(aid)
    except Exception:
        pass
    return ids


def main() -> int:
    from utils.agent_runtime import load_agent

    ids = collect_agent_ids()
    ok: list[tuple[str, str, str]] = []
    fail: list[tuple[str, str]] = []

    for aid in ids:
        try:
            agent = load_agent(aid, fresh=True)
            entries = [
                m
                for m in (
                    "process_request",
                    "process_request_with_enhanced_context",
                    "process",
                    "run",
                    "handle",
                )
                if hasattr(agent, m)
            ]
            ok.append((aid, type(agent).__name__, ",".join(entries) if entries else "(无处理入口)"))
        except Exception as e:
            fail.append((aid, f"{type(e).__name__}: {e}"))

    print(f"=== 全量 Agent Smoke Test ===")
    print(f"总数 {len(ids)} · 成功 {len(ok)} · 失败 {len(fail)}")
    print()
    for aid, cls, entries in ok:
        print(f"  ✅ {aid:35s} {cls:30s} {entries}")
    for aid, err in fail:
        print(f"  ❌ {aid:35s} {err}")

    print()
    if fail:
        print(f"FAIL: {len(fail)} 个 agent 加载失败")
        return 1
    print("PASS: 全部 agent 可加载")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
