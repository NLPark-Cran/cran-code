import { useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { Input } from "@/components/ui/input";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Kbd, KbdGroup } from "@/components/ui/kbd";
import type { Session } from "@/lib/api/models";
import { shortenTitle } from "@/lib/utils";
import {
  ChevronsDownUpIcon,
  ChevronsUpDownIcon,
  GitForkIcon,
  MoreVerticalIcon,
  PanelLeftOpen,
  PanelRightClose,
  PanelRightOpen,
  SearchIcon,
  SparklesIcon,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { SessionInfoPopover } from "./session-info-popover";
import { SwarmPanel } from "./swarm-panel";
import { OpenInMenu } from "./open-in-menu";
import { isMacOS } from "@/hooks/utils";

type ChatWorkspaceHeaderProps = {
  currentStep: number;
  sessionDescription?: string;
  currentSession?: Session;
  selectedSessionId?: string;
  isFilesPanelOpen?: boolean;
  blocksExpanded: boolean;
  onToggleBlocks: () => void;
  onToggleFilesPanel?: () => void;
  onOpenSearch: () => void;
  onOpenSidebar?: () => void;
  onRenameSession?: (sessionId: string, newTitle: string) => Promise<boolean>;
  onForkSessionLatest?: () => Promise<void>;
  onRegenerateTitle?: () => Promise<void>;
};

export function ChatWorkspaceHeader({
  currentStep: _,
  sessionDescription,
  currentSession,
  selectedSessionId,
  isFilesPanelOpen = false,
  blocksExpanded,
  onToggleBlocks,
  onToggleFilesPanel,
  onOpenSearch,
  onOpenSidebar,
  onRenameSession,
  onForkSessionLatest,
  onRegenerateTitle,
}: ChatWorkspaceHeaderProps) {
  const { t } = useTranslation();
  const searchShortcutModifier = isMacOS() ? "Cmd" : "Ctrl";

  // Editing state
  const [isEditing, setIsEditing] = useState(false);
  const [editingTitle, setEditingTitle] = useState("");

  const handleDoubleClick = useCallback(() => {
    if (!(onRenameSession && selectedSessionId && sessionDescription)) return;
    setIsEditing(true);
    setEditingTitle(sessionDescription);
  }, [onRenameSession, selectedSessionId, sessionDescription]);

  const handleCancelEdit = useCallback(() => {
    setIsEditing(false);
    setEditingTitle("");
  }, []);

  const handleSaveEdit = useCallback(async () => {
    if (!(selectedSessionId && onRenameSession)) {
      handleCancelEdit();
      return;
    }

    const trimmedTitle = editingTitle.trim();
    if (!trimmedTitle) {
      handleCancelEdit();
      return;
    }

    const success = await onRenameSession(selectedSessionId, trimmedTitle);
    if (success) {
      handleCancelEdit();
    }
  }, [selectedSessionId, editingTitle, onRenameSession, handleCancelEdit]);

  return (
    <div className="flex min-w-0 flex-col gap-2 px-3 py-2 sm:flex-row sm:items-center sm:justify-between sm:px-5 sm:py-3 lg:pl-8">
      <div className="flex min-w-0 items-center gap-2">
        {onOpenSidebar ? (
          <button
            type="button"
            aria-label={t("chat:openSessionsSidebar")}
            className="inline-flex h-8 w-8 shrink-0 cursor-pointer items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-secondary/60 hover:text-foreground lg:hidden"
            onClick={onOpenSidebar}
          >
            <PanelLeftOpen className="size-4" />
          </button>
        ) : null}
        <div className="min-w-0 flex-1">
          {isEditing ? (
            <Input
              autoFocus
              value={editingTitle}
              onChange={(e) => setEditingTitle(e.target.value)}
              onBlur={handleSaveEdit}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  handleSaveEdit();
                }
                if (e.key === "Escape") {
                  e.preventDefault();
                  handleCancelEdit();
                }
              }}
              className="h-7 text-xs font-bold"
            />
          ) : sessionDescription ? (
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  className="truncate text-xs font-bold cursor-pointer hover:text-primary text-left bg-transparent border-none p-0"
                  onDoubleClick={handleDoubleClick}
                >
                  {shortenTitle(sessionDescription, 60)}
                </button>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="max-w-md">
                <div>{sessionDescription}</div>
                {onRenameSession && (
                  <div className="text-muted-foreground text-[10px] mt-1">
                    {t("chat:doubleClickRename")}
                  </div>
                )}
              </TooltipContent>
            </Tooltip>
          ) : null}
        </div>
      </div>
      <div className="flex items-center justify-end gap-2">
        {selectedSessionId && (
          <>
            {currentSession?.workDir ? (
              <div className="hidden lg:block">
                <OpenInMenu workDir={currentSession.workDir} />
              </div>
            ) : null}

            <SessionInfoPopover
              sessionId={selectedSessionId}
              session={currentSession}
            />

            <SwarmPanel />

            {onToggleFilesPanel ? (
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    aria-label={
                      isFilesPanelOpen
                        ? t("chat:hideWorkspaceFiles")
                        : t("chat:showWorkspaceFiles")
                    }
                    className="relative inline-flex items-center cursor-pointer justify-center rounded-md p-2 text-muted-foreground transition-colors hover:bg-secondary/60 hover:text-foreground"
                    onClick={onToggleFilesPanel}
                  >
                    {isFilesPanelOpen ? (
                      <PanelRightClose className="size-4" />
                    ) : (
                      <PanelRightOpen className="size-4" />
                    )}
                  </button>
                </TooltipTrigger>
                <TooltipContent side="bottom">
                  {isFilesPanelOpen
                    ? t("chat:hideWorkspaceFiles")
                    : t("chat:showWorkspaceFiles")}
                </TooltipContent>
              </Tooltip>
            ) : null}

            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  aria-label={t("chat:searchMessages")}
                  className="inline-flex items-center cursor-pointer justify-center rounded-md p-2 text-muted-foreground transition-colors hover:bg-secondary/60 hover:text-foreground"
                  onClick={onOpenSearch}
                >
                  <SearchIcon className="size-4" />
                </button>
              </TooltipTrigger>
              <TooltipContent className="flex items-center gap-2" side="bottom">
                <span>{t("chat:searchMessages")}</span>
                <KbdGroup>
                  <Kbd>{searchShortcutModifier}</Kbd>
                  <span className="text-muted-foreground">+</span>
                  <Kbd>F</Kbd>
                </KbdGroup>
              </TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  aria-label={
                    blocksExpanded ? t("chat:foldAllBlocks") : t("chat:unfoldAllBlocks")
                  }
                  className="inline-flex items-center cursor-pointer justify-center rounded-md p-2 text-muted-foreground transition-colors hover:bg-secondary/60 hover:text-foreground"
                  onClick={onToggleBlocks}
                >
                  {blocksExpanded ? (
                    <ChevronsDownUpIcon className="size-4" />
                  ) : (
                    <ChevronsUpDownIcon className="size-4" />
                  )}
                </button>
              </TooltipTrigger>
              <TooltipContent side="bottom">
                {blocksExpanded ? t("chat:foldAllBlocks") : t("chat:unfoldAllBlocks")}
              </TooltipContent>
            </Tooltip>

            {(onForkSessionLatest || onRegenerateTitle) && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button
                    type="button"
                    aria-label={t("sessions:sessionActions")}
                    className="inline-flex items-center cursor-pointer justify-center rounded-md p-2 text-muted-foreground transition-colors hover:bg-secondary/60 hover:text-foreground"
                  >
                    <MoreVerticalIcon className="size-4" />
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  {onRegenerateTitle && (
                    <DropdownMenuItem
                      onClick={() =>
                        onRegenerateTitle().catch((error: unknown) => {
                          console.error("[ChatHeader] regenerate title failed:", error);
                        })
                      }
                    >
                      <SparklesIcon className="mr-2 h-4 w-4" />
                      {t("sessions:regenerateTitle")}
                    </DropdownMenuItem>
                  )}
                  {onForkSessionLatest && (
                    <DropdownMenuItem
                      onClick={() =>
                        onForkSessionLatest().catch((error: unknown) => {
                          console.error("[ChatHeader] fork failed:", error);
                        })
                      }
                    >
                      <GitForkIcon className="mr-2 h-4 w-4" />
                      {t("sessions:fork")}
                    </DropdownMenuItem>
                  )}
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </>
        )}
      </div>
    </div>
  );
}
