import { Routes, Route, Navigate } from 'react-router-dom';
import { lazy, Suspense } from 'react';

import { AppLayout } from '@/components/Layout/AppLayout';
import { useCurrentWorkStore } from '@/stores/useCurrentWorkStore';

// 懒加载页面
const HomePage           = lazy(() => import('@/pages/HomePage'));
const WorksListPage      = lazy(() => import('@/pages/WorksListPage'));
const WorkDetailPage     = lazy(() => import('@/pages/WorkDetailPage'));
const NewWorkWizardPage  = lazy(() => import('@/pages/NewWorkWizardPage'));
const ChapterEditorPage  = lazy(() => import('@/pages/ChapterEditorPage'));
const OutlinePage        = lazy(() => import('@/pages/OutlinePage'));
const CharactersPage     = lazy(() => import('@/pages/CharactersPage'));
const WorldBiblePage     = lazy(() => import('@/pages/WorldBiblePage'));
const SettingsPage       = lazy(() => import('@/pages/SettingsPage'));
const HelpPage           = lazy(() => import('@/pages/HelpPage'));
const NotFoundPage       = lazy(() => import('@/pages/NotFoundPage'));

function LoadingFallback() {
  return (
    <div className="flex items-center justify-center h-screen text-on-surface-low">
      <span className="font-code-sm">加载中...</span>
    </div>
  );
}

/** 旧路径 /outline 等转到当前作品设定页；没有当前作品则去作品库。 */
function RedirectSetting({ segment }: { segment: 'outline' | 'characters' | 'world' }) {
  const currentWorkId = useCurrentWorkStore((s) => s.currentWorkId);
  if (currentWorkId) {
    return <Navigate to={`/works/${currentWorkId}/${segment}`} replace />;
  }
  return <Navigate to="/works" replace />;
}

export function AppRouter() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <Routes>
        {/* 带 Layout 的路由 */}
        <Route element={<AppLayout />}>
          <Route path="/" element={<HomePage />} />

          {/* 创作空间 */}
          <Route path="/works" element={<WorksListPage />} />
          <Route path="/works/:id" element={<WorkDetailPage />} />
          <Route path="/works/:id/outline" element={<OutlinePage />} />
          <Route path="/works/:id/characters" element={<CharactersPage />} />
          <Route path="/works/:id/world" element={<WorldBiblePage />} />
          <Route path="/editor" element={<ChapterEditorPage />} />
          <Route path="/editor/:chapterId" element={<ChapterEditorPage />} />

          <Route path="/outline" element={<RedirectSetting segment="outline" />} />
          <Route path="/characters" element={<RedirectSetting segment="characters" />} />
          <Route path="/world" element={<RedirectSetting segment="world" />} />

          {/* 系统设置 */}
          <Route path="/settings" element={<Navigate to="/settings/general" replace />} />
          <Route path="/settings/general"    element={<SettingsPage />} />
          <Route path="/settings/llm"        element={<SettingsPage />} />
          <Route path="/settings/prompts"    element={<SettingsPage />} />
          <Route path="/settings/writing"    element={<SettingsPage />} />
          <Route path="/settings/appearance" element={<SettingsPage />} />
          <Route path="/settings/backup"     element={<SettingsPage />} />
          <Route path="/settings/about"      element={<SettingsPage />} />

          {/* 文档 */}
          <Route path="/help" element={<HelpPage />} />
        </Route>

        {/* 全屏页面（无 Layout） */}
        <Route path="/works/new" element={<NewWorkWizardPage />} />
        <Route path="/404" element={<NotFoundPage />} />
        <Route path="*" element={<Navigate to="/404" replace />} />
      </Routes>
    </Suspense>
  );
}