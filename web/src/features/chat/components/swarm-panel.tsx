import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { BotIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { formatRelativeTime } from "@/hooks/utils";
import {
  selectRunningSwarmCount,
  useSwarmStore,
  type SwarmAgent,
  type SwarmAgentStatus,
} from "@/stores/swarm";

const STATUS_DOT_CLASS: Record<SwarmAgentStatus, string> = {
  running_foreground: "bg-blue-500 animate-pulse",
  running_background: "bg-blue-500 animate-pulse",
  idle: "bg-muted-foreground/40",
  completed: "bg-success",
  failed: "bg-destructive",
  killed: "bg-orange-500",
};

const STATUS_LABEL_KEY: Record<SwarmAgentStatus, string> = {
  running_foreground: "chat:swarmStatusRunning",
  running_background: "chat:swarmStatusRunning",
  idle: "chat:swarmStatusIdle",
  completed: "chat:swarmStatusCompleted",
  failed: "chat:swarmStatusFailed",
  killed: "chat:swarmStatusKilled",
};

function SwarmAgentRow({ agent }: { agent: SwarmAgent }) {
  const { t } = useTranslation();
  return (
    <div className="flex items-center gap-2 px-3 py-2 transition-colors hover:bg-secondary/40">
      <Tooltip>
        <TooltipTrigger asChild>
          <span
            className={cn(
              "size-1.5 shrink-0 rounded-full",
              STATUS_DOT_CLASS[agent.status] ?? "bg-muted-foreground/40",
            )}
          />
        </TooltipTrigger>
        <TooltipContent side="left">
          {t(STATUS_LABEL_KEY[agent.status] ?? "chat:swarmStatusIdle")}
        </TooltipContent>
      </Tooltip>
      <Badge variant="secondary" className="shrink-0 px-1.5 text-[10px]">
        {agent.subagentType || "agent"}
      </Badge>
      <span className="min-w-0 flex-1 truncate text-xs">
        {agent.description || agent.agentId}
      </span>
      {agent.stepCount > 0 ? (
        <span className="shrink-0 text-[10px] text-muted-foreground">
          {t("chat:swarmSteps", { count: agent.stepCount })}
        </span>
      ) : null}
      <span className="shrink-0 text-[10px] text-muted-foreground">
        {formatRelativeTime(new Date(agent.updatedAt * 1000))}
      </span>
    </div>
  );
}

export function SwarmPanel() {
  const { t } = useTranslation();
  const agents = useSwarmStore((s) => s.agents);
  const runningCount = useSwarmStore(selectRunningSwarmCount);

  const sortedAgents = useMemo(
    () => Object.values(agents).sort((a, b) => b.updatedAt - a.updatedAt),
    [agents],
  );

  return (
    <DropdownMenu>
      <Tooltip>
        <TooltipTrigger asChild>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              aria-label={t("chat:swarmButtonLabel")}
              className="relative inline-flex items-center cursor-pointer justify-center rounded-md p-2 text-muted-foreground transition-colors hover:bg-secondary/60 hover:text-foreground"
            >
              <BotIcon className="size-4" />
              {runningCount > 0 ? (
                <span className="absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-blue-500 px-1 text-[10px] font-medium text-white">
                  {runningCount}
                </span>
              ) : null}
            </button>
          </DropdownMenuTrigger>
        </TooltipTrigger>
        <TooltipContent side="bottom">
          {t("chat:swarmButtonLabel")}
        </TooltipContent>
      </Tooltip>
      <DropdownMenuContent align="end" className="w-80 p-0">
        <div className="border-b border-border px-3 py-2 text-xs font-semibold">
          {t("chat:swarmTitle")}
        </div>
        {sortedAgents.length === 0 ? (
          <div className="px-3 py-6 text-center text-xs text-muted-foreground">
            {t("chat:swarmEmpty")}
          </div>
        ) : (
          <div className="max-h-80 overflow-y-auto py-1">
            {sortedAgents.map((agent) => (
              <SwarmAgentRow key={agent.agentId} agent={agent} />
            ))}
          </div>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
