import { useTranslation } from "react-i18next";
import { cranCliVersion } from "@/lib/version";
import { cn } from "@/lib/utils";

type CranCliBrandProps = {
  className?: string;
  size?: "sm" | "md";
  showVersion?: boolean;
};

export function CranCliBrand({
  className,
  size = "md",
  showVersion = true,
}: CranCliBrandProps) {
  const { t } = useTranslation();
  const textSizeClass = size === "sm" ? "text-base" : "text-lg";
  const versionPadding = size === "sm" ? "text-xs" : "text-sm";
  const logoSize = size === "sm" ? "size-6" : "size-7";
  const logoPx = size === "sm" ? 24 : 28;

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <a
        href="https://crys.tt2.li"
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-2 hover:opacity-80 transition-opacity"
      >
        <img
          src="/logo.png"
          alt="Cran"
          width={logoPx}
          height={logoPx}
          className={logoSize}
        />
        <span className={cn(textSizeClass, "font-semibold text-foreground")}>
          {t("common:brandName")}
        </span>
      </a>
      {showVersion && (
        <span
          className={cn("text-muted-foreground font-medium", versionPadding)}
        >
          v{cranCliVersion}
        </span>
      )}
    </div>
  );
}
