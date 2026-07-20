import { useTranslation } from "react-i18next";
import type { ChatStatus } from "ai";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Progress } from "@/components/ui/progress";
import { useGlobalConfig } from "@/hooks/useGlobalConfig";
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
  const { config } = useGlobalConfig();
  const pct = Math.min(100, Math.max(0, usage * 100));

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
