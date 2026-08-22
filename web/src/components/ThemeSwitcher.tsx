import { useTranslation } from "react-i18next";
import { CheckIcon, PaletteIcon } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  COLOR_THEMES,
  COLOR_THEME_SWATCH,
  useColorTheme,
  type ColorTheme,
} from "@/hooks/use-color-theme";
import { cn } from "@/lib/utils";

export const COLOR_THEME_LABEL_KEY: Record<ColorTheme, string> = {
  graphite: "settings:themeGraphite",
  cinnabar: "settings:themeCinnabar",
  teal: "settings:themeTeal",
};

export function ThemeSwatch({ theme }: { theme: ColorTheme }) {
  return (
    <span
      aria-hidden
      className="size-3 shrink-0 rounded-full border border-border/60"
      style={{ backgroundColor: COLOR_THEME_SWATCH[theme] }}
    />
  );
}

/** Palette-icon dropdown button for switching the color theme. */
export function ThemeSwitcher() {
  const { t } = useTranslation();
  const { colorTheme, setColorTheme } = useColorTheme();

  return (
    <DropdownMenu>
      <Tooltip>
        <TooltipTrigger asChild>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              aria-label={t("settings:colorTheme")}
              className="inline-flex items-center cursor-pointer justify-center rounded-md p-2 text-muted-foreground transition-colors hover:bg-secondary/60 hover:text-foreground"
            >
              <PaletteIcon className="size-4" />
            </button>
          </DropdownMenuTrigger>
        </TooltipTrigger>
        <TooltipContent side="bottom">
          {t("settings:colorTheme")}
        </TooltipContent>
      </Tooltip>
      <DropdownMenuContent align="end" className="w-44">
        {COLOR_THEMES.map((theme) => (
          <DropdownMenuItem
            key={theme}
            onClick={() => setColorTheme(theme)}
            className="flex items-center gap-2"
          >
            <ThemeSwatch theme={theme} />
            <span className="flex-1">{t(COLOR_THEME_LABEL_KEY[theme])}</span>
            <CheckIcon
              className={cn(
                "size-3.5 text-primary",
                theme !== colorTheme && "invisible",
              )}
            />
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
