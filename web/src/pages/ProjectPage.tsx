import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, Loader2, Users, GitBranch, FolderOpen, MessageSquare } from "lucide-react";
import { v2Api, type ProjectRes } from "@/lib/api/v2";
import { useAuthStore } from "@/stores/auth";

export default function ProjectPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { user } = useAuthStore();

  const [project, setProject] = useState<ProjectRes | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    v2Api.projects
      .get(projectId)
      .then((data) => setProject(data))
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load project"))
      .finally(() => setLoading(false));
  }, [projectId]);

  const userMembership = project?.members.find((m) => m.user_id === user?.id);

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
          <div className="flex items-center gap-3">
            <img src="/logo.png" alt="Cran" className="size-6" />
            <span className="font-semibold">Cran Code</span>
            <span className="text-muted-foreground">/</span>
            <Button
              variant="ghost"
              size="sm"
              className="h-8 px-2"
              onClick={() => navigate(`/team/${project?.team_id}`)}
            >
              <ArrowLeft className="mr-1 h-4 w-4" />
              {project?.name || "Project"}
            </Button>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted-foreground hidden sm:inline">
              {user?.display_name || user?.username || user?.email}
            </span>
            <Button variant="outline" size="sm" onClick={() => navigate("/")}>
              Chat
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8">
        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {loading ? (
          <div className="flex h-64 items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : project ? (
          <>
            <div className="mb-8">
              <h1 className="text-2xl font-bold">{project.name}</h1>
              <p className="text-muted-foreground">
                {project.description || "No description"}
              </p>
              <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
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

            {/* Placeholder workspace */}
            <div className="grid gap-6 lg:grid-cols-3">
              <Card className="lg:col-span-2">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <MessageSquare className="h-5 w-5" />
                    Chat Workspace
                  </CardTitle>
                  <CardDescription>
                    Start a coding session for this project
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
                    <p className="text-muted-foreground mb-4">
                      Editor and file tree integration coming soon
                    </p>
                    <Button onClick={() => navigate("/")}>
                      Open Chat
                    </Button>
                  </div>
                </CardContent>
              </Card>

              <div className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Members</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {project.members.map((m) => (
                      <div key={m.id} className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-secondary text-xs font-medium">
                            {(m.display_name || m.username).charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <p className="text-sm font-medium">
                              {m.display_name || m.username}
                            </p>
                            <p className="text-xs text-muted-foreground">{m.username}</p>
                          </div>
                        </div>
                        <Badge variant="secondary" className="text-xs">
                          {m.role}
                        </Badge>
                      </div>
                    ))}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Activity</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground">
                      Activity feed coming soon
                    </p>
                  </CardContent>
                </Card>
              </div>
            </div>
          </>
        ) : null}
      </main>
    </div>
  );
}
