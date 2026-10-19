"""
健康检查和监控 API 路由
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any
from datetime import datetime
import psutil
import os

from utils.logger import get_logger

logger = get_logger("HealthAPI")

# 创建路由器
router = APIRouter(prefix="/health", tags=["健康检查"])


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    version: str
    timestamp: str
    uptime: float
    services: Dict[str, str]


@router.get("")
async def health_check():
    """
    基本健康检查端点

    Returns:
        健康状态
    """
    try:
        import time
        from utils.startup_validator import validate_jwt_config

        # 检查关键服务
        services = {}

        # JWT 配置检查
        jwt_ok, jwt_msg = validate_jwt_config()
        services["jwt"] = "ok" if jwt_ok else "error"

        # 数据库连接检查
        try:
            from utils.database_client import test_connection
            services["database"] = "ok" if await test_connection() else "error"
        except Exception:
            services["database"] = "error"

        # 系统资源检查
        services["memory"] = "ok" if psutil.virtual_memory().percent < 90 else "warning"
        services["disk"] = "ok" if psutil.disk_usage('/').percent < 90 else "warning"

        # 计算运行时间
        boot_time = psutil.boot_time()
        uptime = time.time() - boot_time

        # 整体状态
        overall_status = "healthy" if all(s == "ok" for s in services.values()) else "degraded"

        return HealthResponse(
            status=overall_status,
            version=os.getenv("APP_VERSION", "1.0.0"),
            timestamp=datetime.utcnow().isoformat(),
            uptime=uptime,
            services=services
        )

    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return HealthResponse(
            status="unhealthy",
            version=os.getenv("APP_VERSION", "1.0.0"),
            timestamp=datetime.utcnow().isoformat(),
            uptime=0,
            services={"error": str(e)}
        )


@router.get("/detailed")
async def detailed_health():
    """
    详细健康检查

    Returns:
        详细的健康状态信息
    """
    try:
        # CPU 信息
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()

        # 内存信息
        memory = psutil.virtual_memory()
        memory_info = {
            "total": memory.total,
            "available": memory.available,
            "percent": memory.percent,
            "used": memory.used,
            "free": memory.free
        }

        # 磁盘信息
        disk = psutil.disk_usage('/')
        disk_info = {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": disk.percent
        }

        # 进程信息
        process = psutil.Process()
        process_info = {
            "pid": process.pid,
            "memory_percent": process.memory_percent(),
            "cpu_percent": process.cpu_percent(),
            "num_threads": process.num_threads(),
            "create_time": process.create_time()
        }

        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "system": {
                "cpu": {
                    "percent": cpu_percent,
                    "count": cpu_count
                },
                "memory": memory_info,
                "disk": disk_info
            },
            "process": process_info,
            "environment": os.getenv("APP_ENV", "development")
        }

    except Exception as e:
        logger.error(f"详细健康检查失败: {str(e)}")
        raise


@router.get("/metrics")
async def metrics():
    """
    Prometheus 风格的指标端点

    Returns:
        指标数据
    """
    try:
        # 这里可以返回 Prometheus 格式的指标
        metrics = []

        # 自定义指标
        metrics.append(f"juben_api_up {int(datetime.utcnow().timestamp())}")
        metrics.append(f"juben_api_requests_total {os.getenv('REQUEST_COUNT', '0')}")

        return Response(
            content="\n".join(metrics),
            media_type="text/plain"
        )

    except Exception as e:
        logger.error(f"获取指标失败: {str(e)}")
        raise


from fastapi.responses import Response

# 导出
__all__ = ["router"]
