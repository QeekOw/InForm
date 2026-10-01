"use client";

// One metric over time, or the current value when there isn't a trend yet.
//
// Recharts, pinned at 3.10.1 (its peer range covers React 19). Declarative
// components, which is how the rest of this codebase is written.

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export type TrendPoint = {
  /** Milliseconds, so points sit on a real time axis rather than evenly spaced. */
  t: number;
  /** Short date label for the axis. */
  label: string;
  value: number;
  /** Whether this Scan included a value a person typed. */
  corrected: boolean;
};

const ACCENT = "#117d69";

function formatValue(value: number, unit: string, decimals: number): string {
  return `${value.toFixed(decimals)}${unit ? ` ${unit}` : ""}`;
}

/** The change between the first and last point, phrased as a direction.
 *
 * Deliberately not judged as good or bad: whether losing weight or gaining
 * muscle is progress depends on the person's goal, and this component doesn't
 * know it. It states the movement and leaves the meaning alone. */
function describeChange(points: TrendPoint[], unit: string, decimals: number): string | null {
  if (points.length < 2) return null;
  const delta = points[points.length - 1].value - points[0].value;
  if (Math.abs(delta) < Math.pow(10, -decimals) / 2) return "No change so far";
  const direction = delta > 0 ? "Up" : "Down";
  const days = Math.round((points[points.length - 1].t - points[0].t) / 86_400_000);
  const span =
    days >= 60 ? `the past ${Math.round(days / 30)} months` : days >= 14 ? `the past ${Math.round(days / 7)} weeks` : "your first scan";
  return `${direction} ${formatValue(Math.abs(delta), unit, decimals)} ${span === "your first scan" ? "since" : "in"} ${span}`;
}

export default function TrendChart({
  title,
  unit,
  points,
  decimals = 1,
}: {
  title: string;
  unit: string;
  points: TrendPoint[];
  decimals?: number;
}) {
  if (points.length === 0) return null;

  const latest = points[points.length - 1];
  const change = describeChange(points, unit, decimals);

  // One point is not a trend. Drawing a single dot on an axis would dress up
  // "we have measured you once" as a chart, so it shows the number instead
  // (Requirement 6.3).
  if (points.length === 1) {
    return (
      <div className="rounded-[15px] bg-gradient-to-b from-[#fcfcfc] to-[#f3f3f3] p-[20px] text-black shadow-[0_4px_16px_rgba(0,0,0,0.18)]">
        <div className="flex items-baseline justify-between">
          <p className="text-[12px] font-bold">{title}</p>
          {latest.corrected && (
            <span className="rounded bg-sky-100 px-1.5 py-0.5 text-[8px] font-bold text-sky-800">
              Edited
            </span>
          )}
        </div>
        <p className="mt-1 text-[26px] font-bold text-[#117d69]">
          {latest.value.toFixed(decimals)}
          {unit && <span className="ml-1 text-[12px] font-medium opacity-60">{unit}</span>}
        </p>
        <p className="mt-0.5 text-[10px] opacity-60">
          As of {latest.label}. A second scan will start a trend line here.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-[15px] bg-gradient-to-b from-[#fcfcfc] to-[#f3f3f3] p-[20px] text-black shadow-[0_4px_16px_rgba(0,0,0,0.18)]">
      <div className="flex items-baseline justify-between gap-2">
        <p className="text-[12px] font-bold">{title}</p>
        <p className="text-[24px] font-bold leading-none text-[#117d69]">
          {latest.value.toFixed(decimals)}
          {unit && <span className="ml-0.5 text-[10px] font-medium text-black/60">{unit}</span>}
        </p>
      </div>
      {change && <p className="mt-0.5 text-[10px] opacity-60">{change}</p>}

      <div className="mt-2 h-[120px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={points} margin={{ top: 4, right: 8, bottom: 0, left: -18 }}>
            <CartesianGrid stroke="#00000010" vertical={false} />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 9, fill: "#71717a" }}
              tickLine={false}
              axisLine={{ stroke: "#00000015" }}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fontSize: 9, fill: "#71717a" }}
              tickLine={false}
              axisLine={false}
              domain={["auto", "auto"]}
              width={44}
            />
            <Tooltip
              // Recharts types the formatter's value as possibly absent, so this
              // narrows rather than assuming a number.
              formatter={(value) => {
                const numeric = typeof value === "number" ? value : Number(value);
                return [
                  Number.isFinite(numeric) ? formatValue(numeric, unit, decimals) : "—",
                  title,
                ];
              }}
              contentStyle={{
                fontSize: 11,
                borderRadius: 8,
                border: "1px solid #00000015",
              }}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke={ACCENT}
              strokeWidth={2}
              dot={{ r: 3, fill: ACCENT }}
              activeDot={{ r: 5 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
