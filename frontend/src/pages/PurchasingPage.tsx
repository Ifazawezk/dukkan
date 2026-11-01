import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PackageCheck, Plus, Sparkles, Trash2 } from "lucide-react";
import { useState } from "react";
import type { FormEvent } from "react";
import { api } from "../api/client";
import type {
  Page,
  Product,
  PurchaseOrder,
  PurchaseOrderStatus,
  PurchaseOrderSummary,
  StockRow,
  Supplier,
} from "../api/types";
import { useShop } from "../auth/ShopContext";
import { Pager } from "../components/Pager";
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
  cx,
  td,
  th,
  thEnd,
} from "../components/ui";
import { useI18n } from "../i18n";
import { formatAmount, formatDate } from "../lib/format";
import { useDebounced } from "../lib/hooks";

const STATUS_TONES: Record<PurchaseOrderStatus, "gray" | "blue" | "amber" | "green" | "red"> = {
  draft: "gray",
  ordered: "blue",
  partially_received: "amber",
  received: "green",
  cancelled: "red",
};

function useSuppliers() {
  return useQuery({ queryKey: ["suppliers"], queryFn: () => api<Supplier[]>("/suppliers") });
}

export function PurchasingPage() {
  const { t } = useI18n();
  const [tab, setTab] = useState<"orders" | "suppliers">("orders");
  const [creating, setCreating] = useState(false);
  const [editingSupplier, setEditingSupplier] = useState<Supplier | "new" | null>(null);

  return (
    <div>
      <PageHeader
        title={t("purchasing.title")}
        actions={
          tab === "orders" ? (
            <Button icon={<Plus className="size-4" />} onClick={() => setCreating(true)}>
              {t("purchasing.new")}
            </Button>
          ) : (
            <Button icon={<Plus className="size-4" />} onClick={() => setEditingSupplier("new")}>
              {t("suppliers.new")}
            </Button>
          )
        }
      />
      <div className="mb-4 flex gap-1 rounded-lg bg-stone-200/70 p-1 text-sm font-medium sm:w-fit">
        {(["orders", "suppliers"] as const).map((name) => (
          <button
            key={name}
            onClick={() => setTab(name)}
            className={cx(
              "flex-1 whitespace-nowrap rounded-md px-4 py-1.5",
              tab === name ? "bg-white shadow-sm" : "text-stone-600",
            )}
          >
            {t(name === "orders" ? "purchasing.orders" : "purchasing.suppliers")}
          </button>
        ))}
      </div>
      {tab === "orders" ? <OrderList /> : <SupplierList onEdit={setEditingSupplier} />}
      {creating && <NewOrderDialog onClose={() => setCreating(false)} />}
      {editingSupplier && (
        <SupplierDialog
          supplier={editingSupplier === "new" ? null : editingSupplier}
          onClose={() => setEditingSupplier(null)}
        />
      )}
    </div>
  );
}

function OrderList() {
  const { t, lang } = useI18n();
  const [status, setStatus] = useState("");
  const [offset, setOffset] = useState(0);
  const [openId, setOpenId] = useState<number | null>(null);
  const orders = useQuery({
    queryKey: ["purchase-orders", { status, offset }],
    queryFn: () =>
      api<Page<PurchaseOrderSummary>>("/purchase-orders", {
        query: { status, limit: 25, offset },
      }),
    placeholderData: keepPreviousData,
  });

  return (
    <Card>
      <div className="border-b border-stone-100 p-4">
        <Select
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setOffset(0);
          }}
        >
          <option value="">{t("common.all")}</option>
          {(Object.keys(STATUS_TONES) as PurchaseOrderStatus[]).map((s) => (
            <option key={s} value={s}>
              {t(`status.${s}`)}
            </option>
          ))}
        </Select>
      </div>
      {orders.isLoading ? (
        <Spinner />
      ) : orders.data?.items.length === 0 ? (
        <EmptyState>{t("common.nothingFound")}</EmptyState>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-stone-100">
            <thead className="bg-stone-50">
              <tr>
                <th className={th}>{t("purchasing.number")}</th>
                <th className={th}>{t("purchasing.supplier")}</th>
                <th className={th}>{t("products.status")}</th>
                <th className={th}>{t("purchasing.created")}</th>
                <th className={thEnd}>{t("purchasing.items")}</th>
                <th className={thEnd}>{t("purchasing.total")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {orders.data?.items.map((po) => (
                <tr
                  key={po.id}
                  className="cursor-pointer hover:bg-stone-50"
                  onClick={() => setOpenId(po.id)}
                >
                  <td className={`${td} font-medium`}>{po.number}</td>
                  <td className={td}>{po.supplier_name}</td>
                  <td className={td}>
                    <Badge tone={STATUS_TONES[po.status]}>{t(`status.${po.status}`)}</Badge>
                  </td>
                  <td className={`${td} text-stone-600`}>{formatDate(po.created_at, lang)}</td>
                  <td className={`${td} num text-end`}>{po.item_count}</td>
                  <td className={`${td} num text-end`}>{formatAmount(po.total_cost, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {orders.data && (
        <Pager offset={offset} limit={25} total={orders.data.total} onChange={setOffset} />
      )}
      {openId !== null && <OrderDialog id={openId} onClose={() => setOpenId(null)} />}
    </Card>
  );
}

interface DraftLine {
  product: { id: number; name: string; name_ar: string; sku: string };
  quantity: number;
  unit_cost: number;
}

function NewOrderDialog({ onClose }: { onClose: () => void }) {
  const { t, lang, pick } = useI18n();
  const { branchId } = useShop();
  const queryClient = useQueryClient();
  const suppliers = useSuppliers();
  const [supplierId, setSupplierId] = useState("");
  const [expected, setExpected] = useState("");
  const [notes, setNotes] = useState("");
  const [lines, setLines] = useState<DraftLine[]>([]);
  const [search, setSearch] = useState("");
  const q = useDebounced(search);

  const found = useQuery({
    queryKey: ["po-product-search", q],
    queryFn: () => api<Page<Product>>("/products", { query: { q, limit: 8 } }),
    enabled: q.length > 1,
  });

  function addLine(line: DraftLine) {
    setLines((current) =>
      current.some((l) => l.product.id === line.product.id) ? current : [...current, line],
    );
  }

  async function addLowStock() {
    const low = await api<Page<StockRow>>("/inventory/stock", {
      query: { branch_id: branchId, low_only: true, limit: 200 },
    });
    for (const row of low.items) {
      addLine({
        product: { id: row.product_id, name: row.name, name_ar: row.name_ar, sku: row.sku },
        quantity: Math.max(row.low_stock_threshold * 3 - row.quantity, 1),
        unit_cost: row.cost_price ?? 0,
      });
    }
  }

  const save = useMutation({
    mutationFn: () =>
      api<PurchaseOrder>("/purchase-orders", {
        body: {
          supplier_id: Number(supplierId),
          branch_id: branchId,
          expected_date: expected || null,
          notes,
          items: lines.map((l) => ({
            product_id: l.product.id,
            quantity: l.quantity,
            unit_cost: l.unit_cost,
          })),
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["purchase-orders"] });
      onClose();
    },
  });

  const total = lines.reduce((sum, l) => sum + l.quantity * l.unit_cost, 0);

  function submit(event: FormEvent) {
    event.preventDefault();
    save.mutate();
  }

  return (
    <Modal
      open
      wide
      title={t("purchasing.new")}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button
            type="submit"
            form="po-form"
            disabled={save.isPending || !supplierId || lines.length === 0}
          >
            {t("common.save")}
          </Button>
        </>
      }
    >
      <form id="po-form" onSubmit={submit} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Select
            label={t("purchasing.supplier")}
            value={supplierId}
            onChange={(e) => setSupplierId(e.target.value)}
            required
          >
            <option value="" />
            {suppliers.data?.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </Select>
          <Input
            label={t("purchasing.expected")}
            type="date"
            value={expected}
            onChange={(e) => setExpected(e.target.value)}
          />
        </div>

        <div className="relative">
          <div className="flex items-end gap-2">
            <Input
              className="flex-1"
              label={t("purchasing.addProduct")}
              placeholder={t("products.searchHint")}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <Button
              variant="secondary"
              icon={<Sparkles className="size-4" />}
              onClick={() => void addLowStock()}
            >
              {t("purchasing.suggest")}
            </Button>
          </div>
          {q.length > 1 && found.data && found.data.items.length > 0 && (
            <ul className="absolute z-10 mt-1 max-h-60 w-full overflow-y-auto rounded-lg bg-white shadow-lg ring-1 ring-stone-200">
              {found.data.items.map((p) => (
                <li key={p.id}>
                  <button
                    type="button"
                    className="flex w-full items-center justify-between px-3 py-2 text-start text-sm hover:bg-stone-50"
                    onClick={() => {
                      addLine({ product: p, quantity: 12, unit_cost: p.cost_price ?? 0 });
                      setSearch("");
                    }}
                  >
                    <span>{pick(p.name, p.name_ar)}</span>
                    <span className="text-xs text-stone-500">{p.sku}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {lines.length === 0 ? (
          <p className="rounded-lg bg-stone-50 py-6 text-center text-sm text-stone-500">
            {t("purchasing.noItems")}
          </p>
        ) : (
          <table className="min-w-full divide-y divide-stone-100">
            <thead>
              <tr>
                <th className={th}>{t("products.product")}</th>
                <th className={thEnd}>{t("purchasing.ordered")}</th>
                <th className={thEnd}>{t("purchasing.unitCost")}</th>
                <th className={thEnd}>{t("sales.total")}</th>
                <th />
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {lines.map((line, i) => (
                <tr key={line.product.id}>
                  <td className={td}>
                    <div className="font-medium">
                      {pick(line.product.name, line.product.name_ar)}
                    </div>
                    <div className="text-xs text-stone-500">{line.product.sku}</div>
                  </td>
                  <td className={`${td} text-end`}>
                    <input
                      type="number"
                      min="1"
                      className="num h-8 w-20 rounded-md border border-stone-300 px-2 text-end"
                      value={line.quantity}
                      onChange={(e) =>
                        setLines(
                          lines.map((l, j) =>
                            j === i ? { ...l, quantity: Number(e.target.value) } : l,
                          ),
                        )
                      }
                    />
                  </td>
                  <td className={`${td} text-end`}>
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      className="num h-8 w-24 rounded-md border border-stone-300 px-2 text-end"
                      value={line.unit_cost}
                      onChange={(e) =>
                        setLines(
                          lines.map((l, j) =>
                            j === i ? { ...l, unit_cost: Number(e.target.value) } : l,
                          ),
                        )
                      }
                    />
                  </td>
                  <td className={`${td} num text-end`}>
                    {formatAmount(line.quantity * line.unit_cost, lang)}
                  </td>
                  <td className={td}>
                    <button
                      type="button"
                      className="rounded p-1 text-stone-400 hover:text-red-600"
                      onClick={() => setLines(lines.filter((_, j) => j !== i))}
                      aria-label={t("common.delete")}
                    >
                      <Trash2 className="size-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td className={`${td} font-medium`} colSpan={3}>
                  {t("purchasing.total")}
                </td>
                <td className={`${td} num text-end font-semibold`}>{formatAmount(total, lang)}</td>
                <td />
              </tr>
            </tfoot>
          </table>
        )}
        <Input
          label={t("purchasing.notes")}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
        <ErrorText error={save.error} />
      </form>
    </Modal>
  );
}

function OrderDialog({ id, onClose }: { id: number; onClose: () => void }) {
  const { t, lang, pick } = useI18n();
  const queryClient = useQueryClient();
  const [receiving, setReceiving] = useState<Record<number, number> | null>(null);
  const order = useQuery({
    queryKey: ["purchase-order", id],
    queryFn: () => api<PurchaseOrder>(`/purchase-orders/${id}`),
  });

  const act = useMutation({
    mutationFn: ({ path, body }: { path: string; body?: unknown }) =>
      api<PurchaseOrder>(`/purchase-orders/${id}/${path}`, { method: "POST", body }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["purchase-order", id], updated);
      queryClient.invalidateQueries({ queryKey: ["purchase-orders"] });
      queryClient.invalidateQueries({ queryKey: ["stock"] });
      queryClient.invalidateQueries({ queryKey: ["products"] });
      setReceiving(null);
    },
  });

  const po = order.data;
  const open = po && ["draft", "ordered", "partially_received"].includes(po.status);

  function startReceiving() {
    if (!po) return;
    setReceiving(
      Object.fromEntries(po.items.map((i) => [i.id, i.quantity_ordered - i.quantity_received])),
    );
  }

  function receive() {
    if (!receiving) return;
    const lines = Object.entries(receiving)
      .filter(([, quantity]) => quantity > 0)
      .map(([itemId, quantity]) => ({ item_id: Number(itemId), quantity }));
    act.mutate({ path: "receive", body: { lines } });
  }

  return (
    <Modal
      open
      wide
      title={po ? `${po.number} - ${po.supplier_name}` : t("common.loading")}
      onClose={onClose}
      footer={
        po && (
          <>
            {(po.status === "draft" || po.status === "ordered") && (
              <Button variant="ghost" onClick={() => act.mutate({ path: "cancel" })}>
                {t("purchasing.cancel")}
              </Button>
            )}
            {po.status === "draft" && (
              <Button variant="secondary" onClick={() => act.mutate({ path: "submit" })}>
                {t("purchasing.submit")}
              </Button>
            )}
            {open &&
              (receiving ? (
                <Button
                  icon={<PackageCheck className="size-4" />}
                  onClick={receive}
                  disabled={act.isPending}
                >
                  {t("purchasing.receiveNow")}
                </Button>
              ) : (
                <Button icon={<PackageCheck className="size-4" />} onClick={startReceiving}>
                  {t("purchasing.receive")}
                </Button>
              ))}
          </>
        )
      }
    >
      {!po ? (
        <Spinner />
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-3 text-sm text-stone-600">
            <Badge tone={STATUS_TONES[po.status]}>{t(`status.${po.status}`)}</Badge>
            <span>
              {t("purchasing.created")}: {formatDate(po.created_at, lang)}
            </span>
            {po.expected_date && (
              <span>
                {t("purchasing.expected")}: {formatDate(po.expected_date, lang)}
              </span>
            )}
          </div>
          {po.notes && <p className="rounded-lg bg-stone-50 px-3 py-2 text-sm">{po.notes}</p>}
          {receiving && <p className="text-sm text-stone-600">{t("purchasing.receiveHint")}</p>}
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-stone-100">
              <thead>
                <tr>
                  <th className={th}>{t("products.product")}</th>
                  <th className={thEnd}>{t("purchasing.ordered")}</th>
                  <th className={thEnd}>{t("purchasing.received")}</th>
                  <th className={thEnd}>{t("purchasing.unitCost")}</th>
                  <th className={thEnd}>{t("sales.total")}</th>
                  {receiving && <th className={thEnd}>{t("purchasing.receive")}</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {po.items.map((item) => (
                  <tr key={item.id}>
                    <td className={td}>
                      <div className="font-medium">
                        {pick(item.product_name, item.product_name_ar)}
                      </div>
                      <div className="text-xs text-stone-500">{item.sku}</div>
                    </td>
                    <td className={`${td} num text-end`}>{item.quantity_ordered}</td>
                    <td className={`${td} num text-end`}>{item.quantity_received}</td>
                    <td className={`${td} num text-end`}>{formatAmount(item.unit_cost, lang)}</td>
                    <td className={`${td} num text-end`}>{formatAmount(item.line_total, lang)}</td>
                    {receiving && (
                      <td className={`${td} text-end`}>
                        <input
                          type="number"
                          min="0"
                          max={item.quantity_ordered - item.quantity_received}
                          className="num h-8 w-20 rounded-md border border-stone-300 px-2 text-end"
                          value={receiving[item.id] ?? 0}
                          onChange={(e) =>
                            setReceiving({ ...receiving, [item.id]: Number(e.target.value) })
                          }
                        />
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr>
                  <td className={`${td} font-medium`} colSpan={4}>
                    {t("purchasing.total")}
                  </td>
                  <td className={`${td} num text-end font-semibold`}>
                    {formatAmount(po.total_cost, lang)}
                  </td>
                  {receiving && <td />}
                </tr>
              </tfoot>
            </table>
          </div>
          <ErrorText error={act.error} />
        </div>
      )}
    </Modal>
  );
}

function SupplierList({ onEdit }: { onEdit: (supplier: Supplier) => void }) {
  const { t } = useI18n();
  const suppliers = useSuppliers();
  return (
    <Card>
      {suppliers.isLoading ? (
        <Spinner />
      ) : suppliers.data?.length === 0 ? (
        <EmptyState>{t("common.nothingFound")}</EmptyState>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-stone-100">
            <thead className="bg-stone-50">
              <tr>
                <th className={th}>{t("suppliers.name")}</th>
                <th className={th}>{t("suppliers.contact")}</th>
                <th className={th}>{t("suppliers.phone")}</th>
                <th className={th}>{t("suppliers.email")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {suppliers.data?.map((s) => (
                <tr
                  key={s.id}
                  className="cursor-pointer hover:bg-stone-50"
                  onClick={() => onEdit(s)}
                >
                  <td className={`${td} font-medium`}>{s.name}</td>
                  <td className={td}>{s.contact_name}</td>
                  <td className={td} dir="ltr">
                    {s.phone}
                  </td>
                  <td className={td}>{s.email}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

function SupplierDialog({ supplier, onClose }: { supplier: Supplier | null; onClose: () => void }) {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    name: supplier?.name ?? "",
    contact_name: supplier?.contact_name ?? "",
    phone: supplier?.phone ?? "",
    email: supplier?.email ?? "",
    address: supplier?.address ?? "",
    notes: supplier?.notes ?? "",
  });
  const field = (name: keyof typeof form) => ({
    value: form[name],
    onChange: (e: { target: { value: string } }) => setForm({ ...form, [name]: e.target.value }),
  });

  const save = useMutation({
    mutationFn: () =>
      supplier
        ? api<Supplier>(`/suppliers/${supplier.id}`, { method: "PATCH", body: form })
        : api<Supplier>("/suppliers", { body: form }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["suppliers"] });
      onClose();
    },
  });

  return (
    <Modal
      open
      title={supplier ? t("suppliers.edit") : t("suppliers.new")}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button type="submit" form="supplier-form" disabled={save.isPending}>
            {t("common.save")}
          </Button>
        </>
      }
    >
      <form
        id="supplier-form"
        className="grid gap-4 sm:grid-cols-2"
        onSubmit={(e) => {
          e.preventDefault();
          save.mutate();
        }}
      >
        <Input className="sm:col-span-2" label={t("suppliers.name")} required {...field("name")} />
        <Input label={t("suppliers.contact")} {...field("contact_name")} />
        <Input label={t("suppliers.phone")} dir="ltr" {...field("phone")} />
        <Input
          className="sm:col-span-2"
          label={t("suppliers.email")}
          type="email"
          {...field("email")}
        />
        <Input className="sm:col-span-2" label={t("suppliers.address")} {...field("address")} />
        <div className="sm:col-span-2">
          <ErrorText error={save.error} />
        </div>
      </form>
    </Modal>
  );
}
