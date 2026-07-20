import { useMemo, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import type { TFunction } from "i18next";
import { cn } from "@/lib/utils";
import type { ApprovalResponseDecision } from "@/hooks/wireTypes";
import type { LiveMessage } from "@/hooks/types";
import {
  ChainOfThought,
  ChainOfThoughtContent,
  ChainOfThoughtHeader,
  ChainOfThoughtSearchResult,
  ChainOfThoughtSearchResults,
  ChainOfThoughtStep as ChainOfThoughtStepItem,
  Confirmation,
  ConfirmationAccepted,
  ConfirmationAction,
  ConfirmationActions,
  ConfirmationRejected,
  ConfirmationRequest,
  ConfirmationTitle,
  CodeBlock,
  MessageContent,
  MessageResponse,
  Reasoning,
  ReasoningContent,
  ReasoningTrigger,
  SubagentActivity,
  Tool,
  ToolContent,
  ToolDisplay,
  ToolHeader,
  ToolInput,
  ToolMediaPreview,
  ToolOutput,
} from "@ai-elements";
import { BrainIcon, ChevronRightIcon } from "lucide-react";
import { CompactionTimeline } from "./compaction-timeline";
import { CompactedMediaChip } from "./compacted-media-chip";
import { getToolSummary } from "./tool-summary";

export type ToolApproval = NonNullable<LiveMessage["toolCall"]>["approval"];

export type AssistantApprovalHandler = (
  approval: ToolApproval,
  decision: ApprovalResponseDecision,
) => void | Promise<void>;

const assistantContentClass =
  "w-full max-w-full text-sm leading-relaxed overflow-visible";
const assistantMetaTextClass = "text-xs text-muted-foreground";

type AssistantMessageProps = {
  message: LiveMessage;
  pendingApprovalMap: Record<string, boolean>;
  onApprovalAction?: AssistantApprovalHandler;
  canRespondToApproval: boolean;
  blocksExpanded: boolean;
};

export function AssistantMessage({
  message,
  pendingApprovalMap,
  onApprovalAction,
  canRespondToApproval,
  blocksExpanded,
}: AssistantMessageProps) {
  const { t } = useTranslation();
  const content = useMemo(() => {
    switch (message.variant) {
      case "chain-of-thought":
        return renderChainOfThoughtMessage(message, t);
      case "tool":
        return renderToolMessage({
          message,
          pendingApprovalMap,
          onApprovalAction,
          canRespondToApproval,
          blocksExpanded,
          t,
        });
      case "code":
        return renderCodeMessage(message, t);
      case "thinking":
        return renderThinkingMessage(message, blocksExpanded, t);
      case "compaction":
        return renderCompactionMessage(message, t);
      default:
        return renderAssistantText(message, t);
    }
  }, [
    message,
    pendingApprovalMap,
    onApprovalAction,
    canRespondToApproval,
    blocksExpanded,
    t,
  ]);

  return content;
}

const renderCompactionMessage = (message: LiveMessage, t: TFunction) => {
  const summary = message.compactionSummary;
  return (
    <MessageContent className={assistantContentClass}>
      <div className="flex items-center gap-3 py-1 select-none">
        <div className="h-px flex-1 bg-border" />
        <span className="text-[11px] text-muted-foreground/70">
          {t("chat:compactionDivider")}
        </span>
        <div className="h-px flex-1 bg-border" />
      </div>
      {summary ? (
        <CompactionTimeline
          humanTurns={summary.humanTurns}
          aiTurns={summary.aiTurns}
        />
      ) : null}
    </MessageContent>
  );
};

const renderAssistantText = (message: LiveMessage, t: TFunction) => {
  return (
    <MessageContent className={assistantContentClass}>
      <div className="flex items-start gap-2">
        <div className="relative mt-1.5 shrink-0 size-2">
          <span
            className={cn(
              "absolute inset-0 rounded-full transition-all",
              message.isStreaming
                ? "bg-green-500 shadow-[0_0_6px_rgba(34,197,94,0.4)] animate-[glow-pulse_1.5s_ease-in-out_infinite]"
                : "bg-muted-foreground/40",
            )}
          />
        </div>
        <div className="flex-1 min-w-0">
          <MessageResponse
            className="wrap-break-word"
            mode={message.isStreaming ? "streaming" : "static"}
            parseIncompleteMarkdown={Boolean(message.isStreaming)}
          >
            {message.content || t("chat:thinkingResponse")}
          </MessageResponse>
        </div>
      </div>
    </MessageContent>
  );
};

const renderChainOfThoughtMessage = (message: LiveMessage, t: TFunction) => {
  const details = message.chainOfThought;
  if (!details) {
    return renderAssistantText(message, t);
  }
  const visibleSteps = details.steps.slice(0, details.revealedSteps);

  return (
    <MessageContent className={assistantContentClass}>
      <ChainOfThought className="space-y-3">
        <ChainOfThoughtHeader>{details.title}</ChainOfThoughtHeader>
        <ChainOfThoughtContent>
          {visibleSteps.map((step, index) => {
            const isLast = index === visibleSteps.length - 1;
            const status: "complete" | "active" =
              message.isStreaming && isLast ? "active" : "complete";
            return (
              <ChainOfThoughtStepItem
                description={step.description}
                key={`${message.id}-cot-${index}`}
                label={step.label}
                status={status}
              />
            );
          })}
          {details.relatedSources && details.relatedSources.length > 0 ? (
            <ChainOfThoughtSearchResults className="pt-1">
              {details.relatedSources.map((source) => (
                <ChainOfThoughtSearchResult key={`${message.id}-${source}`}>
                  {source}
                </ChainOfThoughtSearchResult>
              ))}
            </ChainOfThoughtSearchResults>
          ) : null}
        </ChainOfThoughtContent>
      </ChainOfThought>
      {message.isStreaming ? (
        <div className={`mt-2 ${assistantMetaTextClass}`}>
          {t("chat:reasoningRequest")}
        </div>
      ) : null}
    </MessageContent>
  );
};

const RUNNING_TOOL_STATES = new Set([
  "input-streaming",
  "input-available",
  "approval-requested",
  "question-requested",
]);

/**
 * Tool card with smart open state: running tools stay expanded with live
 * output, finished tools collapse to a single-line summary card. A manual
 * toggle overrides the heuristic until `blocksExpanded` changes (the key
 * remounts this component, resetting the override).
 */
const SmartTool = ({
  message,
  blocksExpanded,
  children,
}: {
  message: LiveMessage;
  blocksExpanded: boolean;
  children: ReactNode;
}) => {
  const isRunning =
    message.isStreaming === true ||
    (message.toolCall ? RUNNING_TOOL_STATES.has(message.toolCall.state) : false);
  const [override, setOverride] = useState<boolean | null>(null);
  const open = override ?? (blocksExpanded || isRunning);
  return (
    <Tool open={open} onOpenChange={setOverride}>
      {children}
    </Tool>
  );
};

const renderToolMessage = ({
  message,
  pendingApprovalMap,
  onApprovalAction,
  canRespondToApproval,
  blocksExpanded,
  t,
}: {
  message: LiveMessage;
  pendingApprovalMap: Record<string, boolean>;
  onApprovalAction?: AssistantApprovalHandler;
  canRespondToApproval: boolean;
  blocksExpanded: boolean;
  t: TFunction;
}) => {
  const toolCall = message.toolCall;
  if (!toolCall) {
    return renderAssistantText(message, t);
  }

  // Think tool: render as lightweight reasoning-style block
  if (toolCall.title === "Think") {
    return renderThinkToolMessage(message, blocksExpanded);
  }

  const shouldShowOutput = Boolean(
    toolCall.output ?? toolCall.errorText ?? toolCall.display,
  );
  const approval = toolCall.approval;
  const approvalId = approval?.id;
  const approvalResponse =
    typeof approval?.response === "string" ? approval.response : undefined;
  const isApprovalRequested = toolCall.state === "approval-requested";
  const isApprovalDenied = toolCall.state === "output-denied";
  const approvalPending =
    approvalId !== undefined ? pendingApprovalMap[approvalId] === true : false;
  const disableApprovalActions = !(
    canRespondToApproval &&
    onApprovalAction &&
    !approvalPending &&
    !approval?.submitted &&
    isApprovalRequested
  );

  const subagentOriginLabel = toolCall.isSubagentOrigin
    ? toolCall.subagentType
      ? t("chat:subAgentSuffix", { type: toolCall.subagentType })
      : t("chat:subAgent")
    : null;

  const toolSummary = getToolSummary(toolCall.title, toolCall.input, t);

  const toolBlock = (
    <div className="space-y-1">
      <SmartTool
        key={`${message.id}-${blocksExpanded}`}
        message={message}
        blocksExpanded={blocksExpanded}
      >
        <ToolHeader
          state={toolCall.state}
          title={toolCall.title}
          type={toolCall.type}
          input={toolCall.input}
          summary={toolSummary}
        />
        <ToolContent>
          {toolCall.input ? <ToolInput input={toolCall.input} /> : null}
          <ToolDisplay display={toolCall.display} isError={toolCall.isError} />
          {toolCall.subagentSteps && toolCall.subagentSteps.length > 0 ? (
            <SubagentActivity
              steps={toolCall.subagentSteps}
              isRunning={toolCall.subagentRunning}
              defaultOpen={blocksExpanded}
              subagentType={toolCall.subagentType}
            />
          ) : null}
          {shouldShowOutput ? (
            <ToolOutput
              errorText={toolCall.errorText}
              output={toolCall.output}
              message={toolCall.message}
            />
          ) : null}
          {approval ? (
            <Confirmation
              approval={approval}
              state={toolCall.state}
              className="rounded-md bg-muted/30 px-3 py-2.5 text-sm"
            >
              <ConfirmationTitle>
                {t("chat:manualApprovalRequired", { sender: approval.sender })}
              </ConfirmationTitle>
              <ConfirmationRequest>
                <div className="text-sm text-muted-foreground">
                  <p>
                    <span className="font-medium text-foreground">{t("chat:actionLabel")}</span>{" "}
                    {approval.action}
                  </p>
                  {approval.description ? (
                    <p className="mt-2 text-foreground">
                      {approval.description}
                    </p>
                  ) : null}
                </div>
                <ConfirmationActions className="mt-2 gap-2">
                  <ConfirmationAction
                    disabled={disableApprovalActions}
                    onClick={() =>
                      approval && onApprovalAction?.(approval, "reject")
                    }
                    variant="outline"
                  >
                    {approvalPending ? t("chat:declining") : t("chat:decline")}
                  </ConfirmationAction>
                  <ConfirmationAction
                    disabled={disableApprovalActions}
                    onClick={() =>
                      approval && onApprovalAction?.(approval, "approve")
                    }
                  >
                    {approvalPending ? t("chat:confirming") : t("chat:approve")}
                  </ConfirmationAction>
                  <ConfirmationAction
                    disabled={disableApprovalActions}
                    onClick={() =>
                      approval &&
                      onApprovalAction?.(approval, "approve_for_session")
                    }
                    variant="secondary"
                    className="hover:bg-primary/30"
                  >
                    {approvalPending
                      ? t("chat:approvingSession")
                      : t("chat:approveForSession")}
                  </ConfirmationAction>
                </ConfirmationActions>
              </ConfirmationRequest>
              <ConfirmationAccepted>
                <div className="rounded-md bg-success/10 px-3 py-2 text-xs text-success">
                  {approvalResponse === "approve_for_session"
                    ? t("chat:sessionApproved")
                    : t("chat:approvalConfirmed")}
                </div>
              </ConfirmationAccepted>
              <ConfirmationRejected>
                <div className="rounded-md bg-warning/10 px-3 py-2 text-xs text-warning">
                  {t("chat:requestDenied")}
                  {approval.reason ? `: ${approval.reason}` : "."}
                </div>
              </ConfirmationRejected>
            </Confirmation>
          ) : null}
        </ToolContent>
      </SmartTool>
      {toolCall.mediaParts ? (
        <ToolMediaPreview mediaParts={toolCall.mediaParts} />
      ) : null}
      {toolCall.compactedMediaCount ? (
        <div className="mt-1 ml-4">
          <CompactedMediaChip count={toolCall.compactedMediaCount} />
        </div>
      ) : null}
      {isApprovalRequested ? (
        <div className={assistantMetaTextClass}>{t("chat:waitingApproval")}</div>
      ) : isApprovalDenied ? (
        <div className={assistantMetaTextClass}>{t("chat:toolCancelled")}</div>
      ) : null}
    </div>
  );

  // Sub-agent origin: wrap in a visually demoted container with source label
  if (subagentOriginLabel) {
    return (
      <div className="border-l-2 border-muted-foreground/20 pl-3 opacity-80">
        <div className="text-[11px] text-muted-foreground/60 mb-0.5">
          {subagentOriginLabel}
        </div>
        {toolBlock}
      </div>
    );
  }

  return toolBlock;
};

const ThinkToolBlock = ({
  message,
  defaultOpen,
}: { message: LiveMessage; defaultOpen: boolean }) => {
  const { t } = useTranslation();
  const toolCall = message.toolCall;
  const thought =
    toolCall?.input && typeof toolCall.input === "object"
      ? (toolCall.input as Record<string, unknown>).thought
      : undefined;
  const thoughtText = typeof thought === "string" ? thought : "";
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const isComplete =
    toolCall?.state === "output-available" ||
    toolCall?.state === "output-error" ||
    toolCall?.state === "output-denied";

  return (
    <MessageContent className={assistantContentClass}>
      <div className="not-prose">
        <button
          type="button"
          className="flex items-center gap-1.5 text-sm text-muted-foreground cursor-pointer"
          onClick={() => setIsOpen(!isOpen)}
        >
          <BrainIcon className="size-3.5 text-muted-foreground/70 shrink-0" />
          <span className="italic">
            {isComplete
              ? t("chat:thoughtDone")
              : t("chat:thinkingProblem")}
          </span>
          <ChevronRightIcon
            className={cn(
              "size-3 text-muted-foreground/50 transition-transform duration-200",
              isOpen && "rotate-90",
            )}
          />
        </button>
        {isOpen && thoughtText && (
          <div className="mt-1.5 pl-4 border-l-2 border-border text-sm text-muted-foreground italic whitespace-pre-wrap">
            {thoughtText.length > 500
              ? `${thoughtText.slice(0, 500)}…`
              : thoughtText}
          </div>
        )}
      </div>
    </MessageContent>
  );
};

const renderThinkToolMessage = (
  message: LiveMessage,
  blocksExpanded: boolean,
) => {
  return (
    <ThinkToolBlock
      key={`${message.id}-think-${blocksExpanded}`}
      message={message}
      defaultOpen={blocksExpanded}
    />
  );
};

const renderCodeMessage = (message: LiveMessage, t: TFunction) => {
  const snippet = message.codeSnippet;
  if (!snippet) {
    return renderAssistantText(message, t);
  }

  return (
    <MessageContent className={assistantContentClass}>
      <MessageResponse
        className="wrap-break-word font-medium"
        mode={message.isStreaming ? "streaming" : "static"}
        parseIncompleteMarkdown={Boolean(message.isStreaming)}
      >
        {message.content ?? snippet.title ?? t("chat:generatedCode")}
      </MessageResponse>
      {snippet.code ? (
        <div className="mt-3">
          <CodeBlock
            code={snippet.code}
            language={snippet.language}
            showLineNumbers
          />
        </div>
      ) : (
        <div className={`mt-3 ${assistantMetaTextClass}`}>
          {t("chat:assemblingSnippet")}
        </div>
      )}
    </MessageContent>
  );
};

const renderThinkingMessage = (
  message: LiveMessage,
  blocksExpanded: boolean,
  t: TFunction,
) => {
  const thinkingContent = message.thinking;
  if (!thinkingContent) {
    return renderAssistantText(message, t);
  }

  return (
    <MessageContent className={assistantContentClass}>
      <Reasoning
        key={`${message.id}-${blocksExpanded}`}
        isStreaming={message.isStreaming}
        duration={message.thinkingDuration}
        defaultOpen={blocksExpanded}
        disableAutoClose
      >
        <ReasoningTrigger />
        <ReasoningContent>{thinkingContent}</ReasoningContent>
      </Reasoning>
    </MessageContent>
  );
};
