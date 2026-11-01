"""Reports.

All sums are done in SQL on the raw integer dirham columns, then turned back
into Decimals, so totals are exact and the same on SQLite and PostgreSQL.

Two ways of counting returns are used, on purpose:

* The daily sales report is a cash view. A refund counts on the day it was
  paid out, like the money in the till.
* Product, category and cashier reports look at what was really sold. A sale
  stays on its own date and any later returns of it are netted off.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import BigInteger, Select, func, select, type_coerce
from sqlalchemy.orm import Session

from app.models import (
    Branch,
    Category,
    Payment,
    PaymentMethod,
    Product,
    Sale,
    SaleItem,
    SaleReturn,
    SaleReturnItem,
    StockLevel,
    User,
)
from app.money import ZERO, q
from app.services.pricing import from_cents


def cents(column):
    """Read a money column as its stored integer so SQL can add it up."""
    return type_coerce(column, BigInteger)


def money(value) -> Decimal:
    return from_cents(int(value or 0))


def percent(part: Decimal, whole: Decimal) -> Decimal:
    return q(part / whole * 100) if whole else ZERO


@dataclass(frozen=True)
class Period:
    date_from: date
    date_to: date
    branch_id: int | None = None

    def days(self) -> list[date]:
        count = (self.date_to - self.date_from).days + 1
        return [self.date_from + timedelta(days=i) for i in range(count)]


def _in_period(stmt: Select, period: Period, model=Sale) -> Select:
    stmt = stmt.where(model.business_date.between(period.date_from, period.date_to))
    if period.branch_id is not None:
        stmt = stmt.where(model.branch_id == period.branch_id)
    return stmt


# Net figures for a sale line once its returns are taken off.
_returned_cost = (
    select(
        SaleReturnItem.sale_item_id,
        func.sum(cents(SaleReturnItem.cost_amount)).label("cost"),
    )
    .group_by(SaleReturnItem.sale_item_id)
    .subquery()
)
_net_units = SaleItem.quantity - SaleItem.quantity_returned
_net_revenue = (
    cents(SaleItem.line_total)
    - cents(SaleItem.tax_amount)
    - (cents(SaleItem.refunded_amount) - cents(SaleItem.refunded_tax))
)
_net_cost = cents(SaleItem.unit_cost) * SaleItem.quantity - func.coalesce(_returned_cost.c.cost, 0)


def _net_lines(period: Period, *columns) -> Select:
    stmt = (
        select(*columns)
        .select_from(SaleItem)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .outerjoin(_returned_cost, _returned_cost.c.sale_item_id == SaleItem.id)
    )
    return _in_period(stmt, period)


def daily_sales(db: Session, period: Period) -> list[dict]:
    rows = {
        day: {
            "date": day,
            "sales_count": 0,
            "gross_sales": ZERO,
            "discounts": ZERO,
            "tax": ZERO,
            "sales_total": ZERO,
            "refunds": ZERO,
            "net_sales": ZERO,
            "revenue": ZERO,
            "cash": ZERO,
            "card": ZERO,
            "wallet": ZERO,
            "cost_of_goods": ZERO,
            "gross_profit": ZERO,
        }
        for day in period.days()
    }

    totals = db.execute(
        _in_period(
            select(
                Sale.business_date,
                func.count(Sale.id),
                func.sum(cents(Sale.subtotal)),
                func.sum(cents(Sale.discount_total)),
                func.sum(cents(Sale.tax_total)),
                func.sum(cents(Sale.total)),
            ).group_by(Sale.business_date),
            period,
        )
    )
    for day, count, gross, discounts, tax, total in totals:
        row = rows[day]
        row["sales_count"] = count
        row["gross_sales"] = money(gross)
        row["discounts"] = money(discounts)
        row["tax"] = money(tax)
        row["sales_total"] = money(total)

    payments = db.execute(
        _in_period(
            select(Sale.business_date, Payment.method, func.sum(cents(Payment.amount)))
            .join(Payment, Payment.sale_id == Sale.id)
            .group_by(Sale.business_date, Payment.method),
            period,
        )
    )
    for day, method, amount in payments:
        rows[day][PaymentMethod(method).value] = money(amount)

    revenue: dict[date, int] = defaultdict(int)
    cost: dict[date, int] = defaultdict(int)
    lines = db.execute(
        _in_period(
            select(
                Sale.business_date,
                func.sum(cents(SaleItem.line_total) - cents(SaleItem.tax_amount)),
                func.sum(cents(SaleItem.unit_cost) * SaleItem.quantity),
            )
            .join(SaleItem, SaleItem.sale_id == Sale.id)
            .group_by(Sale.business_date),
            period,
        )
    )
    for day, line_revenue, line_cost in lines:
        revenue[day] += int(line_revenue or 0)
        cost[day] += int(line_cost or 0)

    refunds = db.execute(
        _in_period(
            select(
                SaleReturn.business_date,
                func.sum(cents(SaleReturnItem.refund_amount)),
                func.sum(cents(SaleReturnItem.refund_amount) - cents(SaleReturnItem.tax_amount)),
                func.sum(cents(SaleReturnItem.cost_amount)),
            )
            .join(SaleReturnItem, SaleReturnItem.return_id == SaleReturn.id)
            .group_by(SaleReturn.business_date),
            period,
            model=SaleReturn,
        )
    )
    for day, refunded, refunded_revenue, restocked_cost in refunds:
        rows[day]["refunds"] = money(refunded)
        revenue[day] -= int(refunded_revenue or 0)
        cost[day] -= int(restocked_cost or 0)

    for day, row in rows.items():
        row["net_sales"] = row["sales_total"] - row["refunds"]
        row["revenue"] = money(revenue[day])
        row["cost_of_goods"] = money(cost[day])
        row["gross_profit"] = money(revenue[day] - cost[day])
    return list(rows.values())


def product_sales(
    db: Session, period: Period, order_by: str = "revenue", limit: int = 10
) -> list[dict]:
    units = func.sum(_net_units).label("units")
    revenue = func.sum(_net_revenue).label("revenue")
    stmt = _net_lines(
        period,
        Product.id,
        Product.sku,
        Product.name,
        Product.name_ar,
        units,
        revenue,
        func.sum(_net_cost),
    ).join(Product, Product.id == SaleItem.product_id)
    stmt = stmt.group_by(Product.id, Product.sku, Product.name, Product.name_ar)
    stmt = stmt.order_by((units if order_by == "quantity" else revenue).desc(), Product.name)
    rows = []
    for product_id, sku, name, name_ar, sold, line_revenue, line_cost in db.execute(
        stmt.limit(limit)
    ):
        revenue_value, cost_value = money(line_revenue), money(line_cost)
        rows.append(
            {
                "product_id": product_id,
                "sku": sku,
                "name": name,
                "name_ar": name_ar,
                "units_sold": int(sold or 0),
                "revenue": revenue_value,
                "cost": cost_value,
                "profit": revenue_value - cost_value,
            }
        )
    return rows


def profit_by_category(db: Session, period: Period) -> list[dict]:
    stmt = (
        _net_lines(
            period,
            Category.id,
            Category.name,
            Category.name_ar,
            func.sum(_net_units),
            func.sum(_net_revenue),
            func.sum(_net_cost),
        )
        .join(Product, Product.id == SaleItem.product_id)
        .outerjoin(Category, Category.id == Product.category_id)
        .group_by(Category.id, Category.name, Category.name_ar)
    )
    rows = []
    for category_id, name, name_ar, units, line_revenue, line_cost in db.execute(stmt):
        revenue_value, cost_value = money(line_revenue), money(line_cost)
        profit = revenue_value - cost_value
        rows.append(
            {
                "category_id": category_id,
                "category": name or "Uncategorised",
                "category_ar": name_ar or "بدون فئة",
                "units_sold": int(units or 0),
                "revenue": revenue_value,
                "cost": cost_value,
                "profit": profit,
                "margin_percent": percent(profit, revenue_value),
            }
        )
    rows.sort(key=lambda r: r["profit"], reverse=True)
    return rows


def _on_hand(db: Session, branch_id: int | None) -> dict[int, int]:
    stmt = select(StockLevel.product_id, func.sum(StockLevel.quantity)).group_by(
        StockLevel.product_id
    )
    if branch_id is not None:
        stmt = stmt.where(StockLevel.branch_id == branch_id)
    return {product_id: int(qty or 0) for product_id, qty in db.execute(stmt)}


def slow_movers(
    db: Session, as_of: date, days: int, max_units: int, branch_id: int | None = None
) -> list[dict]:
    """Products with stock on the shelf that sold max_units or fewer in the last `days` days."""
    since = as_of - timedelta(days=days - 1)
    recent = _net_lines(
        Period(since, as_of, branch_id), SaleItem.product_id, func.sum(_net_units)
    ).group_by(SaleItem.product_id)
    sold = {product_id: int(units or 0) for product_id, units in db.execute(recent)}

    last_sale_stmt = (
        select(SaleItem.product_id, func.max(Sale.business_date))
        .join(Sale, Sale.id == SaleItem.sale_id)
        .where(Sale.business_date <= as_of)
        .group_by(SaleItem.product_id)
    )
    if branch_id is not None:
        last_sale_stmt = last_sale_stmt.where(Sale.branch_id == branch_id)
    last_sold = dict(db.execute(last_sale_stmt).all())

    on_hand = _on_hand(db, branch_id)
    rows = []
    for product in db.scalars(select(Product).where(Product.is_active.is_(True))):
        quantity = on_hand.get(product.id, 0)
        units = sold.get(product.id, 0)
        if quantity <= 0 or units > max_units:
            continue
        last = last_sold.get(product.id)
        rows.append(
            {
                "product_id": product.id,
                "sku": product.sku,
                "name": product.name,
                "name_ar": product.name_ar,
                "on_hand": quantity,
                "units_sold": units,
                "last_sold": last,
                "days_since_last_sale": (as_of - last).days if last else None,
                "stock_value": product.cost_price * quantity,
            }
        )
    rows.sort(key=lambda r: (r["units_sold"], -r["stock_value"]))
    return rows


def stock_valuation(db: Session, branch_id: int | None = None) -> list[dict]:
    stmt = (
        select(
            Category.id,
            Category.name,
            Category.name_ar,
            func.count(func.distinct(Product.id)),
            func.sum(StockLevel.quantity),
            func.sum(cents(Product.cost_price) * StockLevel.quantity),
            func.sum(cents(Product.sale_price) * StockLevel.quantity),
        )
        .select_from(StockLevel)
        .join(Product, Product.id == StockLevel.product_id)
        .outerjoin(Category, Category.id == Product.category_id)
        .where(StockLevel.quantity > 0, Product.is_active.is_(True))
        .group_by(Category.id, Category.name, Category.name_ar)
    )
    if branch_id is not None:
        stmt = stmt.where(StockLevel.branch_id == branch_id)
    rows = []
    for category_id, name, name_ar, products, units, cost_value, retail_value in db.execute(stmt):
        cost_amount, retail_amount = money(cost_value), money(retail_value)
        rows.append(
            {
                "category_id": category_id,
                "category": name or "Uncategorised",
                "category_ar": name_ar or "بدون فئة",
                "products": products,
                "units": int(units or 0),
                "cost_value": cost_amount,
                "retail_value": retail_amount,
                "potential_profit": retail_amount - cost_amount,
            }
        )
    rows.sort(key=lambda r: r["cost_value"], reverse=True)
    return rows


def cashier_performance(db: Session, period: Period) -> list[dict]:
    totals = db.execute(
        _in_period(
            select(
                User.id,
                User.full_name,
                func.count(Sale.id),
                func.sum(cents(Sale.total)),
                func.sum(cents(Sale.discount_total)),
                func.sum(cents(Sale.refunded_total)),
            )
            .join(User, User.id == Sale.cashier_id)
            .group_by(User.id, User.full_name),
            period,
        )
    )
    items = dict(
        db.execute(
            _in_period(
                select(Sale.cashier_id, func.sum(SaleItem.quantity))
                .join(SaleItem, SaleItem.sale_id == Sale.id)
                .group_by(Sale.cashier_id),
                period,
            )
        ).all()
    )
    rows = []
    for user_id, name, count, total, discounts, refunded in totals:
        sales_total = money(total)
        rows.append(
            {
                "cashier_id": user_id,
                "cashier_name": name,
                "sales_count": count,
                "items_sold": int(items.get(user_id) or 0),
                "sales_total": sales_total,
                "average_basket": q(sales_total / count) if count else ZERO,
                "discounts_given": money(discounts),
                "refunded": money(refunded),
            }
        )
    rows.sort(key=lambda r: r["sales_total"], reverse=True)
    return rows


def low_stock_count(db: Session, branch_id: int | None = None) -> int:
    """Active products at or below their threshold, in the branch or in any branch."""
    if branch_id is None:
        branch_ids = list(db.scalars(select(Branch.id).where(Branch.is_active.is_(True))))
    else:
        branch_ids = [branch_id]
    stock = {branch: _on_hand(db, branch) for branch in branch_ids}
    products = db.execute(
        select(Product.id, Product.low_stock_threshold).where(Product.is_active.is_(True))
    ).all()
    return sum(
        1
        for product_id, threshold in products
        if any(stock[branch].get(product_id, 0) <= threshold for branch in branch_ids)
    )


def summary(db: Session, period: Period, today: date) -> dict:
    days = daily_sales(db, period)
    sales_total = sum((d["sales_total"] for d in days), ZERO)
    count = sum(d["sales_count"] for d in days)
    refunds = sum((d["refunds"] for d in days), ZERO)
    profit = sum((d["gross_profit"] for d in days), ZERO)
    revenue = sum((d["revenue"] for d in days), ZERO)
    today_row = daily_sales(db, Period(today, today, period.branch_id))[0]
    valuation = stock_valuation(db, period.branch_id)
    return {
        "date_from": period.date_from,
        "date_to": period.date_to,
        "sales_total": sales_total,
        "sales_count": count,
        "average_basket": q(sales_total / count) if count else ZERO,
        "refunds": refunds,
        "net_sales": sales_total - refunds,
        "gross_profit": profit,
        "margin_percent": percent(profit, revenue),
        "today_sales_total": today_row["sales_total"],
        "today_sales_count": today_row["sales_count"],
        "low_stock_items": low_stock_count(db, period.branch_id),
        "stock_value": sum((row["cost_value"] for row in valuation), ZERO),
    }
