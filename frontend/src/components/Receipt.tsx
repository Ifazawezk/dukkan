import type { Sale, ShopSettings } from "../api/types";
import { useI18n } from "../i18n";
import { formatAmount, formatDateTime } from "../lib/format";

/** Printable receipt with both English and Arabic shop details. */
export function Receipt({ sale, settings }: { sale: Sale; settings?: ShopSettings }) {
  const { t, lang, pick } = useI18n();
  const money = (value: number) => formatAmount(value, lang);
  const row = "flex justify-between gap-4";

  return (
    <div className="print-area mx-auto max-w-xs bg-white font-mono text-[13px] leading-5 text-stone-900">
      <div className="text-center">
        {settings && <div className="text-base font-bold">{settings.shop_name}</div>}
        {settings?.shop_name_ar && (
          <div className="font-sans text-base font-bold" dir="rtl">
            {settings.shop_name_ar}
          </div>
        )}
        <div>{sale.branch_name}</div>
      </div>
      <hr className="my-2 border-dashed border-stone-400" />
      <div className={row}>
        <span>{t("receipt.no")}</span>
        <span>{sale.receipt_no}</span>
      </div>
      <div className={row}>
        <span>{t("receipt.date")}</span>
        <span>{formatDateTime(sale.created_at, lang, settings?.timezone)}</span>
      </div>
      <div className={row}>
        <span>{t("receipt.cashier")}</span>
        <span>{sale.cashier_name}</span>
      </div>
      <hr className="my-2 border-dashed border-stone-400" />
      {sale.items.map((item) => (
        <div key={item.id} className="mb-1">
          <div className="font-sans">{pick(item.product_name, item.product_name_ar)}</div>
          <div className={`${row} text-stone-600`}>
            <span>
              {item.quantity} x {money(item.unit_price)}
            </span>
            <span className="text-stone-900">{money(item.unit_price * item.quantity)}</span>
          </div>
        </div>
      ))}
      <hr className="my-2 border-dashed border-stone-400" />
      <div className={row}>
        <span>{t("pos.subtotal")}</span>
        <span>{money(sale.subtotal)}</span>
      </div>
      {sale.discount_total > 0 && (
        <div className={row}>
          <span>{t("pos.discount")}</span>
          <span>-{money(sale.discount_total)}</span>
        </div>
      )}
      {sale.tax_total > 0 && (
        <div className={row}>
          <span>{t("pos.tax")}</span>
          <span>{money(sale.tax_total)}</span>
        </div>
      )}
      <div className={`${row} text-base font-bold`}>
        <span>
          {t("pos.total")} {settings?.currency ?? "QAR"}
        </span>
        <span>{money(sale.total)}</span>
      </div>
      {sale.payments.map((payment) => (
        <div key={payment.id} className={row}>
          <span>{t(`pay.${payment.method}`)}</span>
          <span>{money(payment.amount)}</span>
        </div>
      ))}
      {sale.change_due > 0 && (
        <>
          <div className={row}>
            <span>{t("receipt.tendered")}</span>
            <span>{money(sale.amount_tendered)}</span>
          </div>
          <div className={row}>
            <span>{t("pay.change")}</span>
            <span>{money(sale.change_due)}</span>
          </div>
        </>
      )}
      {sale.refunded_total > 0 && (
        <div className={row}>
          <span>{t("receipt.refunded")}</span>
          <span>-{money(sale.refunded_total)}</span>
        </div>
      )}
      <hr className="my-2 border-dashed border-stone-400" />
      <div className="text-center font-sans text-stone-600">
        {settings?.receipt_footer && <div>{settings.receipt_footer}</div>}
        {settings?.receipt_footer_ar && <div dir="rtl">{settings.receipt_footer_ar}</div>}
      </div>
    </div>
  );
}
