import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardHeader,
} from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Switch } from "@/components/ui/switch";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Archive, Brain, ChevronDown, Loader2, Search } from "lucide-react";
import { v2Api, type MemoryKind, type MemoryRes } from "@/lib/api/v2";
import { EmptyState } from "@/components/empty-state";
import Layout from "@/components/Layout";

const PAGE_SIZE = 50;
const SEARCH_DEBOUNCE_MS = 300;

const KIND_BADGE_VARIANT: Record<
  MemoryKind,
  "default" | "secondary" | "outline" | "destructive"
> = {
  fact: "secondary",
  preference: "default",
  decision: "outline",
  gotcha: "destructive",
};

const KIND_LABEL_KEYS: Record<MemoryKind, string> = {
  fact: "memories:kindFact",
  preference: "memories:kindPreference",
  decision: "memories:kindDecision",
  gotcha: "memories:kindGotcha",
};

function formatDate(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

/** True when the v2 client rejected due to 401 (it also forces /login). */
function isAuthError(err: unknown): boolean {
  return (
    err instanceof Error && err.message === "Invalid authentication credentials"
  );
}

function MemoryRow({
  memory,
  archiving,
  onArchive,
}: {
  memory: MemoryRes;
  archiving: boolean;
  onArchive: (memory: MemoryRes) => void;
}) {
  const { t } = useTranslation();
  const [evidenceOpen, setEvidenceOpen] = useState(false);

  return (
    <Card className={memory.archived ? "opacity-70" : undefined}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-2">
          <div className="flex min-w-0 items-center gap-2">
            <Badge
              variant={KIND_BADGE_VARIANT[memory.kind] ?? "outline"}
              className="shrink-0"
            >
              {t(KIND_LABEL_KEYS[memory.kind] ?? "memories:kindFact")}
            </Badge>
            <Badge variant="outline" className="shrink-0 tabular-nums">
              {t("memories:salience")} {memory.salience.toFixed(1)}
            </Badge>
            {memory.archived && (
              <Badge variant="secondary" className="shrink-0">
                {t("memories:archivedBadge")}
              </Badge>
            )}
          </div>
          {!memory.archived && (
            <Button
              variant="ghost"
              size="sm"
              className="shrink-0"
              disabled={archiving}
              onClick={() => onArchive(memory)}
            >
              {archiving ? (
                <Loader2 className="mr-1 h-4 w-4 animate-spin" />
              ) : (
                <Archive className="mr-1 h-4 w-4" />
              )}
              {t("memories:archive")}
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        <p className="whitespace-pre-wrap text-sm">{memory.content}</p>
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground tabular-nums">
          <span>
            {t("memories:createdAt")}: {formatDate(memory.created_at)}
          </span>
          <span>
            {t("memories:updatedAt")}: {formatDate(memory.updated_at)}
          </span>
        </div>
        {memory.evidence && (
          <Collapsible open={evidenceOpen} onOpenChange={setEvidenceOpen}>
            <CollapsibleTrigger asChild>
              <Button variant="ghost" size="sm" className="h-7 gap-1 px-2 text-xs">
                <ChevronDown
                  className={`h-3.5 w-3.5 transition-transform ${evidenceOpen ? "rotate-180" : ""}`}
                />
                {evidenceOpen
                  ? t("memories:evidenceHide")
                  : t("memories:evidenceShow")}
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <pre className="mt-1 whitespace-pre-wrap rounded-md bg-muted p-3 text-xs text-muted-foreground">
                {memory.evidence}
              </pre>
            </CollapsibleContent>
          </Collapsible>
        )}
      </CardContent>
    </Card>
  );
}

export default function MemoriesPage() {
  const { t } = useTranslation();

  const [memories, setMemories] = useState<MemoryRes[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [archivingId, setArchivingId] = useState<string | null>(null);

  const [q, setQ] = useState("");
  const [appliedQ, setAppliedQ] = useState("");
  const [includeArchived, setIncludeArchived] = useState(false);

  // Debounce the search box before hitting the API.
  useEffect(() => {
    const timer = setTimeout(() => setAppliedQ(q.trim()), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [q]);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await v2Api.memories.list({
          q: appliedQ || undefined,
          includeArchived,
          limit: PAGE_SIZE,
          offset: 0,
        });
        if (cancelled) return;
        setMemories(res);
        setHasMore(res.length === PAGE_SIZE);
      } catch (err) {
        if (!cancelled) {
          setError(
            isAuthError(err)
              ? t("memories:loginRequired")
              : err instanceof Error
                ? err.message
                : t("memories:loadFailed"),
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load().catch((err: unknown) => {
      console.error("[MemoriesPage] load failed:", err);
    });
    return () => {
      cancelled = true;
    };
  }, [appliedQ, includeArchived, t]);

  const handleLoadMore = useCallback(async () => {
    setLoadingMore(true);
    setError(null);
    try {
      const res = await v2Api.memories.list({
        q: appliedQ || undefined,
        includeArchived,
        limit: PAGE_SIZE,
        offset: memories.length,
      });
      setMemories((prev) => {
        const seen = new Set(prev.map((m) => m.id));
        return [...prev, ...res.filter((m) => !seen.has(m.id))];
      });
      setHasMore(res.length === PAGE_SIZE);
    } catch (err) {
      setError(
        isAuthError(err)
          ? t("memories:loginRequired")
          : err instanceof Error
            ? err.message
            : t("memories:loadFailed"),
      );
    } finally {
      setLoadingMore(false);
    }
  }, [appliedQ, includeArchived, memories.length, t]);

  const handleArchive = useCallback(
    async (memory: MemoryRes) => {
    // biome-ignore lint/suspicious/noAlert: matches the existing window.confirm pattern in ProvidersPage
      if (!window.confirm(t("memories:confirmArchive"))) return;
      setArchivingId(memory.id);
      setError(null);
      setNotice(null);
      try {
        await v2Api.memories.archive(memory.id);
        setNotice(t("memories:archivedNotice"));
        setMemories((prev) =>
          includeArchived
            ? prev.map((m) =>
                m.id === memory.id ? { ...m, archived: true } : m,
              )
            : prev.filter((m) => m.id !== memory.id),
        );
      } catch (err) {
        setError(
          isAuthError(err)
            ? t("memories:loginRequired")
            : err instanceof Error
              ? err.message
              : t("memories:archiveFailed"),
        );
      } finally {
        setArchivingId(null);
      }
    },
    [includeArchived, t],
  );

  return (
    <Layout>
      <div className="mb-6">
        <h1 className="text-2xl font-bold">{t("memories:title")}</h1>
        <p className="text-muted-foreground">{t("memories:subtitle")}</p>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="relative min-w-56 flex-1 sm:max-w-sm">
          <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            className="pl-8"
            placeholder={t("memories:searchPlaceholder")}
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-2 text-sm">
          <Switch
            checked={includeArchived}
            onCheckedChange={setIncludeArchived}
          />
          <span>{t("memories:includeArchived")}</span>
        </div>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {notice && (
        <Alert className="mb-4">
          <AlertDescription>{notice}</AlertDescription>
        </Alert>
      )}

      {loading ? (
        <div className="flex justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : memories.length === 0 ? (
        <Card className="border-dashed">
          <CardContent>
            <EmptyState
              icon={Brain}
              title={
                appliedQ
                  ? t("memories:emptySearchTitle")
                  : t("memories:emptyTitle")
              }
              hint={
                appliedQ
                  ? t("memories:emptySearchHint")
                  : t("memories:emptyHint")
              }
            />
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {memories.map((memory) => (
            <MemoryRow
              key={memory.id}
              memory={memory}
              archiving={archivingId === memory.id}
              onArchive={handleArchive}
            />
          ))}
          {hasMore && (
            <div className="flex justify-center pt-2">
              <Button
                variant="outline"
                disabled={loadingMore}
                onClick={handleLoadMore}
              >
                {loadingMore && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                {t("memories:loadMore")}
              </Button>
            </div>
          )}
        </div>
      )}
    </Layout>
  );
}
