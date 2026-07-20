import { useState } from "react";
import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";
import { StatusPanel } from "./status-panel";
import type { ChatStatus } from "ai";
import type { TokenUsage } from "@/hooks/wireTypes";

type ContextRingProps = {
  /** Context usage fraction, 0..1 */
  usage: number;
  usedTokens: number;
  maxTokens: number;
  tokenUsage: TokenUsage | null;
  streamStatus?: ChatStatus;
  className?: string;
};

const R = 7;
const CIRCUMFERENCE = 2 * Math.PI * R;

function ringColor(pct: number): string {
  if (pct >= 90) return "stroke-red-500";
  if (pct >= 70) return "stroke-amber-500";
  return "stroke-primary";
}

/** Compact SVG donut showing context usage; click opens the StatusPanel. */
export function ContextRing({
  usage,
  usedTokens,
  maxTokens,
  tokenUsage,
  streamStatus,
  className,
}: ContextRingProps) {
  const { t } = useTranslation();
  const [panelOpen, setPanelOpen] = useState(false);
  const pct = Math.min(100, Math.max(0, usage * 100));

  return (
    <>
      <button
        type="button"
        onClick={() => setPanelOpen(true)}
        aria-label={`${t("chat:contextRingLabel")} ${pct.toFixed(1)}%`}
        title={`${t("chat:contextRingLabel")} ${pct.toFixed(1)}%`}
        className={cn(
          "inline-flex h-7 items-center gap-1 rounded-full px-1.5 cursor-pointer",
          "text-muted-foreground transition-colors hover:bg-secondary/60 hover:text-foreground",
          className,
        )}
      >
        <svg viewBox="0 0 20 20" className="size-[18px] -rotate-90" aria-hidden="true">
          <circle
            cx="10"
            cy="10"
            r={R}
            fill="none"
            strokeWidth="2.5"
            className="stroke-border"
          />
          <circle
            cx="10"
            cy="10"
            r={R}
            fill="none"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={CIRCUMFERENCE * (1 - pct / 100)}
            className={cn("transition-[stroke-dashoffset] duration-300", ringColor(pct))}
          />
        </svg>
        <span className="text-xs font-medium tabular-nums">{pct.toFixed(0)}%</span>
      </button>
      <StatusPanel
        open={panelOpen}
        onOpenChange={setPanelOpen}
        usage={usage}
        usedTokens={usedTokens}
        maxTokens={maxTokens}
        tokenUsage={tokenUsage}
        streamStatus={streamStatus}
      />
    </>
  );
}
