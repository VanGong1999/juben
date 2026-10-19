"""DramaManager — type 字段（short_drama / long_drama / script_analysis）与列表过滤单测"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from utils.drama_manager import DramaManager


def _run(coro):
    return asyncio.run(coro)


def test_create_drama_type_field(tmp_path: Path):
    mgr = DramaManager(base_dir=str(tmp_path))
    short = _run(mgr.create_drama("短剧", type="short_drama"))
    long = _run(mgr.create_drama("长剧", type="long_drama"))
    analysis = _run(mgr.create_drama("分析", type="script_analysis"))

    assert short["type"] == "short_drama"
    assert long["type"] == "long_drama"
    assert analysis["type"] == "script_analysis"

    # drama.json 落盘含 type
    dj = json.loads((tmp_path / long["id"] / "drama.json").read_text(encoding="utf-8"))
    assert dj["type"] == "long_drama"

    # project.json metadata.kind 镜像 type
    pj = json.loads((tmp_path / long["id"] / "project.json").read_text(encoding="utf-8"))
    assert pj["metadata"]["kind"] == "long_drama"


def test_create_drama_defaults_to_short_drama(tmp_path: Path):
    mgr = DramaManager(base_dir=str(tmp_path))
    meta = _run(mgr.create_drama("默认"))
    assert meta["type"] == "short_drama"


def test_list_dramas_type_filter(tmp_path: Path):
    mgr = DramaManager(base_dir=str(tmp_path))
    _run(mgr.create_drama("短", type="short_drama"))
    _run(mgr.create_drama("长", type="long_drama"))
    _run(mgr.create_drama("析", type="script_analysis"))

    all_ = _run(mgr.list_dramas())
    assert {d["title"] for d in all_} == {"短", "长", "析"}

    longs = _run(mgr.list_dramas(type_filter="long_drama"))
    assert {d["title"] for d in longs} == {"长"}

    shorts = _run(mgr.list_dramas(type_filter="short_drama"))
    assert {d["title"] for d in shorts} == {"短"}

    analysis = _run(mgr.list_dramas(type_filter="script_analysis"))
    assert {d["title"] for d in analysis} == {"析"}


def test_update_drama_type(tmp_path: Path):
    mgr = DramaManager(base_dir=str(tmp_path))
    meta = _run(mgr.create_drama("改", type="short_drama"))
    updated = _run(mgr.update_drama(meta["id"], type="long_drama"))
    assert updated["type"] == "long_drama"

    reloaded = _run(mgr._load_meta(meta["id"]))
    assert reloaded["type"] == "long_drama"


def test_legacy_meta_defaults_type(tmp_path: Path):
    """无 drama.json 时从 project.json 迁移，type 取 metadata.kind，缺省 short_drama"""
    mgr = DramaManager(base_dir=str(tmp_path))
    root = tmp_path / "legacy"
    (root / "bible").mkdir(parents=True, exist_ok=True)
    (root / "outline").mkdir(parents=True, exist_ok=True)
    (root / "episodes").mkdir(parents=True, exist_ok=True)
    (root / "project.json").write_text(
        json.dumps(
            {
                "id": "legacy",
                "name": "旧项目",
                "description": "",
                "status": "active",
                "metadata": {"total_episodes": 30, "genre": "都市", "kind": "long_drama"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    meta = _run(mgr._load_meta("legacy"))
    assert meta["type"] == "long_drama"

    # 无 kind 时缺省 short_drama
    root2 = tmp_path / "legacy2"
    (root2 / "bible").mkdir(parents=True, exist_ok=True)
    (root2 / "outline").mkdir(parents=True, exist_ok=True)
    (root2 / "episodes").mkdir(parents=True, exist_ok=True)
    (root2 / "project.json").write_text(
        json.dumps({"id": "legacy2", "name": "旧2", "metadata": {"total_episodes": 30}}, ensure_ascii=False),
        encoding="utf-8",
    )
    meta2 = _run(mgr._load_meta("legacy2"))
    assert meta2["type"] == "short_drama"
