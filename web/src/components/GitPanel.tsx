import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { GitBranch, GitCommit, GitCompare, Loader2 } from "lucide-react";
import { v2Api } from "@/lib/api/v2";

interface GitPanelProps {
  projectId: string;
}

export default function GitPanel({ projectId }: GitPanelProps) {
  const [status, setStatus] = useState<any>(null);
  const [commits, setCommits] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [commitMsg, setCommitMsg] = useState("");
  const [committing, setCommitting] = useState(false);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [diffContent, setDiffContent] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, c] = await Promise.all([
        v2Api.git.status(projectId),
        v2Api.git.log(projectId, 10),
      ]);
      setStatus(s);
      setCommits(c);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load git data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [projectId]);

  const handleCommit = async () => {
    if (!commitMsg.trim()) return;
    setCommitting(true);
    try {
      await v2Api.git.commit(projectId, commitMsg.trim());
      setCommitMsg("");
      fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Commit failed");
    } finally {
      setCommitting(false);
    }
  };

  const handleShowDiff = async (path: string, staged: boolean) => {
    try {
      const data = await v2Api.git.diff(projectId, staged, path);
      setDiffContent(data[0]?.diff || "No diff");
      setSelectedFile(path);
    } catch {
      setDiffContent("Failed to load diff");
      setSelectedFile(path);
    }
  };

  if (loading) {
    return (
      <div className="flex h-32 items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return <p className="text-sm text-destructive">{error}</p>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <GitBranch className="h-4 w-4 text-muted-foreground" />
        <span className="text-sm font-medium">{status?.branch || "main"}</span>
        {status?.ahead > 0 && (
          <Badge variant="secondary" className="text-[10px]">+{status.ahead}</Badge>
        )}
        {status?.behind > 0 && (
          <Badge variant="secondary" className="text-[10px]">-{status.behind}</Badge>
        )}
      </div>

      {/* Commit message */}
      <div className="flex gap-2">
        <Input
          placeholder="Commit message..."
          value={commitMsg}
          onChange={(e) => setCommitMsg(e.target.value)}
          className="h-8 text-sm"
        />
        <Button size="sm" className="h-8" onClick={handleCommit} disabled={committing || status?.clean}>
          {committing && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
          Commit
        </Button>
      </div>

      {/* Status */}
      {status && !status.clean && (
        <div className="space-y-2">
          {status.staged.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold uppercase text-emerald-500">Staged</p>
              {status.staged.map((f: string) => (
                <button
                  key={f}
                  onClick={() => handleShowDiff(f, true)}
                  className={`block w-full truncate text-left text-xs hover:underline ${selectedFile === f ? "text-primary" : "text-muted-foreground"}`}
                >
                  {f}
                </button>
              ))}
            </div>
          )}
          {status.modified.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold uppercase text-amber-500">Modified</p>
              {status.modified.map((f: string) => (
                <button
                  key={f}
                  onClick={() => handleShowDiff(f, false)}
                  className={`block w-full truncate text-left text-xs hover:underline ${selectedFile === f ? "text-primary" : "text-muted-foreground"}`}
                >
                  {f}
                </button>
              ))}
            </div>
          )}
          {status.untracked.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold uppercase text-blue-500">Untracked</p>
              {status.untracked.map((f: string) => (
                <p key={f} className="truncate text-xs text-muted-foreground">{f}</p>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Diff view */}
      {diffContent && (
        <div className="rounded border bg-black/50 p-2">
          <div className="mb-1 flex items-center justify-between">
            <span className="text-[10px] text-muted-foreground">Diff</span>
            <button onClick={() => setDiffContent(null)} className="text-[10px] text-muted-foreground hover:text-foreground">Close</button>
          </div>
          <pre className="max-h-40 overflow-auto text-[10px] text-muted-foreground">{diffContent}</pre>
        </div>
      )}

      {/* Recent commits */}
      <div className="space-y-1">
        <p className="text-[10px] font-semibold uppercase text-muted-foreground">Recent commits</p>
        {commits.map((c) => (
          <div key={c.hash} className="flex items-start gap-1.5">
            <GitCommit className="mt-0.5 h-3 w-3 shrink-0 text-muted-foreground" />
            <div className="min-w-0">
              <p className="truncate text-xs">{c.message}</p>
              <p className="text-[10px] text-muted-foreground">
                {c.author} · {c.short_hash}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
