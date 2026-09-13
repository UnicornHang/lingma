#!/bin/bash
# ============================================
# ZhiMeng 停止脚本
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🛑 停止 ZhiMeng 服务...${NC}"

# 停止服务（保留数据卷）
docker compose down

echo -e "${GREEN}✅ 服务已停止${NC}"
echo ""
echo "提示："
echo "  - 数据保留在 ./data/ 目录"
echo "  - 完全清理（含数据）：docker compose down -v"
echo "  - 重新启动：./scripts/start.sh"