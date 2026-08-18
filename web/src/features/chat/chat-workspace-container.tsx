/**
 * Container component that subscribes to useSessionStream.
 *
 * This exists to isolate high-frequency message updates from App, preventing
 * unnecessary re-renders of SessionsSidebar. When messages update, only this
 * container and ChatWorkspace re-render, not App.
 *
 * TODO: This layer could be simplified by moving useSessionStream directly
 * into ChatWorkspace. The Container/Presentational split here doesn't provide
 * much value since ChatWorkspace receives `messages` as a prop and re-renders
 * on every update anyway.
 */
import { type ReactElement, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import type { ChatStatus, FileUIPart } from "ai";
import type { PromptInputMessage } from "@ai-elements";
import { toast } from "sonner";
import type {
  Session,
  SessionStatus,
  UploadSessionFileResponse,
} from "@/lib/api/models";
import { useGlobalConfig } from "@/hooks/useGlobalConfig";
import type { SessionFileEntry } from "@/hooks/useSessions";
import { getApiBaseUrl, isMacOS } from "@/hooks/utils";
import { useSessionStream } from "@/hooks/useSessionStream";
import { useToolEventsStore } from "@/features/tool/store";
import { useQueueStore } from "./queue-store";
import { ChatWorkspace } from "./chat";

type PendingMessage = {
  text: string;
  targetSessionId: string;
};

type ChatWorkspaceContainerProps = {
  selectedSessionId: string;
  currentSession?: Session;
  sessionDescription?: string;
  onSessionStatus: (status: SessionStatus) => void;
  onStreamStatusChange?: (status: ChatStatus) => void;
  uploadSessionFile: (
    sessionId: string,
    file: File,
  ) => Promise<UploadSessionFileResponse>;
  onListSessionDirectory?: (
    sessionId: string,
    path?: string,
  ) => Promise<SessionFileEntry[]>;
  onGetSessionFileUrl?: (sessionId: string, path: string) => string;
  onGetSessionFile?: (sessionId: string, path: string) => Promise<Blob>;
  onOpenCreateDialog?: () => void;
  onOpenSidebar?: () => void;
  generateTitle?: (sessionId: string) => Promise<string | null>;
  onRenameSession?: (sessionId: string, newTitle: string) => Promise<boolean>;
  onForkSession?: (sessionId: string, turnIndex: number) => Promise<void>;
  onForkSessionLatest?: (sessionId: string) => Promise<void>;
};

export function ChatWorkspaceContainer({
  selectedSessionId,
  currentSession,
  sessionDescription,
  onSessionStatus,
  onStreamStatusChange,
  uploadSessionFile,
  onListSessionDirectory,
  onGetSessionFileUrl,
  onGetSessionFile,
  onOpenCreateDialog,
  onOpenSidebar,
  generateTitle,
  onRenameSession,
  onForkSession,
  onForkSessionLatest,
}: ChatWorkspaceContainerProps): ReactElement {
  const { t } = useTranslation();
  const [isUploadingFiles, setIsUploadingFiles] = useState(false);
  // Pending message state for when we need to create a session first
  const [pendingMessage, setPendingMessage] = useState<PendingMessage | null>(
    null,
  );
  const sessionId = selectedSessionId || null;

  const { config } = useGlobalConfig();
  const maxContextSize = useMemo(() => {
    if (!config) return undefined;
    const model = config.models.find((m) => m.name === config.defaultModel);
    return model?.maxContextSize;
  }, [config]);

  const handleStreamError = useCallback((error: Error) => {
    toast.error(t("chat:connectionError"), {
      description: error.message,
    });
  }, [t]);

  // Handle first turn completion for auto-rename
  // Backend reads messages from wire.jsonl automatically
  const handleFirstTurnComplete = useCallback(async () => {
    if (!(selectedSessionId && generateTitle)) {
      return;
    }

    await generateTitle(selectedSessionId);
  }, [selectedSessionId, generateTitle]);

  const sessionStream = useSessionStream({
    sessionId,
    baseUrl: getApiBaseUrl(),
    onError: handleStreamError,
    onSessionStatus,
    onFirstTurnComplete: handleFirstTurnComplete,
  });

  const {
    messages,
    status,
    isAwaitingFirstResponse,
    sendMessage,
    respondToApproval,
    respondToQuestion,
    cancel: cancelStream,
    contextUsage,
    tokenUsage,
    currentStep,
    isConnected: isStreamConnected,
    isReplayingHistory,
    planMode,
    sendSetPlanMode,
    slashCommands,
    error: streamError,
    hasMoreHistory,
    isLoadingOlder,
    loadOlderHistory,
    lastPrependCountRef,
  } = sessionStream;

  const clearNewFiles = useToolEventsStore((state) => state.clearNewFiles);
  const enqueue = useQueueStore((s) => s.enqueue);
  const queueLength = useQueueStore((s) => s.queue.length);
  const dequeue = useQueueStore((s) => s.dequeue);
  const clearQueue = useQueueStore((s) => s.clearQueue);

  useEffect(() => {
    if (status === "streaming") {
      clearNewFiles();
    }
  }, [status, clearNewFiles]);

  // Clear queue when session changes (must run before auto-send to prevent
  // sending stale queued messages to the wrong session)
  // biome-ignore lint/correctness/useExhaustiveDependencies: selectedSessionId triggers queue clear on session switch
  useEffect(() => {
    clearQueue();
  }, [selectedSessionId, clearQueue]);

  // Auto-send next queued message when status becomes ready
  const prevStatusRef = useRef(status);
  useEffect(() => {
    const wasProcessing =
      prevStatusRef.current === "streaming" ||
      prevStatusRef.current === "submitted" ||
      prevStatusRef.current === "error";
    prevStatusRef.current = status;

    if (status === "ready" && wasProcessing && queueLength > 0) {
      const next = dequeue();
      if (next) {
        sendMessage(next.text);
      }
    }
  }, [status, queueLength, dequeue, sendMessage]);

  useEffect(() => {
    onStreamStatusChange?.(status);
  }, [status, onStreamStatusChange]);

  useEffect(() => {
    if (
      !pendingMessage ||
      pendingMessage.targetSessionId !== selectedSessionId ||
      !isStreamConnected ||
      (status !== "ready" && status !== "streaming")
    ) {
      return;
    }

    // Send only when the stream is connected to the intended session.
    // Using state (not ref) ensures this effect re-runs even if connection
    // happens before the pending message is set.
    setPendingMessage(null);
    sendMessage(pendingMessage.text);
  }, [
    isStreamConnected,
    status,
    selectedSessionId,
    sendMessage,
    pendingMessage,
  ]);

  useEffect(() => {
    if (
      !pendingMessage ||
      pendingMessage.targetSessionId === selectedSessionId
    ) {
      return;
    }

    // Drop stale pending messages if the user switches away before it is sent.
    setPendingMessage(null);
  }, [pendingMessage, selectedSessionId]);

  const uploadFilesToSession = useCallback(
    async (targetSessionId: string, files: FileUIPart[]) => {
      if (files.length === 0) {
        return 0;
      }

      setIsUploadingFiles(true);
      try {
        const uploadResults = await Promise.all(
          files.map(async (filePart) => {
            if (!filePart.url) return false;

            const response = await fetch(filePart.url);
            const blob = await response.blob();
            const file = new File([blob], filePart.filename ?? "unnamed_file", {
              type: filePart.mediaType ?? blob.type,
            });

            const uploadResult = await uploadSessionFile(targetSessionId, file);
            console.log(
              "[ChatWorkspaceContainer] File uploaded:",
              uploadResult,
            );
            return true;
          }),
        );

        const uploadedCount = uploadResults.filter(Boolean).length;
        if (uploadedCount > 0) {
          toast.success(t("chat:filesUploaded"), {
            description:
              uploadedCount === 1
                ? t("chat:filesUploadedOne")
                : t("chat:filesUploadedMany", { count: uploadedCount }),
          });
        }
        return uploadedCount;
      } catch (error) {
        console.error(
          "[ChatWorkspaceContainer] Failed to upload files:",
          error,
        );
        toast.error(t("chat:uploadFailedTitle"), {
          description:
            error instanceof Error ? error.message : t("chat:uploadFailed"),
        });
        return 0;
      } finally {
        setIsUploadingFiles(false);
      }
    },
    [uploadSessionFile, t],
  );

  const handlePromptSubmit = useCallback(
    async (message: PromptInputMessage) => {
      const hasPayload =
        message.text.trim().length > 0 || message.files.length > 0;
      if (!hasPayload) {
        toast.info(t("chat:emptyMessage"), {
          description: t("chat:emptyMessageDesc"),
        });
        return;
      }

      if (isUploadingFiles) {
        toast.info(t("chat:stillUploading"), {
          description: t("chat:stillUploadingDesc"),
        });
        return;
      }

      if (status === "streaming" || status === "submitted") {
        // Queue text-only messages when AI is processing
        if (message.files.length > 0) {
          toast.info(t("chat:stillProcessing"), {
            description: t("chat:stillProcessingDesc"),
          });
          return;
        }
        const messageText = message.text.trim();
        if (messageText) {
          enqueue(messageText);
          toast.info(t("chat:messageQueued"), {
            description: t("chat:messageQueuedDesc"),
          });
        }
        return;
      }

      // Note: This check is defensive - the submit button is disabled when no session exists
      if (!selectedSessionId) {
        return;
      }

      const targetSessionId = selectedSessionId;

      if (message.files.length > 0 && targetSessionId) {
        await uploadFilesToSession(targetSessionId, message.files);
      }

      const messageText =
        message.text.trim() ||
        (message.files.length > 0 ? "KIMI_FILE_UPLOAD_WITHOUT_MESSAGE" : "");

      await sendMessage(messageText);
    },
    [status, isUploadingFiles, selectedSessionId, uploadFilesToSession, sendMessage, enqueue, t],
  );

  const handlePlanModeChange = useCallback((enabled: boolean) => {
    sendSetPlanMode(enabled);
  }, [sendSetPlanMode]);

  const handleForkSession = useCallback(
    async (turnIndex: number) => {
      if (!(selectedSessionId && onForkSession)) {
        return;
      }
      try {
        await onForkSession(selectedSessionId, turnIndex);
        toast.success(t("chat:sessionForked"));
      } catch (error) {
        toast.error(t("chat:forkFailed"), {
          description:
            error instanceof Error ? error.message : t("chat:forkFailedFallback"),
        });
      }
    },
    [selectedSessionId, onForkSession, t],
  );

  const handleForkSessionLatest = useCallback(async () => {
    if (!(selectedSessionId && onForkSessionLatest)) return;
    await onForkSessionLatest(selectedSessionId);
  }, [selectedSessionId, onForkSessionLatest]);

  const handleRegenerateTitle = useCallback(async () => {
    if (!(selectedSessionId && generateTitle)) return;
    const title = await generateTitle(selectedSessionId);
    if (title) {
      toast.success(t("sessions:regenerateTitleSuccess"), { description: title });
    }
  }, [selectedSessionId, generateTitle, t]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.defaultPrevented) {
        return;
      }

      if (event.key.toLowerCase() !== "o") {
        return;
      }

      const hasModifier = isMacOS() ? event.metaKey : event.ctrlKey;
      if (!(hasModifier && event.shiftKey)) {
        return;
      }

      event.preventDefault();
      onOpenCreateDialog?.();
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [onOpenCreateDialog]);

  return (
    <ChatWorkspace
      selectedSessionId={selectedSessionId}
      messages={messages}
      onSubmit={handlePromptSubmit}
      status={status}
      isUploadingFiles={isUploadingFiles}
      onCreateSession={onOpenCreateDialog}
      onCancel={cancelStream}
      onApprovalResponse={respondToApproval}
      onQuestionResponse={respondToQuestion}
      sessionDescription={sessionDescription}
      contextUsage={contextUsage}
      maxContextSize={maxContextSize}
      tokenUsage={tokenUsage}
      currentStep={currentStep}
      currentSession={currentSession}
      isReplayingHistory={isReplayingHistory}
      isAwaitingFirstResponse={isAwaitingFirstResponse}
      onListSessionDirectory={onListSessionDirectory}
      onGetSessionFileUrl={onGetSessionFileUrl}
      onGetSessionFile={onGetSessionFile}
      onOpenSidebar={onOpenSidebar}
      onRenameSession={onRenameSession}
      onForkSessionLatest={onForkSessionLatest ? handleForkSessionLatest : undefined}
      onRegenerateTitle={generateTitle ? handleRegenerateTitle : undefined}
      slashCommands={slashCommands}
      planMode={planMode}
      onPlanModeChange={handlePlanModeChange}
      errorMessage={streamError?.message}
      onForkSession={onForkSession ? handleForkSession : undefined}
      hasMoreHistory={hasMoreHistory}
      isLoadingOlder={isLoadingOlder}
      onLoadOlderHistory={loadOlderHistory}
      lastPrependCountRef={lastPrependCountRef}
    />
  );
}
