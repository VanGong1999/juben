"""
Atelier 编排 API — 首页对话驱动的多智能体创作
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from apis.dramas.ownership import auth_uid, ensure_owner
from utils import atelier_pipeline as atelier

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/juben/atelier", tags=["atelier"])


class AtelierConstraints(BaseModel):
    title: str = ""
    genre: str = "都市情感"
    total_episodes: int = Field(default=80, ge=1, le=200)
    audience: str = ""
    tone: str = ""
    modules: Optional[List[str]] = None
    drama_id: Optional[str] = None
    user_id: str = "default_user"


class ProposePlanRequest(BaseModel):
    query: str
    constraints: AtelierConstraints = Field(default_factory=AtelierConstraints)


class PlanStepIn(BaseModel):
    id: Optional[str] = None
    agent_id: str
    title: Optional[str] = None
    rationale: Optional[str] = None
    enabled: bool = True
    status: Optional[str] = None


class CreateRunRequest(BaseModel):
    query: str
    constraints: AtelierConstraints = Field(default_factory=AtelierConstraints)
    steps: List[PlanStepIn]


class PatchRunRequest(BaseModel):
    constraints: Optional[Dict[str, Any]] = None
    steps: Optional[List[PlanStepIn]] = None
    drama_id: Optional[str] = None


class StartStepRequest(BaseModel):
    drama_id: Optional[str] = None
    user_id: str = "default_user"
    session_id: Optional[str] = None
    model_provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None


class PreflightRequest(BaseModel):
    user_id: str = "default_user"
    query: Optional[str] = None
    force: bool = False


def _sse(event: Dict[str, Any]) -> str:
    payload = {
        "event": event.get("event_type") or event.get("event") or "message",
        "data": {
            "content": event.get("data"),
            "metadata": event.get("metadata") or {},
        },
    }
    # complete 事件保留结构化 data
    if payload["event"] == "complete" and isinstance(event.get("data"), dict):
        payload["data"] = event["data"]
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/plan")
async def propose_plan(req: ProposePlanRequest):
    if not (req.query or "").strip():
        raise HTTPException(status_code=400, detail="query 不能为空")
    plan = atelier.propose_plan(req.query, req.constraints.model_dump())
    return {"success": True, "plan": plan}


@router.post("/runs")
async def create_run(req: CreateRunRequest):
    if not (req.query or "").strip():
        raise HTTPException(status_code=400, detail="query 不能为空")
    try:
        run = await atelier.create_run(
            req.query,
            req.constraints.model_dump(),
            [s.model_dump() for s in req.steps],
        )
        return {"success": True, "run": run}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("创建 atelier run 失败")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runs/{run_id}")
async def get_run(run_id: str, drama_id: Optional[str] = None):
    run = await atelier.load_run(run_id, drama_id=drama_id)
    if not run:
        raise HTTPException(status_code=404, detail="编排任务不存在")
    return {"success": True, "run": run}


@router.get("/dramas/{drama_id}/run")
async def get_run_by_drama(drama_id: str, request: Request = None):
    await ensure_owner(drama_id, auth_uid(request) if request else None)
    run = await atelier.load_run_for_drama(drama_id)
    if not run:
        raise HTTPException(status_code=404, detail="该作品暂无编排任务")
    return {"success": True, "run": run}


@router.patch("/runs/{run_id}")
async def patch_run(run_id: str, req: PatchRunRequest):
    try:
        steps = [s.model_dump() for s in req.steps] if req.steps is not None else None
        run = await atelier.patch_run(
            run_id,
            constraints=req.constraints,
            steps=steps,
            drama_id=req.drama_id,
        )
        return {"success": True, "run": run}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("更新 atelier run 失败")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/runs/{run_id}/steps/{step_id}/start")
async def start_step(run_id: str, step_id: str, req: StartStepRequest, request: Request = None):
    uid = auth_uid(request) if request else None
    if req.drama_id:
        await ensure_owner(req.drama_id, uid)
    async def generate():
        try:
            async for event in atelier.execute_step(
                run_id,
                step_id,
                drama_id=req.drama_id,
                user_id=uid or req.user_id,
                session_id=req.session_id,
                model_provider=req.model_provider,
                model=req.model,
                api_key=req.api_key,
                base_url=req.base_url,
            ):
                yield _sse(event)
        except Exception as e:
            logger.exception("步骤 SSE 失败")
            yield _sse({"event_type": "error", "data": str(e)})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/catalog")
async def get_catalog():
    return {"success": True, "steps": atelier.STEP_CATALOG}


@router.post("/dramas/{drama_id}/preflight")
async def start_preflight(drama_id: str, req: PreflightRequest, request: Request = None):
    """一键启动前置创作（策划·知识设定·人物·情节点），后台顺序执行并落盘到作品。"""
    uid = auth_uid(request) if request else None
    await ensure_owner(drama_id, uid)
    try:
        run = await atelier.start_preflight(drama_id, user_id=uid or req.user_id, query=req.query, force=req.force)
        return {"success": True, "run": run}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("启动前置创作失败")
        raise HTTPException(status_code=500, detail=str(e))
