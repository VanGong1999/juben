#!/usr/bin/env python3
"""
用已有五集剧本测试：视频提示词批量编排（豆包 Seedance）

默认使用上次分集测试作品：
  9573ac51-ffc1-458a-906b-6dc60ab705d7

用法:
  source venv/bin/activate
  python scripts/test_video_prompt_batch_5ep.py
  python scripts/test_video_prompt_batch_5ep.py --drama-id <id>
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DEFAULT_DRAMA = "9573ac51-ffc1-458a-906b-6dc60ab705d7"


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--drama-id", default=DEFAULT_DRAMA)
    parser.add_argument("--from", dest="from_ep", type=int, default=1)
    parser.add_argument("--to", dest="to_ep", type=int, default=5)
    args = parser.parse_args()

    from utils.agent_runtime import load_agent, clear_agent_cache
    from utils.drama_manager import get_drama_manager

    drama_id = args.drama_id
    mgr = get_drama_manager()
    meta = await mgr._load_meta(drama_id)
    if not meta:
        print(f"❌ 短剧不存在: {drama_id}")
        sys.exit(1)

    print(f"📺 《{meta.get('title')}》 drama_id={drama_id}")
    for n in range(args.from_ep, args.to_ep + 1):
        ep = await mgr.get_episode(drama_id, n)
        print(f"  剧本 第{n}集 status={ep.get('status')} words={ep.get('word_count')}")
        if ep.get("status") != "done":
            print("❌ 请先完成分集剧本")
            sys.exit(1)

    clear_agent_cache("video_prompt_batch")
    clear_agent_cache("video_prompt_writer")
    agent = load_agent("video_prompt_batch", fresh=True)

    instruction = (
        f"请把第{args.from_ep}–{args.to_ep}集剧本批量转为豆包 Seedance 2.5 视频提示词。"
        "竖屏9:16，不要字幕，无BGM只保留环境音与动作音，电影级写实光影。"
    )
    request_data = {
        "input": instruction,
        "query": instruction,
        "from_episode": args.from_ep,
        "to_episode": args.to_ep,
        "drama_id": drama_id,
        "target_model": "豆包 Seedance 2.5",
        "user_requirements": instruction,
    }
    context = {
        "drama_id": drama_id,
        "project_id": drama_id,
        "user_id": "default_user",
        "session_id": f"test_vp_{drama_id[:8]}",
        "from_episode": args.from_ep,
        "to_episode": args.to_ep,
        "target_model": "豆包 Seedance 2.5",
        "user_requirements": instruction,
    }

    print("🚀 启动视频提示词批量编排…")
    starts = ends = 0
    async for ev in agent.process_request(request_data, context):
        et = ev.get("event_type")
        data = ev.get("data")
        meta_ev = ev.get("metadata") or {}
        if et == "system":
            print(f"  [system] {str(data)[:120]}")
        elif et == "subagent_start":
            starts += 1
            print(f"  [subagent_start] 第{meta_ev.get('episode_number') or (data or {}).get('episode_number')}集")
        elif et == "subagent_end":
            ends += 1
            epn = meta_ev.get("episode_number") or (data or {}).get("episode_number")
            print(
                f"  [subagent_end] 第{epn}集 success={meta_ev.get('success')} "
                f"words={(data or {}).get('word_count')}"
            )
        elif et == "complete":
            print(f"  [complete] success={(data or {}).get('success')}")

    items = []
    for n in range(args.from_ep, args.to_ep + 1):
        item = await mgr.get_video_prompt(drama_id, n)
        items.append(item)
        print(
            f"  🎥 第{n}集 vp status={item.get('status')} "
            f"words={item.get('word_count')} path={item.get('path')}"
        )

    visual = mgr._dir(drama_id) / "video_prompts" / "visual_continuity.json"
    done = sum(1 for i in items if i.get("status") == "done" and (i.get("word_count") or 0) > 200)
    # 抽查是否含 Seedance 关键要素
    sample = (items[0].get("content") or "") if items else ""
    has_shot = "SHOT-" in sample or "镜头" in sample or "可复制提示词" in sample
    has_symbol = "{" in sample or "不要字幕" in sample

    result = {
        "drama_id": drama_id,
        "studio_url": f"/studio/{drama_id}",
        "subagent_starts": starts,
        "subagent_ends": ends,
        "video_prompts_done": done,
        "visual_continuity": visual.exists(),
        "sample_has_shot_structure": has_shot,
        "sample_has_seedance_symbols": has_symbol,
        "ok": done >= (args.to_ep - args.from_ep + 1) and visual.exists() and starts >= done,
    }
    out = ROOT / "data" / "test_video_prompt_batch_5ep_result.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if items and sample:
        print("\n--- 第1集提示词预览 ---")
        print(sample[:600])
        print("...")
    if not result["ok"]:
        sys.exit(1)
    print(f"\n🎉 查看: projects/{drama_id}/video_prompts/ 或工作室 /studio/{drama_id}")


if __name__ == "__main__":
    asyncio.run(main())
