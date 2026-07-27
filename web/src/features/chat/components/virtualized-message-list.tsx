import type { LiveMessage } from "@/hooks/types";
import {
  Message,
  MessageActions,
  MessageAttachment,
  MessageAttachments,
  MessageContent,
  MessageCopyButton,
  MessageForkButton,
  UserMessageContent,
} from "@ai-elements";
import {
  AssistantMessage,
  type AssistantApprovalHandler,
} from "./assistant-message";

import type React from "react";
import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
  type ComponentPropsWithoutRef,
} from "react";
import { useTranslation } from "react-i18next";
import { Virtuoso, type VirtuosoHandle } from "react-virtuoso";
import { Loader2Icon, WrenchIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { CompactedMediaChip } from "./compacted-media-chip";

export type VirtualizedMessageListProps = {
  messages: LiveMessage[];
  conversationKey: string;
  pendingApprovalMap: Record<string, boolean>;
  onApprovalAction?: AssistantApprovalHandler;
  canRespondToApproval: boolean;
  blocksExpanded: boolean;
  /** Index of message to highlight (for search) */
  highlightedMessageIndex?: number;
  /** Callback when scroll position changes */
  onAtBottomChange?: (atBottom: boolean) => void;
  /** Callback to fork session from before a specific turn */
  onForkSession?: (turnIndex: number) => void;
  /** Whether the initial replay is still running (suppresses auto-scroll) */
  isReplayingHistory?: boolean;
  /** Whether older history pages exist on the server */
  hasMoreHistory?: boolean;
  /** Whether an older history page is being fetched */
  isLoadingOlder?: boolean;
  /** Fetch and prepend the next older history page */
  onLoadOlderHistory?: () => Promise<void>;
};

export type VirtualizedMessageListHandle = {
  scrollToIndex: (index: number, behavior?: "auto" | "smooth") => void;
  scrollToBottom: () => void;
};

type ConversationListItem = {
  message: LiveMessage;
  index: number;
};

// Virtuoso firstItemIndex base; prepends decrement from here so the
// scroll anchor is preserved when older pages are added at the top.
const FIRST_ITEM_BASE = 1_000_000;
const START_REACHED_DEBOUNCE_MS = 500;

/** Visual group of consecutive assistant tool calls (stacked, less noise) */
type ToolGroupInfo = {
  index: number;
  size: number;
};

const isGroupableToolMessage = (message: LiveMessage): boolean =>
  message.role === "assistant" &&
  message.variant === "tool" &&
  message.toolCall?.title !== "Think";

function VirtuosoScrollerComponent(
  props: ComponentPropsWithoutRef<"div">,
  ref: React.Ref<HTMLDivElement>,
) {
  const { className, ...rest } = props;
  return (
    <div
      ref={ref}
      className={cn(
        "flex-1 overflow-y-auto overflow-x-hidden pr-1 sm:pr-2",
        className,
      )}
      {...rest}
    />
  );
}

const VirtuosoScroller = forwardRef(VirtuosoScrollerComponent);

function VirtuosoListComponent(
  props: ComponentPropsWithoutRef<"div">,
  ref: React.Ref<HTMLDivElement>,
) {
  const { className, ...rest } = props;
  return (
    <div
      ref={ref}
      className={cn("flex flex-col px-3 py-4 sm:px-6 lg:px-8", className)}
      {...rest}
    />
  );
}

const VirtuosoList = forwardRef(VirtuosoListComponent);

VirtuosoScroller.displayName = "VirtuosoScroller";
VirtuosoList.displayName = "VirtuosoList";

function getMessageSpacingClass(
  message: LiveMessage,
  index: number,
  allMessages: LiveMessage[],
): string | undefined {
  // Terminal-style message spacing - more compact
  // 1. User messages get breathing room (`mt-3`) from previous content
  // 2. Assistant messages flow naturally with minimal spacing
  // 3. Tool calls have subtle spacing to group related operations
  const previousMessage = index > 0 ? allMessages[index - 1] : undefined;
  const nextMessage =
    index < allMessages.length - 1 ? allMessages[index + 1] : undefined;

  const classes: string[] = [];

  const isUser = message.role === "user";
  const isAssistant = message.role === "assistant";
  const isToolMessage = isAssistant && message.variant === "tool";
  const isThinkingMessage = isAssistant && message.variant === "thinking";
  const previousIsUser = previousMessage?.role === "user";
  const previousIsAssistant = previousMessage?.role === "assistant";
  const previousIsTool =
    previousIsAssistant && previousMessage?.variant === "tool";

  if (index > 0) {
    if (isUser) {
      // User messages get more space from previous content
      classes.push("mt-4");
    } else if (isAssistant) {
      if (isToolMessage) {
        // Tool calls: slightly more breathing room between consecutive calls
        classes.push(previousIsUser ? "mt-2" : "mt-1.5");
      } else if (isThinkingMessage) {
        // Thinking blocks have minimal spacing
        classes.push(previousIsUser ? "mt-2" : "mt-1");
      } else if (previousIsTool) {
        // Text after tool gets slight spacing
        classes.push("mt-2");
      } else if (previousIsAssistant) {
        // Consecutive assistant messages flow together
        classes.push("mt-1");
      } else {
        // After user message
        classes.push("mt-2");
      }
    }
  }

  // Add bottom margin for the last message to avoid clashing with UI below
  if (!nextMessage) {
    classes.push("mb-30");
  }

  return classes.length > 0 ? classes.join(" ") : undefined;
}

function VirtualizedMessageListComponent(
  {
    messages,
    conversationKey,
    pendingApprovalMap,
    onApprovalAction,
    canRespondToApproval,
    blocksExpanded,
    highlightedMessageIndex = -1,
    onAtBottomChange,
    onForkSession,
    isReplayingHistory = false,
    hasMoreHistory = false,
    isLoadingOlder = false,
    onLoadOlderHistory,
  }: VirtualizedMessageListProps,
  ref: React.Ref<VirtualizedMessageListHandle>,
) {
  const virtuosoRef = useRef<VirtuosoHandle | null>(null);
  const scrollerRef = useRef<HTMLElement | null>(null);
  const { t } = useTranslation();
  const [firstItemIndex, setFirstItemIndex] = useState(FIRST_ITEM_BASE);
  const prevFirstIdRef = useRef<string | null>(null);
  const prevLengthRef = useRef(0);
  const startReachedAtRef = useRef(0);

  // Filtered messages list (excluding message-id) aligned with listItems indices
  const filteredMessages = useMemo(
    () => messages.filter((m) => m.variant !== "message-id"),
    [messages],
  );

  const listItems = useMemo<ConversationListItem[]>(
    () =>
      filteredMessages.map((message, index) => ({ message, index })),
    [filteredMessages],
  );

  const listItemsRef = useRef<ConversationListItem[]>([]);
  listItemsRef.current = listItems;

  // Reset scroll anchoring when switching conversations
  // biome-ignore lint/correctness/useExhaustiveDependencies: conversationKey is the intentional reset trigger; list items are read via ref
  useEffect(() => {
    setFirstItemIndex(FIRST_ITEM_BASE);
    prevFirstIdRef.current = listItemsRef.current[0]?.message.id ?? null;
    prevLengthRef.current = listItemsRef.current.length;
  }, [conversationKey]);

  // Prepend detection: first message id changed without conversation switch
  // → an older page was prepended. Decrement firstItemIndex by the number
  // of new items so the viewport stays anchored (no scroll jump).
  useEffect(() => {
    const firstId = listItems[0]?.message.id ?? null;
    const prevFirstId = prevFirstIdRef.current;
    if (prevFirstId !== null && firstId !== null && firstId !== prevFirstId) {
      const prepended = listItems.length - prevLengthRef.current;
      if (prepended > 0) {
        setFirstItemIndex((value) => value - prepended);
      }
    }
    prevFirstIdRef.current = firstId;
    prevLengthRef.current = listItems.length;
  }, [listItems]);

  // During the initial replay we suppress auto-scroll entirely and jump to
  // the bottom exactly once, when replay/history completes.
  const prevReplayingRef = useRef(isReplayingHistory);
  useEffect(() => {
    if (prevReplayingRef.current && !isReplayingHistory && listItems.length > 0) {
      virtuosoRef.current?.scrollToIndex({
        index: listItems.length - 1,
        align: "end",
        behavior: "auto",
      });
    }
    prevReplayingRef.current = isReplayingHistory;
  }, [isReplayingHistory, listItems.length]);

  // Map message id -> position within a run of consecutive tool calls
  const toolGroups = useMemo(() => {
    const groups = new Map<string, ToolGroupInfo>();
    let run: string[] = [];
    const flush = () => {
      if (run.length >= 2) {
        for (const [index, id] of run.entries()) {
          groups.set(id, { index, size: run.length });
        }
      }
      run = [];
    };
    for (const message of filteredMessages) {
      if (isGroupableToolMessage(message)) {
        run.push(message.id);
      } else {
        flush();
      }
    }
    flush();
    return groups;
  }, [filteredMessages]);

  const handleAtBottomChange = useCallback(
    (atBottom: boolean) => {
      onAtBottomChange?.(atBottom);
    },
    [onAtBottomChange],
  );

  const handleScrollerRef = useCallback(
    (ref: HTMLElement | Window | null) => {
      scrollerRef.current = ref instanceof HTMLElement ? ref : null;
    },
    [],
  );

  // Use a generous threshold to tolerate height estimation mismatches
  // when blocks are expanded (actual heights >> defaultItemHeight).
  // This is decoupled from atBottomStateChange which uses Virtuoso's
  // default tight threshold for the scroll-to-bottom button.
  const handleFollowOutput = useCallback(
    (isAtBottom: boolean) => {
      // No auto-scroll during initial replay or while older pages load;
      // only follow live output when the user is pinned to the bottom.
      if (isReplayingHistory || isLoadingOlder) return false;
      if (isAtBottom) return "auto" as const;
      const scroller = scrollerRef.current;
      if (scroller) {
        const gap =
          scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight;
        if (gap <= 1500) return "auto" as const;
      }
      return false;
    },
    [isReplayingHistory, isLoadingOlder],
  );

  const handleStartReached = useCallback(() => {
    const canLoadOlder =
      onLoadOlderHistory && hasMoreHistory && !isLoadingOlder;
    if (!canLoadOlder) return;
    const now = Date.now();
    if (now - startReachedAtRef.current < START_REACHED_DEBOUNCE_MS) return;
    startReachedAtRef.current = now;
    onLoadOlderHistory().catch((error: unknown) => {
      console.error("[MessageList] load older history failed:", error);
    });
  }, [onLoadOlderHistory, hasMoreHistory, isLoadingOlder]);

  useImperativeHandle(
    ref,
    () => ({
      scrollToIndex: (
        index: number,
        behavior: "auto" | "smooth" = "smooth",
      ) => {
        virtuosoRef.current?.scrollToIndex({
          index,
          align: "center",
          behavior,
        });
      },
      scrollToBottom: () => {
        if (listItems.length > 0) {
          virtuosoRef.current?.scrollToIndex({
            index: listItems.length - 1,
            align: "end",
            behavior: "auto",
          });
        }
      },
    }),
    [listItems.length],
  );

  const ListHeader = useMemo(() => {
    const showHeader = hasMoreHistory && onLoadOlderHistory;
    if (!showHeader) return undefined;
    const HeaderComponent = () => (
      <div className="flex justify-center pb-2 pt-1">
        <button
          type="button"
          onClick={handleStartReached}
          disabled={isLoadingOlder}
          className="inline-flex cursor-pointer items-center gap-1.5 rounded-full border border-border-subtle bg-surface-muted/60 px-3 py-1 text-xs text-muted-foreground transition-colors hover:text-foreground disabled:opacity-60"
        >
          {isLoadingOlder && <Loader2Icon className="size-3 animate-spin" />}
          {t("chat:loadOlderMessages")}
        </button>
      </div>
    );
    HeaderComponent.displayName = "ListHeader";
    return HeaderComponent;
  }, [hasMoreHistory, onLoadOlderHistory, isLoadingOlder, handleStartReached, t]);

  return (
    <Virtuoso
      key={conversationKey}
      ref={virtuosoRef}
      data={listItems}
      className="h-full"
      scrollerRef={handleScrollerRef}
      followOutput={handleFollowOutput}
      firstItemIndex={firstItemIndex}
      startReached={handleStartReached}
      defaultItemHeight={160}
      increaseViewportBy={{ top: 400, bottom: 400 }}
      overscan={200}
      minOverscanItemCount={4}
      atBottomStateChange={handleAtBottomChange}
      initialTopMostItemIndex={{
        index: Math.max(0, listItems.length - 1),
        align: "end",
      }}
      components={{
        Scroller: VirtuosoScroller,
        List: VirtuosoList,
        ...(ListHeader ? { Header: ListHeader } : {}),
      }}
      computeItemKey={(_index: number, item: ConversationListItem) =>
        item.message.id
      }
      itemContent={(_index, item) => {
        const message = item.message;

        if (message.variant === "status") {
          return (
            <Message
              className={messages.length > 0 ? "mt-2" : undefined}
              from="assistant"
            >
              <MessageContent className="text-xs text-muted-foreground">
                {message.content}
              </MessageContent>
            </Message>
          );
        }

        let spacingClass = getMessageSpacingClass(
          message,
          item.index,
          filteredMessages,
        );

        const isHighlighted = item.index === highlightedMessageIndex;
        const group = toolGroups.get(message.id);

        // Inside a tool group the wrapper owns the outer spacing
        if (group && spacingClass) {
          spacingClass =
            spacingClass
              .split(" ")
              .filter(
                (cls) =>
                  (group.index === 0 || !cls.startsWith("mt-")) &&
                  (group.index >= group.size - 1 || cls !== "mb-30"),
              )
              .join(" ") || undefined;
        }

        const messageNode = (
          <Message
            className={cn(
              spacingClass,
              isHighlighted && "rounded-lg ring-2 ring-primary/50",
            )}
            from={message.role}
          >
            {message.role === "user" ? (
              message.content ? (
                <UserMessageContent>{message.content}</UserMessageContent>
              ) : null
            ) : (
              <>
                <AssistantMessage
                  message={message}
                  pendingApprovalMap={pendingApprovalMap}
                  onApprovalAction={onApprovalAction}
                  canRespondToApproval={canRespondToApproval}
                  blocksExpanded={blocksExpanded}
                />
                {!message.isStreaming &&
                  (!message.variant || message.variant === "text") &&
                  (message.content || (onForkSession && message.turnIndex !== undefined)) && (
                  <MessageActions className="
                  hover-reveal
                   opacity-0 group-hover:opacity-100 transition-opacity mt-1">
                    {message.content && <MessageCopyButton content={message.content} />}
                    {onForkSession && message.turnIndex !== undefined && (
                      <MessageForkButton onFork={() => onForkSession(message.turnIndex!)} />
                    )}
                  </MessageActions>
                )}
              </>
            )}
            {message.attachments && message.attachments.length > 0 ? (
              <MessageAttachments>
                {message.attachments.map((attachment, attIdx) => {
                  const key =
                    "kind" in attachment
                      ? (attachment.filename ?? `${message.id}-${attIdx}`)
                      : (attachment.filename ??
                        attachment.url ??
                        `${message.id}-${attIdx}`);
                  if ("kind" in attachment && attachment.kind === "compacted") {
                    return (
                      <CompactedMediaChip
                        key={key}
                        filename={attachment.filename}
                      />
                    );
                  }
                  return (
                    <MessageAttachment
                      className="size-28 sm:size-32 lg:size-40"
                      data={attachment}
                      key={key}
                    />
                  );
                })}
              </MessageAttachments>
            ) : null}
          </Message>
        );

        if (!group) {
          return messageNode;
        }

        return (
          <div
            className={cn(
              "border-x border-border-subtle bg-surface-muted/40 px-2",
              group.index === 0 && "mt-2 rounded-t-lg border-t pt-1",
              group.index === group.size - 1 && "mb-2 rounded-b-lg border-b pb-1",
            )}
          >
            {group.index === 0 && (
              <div className="flex items-center gap-1 pt-1 text-[10px] text-muted-foreground/70 select-none">
                <WrenchIcon className="size-3" />
                {t("chat:toolGroupCount", { count: group.size })}
              </div>
            )}
            {messageNode}
          </div>
        );
      }}
    />
  );
}

export const VirtualizedMessageList = forwardRef(
  VirtualizedMessageListComponent,
);
VirtualizedMessageList.displayName = "VirtualizedMessageList";
