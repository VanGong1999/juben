#!/usr/bin/env python3
"""Prompt-cache 组装冒烟：stable/dynamic 分离、hooks、compaction 边界。"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


async def main() -> int:
    from utils.agent_infra.context_budget import assemble_prompt_bundle
    from utils.agent_infra.prompt_cache import fingerprint_prefix, load_prompt_cache_config
    from utils.agent_infra.prompt_hooks import get_prompt_hooks
    from utils.agent_infra.cache_compaction import compact_messages, should_compact
    from utils.agent_infra.prompt_cache import PromptCacheConfig

    hooks = get_prompt_hooks()
    hooks.clear()

    def static_hook(_ctx):
        return {"prependSystemContext": "【静态策略】始终遵守短剧竖屏规范。"}

    def dynamic_hook(_ctx):
        return {"prependDynamicSystemContext": "【运行时】now=turn-volatile"}

    hooks.on("before_prompt_build", static_hook, name="static", priority=10)
    hooks.on("before_prompt_build", dynamic_hook, name="dynamic", priority=5)

    cfg = load_prompt_cache_config()
    assert cfg.enabled, "prompt_cache should be enabled in config"

    a1 = await assemble_prompt_bundle(
        system_prompt="你是短剧策划助手。",
        user_messages=[{"role": "user", "content": "写第一集"}],
        session_id="smoke-pc-1",
        agent_id="smoke",
        query="写第一集",
        run_hooks=True,
    )
    a2 = await assemble_prompt_bundle(
        system_prompt="你是短剧策划助手。",
        user_messages=[{"role": "user", "content": "继续第二集"}],
        session_id="smoke-pc-1",
        agent_id="smoke",
        query="继续第二集",
        run_hooks=True,
    )

    assert a1.parts.stable_prefix == a2.parts.stable_prefix, "stable prefix must be byte-identical"
    assert "短剧策划助手" in a1.parts.stable_prefix
    assert "静态策略" in a1.parts.stable_prefix
    assert "运行时" in a1.parts.dynamic_suffix
    assert a1.parts.stable_prefix == a2.parts.stable_prefix
    assert fingerprint_prefix(a1.parts.stable_prefix) == fingerprint_prefix(a2.parts.stable_prefix)
    assert a1.prompt_cache_key == a2.prompt_cache_key, "same session cache key until compaction"

    # compaction 后 cache key 应变（compaction_count）
    long_msgs = [{"role": "system", "content": "stable rules", "_cacheable": True}]
    for i in range(40):
        long_msgs.append({"role": "user", "content": ("x" * 800) + f" turn-{i}"})
        long_msgs.append({"role": "assistant", "content": ("y" * 800) + f" ans-{i}"})
    compact_cfg = PromptCacheConfig(compact_threshold_chars=5000, keep_recent_messages=4)
    assert should_compact(long_msgs, compact_cfg)
    result = await compact_messages(long_msgs, client=None, config=compact_cfg, session_id="smoke-pc-1")
    assert result.mode in ("compact", "self_compact")
    assert result.kept_recent == 4
    assert any("Context Compaction Summary" in str(m.get("content") or "") for m in result.messages)

    a3 = await assemble_prompt_bundle(
        system_prompt="你是短剧策划助手。",
        user_messages=[{"role": "user", "content": "第三集"}],
        session_id="smoke-pc-1",
        agent_id="smoke",
        query="第三集",
        run_hooks=True,
    )
    assert a3.prompt_cache_key != a1.prompt_cache_key, "compaction should bump cache key lineage"

    print("OK prompt_cache smoke")
    print(f"  stable_len={len(a1.parts.stable_prefix)} dynamic_len={len(a1.parts.dynamic_suffix)}")
    print(f"  cache_key_before={a1.prompt_cache_key} after_compact={a3.prompt_cache_key}")
    print(f"  compaction mode={result.mode} dropped={result.dropped_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
