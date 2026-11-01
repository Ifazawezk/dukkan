import { useQuery } from "@tanstack/react-query";
import { Download } from "lucide-react";
import { useState } from "react";
import type { ReactNode } from "react";
import { api, downloadFile } from "../api/client";
import type {
  CashierRow,
  CategoryProfitRow,
  DailySalesRow,
  ProductSalesRow,
  ReportSummary,
  SlowMoverRow,
  StockValuationRow,
} from "../api/types";
import { useShop } from "../auth/ShopContext";
import { ChartLegend, DailySalesChart, HorizontalBars, SERIES } from "../components/charts";
import { Button, Card, EmptyState, PageHeader, Spinner, cx, td, th, thEnd } from "../components/ui";
import { useI18n } from "../i18n";
import { formatAmount, formatDate, formatMoney, isoDate } from "../lib/format";

type Query = Record<string, string | number | undefined>;

function useReport<T>(path: string, query: Query) {
  return useQuery({
    queryKey: ["report", path, query],
    queryFn: () => api<T>(`/reports/${path}`, { query }),
  });
}

function CsvButton({ path, query }: { path: string; query: Query }) {
  const { t } = useI18n();
  return (
    <Button
      size="sm"
      variant="ghost"
      icon={<Download className="size-4" />}
      onClick={() => void downloadFile(`/reports/${path}`, { ...query, format: "csv" })}
    >
      {t("reports.csv")}
    </Button>
  );
}

function StatTile({ label, value, detail }: { label: string; value: string; detail?: ReactNode }) {
  return (
    <div className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-stone-200">
      <div className="text-xs font-medium uppercase tracking-wide text-stone-500">{label}</div>
      <div className="num mt-1 text-2xl font-semibold text-stone-900">{value}</div>
      {detail && <div className="mt-0.5 text-xs text-stone-500">{detail}</div>}
    </div>
  );
}

const RANGES = [7, 30, 90] as const;

export function ReportsPage() {
  const { t, lang, pick } = useI18n();
  const { branches } = useShop();
  const [days, setDays] = useState<(typeof RANGES)[number]>(30);
  const [branch, setBranch] = useState("");
  const [productOrder, setProductOrder] = useState<"revenue" | "quantity">("revenue");
  const [dailyView, setDailyView] = useState<"chart" | "table">("chart");

  const dateTo = isoDate(new Date());
  const dateFrom = isoDate(new Date(Date.now() - (days - 1) * 86_400_000));
  const period: Query = { date_from: dateFrom, date_to: dateTo, branch_id: branch || undefined };
  const branchOnly: Query = { branch_id: branch || undefined };

  const summary = useReport<ReportSummary>("summary", period);
  const daily = useReport<DailySalesRow[]>("daily-sales", period);
  const productQuery = { ...period, by: productOrder, limit: 8 };
  const products = useReport<ProductSalesRow[]>("top-products", productQuery);
  const categories = useReport<CategoryProfitRow[]>("profit-by-category", period);
  const cashiers = useReport<CashierRow[]>("cashier-performance", period);
  const slow = useReport<SlowMoverRow[]>("slow-movers", branchOnly);
  const valuation = useReport<StockValuationRow[]>("stock-valuation", branchOnly);

  const money = (value: number) => formatAmount(value, lang);
  const s = summary.data;

  return (
    <div className="space-y-5">
      <PageHeader
        title={t("reports.title")}
        subtitle={t("reports.subtitle", {
          from: formatDate(dateFrom, lang),
          to: formatDate(dateTo, lang),
        })}
        actions={
          <>
            <select
              className="h-10 rounded-lg border border-stone-300 bg-white px-3 text-sm"
              value={branch}
              onChange={(e) => setBranch(e.target.value)}
              aria-label={t("nav.branch")}
            >
              <option value="">{t("reports.allBranches")}</option>
              {branches.map((b) => (
                <option key={b.id} value={b.id}>
                  {pick(b.name, b.name_ar)}
                </option>
              ))}
            </select>
            <div className="flex rounded-lg bg-stone-200/70 p-1 text-sm font-medium">
              {RANGES.map((range) => (
                <button
                  key={range}
                  onClick={() => setDays(range)}
                  className={cx(
                    "rounded-md px-3 py-1",
                    days === range ? "bg-white shadow-sm" : "text-stone-600",
                  )}
                >
                  {t(`reports.last${range}`)}
                </button>
              ))}
            </div>
          </>
        }
      />

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <StatTile
          label={t("reports.netSales")}
          value={s ? formatMoney(s.net_sales, lang) : "..."}
          detail={s && s.refunds > 0 && t("reports.refunds", { amount: money(s.refunds) })}
        />
        <StatTile
          label={t("reports.salesCount")}
          value={s ? String(s.sales_count) : "..."}
          detail={s && `${t("reports.avgBasket")} ${money(s.average_basket)}`}
        />
        <StatTile
          label={t("reports.grossProfit")}
          value={s ? formatMoney(s.gross_profit, lang) : "..."}
          detail={s && t("reports.margin", { percent: s.margin_percent.toFixed(1) })}
        />
        <StatTile
          label={t("reports.today")}
          value={s ? formatMoney(s.today_sales_total, lang) : "..."}
          detail={s && t("reports.todayCount", { count: s.today_sales_count })}
        />
        <StatTile
          label={t("reports.lowStock")}
          value={s ? String(s.low_stock_items) : "..."}
          detail={s && t("reports.stockValue", { amount: money(s.stock_value) })}
        />
      </div>

      <Card
        title={
          <span>
            {t("reports.daily")}
            <span className="ms-2 font-normal text-stone-500">{t("reports.dailyHint")}</span>
          </span>
        }
        actions={
          <div className="flex items-center gap-1">
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setDailyView(dailyView === "chart" ? "table" : "chart")}
            >
              {t(dailyView === "chart" ? "reports.showTable" : "reports.showChart")}
            </Button>
            <CsvButton path="daily-sales" query={period} />
          </div>
        }
      >
        <div className="p-4">
          {daily.isLoading ? (
            <Spinner />
          ) : dailyView === "chart" ? (
            <div className="space-y-3">
              <ChartLegend
                items={(["cash", "card", "wallet"] as const).map((m) => ({
                  label: t(`pay.${m}`),
                  color: SERIES[m],
                }))}
              />
              <DailySalesChart rows={daily.data ?? []} />
            </div>
          ) : (
            <div className="max-h-80 overflow-auto">
              <table className="min-w-full divide-y divide-stone-100">
                <thead className="sticky top-0 bg-stone-50">
                  <tr>
                    <th className={th}>{t("reports.date")}</th>
                    <th className={thEnd}>{t("reports.salesCount")}</th>
                    <th className={thEnd}>{t("pay.cash")}</th>
                    <th className={thEnd}>{t("pay.card")}</th>
                    <th className={thEnd}>{t("pay.wallet")}</th>
                    <th className={thEnd}>{t("reports.refunded")}</th>
                    <th className={thEnd}>{t("reports.netSales")}</th>
                    <th className={thEnd}>{t("reports.profit")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-100">
                  {[...(daily.data ?? [])].reverse().map((row) => (
                    <tr key={row.date}>
                      <td className={td}>{formatDate(row.date, lang)}</td>
                      <td className={`${td} num text-end`}>{row.sales_count}</td>
                      <td className={`${td} num text-end`}>{money(row.cash)}</td>
                      <td className={`${td} num text-end`}>{money(row.card)}</td>
                      <td className={`${td} num text-end`}>{money(row.wallet)}</td>
                      <td className={`${td} num text-end`}>{money(row.refunds)}</td>
                      <td className={`${td} num text-end font-medium`}>{money(row.net_sales)}</td>
                      <td className={`${td} num text-end`}>{money(row.gross_profit)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </Card>

      <div className="grid gap-5 xl:grid-cols-2">
        <Card
          title={t("reports.topProducts")}
          actions={
            <div className="flex items-center gap-1">
              <div className="flex rounded-md bg-stone-100 p-0.5 text-xs font-medium">
                {(["revenue", "quantity"] as const).map((order) => (
                  <button
                    key={order}
                    onClick={() => setProductOrder(order)}
                    className={cx(
                      "rounded px-2 py-1",
                      productOrder === order ? "bg-white shadow-sm" : "text-stone-600",
                    )}
                  >
                    {t(order === "revenue" ? "reports.byRevenue" : "reports.byQuantity")}
                  </button>
                ))}
              </div>
              <CsvButton path="top-products" query={productQuery} />
            </div>
          }
        >
          <div className="p-4">
            {products.isLoading ? (
              <Spinner />
            ) : products.data?.length === 0 ? (
              <EmptyState>{t("reports.noData")}</EmptyState>
            ) : (
              <HorizontalBars
                data={(products.data ?? []).map((row) => ({
                  label: pick(row.name, row.name_ar),
                  value: productOrder === "revenue" ? row.revenue : row.units_sold,
                }))}
                format={(value) =>
                  productOrder === "revenue" ? money(value) : `${value} ${t("reports.units")}`
                }
              />
            )}
          </div>
        </Card>

        <Card
          title={t("reports.categoryProfit")}
          actions={<CsvButton path="profit-by-category" query={period} />}
        >
          <div className="p-4">
            {categories.isLoading ? (
              <Spinner />
            ) : categories.data?.length === 0 ? (
              <EmptyState>{t("reports.noData")}</EmptyState>
            ) : (
              <HorizontalBars
                data={(categories.data ?? []).map((row) => ({
                  label: pick(row.category, row.category_ar),
                  value: row.profit,
                  note: `${row.margin_percent.toFixed(1)}%`,
                }))}
                format={money}
              />
            )}
          </div>
        </Card>
      </div>

      <Card
        title={t("reports.cashiers")}
        actions={<CsvButton path="cashier-performance" query={period} />}
      >
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-stone-100">
            <thead className="bg-stone-50">
              <tr>
                <th className={th}>{t("sales.cashier")}</th>
                <th className={thEnd}>{t("reports.salesCount")}</th>
                <th className={thEnd}>{t("reports.units")}</th>
                <th className={thEnd}>{t("reports.total")}</th>
                <th className={thEnd}>{t("reports.avgBasket")}</th>
                <th className={thEnd}>{t("reports.discounts")}</th>
                <th className={thEnd}>{t("reports.refunded")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {cashiers.data?.map((row) => (
                <tr key={row.cashier_id}>
                  <td className={`${td} font-medium`}>{row.cashier_name}</td>
                  <td className={`${td} num text-end`}>{row.sales_count}</td>
                  <td className={`${td} num text-end`}>{row.items_sold}</td>
                  <td className={`${td} num text-end font-medium`}>{money(row.sales_total)}</td>
                  <td className={`${td} num text-end`}>{money(row.average_basket)}</td>
                  <td className={`${td} num text-end`}>{money(row.discounts_given)}</td>
                  <td className={`${td} num text-end`}>{money(row.refunded)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <div className="grid gap-5 xl:grid-cols-2">
        <Card
          title={
            <span>
              {t("reports.slowMovers")}
              <span className="ms-2 font-normal text-stone-500">{t("reports.slowHint")}</span>
            </span>
          }
          actions={<CsvButton path="slow-movers" query={branchOnly} />}
        >
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-stone-100">
              <thead className="bg-stone-50">
                <tr>
                  <th className={th}>{t("products.product")}</th>
                  <th className={thEnd}>{t("inventory.onHand")}</th>
                  <th className={th}>{t("reports.lastSold")}</th>
                  <th className={thEnd}>{t("reports.costValue")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {slow.data?.map((row) => (
                  <tr key={row.product_id}>
                    <td className={td}>
                      <div className="font-medium">{pick(row.name, row.name_ar)}</div>
                      <div className="text-xs text-stone-500">{row.sku}</div>
                    </td>
                    <td className={`${td} num text-end`}>{row.on_hand}</td>
                    <td className={`${td} text-stone-600`}>
                      {row.days_since_last_sale === null
                        ? t("reports.never")
                        : t("reports.daysAgo", { days: row.days_since_last_sale })}
                    </td>
                    <td className={`${td} num text-end`}>{money(row.stock_value)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        <Card
          title={t("reports.valuation")}
          actions={<CsvButton path="stock-valuation" query={branchOnly} />}
        >
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-stone-100">
              <thead className="bg-stone-50">
                <tr>
                  <th className={th}>{t("products.category")}</th>
                  <th className={thEnd}>{t("reports.units")}</th>
                  <th className={thEnd}>{t("reports.costValue")}</th>
                  <th className={thEnd}>{t("reports.retailValue")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {valuation.data?.map((row) => (
                  <tr key={row.category_id ?? "none"}>
                    <td className={`${td} font-medium`}>{pick(row.category, row.category_ar)}</td>
                    <td className={`${td} num text-end`}>{row.units}</td>
                    <td className={`${td} num text-end`}>{money(row.cost_value)}</td>
                    <td className={`${td} num text-end`}>{money(row.retail_value)}</td>
                  </tr>
                ))}
              </tbody>
              {valuation.data && valuation.data.length > 0 && (
                <tfoot className="bg-stone-50">
                  <tr>
                    <td className={`${td} font-semibold`}>{t("reports.total")}</td>
                    <td className={`${td} num text-end font-semibold`}>
                      {valuation.data.reduce((sum, r) => sum + r.units, 0)}
                    </td>
                    <td className={`${td} num text-end font-semibold`}>
                      {money(valuation.data.reduce((sum, r) => sum + r.cost_value, 0))}
                    </td>
                    <td className={`${td} num text-end font-semibold`}>
                      {money(valuation.data.reduce((sum, r) => sum + r.retail_value, 0))}
                    </td>
                  </tr>
                </tfoot>
              )}
            </table>
          </div>
        </Card>
      </div>
    </div>
  );
}
