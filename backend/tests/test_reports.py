"""Reports, checked against a small shop history with hand-worked numbers.

1 Oct  sale A (cashier): 2 milk at 6.50 + 3 chips at 2.00, cash      = 19.00
                         cost 2 x 5.00 + 3 x 1.00 = 13.00, profit       =  6.00
2 Oct  sale B (manager): 1 milk at 6.50 less 10%, card               =  5.85
                         cost 5.00, profit                              =  0.85
2 Oct  return of 1 chips from sale A, back on the shelf, refund 2.00, cost 1.00
"""

import csv
import io
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.models import Category, PaymentMethod
from app.services import pricing, reports, returns, sales
from tests.helpers import give_stock, make_product

DAY1 = datetime(2026, 10, 1, 7, 0, tzinfo=UTC)  # 10:00 in Doha
DAY2 = datetime(2026, 10, 2, 15, 0, tzinfo=UTC)
PARAMS = {"date_from": "2026-10-01", "date_to": "2026-10-03"}


@pytest.fixture
def history(db, users, branch):
    dairy = Category(name="Dairy", name_ar="ألبان")
    snacks = Category(name="Snacks", name_ar="وجبات خفيفة")
    db.add_all([dairy, snacks])
    db.commit()
    milk = make_product(db, name="Milk", sale_price="6.50", cost_price="5.00", category_id=dairy.id)
    chips = make_product(
        db, name="Chips", sale_price="2.00", cost_price="1.00", category_id=snacks.id
    )
    charger = make_product(db, name="Charger", sale_price="35.00", cost_price="30.00")
    for product, qty in [(milk, 20), (chips, 20), (charger, 5)]:
        give_stock(db, product, branch.id, qty, users["manager"])

    sale_a = sales.checkout(
        db,
        user=users["cashier"],
        branch_id=branch.id,
        lines=[sales.CartLine(milk.id, 2), sales.CartLine(chips.id, 3)],
        payments=[pricing.PaymentInput(PaymentMethod.cash, Decimal("20.00"))],
        at=DAY1,
    )
    sales.checkout(
        db,
        user=users["manager"],
        branch_id=branch.id,
        lines=[sales.CartLine(milk.id, 1)],
        payments=[pricing.PaymentInput(PaymentMethod.card, Decimal("5.85"))],
        order_discount=sales.OrderDiscount("percent", Decimal("10")),
        at=DAY2,
    )
    db.flush()
    chips_line = next(i for i in sale_a.items if i.product_id == chips.id)
    returns.process_return(
        db,
        sale=sale_a,
        lines=[returns.ReturnLine(chips_line.id, 1)],
        user=users["manager"],
        at=DAY2,
    )
    db.commit()
    return {"milk": milk, "chips": chips, "charger": charger}


def get(client, auth, path, **params):
    response = client.get(f"/api/reports/{path}", params=params, headers=auth["manager"])
    assert response.status_code == 200, response.text
    return response.json()


def test_daily_sales(client, auth, history):
    day1, day2, day3 = get(client, auth, "daily-sales", **PARAMS)
    assert day1["date"] == "2026-10-01"
    assert day1["sales_count"] == 1
    assert day1["sales_total"] == 19.0
    assert day1["cash"] == 19.0
    assert day1["gross_profit"] == 6.0

    assert day2["sales_total"] == 5.85
    assert day2["discounts"] == 0.65
    assert day2["card"] == 5.85
    assert day2["refunds"] == 2.0
    assert day2["net_sales"] == 3.85
    # 0.85 on the sale, minus 1.00 of profit given back with the chips.
    assert day2["gross_profit"] == -0.15

    assert day3["sales_count"] == 0
    assert day3["net_sales"] == 0


def test_top_products_are_net_of_returns(client, auth, history):
    rows = get(client, auth, "top-products", **PARAMS)
    assert [(r["name"], r["units_sold"], r["revenue"], r["profit"]) for r in rows] == [
        ("Milk", 3, 18.85, 3.85),
        ("Chips", 2, 4.0, 2.0),
    ]
    by_quantity = get(client, auth, "top-products", by="quantity", limit=1, **PARAMS)
    assert by_quantity[0]["name"] == "Milk"


def test_profit_by_category_matches_daily_profit(client, auth, history):
    rows = get(client, auth, "profit-by-category", **PARAMS)
    assert [(r["category"], r["profit"], r["margin_percent"]) for r in rows] == [
        ("Dairy", 3.85, 20.42),
        ("Snacks", 2.0, 50.0),
    ]
    daily = get(client, auth, "daily-sales", **PARAMS)
    assert round(sum(r["profit"] for r in rows), 2) == round(
        sum(d["gross_profit"] for d in daily), 2
    )


def test_stock_valuation(client, auth, history):
    rows = {r["category"]: r for r in get(client, auth, "stock-valuation")}
    assert rows["Uncategorised"]["cost_value"] == 150.0
    assert rows["Dairy"]["units"] == 17
    assert rows["Dairy"]["cost_value"] == 85.0
    assert rows["Snacks"]["units"] == 18
    assert rows["Snacks"]["retail_value"] == 36.0
    assert rows["Snacks"]["potential_profit"] == 18.0


def test_slow_movers(db, history):
    rows = reports.slow_movers(db, as_of=date(2026, 10, 3), days=30, max_units=0)
    assert [(r["name"], r["on_hand"], r["last_sold"]) for r in rows] == [("Charger", 5, None)]
    with_chips = reports.slow_movers(db, as_of=date(2026, 10, 3), days=30, max_units=2)
    assert [r["name"] for r in with_chips] == ["Charger", "Chips"]
    assert with_chips[1]["days_since_last_sale"] == 2


def test_cashier_performance(client, auth, history):
    rows = {r["cashier_name"]: r for r in get(client, auth, "cashier-performance", **PARAMS)}
    cashier = rows["Test cashier"]
    assert cashier["sales_count"] == 1
    assert cashier["items_sold"] == 5
    assert cashier["sales_total"] == 19.0
    assert cashier["refunded"] == 2.0
    assert rows["Test manager"]["discounts_given"] == 0.65


def test_summary(client, auth, history):
    summary = get(client, auth, "summary", **PARAMS)
    assert summary["sales_count"] == 2
    assert summary["sales_total"] == 24.85
    assert summary["refunds"] == 2.0
    assert summary["net_sales"] == 22.85
    assert summary["gross_profit"] == 5.85
    assert summary["average_basket"] == 12.43
    assert summary["stock_value"] == 253.0
    # Only the charger (5 left) is at or below its low stock threshold of 5.
    assert summary["low_stock_items"] == 1


def test_csv_export(client, auth, history):
    response = client.get(
        "/api/reports/top-products", params={**PARAMS, "format": "csv"}, headers=auth["manager"]
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "top-products_2026-10-01_2026-10-03.csv" in response.headers["content-disposition"]
    text = response.content.decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text)))
    assert rows[0]["name"] == "Milk"
    assert rows[0]["revenue"] == "18.85"


def test_category_csv_keeps_arabic(client, auth, history):
    response = client.get(
        "/api/reports/profit-by-category",
        params={**PARAMS, "format": "csv"},
        headers=auth["manager"],
    )
    assert response.content.startswith(b"\xef\xbb\xbf")
    assert "ألبان" in response.content.decode("utf-8-sig")


def test_csv_neutralises_spreadsheet_formulas(client, db, auth, users, branch):
    product = make_product(db, name='=HYPERLINK("http://evil.test")', sale_price="5.00")
    give_stock(db, product, branch.id, 1, users["manager"])
    sales.checkout(
        db,
        user=users["manager"],
        branch_id=branch.id,
        lines=[sales.CartLine(product.id, 1)],
        payments=[pricing.PaymentInput(PaymentMethod.cash, Decimal("5.00"))],
        at=DAY1,
    )
    db.commit()
    response = client.get(
        "/api/reports/top-products",
        params={**PARAMS, "format": "csv"},
        headers=auth["manager"],
    )
    rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))
    assert rows[0]["name"].startswith("'=")


def test_tax_is_not_counted_as_revenue(db, users, branch):
    product = make_product(db, sale_price="100.00", cost_price="60.00", tax_rate="5")
    give_stock(db, product, branch.id, 1, users["manager"])
    sales.checkout(
        db,
        user=users["manager"],
        branch_id=branch.id,
        lines=[sales.CartLine(product.id, 1)],
        payments=[pricing.PaymentInput(PaymentMethod.card, Decimal("105.00"))],
        at=DAY1,
    )
    db.commit()
    (row,) = reports.daily_sales(db, reports.Period(date(2026, 10, 1), date(2026, 10, 1)))
    assert row["sales_total"] == Decimal("105.00")
    assert row["tax"] == Decimal("5.00")
    assert row["gross_profit"] == Decimal("40.00")


def test_reports_need_a_manager_and_a_valid_range(client, auth, history):
    assert client.get("/api/reports/summary", headers=auth["cashier"]).status_code == 403
    backwards = client.get(
        "/api/reports/daily-sales",
        params={"date_from": "2026-10-05", "date_to": "2026-10-01"},
        headers=auth["manager"],
    )
    assert backwards.status_code == 422
    too_long = client.get(
        "/api/reports/daily-sales",
        params={"date_from": "2024-01-01", "date_to": "2026-01-01"},
        headers=auth["manager"],
    )
    assert too_long.status_code == 422


def test_branch_filter(client, auth, history):
    other = get(client, auth, "daily-sales", branch_id=999, **PARAMS)
    assert sum(row["sales_count"] for row in other) == 0
