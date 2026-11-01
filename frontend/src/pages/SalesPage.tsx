import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Printer, Undo2 } from "lucide-react";
import { useState } from "react";
import { api } from "../api/client";
import type { Page, PaymentMethod, Sale, SaleReturn, SaleStatus, SaleSummary } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { useShop } from "../auth/ShopContext";
import { Pager } from "../components/Pager";
import { Receipt } from "../components/Receipt";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorText,
  Input,
  Modal,
  PageHeader,
  Select,
  Spinner,
  td,
  th,
  thEnd,
} from "../components/ui";
import { useI18n } from "../i18n";
import { formatAmount, formatDateTime, formatMoney, isoDate } from "../lib/format";
import { useDebounced } from "../lib/hooks";

const STATUS_TONES: Record<SaleStatus, "green" | "amber" | "red"> = {
  completed: "green",
  partially_refunded: "amber",
  refunded: "red",
};

export function SalesPage() {
  const { t, lang } = useI18n();
  const { branchId, settings } = useShop();
  const today = isoDate(new Date());
  const [dateFrom, setDateFrom] = useState(isoDate(new Date(Date.now() - 6 * 86_400_000)));
  const [dateTo, setDateTo] = useState(today);
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [openId, setOpenId] = useState<number | null>(null);
  const q = useDebounced(search);

  const sales = useQuery({
    queryKey: ["sales", { dateFrom, dateTo, q, offset, branchId }],
    queryFn: () =>
      api<Page<SaleSummary>>("/sales", {
        query: { date_from: dateFrom, date_to: dateTo, q, branch_id: branchId, limit: 25, offset },
      }),
    placeholderData: keepPreviousData,
  });

  return (
    <div>
      <PageHeader title={t("sales.title")} />
      <Card>
        <div className="flex flex-wrap items-end gap-3 border-b border-stone-100 p-4">
          <Input
            label={t("sales.from")}
            type="date"
            value={dateFrom}
            max={dateTo}
            onChange={(e) => {
              setDateFrom(e.target.value);
              setOffset(0);
            }}
          />
          <Input
            label={t("sales.to")}
            type="date"
            value={dateTo}
            min={dateFrom}
            onChange={(e) => {
              setDateTo(e.target.value);
              setOffset(0);
            }}
          />
          <Input
            label={t("sales.receiptSearch")}
            value={search}
            placeholder="SAD-000123"
            onChange={(e) => {
              setSearch(e.target.value);
              setOffset(0);
            }}
          />
        </div>
        {sales.isLoading ? (
          <Spinner />
        ) : sales.data?.items.length === 0 ? (
          <EmptyState>{t("sales.empty")}</EmptyState>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-stone-100">
              <thead className="bg-stone-50">
                <tr>
                  <th className={th}>{t("receipt.no")}</th>
                  <th className={th}>{t("sales.time")}</th>
                  <th className={th}>{t("sales.cashier")}</th>
                  <th className={thEnd}>{t("sales.items")}</th>
                  <th className={thEnd}>{t("sales.total")}</th>
                  <th className={th}>{t("sales.status")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {sales.data?.items.map((sale) => (
                  <tr
                    key={sale.id}
                    className="cursor-pointer hover:bg-stone-50"
                    onClick={() => setOpenId(sale.id)}
                  >
                    <td className={`${td} font-medium`}>{sale.receipt_no}</td>
                    <td className={`${td} text-stone-600`}>
                      {formatDateTime(sale.created_at, lang, settings?.timezone)}
                    </td>
                    <td className={td}>{sale.cashier_name}</td>
                    <td className={`${td} num text-end`}>{sale.item_count}</td>
                    <td className={`${td} num text-end font-medium`}>
                      {formatAmount(sale.total, lang)}
                    </td>
                    <td className={td}>
                      <Badge tone={STATUS_TONES[sale.status]}>{t(`status.${sale.status}`)}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {sales.data && (
          <Pager offset={offset} limit={25} total={sales.data.total} onChange={setOffset} />
        )}
      </Card>
      {openId !== null && <SaleDialog id={openId} onClose={() => setOpenId(null)} />}
    </div>
  );
}

function SaleDialog({ id, onClose }: { id: number; onClose: () => void }) {
  const { t, lang } = useI18n();
  const { hasRole } = useAuth();
  const { settings } = useShop();
  const [returning, setReturning] = useState(false);
  const sale = useQuery({ queryKey: ["sale", id], queryFn: () => api<Sale>(`/sales/${id}`) });
  const data = sale.data;
  const canReturn =
    hasRole("owner", "manager") &&
    data !== undefined &&
    data.items.some((i) => i.quantity > i.quantity_returned);

  if (returning && data) {
    return <ReturnDialog sale={data} onClose={() => setReturning(false)} />;
  }

  return (
    <Modal
      open
      title={data?.receipt_no ?? t("common.loading")}
      onClose={onClose}
      footer={
        <>
          {canReturn && (
            <Button
              variant="secondary"
              icon={<Undo2 className="size-4" />}
              onClick={() => setReturning(true)}
            >
              {t("sales.return")}
            </Button>
          )}
          <Button
            icon={<Printer className="size-4" />}
            onClick={() => window.print()}
            disabled={!data}
          >
            {t("receipt.print")}
          </Button>
        </>
      }
    >
      {!data ? (
        <Spinner />
      ) : (
        <div className="space-y-4">
          <div className="flex justify-center">
            <Receipt sale={data} settings={settings} />
          </div>
          {data.returns.length > 0 && (
            <div>
              <h3 className="mb-2 text-sm font-semibold">{t("sales.returns")}</h3>
              <ul className="divide-y divide-stone-100 rounded-lg text-sm ring-1 ring-stone-200">
                {data.returns.map((r: SaleReturn) => (
                  <li key={r.id} className="px-3 py-2">
                    <div className="flex justify-between">
                      <span className="font-medium">{r.return_no}</span>
                      <span className="num">-{formatMoney(r.refund_total, lang)}</span>
                    </div>
                    <div className="text-xs text-stone-500">
                      {formatDateTime(r.created_at, lang, settings?.timezone)} - {r.user_name}
                      {r.reason && ` - ${r.reason}`}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </Modal>
  );
}

function ReturnDialog({ sale, onClose }: { sale: Sale; onClose: () => void }) {
  const { t, lang, pick } = useI18n();
  const queryClient = useQueryClient();
  const [quantities, setQuantities] = useState<Record<number, number>>({});
  const [restock, setRestock] = useState<Record<number, boolean>>({});
  const [reason, setReason] = useState("");
  const [method, setMethod] = useState<PaymentMethod>(sale.payments[0]?.method ?? "cash");

  const lines = sale.items
    .map((item) => ({ item, quantity: quantities[item.id] ?? 0 }))
    .filter((line) => line.quantity > 0);
  // Estimate only; the server works out the exact refund.
  const estimate = lines.reduce(
    (sum, { item, quantity }) => sum + (item.line_total / item.quantity) * quantity,
    0,
  );

  const submit = useMutation({
    mutationFn: () =>
      api<SaleReturn>(`/sales/${sale.id}/returns`, {
        body: {
          items: lines.map(({ item, quantity }) => ({
            sale_item_id: item.id,
            quantity,
            restock: restock[item.id] ?? true,
          })),
          reason,
          refund_method: method,
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sale", sale.id] });
      queryClient.invalidateQueries({ queryKey: ["sales"] });
      queryClient.invalidateQueries({ queryKey: ["stock"] });
      onClose();
    },
  });

  return (
    <Modal
      open
      wide
      title={t("returns.title", { receipt: sale.receipt_no })}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button
            variant="danger"
            disabled={lines.length === 0 || submit.isPending}
            onClick={() => submit.mutate()}
          >
            {t("returns.submit")} {formatMoney(estimate, lang)}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <table className="min-w-full divide-y divide-stone-100">
          <thead>
            <tr>
              <th className={th}>{t("products.product")}</th>
              <th className={thEnd}>{t("returns.sold")}</th>
              <th className={thEnd}>{t("returns.quantity")}</th>
              <th className={th}>{t("returns.restock")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-100">
            {sale.items.map((item) => {
              const left = item.quantity - item.quantity_returned;
              return (
                <tr key={item.id}>
                  <td className={td}>
                    <div className="font-medium">
                      {pick(item.product_name, item.product_name_ar)}
                    </div>
                    <div className="num text-xs text-stone-500">
                      {formatAmount(item.line_total, lang)}
                    </div>
                  </td>
                  <td className={`${td} num text-end`}>
                    {item.quantity}
                    {item.quantity_returned > 0 && (
                      <span className="text-stone-400"> (-{item.quantity_returned})</span>
                    )}
                  </td>
                  <td className={`${td} text-end`}>
                    <input
                      type="number"
                      min="0"
                      max={left}
                      disabled={left === 0}
                      className="num h-8 w-20 rounded-md border border-stone-300 px-2 text-end disabled:bg-stone-100"
                      value={quantities[item.id] ?? 0}
                      onChange={(e) =>
                        setQuantities({
                          ...quantities,
                          [item.id]: Math.min(Math.max(Number(e.target.value), 0), left),
                        })
                      }
                    />
                  </td>
                  <td className={td}>
                    <input
                      type="checkbox"
                      className="size-4 accent-brand-700"
                      checked={restock[item.id] ?? true}
                      onChange={(e) => setRestock({ ...restock, [item.id]: e.target.checked })}
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label={t("returns.reason")}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
          <Select
            label={t("returns.method")}
            value={method}
            onChange={(e) => setMethod(e.target.value as PaymentMethod)}
          >
            {(["cash", "card", "wallet"] as const).map((m) => (
              <option key={m} value={m}>
                {t(`pay.${m}`)}
              </option>
            ))}
          </Select>
        </div>
        <ErrorText error={submit.error} />
      </div>
    </Modal>
  );
}
