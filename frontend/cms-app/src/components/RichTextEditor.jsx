/**
 * 記事本文のリッチテキストエディタ
 */
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { useEffect } from "react";


// 親画面の本文HTMLと同期し、変更時にHTMLを返す
function RichTextEditor({ id, value, onChange, disabled = false }) {
  const editor = useEditor({
    extensions: [StarterKit],
    content: value || "",
    editable: !disabled,
    onUpdate: ({ editor: currentEditor }) => onChange(currentEditor.getHTML()),
  });

  // 記事取得・リビジョン復元後の本文をエディタへ反映
  useEffect(() => {
    if (!editor) return;
    if (editor.getHTML() !== (value || "")) {
      editor.commands.setContent(value || "", { emitUpdate: false });
    }
  }, [editor, value]);

  // 保存処理中は編集不可にする
  useEffect(() => {
    if (editor) editor.setEditable(!disabled);
  }, [editor, disabled]);

  // エディタの装飾ボタンとアクションの定義
  const commands = [
    { label: "太字", action: () => editor.chain().focus().toggleBold().run(), active: "bold" },
    { label: "斜体", action: () => editor.chain().focus().toggleItalic().run(), active: "italic" },
    { label: "見出し2", action: () => editor.chain().focus().toggleHeading({ level: 2 }).run(), active: "heading", level: 2 },
    { label: "箇条書き", action: () => editor.chain().focus().toggleBulletList().run(), active: "bulletList" },
    { label: "番号付き", action: () => editor.chain().focus().toggleOrderedList().run(), active: "orderedList" },
  ];

  return (
    <div className="rich-text-editor" id={id}>
      {/* 装飾用ツールバー */}
      <div className="rich-text-toolbar" role="toolbar" aria-label="本文の書式設定">
        {commands.map((command) => (
          <button key={command.label} type="button" disabled={!editor || disabled}
            className={editor?.isActive(command.active, command.level ? { level: command.level } : {}) ? "active" : ""}
            onClick={command.action}
          >{command.label}</button>
        ))}
      </div>
      {/* 本文の編集領域 */}
      <EditorContent editor={editor} aria-label="本文" />
    </div>
  );
}

export default RichTextEditor;
