"""
作品剧本库 API — 上传 / 列表 / grep / 向量检索
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from apis.dramas.ownership import auth_uid, ensure_owner
from utils.script_library import ALLOWED_EXT, get_script_library

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/juben/dramas", tags=["drama-scripts"])


class ScriptSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    mode: str = Field(default="hybrid", description="grep | vector | hybrid")
    doc_id: Optional[str] = None
    top_k: int = Field(default=10, ge=1, le=50)
    case_insensitive: bool = True


@router.get("/{drama_id}/scripts")
async def list_scripts(drama_id: str, request: Request):
    await ensure_owner(drama_id, auth_uid(request))
    lib = get_script_library()
    try:
        items = await lib.list_docs(drama_id)
        return {"success": True, "scripts": items, "total": len(items)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("列出剧本失败")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{drama_id}/scripts/upload")
async def upload_script(
    drama_id: str,
    file: UploadFile = File(...),
    title: Optional[str] = Form(default=None),
    tags: Optional[str] = Form(default="script,upload"),
    user_id: str = Form(default="default_user"),
    request: Request = None,
):
    uid = auth_uid(request) if request else None
    await ensure_owner(drama_id, uid)
    lib = get_script_library()
    try:
        raw = await file.read()
        tag_list = [t.strip() for t in (tags or "").split(",") if t.strip()]
        meta = await lib.save_upload(
            drama_id,
            filename=file.filename or "script.txt",
            raw=raw,
            title=title,
            tags=tag_list,
            user_id=uid or user_id,
        )
        return {
            "success": True,
            "script": meta,
            "message": f"已入库并分块索引（{meta.get('chunk_count', 0)} 块）",
            "allowed_ext": sorted(ALLOWED_EXT),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("上传剧本失败")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{drama_id}/scripts/{doc_id}")
async def get_script(drama_id: str, doc_id: str, include_content: bool = True, request: Request = None):
    await ensure_owner(drama_id, auth_uid(request) if request else None)
    lib = get_script_library()
    try:
        doc = await lib.get_doc(drama_id, doc_id, include_content=include_content)
        return {"success": True, "script": doc}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("获取剧本失败")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{drama_id}/scripts/{doc_id}")
async def delete_script(drama_id: str, doc_id: str, request: Request = None):
    await ensure_owner(drama_id, auth_uid(request) if request else None)
    lib = get_script_library()
    try:
        ok = await lib.delete_doc(drama_id, doc_id)
        if not ok:
            raise HTTPException(status_code=404, detail="文档不存在")
        return {"success": True, "deleted": True}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("删除剧本失败")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{drama_id}/scripts/search")
async def search_scripts(drama_id: str, req: ScriptSearchRequest, request: Request = None):
    await ensure_owner(drama_id, auth_uid(request) if request else None)
    lib = get_script_library()
    try:
        result = await lib.search(
            drama_id,
            req.query,
            mode=req.mode,
            doc_id=req.doc_id,
            top_k=req.top_k,
            case_insensitive=req.case_insensitive,
        )
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("搜索剧本失败")
        raise HTTPException(status_code=500, detail=str(e))
