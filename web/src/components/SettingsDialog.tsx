"use client";

import { useState } from "react";
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

interface SettingsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function SettingsDialog({
  open,
  onOpenChange,
}: SettingsDialogProps) {
  const { editor, updateEditor, resetEditor } = useSettingsStore();
  const [activeTab, setActiveTab] = useState<"editor" | "keybindings">("editor");

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Settings2 className="h-4 w-4" />
            Settings
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
            Editor
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
            Keybindings
          </button>
        </div>

        {activeTab === "editor" && (
          <div className="space-y-4 mt-4">
            <div className="flex items-center justify-between">
              <span className="text-sm">Font size</span>
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
              <span className="text-sm">Tab size</span>
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
              <span className="text-sm">Word wrap</span>
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
                  <SelectItem value="on">On</SelectItem>
                  <SelectItem value="off">Off</SelectItem>
                  <SelectItem value="wordWrapColumn">Column</SelectItem>
                  <SelectItem value="bounded">Bounded</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm">Line numbers</span>
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
                  <SelectItem value="on">On</SelectItem>
                  <SelectItem value="off">Off</SelectItem>
                  <SelectItem value="relative">Relative</SelectItem>
                  <SelectItem value="interval">Interval</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm">Minimap</span>
              <Switch
                checked={editor.minimap}
                onCheckedChange={(v) => updateEditor({ minimap: v })}
              />
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm">Scroll beyond last line</span>
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
                Reset defaults
              </Button>
            </div>
          </div>
        )}

        {activeTab === "keybindings" && (
          <div className="mt-4">
            <div className="rounded-md border">
              <div className="grid grid-cols-[1fr_auto] gap-4 px-3 py-2 text-xs font-medium text-muted-foreground border-b bg-muted/30">
                <span>Action</span>
                <span>Shortcut</span>
              </div>
              {DEFAULT_KEYBINDINGS.map((kb) => (
                <div
                  key={kb.id}
                  className="grid grid-cols-[1fr_auto] gap-4 px-3 py-2 text-sm border-b last:border-0 items-center"
                >
                  <span>{kb.label}</span>
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
