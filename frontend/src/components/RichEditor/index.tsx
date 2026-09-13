import { useEditor, EditorContent, type Editor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { Button } from 'antd';
import { forwardRef, useEffect, useImperativeHandle } from 'react';
import {
  Bold,
  Italic,
  Strikethrough,
  Code as CodeIcon,
  Heading1,
  Heading2,
  Quote,
  List as ListIcon,
  ListOrdered,
  Undo2,
  Redo2,
} from 'lucide-react';

/**
 * TipTap JSON 文档的最小类型约定。
 * 真正的 TipTap JSON schema 是开放结构，这里只声明我们关心的部分。
 */
export interface TipTapNode {
  type: string;
  attrs?: Record<string, unknown>;
  content?: TipTapNode[];
  marks?: Array<{ type: string; attrs?: Record<string, unknown> }>;
  text?: string;
}

export interface TipTapDoc {
  type: 'doc';
  content?: TipTapNode[];
}

/**
 * 暴露给父组件的命令式句柄 —— 用于 AI 流式生成时实时插入 chunk
 */
export interface RichEditorHandle {
  /** 在光标位置插入纯文本/HTML,返回是否成功。允许在 read-only 文档上调用 */
  insertContent: (text: string) => boolean;
  /** 整体替换编辑器内容(用于 done 兜底:用后端清洗后的 content 强制覆盖) */
  setContent: (text: string) => boolean;
  /** 获取当前纯文本 */
  getText: () => string;
  /** 聚焦编辑器 */
  focus: () => void;
  // [提交 D] 选区/段落级操作 —— 用于行内 AI 改写 / 段内润色建议
  /** 当前选区:{from, to, text}。折叠选区(光标)返回 null */
  getSelection: () => { from: number; to: number; text: string } | null;
  /** 把 [from, to) 区间替换为 text(纯文本),触发 onChange */
  replaceRange: (from: number, to: number, text: string) => boolean;
  /** 获取光标所在自然段:{from, to, text}。无段落返回 null */
  getCurrentParagraph: () => { from: number; to: number; text: string } | null;
}

interface RichEditorProps {
  /** TipTap JSON 内容；传 null 则为空文档 */
  content?: TipTapDoc | null;
  /** 是否可编辑 */
  editable?: boolean;
  /** 内容变更回调（TipTap JSON + 纯文本） */
  onChange?: (json: TipTapDoc, plain: string) => void;
  /** 选区变化回调 —— text 为折叠选区时为 '' */
  onSelectionChange?: (range: { from: number; to: number; text: string }) => void;
  /** 类名 */
  className?: string;
}

/**
 * 基于 TipTap StarterKit 的富文本编辑器
 *
 * - 支持粗体/斜体/删除线/行内代码/标题/引用/列表/撤销
 * - 内容为 TipTap JSON（与后端 Chapter.content 字段一致）
 * - onChange 同时给出纯文本，便于字数统计 / RAG 索引
 * - 通过 ref 暴露 insertContent / getText / focus,支持外部(如 AI 流式)程序化编辑
 */
export const RichEditor = forwardRef<RichEditorHandle, RichEditorProps>(function RichEditor(
  { content, editable = true, onChange, onSelectionChange, className },
  ref
) {
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        history: { depth: 50 },
      }),
    ],
    content: content ?? '',
    editable,
    onUpdate: ({ editor }) => {
      onChange?.(editor.getJSON() as TipTapDoc, editor.getText());
    },
    onSelectionUpdate: ({ editor }) => {
      const { from, to } = editor.state.selection;
      // [提交 D] 回调里附带选区文本(折叠选区时 text='')
      const text = from === to ? '' : editor.state.doc.textBetween(from, to, '\n', '\n');
      onSelectionChange?.({ from, to, text });
    },
    editorProps: {
      attributes: {
        class: 'prose prose-lg max-w-none focus:outline-none min-h-[400px]',
      },
    },
  });

  // 暴露命令式 API
  useImperativeHandle(
    ref,
    () => ({
      insertContent: (text: string) => {
        if (!editor) return false;
        // TipTap 允许在 read-only 文档上做程序化编辑(commands.insertContent)
        editor.commands.insertContent(text);
        return true;
      },
      setContent: (text: string) => {
        if (!editor) return false;
        // 整体替换 —— 用于 done 兜底,把可能含污染的内容替换为后端清洗后的版本
        // false 表示不触发 onUpdate(避免自身引发的更新又被 status effect 当 dirty 触发额外保存)
        editor.commands.setContent(text, false);
        return true;
      },
      getText: () => editor?.getText() ?? '',
      focus: () => {
        editor?.commands.focus('end');
      },
      // [提交 D] 选区/段落级操作
      getSelection: () => {
        if (!editor) return null;
        const { from, to } = editor.state.selection;
        if (from === to) return null;
        const text = editor.state.doc.textBetween(from, to, '\n', '\n');
        return { from, to, text };
      },
      replaceRange: (from: number, to: number, text: string) => {
        if (!editor) return false;
        // insertContentAt 在 from===to 时等价于纯插入,正常返回 true
        return editor.chain().focus().insertContentAt({ from, to }, text).run();
      },
      getCurrentParagraph: () => {
        if (!editor) return null;
        const { from } = editor.state.selection;
        // 解析光标位置,向上找最近的 block 节点(paragraph/heading)
        const $pos = editor.state.doc.resolve(from);
        for (let depth = $pos.depth; depth > 0; depth--) {
          const node = $pos.node(depth);
          if (node.type.name === 'paragraph' || node.type.name === 'heading') {
            const start = $pos.start(depth);
            const end = $pos.end(depth);
            if (start === end) return null;
            const text = editor.state.doc.textBetween(start, end, '\n', '\n');
            return { from: start, to: end, text };
          }
        }
        return null;
      },
    }),
    [editor]
  );

  // editable 变化时同步
  useEffect(() => {
    editor?.setEditable(editable);
  }, [editor, editable]);

  // 外部 content 变化时同步（仅当 editor 未聚焦且 content 不同）
  useEffect(() => {
    if (!editor) return;
    if (!content) return;
    const current = JSON.stringify(editor.getJSON());
    const incoming = JSON.stringify(content);
    if (current !== incoming && !editor.isFocused) {
      editor.commands.setContent(content, false);
    }
  }, [editor, content]);

  return (
    <div className={`rich-editor flex flex-col ${className ?? ''}`}>
      {editable && editor && <Toolbar editor={editor} />}
      <div className="flex-1 px-6 py-4 bg-surface-container-lowest rounded-b-lg border border-t-0 border-outline-variant/30">
        <EditorContent editor={editor} />
      </div>
    </div>
  );
});

interface ToolbarProps {
  editor: Editor;
}

function Toolbar({ editor }: ToolbarProps) {
  const Btn = ({
    onClick,
    active,
    disabled,
    children,
    title,
  }: {
    onClick: () => void;
    active?: boolean;
    disabled?: boolean;
    children: React.ReactNode;
    title: string;
  }) => (
    <Button
      type={active ? 'primary' : 'text'}
      size="small"
      onMouseDown={(e) => e.preventDefault()}
      onClick={onClick}
      disabled={disabled}
      title={title}
      style={{ width: 32, height: 32, padding: 0, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}
    >
      {children}
    </Button>
  );

  const Divider = () => <div className="w-px h-5 bg-outline-variant/40 mx-1" />;

  return (
    <div className="flex items-center gap-1 p-1 bg-surface-container-lowest rounded-t-lg border border-outline-variant/30">
      <Btn onClick={() => editor.chain().focus().undo().run()} disabled={!editor.can().undo()} title="撤销 (Ctrl+Z)">
        <Undo2 size={16} />
      </Btn>
      <Btn onClick={() => editor.chain().focus().redo().run()} disabled={!editor.can().redo()} title="重做 (Ctrl+Y)">
        <Redo2 size={16} />
      </Btn>
      <Divider />
      <Btn onClick={() => editor.chain().focus().toggleBold().run()} active={editor.isActive('bold')} title="粗体 (Ctrl+B)">
        <Bold size={16} />
      </Btn>
      <Btn onClick={() => editor.chain().focus().toggleItalic().run()} active={editor.isActive('italic')} title="斜体 (Ctrl+I)">
        <Italic size={16} />
      </Btn>
      <Btn onClick={() => editor.chain().focus().toggleStrike().run()} active={editor.isActive('strike')} title="删除线">
        <Strikethrough size={16} />
      </Btn>
      <Btn onClick={() => editor.chain().focus().toggleCode().run()} active={editor.isActive('code')} title="行内代码">
        <CodeIcon size={16} />
      </Btn>
      <Divider />
      <Btn onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()} active={editor.isActive('heading', { level: 1 })} title="标题 1">
        <Heading1 size={16} />
      </Btn>
      <Btn onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()} active={editor.isActive('heading', { level: 2 })} title="标题 2">
        <Heading2 size={16} />
      </Btn>
      <Btn onClick={() => editor.chain().focus().toggleBlockquote().run()} active={editor.isActive('blockquote')} title="引用">
        <Quote size={16} />
      </Btn>
      <Divider />
      <Btn onClick={() => editor.chain().focus().toggleBulletList().run()} active={editor.isActive('bulletList')} title="无序列表">
        <ListIcon size={16} />
      </Btn>
      <Btn onClick={() => editor.chain().focus().toggleOrderedList().run()} active={editor.isActive('orderedList')} title="有序列表">
        <ListOrdered size={16} />
      </Btn>
    </div>
  );
}