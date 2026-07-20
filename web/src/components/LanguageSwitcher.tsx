import { useTranslation } from "react-i18next";
import { type Language, setLanguage } from "@/i18n";
import { cn } from "@/lib/utils";

const OPTIONS: { value: Language; label: string }[] = [
  { value: "zh", label: "中文" },
  { value: "en", label: "English" },
];

/** Compact segmented control「中文 | English」with instant switching. */
export default function LanguageSwitcher({ className }: { className?: string }) {
  const { i18n } = useTranslation();
  const current: Language = i18n.resolvedLanguage?.startsWith("zh") ? "zh" : "en";

  return (
    <div
      className={cn(
        "inline-flex items-center rounded-md border bg-muted/40 p-0.5",
        className,
      )}
    >
      {OPTIONS.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => setLanguage(opt.value)}
          className={cn(
            "rounded-sm px-2.5 py-1 text-xs transition-colors",
            current === opt.value
              ? "bg-background text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground",
          )}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
