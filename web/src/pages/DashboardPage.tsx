import { useEffect, useMemo, useState } from "react";
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
  DialogFooter,
} from "@/components/ui/dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  Activity,
  ArrowRight,
  BarChart3,
  ChevronRight,
  Coins,
  HeartPulse,
  Loader2,
  MessageSquarePlus,
  Plus,
  Server,
  Users,
} from "lucide-react";
import { apiClient } from "@/lib/apiClient";
import type { Session } from "@/lib/api/models";
import {
  v2Api,
  type ProviderListRes,
  type TeamRes,
  type UsageDailyPointRes,
} from "@/lib/api/v2";
import { EmptyState } from "@/components/empty-state";
import Layout from "@/components/Layout";
import { formatRelativeTime, getBrowserTimeZone } from "@/hooks/utils";

const RECENT_SESSIONS_LIMIT = 6;

const compact = (n: number): string =>
  new Intl.NumberFormat("en-US", { notation: "compact" }).format(n);

export default function DashboardPage() {
  const navigate = useNavigate();
  const { t } = useTranslation();

  const [teams, setTeams] = useState<TeamRes[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [todayUsage, setTodayUsage] = useState<UsageDailyPointRes[]>([]);
  const [providerData, setProviderData] = useState<ProviderListRes | null>(null);
  const [systemOk, setSystemOk] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [createOpen, setCreateOpen] = useState(false);
  const [createName, setCreateName] = useState("");
  const [createSlug, setCreateSlug] = useState("");
  const [createDesc, setCreateDesc] = useState("");
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError(null);
      // Independent fetches: providers list doubles as the health probe,
      // so a failure there must not blank the whole dashboard.
      const [teamsRes, sessionsRes, usageRes, providersRes] =
        await Promise.allSettled([
          v2Api.teams.list(),
          apiClient.sessions.listSessionsApiSessionsGet({ limit: 100 }),
          // tz-aware: days=1 with tz means the local calendar "today".
          v2Api.users.meUsageDaily(1, getBrowserTimeZone()),
          v2Api.providers.list(),
        ]);
      if (cancelled) return;

      if (teamsRes.status === "fulfilled") setTeams(teamsRes.value);
      if (sessionsRes.status === "fulfilled") setSessions(sessionsRes.value);
      if (usageRes.status === "fulfilled") setTodayUsage(usageRes.value);
      if (providersRes.status === "fulfilled") {
        setProviderData(providersRes.value);
        setSystemOk(true);
      } else {
        setSystemOk(false);
      }
      if (
        teamsRes.status === "rejected" &&
        sessionsRes.status === "rejected"
      ) {
        setError(t("dashboard:loadFailed"));
      }
      setLoading(false);
    };
    load().catch((err: unknown) => {
      console.error("[Dashboard] load failed:", err);
      if (!cancelled) {
        setError(t("dashboard:loadFailed"));
        setLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [t]);

  const generateSlug = (name: string) => {
    return name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "");
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!(createName.trim() && createSlug.trim())) return;
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

  const runningCount = useMemo(
    () => sessions.filter((s) => s.isRunning).length,
    [sessions],
  );
  const recentSessions = useMemo(
    () =>
      [...sessions]
        .sort((a, b) => b.lastUpdated.getTime() - a.lastUpdated.getTime())
        .slice(0, RECENT_SESSIONS_LIMIT),
    [sessions],
  );
  const todayTotals = useMemo(() => {
    const input = todayUsage.reduce((sum, r) => sum + r.input_tokens, 0);
    const output = todayUsage.reduce((sum, r) => sum + r.output_tokens, 0);
    return { input, output };
  }, [todayUsage]);

  const createTeamDialog = (
    <Dialog open={createOpen} onOpenChange={setCreateOpen}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("teams:createTitle")}</DialogTitle>
          <DialogDescription>{t("teams:createDesc")}</DialogDescription>
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
  );

  return (
    <Layout>
      <div className="mb-6">
        <h1 className="text-2xl font-bold">{t("nav:dashboard")}</h1>
        <p className="text-muted-foreground">{t("dashboard:subtitle")}</p>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="space-y-6">
          {/* Status cards row — compact strips */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card className="gap-2 py-3">
              <CardHeader className="pb-0">
                <CardDescription className="flex items-center gap-1.5">
                  <Activity className="h-3.5 w-3.5" />
                  {t("dashboard:runningSessions")}
                </CardDescription>
                <CardTitle className="text-xl tabular-nums">
                  {runningCount}
                </CardTitle>
              </CardHeader>
              <CardContent className="text-xs text-muted-foreground">
                {t("dashboard:totalSessions", { count: sessions.length })}
              </CardContent>
            </Card>
            <Card className="gap-2 py-3">
              <CardHeader className="pb-0">
                <CardDescription className="flex items-center gap-1.5">
                  <Coins className="h-3.5 w-3.5" />
                  {t("dashboard:todayTokens")}
                </CardDescription>
                <CardTitle className="text-xl tabular-nums">
                  {compact(todayTotals.input + todayTotals.output)}
                </CardTitle>
              </CardHeader>
              <CardContent className="text-xs text-muted-foreground tabular-nums">
                {t("dashboard:todayTokensHint", {
                  input: compact(todayTotals.input),
                  output: compact(todayTotals.output),
                })}
              </CardContent>
            </Card>
            <Card className="gap-2 py-3">
              <CardHeader className="pb-0">
                <CardDescription className="flex items-center gap-1.5">
                  <Server className="h-3.5 w-3.5" />
                  {t("dashboard:providers")}
                </CardDescription>
                <CardTitle className="text-xl tabular-nums">
                  {providerData?.providers.length ?? "—"}
                </CardTitle>
              </CardHeader>
              <CardContent className="truncate text-xs text-muted-foreground">
                {providerData
                  ? t("dashboard:defaultModelHint", {
                      model: providerData.default_model,
                    })
                  : "—"}
              </CardContent>
            </Card>
            <Card className="gap-2 py-3">
              <CardHeader className="pb-0">
                <CardDescription className="flex items-center gap-1.5">
                  <HeartPulse className="h-3.5 w-3.5" />
                  {t("dashboard:systemStatus")}
                </CardDescription>
                <CardTitle className="flex items-center gap-2 text-base">
                  <span
                    className={`inline-block size-2.5 rounded-full ${
                      systemOk ? "bg-emerald-500" : "bg-destructive"
                    }`}
                  />
                  {systemOk ? t("dashboard:systemOk") : t("dashboard:systemError")}
                </CardTitle>
              </CardHeader>
            </Card>
          </div>

          {/* Quick actions */}
          <div>
            <h2 className="mb-3 text-sm font-semibold text-muted-foreground">
              {t("dashboard:quickActions")}
            </h2>
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" onClick={() => navigate("/")}>
                <MessageSquarePlus className="mr-2 h-4 w-4" />
                {t("dashboard:newSession")}
              </Button>
              <Button variant="outline" onClick={() => setCreateOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                {t("teams:newTeam")}
              </Button>
              <Button
                variant="outline"
                onClick={() => navigate("/settings/providers")}
              >
                <Server className="mr-2 h-4 w-4" />
                {t("dashboard:providersSettings")}
              </Button>
              <Button
                variant="outline"
                onClick={() => navigate("/settings/usage")}
              >
                <BarChart3 className="mr-2 h-4 w-4" />
                {t("nav:usage")}
              </Button>
            </div>
          </div>

          {/* Recent sessions */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">{t("dashboard:recentSessions")}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-1">
              {recentSessions.length === 0 ? (
                <EmptyState
                  icon={MessageSquarePlus}
                  title={t("dashboard:emptySessions")}
                  hint={t("dashboard:emptySessionsHint")}
                />
              ) : (
                recentSessions.map((session) => (
                  <button
                    key={session.sessionId}
                    type="button"
                    onClick={() =>
                      navigate(`/?session=${encodeURIComponent(session.sessionId)}`)
                    }
                    className="flex w-full cursor-pointer items-center gap-3 rounded-md px-3 py-2 text-left transition-colors hover:bg-accent"
                  >
                    <span
                      className={`inline-block size-2 shrink-0 rounded-full ${
                        session.isRunning ? "bg-emerald-500" : "bg-muted-foreground/40"
                      }`}
                      title={session.isRunning ? t("dashboard:running") : undefined}
                    />
                    <span className="min-w-0 flex-1 truncate text-sm font-medium">
                      {session.title || t("sessions:untitled")}
                    </span>
                    {session.isRunning && (
                      <Badge variant="secondary" className="shrink-0 text-[10px]">
                        {t("dashboard:running")}
                      </Badge>
                    )}
                    <span className="shrink-0 text-xs text-muted-foreground tabular-nums">
                      {formatRelativeTime(session.lastUpdated)}
                    </span>
                    <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                  </button>
                ))
              )}
            </CardContent>
          </Card>

          {/* Teams section */}
          <div>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-muted-foreground">
                {t("teams:title")}
              </h2>
              <Button size="sm" variant="outline" onClick={() => setCreateOpen(true)}>
                <Plus className="mr-1.5 h-3.5 w-3.5" />
                {t("teams:newTeam")}
              </Button>
            </div>
            {teams.length === 0 ? (
              <Card className="border-dashed">
                <CardContent>
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
                        <span>
                          {t("common:memberCount", { count: team.members.length })}
                        </span>
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
          </div>
        </div>
      )}
      {createTeamDialog}
    </Layout>
  );
}
