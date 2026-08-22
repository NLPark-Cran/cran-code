import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Progress } from "@/components/ui/progress";
import { BarChart3, Coins, ExternalLink, Loader2, ServerCog, Users } from "lucide-react";
import { useNavigate } from "react-router-dom";
import {
  v2Api,
  type AdminUsageDailyPointRes,
  type TeamRes,
  type UsageDailyPointRes,
  type UsageSummaryRes,
} from "@/lib/api/v2";
import { useAuthStore } from "@/stores/auth";
import { useTeamStore } from "@/stores/team";
import { EmptyState } from "@/components/empty-state";
import Layout from "@/components/Layout";
import { StackedBarChart, type DailyBar } from "@/components/stacked-bar-chart";
import { getBrowserTimeZone } from "@/hooks/utils";

/* Semantic tokens so segment dots stay visible on both light and dark cards. */
const SOURCE_COLORS: Record<string, string> = {
  personal: "fill-primary",
  team: "fill-info",
  shared: "fill-warning",
};

const SOURCE_BADGE_VARIANT: Record<string, "secondary" | "outline" | "default"> = {
  personal: "secondary",
  team: "outline",
  shared: "default",
};

const formatTokens = (n: number): string =>
  new Intl.NumberFormat("en-US", { notation: "compact" }).format(n);

export default function UsagePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const isAdmin = user?.role === "admin";
  const selectedTeamId = useTeamStore((s) => s.selectedTeamId);

  const [days, setDays] = useState(30);
  const [daily, setDaily] = useState<UsageDailyPointRes[]>([]);
  const [summary, setSummary] = useState<UsageSummaryRes[]>([]);
  const [adminDaily, setAdminDaily] = useState<AdminUsageDailyPointRes[]>([]);
  const [teams, setTeams] = useState<TeamRes[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const browserTz = useMemo(() => getBrowserTimeZone(), []);
  const selectedTeam = teams.find((team) => team.id === selectedTeamId);
  // Team usage buckets by the team's configured timezone when set.
  const effectiveTeamTz = selectedTeam?.timezone ?? browserTz;

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const [dailyRes, summaryRes] = await Promise.all([
          v2Api.users.meUsageDaily(days, browserTz),
          v2Api.users.meUsage(),
        ]);
        if (cancelled) return;
        setDaily(dailyRes);
        setSummary(summaryRes);
        if (isAdmin) {
          // Teams first so the selected team's timezone can drive bucketing.
          const teamsRes = await v2Api.teams.list();
          if (cancelled) return;
          setTeams(teamsRes);
          const team = teamsRes.find((item) => item.id === selectedTeamId);
          const tz = team?.timezone ?? browserTz;
          setAdminDaily(await v2Api.admin.usage(days, tz));
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : t("usage:loadFailed"));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load().catch((err: unknown) => {
      console.error("[UsagePage] load failed:", err);
    });
    return () => {
      cancelled = true;
    };
  }, [days, isAdmin, selectedTeamId, browserTz, t]);

  const sourceLabel = useCallback(
    (source: string) =>
      source === "personal"
        ? t("usage:sourcePersonal")
        : source === "team"
          ? t("usage:sourceTeam")
          : t("usage:sourceShared"),
    [t],
  );

  const totals = useMemo(() => {
    const input = daily.reduce((sum, r) => sum + r.input_tokens, 0);
    const output = daily.reduce((sum, r) => sum + r.output_tokens, 0);
    const providers = new Set(daily.map((r) => r.provider_key)).size;
    return { input, output, providers };
  }, [daily]);

  const bars = useMemo<DailyBar[]>(() => {
    const byDate = new Map<string, Map<string, number>>();
    for (const row of daily) {
      const total = row.input_tokens + row.output_tokens;
      const sources = byDate.get(row.date) ?? new Map<string, number>();
      sources.set(row.source, (sources.get(row.source) ?? 0) + total);
      byDate.set(row.date, sources);
    }
    // Fill every day in the window so gaps render as zero-height bars
    const result: DailyBar[] = [];
    const now = new Date();
    for (let i = days - 1; i >= 0; i--) {
      const d = new Date(now.getTime() - i * 86_400_000);
      const date = d.toISOString().slice(0, 10);
      const sources = byDate.get(date);
      result.push({
        date,
        segments: ["personal", "team", "shared"]
          .filter((s) => (sources?.get(s) ?? 0) > 0)
          .map((s) => ({
            key: s,
            label: sourceLabel(s),
            value: sources?.get(s) ?? 0,
            colorClass: SOURCE_COLORS[s],
          })),
      });
    }
    return result;
  }, [daily, days, sourceLabel]);

  const adminByUser = useMemo(() => {
    const map = new Map<string, { input: number; output: number; providers: Set<string> }>();
    for (const row of adminDaily) {
      const entry = map.get(row.username) ?? { input: 0, output: 0, providers: new Set<string>() };
      entry.input += row.input_tokens;
      entry.output += row.output_tokens;
      entry.providers.add(row.provider_key);
      map.set(row.username, entry);
    }
    return [...map.entries()].sort((a, b) => b[1].input + b[1].output - (a[1].input + a[1].output));
  }, [adminDaily]);

  const isEmpty = daily.length === 0 && summary.length === 0;

  return (
    <Layout>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{t("usage:title")}</h1>
          <p className="text-muted-foreground">{t("usage:subtitle")}</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant={days === 7 ? "default" : "outline"}
            size="sm"
            onClick={() => setDays(7)}
          >
            {t("usage:period7")}
          </Button>
          <Button
            variant={days === 30 ? "default" : "outline"}
            size="sm"
            onClick={() => setDays(30)}
          >
            {t("usage:period30")}
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {loading ? (
        <div className="flex justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : isEmpty ? (
        <Card className="border-dashed">
          <CardContent>
            <EmptyState
              icon={BarChart3}
              title={t("usage:emptyTitle")}
              hint={t("usage:emptyHint")}
            />
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {/* Summary cards */}
          <div className="grid gap-4 sm:grid-cols-3">
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>{t("usage:totalInput")}</CardDescription>
                <CardTitle className="text-2xl tabular-nums">
                  {formatTokens(totals.input)}
                </CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>{t("usage:totalOutput")}</CardDescription>
                <CardTitle className="text-2xl tabular-nums">
                  {formatTokens(totals.output)}
                </CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>{t("usage:activeProviders")}</CardDescription>
                <CardTitle className="text-2xl tabular-nums">
                  {totals.providers}
                </CardTitle>
              </CardHeader>
            </Card>
          </div>

          {/* Daily stacked bar chart (by key source) */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">{t("usage:dailyChart")}</CardTitle>
              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                {(["personal", "team", "shared"] as const).map((s) => (
                  <span key={s} className="inline-flex items-center gap-1.5">
                    <span className={`inline-block size-2.5 rounded-sm ${SOURCE_COLORS[s].replace("fill-", "bg-")}`} />
                    {sourceLabel(s)}
                  </span>
                ))}
              </div>
            </CardHeader>
            <CardContent>
              <StackedBarChart bars={bars} title={t("usage:dailyChart")} />
            </CardContent>
          </Card>

          {/* Per-provider table with quota */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">{t("usage:perProvider")}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {summary.map((row) => {
                const usedPct =
                  row.quota_tokens !== null && row.remaining_tokens !== null && row.quota_tokens > 0
                    ? Math.min(
                        100,
                        Math.round(
                          ((row.quota_tokens - row.remaining_tokens) / row.quota_tokens) * 100,
                        ),
                      )
                    : null;
                return (
                  <div
                    key={`${row.provider_key}:${row.source}`}
                    className="rounded-md border px-3 py-2 space-y-2"
                  >
                    <div className="flex items-center justify-between gap-2 text-sm">
                      <div className="flex items-center gap-2 min-w-0">
                        <Coins className="h-4 w-4 text-muted-foreground shrink-0" />
                        <span className="font-mono truncate">{row.provider_key}</span>
                        <Badge variant={SOURCE_BADGE_VARIANT[row.source] ?? "outline"}>
                          {sourceLabel(row.source)}
                        </Badge>
                      </div>
                      <span className="text-muted-foreground tabular-nums shrink-0">
                        {t("providers:tokensInOut", {
                          input: formatTokens(row.input_tokens),
                          output: formatTokens(row.output_tokens),
                        })}
                      </span>
                    </div>
                    {usedPct !== null ? (
                      <div className="flex items-center gap-3">
                        <Progress value={usedPct} className="h-1.5 bg-muted" />
                        <span className="text-xs text-muted-foreground tabular-nums shrink-0">
                          {t("usage:quotaUsed", { percent: usedPct })}
                          {row.remaining_tokens !== null &&
                            ` · ${t("providers:remaining", { count: formatTokens(row.remaining_tokens) })}`}
                        </span>
                      </div>
                    ) : row.source === "shared" ? (
                      <p className="text-xs text-muted-foreground">
                        {t("usage:quotaUnlimited")}
                      </p>
                    ) : null}
                  </div>
                );
              })}
            </CardContent>
          </Card>

          {/* Admin: all users */}
          {isAdmin && (
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <ServerCog className="h-4 w-4 text-muted-foreground" />
                    <CardTitle className="text-lg">{t("usage:teamUsage")}</CardTitle>
                  </div>
                  {selectedTeam && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 gap-1 px-2 text-xs text-muted-foreground"
                      onClick={() => navigate(`/team/${selectedTeam.id}`)}
                    >
                      {selectedTeam.name}
                      <ExternalLink className="h-3 w-3" />
                    </Button>
                  )}
                </div>
                <CardDescription>
                  {t("usage:teamUsageDesc")}
                  <span className="ml-2 text-xs text-muted-foreground/70">
                    {t("usage:timezoneCaption", { tz: effectiveTeamTz })}
                  </span>
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                {adminByUser.length === 0 ? (
                  <p className="text-sm text-muted-foreground">{t("usage:emptyTitle")}</p>
                ) : (
                  adminByUser.map(([username, entry]) => (
                    <div
                      key={username}
                      className="flex items-center justify-between rounded-md border px-3 py-2 text-sm"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <Users className="h-4 w-4 text-muted-foreground shrink-0" />
                        <span className="font-medium truncate">{username}</span>
                        <Badge variant="outline" className="shrink-0">
                          {entry.providers.size} {t("usage:providers")}
                        </Badge>
                      </div>
                      <span className="text-muted-foreground tabular-nums shrink-0">
                        {t("providers:tokensInOut", {
                          input: formatTokens(entry.input),
                          output: formatTokens(entry.output),
                        })}
                      </span>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </Layout>
  );
}
