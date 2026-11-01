import { Banknote, CreditCard, Smartphone, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import type { PaymentMethod } from "../../api/types";
import { Button, ErrorText, Modal, cx } from "../../components/ui";
import { useI18n } from "../../i18n";
import { formatMoney } from "../../lib/format";
import { suggestedCash } from "../../lib/pricing";

export interface PaymentLine {
  method: PaymentMethod;
  amount: number;
  reference: string;
}

const METHODS: { method: PaymentMethod; icon: typeof Banknote; key: string }[] = [
  { method: "cash", icon: Banknote, key: "1" },
  { method: "card", icon: CreditCard, key: "2" },
  { method: "wallet", icon: Smartphone, key: "3" },
];

const round = (value: number) => Math.round(value * 100) / 100;

export function PaymentDialog({
  total,
  busy,
  error,
  onCancel,
  onComplete,
}: {
  total: number;
  busy: boolean;
  error: unknown;
  onCancel: () => void;
  onComplete: (payments: PaymentLine[]) => void;
}) {
  const { t, lang } = useI18n();
  const [payments, setPayments] = useState<PaymentLine[]>([]);
  const [method, setMethod] = useState<PaymentMethod>("cash");
  const [reference, setReference] = useState("");
  const paid = round(payments.reduce((sum, p) => sum + p.amount, 0));
  const remaining = round(Math.max(total - paid, 0));
  const change = round(Math.max(paid - total, 0));
  const [amount, setAmount] = useState(remaining.toFixed(2));
  const amountRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setAmount(remaining.toFixed(2));
    amountRef.current?.select();
  }, [remaining]);

  function finish(lines: PaymentLine[]) {
    const covered = round(lines.reduce((sum, p) => sum + p.amount, 0)) >= total;
    if (covered) onComplete(lines);
  }

  function add(value: number, how: PaymentMethod = method) {
    if (!(value > 0)) return;
    // Card and wallet are charged for exact amounts; only cash can be more than due.
    const capped = how === "cash" ? value : Math.min(value, remaining);
    const next = [...payments, { method: how, amount: round(capped), reference }];
    setPayments(next);
    setReference("");
    finish(next);
  }

  function onKeyDown(event: KeyboardEvent) {
    const choice = METHODS.find((m) => m.key === event.key && event.altKey);
    if (choice) {
      event.preventDefault();
      setMethod(choice.method);
    }
  }

  return (
    <Modal
      open
      title={t("pay.title")}
      onClose={onCancel}
      footer={
        <>
          <Button variant="secondary" onClick={onCancel}>
            {t("common.cancel")}
          </Button>
          <Button
            disabled={busy || (total > 0 && paid < total)}
            onClick={() => onComplete(payments)}
          >
            {t("pay.complete")}
          </Button>
        </>
      }
    >
      <div onKeyDown={onKeyDown} className="space-y-4">
        <div className="rounded-xl bg-stone-900 px-4 py-3 text-white">
          <div className="text-xs uppercase tracking-wide text-stone-400">{t("pay.due")}</div>
          <div className="num text-3xl font-semibold">{formatMoney(total, lang)}</div>
        </div>

        <div className="grid grid-cols-3 gap-2">
          {METHODS.map(({ method: m, icon: Icon }) => (
            <button
              key={m}
              onClick={() => setMethod(m)}
              className={cx(
                "flex flex-col items-center gap-1 rounded-xl border px-3 py-3 text-sm font-medium",
                method === m
                  ? "border-brand-700 bg-brand-50 text-brand-800"
                  : "border-stone-200 hover:bg-stone-50",
              )}
            >
              <Icon className="size-5" />
              {t(`pay.${m}`)}
            </button>
          ))}
        </div>

        {remaining > 0 && (
          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault();
              add(Number(amount));
            }}
          >
            <div className="flex gap-2">
              <input
                ref={amountRef}
                autoFocus
                type="number"
                step="0.01"
                min="0"
                inputMode="decimal"
                aria-label={t("pay.amount")}
                className="num h-12 w-full rounded-lg border border-stone-300 px-3 text-lg focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-600/20"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
              />
              <Button type="submit" size="lg" variant="secondary">
                {t("pay.add")}
              </Button>
            </div>
            {method !== "cash" && (
              <input
                className="h-10 w-full rounded-lg border border-stone-300 px-3 text-sm"
                placeholder={t("pay.reference")}
                value={reference}
                onChange={(e) => setReference(e.target.value)}
              />
            )}
            {method === "cash" && (
              <div className="flex flex-wrap gap-2">
                <Button size="sm" variant="secondary" onClick={() => add(remaining, "cash")}>
                  {t("pay.exact")}
                </Button>
                {suggestedCash(remaining).map((note) => (
                  <Button
                    key={note}
                    size="sm"
                    variant="secondary"
                    onClick={() => add(note, "cash")}
                  >
                    {note}
                  </Button>
                ))}
              </div>
            )}
          </form>
        )}

        {payments.length > 0 && (
          <ul className="divide-y divide-stone-100 rounded-lg ring-1 ring-stone-200">
            {payments.map((p, i) => (
              <li key={i} className="flex items-center justify-between px-3 py-2 text-sm">
                <span>
                  {t(`pay.${p.method}`)}
                  {p.reference && <span className="ms-2 text-stone-500">{p.reference}</span>}
                </span>
                <span className="flex items-center gap-2">
                  <span className="num">{formatMoney(p.amount, lang)}</span>
                  <button
                    className="rounded p-1 text-stone-400 hover:bg-stone-100 hover:text-red-600"
                    onClick={() => setPayments(payments.filter((_, j) => j !== i))}
                    aria-label={t("common.delete")}
                  >
                    <Trash2 className="size-4" />
                  </button>
                </span>
              </li>
            ))}
          </ul>
        )}

        <dl className="grid grid-cols-3 gap-2 text-center text-sm">
          <div className="rounded-lg bg-stone-50 p-2">
            <dt className="text-stone-500">{t("pay.paid")}</dt>
            <dd className="num font-semibold">{formatMoney(paid, lang)}</dd>
          </div>
          <div className="rounded-lg bg-stone-50 p-2">
            <dt className="text-stone-500">{t("pay.remaining")}</dt>
            <dd className="num font-semibold">{formatMoney(remaining, lang)}</dd>
          </div>
          <div className="rounded-lg bg-emerald-50 p-2">
            <dt className="text-emerald-700">{t("pay.change")}</dt>
            <dd className="num font-semibold text-emerald-800">{formatMoney(change, lang)}</dd>
          </div>
        </dl>

        <ErrorText error={error} />
      </div>
    </Modal>
  );
}
