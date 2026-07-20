import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useParams, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  Plus,
  FolderGit,
  ArrowLeft,
  Loader2,
  Users,
  Settings,
  GitBranch,
} from "lucide-react";
import { v2Api, type TeamRes, type ProjectRes } from "@/lib/api/v2";
import { roleKey } from "@/i18n";
import { EmptyState } from "@/components/empty-state";
import { useAuthStore } from "@/stores/auth";
import Layout from "@/components/Layout";
import MemberManagement from "@/components/MemberManagement";
import TeamProviderKeys from "@/components/TeamProviderKeys";

export default function TeamPage() {
  const { teamId } = useParams<{ teamId: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { user } = useAuthStore();

  const [team, setTeam] = useState<TeamRes | null>(null);
  const [projects, setProjects] = useState<ProjectRes[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [createOpen, setCreateOpen] = useState(false);
  const [createName, setCreateName] = useState("");
  const [createSlug, setCreateSlug] = useState("");
  const [createDesc, setCreateDesc] = useState("");
  const [createWorkDir, setCreateWorkDir] = useState("");
  const [createGitUrl, setCreateGitUrl] = useState("");
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const fetchData = async () => {
    if (!teamId) return;
    setLoading(true);
    setError(null);
    try {
      const [teamData, projectsData] = await Promise.all([
        v2Api.teams.get(teamId),
        v2Api.projects.list(teamId),
      ]);
      setTeam(teamData);
      setProjects(projectsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("teams:loadDataFailed"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [teamId]);

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!teamId || !createName.trim() || !createSlug.trim()) return;
    setCreateLoading(true);
    setCreateError(null);
    try {
      const project = await v2Api.projects.create({
        team_id: teamId,
        name: createName.trim(),
        slug: createSlug.trim().toLowerCase().replace(/\s+/g, "-"),
        description: createDesc.trim() || undefined,
        work_dir: createWorkDir.trim() || undefined,
        git_repo_url: createGitUrl.trim() || undefined,
      });
      setCreateOpen(false);
      setCreateName("");
      setCreateSlug("");
      setCreateDesc("");
      setCreateWorkDir("");
      setCreateGitUrl("");
      navigate(`/project/${project.id}`);
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : t("project:createFailed"));
    } finally {
      setCreateLoading(false);
    }
  };

  const generateSlug = (name: string) => {
    return name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "");
  };

  const userMembership = team?.members.find((m) => m.user_id === user?.id);
  const canCreateProject = userMembership?.role === "owner" || userMembership?.role === "admin";
  const canManageMembers = userMembership?.role === "owner" || userMembership?.role === "admin";

  const breadcrumbs = (
    <Button
      variant="ghost"
      size="sm"
      className="h-8 px-2"
      onClick={() => navigate("/dashboard")}
    >
      <ArrowLeft className="mr-1 h-4 w-4" />
      {t("nav:dashboard")}
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
      ) : team ? (
        <div className="grid gap-8 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-8">
            {/* Team header */}
            <div className="flex items-start justify-between gap-4">
              <div>
                <h1 className="text-2xl font-bold">{team.name}</h1>
                <p className="text-muted-foreground">
                  {team.description || t("common:noDescription")}
                </p>
                <div className="mt-2 flex items-center gap-4 text-sm text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <Users className="h-4 w-4" />
                    {t("common:memberCount", { count: team.members.length })}
                  </span>
                  <Badge variant="outline" className="text-xs">
                    {t(roleKey(userMembership?.role || "member"))}
                  </Badge>
                </div>
              </div>
              {canCreateProject && (
                <Dialog open={createOpen} onOpenChange={setCreateOpen}>
                  <DialogTrigger asChild>
                    <Button>
                      <Plus className="mr-2 h-4 w-4" />
                      {t("project:newProject")}
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="max-w-lg">
                    <DialogHeader>
                      <DialogTitle>{t("project:createTitle")}</DialogTitle>
                      <DialogDescription>
                        {t("project:createDesc")}
                      </DialogDescription>
                    </DialogHeader>
                    {createError && (
                      <Alert variant="destructive">
                        <AlertDescription>{createError}</AlertDescription>
                      </Alert>
                    )}
                    <form onSubmit={handleCreateProject} className="space-y-4">
                      <div className="space-y-2">
                        <label className="text-sm font-medium">{t("project:nameLabel")}</label>
                        <Input
                          placeholder="my-app"
                          value={createName}
                          onChange={(e) => {
                            setCreateName(e.target.value);
                            if (!createSlug || createSlug === generateSlug(createName)) {
                              setCreateSlug(generateSlug(e.target.value));
                            }
                          }}
                          required
                        />
                      </div>
                      <div className="space-y-2">
                        <label className="text-sm font-medium">{t("project:slugLabel")}</label>
                        <Input
                          placeholder="my-app"
                          value={createSlug}
                          onChange={(e) => setCreateSlug(e.target.value)}
                          required
                        />
                      </div>
                      <div className="space-y-2">
                        <label className="text-sm font-medium">{t("project:descLabel")}</label>
                        <Textarea
                          placeholder={t("project:descPlaceholder")}
                          value={createDesc}
                          onChange={(e) => setCreateDesc(e.target.value)}
                        />
                      </div>
                      <div className="space-y-2">
                        <label className="text-sm font-medium">{t("project:workDirLabel")}</label>
                        <Input
                          placeholder="/home/user/projects/my-app"
                          value={createWorkDir}
                          onChange={(e) => setCreateWorkDir(e.target.value)}
                        />
                      </div>
                      <div className="space-y-2">
                        <label className="text-sm font-medium">{t("project:gitUrlLabel")}</label>
                        <Input
                          placeholder="https://github.com/..."
                          value={createGitUrl}
                          onChange={(e) => setCreateGitUrl(e.target.value)}
                        />
                      </div>
                      <DialogFooter>
                        <Button type="submit" disabled={createLoading}>
                          {createLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                          {t("project:createButton")}
                        </Button>
                      </DialogFooter>
                    </form>
                  </DialogContent>
                </Dialog>
              )}
            </div>

            {/* Projects */}
            <div>
              <h2 className="text-lg font-semibold mb-4">{t("project:listTitle")}</h2>
              {projects.length === 0 ? (
                <Card className="border-dashed">
                  <CardContent className="py-8">
                    <EmptyState
                      icon={FolderGit}
                      title={t("project:emptyTitle")}
                      hint={t("project:emptyDesc")}
                      action={
                        canCreateProject ? (
                          <Button onClick={() => setCreateOpen(true)}>
                            <Plus className="mr-2 h-4 w-4" />
                            {t("project:newProject")}
                          </Button>
                        ) : undefined
                      }
                    />
                  </CardContent>
                </Card>
              ) : (
                <div className="grid gap-4 sm:grid-cols-2">
                  {projects.map((project) => (
                    <Card
                      key={project.id}
                      className="cursor-pointer transition-shadow hover:shadow-md"
                      onClick={() => navigate(`/project/${project.id}`)}
                    >
                      <CardHeader className="pb-3">
                        <div className="flex items-start justify-between">
                          <CardTitle className="text-lg">{project.name}</CardTitle>
                          <Settings className="h-4 w-4 text-muted-foreground" />
                        </div>
                        <CardDescription className="line-clamp-2">
                          {project.description || t("common:noDescription")}
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="flex flex-col gap-2 text-sm text-muted-foreground">
                          <div className="flex items-center gap-2">
                            <Users className="h-4 w-4" />
                            <span>{t("common:memberCount", { count: project.members.length })}</span>
                          </div>
                          {project.git_repo_url && (
                            <div className="flex items-center gap-2">
                              <GitBranch className="h-4 w-4" />
                              <span className="truncate">{project.git_repo_url}</span>
                            </div>
                          )}
                        </div>
                        <div className="mt-3 flex flex-wrap gap-1">
                          {project.members.slice(0, 3).map((m) => (
                            <Badge key={m.id} variant="secondary" className="text-xs">
                              {m.display_name || m.username}
                            </Badge>
                          ))}
                          {project.members.length > 3 && (
                            <Badge variant="secondary" className="text-xs">
                              +{project.members.length - 3}
                            </Badge>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Sidebar: Member Management */}
          <div>
            <MemberManagement
              members={team.members}
              resourceId={team.id}
              resourceType="team"
              canManage={canManageMembers}
              onChange={fetchData}
            />
            {canManageMembers && <TeamProviderKeys teamId={team.id} />}
          </div>
        </div>
      ) : null}
    </Layout>
  );
}
