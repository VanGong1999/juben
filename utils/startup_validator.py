"""
启动验证模块
在应用启动前验证关键配置是否正确
"""
import os
import sys
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


class StartupValidationError(Exception):
    """启动验证错误"""
    pass


def _is_development() -> bool:
    return os.getenv("APP_ENV", "development").lower() in ("development", "dev", "local")


def validate_jwt_config() -> Tuple[bool, str]:
    """验证 JWT 配置"""
    jwt_secret = os.getenv("JWT_SECRET_KEY", "")
    default_secrets = {
        "your-secret-key-change-this-in-production-min-32-chars",
        "REPLACE_WITH_RANDOM_STRING_MIN_32_CHARS",
    }

    # 检查是否为空
    if not jwt_secret:
        return False, "JWT_SECRET_KEY 环境变量未设置"

    # 检查长度
    if len(jwt_secret) < 32:
        return False, f"JWT_SECRET_KEY 长度不足: {len(jwt_secret)} < 32"

    # 生产环境禁止默认/弱密钥；开发环境仅警告通过
    if jwt_secret in default_secrets or jwt_secret in ["secret", "password", "123456", "admin"]:
        if _is_development():
            return True, "开发环境使用占位 JWT_SECRET_KEY（生产环境必须更换）"
        return False, "JWT_SECRET_KEY 使用默认值或过弱，存在安全风险"

    return True, "OK"


def validate_database_config() -> Tuple[bool, str]:
    """验证数据库配置"""
    # 支持 DATABASE_URL，或由 POSTGRES_* 组装连接信息
    if os.getenv("DATABASE_URL"):
        return True, "OK"

    postgres_host = os.getenv("POSTGRES_HOST")
    postgres_db = os.getenv("POSTGRES_DB")
    postgres_user = os.getenv("POSTGRES_USER")
    if postgres_host and postgres_db and postgres_user:
        return True, "OK (POSTGRES_* )"

    if _is_development():
        return True, "开发环境未配置数据库，将按需延迟连接"

    return False, "缺少必需的数据库配置: DATABASE_URL 或 POSTGRES_HOST/DB/USER"


def validate_admin_config() -> Tuple[bool, str]:
    """验证管理员配置"""
    admin_username = os.getenv("ADMIN_USERNAME")
    admin_password = os.getenv("ADMIN_PASSWORD")

    if not admin_username:
        if _is_development():
            return True, "开发环境未设置 ADMIN_USERNAME，将使用默认值"
        return False, "ADMIN_USERNAME 环境变量未设置"

    if not admin_password:
        if _is_development():
            return True, "开发环境未设置 ADMIN_PASSWORD，将使用默认值"
        return False, "ADMIN_PASSWORD 环境变量未设置"

    if len(admin_password) < 8:
        return False, "ADMIN_PASSWORD 长度不足 8 位"

    # 检查默认密码
    weak_passwords = {"admin123", "password", "12345678", "REPLACE_WITH_STRONG_PASSWORD"}
    if admin_password in weak_passwords:
        if _is_development():
            return True, "开发环境使用占位管理员密码（生产环境必须更换）"
        return False, "ADMIN_PASSWORD 使用默认值，存在安全风险"

    return True, "OK"


def validate_api_config() -> Tuple[bool, str]:
    """验证 API 配置"""
    # 与项目其余代码统一使用 ZHIPU_API_KEY，同时兼容旧名 ZHIPUAI_API_KEY
    zhipu_key = os.getenv("ZHIPU_API_KEY") or os.getenv("ZHIPUAI_API_KEY")
    if not zhipu_key:
        if _is_development():
            return True, "开发环境未设置智谱 API Key，LLM 调用将失败直到配置密钥"
        return False, "ZHIPU_API_KEY 环境变量未设置"

    placeholder_keys = {
        "your_zhipu_api_key_here",
        "your-zhipuai-api-key-here",
        "your_api_key_here",
    }
    if zhipu_key in placeholder_keys:
        if _is_development():
            return True, "开发环境使用占位智谱 API Key"
        return False, "ZHIPU_API_KEY 仍为占位值，请配置真实密钥"

    return True, "OK"


def validate_cors_config() -> Tuple[bool, str]:
    """验证 CORS 配置"""
    allowed_origins = os.getenv("ALLOWED_ORIGINS", "")

    # 检查是否允许所有来源
    if "*" in allowed_origins or allowed_origins == "":
        app_env = os.getenv("APP_ENV", "development")
        if app_env == "production":
            return False, "生产环境不能使用 '*' 作为 CORS 来源"

    return True, "OK"


def validate_environment() -> Tuple[bool, str]:
    """验证环境配置"""
    app_env = os.getenv("APP_ENV", "development")

    if app_env not in ["development", "staging", "production"]:
        return False, f"无效的 APP_ENV: {app_env}"

    return True, "OK"


def run_startup_validation(strict: bool = True) -> List[Tuple[str, bool, str]]:
    """
    运行启动验证

    Args:
        strict: 是否严格模式（失败则退出）

    Returns:
        验证结果列表 [(名称, 是否通过, 消息)]
    """
    validators = [
        ("环境配置", validate_environment),
        ("JWT 配置", validate_jwt_config),
        ("数据库配置", validate_database_config),
        ("管理员配置", validate_admin_config),
        ("API 配置", validate_api_config),
        ("CORS 配置", validate_cors_config),
    ]

    results = []
    all_passed = True

    logger.info("=" * 60)
    logger.info("🔍 启动配置验证")
    logger.info("=" * 60)

    for name, validator in validators:
        try:
            passed, message = validator()
            results.append((name, passed, message))

            status = "✅" if passed else "❌"
            logger.info(f"{status} {name}: {message}")

            if not passed:
                all_passed = False

        except Exception as e:
            results.append((name, False, f"验证异常: {str(e)}"))
            logger.error(f"❌ {name}: 验证异常 - {str(e)}")
            all_passed = False

    logger.info("=" * 60)

    if not all_passed:
        if strict:
            logger.error("❌ 配置验证失败，无法启动应用")
            logger.error("请修复上述问题后重试")
            raise StartupValidationError("配置验证失败")
        else:
            logger.warning("⚠️ 配置验证存在警告，但继续启动")
    else:
        logger.info("✅ 所有配置验证通过")

    return results


def get_startup_checklist() -> str:
    """获取启动检查清单"""
    return """
📋 启动前检查清单：

必需的环境变量：
  • JWT_SECRET_KEY (>=32 字符，非默认值)
  • DATABASE_URL 或 POSTGRES_HOST/DB/USER
  • ADMIN_USERNAME
  • ADMIN_PASSWORD (>=8 字符，非默认值)
  • ZHIPU_API_KEY（兼容 ZHIPUAI_API_KEY）

可选的环境变量：
  • REDIS_URL (推荐，用于缓存和会话)
  • ALLOWED_ORIGINS (生产环境必须设置)
  • APP_ENV (development/staging/production)

示例 .env 文件：
  JWT_SECRET_KEY=your-production-secret-key-at-least-32-chars
  DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
  ADMIN_USERNAME=admin
  ADMIN_PASSWORD=secure_password_here
  ZHIPU_API_KEY=your_zhipu_api_key
  ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
  APP_ENV=production
"""


if __name__ == "__main__":
    # 直接运行此脚本进行配置检查
    try:
        run_startup_validation(strict=False)
        logger.info(get_startup_checklist())
    except StartupValidationError as e:
        logger.error(f"\n{get_startup_checklist()}")
        sys.exit(1)
