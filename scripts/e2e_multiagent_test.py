#!/usr/bin/env python3
"""同一部剧多 Agent 实际协作端到端测试（走真实 API + 真实 LLM）。

流程：创建测试剧 → 启动前置创作（AgentTeam：策划→故事→人物/情节点 DAG 并行 + lead 合成）
      → 轮询到完成 → 验证 bible/outline/artifacts 落盘、无 error、下游读到上游。

结果落盘到 projects/{id}/，前端 /dramas 列表和 /studio/{id} 可直接查看。

用法：venv/bin/python scripts/e2e_multiagent_test.py
"""
from __future__ import annotations

import sys
import time
from datetime import datetime

import httpx

BASE = "http://localhost:8000"
POLL_INTERVAL = 3.0
TOTAL_TIMEOUT = 600.0  # 10 分钟


def _post(path: str, json: dict | None = None):
    r = httpx.post(f"{BASE}{path}", json=json, timeout=60.0)
    r.raise_for_status()
    return r.json()


def _get(path: str):
    r = httpx.get(f"{BASE}{path}", timeout=30.0)
    r.raise_for_status()
    return r.json()


def main() -> int:
    title = f"E2E多智能体协作测试_{datetime.now().strftime('%H%M%S')}"
    print(f"① 创建测试剧：{title}")
    created = _post("/juben/dramas", {
        "title": title,
        "description": "都市逆袭短剧：落魄女主重生后向欺辱她的豪门复仇，一路打脸升级，最终夺回一切并收获真爱。",
        "genre": "都市情感",
        "total_episodes": 60,
        "type": "short_drama",
    })
    drama_id = created["drama"]["id"]
    print(f"    drama_id={drama_id}")

    print("② 启动前置创作（策划→故事→人物/情节点）")
    _post(f"/juben/atelier/dramas/{drama_id}/preflight", {"user_id": "default_user", "force": True})
    print("    已启动，轮询状态…")

    # ③ 轮询直到 completed / error / 超时
    start = time.time()
    last_snapshot = ""
    run = None
    while time.time() - start < TOTAL_TIMEOUT:
        time.sleep(POLL_INTERVAL)
        run = _get(f"/juben/atelier/dramas/{drama_id}/run").get("run")
        if not run:
            continue
        snapshot = " · ".join(
            f"{s.get('title') or s.get('id')}={s.get('status')}" for s in run.get("steps") or []
        )
        if snapshot != last_snapshot:
            print(f"    [{run.get('status')}] {snapshot}")
            last_snapshot = snapshot
        if run.get("status") in ("completed", "error"):
            break

    if not run or run.get("status") not in ("completed", "error"):
        print("    ⚠️ 超时未完成")
        return 1

    # ④ 验证结果
    print("\n③ 验证结果")
    steps = run.get("steps") or []
    errors = [s for s in steps if s.get("status") == "error"]
    done = [s for s in steps if s.get("status") == "done"]

    drama = _get(f"/juben/dramas/{drama_id}")["drama"]
    world = (drama.get("bible") or {}).get("world") or ""
    characters = (drama.get("bible") or {}).get("characters") or ""
    outline = drama.get("outline") or ""

    artifacts = _get(f"/juben/dramas/{drama_id}/artifacts", )["artifacts"]

    print(f"    run 状态: {run.get('status')}")
    print(f"    步骤: {len(done)}/{len(steps)} done" + (f"，{len(errors)} error" if errors else ""))
    print(f"    世界观 world.md: {len(world)} 字")
    print(f"    人物 characters.md: {len(characters)} 字")
    print(f"    大纲 outline: {len(outline)} 字")
    print(f"    artifacts: {len(artifacts)} 份")

    for s in steps:
        status = s.get("status")
        mark = "✅" if status == "done" else ("❌" if status == "error" else "⏳")
        print(f"      {mark} [{s.get('module') or s.get('category')}] {s.get('title')} ({status})")

    # ⑤ 输出各步骤产出摘要（人工核查是否割裂）
    print("\n④ 各步骤产出摘要（供人工核查多 agent 是否一致）")
    for s in steps:
        if s.get("status") != "done":
            continue
        aid = s.get("artifact_id")
        if not aid:
            continue
        art = _get(f"/juben/dramas/{drama_id}/artifacts/{aid}").get("artifact")
        if art:
            preview = (art.get("content") or "").replace("\n", " ")[:160]
            print(f"    [{s.get('title')}] {preview}…")

    # ⑥ 判定
    ok = (
        run.get("status") == "completed"
        and not errors
        and len(world) > 50
        and len(characters) > 50
        and len(outline) > 50
        and len(artifacts) >= len(done)
    )
    print(f"\n{'✅ PASS' if ok else '❌ FAIL'}  — drama_id={drama_id}（前端 /dramas 与 /studio/{drama_id} 可查看）")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
