import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Minus, Plus, Printer, ScanBarcode, ShoppingCart, Trash2, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { KeyboardEvent as ReactKeyboardEvent, ReactNode } from "react";
import { ApiError, api } from "../../api/client";
import type { CheckoutInput, Page, Product, Sale } from "../../api/types";
import { useAuth } from "../../auth/AuthContext";
import { useShop } from "../../auth/ShopContext";
import { Receipt } from "../../components/Receipt";
import { Button, Modal, cx } from "../../components/ui";
import { useI18n } from "../../i18n";
import { formatAmount, formatMoney } from "../../lib/format";
import { useDebounced } from "../../lib/hooks";
import { priceCart } from "../../lib/pricing";
import type { OrderDiscount } from "../../lib/pricing";
import { useCategories } from "../ProductsPage";
import { PaymentDialog } from "./PaymentDialog";
import type { PaymentLine } from "./PaymentDialog";

interface CartLine {
  product: Product;
  quantity: number;
}

export function PosPage() {
  const { t, lang, pick } = useI18n();
  const { hasRole } = useAuth();
  const { branchId, settings } = useShop();
  const queryClient = useQueryClient();

  const [cart, setCart] = useState<CartLine[]>([]);
  const [selected, setSelected] = useState(0);
  const [search, setSearch] = useState("");
  const [categoryId, setCategoryId] = useState<number | null>(null);
  const [highlight, setHighlight] = useState(0);
  const [notice, setNotice] = useState<string | null>(null);
  const [discount, setDiscount] = useState<OrderDiscount>({ type: "percent", value: 0 });
  const [paying, setPaying] = useState(false);
  const [receipt, setReceipt] = useState<Sale | null>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const q = useDebounced(search, 150);

  const categories = useCategories();
  const products = useQuery({
    queryKey: ["pos-products", { q, categoryId, branchId }],
    queryFn: () =>
      api<Page<Product>>("/products", {
        query: { q, category_id: categoryId, branch_id: branchId, limit: 60 },
      }),
    placeholderData: keepPreviousData,
    enabled: branchId !== null,
  });
  const results = products.data?.items ?? [];

  const allowNegative = settings?.allow_negative_stock ?? false;
  const defaultTax = settings?.default_tax_rate ?? 0;

  const totals = useMemo(
    () =>
      priceCart(
        cart.map((line) => ({
          price: line.product.sale_price,
          quantity: line.quantity,
          taxRate: line.product.tax_rate ?? defaultTax,
        })),
        discount.value > 0 ? discount : null,
      ),
    [cart, discount, defaultTax],
  );
  const itemCount = cart.reduce((sum, line) => sum + line.quantity, 0);

  const focusSearch = useCallback(() => searchRef.current?.focus(), []);

  // A ref so quick back-to-back barcode scans always see the latest cart.
  const cartRef = useRef(cart);
  cartRef.current = cart;

  function addProduct(product: Product, quantity = 1) {
    setNotice(null);
    const current = cartRef.current;
    const index = current.findIndex((line) => line.product.id === product.id);
    const inCart = index >= 0 ? current[index].quantity : 0;
    if (!allowNegative && product.stock !== null && inCart + quantity > product.stock) {
      setNotice(
        t("pos.outOfStock", { name: pick(product.name, product.name_ar), count: product.stock }),
      );
      return;
    }
    const next =
      index >= 0
        ? current.map((line, i) =>
            i === index ? { ...line, quantity: line.quantity + quantity } : line,
          )
        : [...current, { product, quantity }];
    cartRef.current = next;
    setCart(next);
    setSelected(index >= 0 ? index : current.length);
  }

  function changeQuantity(index: number, delta: number) {
    const line = cart[index];
    if (!line) return;
    if (delta > 0) {
      addProduct(line.product, delta);
      return;
    }
    setCart((current) =>
      current
        .map((l, i) => (i === index ? { ...l, quantity: l.quantity + delta } : l))
        .filter((l) => l.quantity > 0),
    );
  }

  function removeLine(index: number) {
    setCart((current) => current.filter((_, i) => i !== index));
    setSelected((s) => Math.max(0, Math.min(s, cart.length - 2)));
  }

  const clearCart = useCallback(() => {
    setCart([]);
    setDiscount({ type: "percent", value: 0 });
    setSelected(0);
    setNotice(null);
    focusSearch();
  }, [focusSearch]);

  // Barcode scanners type the code and press Enter.
  async function submitSearch() {
    const code = search.trim();
    if (!code) return;
    try {
      const product = await api<Product>("/products/lookup", {
        query: { code, branch_id: branchId },
      });
      addProduct(product);
      setSearch("");
      return;
    } catch (error) {
      if (!(error instanceof ApiError && error.status === 404)) throw error;
    }
    const match = results[highlight] ?? (results.length === 1 ? results[0] : undefined);
    if (match && q === search) {
      addProduct(match);
      setSearch("");
    } else {
      setNotice(t("pos.notFound", { code }));
    }
  }

  function onSearchKey(event: ReactKeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") {
      event.preventDefault();
      void submitSearch();
    } else if (event.key === "ArrowDown") {
      event.preventDefault();
      setHighlight((h) => Math.min(h + 1, results.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setHighlight((h) => Math.max(h - 1, 0));
    }
  }

  useEffect(() => setHighlight(0), [q, categoryId]);

  // Till shortcuts. They are ignored while a dialog is open.
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (paying || receipt) return;
      const typing = event.target instanceof HTMLInputElement && event.target !== searchRef.current;
      if (event.key === "F2") {
        event.preventDefault();
        focusSearch();
      } else if (event.key === "F4") {
        event.preventDefault();
        if (cart.length) setPaying(true);
      } else if (event.key === "F8") {
        event.preventDefault();
        clearCart();
      } else if (!typing && search === "" && (event.key === "+" || event.key === "-")) {
        event.preventDefault();
        changeQuantity(selected, event.key === "+" ? 1 : -1);
      } else if (!typing && search === "" && event.key === "Delete") {
        event.preventDefault();
        removeLine(selected);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const checkout = useMutation({
    mutationFn: (payments: PaymentLine[]) => {
      const body: CheckoutInput = {
        branch_id: branchId,
        items: cart.map((line) => ({ product_id: line.product.id, quantity: line.quantity })),
        discount: discount.value > 0 ? discount : null,
        payments: payments.map((p) => ({
          method: p.method,
          amount: p.amount,
          reference: p.reference,
        })),
      };
      return api<Sale>("/sales", { body });
    },
    onSuccess: (sale) => {
      setPaying(false);
      setReceipt(sale);
      queryClient.invalidateQueries({ queryKey: ["pos-products"] });
      queryClient.invalidateQueries({ queryKey: ["sales"] });
    },
  });

  function newSale() {
    setReceipt(null);
    checkout.reset();
    clearCart();
  }

  const maxCashierDiscount = settings?.max_cashier_discount_percent ?? 0;
  const isCashier = !hasRole("owner", "manager");

  return (
    <div className="grid h-full gap-4 lg:grid-cols-[minmax(0,1fr)_400px]">
      {/* Product picker */}
      <section className="flex min-h-0 flex-col gap-3">
        <div className="relative">
          <ScanBarcode className="pointer-events-none absolute start-3 top-1/2 size-5 -translate-y-1/2 text-stone-400" />
          <input
            ref={searchRef}
            autoFocus
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setNotice(null);
            }}
            onKeyDown={onSearchKey}
            placeholder={t("pos.searchHint")}
            className="h-14 w-full rounded-xl border border-stone-300 bg-white ps-11 pe-4 text-lg shadow-sm focus:border-brand-600 focus:outline-none focus:ring-4 focus:ring-brand-600/15"
          />
        </div>
        {notice && (
          <div className="flex items-center justify-between rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900 ring-1 ring-amber-200">
            {notice}
            <button onClick={() => setNotice(null)} aria-label={t("common.close")}>
              <X className="size-4" />
            </button>
          </div>
        )}

        <div className="flex gap-2 overflow-x-auto pb-1">
          <CategoryChip active={categoryId === null} onClick={() => setCategoryId(null)}>
            {t("common.all")}
          </CategoryChip>
          {categories.data?.map((c) => (
            <CategoryChip
              key={c.id}
              active={categoryId === c.id}
              onClick={() => setCategoryId(c.id)}
            >
              {pick(c.name, c.name_ar)}
            </CategoryChip>
          ))}
        </div>

        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-4">
          {results.map((product, index) => {
            const out = product.stock !== null && product.stock <= 0;
            return (
              <button
                key={product.id}
                onClick={() => {
                  addProduct(product);
                  focusSearch();
                }}
                disabled={out && !allowNegative}
                className={cx(
                  "flex min-h-24 flex-col justify-between rounded-xl bg-white p-3 text-start shadow-sm ring-1 transition",
                  index === highlight && search ? "ring-2 ring-brand-600" : "ring-stone-200",
                  out ? "opacity-50" : "hover:-translate-y-0.5 hover:shadow-md",
                )}
              >
                <span className="line-clamp-2 text-sm font-medium leading-snug">
                  {pick(product.name, product.name_ar)}
                </span>
                <span className="mt-2 flex items-end justify-between gap-2">
                  <span className="num text-base font-semibold text-brand-800">
                    {formatAmount(product.sale_price, lang)}
                  </span>
                  <span className={cx("text-xs", out ? "text-red-600" : "text-stone-500")}>
                    {out ? t("pos.noStock") : t("pos.inStock", { count: product.stock ?? 0 })}
                  </span>
                </span>
              </button>
            );
          })}
        </div>
        <p className="mt-auto hidden text-xs text-stone-500 lg:block">{t("pos.shortcuts")}</p>
      </section>

      {/* Cart */}
      <section className="flex min-h-[28rem] flex-col rounded-2xl bg-white shadow-sm ring-1 ring-stone-200 lg:sticky lg:top-4 lg:max-h-[calc(100vh-7rem)]">
        <header className="flex items-center justify-between border-b border-stone-100 px-4 py-3">
          <div className="flex items-center gap-2">
            <ShoppingCart className="size-4 text-stone-500" />
            <h2 className="text-sm font-semibold">{t("pos.cart")}</h2>
            {itemCount > 0 && (
              <span className="text-xs text-stone-500">{t("pos.items", { count: itemCount })}</span>
            )}
          </div>
          <Button size="sm" variant="ghost" onClick={clearCart} disabled={!cart.length}>
            {t("pos.clear")}
          </Button>
        </header>

        <ul className="min-h-0 flex-1 divide-y divide-stone-100 overflow-y-auto">
          {cart.length === 0 && (
            <li className="flex h-full flex-col items-center justify-center gap-2 p-8 text-center text-sm text-stone-500">
              <ScanBarcode className="size-8 text-stone-300" />
              {t("pos.emptyCart")}
            </li>
          )}
          {cart.map((line, index) => (
            <li
              key={line.product.id}
              onClick={() => setSelected(index)}
              className={cx(
                "flex items-center gap-3 px-4 py-2.5",
                index === selected && "bg-brand-50/60",
              )}
            >
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-medium">
                  {pick(line.product.name, line.product.name_ar)}
                </div>
                <div className="num text-xs text-stone-500">
                  {formatAmount(line.product.sale_price, lang)}
                </div>
              </div>
              <div className="flex items-center gap-1">
                <QtyButton label="-" onClick={() => changeQuantity(index, -1)}>
                  <Minus className="size-3.5" />
                </QtyButton>
                <span className="num w-8 text-center text-sm font-semibold">{line.quantity}</span>
                <QtyButton label="+" onClick={() => changeQuantity(index, 1)}>
                  <Plus className="size-3.5" />
                </QtyButton>
              </div>
              <div className="num w-20 text-end text-sm font-semibold">
                {formatAmount(totals.lineTotals[index], lang)}
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  removeLine(index);
                }}
                className="rounded p-1 text-stone-400 hover:bg-stone-100 hover:text-red-600"
                aria-label={t("common.delete")}
              >
                <Trash2 className="size-4" />
              </button>
            </li>
          ))}
        </ul>

        <div className="space-y-2 border-t border-stone-100 px-4 py-3 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-stone-600">{t("pos.subtotal")}</span>
            <span className="num">{formatAmount(totals.subtotal, lang)}</span>
          </div>
          <div className="flex items-center justify-between gap-3">
            <span className="text-stone-600">{t("pos.discount")}</span>
            <div className="flex items-center gap-1">
              <input
                type="number"
                min="0"
                step="0.01"
                value={discount.value || ""}
                onChange={(e) => setDiscount({ ...discount, value: Number(e.target.value) || 0 })}
                className="num h-8 w-20 rounded-md border border-stone-300 px-2 text-end text-sm"
                aria-label={t("pos.discount")}
              />
              <div className="flex overflow-hidden rounded-md ring-1 ring-stone-300">
                {(["percent", "amount"] as const).map((type) => (
                  <button
                    key={type}
                    onClick={() => setDiscount({ ...discount, type })}
                    className={cx(
                      "h-8 px-2 text-xs font-medium",
                      discount.type === type
                        ? "bg-stone-800 text-white"
                        : "bg-white text-stone-600",
                    )}
                  >
                    {t(type === "percent" ? "pos.discountPercent" : "pos.discountAmount")}
                  </button>
                ))}
              </div>
              <span className="num w-16 text-end text-red-600">
                {totals.discount > 0 ? `-${formatAmount(totals.discount, lang)}` : ""}
              </span>
            </div>
          </div>
          {isCashier && discount.value > 0 && (
            <p className="text-xs text-stone-500">
              {t("pos.cashierLimit", { percent: maxCashierDiscount })}
            </p>
          )}
          {totals.tax > 0 && (
            <div className="flex items-center justify-between">
              <span className="text-stone-600">{t("pos.tax")}</span>
              <span className="num">{formatAmount(totals.tax, lang)}</span>
            </div>
          )}
          <div className="flex items-end justify-between pt-1">
            <span className="text-base font-semibold">{t("pos.total")}</span>
            <span className="num text-2xl font-bold text-stone-900">
              {formatMoney(totals.total, lang)}
            </span>
          </div>
          <Button
            size="lg"
            className="w-full text-base"
            disabled={!cart.length}
            onClick={() => setPaying(true)}
          >
            {t("pos.pay")}
          </Button>
        </div>
      </section>

      {paying && (
        <PaymentDialog
          total={totals.total}
          busy={checkout.isPending}
          error={checkout.error}
          onCancel={() => {
            setPaying(false);
            checkout.reset();
            focusSearch();
          }}
          onComplete={(payments) => checkout.mutate(payments)}
        />
      )}

      {receipt && (
        <Modal
          open
          title={t("receipt.title")}
          onClose={newSale}
          footer={
            <>
              <Button
                variant="secondary"
                icon={<Printer className="size-4" />}
                onClick={() => window.print()}
              >
                {t("receipt.print")}
              </Button>
              <Button autoFocus onClick={newSale}>
                {t("receipt.newSale")}
              </Button>
            </>
          }
        >
          <div className="flex justify-center">
            <Receipt sale={receipt} settings={settings} />
          </div>
        </Modal>
      )}
    </div>
  );
}

function CategoryChip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={cx(
        "shrink-0 rounded-full px-3 py-1.5 text-sm font-medium ring-1",
        active
          ? "bg-stone-900 text-white ring-stone-900"
          : "bg-white text-stone-700 ring-stone-200 hover:bg-stone-50",
      )}
    >
      {children}
    </button>
  );
}

function QtyButton({
  label,
  onClick,
  children,
}: {
  label: string;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      aria-label={label}
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      className="grid size-7 place-items-center rounded-md bg-stone-100 text-stone-700 hover:bg-stone-200"
    >
      {children}
    </button>
  );
}
