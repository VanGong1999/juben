"""Agent Memory v2 — 版本链 / OCC / 双时态 / 强度 / org / 导出脱敏 单测"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from utils.agent_memory.service import AgentMemoryService
from utils.agent_memory.store import MemoryStore
from utils.agent_memory.version_store import MemoryVersionStore, unified_diff


def _svc(tmp_path: Path) -> AgentMemoryService:
    return AgentMemoryService(store=MemoryStore(workspace_root=tmp_path))


# ---------------- version store ----------------

def test_version_store_diff_and_rollback(tmp_path: Path):
    base = tmp_path / "mem"
    vs = MemoryVersionStore(base)
    r1 = vs.commit("memory", "# MEMORY\n\nv1\n")
    assert r1["success"] and r1["changed"]
    r2 = vs.commit("memory", "# MEMORY\n\nv2\n")
    assert r2["success"] and r2["changed"]
    versions = vs.list_versions(target="memory")
    assert len(versions) == 2
    assert versions[0]["version_id"] == r2["version_id"]
    assert "v2" in vs.diff(r2["version_id"])
    # rollback to v1
    rb = vs.rollback(r1["version_id"])
    assert rb["changed"]
    assert "v1" in vs.read_target("memory")
    assert len(vs.list_versions(target="memory")) == 3


def test_version_store_occ_conflict(tmp_path: Path):
    vs = MemoryVersionStore(tmp_path / "mem")
    r1 = vs.commit("memory", "v1")
    vs.commit("memory", "v2")  # someone else writes
    res = vs.commit("memory", "v3", expected_version=r1["version_id"])
    assert res["conflict"] is True
    assert res["current_version_id"] != r1["version_id"]
    assert vs.read_target("memory") == "v2"  # 绝不静默覆盖


def test_unified_diff_empty_on_equal():
    assert unified_diff("a", "a") == ""
    assert "+b" in unified_diff("a", "b")


# ---------------- service: markdown version chain ----------------

def test_drama_resident_version_chain_and_conflict(tmp_path: Path):
    svc = _svc(tmp_path)
    drama = "d1"
    svc.set_drama_resident(drama, "# MEMORY\n\nv1\n")
    head = svc.list_memory_versions(drama, target="memory")[0]["version_id"]
    svc.set_drama_resident(drama, "# MEMORY\n\nv2\n")
    assert len(svc.list_memory_versions(drama, target="memory")) == 2

    res = svc.set_drama_resident(drama, "# MEMORY\n\nv3\n", expected_version=head)
    assert res["conflict"] is True
    assert "v2" in svc.get_drama_resident(drama)  # not overwritten

    svc.rollback_memory_version(drama, head)
    assert "v1" in svc.get_drama_resident(drama)


# ---------------- service: semantic OCC ----------------

def test_semantic_occ_conflict(tmp_path: Path):
    svc = _svc(tmp_path)
    drama = "d1"
    svc.upsert_fact(drama_id=drama, entity_type="plot_thread", entity_id="a", predicate="open_thread", value="A")
    head = int(svc.store.read_meta(drama)["head_version"])
    svc.upsert_fact(drama_id=drama, entity_type="plot_thread", entity_id="b", predicate="open_thread", value="B")
    res = svc.upsert_fact(
        drama_id=drama,
        entity_type="plot_thread",
        entity_id="c",
        predicate="open_thread",
        value="C",
        expected_version=head,
    )
    assert res.get("conflict") is True
    # 确认 C 未被写入
    values = [f["value"] for f in svc.list_facts(drama, active_only=False)]
    assert "C" not in values


# ---------------- service: bitemporal supersession ----------------

def test_supersession_keeps_history(tmp_path: Path):
    svc = _svc(tmp_path)
    drama = "d1"
    f1 = svc.upsert_fact(drama_id=drama, entity_type="character", entity_id="c1", predicate="has_trait", value="冷静")
    f2 = svc.upsert_fact(drama_id=drama, entity_type="character", entity_id="c1", predicate="has_trait", value="暴躁")
    facts = svc.list_facts(drama, active_only=False)
    old = next(f for f in facts if f["fact_id"] == f1["fact_id"])
    assert old["status"] == "superseded"
    assert old.get("valid_until") is not None
    assert old["superseded_by"] == f2["fact_id"]


# ---------------- service: strength decay ----------------

def test_strength_decay_archives(tmp_path: Path):
    svc = _svc(tmp_path)
    drama = "d1"
    f = svc.upsert_fact(drama_id=drama, entity_type="plot_thread", entity_id="x", predicate="cliffhanger", value="旧悬念")
    path = svc._semantic_path(drama)
    facts = svc._read_semantic(drama)
    for x in facts:
        if x["fact_id"] == f["fact_id"]:
            x["valid_from"] = (datetime.now() - timedelta(days=100)).isoformat()
            x["strength"] = 0.5
    svc._write_semantic(path, facts)
    report = svc.run_forgetting(drama)
    assert report["decayed_facts"] >= 1


# ---------------- service: org isolation ----------------

def test_org_isolation(tmp_path: Path):
    svc = _svc(tmp_path)
    drama = "d1"
    svc.set_org_resident("# ORG\n\n规则一\n")
    svc.upsert_org_fact(entity_type="decision", entity_id="cross", predicate="best_practice", value="黄金三秒")
    org_facts = svc.list_org_facts()
    assert any(f["predicate"] == "best_practice" for f in org_facts)
    # org 事实不混入作品语义
    drama_facts = svc.list_facts(drama, active_only=False)
    assert all(f.get("scope") != "org" for f in drama_facts)
    # org resident 版本链
    assert len(svc.list_org_versions()) >= 1


# ---------------- service: export / redact ----------------

def test_export_and_redact(tmp_path: Path):
    svc = _svc(tmp_path)
    drama = "d1"
    svc.upsert_fact(
        drama_id=drama,
        entity_type="decision",
        entity_id="contact",
        predicate="lesson_learned",
        value="联系人 13800138000 邮箱 a@b.com",
    )
    export = svc.export_memory(drama)
    assert export["schema_version"] == 2
    assert export["facts"]
    assert "versions" in export

    red = svc.redact_memory(drama, preview=True)
    assert red["count"] >= 1
    assert any(h["type"] == "phone_cn" for h in red["hits"])
    assert "13800138000" not in red["redacted_text"]
