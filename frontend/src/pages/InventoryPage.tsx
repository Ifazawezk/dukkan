import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { History, ShieldCheck, SlidersHorizontal } from "lucide-react";
import { useState } from "react";
import type { FormEvent } from "react";
import { api } from "../api/client";
import type {
  AdjustmentReason,
  LedgerCheck,
  Movement,
  MovementKind,
  Page,
  StockRow,
} from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { useShop } from "../auth/ShopContext";
import { Pager } from "../components/Pager";
import {
  Badge,
  Button,
  Card,
  Checkbox,
  EmptyState,
  ErrorText,
  Input,
  Modal,
  PageHeader,
  Select,
  Spinner,
  cx,
  td,
  th,
  thEnd,
} from "../components/ui";
import { useI18n } from "../i18n";
import { formatAmount, formatDateTime } from "../lib/format";
import { useDebounced } from "../lib/hooks";
import { useCategories } from "./ProductsPage";

const PAGE_SIZE = 50;
const REASONS: AdjustmentReason[] = [
  "count_correction",
  "damaged",
  "expired",
  "lost",
  "internal_use",
  "opening_stock",
  "other",
];
const KIND_TONES: Record<MovementKind, "green" | "blue" | "amber" | "gray"> = {
  purchase: "green",
  sale: "blue",
  return: "amber",
  adjustment: "gray",
};

export function InventoryPage() {
  const { t } = useI18n();
  const { hasRole } = useAuth();
  const isManager = hasRole("owner", "manager");
  const [tab, setTab] = useState<"stock" | "ledger">("stock");
  const [check, setCheck] = useState<LedgerCheck | null>(null);

  const verify = useMutation({
    mutationFn: () => api<LedgerCheck>("/inventory/verify"),
    onSuccess: setCheck,
  });

  return (
    <div>
      <PageHeader
        title={t("inventory.title")}
        actions={
          isManager && (
            <Button
              variant="secondary"
              icon={<ShieldCheck className="size-4" />}
              onClick={() => verify.mutate()}
              disabled={verify.isPending}
            >
              {t("inventory.verify")}
            </Button>
          )
        }
      />
      {check && (
        <div
          className={cx(
            "mb-4 rounded-lg px-3 py-2 text-sm ring-1",
            check.ok
              ? "bg-emerald-50 text-emerald-800 ring-emerald-200"
              : "bg-red-50 text-red-800 ring-red-200",
          )}
        >
          {check.ok
            ? t("inventory.verifyOk", { count: check.pairs_checked })
            : t("inventory.verifyBad", { count: check.problems.length })}
        </div>
      )}
      {isManager && (
        <div className="mb-4 flex gap-1 rounded-lg bg-stone-200/70 p-1 text-sm font-medium sm:w-fit">
          {(["stock", "ledger"] as const).map((name) => (
            <button
              key={name}
              onClick={() => setTab(name)}
              className={cx(
                "flex-1 whitespace-nowrap rounded-md px-4 py-1.5",
                tab === name ? "bg-white shadow-sm" : "text-stone-600",
              )}
            >
              {t(name === "stock" ? "inventory.stock" : "inventory.movements")}
            </button>
          ))}
        </div>
      )}
      {tab === "stock" ? <StockTable /> : <MovementTable />}
    </div>
  );
}

function StockTable() {
  const { t, lang, pick } = useI18n();
  const { hasRole } = useAuth();
  const { branchId } = useShop();
  const isManager = hasRole("owner", "manager");
  const [search, setSearch] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [lowOnly, setLowOnly] = useState(false);
  const [offset, setOffset] = useState(0);
  const [adjusting, setAdjusting] = useState<StockRow | null>(null);
  const [history, setHistory] = useState<StockRow | null>(null);
  const q = useDebounced(search);
  const categories = useCategories();

  const stock = useQuery({
    queryKey: ["stock", { q, categoryId, lowOnly, offset, branchId }],
    queryFn: () =>
      api<Page<StockRow>>("/inventory/stock", {
        query: {
          q,
          category_id: categoryId,
          low_only: lowOnly,
          branch_id: branchId,
          limit: PAGE_SIZE,
          offset,
        },
      }),
    placeholderData: keepPreviousData,
    enabled: branchId !== null,
  });

  const pageValue = stock.data?.items.reduce((sum, row) => sum + (row.stock_value ?? 0), 0) ?? 0;

  return (
    <Card>
      <div className="flex flex-wrap items-end gap-3 border-b border-stone-100 p-4">
        <Input
          className="min-w-56 flex-1"
          placeholder={t("products.searchHint")}
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setOffset(0);
          }}
        />
        <Select
          value={categoryId}
          onChange={(e) => {
            setCategoryId(e.target.value);
            setOffset(0);
          }}
        >
          <option value="">{t("common.all")}</option>
          {categories.data?.map((c) => (
            <option key={c.id} value={c.id}>
              {pick(c.name, c.name_ar)}
            </option>
          ))}
        </Select>
        <div className="pb-2">
          <Checkbox
            label={t("inventory.lowOnly")}
            checked={lowOnly}
            onChange={(value) => {
              setLowOnly(value);
              setOffset(0);
            }}
          />
        </div>
      </div>

      {stock.isLoading ? (
        <Spinner label={t("common.loading")} />
      ) : stock.error ? (
        <div className="p-4">
          <ErrorText error={stock.error} />
        </div>
      ) : stock.data?.items.length === 0 ? (
        <EmptyState>{t("common.nothingFound")}</EmptyState>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-stone-100">
            <thead className="bg-stone-50">
              <tr>
                <th className={th}>{t("products.product")}</th>
                <th className={thEnd}>{t("inventory.onHand")}</th>
                <th className={thEnd}>{t("products.threshold")}</th>
                <th className={th}>{t("products.status")}</th>
                {isManager && <th className={thEnd}>{t("inventory.value")}</th>}
                <th className={th} />
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {stock.data?.items.map((row) => (
                <tr key={row.product_id}>
                  <td className={td}>
                    <div className="font-medium">{pick(row.name, row.name_ar)}</div>
                    <div className="text-xs text-stone-500">{row.sku}</div>
                  </td>
                  <td className={`${td} num text-end font-semibold`}>{row.quantity}</td>
                  <td className={`${td} num text-end text-stone-500`}>{row.low_stock_threshold}</td>
                  <td className={td}>
                    {row.quantity <= 0 ? (
                      <Badge tone="red">{t("inventory.out")}</Badge>
                    ) : row.is_low ? (
                      <Badge tone="amber">{t("inventory.low")}</Badge>
                    ) : (
                      <Badge tone="green">{t("inventory.ok")}</Badge>
                    )}
                  </td>
                  {isManager && (
                    <td className={`${td} num text-end`}>{formatAmount(row.stock_value, lang)}</td>
                  )}
                  <td className={`${td} whitespace-nowrap text-end`}>
                    {isManager && (
                      <div className="flex justify-end gap-1">
                        <Button
                          size="sm"
                          variant="ghost"
                          icon={<History className="size-4" />}
                          onClick={() => setHistory(row)}
                        >
                          {t("inventory.history")}
                        </Button>
                        <Button
                          size="sm"
                          variant="secondary"
                          icon={<SlidersHorizontal className="size-4" />}
                          onClick={() => setAdjusting(row)}
                        >
                          {t("inventory.adjust")}
                        </Button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
            {isManager && (
              <tfoot className="bg-stone-50">
                <tr>
                  <td className={`${td} font-medium`} colSpan={4}>
                    {t("inventory.totalValue")}
                  </td>
                  <td className={`${td} num text-end font-semibold`}>
                    {formatAmount(pageValue, lang)}
                  </td>
                  <td />
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      )}
      {stock.data && (
        <Pager offset={offset} limit={PAGE_SIZE} total={stock.data.total} onChange={setOffset} />
      )}
      {adjusting && <AdjustDialog row={adjusting} onClose={() => setAdjusting(null)} />}
      {history && (
        <Modal
          open
          wide
          title={`${t("inventory.history")}: ${pick(history.name, history.name_ar)}`}
          onClose={() => setHistory(null)}
        >
          <MovementTable productId={history.product_id} compact />
        </Modal>
      )}
    </Card>
  );
}

function MovementTable({ productId, compact = false }: { productId?: number; compact?: boolean }) {
  const { t, lang } = useI18n();
  const { branchId, settings } = useShop();
  const [kind, setKind] = useState("");
  const [offset, setOffset] = useState(0);
  const limit = compact ? 15 : PAGE_SIZE;

  const movements = useQuery({
    queryKey: ["movements", { productId, kind, offset, branchId, limit }],
    queryFn: () =>
      api<Page<Movement>>("/inventory/movements", {
        query: { product_id: productId, kind, branch_id: branchId, limit, offset },
      }),
    placeholderData: keepPreviousData,
  });

  const table = (
    <>
      {!compact && (
        <div className="flex gap-3 border-b border-stone-100 p-4">
          <Select
            value={kind}
            onChange={(e) => {
              setKind(e.target.value);
              setOffset(0);
            }}
          >
            <option value="">{t("common.all")}</option>
            {(["sale", "purchase", "return", "adjustment"] as const).map((k) => (
              <option key={k} value={k}>
                {t(`kind.${k}`)}
              </option>
            ))}
          </Select>
        </div>
      )}
      {movements.isLoading ? (
        <Spinner />
      ) : movements.data?.items.length === 0 ? (
        <EmptyState>{t("common.nothingFound")}</EmptyState>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-stone-100">
            <thead className="bg-stone-50">
              <tr>
                <th className={th}>{t("inventory.when")}</th>
                {!compact && <th className={th}>{t("products.product")}</th>}
                <th className={th}>{t("inventory.kind")}</th>
                <th className={thEnd}>{t("inventory.quantityChange")}</th>
                <th className={thEnd}>{t("inventory.balance")}</th>
                <th className={th}>{t("inventory.note")}</th>
                <th className={th}>{t("inventory.by")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {movements.data?.items.map((m) => (
                <tr key={m.id}>
                  <td className={`${td} whitespace-nowrap text-stone-600`}>
                    {formatDateTime(m.created_at, lang, settings?.timezone)}
                  </td>
                  {!compact && (
                    <td className={td}>
                      <div className="font-medium">{m.product_name}</div>
                      <div className="text-xs text-stone-500">{m.sku}</div>
                    </td>
                  )}
                  <td className={td}>
                    <Badge tone={KIND_TONES[m.kind]}>{t(`kind.${m.kind}`)}</Badge>
                  </td>
                  <td
                    className={cx(
                      td,
                      "num text-end font-semibold",
                      m.quantity_change > 0 ? "text-emerald-700" : "text-red-600",
                    )}
                    dir="ltr"
                  >
                    {m.quantity_change > 0 ? `+${m.quantity_change}` : m.quantity_change}
                  </td>
                  <td className={`${td} num text-end`}>{m.balance_after}</td>
                  <td className={`${td} text-stone-600`}>
                    {m.reason ? t(`reason.${m.reason}`) : ""}
                    {m.note && <span className="ms-1 text-stone-500">{m.note}</span>}
                  </td>
                  <td className={`${td} text-stone-600`}>{m.user_name}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {movements.data && (
        <Pager offset={offset} limit={limit} total={movements.data.total} onChange={setOffset} />
      )}
    </>
  );
  return compact ? table : <Card>{table}</Card>;
}

function AdjustDialog({ row, onClose }: { row: StockRow; onClose: () => void }) {
  const { t, pick } = useI18n();
  const { branchId } = useShop();
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<"change" | "count">("count");
  const [value, setValue] = useState("");
  const [reason, setReason] = useState<AdjustmentReason>("count_correction");
  const [note, setNote] = useState("");

  const save = useMutation({
    mutationFn: () =>
      api<Movement>("/inventory/adjustments", {
        body: {
          product_id: row.product_id,
          branch_id: branchId,
          reason,
          note,
          ...(mode === "count"
            ? { counted_quantity: Number(value) }
            : { quantity_change: Number(value) }),
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["stock"] });
      queryClient.invalidateQueries({ queryKey: ["movements"] });
      queryClient.invalidateQueries({ queryKey: ["products"] });
      onClose();
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    save.mutate();
  }

  return (
    <Modal
      open
      title={t("inventory.adjustTitle", { name: pick(row.name, row.name_ar) })}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button type="submit" form="adjust-form" disabled={save.isPending || value === ""}>
            {t("common.save")}
          </Button>
        </>
      }
    >
      <form id="adjust-form" onSubmit={submit} className="space-y-4">
        <p className="text-sm text-stone-600">
          {t("inventory.onHand")}: <span className="num font-semibold">{row.quantity}</span>
        </p>
        <Select
          label={t("inventory.mode")}
          value={mode}
          onChange={(e) => setMode(e.target.value as "change" | "count")}
        >
          <option value="count">{t("inventory.modeCount")}</option>
          <option value="change">{t("inventory.modeChange")}</option>
        </Select>
        <Input
          label={mode === "count" ? t("inventory.counted") : t("inventory.change")}
          type="number"
          step="1"
          min={mode === "count" ? 0 : undefined}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          autoFocus
          required
        />
        <Select
          label={t("inventory.reason")}
          value={reason}
          onChange={(e) => setReason(e.target.value as AdjustmentReason)}
        >
          {REASONS.map((r) => (
            <option key={r} value={r}>
              {t(`reason.${r}`)}
            </option>
          ))}
        </Select>
        <Input label={t("inventory.note")} value={note} onChange={(e) => setNote(e.target.value)} />
        <ErrorText error={save.error} />
      </form>
    </Modal>
  );
}
