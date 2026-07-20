"use client";

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";
import { ChevronDown, ChevronRight, User, Bot, Clock } from "lucide-react";

interface CompactionTurn {
  author?: string;
  timestamp?: number;
  excerpt?: string;
}

interface CompactionAiTurn {
  timestamp?: number;
  summary?: string;
}

interface CompactionTimelineProps {
  humanTurns: CompactionTurn[];
  aiTurns: CompactionAiTurn[];
  className?: string;
}

function formatTime(ts?: number): string {
  if (!ts) return "";
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function CompactionTimeline({
  humanTurns,
  aiTurns,
  className,
}: CompactionTimelineProps) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);
  const totalTurns = humanTurns.length;

  return (
    <div className={cn("rounded-lg border bg-muted/30", className)}>
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-muted/50 transition-colors"
      >
        {expanded ? (
          <ChevronDown className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
        ) : (
          <ChevronRight className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
        )}
        <Clock className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
        <span className="text-xs font-medium text-muted-foreground">
          {t("chat:compactionSummary")}
        </span>
        <span className="ml-auto text-[10px] text-muted-foreground/60">
          {t("chat:turns", { count: totalTurns })}
        </span>
      </button>

      {expanded && (
        <div className="border-t px-3 py-2 space-y-2 max-h-[300px] overflow-auto">
          {humanTurns.map((turn, i) => (
            <div key={`h-${i}`} className="space-y-1">
              <div className="flex items-center gap-1.5">
                <User className="h-3 w-3 text-blue-400 shrink-0" />
                <span className="text-[10px] font-medium text-blue-400">
                  {turn.author || t("chat:labelUser")}
                </span>
                {turn.timestamp ? (
                  <span className="text-[10px] text-muted-foreground/50">
                    {formatTime(turn.timestamp)}
                  </span>
                ) : null}
              </div>
              {turn.excerpt ? (
                <p className="text-xs text-muted-foreground pl-4 truncate">
                  {turn.excerpt}
                </p>
              ) : null}
              {aiTurns[i] ? (
                <div className="flex items-start gap-1.5 pl-4">
                  <Bot className="h-3 w-3 text-emerald-400 shrink-0 mt-0.5" />
                  <p className="text-xs text-muted-foreground/70 line-clamp-2">
                    {aiTurns[i]?.summary || t("chat:response")}
                  </p>
                </div>
              ) : null}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
