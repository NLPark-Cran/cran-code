import { useState, useCallback } from "react";
import { ChevronRight, ChevronDown, FileText, Folder, FolderOpen } from "lucide-react";

export interface FsEntry {
  name: string;
  path: string;
  type: string;
  size?: number;
}

interface FileTreeNodeProps {
  entry: FsEntry;
  depth: number;
  selectedPath: string | null;
  onSelect: (path: string, type: string) => void;
  loadChildren: (path: string) => Promise<FsEntry[]>;
}

function FileTreeNode({ entry, depth, selectedPath, onSelect, loadChildren }: FileTreeNodeProps) {
  const [expanded, setExpanded] = useState(false);
  const [children, setChildren] = useState<FsEntry[] | null>(null);
  const [loading, setLoading] = useState(false);
  const isSelected = selectedPath === entry.path;
  const isDir = entry.type === "directory";

  const toggle = useCallback(async () => {
    if (!isDir) {
      onSelect(entry.path, entry.type);
      return;
    }
    if (expanded) {
      setExpanded(false);
      return;
    }
    if (children === null) {
      setLoading(true);
      try {
        const data = await loadChildren(entry.path);
        setChildren(data);
      } catch {
        setChildren([]);
      } finally {
        setLoading(false);
      }
    }
    setExpanded(true);
    onSelect(entry.path, entry.type);
  }, [expanded, children, isDir, entry.path, entry.type, loadChildren, onSelect]);

  return (
    <div>
      <button
        onClick={toggle}
        className={`flex w-full items-center gap-1 rounded-sm px-1 py-0.5 text-sm hover:bg-accent ${
          isSelected ? "bg-accent" : ""
        }`}
        style={{ paddingLeft: `${depth * 12 + 4}px` }}
      >
        {isDir ? (
          expanded ? (
            <ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
          )
        ) : (
          <span className="w-3.5 shrink-0" />
        )}
        {isDir ? (
          expanded ? (
            <FolderOpen className="h-4 w-4 shrink-0 text-amber-500" />
          ) : (
            <Folder className="h-4 w-4 shrink-0 text-amber-500" />
          )
        ) : (
          <FileText className="h-4 w-4 shrink-0 text-blue-400" />
        )}
        <span className="truncate">{entry.name}</span>
      </button>
      {isDir && expanded && (
        <div>
          {loading ? (
            <div className="py-1 pl-8 text-xs text-muted-foreground">Loading...</div>
          ) : children && children.length > 0 ? (
            children.map((child) => (
              <FileTreeNode
                key={child.path}
                entry={child}
                depth={depth + 1}
                selectedPath={selectedPath}
                onSelect={onSelect}
                loadChildren={loadChildren}
              />
            ))
          ) : (
            <div className="py-1 pl-8 text-xs text-muted-foreground">Empty</div>
          )}
        </div>
      )}
    </div>
  );
}

interface FileTreeProps {
  entries: FsEntry[];
  selectedPath: string | null;
  onSelect: (path: string, type: string) => void;
  loadChildren: (path: string) => Promise<FsEntry[]>;
}

export default function FileTree({ entries, selectedPath, onSelect, loadChildren }: FileTreeProps) {
  return (
    <div className="overflow-auto text-sm">
      {entries.map((entry) => (
        <FileTreeNode
          key={entry.path}
          entry={entry}
          depth={0}
          selectedPath={selectedPath}
          onSelect={onSelect}
          loadChildren={loadChildren}
        />
      ))}
    </div>
  );
}
