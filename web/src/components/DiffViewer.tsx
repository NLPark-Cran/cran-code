import { DiffEditor } from "@monaco-editor/react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Check, X } from "lucide-react";

interface DiffViewerProps {
  original: string;
  modified: string;
  path: string;
  onAccept: () => void;
  onReject: () => void;
}

export default function DiffViewer({ original, modified, path, onAccept, onReject }: DiffViewerProps) {
  const { t } = useTranslation();
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b bg-card px-3 py-2">
        <span className="text-xs text-muted-foreground truncate max-w-[50%]">{path}</span>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" className="h-7 gap-1" onClick={onReject}>
            <X className="h-3.5 w-3.5" />
            Reject
          </Button>
          <Button size="sm" className="h-7 gap-1" onClick={onAccept}>
            <Check className="h-3.5 w-3.5" />
            Accept
          </Button>
        </div>
      </div>
      <div className="flex-1 overflow-hidden">
        <DiffEditor
          original={original}
          modified={modified}
          language="plaintext"
          theme="vs-dark"
          options={{
            readOnly: true,
            minimap: { enabled: false },
            fontSize: 13,
            lineNumbers: "on",
            scrollBeyondLastLine: false,
            automaticLayout: true,
            renderSideBySide: true,
            wordWrap: "on",
          }}
          loading={<div className="flex h-full items-center justify-center text-sm text-muted-foreground">{t("project:loadingDiff")}</div>}
        />
      </div>
    </div>
  );
}
