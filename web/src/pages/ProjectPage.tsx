import { useEffect, useState, useCallback, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useParams, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, Loader2, Users, GitBranch, FolderOpen } from "lucide-react";
import * as Y from "yjs";
import { v2Api, type ProjectRes, type FsEntry } from "@/lib/api/v2";
import { roleKey } from "@/i18n";
import { useAuthStore } from "@/stores/auth";
import { useTeamStore } from "@/stores/team";
import { useYjsCollab, type LineComment } from "@/hooks/useYjsCollab";
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
  const { t } = useTranslation();
  const { user } = useAuthStore();
  const { setSelectedTeamId } = useTeamStore();

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
  const [fileComments, setFileComments] = useState<LineComment[]>([]);
  const [uploading, setUploading] = useState(false);
  const [activityRefreshKey, setActivityRefreshKey] = useState(0);

  const { provider } = useYjsCollab(projectId, user?.display_name || user?.username || t("common:defaultUser"));
  const yTextsRef = useRef<Record<string, Y.Text>>({});
  const commentsObserverRef = useRef<(() => void) | null>(null);

  const fetchProject = async () => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await v2Api.projects.get(projectId);
      setProject(data);
      if (data.team_id) {
        setSelectedTeamId(data.team_id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t("project:loadFailed"));
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
      setFsError(err instanceof Error ? err.message : t("project:fsLoadFailed"));
    } finally {
      setFsLoading(false);
    }
  }, [projectId, t]);

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
        setError(err instanceof Error ? err.message : t("project:openFileFailed"));
      }
    },
    [projectId, tabs, provider, t]
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

  // Sync comments from Yjs when active file changes
  useEffect(() => {
    if (!provider || !activePath) {
      setFileComments([]);
      return;
    }
    const arr = provider.getComments(activePath);
    const update = () => {
      setFileComments(arr.toArray());
    };
    update();
    arr.observe(update);
    commentsObserverRef.current = () => arr.unobserve(update);
    return () => {
      commentsObserverRef.current?.();
      commentsObserverRef.current = null;
    };
  }, [provider, activePath]);

  const handleAddComment = useCallback(
    (line: number, text: string) => {
      if (!provider || !activePath || !user) return;
      provider.addComment(activePath, {
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        line,
        text,
        author: user.display_name || user.username || user.email || t("common:defaultUser"),
        timestamp: Date.now() / 1000,
      });
    },
    [provider, activePath, user, t]
  );

  const handleDeleteComment = useCallback(
    (id: string) => {
      if (!provider || !activePath) return;
      provider.deleteComment(activePath, id);
    },
    [provider, activePath]
  );

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
        setActivityRefreshKey((k) => k + 1);
      } catch (err) {
        setError(err instanceof Error ? err.message : t("project:saveFileFailed"));
      } finally {
        setSavingPath(null);
      }
    },
    [projectId, fileContents, t]
  );

  const handleUpload = useCallback(
    async (targetDir: string, files: FileList) => {
      if (!projectId || files.length === 0) return;
      setUploading(true);
      setError(null);
      try {
        const uploaded: string[] = [];
        for (const file of Array.from(files)) {
          const res = await v2Api.fs.upload(projectId, file, targetDir);
          uploaded.push(res.path);
        }
        await loadRootEntries();
        setActivityRefreshKey((k) => k + 1);
      } catch (err) {
        setError(err instanceof Error ? err.message : t("project:uploadFailed"));
      } finally {
        setUploading(false);
      }
    },
    [projectId, loadRootEntries, t]
  );

  const handleDownload = useCallback(
    async (path: string, name: string) => {
      if (!projectId) return;
      try {
        await v2Api.fs.download(projectId, path, name);
        setActivityRefreshKey((k) => k + 1);
      } catch (err) {
        setError(err instanceof Error ? err.message : t("project:downloadFailed"));
      }
    },
    [projectId, t]
  );

  const refreshAfterFsChange = useCallback(async () => {
    await loadRootEntries();
    setActivityRefreshKey((k) => k + 1);
  }, [loadRootEntries]);

  const handleCopy = useCallback(
    async (src: string, dst: string) => {
      if (!projectId) return;
      try {
        await v2Api.fs.copy(projectId, src, dst);
        await refreshAfterFsChange();
      } catch (err) {
        setError(err instanceof Error ? err.message : t("project:copyFailed"));
      }
    },
    [projectId, refreshAfterFsChange, t]
  );

  const handleMove = useCallback(
    async (src: string, dst: string) => {
      if (!projectId) return;
      try {
        await v2Api.fs.move(projectId, src, dst);
        await refreshAfterFsChange();
        if (activePath === src) {
          setActivePath(null);
          setTabs((prev) => prev.filter((t) => t.path !== src));
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : t("project:moveFailed"));
      }
    },
    [projectId, refreshAfterFsChange, activePath, t]
  );

  const handleDelete = useCallback(
    async (path: string) => {
      if (!projectId) return;
      try {
        await v2Api.fs.delete(projectId, path);
        await refreshAfterFsChange();
        if (activePath === path) {
          setActivePath(null);
          setTabs((prev) => prev.filter((t) => t.path !== path));
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : t("project:deleteFailed"));
      }
    },
    [projectId, refreshAfterFsChange, activePath, t]
  );

  const handleCompress = useCallback(
    async (path: string, archive: string) => {
      if (!projectId) return;
      try {
        await v2Api.fs.compress(projectId, path, archive);
        await refreshAfterFsChange();
      } catch (err) {
        setError(err instanceof Error ? err.message : t("project:compressFailed"));
      }
    },
    [projectId, refreshAfterFsChange, t]
  );

  const handleExtract = useCallback(
    async (archive: string, dest?: string) => {
      if (!projectId) return;
      try {
        await v2Api.fs.extract(projectId, archive, dest);
        await refreshAfterFsChange();
      } catch (err) {
        setError(err instanceof Error ? err.message : t("project:extractFailed"));
      }
    },
    [projectId, refreshAfterFsChange, t]
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
      {project?.name || t("project:defaultName")}
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
              {project.description || t("common:noDescription")}
            </p>
            <div className="mt-1 flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
              <span className="flex items-center gap-1">
                <Users className="h-4 w-4" />
                {t("common:memberCount", { count: project.members.length })}
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
                {t(roleKey(userMembership?.role || "member"))}
              </Badge>
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-4" style={{ height: "calc(100vh - 240px)" }}>
            {/* File tree */}
            <Card className="lg:col-span-1 flex flex-col overflow-hidden">
              <div className="border-b px-3 py-2 text-xs font-semibold uppercase text-muted-foreground">
                {t("project:filesTitle")}
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
                    onUpload={handleUpload}
                    onDownload={handleDownload}
                    onCopy={handleCopy}
                    onMove={handleMove}
                    onDelete={handleDelete}
                    onCompress={handleCompress}
                    onExtract={handleExtract}
                    uploading={uploading}
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
                    ytext={yTextsRef.current[activePath]}
                    awareness={provider?.getAwareness()}
                    comments={fileComments}
                    onAddComment={handleAddComment}
                    onDeleteComment={handleDeleteComment}
                    currentUser={user?.display_name || user?.username || user?.email}
                  />
                ) : (
                  <div className="flex h-full flex-col items-center justify-center text-muted-foreground">
                    <p className="mb-2 text-sm">{t("project:selectFileHint")}</p>
                    <Button size="sm" variant="outline" onClick={() => navigate("/")}>
                      {t("project:openChat")}
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
                  <ActivityStream projectId={project.id} refreshKey={activityRefreshKey} />
                </CardContent>
              </Card>
            </div>
          </div>
        </>
      ) : null}
    </Layout>
  );
}
