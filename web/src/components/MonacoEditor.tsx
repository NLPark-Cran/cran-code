import { useRef, useCallback, useEffect } from "react";
import Editor from "@monaco-editor/react";
import { Button } from "@/components/ui/button";
import { Save, Loader2 } from "lucide-react";
import type * as Y from "yjs";

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
}: MonacoEditorProps) {
  const editorRef = useRef<any>(null);
  const bindingRef = useRef<any>(null);

  const handleEditorDidMount = useCallback((editor: any) => {
    editorRef.current = editor;
    editor.addCommand(0x800 | 3, () => onSave());
  }, [onSave]);

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
        awareness
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
          <Button size="sm" variant="ghost" className="h-7 px-2" onClick={onSave} disabled={saving || readOnly}>
            {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
            <span className="ml-1 text-xs">Save</span>
          </Button>
        </div>
      </div>
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
            minimap: { enabled: false },
            fontSize: 13,
            lineNumbers: "on",
            scrollBeyondLastLine: false,
            automaticLayout: true,
            tabSize: 2,
            wordWrap: "on",
          }}
          loading={<div className="flex h-full items-center justify-center text-sm text-muted-foreground">Loading editor...</div>}
        />
      </div>
    </div>
  );
}
