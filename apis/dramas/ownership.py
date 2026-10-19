"""多租户归属校验共享 helper — 认证中间件注入的 user_id 覆盖请求体、强制资源归属。

未启用认证（AUTH_ENABLED=false）时 auth_uid 返回 None，归属校验自动放行以保持开发兼容。
"""
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, Request

from utils.drama_manager import get_drama_manager


def auth_uid(request: Request) -> Optional[str]:
    """认证中间件注入的真实 user_id；未启用认证时返回 None。"""
    return getattr(request.state, "user_id", None) or None


async def ensure_owner(drama_id: str, uid: Optional[str]) -> None:
    """多租户归属校验：仅在认证用户存在时强制，避免越权读改删他人作品。"""
    if not uid:
        return
    try:
        meta = await get_drama_manager()._load_meta(drama_id)
    except ValueError:
        # 非法 id（路径穿越等）交由后续 404 处理
        return
    if meta and meta.get("user_id") and meta.get("user_id") != uid:
        raise HTTPException(status_code=403, detail="无权访问该作品")
