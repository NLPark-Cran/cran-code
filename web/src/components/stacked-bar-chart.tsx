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
const BAR_GAP_RATIO = 0.25;

const compact = (n: number): string =>
  new Intl.NumberFormat("en-US", { notation: "compact" }).format(n);

/** Lightweight stacked bar chart (SVG, no chart dependency). */
export function StackedBarChart({ bars, title, className }: StackedBarChartProps) {
  const max = useMemo(
    () =>
      Math.max(
        1,
        ...bars.map((bar) => bar.segments.reduce((sum, s) => sum + s.value, 0)),
      ),
    [bars],
  );

  if (bars.length === 0) return null;

  const slotWidth = 100 / bars.length;
  const barWidth = slotWidth * (1 - BAR_GAP_RATIO);

  return (
    <div className={cn("w-full", className)}>
      <svg
        viewBox={`0 0 100 ${SVG_HEIGHT}`}
        preserveAspectRatio="none"
        className="h-40 w-full"
        role="img"
      >
        <title>{title}</title>
        {bars.map((bar, i) => {
          const total = bar.segments.reduce((sum, s) => sum + s.value, 0);
          let acc = 0;
          const x = i * slotWidth + (slotWidth - barWidth) / 2;
          return (
            <g key={bar.date}>
              {bar.segments.map((seg) => {
                const h = (seg.value / max) * (SVG_HEIGHT - 24);
                const y = SVG_HEIGHT - 14 - acc - h;
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
              {total === 0 ? null : (
                <text
                  x={x + barWidth / 2}
                  y={SVG_HEIGHT - 14 - acc - 3}
                  textAnchor="middle"
                  className="fill-muted-foreground"
                  fontSize={4}
                >
                  {compact(total)}
                </text>
              )}
              {(bars.length <= 10 || i % Math.ceil(bars.length / 10) === 0) && (
                <text
                  x={x + barWidth / 2}
                  y={SVG_HEIGHT - 3}
                  textAnchor="middle"
                  className="fill-muted-foreground"
                  fontSize={4}
                >
                  {bar.date.slice(5)}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
