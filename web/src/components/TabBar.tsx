import { X, FileText } from "lucide-react";

export interface EditorTab {
  path: string;
  name: string;
  modified: boolean;
}

interface TabBarProps {
  tabs: EditorTab[];
  activePath: string | null;
  onSelect: (path: string) => void;
  onClose: (path: string) => void;
}

export default function TabBar({ tabs, activePath, onSelect, onClose }: TabBarProps) {
  if (tabs.length === 0) return null;

  return (
    <div className="flex h-9 items-end gap-0.5 overflow-x-auto border-b bg-card px-1">
      {tabs.map((tab) => {
        const isActive = tab.path === activePath;
        return (
          <button
            key={tab.path}
            onClick={() => onSelect(tab.path)}
            className={`group flex max-w-[180px] shrink-0 items-center gap-1.5 rounded-t-md border border-b-0 px-3 py-1.5 text-xs transition-colors ${
              isActive
                ? "border-border bg-background text-foreground"
                : "border-transparent bg-muted text-muted-foreground hover:bg-accent"
            }`}
          >
            <FileText className="h-3 w-3 shrink-0" />
            <span className="truncate">
              {tab.name}
              {tab.modified && <span className="ml-0.5">•</span>}
            </span>
            <span
              onClick={(e) => {
                e.stopPropagation();
                onClose(tab.path);
              }}
              className="ml-1 flex h-4 w-4 shrink-0 items-center justify-center rounded-sm opacity-0 transition-opacity hover:bg-destructive/20 hover:text-destructive group-hover:opacity-100"
            >
              <X className="h-3 w-3" />
            </span>
          </button>
        );
      })}
    </div>
  );
}
