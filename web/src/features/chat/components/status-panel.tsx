import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import type { ChatStatus } from "ai";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { ArrowRightIcon, Loader2 } from "lucide-react";
import { useGlobalConfig } from "@/hooks/useGlobalConfig";
import { useAuthStore } from "@/stores/auth";
import { v2Api } from "@/lib/api/v2";
import type { TokenUsage } from "@/hooks/wireTypes";

type StatusPanelProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Context usage fraction, 0..1 */
  usage: number;
  usedTokens: number;
  maxTokens: number;
  tokenUsage: TokenUsage | null;
  streamStatus?: ChatStatus;
};

const compact = (n: number): string =>
  new Intl.NumberFormat("en-US", { notation: "compact" }).format(n);

const WORKER_STATUS_KEYS: Record<ChatStatus, string> = {
  ready: "chat:workerReady",
  submitted: "chat:workerConnecting",
  streaming: "chat:workerGenerating",
  error: "chat:workerError",
};

const CONTEXT_TIERS = [
  { label: "256K", value: 262144 },
  { label: "512K", value: 524288 },
  { label: "1M", value: 1048576 },
];

function StatusRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium text-right min-w-0 truncate">{value}</span>
    </div>
  );
}

/** /status-style dialog: model, thinking, context, token breakdown, worker. */
export function StatusPanel({
  open,
  onOpenChange,
  usage,
  usedTokens,
  maxTokens,
  tokenUsage,
  streamStatus,
}: StatusPanelProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const isAdmin = user?.role === "admin";
  const { config, refresh } = useGlobalConfig();
  const [contextBusy, setContextBusy] = useState<number | null>(null);
  const [contextError, setContextError] = useState<string | null>(null);
  const pct = Math.min(100, Math.max(0, usage * 100));

  const currentModel = config?.models.find(
    (m) => m.name === config.defaultModel,
  );
  const modelContextSize = currentModel?.maxContextSize ?? maxTokens;

  const handleSetContext = async (size: number) => {
    if (!config?.defaultModel || contextBusy !== null) return;
    setContextBusy(size);
    setContextError(null);
    try {
      await v2Api.providers.setModelContext(config.defaultModel, {
        max_context_size: size,
      });
      await refresh();
      // Let other useGlobalConfig consumers (composer, container) refresh too
      window.dispatchEvent(new Event("cran:config-update"));
    } catch (err) {
      setContextError(
        err instanceof Error ? err.message : t("providers:contextFailed"),
      );
    } finally {
      setContextBusy(null);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>{t("chat:statusPanelTitle")}</DialogTitle>
        </DialogHeader>

        <div className="space-y-2.5">
          <StatusRow label={t("chat:statusModel")} value={config?.defaultModel ?? t("chat:statusNone")} />
          <StatusRow
            label={t("chat:statusThinkingLabel")}
            value={config?.defaultThinking ? t("common:on") : t("common:off")}
          />
          <StatusRow
            label={t("chat:statusWorker")}
            value={streamStatus ? t(WORKER_STATUS_KEYS[streamStatus]) : t("chat:statusNone")}
          />
        </div>

        <div className="space-y-2 border-t pt-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">{t("chat:statusContext")}</span>
            <span className="font-mono text-muted-foreground tabular-nums">
              {compact(usedTokens)} / {compact(maxTokens)} · {pct.toFixed(1)}%
            </span>
          </div>
          <Progress className="bg-muted" value={pct} />
        </div>

        {/* Context window quick-set (admins); read-only for others */}
        <div className="space-y-2 border-t pt-3">
          <div className="flex items-center justify-between gap-2 text-sm">
            <span className="text-muted-foreground">
              {t("chat:statusContextLimit")}
            </span>
            {isAdmin ? (
              <div className="flex items-center gap-1">
                {contextBusy !== null ? (
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                ) : (
                  CONTEXT_TIERS.map((tier) => (
                    <Button
                      key={tier.value}
                      variant={
                        modelContextSize === tier.value ? "secondary" : "ghost"
                      }
                      size="sm"
                      className="h-7 px-2 text-xs"
                      disabled={modelContextSize === tier.value}
                      onClick={() => handleSetContext(tier.value)}
                    >
                      {tier.label}
                    </Button>
                  ))
                )}
              </div>
            ) : (
              <span className="font-mono text-muted-foreground tabular-nums">
                {compact(modelContextSize)}
              </span>
            )}
          </div>
          {isAdmin && (
            <p className="text-xs text-muted-foreground">
              {t("chat:statusContext1mHint")}
            </p>
          )}
          {contextError && (
            <p className="text-xs text-destructive">{contextError}</p>
          )}
          <button
            type="button"
            onClick={() => {
              onOpenChange(false);
              navigate("/settings/providers");
            }}
            className="inline-flex items-center gap-1 text-xs text-primary hover:underline cursor-pointer"
          >
            {t("chat:statusGoProviders")}
            <ArrowRightIcon className="size-3" />
          </button>
        </div>

        {tokenUsage && (
          <div className="space-y-1.5 border-t pt-3 text-sm">
            <p className="text-xs font-medium text-muted-foreground">
              {t("chat:statusLastTokens")}
            </p>
            <StatusRow label={t("chat:regular")} value={compact(tokenUsage.input_other)} />
            <StatusRow label={t("chat:cacheRead")} value={compact(tokenUsage.input_cache_read)} />
            <StatusRow label={t("chat:cacheWrite")} value={compact(tokenUsage.input_cache_creation)} />
            <StatusRow label={t("chat:generated")} value={compact(tokenUsage.output)} />
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
