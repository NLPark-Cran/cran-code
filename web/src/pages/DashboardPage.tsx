import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
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
import { Plus, Users, ArrowRight, Loader2 } from "lucide-react";
import { v2Api, type TeamRes } from "@/lib/api/v2";
import { EmptyState } from "@/components/empty-state";
import Layout from "@/components/Layout";

export default function DashboardPage() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [teams, setTeams] = useState<TeamRes[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [createOpen, setCreateOpen] = useState(false);
  const [createName, setCreateName] = useState("");
  const [createSlug, setCreateSlug] = useState("");
  const [createDesc, setCreateDesc] = useState("");
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const fetchTeams = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await v2Api.teams.list();
      setTeams(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("teams:loadFailed"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTeams();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createName.trim() || !createSlug.trim()) return;
    setCreateLoading(true);
    setCreateError(null);
    try {
      const team = await v2Api.teams.create({
        name: createName.trim(),
        slug: createSlug.trim().toLowerCase().replace(/\s+/g, "-"),
        description: createDesc.trim() || undefined,
      });
      setCreateOpen(false);
      setCreateName("");
      setCreateSlug("");
      setCreateDesc("");
      navigate(`/team/${team.id}`);
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : t("teams:createFailed"));
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

  return (
    <Layout>
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{t("teams:title")}</h1>
          <p className="text-muted-foreground">
            {t("teams:subtitle")}
          </p>
        </div>
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              {t("teams:newTeam")}
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{t("teams:createTitle")}</DialogTitle>
              <DialogDescription>
                {t("teams:createDesc")}
              </DialogDescription>
            </DialogHeader>
            {createError && (
              <Alert variant="destructive">
                <AlertDescription>{createError}</AlertDescription>
              </Alert>
            )}
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">{t("teams:nameLabel")}</label>
                <Input
                  placeholder={t("teams:namePlaceholder")}
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
                <label className="text-sm font-medium">{t("teams:slugLabel")}</label>
                <Input
                  placeholder="my-team"
                  value={createSlug}
                  onChange={(e) => setCreateSlug(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">{t("teams:descLabel")}</label>
                <Textarea
                  placeholder={t("teams:descPlaceholder")}
                  value={createDesc}
                  onChange={(e) => setCreateDesc(e.target.value)}
                />
              </div>
              <DialogFooter>
                <Button type="submit" disabled={createLoading}>
                  {createLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  {t("teams:createButton")}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : teams.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="py-8">
            <EmptyState
              icon={Users}
              title={t("teams:emptyTitle")}
              hint={t("teams:emptyDesc")}
              action={
                <Button onClick={() => setCreateOpen(true)}>
                  <Plus className="mr-2 h-4 w-4" />
                  {t("teams:createButton")}
                </Button>
              }
            />
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {teams.map((team) => (
            <Card
              key={team.id}
              className="cursor-pointer transition-shadow hover:shadow-md"
              onClick={() => navigate(`/team/${team.id}`)}
            >
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <CardTitle className="text-lg">{team.name}</CardTitle>
                  <ArrowRight className="h-4 w-4 text-muted-foreground" />
                </div>
                <CardDescription className="line-clamp-2">
                  {team.description || t("common:noDescription")}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Users className="h-4 w-4" />
                  <span>{t("common:memberCount", { count: team.members.length })}</span>
                </div>
                <div className="mt-2 flex flex-wrap gap-1">
                  {team.members.slice(0, 3).map((m) => (
                    <Badge key={m.id} variant="secondary" className="text-xs">
                      {m.display_name || m.username}
                    </Badge>
                  ))}
                  {team.members.length > 3 && (
                    <Badge variant="secondary" className="text-xs">
                      +{team.members.length - 3}
                    </Badge>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </Layout>
  );
}
