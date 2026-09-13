# ZhiMeng Frontend

> React 18 + Vite + TypeScript + Ant Design 5 + TipTap

## 快速开始

### 本地开发

```bash
# 1. 安装依赖
npm install

# 2. 启动开发服务器
npm run dev
# → http://localhost:5173

# 后端 API 代理已配置（自动转发到 http://localhost:8000）
```

### Docker 启动（推荐）

从项目根目录：

```bash
./scripts/start.sh
# → http://localhost:7860
```

## 目录结构

```
frontend/
├── src/
│   ├── main.tsx           # 应用入口
│   ├── App.tsx            # 根组件
│   ├── router.tsx         # 路由配置
│   ├── api/               # API 客户端
│   ├── stores/            # Zustand 状态
│   ├── components/        # 通用组件
│   ├── pages/             # 页面
│   ├── types/             # TypeScript 类型
│   └── styles/            # 全局样式
├── index.html
├── vite.config.ts
├── tailwind.config.ts
└── package.json
```

## 技术栈

- **React 18** - UI 框架
- **Vite 5** - 构建工具
- **TypeScript 5** - 类型系统
- **Ant Design 5** - UI 组件库
- **Tailwind CSS 3** - 原子化样式
- **Zustand 4** - 状态管理
- **TanStack Query 5** - 数据请求与缓存
- **React Router 6** - 路由
- **TipTap 2** - 富文本编辑器
- **Axios** - HTTP 客户端

## 开发命令

```bash
npm run dev          # 开发服务器
npm run build        # 生产构建
npm run preview      # 预览构建产物
npm run type-check   # 类型检查
npm run lint         # 代码检查
npm run test         # 单元测试
npm run test:e2e     # E2E 测试
```

详见 [../docs/FRONTEND_REQUIREMENTS.md](../docs/FRONTEND_REQUIREMENTS.md)。