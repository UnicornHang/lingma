import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import { chaptersApi } from '@/api/chapters';
import { useCurrentWorkStore } from '@/stores/useCurrentWorkStore';

/** 从 /works/:id 或 /editor/:chapterId 同步当前作品。 */
export function useSyncCurrentWork() {
  const { pathname } = useLocation();
  const setCurrentWorkId = useCurrentWorkStore((s) => s.setCurrentWorkId);

  const workIdFromPath = matchWorkId(pathname);
  const chapterIdFromPath = matchChapterId(pathname);

  useEffect(() => {
    if (workIdFromPath) setCurrentWorkId(workIdFromPath);
  }, [workIdFromPath, setCurrentWorkId]);

  const chapterQuery = useQuery({
    queryKey: ['chapter-work', chapterIdFromPath],
    queryFn: () => chaptersApi.get(chapterIdFromPath!),
    enabled: !!chapterIdFromPath && !workIdFromPath,
  });

  useEffect(() => {
    const workId = chapterQuery.data?.work_id;
    if (workId) setCurrentWorkId(workId);
  }, [chapterQuery.data?.work_id, setCurrentWorkId]);
}

/** 解析 /works/{uuid}，排除 /works/new。 */
function matchWorkId(pathname: string): string | null {
  const m = pathname.match(/^\/works\/([^/]+)/);
  if (!m) return null;
  if (m[1] === 'new') return null;
  return m[1];
}

/** 解析 /editor/{chapterId}。 */
function matchChapterId(pathname: string): string | null {
  const m = pathname.match(/^\/editor\/([^/]+)/);
  return m ? m[1] : null;
}
