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
