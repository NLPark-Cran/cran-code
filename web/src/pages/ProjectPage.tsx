import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, Loader2, Users, GitBranch, FolderOpen, MessageSquare } from "lucide-react";
import { v2Api, type ProjectRes } from "@/lib/api/v2";
import { useAuthStore } from "@/stores/auth";
import Layout from "@/components/Layout";
import MemberManagement from "@/components/MemberManagement";
import ActivityStream from "@/components/ActivityStream";

export default function ProjectPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { user } = useAuthStore();

  const [project, setProject] = useState<ProjectRes | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  useEffect(() => {
    fetchProject();
  }, [projectId]);

  const userMembership = project?.members.find((m) => m.user_id === user?.id);
  const canManageMembers =
    userMembership?.role === "owner" || userMembership?.role === "admin";

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

          <div className="grid gap-6 lg:grid-cols-3">
            {/* Main workspace area */}
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

            {/* Sidebar */}
            <div className="space-y-6">
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
