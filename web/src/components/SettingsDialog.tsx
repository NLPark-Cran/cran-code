"use client";

import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Switch } from "@/components/ui/switch";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import {
  useSettingsStore,
  DEFAULT_KEYBINDINGS,
  type EditorSettings,
} from "@/stores/settings";
import { RotateCcw, Keyboard, Code, Settings2 } from "lucide-react";
import { cn } from "@/lib/utils";

const KB_LABEL_KEYS: Record<string, string> = {
  save: "settings:kbSaveFile",
  send: "settings:kbSendMessage",
  newline: "settings:kbNewLine",
  "toggle-sidebar": "settings:kbToggleSidebar",
};

interface SettingsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function SettingsDialog({
  open,
  onOpenChange,
}: SettingsDialogProps) {
  const { editor, updateEditor, resetEditor } = useSettingsStore();
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<"editor" | "keybindings">("editor");

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Settings2 className="h-4 w-4" />
            {t("settings:title")}
          </DialogTitle>
        </DialogHeader>

        <div className="flex border-b">
          <button
            type="button"
            onClick={() => setActiveTab("editor")}
            className={cn(
              "flex items-center gap-1.5 px-3 py-2 text-sm border-b-2 transition-colors",
              activeTab === "editor"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground",
            )}
          >
            <Code className="h-3.5 w-3.5" />
            {t("settings:editorTab")}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("keybindings")}
            className={cn(
              "flex items-center gap-1.5 px-3 py-2 text-sm border-b-2 transition-colors",
              activeTab === "keybindings"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground",
            )}
          >
            <Keyboard className="h-3.5 w-3.5" />
            {t("settings:keybindingsTab")}
          </button>
        </div>

        {activeTab === "editor" && (
          <div className="space-y-4 mt-4">
            <div className="flex items-center justify-between">
              <span className="text-sm">{t("settings:fontSize")}</span>
              <Input
                type="number"
                min={8}
                max={32}
                className="w-20"
                value={editor.fontSize}
                onChange={(e) =>
                  updateEditor({ fontSize: Number(e.target.value) })
                }
              />
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm">{t("settings:tabSize")}</span>
              <Input
                type="number"
                min={1}
                max={8}
                className="w-20"
                value={editor.tabSize}
                onChange={(e) =>
                  updateEditor({ tabSize: Number(e.target.value) })
                }
              />
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm">{t("settings:wordWrap")}</span>
              <Select
                value={editor.wordWrap}
                onValueChange={(v) =>
                  updateEditor({ wordWrap: v as EditorSettings["wordWrap"] })
                }
              >
                <SelectTrigger className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="on">{t("settings:wrapOn")}</SelectItem>
                  <SelectItem value="off">{t("settings:wrapOff")}</SelectItem>
                  <SelectItem value="wordWrapColumn">{t("settings:wrapColumn")}</SelectItem>
                  <SelectItem value="bounded">{t("settings:wrapBounded")}</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm">{t("settings:lineNumbers")}</span>
              <Select
                value={editor.lineNumbers}
                onValueChange={(v) =>
                  updateEditor({
                    lineNumbers: v as EditorSettings["lineNumbers"],
                  })
                }
              >
                <SelectTrigger className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="on">{t("settings:lineOn")}</SelectItem>
                  <SelectItem value="off">{t("settings:lineOff")}</SelectItem>
                  <SelectItem value="relative">{t("settings:lineRelative")}</SelectItem>
                  <SelectItem value="interval">{t("settings:lineInterval")}</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm">{t("settings:minimap")}</span>
              <Switch
                checked={editor.minimap}
                onCheckedChange={(v) => updateEditor({ minimap: v })}
              />
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm">{t("settings:scrollBeyond")}</span>
              <Switch
                checked={editor.scrollBeyondLastLine}
                onCheckedChange={(v) =>
                  updateEditor({ scrollBeyondLastLine: v })
                }
              />
            </div>

            <div className="pt-2 flex justify-end">
              <Button
                variant="ghost"
                size="sm"
                onClick={resetEditor}
                className="gap-1"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                {t("settings:resetDefaults")}
              </Button>
            </div>
          </div>
        )}

        {activeTab === "keybindings" && (
          <div className="mt-4">
            <div className="rounded-md border">
              <div className="grid grid-cols-[1fr_auto] gap-4 px-3 py-2 text-xs font-medium text-muted-foreground border-b bg-muted/30">
                <span>{t("settings:actionCol")}</span>
                <span>{t("settings:shortcutCol")}</span>
              </div>
              {DEFAULT_KEYBINDINGS.map((kb) => (
                <div
                  key={kb.id}
                  className="grid grid-cols-[1fr_auto] gap-4 px-3 py-2 text-sm border-b last:border-0 items-center"
                >
                  <span>{KB_LABEL_KEYS[kb.id] ? t(KB_LABEL_KEYS[kb.id]) : kb.label}</span>
                  <div className="flex gap-1">
                    {kb.keys.map((k) => (
                      <kbd
                        key={k}
                        className="inline-flex items-center rounded border bg-muted px-1.5 py-0.5 text-[10px] font-mono"
                      >
                        {k}
                      </kbd>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
