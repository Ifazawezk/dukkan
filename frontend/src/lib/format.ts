import type { Lang } from "../i18n";

// Arabic UI with Latin digits, which is what most shops in Qatar print on receipts.
const locales: Record<Lang, string> = { en: "en-QA", ar: "ar-QA-u-nu-latn" };

const moneyFormats = new Map<string, Intl.NumberFormat>();

export function formatMoney(value: number | null | undefined, lang: Lang, currency = "QAR") {
  if (value === null || value === undefined) return "";
  const key = `${lang}-${currency}`;
  let format = moneyFormats.get(key);
  if (!format) {
    format = new Intl.NumberFormat(locales[lang], { style: "currency", currency });
    moneyFormats.set(key, format);
  }
  return format.format(value);
}

/** Plain number with two decimals, for tables where the currency is in the header. */
export function formatAmount(value: number | null | undefined, lang: Lang) {
  if (value === null || value === undefined) return "";
  return new Intl.NumberFormat(locales[lang], {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatNumber(value: number, lang: Lang) {
  return new Intl.NumberFormat(locales[lang]).format(value);
}

export function formatDate(value: string, lang: Lang) {
  return new Intl.DateTimeFormat(locales[lang], { dateStyle: "medium" }).format(new Date(value));
}

export function formatDateTime(value: string, lang: Lang) {
  return new Intl.DateTimeFormat(locales[lang], {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function marginPercent(price: number, cost: number | null) {
  if (cost === null || price <= 0) return null;
  return ((price - cost) / price) * 100;
}

/** Today's date as YYYY-MM-DD in the browser's time zone. */
export function isoDate(date: Date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}
