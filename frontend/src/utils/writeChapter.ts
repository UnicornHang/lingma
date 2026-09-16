import { chaptersApi, type OutlineTreeNode } from '@/api';

/**
 * 为章纲打开已有正文，或创建空章节（不调用 Writer）。
 */
export async function openOrCreateChapterForNode(
  workId: string,
  node: OutlineTreeNode,
) {
  const listed = await chaptersApi.listByWork(workId, { page: 1, page_size: 200 });
  const existing = listed.items.find((c) => c.outline_node_id === node.id);
  if (existing) return existing;
  return chaptersApi.create({
    work_id: workId,
    title: node.title,
    outline_node_id: node.id,
    summary: node.summary,
  });
}
