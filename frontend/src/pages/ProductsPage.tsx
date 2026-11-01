import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Tags } from "lucide-react";
import { useState } from "react";
import type { FormEvent } from "react";
import { api } from "../api/client";
import type { Category, Page, Product, ProductInput } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { useShop } from "../auth/ShopContext";
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
  td,
  th,
  thEnd,
} from "../components/ui";
import { Pager } from "../components/Pager";
import { useI18n } from "../i18n";
import { formatAmount, marginPercent } from "../lib/format";
import { useDebounced } from "../lib/hooks";

const PAGE_SIZE = 25;

export function useCategories() {
  return useQuery({ queryKey: ["categories"], queryFn: () => api<Category[]>("/categories") });
}

export function ProductsPage() {
  const { t, lang, pick } = useI18n();
  const { hasRole } = useAuth();
  const { branchId } = useShop();
  const isManager = hasRole("owner", "manager");

  const [search, setSearch] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [showInactive, setShowInactive] = useState(false);
  const [offset, setOffset] = useState(0);
  const [editing, setEditing] = useState<Product | "new" | null>(null);
  const [showCategories, setShowCategories] = useState(false);
  const q = useDebounced(search);

  const categories = useCategories();
  const products = useQuery({
    queryKey: ["products", { q, categoryId, showInactive, offset, branchId }],
    queryFn: () =>
      api<Page<Product>>("/products", {
        query: {
          q,
          category_id: categoryId,
          include_inactive: showInactive,
          branch_id: branchId,
          limit: PAGE_SIZE,
          offset,
        },
      }),
    placeholderData: keepPreviousData,
  });

  const categoryName = (id: number | null) => {
    const category = categories.data?.find((c) => c.id === id);
    return category ? pick(category.name, category.name_ar) : t("categories.uncategorised");
  };

  return (
    <div>
      <PageHeader
        title={t("products.title")}
        actions={
          isManager && (
            <>
              <Button
                variant="secondary"
                icon={<Tags className="size-4" />}
                onClick={() => setShowCategories(true)}
              >
                {t("products.categories")}
              </Button>
              <Button icon={<Plus className="size-4" />} onClick={() => setEditing("new")}>
                {t("products.new")}
              </Button>
            </>
          )
        }
      />

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
              label={t("products.showInactive")}
              checked={showInactive}
              onChange={setShowInactive}
            />
          </div>
        </div>

        {products.isLoading ? (
          <Spinner label={t("common.loading")} />
        ) : products.error ? (
          <div className="p-4">
            <ErrorText error={products.error} />
          </div>
        ) : products.data && products.data.items.length === 0 ? (
          <EmptyState>{q ? t("common.nothingFound") : t("products.empty")}</EmptyState>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-stone-100">
              <thead className="bg-stone-50">
                <tr>
                  <th className={th}>{t("products.product")}</th>
                  <th className={th}>{t("products.category")}</th>
                  <th className={thEnd}>{t("products.price")}</th>
                  {isManager && <th className={thEnd}>{t("products.cost")}</th>}
                  {isManager && <th className={thEnd}>{t("products.margin")}</th>}
                  <th className={thEnd}>{t("products.stock")}</th>
                  <th className={th}>{t("products.status")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {products.data?.items.map((p) => {
                  const margin = marginPercent(p.sale_price, p.cost_price);
                  const low = p.stock !== null && p.stock <= p.low_stock_threshold;
                  return (
                    <tr
                      key={p.id}
                      className={isManager ? "cursor-pointer hover:bg-stone-50" : undefined}
                      onClick={() => isManager && setEditing(p)}
                    >
                      <td className={td}>
                        <div className="font-medium">{pick(p.name, p.name_ar)}</div>
                        <div className="text-xs text-stone-500">
                          {p.sku}
                          {p.barcode && <span className="ms-2">{p.barcode}</span>}
                        </div>
                      </td>
                      <td className={td}>{categoryName(p.category_id)}</td>
                      <td className={`${td} num text-end`}>{formatAmount(p.sale_price, lang)}</td>
                      {isManager && (
                        <td className={`${td} num text-end`}>{formatAmount(p.cost_price, lang)}</td>
                      )}
                      {isManager && (
                        <td className={`${td} num text-end`}>
                          {margin === null ? "" : `${margin.toFixed(1)}%`}
                        </td>
                      )}
                      <td className={`${td} num text-end`}>
                        {p.stock === null ? (
                          ""
                        ) : (
                          <span className={low ? "font-semibold text-red-600" : ""}>{p.stock}</span>
                        )}
                      </td>
                      <td className={td}>
                        <Badge tone={p.is_active ? "green" : "gray"}>
                          {p.is_active ? t("common.active") : t("common.inactive")}
                        </Badge>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        {products.data && (
          <Pager
            offset={offset}
            limit={PAGE_SIZE}
            total={products.data.total}
            onChange={setOffset}
          />
        )}
      </Card>

      {editing && (
        <ProductForm
          product={editing === "new" ? null : editing}
          categories={categories.data ?? []}
          onClose={() => setEditing(null)}
        />
      )}
      <CategoriesModal open={showCategories} onClose={() => setShowCategories(false)} />
    </div>
  );
}

function toNumber(value: string): number | null {
  const trimmed = value.trim();
  return trimmed === "" ? null : Number(trimmed);
}

function ProductForm({
  product,
  categories,
  onClose,
}: {
  product: Product | null;
  categories: Category[];
  onClose: () => void;
}) {
  const { t, pick } = useI18n();
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    sku: product?.sku ?? "",
    barcode: product?.barcode ?? "",
    name: product?.name ?? "",
    name_ar: product?.name_ar ?? "",
    category_id: product?.category_id ? String(product.category_id) : "",
    unit: product?.unit ?? "pcs",
    cost_price: product?.cost_price?.toFixed(2) ?? "",
    sale_price: product ? product.sale_price.toFixed(2) : "",
    tax_rate:
      product?.tax_rate === null || product?.tax_rate === undefined ? "" : String(product.tax_rate),
    low_stock_threshold: product ? String(product.low_stock_threshold) : "",
    is_active: product?.is_active ?? true,
  });
  const set = (field: keyof typeof form) => (value: string | boolean) =>
    setForm((current) => ({ ...current, [field]: value }));

  const save = useMutation({
    mutationFn: () => {
      const body: ProductInput = {
        sku: form.sku,
        barcode: form.barcode.trim() || null,
        name: form.name,
        name_ar: form.name_ar,
        category_id: form.category_id ? Number(form.category_id) : null,
        unit: form.unit,
        cost_price: toNumber(form.cost_price) ?? 0,
        sale_price: toNumber(form.sale_price) ?? 0,
        tax_rate: toNumber(form.tax_rate),
        low_stock_threshold: toNumber(form.low_stock_threshold),
        is_active: form.is_active,
      };
      return product
        ? api<Product>(`/products/${product.id}`, { method: "PATCH", body })
        : api<Product>("/products", { method: "POST", body });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] });
      queryClient.invalidateQueries({ queryKey: ["categories"] });
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
      wide
      title={product ? t("products.edit") : t("products.new")}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button type="submit" form="product-form" disabled={save.isPending}>
            {t("common.save")}
          </Button>
        </>
      }
    >
      <form id="product-form" onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
        <Input
          label={t("products.name")}
          value={form.name}
          onChange={(e) => set("name")(e.target.value)}
          required
        />
        <Input
          label={t("products.nameAr")}
          dir="rtl"
          value={form.name_ar}
          onChange={(e) => set("name_ar")(e.target.value)}
        />
        <Input
          label={t("products.sku")}
          value={form.sku}
          onChange={(e) => set("sku")(e.target.value)}
          required
        />
        <Input
          label={t("products.barcode")}
          value={form.barcode}
          onChange={(e) => set("barcode")(e.target.value)}
          hint={t("common.optional")}
        />
        <Select
          label={t("products.category")}
          value={form.category_id}
          onChange={(e) => set("category_id")(e.target.value)}
        >
          <option value="">{t("categories.uncategorised")}</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {pick(c.name, c.name_ar)}
            </option>
          ))}
        </Select>
        <Input
          label={t("products.unit")}
          value={form.unit}
          onChange={(e) => set("unit")(e.target.value)}
          required
        />
        <Input
          label={`${t("products.cost")} (QAR)`}
          type="number"
          step="0.01"
          min="0"
          value={form.cost_price}
          onChange={(e) => set("cost_price")(e.target.value)}
        />
        <Input
          label={`${t("products.price")} (QAR)`}
          type="number"
          step="0.01"
          min="0"
          value={form.sale_price}
          onChange={(e) => set("sale_price")(e.target.value)}
          required
        />
        <Input
          label={t("products.taxRate")}
          type="number"
          step="0.01"
          min="0"
          max="100"
          value={form.tax_rate}
          onChange={(e) => set("tax_rate")(e.target.value)}
          hint={t("products.taxDefault")}
        />
        <Input
          label={t("products.threshold")}
          type="number"
          min="0"
          value={form.low_stock_threshold}
          onChange={(e) => set("low_stock_threshold")(e.target.value)}
        />
        <div className="sm:col-span-2">
          <Checkbox
            label={t("common.active")}
            checked={form.is_active}
            onChange={set("is_active")}
          />
        </div>
        {save.error && (
          <div className="sm:col-span-2">
            <ErrorText error={save.error} />
          </div>
        )}
      </form>
    </Modal>
  );
}

function CategoriesModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const categories = useCategories();
  const [name, setName] = useState("");
  const [nameAr, setNameAr] = useState("");

  const refresh = () => queryClient.invalidateQueries({ queryKey: ["categories"] });
  const create = useMutation({
    mutationFn: () => api<Category>("/categories", { body: { name, name_ar: nameAr } }),
    onSuccess: () => {
      setName("");
      setNameAr("");
      refresh();
    },
  });
  const remove = useMutation({
    mutationFn: (id: number) => api<void>(`/categories/${id}`, { method: "DELETE" }),
    onSuccess: refresh,
  });

  return (
    <Modal open={open} title={t("categories.title")} onClose={onClose}>
      <form
        className="mb-4 flex flex-wrap items-end gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          create.mutate();
        }}
      >
        <Input
          className="flex-1"
          label={t("categories.name")}
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <Input
          className="flex-1"
          label={t("categories.nameAr")}
          dir="rtl"
          value={nameAr}
          onChange={(e) => setNameAr(e.target.value)}
        />
        <Button type="submit" icon={<Plus className="size-4" />} disabled={create.isPending}>
          {t("common.add")}
        </Button>
      </form>
      <ErrorText error={create.error ?? remove.error} />
      <ul className="mt-2 divide-y divide-stone-100">
        {categories.data?.map((c) => (
          <li key={c.id} className="flex items-center justify-between py-2 text-sm">
            <span>
              {c.name}
              {c.name_ar && <span className="ms-2 text-stone-500">{c.name_ar}</span>}
            </span>
            <span className="flex items-center gap-3">
              <span className="text-stone-500">{c.product_count}</span>
              <Button size="sm" variant="ghost" onClick={() => remove.mutate(c.id)}>
                {t("common.delete")}
              </Button>
            </span>
          </li>
        ))}
      </ul>
    </Modal>
  );
}
