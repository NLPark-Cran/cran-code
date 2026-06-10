"use client";

import { useRef, useCallback, useEffect, useState } from "react";
import Editor from "@monaco-editor/react";
import { Button } from "@/components/ui/button";
import { Save, Loader2, MessageSquarePlus, Trash2, X } from "lucide-react";
import type * as Y from "yjs";
import { useSettingsStore } from "@/stores/settings";
import type { LineComment } from "@/hooks/useYjsCollab";
import { Input } from "@/components/ui/input";

function getLanguageFromPath(path: string): string {
  const ext = path.split(".").pop()?.toLowerCase();
  const map: Record<string, string> = {
    ts: "typescript", tsx: "typescript", js: "javascript", jsx: "javascript",
    py: "python", rs: "rust", go: "go", java: "java", cpp: "cpp", c: "c",
    h: "c", hpp: "cpp", cs: "csharp", rb: "ruby", php: "php", swift: "swift",
    kt: "kotlin", scala: "scala", md: "markdown", json: "json", yaml: "yaml",
    yml: "yaml", toml: "toml", xml: "xml", html: "html", css: "css",
    scss: "scss", less: "less", sql: "sql", sh: "shell", bash: "shell",
    zsh: "shell", dockerfile: "dockerfile", vue: "html", svelte: "html",
  };
  return map[ext || ""] || "plaintext";
}

interface MonacoEditorProps {
  path: string;
  content: string;
  onChange: (value: string) => void;
  onSave: () => void;
  saving: boolean;
  readOnly?: boolean;
  ytext?: Y.Text;
  awareness?: any;
  comments?: LineComment[];
  onAddComment?: (line: number, text: string) => void;
  onDeleteComment?: (id: string) => void;
  currentUser?: string;
}

export default function MonacoEditor({
  path,
  content,
  onChange,
  onSave,
  saving,
  readOnly,
  ytext,
  awareness,
  comments = [],
  onAddComment,
  onDeleteComment,
  currentUser,
}: MonacoEditorProps) {
  const editorRef = useRef<any>(null);
  const bindingRef = useRef<any>(null);
  const decorationsRef = useRef<string[]>([]);
  const editorSettings = useSettingsStore((s) => s.editor);
  const [activeLine, setActiveLine] = useState<number | null>(null);
  const [newCommentText, setNewCommentText] = useState("");

  const handleEditorDidMount = useCallback((editor: any, monaco: any) => {
    editorRef.current = editor;
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => onSave());

    // Click on line numbers to toggle comment panel for that line
    editor.onMouseDown((e: any) => {
      const type = e.target.type;
      // GUTTER_LINE_NUMBERS = 3 in monaco
      if (type === 3) {
        const line = e.target.position?.lineNumber;
        if (line) {
          setActiveLine((prev) => (prev === line ? null : line));
        }
      }
    });
  }, [onSave]);

  // Update decorations when comments change
  useEffect(() => {
    const editor = editorRef.current;
    if (!editor) return;

    const newDecorations = comments.map((c) => ({
      range: new editor.constructor.Range(c.line, 1, c.line, 1),
      options: {
        isWholeLine: true,
        className: "bg-amber-500/10",
        glyphMarginClassName: "line-comment-glyph",
        overviewRuler: { color: "#f59e0b", position: 4 },
      },
    }));

    decorationsRef.current = editor.deltaDecorations(
      decorationsRef.current,
      newDecorations,
    );
  }, [comments]);

  // Bind to Yjs when ytext is available
  useEffect(() => {
    const editor = editorRef.current;
    if (!editor || !ytext) return;

    let binding: any;
    const setupBinding = async () => {
      const { MonacoBinding } = await import("y-monaco");
      binding = new MonacoBinding(
        ytext,
        editor.getModel(),
        new Set([editor]),
        awareness,
      );
      bindingRef.current = binding;
    };
    setupBinding();

    return () => {
      if (binding) {
        binding.destroy();
        bindingRef.current = null;
      }
    };
  }, [ytext, awareness]);

  const lineComments = activeLine
    ? comments.filter((c) => c.line === activeLine)
    : [];

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b bg-card px-3 py-1.5">
        <span className="text-xs text-muted-foreground truncate max-w-[60%]">{path}</span>
        <div className="flex items-center gap-2">
          {ytext && (
            <span className="text-[10px] text-emerald-400 uppercase">Live</span>
          )}
          {readOnly && (
            <span className="text-[10px] text-muted-foreground uppercase">Read-only</span>
          )}
          {activeLine !== null && (
            <span className="text-[10px] text-amber-400 uppercase">
              Line {activeLine}
            </span>
          )}
          <Button size="sm" variant="ghost" className="h-7 px-2" onClick={onSave} disabled={saving || readOnly}>
            {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
            <span className="ml-1 text-xs">Save</span>
          </Button>
        </div>
      </div>

      {/* Inline comment panel for selected line */}
      {activeLine !== null && onAddComment && (
        <div className="border-b bg-card px-3 py-2 space-y-2 max-h-[180px] overflow-auto">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground">
              Comments on line {activeLine}
            </span>
            <Button size="icon" variant="ghost" className="h-5 w-5" onClick={() => setActiveLine(null)}>
              <X className="h-3 w-3" />
            </Button>
          </div>
          <div className="space-y-1.5">
            {lineComments.length === 0 && (
              <div className="text-xs text-muted-foreground/60">No comments yet. Click line number to add.</div>
            )}
            {lineComments.map((c) => (
              <div key={c.id} className="rounded border bg-muted/40 px-2 py-1.5 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-primary">{c.author}</span>
                  <div className="flex items-center gap-1">
                    <span className="text-[10px] text-muted-foreground/50">
                      {new Date(c.timestamp * 1000).toLocaleTimeString()}
                    </span>
                    {onDeleteComment && c.author === currentUser && (
                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-5 w-5"
                        onClick={() => onDeleteComment(c.id)}
                      >
                        <Trash2 className="h-3 w-3 text-muted-foreground" />
                      </Button>
                    )}
                  </div>
                </div>
                <div className="text-foreground mt-0.5">{c.text}</div>
              </div>
            ))}
          </div>
          <div className="flex gap-1">
            <Input
              placeholder="Add comment..."
              className="h-7 text-xs"
              value={newCommentText}
              onChange={(e) => setNewCommentText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && newCommentText.trim() && activeLine) {
                  onAddComment?.(activeLine, newCommentText.trim());
                  setNewCommentText("");
                }
              }}
            />
            <Button
              size="sm"
              className="h-7 px-2"
              disabled={!newCommentText.trim()}
              onClick={() => {
                if (newCommentText.trim() && activeLine) {
                  onAddComment?.(activeLine, newCommentText.trim());
                  setNewCommentText("");
                }
              }}
            >
              <MessageSquarePlus className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      )}

      <div className="flex-1 overflow-hidden">
        <Editor
          height="100%"
          language={getLanguageFromPath(path)}
          value={content}
          theme="vs-dark"
          onChange={(v) => onChange(v || "")}
          onMount={handleEditorDidMount}
          options={{
            readOnly: readOnly ?? false,
            minimap: { enabled: editorSettings.minimap },
            fontSize: editorSettings.fontSize,
            lineNumbers: editorSettings.lineNumbers,
            scrollBeyondLastLine: editorSettings.scrollBeyondLastLine,
            automaticLayout: true,
            tabSize: editorSettings.tabSize,
            wordWrap: editorSettings.wordWrap,
            glyphMargin: true,
          }}
          loading={<div className="flex h-full items-center justify-center text-sm text-muted-foreground">Loading editor...</div>}
        />
      </div>
    </div>
  );
}
