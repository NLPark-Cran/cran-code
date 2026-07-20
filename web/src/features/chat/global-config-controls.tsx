import { useCallback, useMemo, useState, type ReactElement } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { Check, Cpu, Paperclip, RefreshCcw } from "lucide-react";
import { usePromptInputAttachments } from "@ai-elements";
import type { ConfigModel } from "@/lib/api/models";
import { ModelCapability } from "@/lib/api/models";
import { useGlobalConfig } from "@/hooks/useGlobalConfig";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Loader } from "@/components/ai-elements/loader";
import {
  ModelSelector,
  ModelSelectorContent,
  ModelSelectorEmpty,
  ModelSelectorGroup,
  ModelSelectorInput,
  ModelSelectorItem,
  ModelSelectorList,
  ModelSelectorName,
  ModelSelectorTrigger,
} from "@/components/ai-elements/model-selector";
import { cn } from "@/lib/utils";

type ThinkingState = "enabled" | "disabled" | "forced";

function getThinkingState(model: ConfigModel | null): ThinkingState {
  const capabilities = model?.capabilities;
  if (!capabilities) {
    return "disabled";
  }
  if (capabilities.has(ModelCapability.AlwaysThinking)) {
    return "forced";
  }
  if (capabilities.has(ModelCapability.Thinking)) {
    return "enabled";
  }
  return "disabled";
}

export type GlobalConfigControlsProps = {
  className?: string;
  planMode?: boolean;
  onPlanModeChange?: (enabled: boolean) => void;
};

export function GlobalConfigControls({
  className,
  planMode = false,
  onPlanModeChange,
}: GlobalConfigControlsProps): ReactElement {
  const { t } = useTranslation();
  const { config, isLoading, isUpdating, error, refresh, update } =
    useGlobalConfig();

  const [isSelectorOpen, setIsSelectorOpen] = useState(false);
  const [lastBusySkip, setLastBusySkip] = useState<string[] | null>(null);

  const currentModel = useMemo(() => {
    if (!config) {
      return null;
    }
    return config.models.find((m) => m.name === config.defaultModel) ?? null;
  }, [config]);

  const thinkingState = useMemo(
    () => getThinkingState(currentModel),
    [currentModel],
  );

  const thinkingChecked = config?.defaultThinking ?? false;
  const thinkingDisabled =
    isLoading || isUpdating || thinkingState !== "enabled";

  const handleSelectModel = useCallback(
    async (modelKey: string) => {
      setIsSelectorOpen(false);
      if (!config || modelKey === config.defaultModel) {
        return;
      }

      try {
        const resp = await update({ defaultModel: modelKey });
        const restarted = resp.restartedSessionIds ?? [];
        const skippedBusy = resp.skippedBusySessionIds ?? [];

        if (restarted.length > 0) {
          toast.success(t("chat:globalModelUpdated"), {
            description: t("chat:restartedSessions", { count: restarted.length }),
          });
        } else {
          toast.success(t("chat:globalModelUpdated"));
        }

        if (skippedBusy.length > 0) {
          setLastBusySkip(skippedBusy);
          toast.message(t("chat:sessionsSkippedBusy"), {
            description: t("chat:sessionsSkippedBusyDesc", { count: skippedBusy.length }),
          });
        } else {
          setLastBusySkip(null);
        }
      } catch (err) {
        const message =
          err instanceof Error ? err.message : t("chat:updateModelFailed");
        toast.error(t("chat:updateModelFailed"), { description: message });
      }
    },
    [config, update, t],
  );

  const handleThinkingToggle = useCallback(
    async (checked: boolean) => {
      if (!config) {
        return;
      }
      try {
        const resp = await update({ defaultThinking: checked });
        const skippedBusy = resp.skippedBusySessionIds ?? [];

        if (skippedBusy.length > 0) {
          setLastBusySkip(skippedBusy);
          toast.message(t("chat:sessionsSkippedBusy"), {
            description: t("chat:sessionsSkippedBusyDesc", { count: skippedBusy.length }),
          });
        } else {
          setLastBusySkip(null);
        }
      } catch (err) {
        const message =
          err instanceof Error
            ? err.message
            : t("chat:updateThinkingFailed");
        toast.error(t("chat:updateThinkingFailed"), {
          description: message,
        });
      }
    },
    [config, update, t],
  );

  const handleForceRestartBusy = useCallback(async () => {
    if (!lastBusySkip || lastBusySkip.length === 0) {
      return;
    }
    try {
      const resp = await update({ forceRestartBusySessions: true });
      const restarted = resp.restartedSessionIds ?? [];
      const skippedBusy = resp.skippedBusySessionIds ?? [];

      if (skippedBusy.length === 0) {
        setLastBusySkip(null);
      } else {
        setLastBusySkip(skippedBusy);
      }

      toast.success(t("chat:restartedRunning"), {
        description:
          restarted.length > 0
            ? t("chat:restartedCount", { count: restarted.length })
            : t("chat:noRunningSessions"),
      });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : t("chat:restartBusyFailed");
      toast.error(t("chat:restartBusyFailed"), { description: message });
    }
  }, [lastBusySkip, update, t]);

  const thinkingTooltip = useMemo(() => {
    if (thinkingState === "forced") {
      return t("chat:thinkingForced");
    }
    if (thinkingState === "disabled") {
      return t("chat:thinkingUnsupported");
    }
    return null;
  }, [thinkingState, t]);

  const thinkingToggle = (
    <div className="flex h-9 items-center gap-2 rounded-md px-2">
      <span className="text-xs text-muted-foreground">{t("chat:thinking")}</span>
      <Switch
        aria-label={t("chat:toggleThinking")}
        checked={
          thinkingState === "forced"
            ? true
            : thinkingState === "disabled"
              ? false
              : thinkingChecked
        }
        disabled={thinkingDisabled}
        onCheckedChange={handleThinkingToggle}
      />
    </div>
  );

  const attachments = usePromptInputAttachments();

  return (
    <div className={cn("flex items-center gap-1", className)}>
      <Button
        variant="ghost"
        size="icon"
        className="size-9 border-0"
        aria-label={t("chat:attachFiles")}
        type="button"
        onClick={() => attachments.openFileDialog()}
      >
        <Paperclip className="size-4" />
      </Button>

      <div className="mx-0 h-4 w-px bg-border/70" />

      <ModelSelector open={isSelectorOpen} onOpenChange={setIsSelectorOpen}>
        <ModelSelectorTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="h-9 max-w-[160px] justify-start gap-2 border-0"
            aria-label={t("chat:changeModel")}
            type="button"
            disabled={isLoading || isUpdating || !config}
          >
            <Cpu className="size-4 shrink-0" />
            <span className="truncate">
              {config ? config.defaultModel : t("chat:model")}
            </span>
            {(isLoading || isUpdating) && (
              <Loader className="ml-auto shrink-0" size={14} />
            )}
          </Button>
        </ModelSelectorTrigger>
        <ModelSelectorContent title={t("chat:selectGlobalModel")}>
          <ModelSelectorInput placeholder={t("chat:searchModels")} />
          <ModelSelectorList>
            <ModelSelectorEmpty>{t("chat:noModelsFound")}</ModelSelectorEmpty>
            <ModelSelectorGroup heading={t("chat:modelsHeading")}>
              {(config?.models ?? []).map((m) => {
                const isSelected = m.name === config?.defaultModel;
                const label = `${m.name} (${m.provider})`;
                return (
                  <ModelSelectorItem
                    key={m.name}
                    value={`${m.name} ${m.model} ${m.provider}`}
                    onSelect={(_value) => handleSelectModel(m.name)}
                    className="flex items-center gap-2"
                  >
                    {isSelected ? (
                      <Check className="size-4 text-foreground" />
                    ) : (
                      <span className="size-4" />
                    )}
                    <ModelSelectorName title={label}>
                      {m.name}
                    </ModelSelectorName>
                    <span className="shrink-0 text-xs text-muted-foreground">
                      {m.provider}
                    </span>
                  </ModelSelectorItem>
                );
              })}
            </ModelSelectorGroup>
          </ModelSelectorList>
        </ModelSelectorContent>
      </ModelSelector>

      <div className="mx-0 h-4 w-px bg-border/70" />
      
      {thinkingTooltip ? (
        <Tooltip>
          <TooltipTrigger asChild>{thinkingToggle}</TooltipTrigger>
          <TooltipContent sideOffset={8}>{thinkingTooltip}</TooltipContent>
        </Tooltip>
      ) : (
        thinkingToggle
      )}

      {onPlanModeChange && (
        <>
          <div className="mx-0 h-4 w-px bg-border/70" />
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex h-9 items-center gap-2 rounded-md px-2">
                <span className="text-xs text-muted-foreground">
                  {t("chat:plan")}
                </span>
                <Switch
                  aria-label={t("chat:togglePlanMode")}
                  checked={planMode}
                  onCheckedChange={onPlanModeChange}
                />
              </div>
            </TooltipTrigger>
            <TooltipContent sideOffset={8}>
              {planMode
                ? t("chat:planModeActive")
                : t("chat:planModeEnable")}
            </TooltipContent>
          </Tooltip>
        </>
      )}

      {(lastBusySkip && lastBusySkip.length > 0) || error ? (
        <div className="mx-1.5 h-4 w-px bg-border/70" />
      ) : null}

      {lastBusySkip && lastBusySkip.length > 0 ? (
        <Button
          variant="outline"
          size="icon"
          className="size-9"
          aria-label={t("chat:forceRestartBusy")}
          title={t("chat:forceRestartBusy")}
          type="button"
          onClick={handleForceRestartBusy}
          disabled={isUpdating}
        >
          <RefreshCcw className="size-4" />
        </Button>
      ) : null}

      {error ? (
        <Button
          variant="outline"
          size="icon"
          className="size-9"
          aria-label={t("chat:reloadGlobalConfig")}
          title={t("chat:reloadGlobalConfig")}
          type="button"
          onClick={() => {
            refresh();
          }}
        >
          <RefreshCcw className="size-4" />
        </Button>
      ) : null}
    </div>
  );
}
