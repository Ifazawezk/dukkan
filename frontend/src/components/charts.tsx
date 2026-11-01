// Chart building blocks for the reports page.
//
// Colours: the three payment methods use the first three slots of a
// colour-blind safe categorical palette (checked for deuteranopia,
// protanopia and tritanopia separation). Single series charts use slot one.
// Text always uses the ink colours, never the series colour.

import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DailySalesRow } from "../api/types";
import { useI18n } from "../i18n";
import { formatAmount, formatMoney } from "../lib/format";

export const SERIES = {
  cash: "#2a78d6",
  card: "#eb6834",
  wallet: "#1baf7a",
} as const;
const SINGLE = SERIES.cash;
const GRID = "#e7e5e4";
const INK_MUTED = "#78716c";
const INK = "#44403c";
const SURFACE = "#ffffff";

const METHODS = ["cash", "card", "wallet"] as const;

function compact(value: number, lang: string) {
  return new Intl.NumberFormat(lang === "ar" ? "ar-QA-u-nu-latn" : "en-QA", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

function shortDate(value: string, lang: string) {
  return new Intl.DateTimeFormat(lang === "ar" ? "ar-QA-u-nu-latn" : "en-QA", {
    day: "numeric",
    month: "short",
  }).format(new Date(`${value}T00:00:00`));
}

export function ChartLegend({ items }: { items: { label: string; color: string }[] }) {
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-stone-600">
      {items.map((item) => (
        <li key={item.label} className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-sm" style={{ background: item.color }} />
          {item.label}
        </li>
      ))}
    </ul>
  );
}

/** Stacked columns: one per day, split by how customers paid. */
export function DailySalesChart({ rows }: { rows: DailySalesRow[] }) {
  const { t, lang } = useI18n();
  return (
    <div dir="ltr" className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} stroke={GRID} />
          <XAxis
            dataKey="date"
            tickFormatter={(value: string) => shortDate(value, lang)}
            tick={{ fill: INK_MUTED, fontSize: 12 }}
            tickLine={false}
            axisLine={{ stroke: GRID }}
            minTickGap={16}
          />
          <YAxis
            tickFormatter={(value: number) => compact(value, lang)}
            tick={{ fill: INK_MUTED, fontSize: 12 }}
            tickLine={false}
            axisLine={false}
            width={44}
          />
          <Tooltip
            cursor={{ fill: "rgba(28, 25, 23, 0.05)" }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const row = payload[0].payload as DailySalesRow;
              return (
                <div className="min-w-44 rounded-lg bg-white px-3 py-2 text-xs shadow-lg ring-1 ring-stone-200">
                  <div className="mb-1 font-semibold text-stone-800">
                    {shortDate(row.date, lang)}
                  </div>
                  {[...METHODS].reverse().map((method) => (
                    <div key={method} className="flex items-center justify-between gap-4">
                      <span className="flex items-center gap-1.5 text-stone-600">
                        <span
                          className="size-2 rounded-sm"
                          style={{ background: SERIES[method] }}
                        />
                        {t(`pay.${method}`)}
                      </span>
                      <span className="num text-stone-800">{formatAmount(row[method], lang)}</span>
                    </div>
                  ))}
                  <div className="mt-1 flex justify-between gap-4 border-t border-stone-100 pt-1 font-semibold text-stone-900">
                    <span>{t("reports.total")}</span>
                    <span className="num">{formatMoney(row.sales_total, lang)}</span>
                  </div>
                  <div className="text-stone-500">
                    {t("reports.todayCount", { count: row.sales_count })}
                  </div>
                </div>
              );
            }}
          />
          {METHODS.map((method, i) => (
            <Bar
              key={method}
              dataKey={method}
              stackId="payments"
              fill={SERIES[method]}
              stroke={SURFACE}
              strokeWidth={2}
              maxBarSize={24}
              radius={i === METHODS.length - 1 ? [4, 4, 0, 0] : 0}
              isAnimationActive={false}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export interface BarDatum {
  label: string;
  value: number;
  /** Optional text shown after the value, such as a margin. */
  note?: string;
}

/** Horizontal bars with the value written at the end of each bar. */
export function HorizontalBars({
  data,
  format,
}: {
  data: BarDatum[];
  format: (value: number) => string;
}) {
  const height = data.length * 34 + 12;
  return (
    <div dir="ltr" style={{ height }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart layout="vertical" data={data} margin={{ top: 4, right: 96, bottom: 4, left: 0 }}>
          <XAxis type="number" hide domain={[0, "dataMax"]} />
          <YAxis
            type="category"
            dataKey="label"
            width={170}
            tick={{ fill: INK, fontSize: 12 }}
            tickLine={false}
            axisLine={{ stroke: GRID }}
          />
          <Tooltip
            cursor={{ fill: "rgba(28, 25, 23, 0.05)" }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const datum = payload[0].payload as BarDatum;
              return (
                <div className="rounded-lg bg-white px-3 py-2 text-xs shadow-lg ring-1 ring-stone-200">
                  <div className="font-semibold text-stone-800">{datum.label}</div>
                  <div className="num text-stone-700">
                    {format(datum.value)}
                    {datum.note && <span className="ms-2 text-stone-500">{datum.note}</span>}
                  </div>
                </div>
              );
            }}
          />
          <Bar
            dataKey="value"
            fill={SINGLE}
            maxBarSize={18}
            radius={[0, 4, 4, 0]}
            isAnimationActive={false}
          >
            <LabelList
              dataKey="value"
              position="right"
              content={(props) => {
                const { x, y, width, height, index } = props as {
                  x: number;
                  y: number;
                  width: number;
                  height: number;
                  index: number;
                };
                const datum = data[index];
                return (
                  <text
                    x={x + width + 6}
                    y={y + height / 2}
                    dominantBaseline="central"
                    fontSize={12}
                    fill={INK}
                  >
                    {format(datum.value)}
                    {datum.note && <tspan fill={INK_MUTED}> {datum.note}</tspan>}
                  </text>
                );
              }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
