import type { OutlineTreeNode } from '@/api';

/** 深度优先找到第一份章纲（跳过卷）。 */
export function findFirstChapterNode(nodes: OutlineTreeNode[]): OutlineTreeNode | null {
  for (const node of nodes) {
    if (node.type === 'chapter') return node;
    const child = findFirstChapterNode(node.children ?? []);
    if (child) return child;
  }
  return null;
}
