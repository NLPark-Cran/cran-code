import { type ReactElement, memo } from "react";
import { useTranslation } from "react-i18next";
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Progress } from "@/components/ui/progress";
import { ContextProgressIcon } from "@ai-elements";
import { cn } from "@/lib/utils";
import type { TokenUsage } from "@/hooks/wireTypes";

type ToolbarContextIndicatorProps = {
  usagePercent: number;
  usedTokens: number;
  maxTokens: number;
  tokenUsage: TokenUsage | null;
  className?: string;
};

export const ToolbarContextIndicator = memo(
  function ToolbarContextIndicatorComponent({
    usagePercent,
    usedTokens,
    maxTokens,
    tokenUsage,
    className,
  }: ToolbarContextIndicatorProps): ReactElement {
    const { t } = useTranslation();
    const usedPercent = maxTokens > 0 ? usedTokens / maxTokens : 0;

    const used = new Intl.NumberFormat("en-US", {
      notation: "compact",
    }).format(usedTokens);
    const total = new Intl.NumberFormat("en-US", {
      notation: "compact",
    }).format(maxTokens);

    return (
      <HoverCard openDelay={200} closeDelay={150}>
        <HoverCardTrigger asChild>
          <button
            type="button"
            className={cn(
              "flex items-center gap-1.5 h-7 px-2.5 rounded-full text-xs font-medium",
              "transition-colors cursor-default border",
              "bg-transparent text-muted-foreground border-border/60",
              "hover:text-foreground hover:border-border",
              className,
            )}
          >
            <ContextProgressIcon usedPercent={usedPercent} size={14} />
            <span>{t("chat:contextUsage", { percent: usagePercent.toFixed(1) })}</span>
          </button>
        </HoverCardTrigger>
        <HoverCardContent
          align="end"
          side="top"
          sideOffset={8}
          className="w-64 p-0"
        >
          <div className="w-full space-y-2 p-3">
            <div className="flex items-center justify-between gap-3 text-xs">
              <p>{usagePercent.toFixed(1)}%</p>
              <p className="font-mono text-muted-foreground">
                {used} / {total}
              </p>
            </div>
            <Progress className="bg-muted" value={usagePercent} />
          </div>

          {tokenUsage && (
            <div className="border-t p-3 space-y-2.5 text-xs">
              <div className="space-y-1">
                <div className="text-[11px] font-medium text-muted-foreground">
                  {t("chat:inputTokens")}
                </div>
                <RawUsageRow
                  label={t("chat:regular")}
                  value={tokenUsage.input_other}
                  description={t("chat:regularDesc")}
                />
                <RawUsageRow
                  label={t("chat:cacheRead")}
                  value={tokenUsage.input_cache_read}
                  description={t("chat:cacheReadDesc")}
                />
                <RawUsageRow
                  label={t("chat:cacheWrite")}
                  value={tokenUsage.input_cache_creation}
                  description={t("chat:cacheWriteDesc")}
                />
                <div className="flex items-center justify-between text-xs font-medium border-t mt-1 pt-1">
                  <span>{t("chat:totalInput")}</span>
                  <span>
                    {new Intl.NumberFormat("en-US", { notation: "compact" }).format(
                      tokenUsage.input_other +
                      tokenUsage.input_cache_read +
                      tokenUsage.input_cache_creation
                    )}
                  </span>
                </div>
              </div>

              <div className="space-y-1 border-t pt-2.5">
                <div className="text-[11px] font-medium text-muted-foreground">
                  {t("chat:outputTokens")}
                </div>
                <RawUsageRow
                  label={t("chat:generated")}
                  value={tokenUsage.output}
                  description={t("chat:generatedDesc")}
                />
              </div>
            </div>
          )}
        </HoverCardContent>
      </HoverCard>
    );
  },
);

const RawUsageRow = ({
  label,
  value,
  description,
}: {
  label: string;
  value: number;
  description?: string;
}) => {
  const content = (
    <div className="flex items-center justify-between text-xs">
      <span className="text-muted-foreground">{label}</span>
      <span>
        {new Intl.NumberFormat("en-US", { notation: "compact" }).format(value)}
      </span>
    </div>
  );

  if (description) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="cursor-help">{content}</div>
        </TooltipTrigger>
        <TooltipContent side="left">
          <p className="text-xs">{description}</p>
        </TooltipContent>
      </Tooltip>
    );
  }

  return content;
};
