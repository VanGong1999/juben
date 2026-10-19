"""
个性化记忆 API 路由
提供用户画像管理和风格编辑分析的接口

端点：
- POST   /juben/user/profile           # 更新用户画像
- GET    /juben/user/profile/{uid}     # 获取用户画像
- POST   /juben/user/style/analyze     # 分析风格编辑
- POST   /juben/user/style/save        # 保存用户风格编辑
- GET    /juben/user/style/examples    # 获取用户风格示例

代码作者：Claude
创建时间：2026年2月7日
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

from utils.memory_manager import (
    get_user_profile_manager,
    get_style_memory,
    UserProfile,
    save_user_style_edit,
    get_user_style_examples,
    get_unified_memory_manager
)
from utils.memory_settings import get_memory_settings_manager
from utils.memory_audit import get_memory_audit_manager
from utils.style_analyzer import (
    get_style_analyzer,
    analyze_style_edit,
    ModificationIntent,
    StyleFeature
)
from utils.llm_client import get_llm_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/juben/user", tags=["个性化记忆"])


# ==================== 请求/响应模型 ====================

class UserProfileUpdate(BaseModel):
    """用户画像更新请求"""
    user_id: str = Field(..., description="用户ID")
    fav_genres: Optional[List[str]] = Field(None, description="偏好题材")
    avoid_tropes: Optional[List[str]] = Field(None, description="讨厌的桥段")
    language_style: Optional[List[str]] = Field(None, description="语言风格标签")


class UserProfileResponse(BaseModel):
    """用户画像响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class StyleAnalyzeRequest(BaseModel):
    """风格分析请求"""
    user_id: str = Field(..., description="用户ID")
    session_id: str = Field(..., description="会话ID")
    original_text: str = Field(..., description="AI生成的原文")
    modified_text: str = Field(..., description="用户修改后的文本")
    context: str = Field(default="", description="上下文信息")
    save_to_memory: bool = Field(True, description="是否保存到向量库")


class StyleAnalyzeResponse(BaseModel):
    """风格分析响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class StyleSaveRequest(BaseModel):
    """风格保存请求"""
    user_id: str = Field(..., description="用户ID")
    session_id: str = Field(..., description="会话ID")
    original_text: str = Field(..., description="AI生成的原文")
    modified_text: str = Field(..., description="用户修改后的文本")
    context: str = Field(default="", description="上下文信息")
    analysis_result: Dict[str, Any] = Field(..., description="风格分析结果")
    artifact_id: Optional[str] = Field(None, description="关联的Artifact ID")


class StyleExamplesRequest(BaseModel):
    """风格示例请求"""
    user_id: str = Field(..., description="用户ID")
    query_text: str = Field(..., description="查询文本")
    count: int = Field(3, ge=1, le=10, description="返回数量")


class StyleExamplesResponse(BaseModel):
    """风格示例响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class MemoryMetricsResponse(BaseModel):
    """记忆指标响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class MemorySettingsRequest(BaseModel):
    user_id: str = Field(..., description="用户ID")
    project_id: Optional[str] = Field(default=None, description="项目ID")
    user_enabled: Optional[bool] = Field(default=None, description="用户维度开关")
    project_enabled: Optional[bool] = Field(default=None, description="项目维度开关")


class MemorySettingsResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class MemorySnapshotRequest(BaseModel):
    user_id: str = Field(..., description="用户ID")
    session_id: str = Field(..., description="会话ID")
    project_id: Optional[str] = Field(default=None, description="项目ID")
    label: Optional[str] = Field(default=None, description="快照标签")


class MemorySnapshotRestoreRequest(BaseModel):
    user_id: str = Field(..., description="用户ID")
    session_id: str = Field(..., description="会话ID")


class MemoryQualityResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ==================== 用户画像 API ====================

@router.post("/profile")
async def update_user_profile(request: UserProfileUpdate) -> UserProfileResponse:
    """
    更新用户画像

    支持更新以下字段：
    - fav_genres: 偏好题材（如：都市、古装、悬疑、甜宠）
    - avoid_tropes: 讨厌的桥段（如：三角恋、重生、穿越）
    - language_style: 语言风格标签（如：formal, casual, literary）

    Example:
    ```json
    {
      "user_id": "user123",
      "fav_genres": ["都市", "悬疑"],
      "avoid_tropes": ["三角恋"],
      "language_style": ["casual", "humorous"]
    }
    ```
    """
    try:
        manager = get_user_profile_manager()

        # 获取或创建画像
        profile = await manager.get_profile(request.user_id)
        if not profile:
            profile = await manager.create_profile(request.user_id)

        # 更新字段
        success = await manager.update_preferences(
            user_id=request.user_id,
            fav_genres=request.fav_genres,
            avoid_tropes=request.avoid_tropes,
            language_style=request.language_style
        )

        if success:
            # 获取更新后的画像
            updated_profile = await manager.get_profile(request.user_id)
            # 同步到五层记忆 USER.md（常驻画像）
            try:
                from utils.agent_memory import get_agent_memory_service

                if updated_profile:
                    get_agent_memory_service().sync_user_profile_to_resident(
                        request.user_id, updated_profile.to_dict()
                    )
            except Exception as sync_err:
                logger.warning(f"同步 USER.md 失败: {sync_err}")
            return UserProfileResponse(
                success=True,
                data=updated_profile.to_dict() if updated_profile else None
            )
        else:
            raise HTTPException(status_code=500, detail="更新失败")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新用户画像失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profile/{user_id}")
async def get_user_profile(user_id: str) -> UserProfileResponse:
    """
    获取用户画像

    返回用户的偏好设置，包括：
    - fav_genres: 偏好题材
    - avoid_tropes: 讨厌的桥段
    - language_style: 语言风格标签
    - total_edits: 总编辑次数
    - total_scripts: 总剧本数量
    """
    try:
        manager = get_user_profile_manager()
        profile = await manager.get_profile(user_id)

        if not profile:
            # 自动创建新画像
            profile = await manager.create_profile(user_id)

        return UserProfileResponse(
            success=True,
            data=profile.to_dict()
        )

    except Exception as e:
        logger.error(f"获取用户画像失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/metrics")
async def get_memory_metrics(
    user_id: str = Query(..., description="用户ID"),
    session_id: str = Query(..., description="会话ID"),
    query: Optional[str] = Query("", description="当前查询")
) -> MemoryMetricsResponse:
    """
    获取记忆质量指标
    """
    try:
        manager = get_unified_memory_manager()
        data = await manager.get_memory_metrics(
            user_id=user_id,
            session_id=session_id,
            current_query=query or ""
        )
        return MemoryMetricsResponse(success=True, data=data)
    except Exception as e:
        logger.error(f"获取记忆指标失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/settings")
async def get_memory_settings(
    user_id: str = Query(..., description="用户ID"),
    project_id: Optional[str] = Query(default=None, description="项目ID")
) -> MemorySettingsResponse:
    try:
        settings = get_memory_settings_manager().get_settings(user_id, project_id)
        return MemorySettingsResponse(
            success=True,
            data={
                "user_enabled": settings.user_enabled,
                "project_enabled": settings.project_enabled,
                "effective_enabled": settings.effective_enabled,
                "updated_at": settings.updated_at
            }
        )
    except Exception as e:
        logger.error(f"获取记忆设置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory/settings")
async def update_memory_settings(request: MemorySettingsRequest) -> MemorySettingsResponse:
    try:
        manager = get_memory_settings_manager()
        result = None
        if request.user_enabled is not None:
            result = manager.set_user_enabled(request.user_id, request.user_enabled)
        if request.project_id and request.project_enabled is not None:
            result = manager.set_project_enabled(request.project_id, request.project_enabled, request.user_id)
        if result is None:
            result = manager.get_settings(request.user_id, request.project_id)
        return MemorySettingsResponse(
            success=True,
            data={
                "user_enabled": result.user_enabled,
                "project_enabled": result.project_enabled,
                "effective_enabled": result.effective_enabled,
                "updated_at": result.updated_at
            }
        )
    except Exception as e:
        logger.error(f"更新记忆设置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory/snapshots")
async def create_memory_snapshot(request: MemorySnapshotRequest):
    try:
        manager = get_memory_audit_manager()
        snapshot = await manager.create_snapshot(
            request.user_id, request.session_id, request.project_id, request.label
        )
        return {"success": True, "data": snapshot}
    except Exception as e:
        logger.error(f"创建记忆快照失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/snapshots")
async def list_memory_snapshots(
    user_id: str = Query(..., description="用户ID"),
    session_id: str = Query(..., description="会话ID"),
    project_id: Optional[str] = Query(default=None, description="项目ID")
):
    try:
        manager = get_memory_audit_manager()
        return {"success": True, "data": manager.list_snapshots(user_id, session_id, project_id)}
    except Exception as e:
        logger.error(f"获取记忆快照失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory/snapshots/{snapshot_id}/restore")
async def restore_memory_snapshot(snapshot_id: str, request: MemorySnapshotRestoreRequest):
    try:
        manager = get_memory_audit_manager()
        snapshot = await manager.restore_snapshot(snapshot_id, request.user_id, request.session_id)
        return {"success": True, "data": snapshot}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"回滚记忆快照失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/quality")
async def get_memory_quality(
    user_id: str = Query(..., description="用户ID"),
    session_id: str = Query(..., description="会话ID"),
    query: Optional[str] = Query("", description="查询文本")
) -> MemoryQualityResponse:
    try:
        manager = get_memory_audit_manager()
        result = await manager.evaluate_quality(user_id, session_id, query)
        return MemoryQualityResponse(success=True, data=result)
    except Exception as e:
        logger.error(f"获取记忆质量失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 风格分析 API ====================

@router.post("/style/analyze")
async def analyze_style_edit(request: StyleAnalyzeRequest) -> StyleAnalyzeResponse:
    """
    分析风格编辑

    对比AI原文与用户修改文，提取：
    - 修改意图（add_detail, enhance_emotion等）
    - 风格特征（descriptive, emotional等）
    - 写作模式（句子长度、词汇类型等）
    - 词汇偏好

    如果 save_to_memory=true，会自动保存到向量库
    """
    try:
        # 获取LLM客户端用于智能分析
        llm_client = get_llm_client()

        # 执行风格分析
        result = await analyze_style_edit(
            original_text=request.original_text,
            modified_text=request.modified_text,
            user_id=request.user_id,
            session_id=request.session_id,
            llm_client=llm_client
        )

        # 如果需要，保存到向量库
        saved = False
        if request.save_to_memory:
            saved = await save_user_style_edit(
                user_id=request.user_id,
                session_id=request.session_id,
                original_text=request.original_text,
                modified_text=request.modified_text,
                context=request.context,
                analysis_result=result.to_dict(),
                artifact_id=None
            )

            # 更新编辑计数
            manager = get_user_profile_manager()
            await manager.increment_edits(request.user_id)

        return StyleAnalyzeResponse(
            success=True,
            data={
                "analysis": result.to_dict(),
                "saved_to_memory": saved
            }
        )

    except Exception as e:
        logger.error(f"风格分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/style/save")
async def save_style_edit(request: StyleSaveRequest) -> Dict[str, Any]:
    """
    保存风格编辑到向量库

    将用户编辑的内容及其分析结果保存到Milvus向量库，
    用于后续的个性化风格检索和注入。
    """
    try:
        saved = await save_user_style_edit(
            user_id=request.user_id,
            session_id=request.session_id,
            original_text=request.original_text,
            modified_text=request.modified_text,
            context=request.context,
            analysis_result=request.analysis_result,
            artifact_id=request.artifact_id
        )

        # 更新编辑计数
        manager = get_user_profile_manager()
        await manager.increment_edits(request.user_id)

        return {
            "success": True,
            "saved": saved,
            "message": "风格片段已保存到向量库"
        }

    except Exception as e:
        logger.error(f"保存风格编辑失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/style/examples")
async def get_style_examples(
    user_id: str = Query(..., description="用户ID"),
    query_text: str = Query(..., description="查询文本"),
    count: int = Query(3, ge=1, le=10, description="返回数量")
) -> StyleExamplesResponse:
    """
    获取用户风格示例

    从向量库中检索与查询文本最相似的用户历史编辑片段，
    返回可作为Few-Shot Examples使用的风格示例。
    """
    try:
        examples = await get_user_style_examples(
            user_id=user_id,
            query_text=query_text,
            count=count
        )

        return StyleExamplesResponse(
            success=True,
            data={
                "examples": examples,
                "count": len(examples)
            }
        )

    except Exception as e:
        logger.error(f"获取风格示例失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 批量操作 API ====================

@router.post("/style/batch")
async def batch_analyze_style(
    requests: List[StyleAnalyzeRequest],
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    批量分析风格编辑

    支持一次性分析多个编辑片段，适合批量处理场景。
    """
    try:
        results = []
        llm_client = get_llm_client()

        for req in requests:
            try:
                result = await analyze_style_edit(
                    original_text=req.original_text,
                    modified_text=req.modified_text,
                    user_id=req.user_id,
                    session_id=req.session_id,
                    llm_client=llm_client
                )

                saved = False
                if req.save_to_memory:
                    saved = await save_user_style_edit(
                        user_id=req.user_id,
                        session_id=req.session_id,
                        original_text=req.original_text,
                        modified_text=req.modified_text,
                        context=req.context,
                        analysis_result=result.to_dict(),
                        artifact_id=None
                    )

                results.append({
                    "user_id": req.user_id,
                    "session_id": req.session_id,
                    "success": True,
                    "analysis": result.to_dict(),
                    "saved": saved
                })

            except Exception as e:
                logger.error(f"分析失败 (user: {req.user_id}): {e}")
                results.append({
                    "user_id": req.user_id,
                    "session_id": req.session_id,
                    "success": False,
                    "error": str(e)
                })

        return {
            "success": True,
            "total": len(requests),
            "results": results
        }

    except Exception as e:
        logger.error(f"批量分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 统计 API ====================

@router.get("/statistics/{user_id}")
async def get_user_statistics(user_id: str) -> Dict[str, Any]:
    """
    获取用户统计信息

    返回：
    - total_edits: 总编辑次数
    - total_scripts: 总剧本数量
    - style_fragments_count: 风格片段数量
    - profile_created_at: 画像创建时间
    - profile_updated_at: 画像更新时间
    """
    try:
        manager = get_user_profile_manager()
        profile = await manager.get_profile(user_id)

        if not profile:
            raise HTTPException(status_code=404, detail="用户不存在")

        # 获取风格片段数量
        style_memory = get_style_memory()
        fragments = await style_memory.get_user_fragments(user_id, limit=1000)

        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "total_edits": profile.total_edits,
                "total_scripts": profile.total_scripts,
                "style_fragments_count": len(fragments),
                "fav_genres": profile.fav_genres,
                "avoid_tropes": profile.avoid_tropes,
                "language_style": profile.language_style,
                "profile_created_at": profile.created_at,
                "profile_updated_at": profile.updated_at
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 五层 Agent Memory（生产级） ====================

class AgentMemoryAssembleRequest(BaseModel):
    user_id: str
    drama_id: Optional[str] = None
    query: str = ""
    budget_chars: int = 8000


class AgentMemoryFactRequest(BaseModel):
    drama_id: str
    entity_type: str
    entity_id: str
    predicate: str
    value: Any
    confidence: str = "fact"
    user_id: Optional[str] = None
    pinned: bool = False
    expected_version: Optional[int] = None


class AgentMemoryEpisodeRequest(BaseModel):
    user_id: str
    agent_id: str
    task_description: str
    drama_id: Optional[str] = None
    session_id: Optional[str] = None
    outcome: str = "success"
    approach: str = ""
    resolution: str = ""
    tags: Optional[List[str]] = None


class AgentMemoryTextRequest(BaseModel):
    content: str
    expected_version: Optional[str] = None
    session_id: Optional[str] = None


@router.get("/agent-memory/overview")
async def agent_memory_overview(
    user_id: str = Query(...),
    drama_id: Optional[str] = Query(None),
):
    """五层记忆总览：规则/常驻/情节/语义/程序 + 本体"""
    try:
        from utils.agent_memory import get_agent_memory_service

        return {"success": True, "data": get_agent_memory_service().overview(user_id, drama_id)}
    except Exception as e:
        logger.error(f"agent memory overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent-memory/assemble")
async def agent_memory_assemble(request: AgentMemoryAssembleRequest):
    """组装工作记忆注入块（受预算约束）"""
    try:
        from utils.agent_memory import get_agent_memory_service

        bundle = get_agent_memory_service().assemble_working_memory(
            user_id=request.user_id,
            drama_id=request.drama_id,
            query=request.query,
            budget_chars=request.budget_chars,
        )
        return {"success": True, "data": bundle.to_dict()}
    except Exception as e:
        logger.error(f"agent memory assemble: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent-memory/rules/{drama_id}")
async def get_drama_rules(drama_id: str):
    from utils.agent_memory import get_agent_memory_service

    return {"success": True, "data": {"content": get_agent_memory_service().get_rules(drama_id)}}


@router.put("/agent-memory/rules/{drama_id}")
async def put_drama_rules(drama_id: str, request: AgentMemoryTextRequest):
    from utils.agent_memory import get_agent_memory_service

    try:
        result = get_agent_memory_service().set_rules(
            drama_id, request.content, expected_version=request.expected_version, session_id=request.session_id
        )
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/agent-memory/resident")
async def get_resident(
    user_id: str = Query(...),
    drama_id: Optional[str] = Query(None),
):
    from utils.agent_memory import get_agent_memory_service

    svc = get_agent_memory_service()
    return {
        "success": True,
        "data": {
            "user_md": svc.get_user_resident(user_id),
            "memory_md": svc.get_drama_resident(drama_id) if drama_id else "",
        },
    }


@router.put("/agent-memory/resident/user/{user_id}")
async def put_user_resident(user_id: str, request: AgentMemoryTextRequest):
    from utils.agent_memory import get_agent_memory_service

    try:
        result = get_agent_memory_service().set_user_resident(
            user_id, request.content, expected_version=request.expected_version, session_id=request.session_id
        )
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/agent-memory/resident/drama/{drama_id}")
async def put_drama_resident(drama_id: str, request: AgentMemoryTextRequest):
    from utils.agent_memory import get_agent_memory_service

    try:
        result = get_agent_memory_service().set_drama_resident(
            drama_id, request.content, expected_version=request.expected_version, session_id=request.session_id
        )
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/agent-memory/episodes/{drama_id}")
async def list_memory_episodes(
    drama_id: str,
    limit: int = Query(50, ge=1, le=200),
    q: Optional[str] = Query(None),
):
    from utils.agent_memory import get_agent_memory_service

    svc = get_agent_memory_service()
    data = svc.search_episodes(drama_id, q or "", top_k=limit) if q else svc.list_episodes(drama_id, limit=limit)
    return {"success": True, "data": data, "total": len(data)}


@router.post("/agent-memory/episodes")
async def create_memory_episode(request: AgentMemoryEpisodeRequest):
    from utils.agent_memory import get_agent_memory_service

    ep = get_agent_memory_service().record_agent_turn(
        user_id=request.user_id,
        agent_id=request.agent_id,
        task_description=request.task_description,
        drama_id=request.drama_id,
        session_id=request.session_id,
        outcome=request.outcome,
        approach=request.approach,
        resolution=request.resolution,
        tags=request.tags,
    )
    return {"success": True, "data": ep.to_dict()}


@router.get("/agent-memory/facts/{drama_id}")
async def list_memory_facts(
    drama_id: str,
    q: Optional[str] = Query(None),
    active_only: bool = Query(True),
):
    from utils.agent_memory import get_agent_memory_service

    svc = get_agent_memory_service()
    data = svc.search_facts(drama_id, q or "", top_k=50) if q else svc.list_facts(drama_id, active_only=active_only)
    return {"success": True, "data": data, "total": len(data)}


@router.post("/agent-memory/facts")
async def upsert_memory_fact(request: AgentMemoryFactRequest):
    from utils.agent_memory import get_agent_memory_service

    try:
        fact = get_agent_memory_service().upsert_fact(
            drama_id=request.drama_id,
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            predicate=request.predicate,
            value=request.value,
            confidence=request.confidence,
            user_id=request.user_id,
            pinned=request.pinned,
            expected_version=request.expected_version,
        )
        if isinstance(fact, dict) and fact.get("conflict"):
            return {"success": False, "conflict": True, "data": fact}
        return {"success": True, "data": fact}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/agent-memory/forget/{drama_id}")
async def run_memory_forgetting(drama_id: str):
    from utils.agent_memory import get_agent_memory_service

    return {"success": True, "data": get_agent_memory_service().run_forgetting(drama_id)}


@router.post("/agent-memory/dream/{drama_id}")
async def run_memory_dream(
    drama_id: str,
    user_id: Optional[str] = Query(None),
    auto_promote: bool = Query(True),
    compress_resident: bool = Query(True),
):
    """空闲离线整理：遗忘 + 反思沉淀 + MEMORY 压缩 + 技能晋升 + 向量重建。"""
    from utils.agent_memory import get_agent_memory_service

    data = get_agent_memory_service().run_dream(
        drama_id,
        user_id=user_id,
        auto_promote=auto_promote,
        compress_resident=compress_resident,
    )
    return {"success": True, "data": data}


@router.post("/agent-memory/promote-skill/{drama_id}")
async def promote_memory_skill(
    drama_id: str,
    name: str = Query(...),
    trigger: str = Query(...),
    min_success: int = Query(3, ge=2, le=20),
):
    from utils.agent_memory import get_agent_memory_service

    skill = get_agent_memory_service().promote_skill_from_episodes(
        drama_id, name=name, trigger=trigger, min_success=min_success
    )
    if not skill:
        return {"success": False, "error": f"成功次数不足 {min_success}，未晋升"}
    return {"success": True, "data": skill}


@router.get("/agent-memory/skills/{drama_id}")
async def list_memory_skills(
    drama_id: str,
    enabled_only: bool = Query(False),
):
    from utils.agent_memory import get_agent_memory_service

    data = get_agent_memory_service().list_promoted_skills(drama_id, enabled_only=enabled_only)
    return {"success": True, "data": data, "total": len(data)}


class SkillToggleRequest(BaseModel):
    enabled: bool
    user_id: Optional[str] = None


@router.patch("/agent-memory/skills/{drama_id}/{skill_id}")
async def toggle_memory_skill(drama_id: str, skill_id: str, request: SkillToggleRequest):
    from utils.agent_memory import get_agent_memory_service

    ok = get_agent_memory_service().set_skill_enabled(
        drama_id, skill_id, request.enabled, user_id=request.user_id
    )
    if not ok:
        raise HTTPException(status_code=404, detail="skill not found")
    return {"success": True}


@router.delete("/agent-memory/skills/{drama_id}/{skill_id}")
async def delete_memory_skill(
    drama_id: str,
    skill_id: str,
    user_id: Optional[str] = Query(None),
):
    from utils.agent_memory import get_agent_memory_service

    ok = get_agent_memory_service().delete_skill(drama_id, skill_id, user_id=user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="skill not found")
    return {"success": True}


class FactPatchRequest(BaseModel):
    value: Optional[Any] = None
    confidence: Optional[str] = None
    pinned: Optional[bool] = None
    status: Optional[str] = None
    user_id: Optional[str] = None
    expected_version: Optional[int] = None


@router.patch("/agent-memory/facts/{drama_id}/{fact_id}")
async def patch_memory_fact(drama_id: str, fact_id: str, request: FactPatchRequest):
    from utils.agent_memory import get_agent_memory_service

    fact = get_agent_memory_service().update_fact(
        drama_id,
        fact_id,
        value=request.value,
        confidence=request.confidence,
        pinned=request.pinned,
        status=request.status,
        user_id=request.user_id,
        expected_version=request.expected_version,
    )
    if not fact:
        raise HTTPException(status_code=404, detail="fact not found")
    if isinstance(fact, dict) and fact.get("conflict"):
        return {"success": False, "conflict": True, "data": fact}
    return {"success": True, "data": fact}


@router.delete("/agent-memory/facts/{drama_id}/{fact_id}")
async def delete_memory_fact(
    drama_id: str,
    fact_id: str,
    user_id: Optional[str] = Query(None),
    hard: bool = Query(False),
):
    from utils.agent_memory import get_agent_memory_service

    ok = get_agent_memory_service().delete_fact(drama_id, fact_id, user_id=user_id, hard=hard)
    if not ok:
        raise HTTPException(status_code=404, detail="fact not found")
    return {"success": True}


@router.get("/agent-memory/episodes/{drama_id}/{episode_id}")
async def get_memory_episode(drama_id: str, episode_id: str):
    from utils.agent_memory import get_agent_memory_service

    ep = get_agent_memory_service().get_episode(drama_id, episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="episode not found")
    return {"success": True, "data": ep}


@router.delete("/agent-memory/episodes/{drama_id}/{episode_id}")
async def delete_memory_episode(
    drama_id: str,
    episode_id: str,
    user_id: Optional[str] = Query(None),
):
    from utils.agent_memory import get_agent_memory_service

    ok = get_agent_memory_service().soft_delete_episode(drama_id, episode_id, user_id=user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="episode not found")
    return {"success": True}


class EpisodePinRequest(BaseModel):
    pinned: bool = True


@router.post("/agent-memory/episodes/{drama_id}/{episode_id}/pin")
async def pin_memory_episode(drama_id: str, episode_id: str, request: EpisodePinRequest):
    from utils.agent_memory import get_agent_memory_service

    ok = get_agent_memory_service().pin_episode(drama_id, episode_id, request.pinned)
    if not ok:
        raise HTTPException(status_code=404, detail="episode not found")
    return {"success": True}


@router.post("/agent-memory/episodes/{drama_id}/{episode_id}/reflect")
async def reflect_memory_episode(
    drama_id: str,
    episode_id: str,
    user_id: Optional[str] = Query(None),
):
    from utils.agent_memory import get_agent_memory_service

    ref = get_agent_memory_service().reflect_on_episode(drama_id, episode_id, user_id=user_id)
    if not ref:
        raise HTTPException(status_code=404, detail="episode not found")
    return {"success": True, "data": ref}


@router.get("/agent-memory/reflections/{drama_id}")
async def list_memory_reflections(drama_id: str, limit: int = Query(50, ge=1, le=200)):
    from utils.agent_memory import get_agent_memory_service

    data = get_agent_memory_service().list_reflections(drama_id, limit=limit)
    return {"success": True, "data": data, "total": len(data)}


@router.get("/agent-memory/audit/{drama_id}")
async def list_memory_audit(drama_id: str, limit: int = Query(100, ge=1, le=500)):
    from utils.agent_memory import get_agent_memory_service

    data = get_agent_memory_service().list_audit(drama_id, limit=limit)
    return {"success": True, "data": data, "total": len(data)}


@router.get("/agent-memory/slice/{drama_id}")
async def read_memory_slice(
    drama_id: str,
    path: str = Query(..., description="相对 memory/ 的路径，如 topics/foo.md"),
    offset: int = Query(0, ge=0),
    length: int = Query(2000, ge=1, le=20000),
):
    from utils.agent_memory import get_agent_memory_service

    try:
        data = get_agent_memory_service().read_memory_slice(
            drama_id, relative_path=path, offset=offset, length=length
        )
        return {"success": True, "data": data}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="file not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/agent-memory/reindex/{drama_id}")
async def reindex_memory_vectors(drama_id: str):
    from utils.agent_memory import get_agent_memory_service

    return {"success": True, "data": get_agent_memory_service().rebuild_vector_index(drama_id)}


@router.get("/agent-memory/search/{drama_id}")
async def search_memory_hybrid(
    drama_id: str,
    q: str = Query(...),
    top_k: int = Query(8, ge=1, le=30),
    layer: Optional[str] = Query(None),
):
    """混合检索：向量 ANN + 关键词（对齐架构图 Working Memory 注入）。"""
    from utils.agent_memory import get_agent_memory_service

    svc = get_agent_memory_service()
    return {
        "success": True,
        "data": {
            "vector": svc.vector_search(drama_id, q, top_k=top_k, layer=layer),
            "episodic": svc.search_episodes(drama_id, q, top_k=top_k) if layer in (None, "episodic", "all") else [],
            "semantic": svc.search_facts(drama_id, q, top_k=top_k) if layer in (None, "semantic", "all") else [],
        },
    }


# ==================== 版本链 / 导出 / 脱敏 / Org ====================

@router.get("/agent-memory/versions/{drama_id}")
async def list_memory_versions(drama_id: str, target: Optional[str] = Query(None)):
    from utils.agent_memory import get_agent_memory_service

    data = get_agent_memory_service().list_memory_versions(drama_id, target=target)
    return {"success": True, "data": data, "total": len(data)}


@router.get("/agent-memory/versions/{drama_id}/{version_id}")
async def get_memory_version(drama_id: str, version_id: str):
    from utils.agent_memory import get_agent_memory_service

    data = get_agent_memory_service().get_memory_version(drama_id, version_id)
    if not data:
        raise HTTPException(status_code=404, detail="version not found")
    return {"success": True, "data": data}


@router.get("/agent-memory/versions/{drama_id}/{version_id}/diff")
async def diff_memory_version(drama_id: str, version_id: str):
    from utils.agent_memory import get_agent_memory_service

    diff = get_agent_memory_service().diff_memory_version(drama_id, version_id)
    return {"success": True, "data": {"version_id": version_id, "diff": diff}}


@router.post("/agent-memory/versions/{drama_id}/{version_id}/rollback")
async def rollback_memory_version(drama_id: str, version_id: str):
    from utils.agent_memory import get_agent_memory_service

    try:
        result = get_agent_memory_service().rollback_memory_version(drama_id, version_id)
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/agent-memory/export/{drama_id}")
async def export_agent_memory(drama_id: str):
    from utils.agent_memory import get_agent_memory_service

    return {"success": True, "data": get_agent_memory_service().export_memory(drama_id)}


class RedactRequest(BaseModel):
    preview: bool = True


@router.post("/agent-memory/redact/{drama_id}")
async def redact_agent_memory(drama_id: str, request: RedactRequest):
    from utils.agent_memory import get_agent_memory_service

    return {"success": True, "data": get_agent_memory_service().redact_memory(drama_id, preview=request.preview)}


@router.get("/agent-memory/org")
async def get_org_memory():
    from utils.agent_memory import get_agent_memory_service

    svc = get_agent_memory_service()
    return {
        "success": True,
        "data": {
            "resident": svc.get_org_resident(),
            "facts": svc.list_org_facts(active_only=False),
            "versions": svc.list_org_versions(),
        },
    }


class OrgResidentRequest(BaseModel):
    content: str
    expected_version: Optional[str] = None
    session_id: Optional[str] = None


@router.post("/agent-memory/org/resident")
async def set_org_resident(request: OrgResidentRequest):
    from utils.agent_memory import get_agent_memory_service

    try:
        result = get_agent_memory_service().set_org_resident(
            request.content, expected_version=request.expected_version, session_id=request.session_id
        )
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class OrgFactRequest(BaseModel):
    entity_type: str
    entity_id: str
    predicate: str
    value: Any
    confidence: str = "fact"
    pinned: bool = False


@router.post("/agent-memory/org/facts")
async def upsert_org_fact(request: OrgFactRequest):
    from utils.agent_memory import get_agent_memory_service

    try:
        fact = get_agent_memory_service().upsert_org_fact(
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            predicate=request.predicate,
            value=request.value,
            confidence=request.confidence,
            pinned=request.pinned,
        )
        return {"success": True, "data": fact}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/agent-memory/org/dream")
async def run_org_dream():
    from utils.agent_memory import get_agent_memory_service

    return {"success": True, "data": get_agent_memory_service().run_org_dream()}
