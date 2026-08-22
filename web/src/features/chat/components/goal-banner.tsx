import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  AlertTriangleIcon,
  FlagIcon,
  PauseIcon,
  PlayIcon,
  XIcon,
} from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { getAuthHeader } from "@/lib/auth";
import { getApiBaseUrl } from "@/hooks/utils";
import {
  currentGoalActiveSeconds,
  effectiveGoalMaxTurns,
  useGoalStore,
  type GoalSnapshot,
  type GoalStatus,
} from "@/stores/goal";

const COMPACT_NUMBER_FORMAT = new Intl.NumberFormat("en-US", {
  notation: "compact",
});

/** Compact duration: "45s" / "12m 30s" / "2h 5m". */
function formatGoalDuration(totalSeconds: number): string {
  const seconds = Math.max(0, Math.floor(totalSeconds));
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    const restSeconds = seconds % 60;
    return restSeconds > 0 ? `${minutes}m ${restSeconds}s` : `${minutes}m`;
  }
  const hours = Math.floor(minutes / 60);
  const restMinutes = minutes % 60;
  return restMinutes > 0 ? `${hours}h ${restMinutes}m` : `${hours}h`;
}

const STATUS_CHIP_CLASS: Record<GoalStatus, string> = {
  active: "border-blue-500/40 bg-blue-500/10 text-blue-600 dark:text-blue-400",
  paused: "border-border bg-secondary/60 text-muted-foreground",
  blocked: "border-amber-500/40 bg-amber-500/10 text-amber-600 dark:text-amber-400",
};

const STATUS_LABEL_KEY: Record<GoalStatus, string> = {
  active: "chat:goalStatusActive",
  paused: "chat:goalStatusPaused",
  blocked: "chat:goalStatusBlocked",
};

type GoalBannerProps = {
  sessionId?: string;
};

export function GoalBanner({ sessionId }: GoalBannerProps) {
  const { t } = useTranslation();
  const goal = useGoalStore((s) => s.goal);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [pending, setPending] = useState(false);

  /** Re-sync the store from the server after a conflict/error. */
  const resync = useCallback(async () => {
    if (!sessionId) return;
    try {
      const response = await fetch(
        `${getApiBaseUrl()}/api/sessions/${encodeURIComponent(sessionId)}/goal`,
        { headers: { ...getAuthHeader() } },
      );
      if (!response.ok) return;
      const data = (await response.json()) as { goal?: GoalSnapshot | null };
      useGoalStore.getState().setFromSnapshot(data.goal ?? null);
    } catch {
      // Network error: leave the store as-is; the wire stream will catch up.
    }
  }, [sessionId]);

  const runAction = useCallback(
    async (action: "pause" | "resume" | "cancel") => {
      if (!sessionId || pending) return;
      setPending(true);
      try {
        const base = `${getApiBaseUrl()}/api/sessions/${encodeURIComponent(sessionId)}/goal`;
        const response = await fetch(
          action === "cancel" ? base : `${base}/${action}`,
          {
            method: action === "cancel" ? "DELETE" : "POST",
            headers: { ...getAuthHeader() },
          },
        );
        if (!response.ok) {
          // 404 (no goal) / 409 (invalid transition): the UI is stale — resync.
          toast.error(t("chat:goalActionFailed"));
          await resync();
          return;
        }
        const data = (await response.json()) as { goal?: GoalSnapshot | null };
        useGoalStore.getState().setFromSnapshot(data.goal ?? null);
      } catch (error) {
        console.error("[GoalBanner] action failed:", error);
        toast.error(t("chat:goalActionFailed"));
        await resync();
      } finally {
        setPending(false);
        setConfirmOpen(false);
      }
    },
    [sessionId, pending, resync, t],
  );

  if (!(goal && sessionId)) return null;

  const maxTurns = effectiveGoalMaxTurns(goal);
  const activeSeconds = currentGoalActiveSeconds(goal, Date.now() / 1000);
  const isActive = goal.status === "active";
  const isParked = goal.status === "paused" || goal.status === "blocked";

  return (
    <div className="border-b border-border bg-secondary/30 px-3 py-2 sm:px-5">
      <div className="flex items-center gap-2">
        <FlagIcon className="size-3.5 shrink-0 text-primary" />
        <Badge
          variant="outline"
          className={cn(
            "shrink-0 gap-1.5 px-1.5 text-[10px]",
            STATUS_CHIP_CLASS[goal.status],
          )}
        >
          <span
            className={cn(
              "size-1.5 rounded-full",
              isActive && "bg-blue-500 animate-pulse",
              goal.status === "paused" && "bg-muted-foreground/40",
              goal.status === "blocked" && "bg-amber-500",
            )}
          />
          {t(STATUS_LABEL_KEY[goal.status])}
        </Badge>
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="min-w-0 flex-1 cursor-default truncate text-xs font-medium">
              {goal.objective}
            </span>
          </TooltipTrigger>
          <TooltipContent side="bottom" className="max-w-md">
            {goal.objective}
            {goal.criteria ? (
              <div className="mt-1 text-muted-foreground">{goal.criteria}</div>
            ) : null}
          </TooltipContent>
        </Tooltip>
        <span className="hidden shrink-0 text-[10px] text-muted-foreground md:inline">
          {t("chat:goalStatTurns", { used: goal.stats.turns, total: maxTurns })}
        </span>
        <span className="hidden shrink-0 text-[10px] text-muted-foreground lg:inline">
          {t("chat:goalStatTime", { duration: formatGoalDuration(activeSeconds) })}
        </span>
        <span className="hidden shrink-0 text-[10px] text-muted-foreground lg:inline">
          {t("chat:goalStatTokens", {
            count: COMPACT_NUMBER_FORMAT.format(goal.stats.tokens),
          })}
        </span>
        {isActive ? (
          <button
            type="button"
            disabled={pending}
            aria-label={t("chat:goalPause")}
            className="inline-flex shrink-0 cursor-pointer items-center gap-1 rounded-md px-2 py-1 text-[10px] text-muted-foreground transition-colors hover:bg-secondary/60 hover:text-foreground disabled:cursor-not-allowed disabled:opacity-50"
            onClick={() => {
              runAction("pause");
            }}
          >
            <PauseIcon className="size-3" />
            {t("chat:goalPause")}
          </button>
        ) : (
          <button
            type="button"
            disabled={pending}
            aria-label={t("chat:goalResume")}
            className="inline-flex shrink-0 cursor-pointer items-center gap-1 rounded-md px-2 py-1 text-[10px] text-muted-foreground transition-colors hover:bg-secondary/60 hover:text-foreground disabled:cursor-not-allowed disabled:opacity-50"
            onClick={() => {
              runAction("resume");
            }}
          >
            <PlayIcon className="size-3" />
            {t("chat:goalResume")}
          </button>
        )}
        <button
          type="button"
          disabled={pending}
          aria-label={t("chat:goalCancel")}
          className="inline-flex shrink-0 cursor-pointer items-center justify-center rounded-md p-1 text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive disabled:cursor-not-allowed disabled:opacity-50"
          onClick={() => setConfirmOpen(true)}
        >
          <XIcon className="size-3.5" />
        </button>
      </div>
      {isParked ? (
        <div className="mt-1 flex items-center gap-2 pl-5 text-[10px] text-muted-foreground">
          {goal.stop_reason ? (
            <span className="min-w-0 flex-1 truncate" title={goal.stop_reason}>
              {goal.stop_reason}
            </span>
          ) : (
            <span className="flex-1" />
          )}
          <span className="shrink-0">{t("chat:goalResumeHint")}</span>
        </div>
      ) : null}

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-destructive">
              <AlertTriangleIcon className="size-5" />
              {t("chat:goalCancelTitle")}
            </DialogTitle>
            <DialogDescription>
              {t("chat:goalCancelDescription")}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 w-full justify-end">
            <Button
              variant="outline"
              disabled={pending}
              onClick={() => setConfirmOpen(false)}
            >
              {t("common:cancel")}
            </Button>
            <Button
              variant="destructive"
              disabled={pending}
              onClick={() => {
                runAction("cancel");
              }}
            >
              {t("chat:goalCancelConfirm")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
