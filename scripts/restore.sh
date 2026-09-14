#!/bin/bash
# ============================================
# ZhiMeng 数据恢复脚本
# 用法: ./scripts/restore.sh ./backups/zhimeng_YYYYMMDD_HHMMSS.tar.gz
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

BACKUP_PATH="$1"

if [ -z "$BACKUP_PATH" ]; then
    echo -e "${RED}用法: $0 <backup.tar.gz>${NC}"
    echo "示例: $0 ./backups/zhimeng_20260914_120000.tar.gz"
    exit 1
fi

if [ ! -f "$BACKUP_PATH" ]; then
    echo -e "${RED}备份文件不存在: $BACKUP_PATH${NC}"
    exit 1
fi

echo -e "${BLUE}⚠️  即将用 $BACKUP_PATH 覆盖 ./data/works 与 ./data/vector_store${NC}"
echo "建议先停止服务: ./scripts/stop.sh 或 docker compose down"
read -r -p "确认继续? [y/N] " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "已取消"
    exit 0
fi

# 恢复前再做一次安全备份
if [ -f "./scripts/backup.sh" ]; then
    echo -e "${BLUE}先创建安全备份...${NC}"
    ./scripts/backup.sh || true
fi

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

echo -e "${BLUE}解压备份...${NC}"
tar -xzf "$BACKUP_PATH" -C "$TMP_DIR"

if [ ! -d "$TMP_DIR/works" ]; then
    echo -e "${RED}备份包缺少 works/ 目录${NC}"
    exit 1
fi

mkdir -p ./data
rm -rf ./data/works
cp -a "$TMP_DIR/works" ./data/works

rm -rf ./data/vector_store
if [ -d "$TMP_DIR/vector_store" ]; then
    cp -a "$TMP_DIR/vector_store" ./data/vector_store
else
    mkdir -p ./data/vector_store
fi

echo -e "${GREEN}✅ 恢复完成${NC}"
echo "请重新启动服务: ./scripts/start.sh 或 docker compose up -d"
