import { ImageOffIcon } from "lucide-react";
import { useTranslation } from "react-i18next";

type CompactedMediaChipProps = {
  filename?: string;
  count?: number;
};

/**
 * Placeholder chip for media tombstoned by context compaction
 * (`[image removed by context compaction]` / `compacted:` URL prefix).
 */
export function CompactedMediaChip({ filename, count }: CompactedMediaChipProps) {
  const { t } = useTranslation();
  return (
    <span className="inline-flex max-w-full items-center gap-1.5 rounded-md border border-dashed border-border-subtle bg-surface-muted/60 px-2 py-1 text-[11px] text-muted-foreground">
      <ImageOffIcon className="size-3 shrink-0" />
      {filename && <span className="max-w-[200px] truncate">{filename}</span>}
      <span className="shrink-0 rounded bg-muted px-1 py-px text-[10px] font-medium uppercase">
        {count && count > 1
          ? t("chat:compactedMediaCount", { count })
          : t("chat:compactedMedia")}
      </span>
    </span>
  );
}
