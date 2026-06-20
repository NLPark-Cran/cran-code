import { useState, useCallback, useRef } from "react";
import {
  ChevronRight,
  ChevronDown,
  FileText,
  Folder,
  FolderOpen,
  Download,
  Upload,
  Copy,
  Scissors,
  Trash2,
  FileArchive,
  FileUp,
  Pencil,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";

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
  onDownload?: (path: string, name: string) => void;
  onUpload?: (targetDir: string, files: FileList) => void;
  onCopy?: (src: string, dst: string) => void;
  onMove?: (src: string, dst: string) => void;
  onDelete?: (path: string) => void;
  onCompress?: (path: string, archive: string) => void;
  onExtract?: (archive: string, dest?: string) => void;
}

function formatSize(bytes?: number): string {
  if (bytes === undefined || bytes === null) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function FileTreeNode({
  entry,
  depth,
  selectedPath,
  onSelect,
  loadChildren,
  onDownload,
  onUpload,
  onCopy,
  onMove,
  onDelete,
  onCompress,
  onExtract,
}: FileTreeNodeProps) {
  const [expanded, setExpanded] = useState(false);
  const [children, setChildren] = useState<FsEntry[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
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

  const handleDownload = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDownload?.(entry.path, entry.name);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    if (!(onUpload && e.dataTransfer.files.length)) return;
    const targetDir = isDir ? entry.path : "";
    onUpload(targetDir, e.dataTransfer.files);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (onUpload) setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };

  const promptDestination = (defaultValue: string) =>
    window.prompt("Enter destination path (relative to project root):", defaultValue);

  const handleCopy = () => {
    const dst = promptDestination(`${entry.path}-copy`);
    if (dst) onCopy?.(entry.path, dst);
  };

  const handleMove = () => {
    const dst = promptDestination(entry.path);
    if (dst) onMove?.(entry.path, dst);
  };

  const handleDelete = () => {
    if (window.confirm(`Delete "${entry.name}"?`)) {
      onDelete?.(entry.path);
    }
  };

  const handleCompress = () => {
    const archive = isDir
      ? `${entry.path}.zip`
      : `${entry.path.replace(/\.[^/.]+$/, "")}.zip`;
    const name = promptDestination(archive);
    if (name) onCompress?.(entry.path, name);
  };

  const handleExtract = () => {
    const dest = window.prompt(
      "Extract to directory (leave empty for same directory):",
      ""
    );
    onExtract?.(entry.path, dest || undefined);
  };

  const handleUploadHere = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.multiple = true;
    input.onchange = (e) => {
      const files = (e.target as HTMLInputElement).files;
      if (files?.length) onUpload?.(entry.path, files);
    };
    input.click();
  };

  const buttonContent = (
    <button
      type="button"
      onClick={toggle}
      className={`group flex w-full items-center gap-1 rounded-sm px-1 py-0.5 text-sm hover:bg-accent ${
        isSelected ? "bg-accent" : ""
      } ${isDragOver && isDir ? "ring-1 ring-inset ring-primary bg-primary/10" : ""}`}
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
      {!isDir && entry.size !== undefined && (
        <span className="ml-1 text-[10px] text-muted-foreground">
          {formatSize(entry.size)}
        </span>
      )}
      {!isDir && onDownload && (
        <span className="ml-auto shrink-0 opacity-0 group-hover:opacity-100">
          <Download
            className="h-3.5 w-3.5 text-muted-foreground hover:text-foreground"
            onClick={handleDownload}
          />
        </span>
      )}
    </button>
  );

  return (
    <div
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
    >
      <ContextMenu>
        <ContextMenuTrigger asChild>{buttonContent}</ContextMenuTrigger>
        <ContextMenuContent className="w-48">
          {isDir && onUpload && (
            <ContextMenuItem onClick={handleUploadHere}>
              <FileUp className="mr-2 h-4 w-4" />
              Upload files here
            </ContextMenuItem>
          )}
          {!isDir && onDownload && (
            <ContextMenuItem onClick={() => onDownload(entry.path, entry.name)}>
              <Download className="mr-2 h-4 w-4" />
              Download
            </ContextMenuItem>
          )}
          <ContextMenuItem onClick={handleCopy}>
            <Copy className="mr-2 h-4 w-4" />
            Copy
          </ContextMenuItem>
          <ContextMenuItem onClick={handleMove}>
            <Scissors className="mr-2 h-4 w-4" />
            Move / Rename
          </ContextMenuItem>
          <ContextMenuSeparator />
          <ContextMenuItem onClick={handleCompress}>
            <FileArchive className="mr-2 h-4 w-4" />
            Compress to .zip
          </ContextMenuItem>
          {!isDir && entry.name.endsWith(".zip") && onExtract && (
            <ContextMenuItem onClick={handleExtract}>
              <FolderOpen className="mr-2 h-4 w-4" />
              Extract .zip
            </ContextMenuItem>
          )}
          <ContextMenuSeparator />
          <ContextMenuItem onClick={handleDelete} variant="destructive">
            <Trash2 className="mr-2 h-4 w-4" />
            Delete
          </ContextMenuItem>
        </ContextMenuContent>
      </ContextMenu>

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
                onDownload={onDownload}
                onUpload={onUpload}
                onCopy={onCopy}
                onMove={onMove}
                onDelete={onDelete}
                onCompress={onCompress}
                onExtract={onExtract}
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
  onDownload?: (path: string, name: string) => void;
  onUpload?: (targetDir: string, files: FileList) => void;
  onCopy?: (src: string, dst: string) => void;
  onMove?: (src: string, dst: string) => void;
  onDelete?: (path: string) => void;
  onCompress?: (path: string, archive: string) => void;
  onExtract?: (archive: string, dest?: string) => void;
  uploading?: boolean;
}

export default function FileTree({
  entries,
  selectedPath,
  onSelect,
  loadChildren,
  onDownload,
  onUpload,
  onCopy,
  onMove,
  onDelete,
  onCompress,
  onExtract,
  uploading,
}: FileTreeProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (!(onUpload && e.dataTransfer.files.length)) return;
    onUpload("", e.dataTransfer.files);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (onUpload) setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!(onUpload && e.target.files?.length)) return;
    onUpload("", e.target.files);
    e.target.value = "";
  };

  return (
    <div
      className={`flex h-full flex-col overflow-auto text-sm ${
        isDragOver ? "bg-primary/5" : ""
      }`}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
    >
      {onUpload && (
        <div className="sticky top-0 z-10 border-b bg-card px-2 py-1.5">
          <Button
            variant="ghost"
            size="sm"
            className="h-7 w-full justify-start gap-2 text-xs"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            <Upload className="h-3.5 w-3.5" />
            {uploading ? "Uploading..." : "Upload files"}
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="hidden"
            onChange={handleFileInputChange}
          />
        </div>
      )}
      <div className="flex-1 p-1">
        {entries.map((entry) => (
          <FileTreeNode
            key={entry.path}
            entry={entry}
            depth={0}
            selectedPath={selectedPath}
            onSelect={onSelect}
            loadChildren={loadChildren}
            onDownload={onDownload}
            onUpload={onUpload}
            onCopy={onCopy}
            onMove={onMove}
            onDelete={onDelete}
            onCompress={onCompress}
            onExtract={onExtract}
          />
        ))}
        {entries.length === 0 && (
          <p className="p-2 text-xs text-muted-foreground">
            Drop files here or click "Upload files"
          </p>
        )}
      </div>
    </div>
  );
}
