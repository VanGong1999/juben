"""
短剧连载 API
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from utils.drama_manager import get_drama_manager
from utils.drama_version_store import get_drama_version_store, TARGET_KINDS, TARGET_LABELS
from utils.skill_loader import list_skills, get_skill

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/juben", tags=["dramas"])


def _auth_uid(request: Request) -> Optional[str]:
    """认证中间件注入的真实 user_id；未启用认证时返回 None（保持兼容）。"""
    return getattr(request.state, "user_id", None) or None


async def _ensure_owner(mgr, drama_id: str, uid: Optional[str]) -> None:
    """多租户归属校验：仅在认证用户存在时强制，避免越权读改删他人作品。"""
    if not uid:
        return
    meta = await mgr._load_meta(drama_id)
    if meta and meta.get("user_id") and meta.get("user_id") != uid:
        raise HTTPException(status_code=403, detail="无权访问该作品")


class CreateDramaRequest(BaseModel):
    title: str
    description: str = ""
    genre: str = "都市情感"
    total_episodes: int = Field(default=80, ge=1, le=200)
    tags: Optional[List[str]] = None
    user_id: str = "default_user"
    type: str = "short_drama"


class OutlineRequest(BaseModel):
    premise: Optional[str] = None


class WriteEpisodeRequest(BaseModel):
    instruction: Optional[str] = None
    target_words: Optional[int] = None


class AutoWriteRequest(BaseModel):
    from_episode: int = 1
    to_episode: Optional[int] = None


class SaveArtifactRequest(BaseModel):
    content: str
    agent_id: str = ""
    agent_name: str = ""
    category: str = ""
    kind: str = ""
    title: str = ""
    user_prompt: str = ""
    sync_bible: bool = True


class UpdateDramaRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    genre: Optional[str] = None
    total_episodes: Optional[int] = None
    type: Optional[str] = None


class SaveBibleRequest(BaseModel):
    world: Optional[str] = None
    characters: Optional[str] = None


class WritePartRequest(BaseModel):
    content: str
    agent_id: str = ""
    agent_name: str = ""
    session_id: str = ""
    expected_version: Optional[str] = None
    episode_number: Optional[int] = None
    title: str = ""


@router.get("/dramas")
async def list_dramas(request: Request, page: int = 1, page_size: int = 50, type: Optional[str] = None):
    mgr = get_drama_manager()
    dramas = await mgr.list_dramas(type_filter=type, user_id=_auth_uid(request))
    start = (page - 1) * page_size
    end = start + page_size
    return {"success": True, "dramas": dramas[start:end], "total": len(dramas)}


@router.post("/dramas")
async def create_drama(req: CreateDramaRequest, request: Request):
    mgr = get_drama_manager()
    drama = await mgr.create_drama(
        title=req.title,
        description=req.description,
        genre=req.genre,
        total_episodes=req.total_episodes,
        tags=req.tags,
        user_id=_auth_uid(request) or req.user_id,
        type=req.type,
    )
    return {"success": True, "drama": drama}


@router.get("/dramas/{drama_id}")
async def get_drama(drama_id: str, request: Request):
    mgr = get_drama_manager()
    await _ensure_owner(mgr, drama_id, _auth_uid(request))
    drama = await mgr.get_drama(drama_id)
    if not drama:
        raise HTTPException(status_code=404, detail="短剧不存在")
    return {"success": True, "drama": drama}


@router.put("/dramas/{drama_id}")
async def update_drama(drama_id: str, req: UpdateDramaRequest, request: Request):
    mgr = get_drama_manager()
    await _ensure_owner(mgr, drama_id, _auth_uid(request))
    drama = await mgr.update_drama(
        drama_id,
        title=req.title,
        description=req.description,
        genre=req.genre,
        total_episodes=req.total_episodes,
        type=req.type,
    )
    if not drama:
        raise HTTPException(status_code=404, detail="短剧不存在")
    return {"success": True, "drama": drama}


@router.delete("/dramas/{drama_id}")
async def delete_drama(drama_id: str, request: Request):
    mgr = get_drama_manager()
    await _ensure_owner(mgr, drama_id, _auth_uid(request))
    ok = await mgr.delete_drama(drama_id)
    if not ok:
        raise HTTPException(status_code=404, detail="短剧不存在")
    return {"success": True}


@router.delete("/dramas/{drama_id}/episodes/{episode_number}")
async def delete_episode(drama_id: str, episode_number: int):
    mgr = get_drama_manager()
    try:
        result = await mgr.delete_episode(drama_id, episode_number)
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/dramas/{drama_id}/bible")
async def save_bible(drama_id: str, req: SaveBibleRequest):
    mgr = get_drama_manager()
    try:
        result = await mgr.save_bible(drama_id, world=req.world, characters=req.characters)
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/dramas/{drama_id}/outline")
async def generate_outline(drama_id: str, req: OutlineRequest):
    mgr = get_drama_manager()
    try:
        result = await mgr.generate_outline(drama_id, req.premise)
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("生成大纲失败")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dramas/{drama_id}/episodes")
async def list_episodes(drama_id: str):
    mgr = get_drama_manager()
    drama = await mgr.get_drama(drama_id)
    if not drama:
        raise HTTPException(status_code=404, detail="短剧不存在")
    return {"success": True, "episodes": drama.get("episodes", [])}


@router.get("/dramas/{drama_id}/episodes/{episode_number}")
async def get_episode(drama_id: str, episode_number: int):
    mgr = get_drama_manager()
    if not await mgr._load_meta(drama_id):
        raise HTTPException(status_code=404, detail="短剧不存在")
    episode = await mgr.get_episode(drama_id, episode_number)
    return {"success": True, "episode": episode}


@router.post("/dramas/{drama_id}/episodes/{episode_number}/write")
async def write_episode(drama_id: str, episode_number: int, req: WriteEpisodeRequest):
    mgr = get_drama_manager()
    try:
        result = await mgr.write_episode_with_llm(
            drama_id, episode_number, req.instruction, req.target_words
        )
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("写作失败")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dramas/{drama_id}/auto-write")
async def auto_write(drama_id: str, req: AutoWriteRequest):
    mgr = get_drama_manager()
    meta = await mgr._load_meta(drama_id)
    if not meta:
        raise HTTPException(status_code=404, detail="短剧不存在")
    from_ep = max(1, req.from_episode)
    to_ep = req.to_episode or min(meta.get("total_episodes", 80), from_ep + 4)
    to_ep = min(to_ep, meta.get("total_episodes", 80))
    if to_ep < from_ep:
        raise HTTPException(status_code=400, detail="集数范围无效")
    job_id = mgr.start_auto_write(drama_id, from_ep, to_ep)
    return {"success": True, "job_id": job_id, "mode": "episode_batch_creator"}


@router.get("/dramas/{drama_id}/auto-write/{job_id}")
async def auto_write_status(drama_id: str, job_id: str):
    mgr = get_drama_manager()
    job = mgr.get_job(job_id)
    if not job or job.get("drama_id") != drama_id:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"success": True, "job": job}


class BatchWriteRequest(BaseModel):
    from_episode: int = 1
    to_episode: Optional[int] = None
    instruction: Optional[str] = None
    target_words: int = Field(default=800, ge=300, le=3000)
    user_id: str = "default_user"
    session_id: Optional[str] = None


class VideoPromptWriteRequest(BaseModel):
    instruction: Optional[str] = None
    target_model: str = "豆包 Seedance 2.5"
    user_id: str = "default_user"
    session_id: Optional[str] = None


class VideoPromptBatchRequest(BaseModel):
    from_episode: int = 1
    to_episode: Optional[int] = None
    instruction: Optional[str] = None
    target_model: str = "豆包 Seedance 2.5"
    user_id: str = "default_user"
    session_id: Optional[str] = None


def _batch_sse(event: Dict[str, Any]) -> str:
    et = event.get("event_type") or event.get("event") or "message"
    payload = {
        "event": et,
        "data": {
            "content": event.get("data"),
            "metadata": event.get("metadata") or {},
        },
        "timestamp": event.get("timestamp"),
    }
    if et in ("complete", "subagent_end", "subagent_start", "composition") and isinstance(
        event.get("data"), dict
    ):
        payload["data"] = {**event["data"], "metadata": event.get("metadata") or {}}
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/dramas/{drama_id}/batch-write")
async def batch_write_stream(drama_id: str, req: BatchWriteRequest, request: Request):
    """SSE：连贯性草稿 + 并行单集 subagents，前端可实时看到 Cursor 风格子专家过程。"""
    await _ensure_owner(get_drama_manager(), drama_id, _auth_uid(request))
    mgr = get_drama_manager()
    meta = await mgr._load_meta(drama_id)
    if not meta:
        raise HTTPException(status_code=404, detail="短剧不存在")
    from_ep = max(1, req.from_episode)
    to_ep = req.to_episode or min(meta.get("total_episodes", 80), from_ep + 4)
    to_ep = min(to_ep, meta.get("total_episodes", 80))
    if to_ep < from_ep:
        raise HTTPException(status_code=400, detail="集数范围无效")

    uid = _auth_uid(request) or req.user_id
    instruction = (req.instruction or "").strip() or (
        f"请并行撰写第{from_ep}–{to_ep}集，确保前后连贯、不重复"
    )

    async def generate():
        try:
            from utils.agent_runtime import load_agent

            agent = load_agent("episode_batch_creator", fresh=True)
            request_data = {
                "input": instruction,
                "query": instruction,
                "from_episode": from_ep,
                "to_episode": to_ep,
                "drama_id": drama_id,
                "target_words": req.target_words,
                "user_requirements": instruction,
            }
            context = {
                "drama_id": drama_id,
                "project_id": drama_id,
                "user_id": uid,
                "session_id": req.session_id or f"batch_{drama_id}",
                "from_episode": from_ep,
                "to_episode": to_ep,
                "target_words": req.target_words,
                "user_requirements": instruction,
            }
            async for event in agent.process_request(request_data, context):
                yield _batch_sse(event)
            yield _batch_sse({"event_type": "done", "data": "ok"})
        except Exception as e:
            logger.exception("batch-write SSE 失败")
            yield _batch_sse({"event_type": "error", "data": str(e)})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/dramas/{drama_id}/video-prompts")
async def list_video_prompts(drama_id: str, request: Request):
    mgr = get_drama_manager()
    await _ensure_owner(mgr, drama_id, _auth_uid(request))
    meta = await mgr._load_meta(drama_id)
    if not meta:
        raise HTTPException(status_code=404, detail="短剧不存在")
    items = await mgr.list_video_prompts(drama_id, meta.get("total_episodes"))
    return {"success": True, "video_prompts": items}


@router.get("/dramas/{drama_id}/video-prompts/{episode_number}")
async def get_video_prompt(drama_id: str, episode_number: int, request: Request):
    mgr = get_drama_manager()
    await _ensure_owner(mgr, drama_id, _auth_uid(request))
    if not await mgr._load_meta(drama_id):
        raise HTTPException(status_code=404, detail="短剧不存在")
    item = await mgr.get_video_prompt(drama_id, episode_number)
    return {"success": True, "video_prompt": item}


@router.post("/dramas/{drama_id}/video-prompts/{episode_number}/write")
async def write_video_prompt(
    drama_id: str,
    episode_number: int,
    req: VideoPromptWriteRequest,
    request: Request,
):
    """单集：剧本 → 豆包 Seedance 视频提示词（SSE）。"""
    await _ensure_owner(get_drama_manager(), drama_id, _auth_uid(request))
    mgr = get_drama_manager()
    if not await mgr._load_meta(drama_id):
        raise HTTPException(status_code=404, detail="短剧不存在")
    ep = await mgr.get_episode(drama_id, episode_number)
    if not (ep.get("content") or "").strip():
        raise HTTPException(status_code=400, detail="该集剧本尚未完成")
    uid = _auth_uid(request) or req.user_id
    instruction = (req.instruction or "").strip() or (
        f"把第{episode_number}集剧本转为豆包 Seedance 视频提示词"
    )

    async def generate():
        try:
            from utils.agent_runtime import load_agent

            agent = load_agent("video_prompt_writer", fresh=True)
            request_data = {
                "input": instruction,
                "query": instruction,
                "episode_number": episode_number,
                "drama_id": drama_id,
                "target_model": req.target_model,
                "user_requirements": instruction,
                "save": True,
            }
            context = {
                "drama_id": drama_id,
                "project_id": drama_id,
                "user_id": uid,
                "session_id": req.session_id or f"vp_{drama_id}_{episode_number}",
                "episode_number": episode_number,
                "episode_script": ep.get("content") or "",
                "target_model": req.target_model,
                "user_requirements": instruction,
                "save": True,
                "bible_excerpt": mgr._bible_text(drama_id),
            }
            async for event in agent.process_request(request_data, context):
                yield _batch_sse(event)
            yield _batch_sse({"event_type": "done", "data": "ok"})
        except Exception as e:
            logger.exception("video-prompt write SSE 失败")
            yield _batch_sse({"event_type": "error", "data": str(e)})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/dramas/{drama_id}/video-prompts/batch-write")
async def batch_write_video_prompts(
    drama_id: str,
    req: VideoPromptBatchRequest,
    request: Request,
):
    """批量：视觉连贯性草稿 + 并行转 Seedance 提示词（SSE）。"""
    await _ensure_owner(get_drama_manager(), drama_id, _auth_uid(request))
    mgr = get_drama_manager()
    meta = await mgr._load_meta(drama_id)
    if not meta:
        raise HTTPException(status_code=404, detail="短剧不存在")
    from_ep = max(1, req.from_episode)
    to_ep = req.to_episode or min(meta.get("total_episodes", 80), from_ep + 4)
    to_ep = min(to_ep, meta.get("total_episodes", 80))
    if to_ep < from_ep:
        raise HTTPException(status_code=400, detail="集数范围无效")
    uid = _auth_uid(request) or req.user_id
    instruction = (req.instruction or "").strip() or (
        f"请把第{from_ep}–{to_ep}集剧本批量转为豆包 Seedance 视频提示词，竖屏不要字幕"
    )

    async def generate():
        try:
            from utils.agent_runtime import load_agent

            agent = load_agent("video_prompt_batch", fresh=True)
            request_data = {
                "input": instruction,
                "query": instruction,
                "from_episode": from_ep,
                "to_episode": to_ep,
                "drama_id": drama_id,
                "target_model": req.target_model,
                "user_requirements": instruction,
            }
            context = {
                "drama_id": drama_id,
                "project_id": drama_id,
                "user_id": uid,
                "session_id": req.session_id or f"vp_batch_{drama_id}",
                "from_episode": from_ep,
                "to_episode": to_ep,
                "target_model": req.target_model,
                "user_requirements": instruction,
            }
            async for event in agent.process_request(request_data, context):
                yield _batch_sse(event)
            yield _batch_sse({"event_type": "done", "data": "ok"})
        except Exception as e:
            logger.exception("video-prompt batch SSE 失败")
            yield _batch_sse({"event_type": "error", "data": str(e)})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/skills")
async def get_skills():
    skills = list_skills()
    # Don't dump full body to list API
    light = [
        {
            "id": s["id"],
            "name": s["name"],
            "description": s["description"],
            "category": s.get("category"),
            "enabled": s.get("enabled", True),
        }
        for s in skills
    ]
    return {"success": True, "skills": light}


@router.get("/skills/{skill_id}")
async def get_skill_detail(skill_id: str):
    skill = get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill 不存在")
    return {"success": True, "skill": skill}


@router.get("/dramas/{drama_id}/artifacts")
async def list_drama_artifacts(drama_id: str, kind: Optional[str] = None, limit: int = 100):
    mgr = get_drama_manager()
    try:
        items = await mgr.list_artifacts(drama_id, kind=kind, limit=limit)
        # summary counts by kind
        counts: Dict[str, int] = {}
        for it in items:
            k = it.get("kind") or "other"
            counts[k] = counts.get(k, 0) + 1
        return {
            "success": True,
            "artifacts": items,
            "total": len(items),
            "counts": counts,
            "kinds": [
                {"id": k, "label": mgr.KIND_LABELS.get(k, k)}
                for k in mgr.ARTIFACT_KINDS
            ],
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/dramas/{drama_id}/artifacts/{artifact_id}")
async def get_drama_artifact(drama_id: str, artifact_id: str):
    mgr = get_drama_manager()
    try:
        item = await mgr.get_artifact(drama_id, artifact_id)
        if not item:
            raise HTTPException(status_code=404, detail="产物不存在")
        return {"success": True, "artifact": item}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/dramas/{drama_id}/artifacts")
async def save_drama_artifact(drama_id: str, req: SaveArtifactRequest):
    mgr = get_drama_manager()
    try:
        artifact = await mgr.save_artifact(
            drama_id,
            content=req.content,
            agent_id=req.agent_id,
            agent_name=req.agent_name,
            category=req.category,
            kind=req.kind,
            title=req.title,
            user_prompt=req.user_prompt,
            sync_bible=req.sync_bible,
        )
        return {"success": True, "artifact": artifact}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("保存产物失败")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/dramas/{drama_id}/artifacts/{artifact_id}")
async def delete_drama_artifact(drama_id: str, artifact_id: str):
    mgr = get_drama_manager()
    try:
        ok = await mgr.delete_artifact(drama_id, artifact_id)
        if not ok:
            raise HTTPException(status_code=404, detail="产物不存在或不可删除")
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ---------------------------------------------------------------------------
# 版本化写回（对话内直接改 小传/大纲/剧本，带版本号 + diff + 并发冲突保护）
# ---------------------------------------------------------------------------

@router.get("/dramas/{drama_id}/parts/{target}")
async def read_drama_part(drama_id: str, target: str, episode_number: Optional[int] = None):
    store = get_drama_version_store()
    try:
        part = await store.read_part(drama_id, target, episode_number=episode_number)
        return {"success": True, "part": part}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/dramas/{drama_id}/parts/{target}")
async def write_drama_part(drama_id: str, target: str, req: WritePartRequest):
    store = get_drama_version_store()
    try:
        result = await store.write(
            drama_id,
            target,
            req.content,
            agent_id=req.agent_id,
            agent_name=req.agent_name,
            session_id=req.session_id,
            expected_version=req.expected_version,
            episode_number=req.episode_number,
            title=req.title,
        )
        return {"success": not result.get("conflict"), "conflict": bool(result.get("conflict")), "result": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("版本化写回失败")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dramas/{drama_id}/versions")
async def list_drama_versions(drama_id: str, target: Optional[str] = None):
    store = get_drama_version_store()
    versions = await store.list_versions(drama_id, target=target)
    return {
        "success": True,
        "versions": versions,
        "total": len(versions),
        "targets": [{"id": k, "label": v} for k, v in TARGET_LABELS.items()],
    }


@router.get("/dramas/{drama_id}/versions/{version_id}")
async def get_drama_version(drama_id: str, version_id: str):
    store = get_drama_version_store()
    version = await store.get_version(drama_id, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="版本不存在")
    return {"success": True, "version": version}


@router.post("/dramas/{drama_id}/versions/{version_id}/rollback")
async def rollback_drama_version(drama_id: str, version_id: str, req: WritePartRequest):
    store = get_drama_version_store()
    try:
        result = await store.rollback(
            drama_id,
            version_id,
            agent_id=req.agent_id,
            agent_name=req.agent_name,
            session_id=req.session_id,
        )
        return {"success": True, "result": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("版本回滚失败")
        raise HTTPException(status_code=500, detail=str(e))
