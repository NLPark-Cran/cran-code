import { useMemo } from "react";
import { cn } from "@/lib/utils";

export type BarSegment = {
  key: string;
  label: string;
  value: number;
  colorClass: string;
};

export type DailyBar = {
  date: string;
  segments: BarSegment[];
};

type StackedBarChartProps = {
  bars: DailyBar[];
  title: string;
  className?: string;
};

const SVG_HEIGHT = 160;
/** Bottom padding inside the SVG reserved below the bars. */
const X_AXIS_RESERVE = 14;
const BAR_GAP_RATIO = 0.25;
/** Above this many bars, per-bar value labels are hidden to avoid overlap. */
const MAX_BARS_WITH_VALUE_LABELS = 14;
/** Maximum number of x-axis date labels shown at once. */
const MAX_X_LABELS = 8;

const compact = (n: number): string =>
  new Intl.NumberFormat("en-US", { notation: "compact" }).format(n);

/**
 * Lightweight stacked bar chart (SVG bars + HTML labels).
 * Labels are HTML (not SVG text) because the SVG uses
 * preserveAspectRatio="none", which would stretch text horizontally.
 */
export function StackedBarChart({ bars, title, className }: StackedBarChartProps) {
  const max = useMemo(
    () =>
      Math.max(
        1,
        ...bars.map((bar) => bar.segments.reduce((sum, s) => sum + s.value, 0)),
      ),
    [bars],
  );

  const enriched = useMemo(
    () =>
      bars.map((bar) => ({
        ...bar,
        total: bar.segments.reduce((sum, s) => sum + s.value, 0),
      })),
    [bars],
  );

  if (bars.length === 0) return null;

  const slotWidth = 100 / bars.length;
  const barWidth = slotWidth * (1 - BAR_GAP_RATIO);
  const showValueLabels = bars.length <= MAX_BARS_WITH_VALUE_LABELS;
  // Thin out x labels so they never overlap (≈8 labels for a 30-day view).
  const xLabelStep = Math.max(1, Math.ceil(bars.length / MAX_X_LABELS));

  return (
    <div className={cn("w-full", className)}>
      <div className="relative">
        <svg
          viewBox={`0 0 100 ${SVG_HEIGHT}`}
          preserveAspectRatio="none"
          className="h-40 w-full"
          role="img"
        >
          <title>{title}</title>
          {enriched.map((bar, i) => {
            let acc = 0;
            const x = i * slotWidth + (slotWidth - barWidth) / 2;
            return (
              <g key={bar.date}>
                {bar.segments.map((seg) => {
                  const h = (seg.value / max) * (SVG_HEIGHT - 24);
                  const y = SVG_HEIGHT - X_AXIS_RESERVE - acc - h;
                  acc += h;
                  return (
                    <rect
                      key={seg.key}
                      x={x}
                      y={y}
                      width={barWidth}
                      height={Math.max(0, h)}
                      className={seg.colorClass}
                      rx={0.4}
                    >
                      <title>{`${bar.date} · ${seg.label}: ${seg.value.toLocaleString()}`}</title>
                    </rect>
                  );
                })}
              </g>
            );
          })}
        </svg>
        {/* Per-bar value labels (HTML overlay; SVG_HEIGHT px == h-40) */}
        {showValueLabels
          ? enriched.map((bar, i) => {
              if (bar.total === 0) return null;
              const x = i * slotWidth + slotWidth / 2;
              // h of the whole stack in px == SVG units (height is unstretched)
              const stackH = (bar.total / max) * (SVG_HEIGHT - 24);
              return (
                <span
                  key={`label-${bar.date}`}
                  className="pointer-events-none absolute -translate-x-1/2 text-[10px] text-muted-foreground tabular-nums"
                  style={{
                    left: `${x}%`,
                    bottom: `${Math.min(SVG_HEIGHT - 12, X_AXIS_RESERVE + stackH + 4)}px`,
                  }}
                >
                  {compact(bar.total)}
                </span>
              );
            })
          : null}
      </div>
      {/* X-axis date labels (HTML so text is never stretched) */}
      <div className="relative h-4">
        {enriched.map((bar, i) =>
          i % xLabelStep !== 0 ? null : (
            <span
              key={`x-${bar.date}`}
              className="absolute -translate-x-1/2 text-[10px] text-muted-foreground tabular-nums"
              style={{ left: `${i * slotWidth + slotWidth / 2}%` }}
            >
              {bar.date.slice(5)}
            </span>
          ),
        )}
      </div>
    </div>
  );
}
