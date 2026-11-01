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
