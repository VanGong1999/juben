"""数据库迁移脚本（简易版）"""
import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


async def main():
    from utils.database_client import get_postgres_pool

    pool = await get_postgres_pool()
    migrations_dir = Path(__file__).parent / "migrations"
    migrations_dir.mkdir(exist_ok=True)

    async with pool.acquire() as conn:
        # 确保迁移表存在
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )

        rows = await conn.fetch("SELECT version FROM schema_migrations")
        applied_versions = {r["version"] for r in rows}

        sql_files = sorted(migrations_dir.glob("*.sql"))
        if not sql_files:
            logger.warning("未发现迁移文件")
            return

        for sql_file in sql_files:
            version = sql_file.name
            if version in applied_versions:
                logger.info(f"跳过已应用迁移: {version}")
                continue

            sql_content = sql_file.read_text(encoding="utf-8")
            logger.info(f"应用迁移: {version}")
            await conn.execute(sql_content)
            await conn.execute("INSERT INTO schema_migrations (version) VALUES ($1)", version)

        logger.info("迁移完成")

if __name__ == "__main__":
    asyncio.run(main())
