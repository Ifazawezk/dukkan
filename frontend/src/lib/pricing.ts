// Live cart totals for the checkout screen. This mirrors app/services/pricing.py
// on the server (same rounding, same discount split) so the total on screen is
// the total that gets charged. The server still recalculates everything.

export interface PricingLine {
  price: number;
  quantity: number;
  taxRate: number;
}

export interface OrderDiscount {
  type: "percent" | "amount";
  value: number;
}

export interface CartTotals {
  subtotal: number;
  discount: number;
  tax: number;
  total: number;
  lineTotals: number[];
}

const toCents = (value: number) => Math.round(value * 100);
const fromCents = (cents: number) => cents / 100;

/** Split an amount over weights so the parts add up exactly (largest remainder). */
export function allocate(amount: number, weights: number[]): number[] {
  const totalWeight = weights.reduce((a, b) => a + b, 0);
  if (amount === 0 || totalWeight === 0) return weights.map(() => 0);
  const exact = weights.map((w) => amount * w);
  const parts = exact.map((e) => Math.floor(e / totalWeight));
  let leftover = amount - parts.reduce((a, b) => a + b, 0);
  const order = weights
    .map((_, i) => i)
    .sort((a, b) => (exact[b] % totalWeight) - (exact[a] % totalWeight) || a - b);
  for (const i of order) {
    if (leftover <= 0) break;
    parts[i] += 1;
    leftover -= 1;
  }
  return parts;
}

export function priceCart(lines: PricingLine[], discount: OrderDiscount | null): CartTotals {
  const gross = lines.map((line) => toCents(line.price) * line.quantity);
  const base = gross.reduce((a, b) => a + b, 0);
  let off = 0;
  if (discount && discount.value > 0) {
    off =
      discount.type === "percent"
        ? Math.round((base * discount.value) / 100)
        : toCents(discount.value);
  }
  off = Math.min(Math.max(off, 0), base);
  const shares = allocate(off, gross);

  let tax = 0;
  const lineTotals = lines.map((line, i) => {
    const net = gross[i] - shares[i];
    const lineTax = Math.round((net * line.taxRate) / 100);
    tax += lineTax;
    return fromCents(net + lineTax);
  });

  return {
    subtotal: fromCents(base),
    discount: fromCents(off),
    tax: fromCents(tax),
    total: fromCents(base - off + tax),
    lineTotals,
  };
}

/** Banknotes a customer is likely to hand over for this total. */
export function suggestedCash(total: number): number[] {
  const notes = [1, 5, 10, 50, 100, 200, 500];
  const options = new Set<number>();
  for (const note of notes) {
    if (note >= 5) {
      const rounded = Math.ceil(total / note) * note;
      if (rounded > total) options.add(rounded);
    }
  }
  return [...options].sort((a, b) => a - b).slice(0, 4);
}
