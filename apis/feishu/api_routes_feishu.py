"""
飞书集成管理路由

提供运维视角的状态查询与手动启停（WebSocket 长连接默认随应用启动自动拉起，
见 main.py startup；此处接口用于运行时观察与恢复）。
"""
from __future__ import annotations

import os
from typing import Any, Dict

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/feishu", tags=["飞书集成"])


class FeishuStatus(BaseModel):
    enabled: bool
    running: bool
    app_id_configured: bool
    app_secret_configured: bool


def _status() -> Dict[str, Any]:
    from utils.feishu_bot import get_feishu_bot
    from utils import feishu_client as fc

    bot = get_feishu_bot()
    return {
        "enabled": fc.feishu_enabled(),
        "running": bot.is_running(),
        "app_id_configured": bool(os.getenv("FEISHU_APP_ID", "").strip()),
        "app_secret_configured": bool(os.getenv("FEISHU_APP_SECRET", "").strip()),
    }


@router.get("/status", response_model=FeishuStatus)
async def status() -> FeishuStatus:
    """飞书机器人状态。"""
    return FeishuStatus(**_status())


@router.post("/start")
async def start() -> Dict[str, Any]:
    """手动启动飞书机器人。"""
    from utils.feishu_bot import get_feishu_bot

    bot = get_feishu_bot()
    bot.start()
    return {"success": True, **_status()}


@router.post("/stop")
async def stop() -> Dict[str, Any]:
    """手动停止飞书机器人。"""
    from utils.feishu_bot import get_feishu_bot

    bot = get_feishu_bot()
    bot.stop()
    return {"success": True, **_status()}


__all__ = ["router"]
