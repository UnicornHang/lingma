/** 与 RichEditor 对齐的最小 TipTap 文档，避免循环依赖。 */
interface TipTapNode {
  type: string;
  content?: TipTapNode[];
  text?: string;
}

interface TipTapDoc {
  type: 'doc';
  content?: TipTapNode[];
}

const MAX_PARA = 120;

/** 润色 JSON 样例被模型抄进正文时的尖括号占位。 */
const LEAK_RES: RegExp[] = [
  /<改写后片段[^>]*>/g,
  /<原片段[^>]*>/g,
  /<finding[^>]*>/g,
  /若判定无需改写[,，]?填原文/g,
  /<\/?think>/g,
];

/** 去掉提示词泄漏。 */
export function stripPromptLeaks(text: string): string {
  if (!text) return text;
  return LEAK_RES.reduce((acc, re) => acc.replace(re, ''), text);
}

/** 墙式正文切成网文自然段：对话独立、场景切换空行、过长段按句切开。 */
export function normalizeNovelParagraphs(text: string, maxPara = MAX_PARA): string {
  if (!text.trim()) return text;
  let t = stripPromptLeaks(text).replace(/\r\n/g, '\n').replace(/\r/g, '\n').trim();
  if ((t.match(/\n/g) ?? []).length >= 3) {
    return t.split(/\n+/).map((p) => p.trim()).filter(Boolean).join('\n\n');
  }
  t = t.replace(/([。！？…])\s*(?=[「“"『])/g, '$1\n\n');
  t = t.replace(/([」”"』])\s+(?=\S)/g, '$1\n\n');
  t = t.replace(/([。！？…」”"』])\s*——\s+/g, '$1\n\n——\n\n');
  return splitLongBlocks(t, maxPara);
}

/** 超长块在句号处切开。 */
function splitLongBlocks(text: string, maxPara: number): string {
  const out: string[] = [];
  for (const raw of text.split(/\n+/)) {
    const block = raw.trim();
    if (!block) continue;
    if (block.length <= maxPara) {
      out.push(block);
      continue;
    }
    const sentences = block.split(/(?<=[。！？…])/);
    let buf = '';
    for (const sent of sentences) {
      if (!sent) continue;
      if (buf && buf.length + sent.length > maxPara) {
        out.push(buf.trim());
        buf = sent;
      } else {
        buf += sent;
      }
    }
    if (buf.trim()) out.push(buf.trim());
  }
  return out.join('\n\n');
}

/** 纯文本转 TipTap JSON，每行/每段一个 paragraph。 */
export function plainToTipTapDoc(plain: string): TipTapDoc {
  const normalized = normalizeNovelParagraphs(plain);
  const blocks = normalized.split(/\n+/).map((b) => b.trim()).filter(Boolean);
  const content: TipTapNode[] = (blocks.length ? blocks : ['']).map((block) => ({
    type: 'paragraph',
    content: block ? [{ type: 'text', text: block }] : [],
  }));
  return { type: 'doc', content };
}
