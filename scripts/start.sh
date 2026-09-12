#!/bin/bash
# ============================================
# LingMa 启动脚本
# ============================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 打印信息函数
info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
success() { echo -e "${GREEN}✅ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
error() { echo -e "${RED}❌ $1${NC}"; }

echo ""
echo "=========================================="
echo "  🚀 LingMa Novel Studio"
echo "=========================================="
echo ""

# 切换到项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."
PROJECT_ROOT=$(pwd)

info "项目目录: $PROJECT_ROOT"

# ==================== 检查依赖 ====================
info "检查 Docker..."
if ! command -v docker &> /dev/null; then
    error "未检测到 Docker，请先安装: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! docker info &> /dev/null; then
    error "Docker 未运行，请启动 Docker Desktop"
    exit 1
fi

if ! command -v docker compose &> /dev/null && ! docker compose version &> /dev/null; then
    error "未检测到 Docker Compose，请安装最新 Docker"
    exit 1
fi

success "Docker 环境正常"

# ==================== 准备环境 ====================
info "准备数据目录..."
mkdir -p ./data/works ./data/vector_store ./data/logs ./backups

# .env 文件
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        warn "已创建 .env 文件，请编辑填入你的 LLM API Key 后重新启动"
        warn "至少需要配置以下之一: OPENAI_API_KEY / ANTHROPIC_API_KEY / DEEPSEEK_API_KEY / QWEN_API_KEY"
        echo ""
        info "现在你可以："
        info "  1. 编辑 .env 文件: vim .env"
        info "  2. 重新运行启动脚本: ./scripts/start.sh"
        echo ""
        # 询问是否继续（无 API Key 也能启动，但生成功能不可用）
        read -p "是否使用空 API Key 继续启动？(y/N) " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 0
        fi
    else
        error ".env.example 文件不存在"
        exit 1
    fi
fi

# 检查 APP_SECRET
if grep -q "change-me-to-random-32-chars-string" .env; then
    warn "检测到默认 APP_SECRET，建议修改为随机字符串（生产环境必须修改）"
fi

# ==================== 构建并启动 ====================
info "构建并启动服务..."
docker compose up -d --build

# ==================== 等待就绪 ====================
info "等待服务启动..."
sleep 5

# 检查容器状态
if docker compose ps | grep -q "lingma-backend.*Up"; then
    success "后端服务已启动"
else
    error "后端服务启动失败，请查看日志: docker compose logs backend"
    exit 1
fi

if docker compose ps | grep -q "lingma-frontend.*Up"; then
    success "前端服务已启动"
else
    error "前端服务启动失败，请查看日志: docker compose logs frontend"
    exit 1
fi

# ==================== 健康检查 ====================
info "健康检查..."
sleep 3
FRONTEND_PORT=$(grep FRONTEND_PORT .env | cut -d '=' -f2 | tr -d '"' | tr -d "'" || echo "7860")
FRONTEND_PORT=${FRONTEND_PORT:-7860}

if curl -sf "http://localhost:${FRONTEND_PORT}" > /dev/null; then
    success "前端可访问"
else
    warn "前端暂未响应（可能还在初始化）"
fi

# ==================== 完成 ====================
echo ""
echo "=========================================="
echo -e "  ${GREEN}✅ LingMa 启动成功！${NC}"
echo "=========================================="
echo ""
echo -e "  📖 访问地址: ${GREEN}http://localhost:${FRONTEND_PORT}${NC}"
echo "  📚 项目文档: ./docs/README.md"
echo ""
echo "  常用命令："
echo "    - 查看日志:     docker compose logs -f"
echo "    - 停止服务:     ./scripts/stop.sh"
echo "    - 重启服务:     docker compose restart"
echo "    - 进入容器:     docker compose exec backend bash"
echo "    - 备份数据:     ./scripts/backup.sh"
echo ""
echo "=========================================="