// Shapes returned by the API. Money is a number in QAR with two decimals.

export type Role = "owner" | "manager" | "cashier";

export interface Page<T> {
  items: T[];
  total: number;
}

export interface User {
  id: number;
  username: string;
  full_name: string;
  role: Role;
  branch_id: number | null;
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface TokenOut {
  access_token: string;
  token_type: string;
  expires_at: string;
  user: User;
}

export interface Branch {
  id: number;
  code: string;
  name: string;
  name_ar: string;
  address: string;
  phone: string;
  is_active: boolean;
}

export interface ShopSettings {
  shop_name: string;
  shop_name_ar: string;
  currency: string;
  timezone: string;
  default_tax_rate: number;
  allow_negative_stock: boolean;
  max_cashier_discount_percent: number;
  default_low_stock_threshold: number;
  receipt_footer: string;
  receipt_footer_ar: string;
}

export interface Category {
  id: number;
  name: string;
  name_ar: string;
  product_count: number;
}

export interface Product {
  id: number;
  sku: string;
  barcode: string | null;
  name: string;
  name_ar: string;
  category_id: number | null;
  unit: string;
  cost_price: number | null;
  sale_price: number;
  tax_rate: number | null;
  low_stock_threshold: number;
  is_active: boolean;
  stock: number | null;
}

export interface ProductInput {
  sku: string;
  barcode: string | null;
  name: string;
  name_ar: string;
  category_id: number | null;
  unit: string;
  cost_price: number;
  sale_price: number;
  tax_rate: number | null;
  low_stock_threshold: number | null;
  is_active: boolean;
}

export type PaymentMethod = "cash" | "card" | "wallet";
export type SaleStatus = "completed" | "partially_refunded" | "refunded";

export interface SaleItem {
  id: number;
  product_id: number;
  sku: string;
  product_name: string;
  product_name_ar: string;
  quantity: number;
  unit_price: number;
  line_discount: number;
  order_discount: number;
  tax_rate: number;
  tax_amount: number;
  line_total: number;
  quantity_returned: number;
  refunded_amount: number;
}

export interface Payment {
  id: number;
  method: PaymentMethod;
  amount: number;
  reference: string;
}

export interface ReturnItem {
  id: number;
  sale_item_id: number;
  product_id: number;
  product_name: string;
  quantity: number;
  refund_amount: number;
  restocked: boolean;
}

export interface SaleReturn {
  id: number;
  return_no: string;
  sale_id: number;
  receipt_no: string;
  branch_id: number;
  user_id: number;
  user_name: string;
  business_date: string;
  created_at: string;
  reason: string;
  refund_method: PaymentMethod;
  refund_total: number;
  items: ReturnItem[];
}

export interface SaleSummary {
  id: number;
  receipt_no: string;
  branch_id: number;
  cashier_id: number;
  cashier_name: string;
  business_date: string;
  created_at: string;
  status: SaleStatus;
  item_count: number;
  total: number;
}

export interface Sale extends SaleSummary {
  branch_name: string;
  subtotal: number;
  discount_total: number;
  tax_total: number;
  amount_tendered: number;
  change_due: number;
  customer_name: string;
  customer_phone: string;
  note: string;
  refunded_total: number;
  items: SaleItem[];
  payments: Payment[];
  returns: SaleReturn[];
}

export interface CheckoutInput {
  branch_id: number | null;
  items: { product_id: number; quantity: number }[];
  discount: { type: "percent" | "amount"; value: number } | null;
  payments: { method: PaymentMethod; amount: number; reference?: string }[];
}

export interface StockRow {
  product_id: number;
  sku: string;
  barcode: string | null;
  name: string;
  name_ar: string;
  category_id: number | null;
  unit: string;
  quantity: number;
  low_stock_threshold: number;
  is_low: boolean;
  sale_price: number;
  cost_price: number | null;
  stock_value: number | null;
}

export type MovementKind = "purchase" | "sale" | "return" | "adjustment";
export type AdjustmentReason =
  "opening_stock" | "count_correction" | "damaged" | "expired" | "lost" | "internal_use" | "other";

export interface Movement {
  id: number;
  product_id: number;
  sku: string;
  product_name: string;
  branch_id: number;
  kind: MovementKind;
  quantity_change: number;
  balance_after: number;
  unit_cost: number | null;
  reason: AdjustmentReason | null;
  reference_type: string | null;
  reference_id: number | null;
  note: string;
  user_id: number | null;
  user_name: string | null;
  created_at: string;
}

export interface LedgerCheck {
  ok: boolean;
  pairs_checked: number;
  problems: { product_id: number; branch_id: number; problem: string }[];
}

export interface Supplier {
  id: number;
  name: string;
  contact_name: string;
  phone: string;
  email: string;
  address: string;
  notes: string;
  is_active: boolean;
}

export type PurchaseOrderStatus =
  "draft" | "ordered" | "partially_received" | "received" | "cancelled";

export interface PurchaseOrderSummary {
  id: number;
  number: string;
  supplier_id: number;
  supplier_name: string;
  branch_id: number;
  status: PurchaseOrderStatus;
  expected_date: string | null;
  created_at: string;
  item_count: number;
  total_cost: number;
}

export interface PurchaseItem {
  id: number;
  product_id: number;
  sku: string;
  product_name: string;
  product_name_ar: string;
  quantity_ordered: number;
  quantity_received: number;
  unit_cost: number;
  line_total: number;
}

export interface PurchaseOrder extends PurchaseOrderSummary {
  notes: string;
  ordered_at: string | null;
  received_at: string | null;
  cancelled_at: string | null;
  items: PurchaseItem[];
}

export interface ReportSummary {
  date_from: string;
  date_to: string;
  sales_total: number;
  sales_count: number;
  average_basket: number;
  refunds: number;
  net_sales: number;
  gross_profit: number;
  margin_percent: number;
  today_sales_total: number;
  today_sales_count: number;
  low_stock_items: number;
  stock_value: number;
}

export interface DailySalesRow {
  date: string;
  sales_count: number;
  gross_sales: number;
  discounts: number;
  tax: number;
  sales_total: number;
  refunds: number;
  net_sales: number;
  revenue: number;
  cash: number;
  card: number;
  wallet: number;
  cost_of_goods: number;
  gross_profit: number;
}

export interface ProductSalesRow {
  product_id: number;
  sku: string;
  name: string;
  name_ar: string;
  units_sold: number;
  revenue: number;
  cost: number;
  profit: number;
}

export interface CategoryProfitRow {
  category_id: number | null;
  category: string;
  category_ar: string;
  units_sold: number;
  revenue: number;
  cost: number;
  profit: number;
  margin_percent: number;
}

export interface SlowMoverRow {
  product_id: number;
  sku: string;
  name: string;
  name_ar: string;
  on_hand: number;
  units_sold: number;
  last_sold: string | null;
  days_since_last_sale: number | null;
  stock_value: number;
}

export interface StockValuationRow {
  category_id: number | null;
  category: string;
  category_ar: string;
  products: number;
  units: number;
  cost_value: number;
  retail_value: number;
  potential_profit: number;
}

export interface CashierRow {
  cashier_id: number;
  cashier_name: string;
  sales_count: number;
  items_sold: number;
  sales_total: number;
  average_basket: number;
  discounts_given: number;
  refunded: number;
}
