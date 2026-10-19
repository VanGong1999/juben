#!/bin/bash
# 剧本创作 Agent 平台 - 唯一启动入口（本地开发）
#
# 自动拉起外部依赖 + 前后端：
#   - PostgreSQL / Redis  → homebrew（本机服务）
#   - Neo4j / Milvus      → docker compose
#   - 后端                 → venv/bin/python main.py  (http://localhost:8000)
#   - 前端                 → pnpm dev                  (http://localhost:5173)
#
# 用法：bash scripts/start_dev.sh
# 日志：/tmp/juben-backend.log  /tmp/juben-frontend.log
# 停止：kill $(cat /tmp/juben-backend.pid) ; kill $(cat /tmp/juben-frontend.pid)

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "========================================"
echo "  剧本创作 Agent 平台 - 启动中"
echo "========================================"

# ---------- 1. 外部依赖 ----------
echo ""
echo "==> 检查外部依赖"

# PostgreSQL（homebrew postgresql@16，端口 5432）
if lsof -iTCP:5432 -sTCP:LISTEN -nP >/dev/null 2>&1; then
  echo "  ✅ PostgreSQL 已运行 (5432)"
else
  echo "  ⏳ 启动 PostgreSQL..."
  brew services start postgresql@16 >/dev/null 2>&1 \
    && echo "  ✅ PostgreSQL 已启动" \
    || echo "  ⚠️  无法自动启动 PostgreSQL，请手动执行: brew services start postgresql@16"
fi

# Redis（homebrew redis，端口 6379）
if lsof -iTCP:6379 -sTCP:LISTEN -nP >/dev/null 2>&1; then
  echo "  ✅ Redis 已运行 (6379)"
else
  echo "  ⏳ 启动 Redis..."
  brew services start redis >/dev/null 2>&1 \
    && echo "  ✅ Redis 已启动" \
    || echo "  ⚠️  无法自动启动 Redis，请手动执行: brew services start redis"
fi

# Neo4j + Milvus（docker compose）
if docker info >/dev/null 2>&1; then
  docker compose up -d neo4j >/dev/null 2>&1 \
    && echo "  ✅ Neo4j 已启动 (7687)" \
    || echo "  ⚠️  Neo4j 启动失败"
  docker compose -f docker-compose.milvus.yml up -d >/dev/null 2>&1 \
    && echo "  ✅ Milvus 已启动 (19530)" \
    || echo "  ⚠️  Milvus 启动失败"
else
  echo "  ⚠️  Docker 未运行，跳过 Neo4j/Milvus（图谱/向量检索功能不可用）"
fi

# ---------- 2. 后端 ----------
echo ""
echo "==> 启动后端 (http://localhost:8000)"
: > /tmp/juben-backend.log
if [ ! -x "$ROOT/venv/bin/python" ]; then
  echo "  ❌ 未找到 venv，请先执行: python3 -m venv venv && venv/bin/pip install -r requirements.txt"
  exit 1
fi

nohup env SKIP_STARTUP_VALIDATION=1 DEBUG=false REDIS_WARMUP_TIMEOUT=3 \
  "$ROOT/venv/bin/python" main.py >> /tmp/juben-backend.log 2>&1 &
echo "$!" > /tmp/juben-backend.pid
echo "  ✅ 后端 PID: $(cat /tmp/juben-backend.pid)"

# ---------- 3. 前端 ----------
echo ""
echo "==> 启动前端 (http://localhost:5173)"
: > /tmp/juben-frontend.log
if [ ! -d "$ROOT/frontend/node_modules" ]; then
  echo "  ⏳ 首次启动，安装前端依赖..."
  (cd "$ROOT/frontend" && pnpm install) >> /tmp/juben-frontend.log 2>&1
fi

(cd "$ROOT/frontend" && nohup pnpm dev --host >> /tmp/juben-frontend.log 2>&1 &)
# 上面用子 shell 后台启动，稍候读取端口以写入 PID（vite 启动极快）
sleep 1
FE_PID="$(lsof -tiTCP:5173 -sTCP:LISTEN -nP 2>/dev/null | head -1)"
echo "${FE_PID:-unknown}" > /tmp/juben-frontend.pid
echo "  ✅ 前端 PID: $(cat /tmp/juben-frontend.pid)"

echo ""
echo "========================================"
echo "  启动完成"
echo "    前端: http://localhost:5173"
echo "    后端: http://localhost:8000/health"
echo "    API 文档: http://localhost:8000/docs"
echo "  日志: /tmp/juben-backend.log /tmp/juben-frontend.log"
echo "========================================"
