#!/bin/bash
# ============================================
# ZhiMeng 数据备份脚本
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# 读取配置
BACKUP_DIR=$(grep BACKUP_DIR .env 2>/dev/null | cut -d '=' -f2 | tr -d '"' || echo "./backups")
BACKUP_DIR=${BACKUP_DIR:-./backups}

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 生成时间戳
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="zhimeng_${TIMESTAMP}.tar.gz"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"

echo -e "${BLUE}📦 备份 ZhiMeng 数据...${NC}"
echo "目标: $BACKUP_PATH"

# 备份关键数据
tar -czf "$BACKUP_PATH" \
    --exclude='./data/logs/*' \
    --exclude='./backups' \
    ./data/works \
    ./data/vector_store \
    ./.env \
    2>/dev/null || true

if [ -f "$BACKUP_PATH" ]; then
    SIZE=$(du -h "$BACKUP_PATH" | cut -f1)
    echo -e "${GREEN}✅ 备份完成: $BACKUP_PATH ($SIZE)${NC}"
    echo ""
    echo "最近 5 个备份："
    ls -lt "$BACKUP_DIR"/*.tar.gz 2>/dev/null | head -5 | awk '{print "  " $9 " (" $5 ")"}'
else
    echo "❌ 备份失败"
    exit 1
fi

echo ""
echo "恢复命令: ./scripts/restore.sh $BACKUP_PATH"