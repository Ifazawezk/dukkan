from datetime import date

from app.schemas.common import Money, Schema


class SummaryOut(Schema):
    date_from: date
    date_to: date
    sales_total: Money
    sales_count: int
    average_basket: Money
    refunds: Money
    net_sales: Money
    gross_profit: Money
    margin_percent: Money
    today_sales_total: Money
    today_sales_count: int
    low_stock_items: int
    stock_value: Money


class DailySalesRow(Schema):
    date: date
    sales_count: int
    gross_sales: Money
    discounts: Money
    tax: Money
    sales_total: Money
    refunds: Money
    net_sales: Money
    revenue: Money
    cash: Money
    card: Money
    wallet: Money
    cost_of_goods: Money
    gross_profit: Money


class ProductSalesRow(Schema):
    product_id: int
    sku: str
    name: str
    name_ar: str
    units_sold: int
    revenue: Money
    cost: Money
    profit: Money


class CategoryProfitRow(Schema):
    category_id: int | None
    category: str
    category_ar: str
    units_sold: int
    revenue: Money
    cost: Money
    profit: Money
    margin_percent: Money


class SlowMoverRow(Schema):
    product_id: int
    sku: str
    name: str
    name_ar: str
    on_hand: int
    units_sold: int
    last_sold: date | None
    days_since_last_sale: int | None
    stock_value: Money


class StockValuationRow(Schema):
    category_id: int | None
    category: str
    category_ar: str
    products: int
    units: int
    cost_value: Money
    retail_value: Money
    potential_profit: Money


class CashierRow(Schema):
    cashier_id: int
    cashier_name: str
    sales_count: int
    items_sold: int
    sales_total: Money
    average_basket: Money
    discounts_given: Money
    refunded: Money
