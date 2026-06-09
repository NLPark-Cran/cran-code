import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, Loader2, Users, GitBranch, FolderOpen } from "lucide-react";
import * as Y from "yjs";
import { v2Api, type ProjectRes, type FsEntry } from "@/lib/api/v2";
import { useAuthStore } from "@/stores/auth";
import { useYjsCollab } from "@/hooks/useYjsCollab";
import Layout from "@/components/Layout";
import MemberManagement from "@/components/MemberManagement";
import ActivityStream from "@/components/ActivityStream";
import FileTree from "@/components/FileTree";
import MonacoEditor from "@/components/MonacoEditor";
import TabBar, { type EditorTab } from "@/components/TabBar";
import Terminal from "@/components/Terminal";
import GitPanel from "@/components/GitPanel";

export default function ProjectPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { user } = useAuthStore();

  const [project, setProject] = useState<ProjectRes | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [rootEntries, setRootEntries] = useState<FsEntry[]>([]);
  const [fsLoading, setFsLoading] = useState(false);
  const [fsError, setFsError] = useState<string | null>(null);

  const [tabs, setTabs] = useState<EditorTab[]>([]);
  const [activePath, setActivePath] = useState<string | null>(null);
  const [fileContents, setFileContents] = useState<Record<string, string>>({});
  const [modifiedPaths, setModifiedPaths] = useState<Set<string>>(new Set());
  const [savingPath, setSavingPath] = useState<string | null>(null);

  const { provider } = useYjsCollab(projectId, user?.display_name || user?.username || "User");
  const yTextsRef = useRef<Record<string, Y.Text>>({});

  const fetchProject = async () => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await v2Api.projects.get(projectId);
      setProject(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load project");
    } finally {
      setLoading(false);
    }
  };

  const loadRootEntries = useCallback(async () => {
    if (!projectId) return;
    setFsLoading(true);
    setFsError(null);
    try {
      const data = await v2Api.fs.list(projectId, "");
      setRootEntries(data.entries);
    } catch (err) {
      setFsError(err instanceof Error ? err.message : "Failed to load files");
    } finally {
      setFsLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchProject();
    loadRootEntries();
  }, [projectId, loadRootEntries]);

  const loadChildren = useCallback(
    async (path: string) => {
      if (!projectId) return [];
      const data = await v2Api.fs.list(projectId, path);
      return data.entries;
    },
    [projectId]
  );

  const openFile = useCallback(
    async (path: string) => {
      if (!projectId) return;
      // Already open?
      if (tabs.find((t) => t.path === path)) {
        setActivePath(path);
        return;
      }
      try {
        const data = await v2Api.fs.read(projectId, path);
        const name = path.split("/").pop() || path;
        setTabs((prev) => [...prev, { path, name, modified: false }]);
        setFileContents((prev) => ({ ...prev, [path]: data.content }));
        setActivePath(path);

        // Create Y.Text for this file if Yjs is available
        if (provider) {
          const doc = provider.getDoc();
          const ytext = doc.getText(`file:${path}`);
          if (ytext.length === 0 && data.content) {
            ytext.insert(0, data.content);
          }
          yTextsRef.current[path] = ytext;
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to open file");
      }
    },
    [projectId, tabs, provider]
  );

  const handleTreeSelect = useCallback(
    (path: string, type: string) => {
      if (type === "file") {
        openFile(path);
      }
    },
    [openFile]
  );

  const handleTabSelect = useCallback((path: string) => {
    setActivePath(path);
  }, []);

  const handleTabClose = useCallback((path: string) => {
    setTabs((prev) => {
      const next = prev.filter((t) => t.path !== path);
      if (activePath === path) {
        setActivePath(next.length > 0 ? next[next.length - 1].path : null);
      }
      return next;
    });
    setFileContents((prev) => {
      const next = { ...prev };
      delete next[path];
      return next;
    });
    setModifiedPaths((prev) => {
      const next = new Set(prev);
      next.delete(path);
      return next;
    });
    delete yTextsRef.current[path];
  }, [activePath]);

  const handleEditorChange = useCallback((path: string, value: string) => {
    setFileContents((prev) => ({ ...prev, [path]: value }));
    setModifiedPaths((prev) => {
      const next = new Set(prev);
      if (prev.has(path)) return prev;
      next.add(path);
      return next;
    });
    setTabs((prev) =>
      prev.map((t) => (t.path === path ? { ...t, modified: true } : t))
    );
  }, []);

  const handleSave = useCallback(
    async (path: string) => {
      if (!projectId) return;
      setSavingPath(path);
      try {
        await v2Api.fs.write(projectId, path, fileContents[path] || "");
        setModifiedPaths((prev) => {
          const next = new Set(prev);
          next.delete(path);
          return next;
        });
        setTabs((prev) =>
          prev.map((t) => (t.path === path ? { ...t, modified: false } : t))
        );
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to save file");
      } finally {
        setSavingPath(null);
      }
    },
    [projectId, fileContents]
  );

  const userMembership = project?.members.find((m) => m.user_id === user?.id);
  const canManageMembers =
    userMembership?.role === "owner" || userMembership?.role === "admin";

  const [showTerminal, setShowTerminal] = useState(false);

  const breadcrumbs = (
    <Button
      variant="ghost"
      size="sm"
      className="h-8 px-2"
      onClick={() => navigate(`/team/${project?.team_id}`)}
    >
      <ArrowLeft className="mr-1 h-4 w-4" />
      {project?.name || "Project"}
    </Button>
  );

  return (
    <Layout breadcrumbs={breadcrumbs}>
      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : project ? (
        <>
          <div className="mb-4">
            <h1 className="text-2xl font-bold">{project.name}</h1>
            <p className="text-muted-foreground">
              {project.description || "No description"}
            </p>
            <div className="mt-1 flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
              <span className="flex items-center gap-1">
                <Users className="h-4 w-4" />
                {project.members.length} members
              </span>
              {project.work_dir && (
                <span className="flex items-center gap-1">
                  <FolderOpen className="h-4 w-4" />
                  {project.work_dir}
                </span>
              )}
              {project.git_repo_url && (
                <span className="flex items-center gap-1">
                  <GitBranch className="h-4 w-4" />
                  <span className="truncate max-w-[200px]">{project.git_repo_url}</span>
                </span>
              )}
              <Badge variant="outline" className="text-xs">
                {userMembership?.role || "member"}
              </Badge>
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-4" style={{ height: "calc(100vh - 240px)" }}>
            {/* File tree */}
            <Card className="lg:col-span-1 flex flex-col overflow-hidden">
              <div className="border-b px-3 py-2 text-xs font-semibold uppercase text-muted-foreground">
                Files
              </div>
              <div className="flex-1 overflow-auto p-1">
                {fsLoading ? (
                  <div className="flex h-32 items-center justify-center">
                    <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                  </div>
                ) : fsError ? (
                  <p className="p-2 text-xs text-destructive">{fsError}</p>
                ) : (
                  <FileTree
                    entries={rootEntries}
                    selectedPath={activePath}
                    onSelect={handleTreeSelect}
                    loadChildren={loadChildren}
                  />
                )}
              </div>
            </Card>

            {/* Editor + tabs */}
            <Card className="lg:col-span-2 flex flex-col overflow-hidden">
              <TabBar
                tabs={tabs.map((t) => ({
                  ...t,
                  modified: modifiedPaths.has(t.path),
                }))}
                activePath={activePath}
                onSelect={handleTabSelect}
                onClose={handleTabClose}
              />
              <div className="flex-1 overflow-hidden">
                {activePath && fileContents[activePath] !== undefined ? (
                  <MonacoEditor
                    path={activePath}
                    content={fileContents[activePath]}
                    onChange={(v) => handleEditorChange(activePath, v)}
                    onSave={() => handleSave(activePath)}
                    saving={savingPath === activePath}
                  />
                ) : (
                  <div className="flex h-full flex-col items-center justify-center text-muted-foreground">
                    <p className="mb-2 text-sm">Select a file from the tree to start editing</p>
                    <Button size="sm" variant="outline" onClick={() => navigate("/")}>
                      Open Chat
                    </Button>
                  </div>
                )}
              </div>
            </Card>

            {/* Sidebar */}
            <div className="space-y-4 lg:col-span-1 overflow-auto">
              <Card>
                <CardContent className="pt-6">
                  <MemberManagement
                    members={project.members}
                    resourceId={project.id}
                    resourceType="project"
                    canManage={canManageMembers}
                    onChange={fetchProject}
                  />
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <GitPanel projectId={project.id} />
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <ActivityStream projectId={project.id} />
                </CardContent>
              </Card>
            </div>
          </div>
        </>
      ) : null}
    </Layout>
  );
}
