import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

type EmptyStateProps = {
  icon: LucideIcon;
  title: string;
  hint?: string;
  action?: ReactNode;
  className?: string;
};

/**
 * Unified empty/placeholder pattern: icon + title + optional hint + optional
 * action. Used across sessions sidebar, chat, files panel and team pages.
 */
export function EmptyState({
  icon: Icon,
  title,
  hint,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-1.5 py-8 text-center",
        className,
      )}
    >
      <Icon className="mb-1 size-6 text-muted-foreground/70" />
      <p className="text-sm font-medium text-foreground">{title}</p>
      {hint ? <p className="text-xs text-muted-foreground">{hint}</p> : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}
