"""
环境变量设置脚本
帮助用户设置必要的环境变量

⚠️ 安全警告：
- 请勿在代码中硬编码真实API密钥
- 请使用 .env 文件或系统环境变量
- 此脚本仅用于开发环境配置
"""
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def setup_environment():
    """
    设置环境变量

    注意：真实API密钥应从环境变量或 .env 文件读取
    """

    # 智谱AI配置
    # 请在环境变量中设置: ZHIPU_API_KEY
    os.environ.setdefault("ZHIPU_API_KEY", os.getenv("ZHIPU_API_KEY", ""))
    os.environ.setdefault("ZHIPU_MODEL", "search-std")
    os.environ.setdefault("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
    os.environ.setdefault("ZHIPU_TEMPERATURE", "0.7")
    os.environ.setdefault("ZHIPU_MAX_TOKENS", "4096")

    # Tavily搜索配置
    # 请在环境变量中设置: TAVILY_API_KEY
    os.environ.setdefault("TAVILY_API_KEY", os.getenv("TAVILY_API_KEY", ""))
    os.environ.setdefault("TAVILY_BASE_URL", "https://api.tavily.com")

    # OpenRouter配置
    # 请在环境变量中设置: OPENROUTER_API_KEY
    os.environ.setdefault("OPENROUTER_API_KEY", os.getenv("OPENROUTER_API_KEY", ""))
    os.environ.setdefault("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct")
    os.environ.setdefault("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    os.environ.setdefault("OPENROUTER_TEMPERATURE", "0.7")
    os.environ.setdefault("OPENROUTER_MAX_TOKENS", "4096")

    # 应用配置
    os.environ.setdefault("APP_NAME", "竖屏短剧策划助手")
    os.environ.setdefault("APP_VERSION", "1.0.0")
    os.environ.setdefault("DEBUG", "false")
    os.environ.setdefault("LOG_LEVEL", "INFO")
    os.environ.setdefault("DEFAULT_MODEL_PROVIDER", "zhipu")

    # 功能开关
    os.environ.setdefault("KNOWLEDGE_BASE_ENABLED", "true")
    os.environ.setdefault("WEB_SEARCH_ENABLED", "true")

    # Redis配置
    os.environ.setdefault("REDIS_HOST", "localhost")
    os.environ.setdefault("REDIS_PORT", "6379")
    os.environ.setdefault("REDIS_DB", "0")
    os.environ.setdefault("REDIS_PASSWORD", "")

    # Milvus配置
    os.environ.setdefault("MILVUS_HOST", "localhost")
    os.environ.setdefault("MILVUS_PORT", "19530")
    os.environ.setdefault("MILVUS_USERNAME", "")
    os.environ.setdefault("MILVUS_PASSWORD", "")

    # PostgreSQL配置
    os.environ.setdefault("POSTGRES_HOST", "localhost")
    os.environ.setdefault("POSTGRES_PORT", "5432")
    os.environ.setdefault("POSTGRES_DB", "juben")
    os.environ.setdefault("POSTGRES_USER", "juben")
    os.environ.setdefault("POSTGRES_PASSWORD", "")
    os.environ.setdefault("POSTGRES_SSLMODE", "disable")
    os.environ.setdefault("POSTGRES_POOL_MIN", "1")
    os.environ.setdefault("POSTGRES_POOL_MAX", "10")
    
    logger.info("✅ 环境变量设置完成")
    logger.warning("⚠️  请确保已设置以下API密钥：")
    logger.info("   - ZHIPU_API_KEY (必需)")
    logger.info("   - TAVILY_API_KEY (可选)")
    logger.info("   - OPENROUTER_API_KEY (可选)")
    logger.info("")
    logger.info("💡 推荐使用 .env 文件配置环境变量")


def create_env_file():
    """
    创建.env示例文件

    ⚠️ 警告：此文件包含敏感信息，请勿提交到版本控制系统
    """
    env_content = """# 竖屏短剧策划助手环境变量配置
# ⚠️ 请勿将包含真实API密钥的.env文件提交到版本控制系统

# ==================== 必需配置 ====================

# 智谱AI配置（必需）
ZHIPU_API_KEY=your_zhipu_api_key_here
ZHIPU_MODEL=glm-4.7-flash
DEFAULT_MODEL_PROVIDER=zhipu
ZHIPU_BASE_URL=https://open.bigmodel.cn/api/paas/v4
ZHIPU_TEMPERATURE=0.7
ZHIPU_MAX_TOKENS=4096

# ==================== 可选配置 ====================

# Tavily搜索配置（可选）
TAVILY_API_KEY=your_tavily_api_key_here
TAVILY_BASE_URL=https://api.tavily.com

# OpenRouter配置（可选，用于访问其他模型）
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=meta-llama/llama-3.3-70b-instruct
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_TEMPERATURE=0.7
OPENROUTER_MAX_TOKENS=4096

# ==================== 应用配置 ====================

APP_NAME=竖屏短剧策划助手
APP_VERSION=1.0.0
DEBUG=false
LOG_LEVEL=INFO
DEFAULT_MODEL_PROVIDER=zhipu

# 功能开关
KNOWLEDGE_BASE_ENABLED=true
WEB_SEARCH_ENABLED=true

# ==================== 认证配置 ====================

# 认证开关（生产环境建议启用）
AUTH_ENABLED=false
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password_here
ADMIN_PASSWORD_HASH=
JWT_SECRET_KEY=your_jwt_secret_key_minimum_32_characters
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# ==================== 数据库配置 ====================

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# PostgreSQL配置
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=juben
POSTGRES_USER=juben
POSTGRES_PASSWORD=change_this_postgres_password
POSTGRES_SSLMODE=disable
POSTGRES_POOL_MIN=1
POSTGRES_POOL_MAX=10

# Milvus配置
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_USERNAME=
MILVUS_PASSWORD=

# ==================== 其他模型配置（可选）====================

# OPENAI_API_KEY=your_openai_api_key_here
# GEMINI_API_KEY=your_gemini_api_key_here
# KIMI_API_KEY=your_kimi_api_key_here
# DEEPSEEK_API_KEY=your_deepseek_api_key_here
# CLAUDE_API_KEY=your_claude_api_key_here
# DOUBAO_API_KEY=your_doubao_api_key_here
"""

    env_example_file = Path(".env.example")
    if not env_example_file.exists():
        with open(env_example_file, "w", encoding="utf-8") as f:
            f.write(env_content)
        logger.info(f"✅ 已创建 .env.example 文件: {env_example_file.absolute()}")
    else:
        logger.warning(f"⚠️  .env.example 文件已存在: {env_example_file.absolute()}")

    # 检查是否存在实际的.env文件
    env_file = Path(".env")
    if env_file.exists():
        logger.info(f"ℹ️  .env 文件已存在: {env_file.absolute()}")
    else:
        logger.warning(f"💡 请复制 .env.example 为 .env 并填写实际的API密钥")


if __name__ == "__main__":
    logger.info("🚀 设置竖屏短剧策划助手环境变量...")
    setup_environment()
    create_env_file()
    logger.info("🎉 环境设置完成！")
