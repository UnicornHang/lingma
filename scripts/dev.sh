#!/bin/bash
# ============================================
# LingMa 开发模式启动 —— 后端带 --reload
# ============================================
#
# 与 scripts/start.sh(生产 Docker 模式)区别:
# - 直接在宿主机跑 uvicorn(不经过 Docker)
# - 默认带 --reload,改代码自动重启
# - 单 worker(便于看日志)
#
# 典型工作流:
#   1. ./scripts/dev.sh           # 启动后端
#   2. cd frontend && npm run dev # 另一个终端启动前端
#   3. 改后端代码 → uvicorn 自动重启
#
# 停止: Ctrl+C,或运行 ./scripts/stop.sh

set -e

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
success() { echo -e "${GREEN}✅ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
error() { echo -e "${RED}❌ $1${NC}"; }

# 切到 backend 目录(uvicorn 需要在含 app/ 的目录里跑)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../backend"

if [ ! -d ".venv" ] && [ ! -f "pyproject.toml" ]; then
    error "未检测到 backend 环境,请先安装依赖"
    exit 1
fi

# 加载 .env
if [ -f "../.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "../.env"
    set +a
fi

PORT="${BACKEND_PORT:-8000}"
HOST="${BACKEND_HOST:-0.0.0.0}"

echo ""
echo "=========================================="
echo "  🛠️  LingMa Backend (DEV, --reload)"
echo "=========================================="
echo ""
info "监听: http://${HOST}:${PORT}"
info "代码改动会自动重启(uvicorn --reload)"
info "停止: Ctrl+C 或 ./scripts/stop.sh"
echo ""

# 兼容: 优先用 .venv 里的 uvicorn,否则用 PATH 里的
if [ -x ".venv/bin/uvicorn" ]; then
    exec ./.venv/bin/uvicorn app.main:app \
        --host "$HOST" --port "$PORT" \
        --reload \
        --reload-dir app \
        --log-level info
elif command -v uvicorn >/dev/null 2>&1; then
    exec uvicorn app.main:app \
        --host "$HOST" --port "$PORT" \
        --reload \
        --reload-dir app \
        --log-level info
else
    error "未找到 uvicorn,请先 pip install uvicorn"
    exit 1
fi
