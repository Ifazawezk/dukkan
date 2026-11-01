"""Report endpoints. Every table report can also be downloaded as CSV with ?format=csv."""

import csv
import io
from datetime import date, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel

from app.db_types import utcnow
from app.deps import DbSession, ManagerUser
from app.errors import InvalidRequest
from app.schemas.reports import (
    CashierRow,
    CategoryProfitRow,
    DailySalesRow,
    ProductSalesRow,
    SlowMoverRow,
    StockValuationRow,
    SummaryOut,
)
from app.services import reports
from app.services.shop import business_date, get_shop_settings

router = APIRouter(prefix="/reports", tags=["reports"])

Format = Annotated[Literal["json", "csv"], Query(description="json, or csv for a download")]


def today(db: DbSession) -> date:
    return business_date(get_shop_settings(db), utcnow())


def report_period(
    db: DbSession,
    date_from: date | None = None,
    date_to: date | None = None,
    branch_id: int | None = None,
) -> reports.Period:
    """Defaults to the last 30 days, ending today in the shop's time zone."""
    date_to = date_to or today(db)
    date_from = date_from or date_to - timedelta(days=29)
    if date_from > date_to:
        raise InvalidRequest("date_from must be on or before date_to")
    if (date_to - date_from).days > 366:
        raise InvalidRequest("Reports cover at most one year at a time")
    return reports.Period(date_from, date_to, branch_id)


PeriodDep = Annotated[reports.Period, Depends(report_period)]


def respond(rows: list[BaseModel], fmt: str, name: str, model: type[BaseModel]):
    if fmt == "json":
        return rows
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(model.model_fields))
    writer.writeheader()
    for row in rows:
        writer.writerow(row.model_dump(mode="json"))
    # The byte order mark makes Excel open Arabic text correctly.
    return Response(
        content="﻿" + buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{name}.csv"'},
    )


@router.get("/summary", response_model=SummaryOut)
def summary(db: DbSession, _user: ManagerUser, period: PeriodDep) -> SummaryOut:
    """Headline numbers for the dashboard."""
    return SummaryOut(**reports.summary(db, period, today(db)))


@router.get("/daily-sales", response_model=list[DailySalesRow])
def daily_sales(db: DbSession, _user: ManagerUser, period: PeriodDep, format: Format = "json"):
    """One row per day: sales, refunds paid out that day, payment mix and gross profit."""
    rows = [DailySalesRow(**row) for row in reports.daily_sales(db, period)]
    return respond(rows, format, f"daily-sales_{period.date_from}_{period.date_to}", DailySalesRow)


@router.get("/top-products", response_model=list[ProductSalesRow])
def top_products(
    db: DbSession,
    _user: ManagerUser,
    period: PeriodDep,
    by: Literal["revenue", "quantity"] = "revenue",
    limit: int = Query(10, ge=1, le=500),
    format: Format = "json",
):
    """Best sellers, net of returns."""
    rows = [ProductSalesRow(**row) for row in reports.product_sales(db, period, by, limit)]
    return respond(
        rows, format, f"top-products_{period.date_from}_{period.date_to}", ProductSalesRow
    )


@router.get("/profit-by-category", response_model=list[CategoryProfitRow])
def profit_by_category(
    db: DbSession, _user: ManagerUser, period: PeriodDep, format: Format = "json"
):
    rows = [CategoryProfitRow(**row) for row in reports.profit_by_category(db, period)]
    return respond(
        rows, format, f"profit-by-category_{period.date_from}_{period.date_to}", CategoryProfitRow
    )


@router.get("/slow-movers", response_model=list[SlowMoverRow])
def slow_movers(
    db: DbSession,
    _user: ManagerUser,
    branch_id: int | None = None,
    days: int = Query(30, ge=1, le=365),
    max_units: int = Query(2, ge=0),
    format: Format = "json",
):
    """Stock that is sitting on the shelf: max_units or fewer sold in the last `days` days."""
    rows = [
        SlowMoverRow(**row)
        for row in reports.slow_movers(db, today(db), days, max_units, branch_id)
    ]
    return respond(rows, format, f"slow-movers_{days}d", SlowMoverRow)


@router.get("/stock-valuation", response_model=list[StockValuationRow])
def stock_valuation(
    db: DbSession, _user: ManagerUser, branch_id: int | None = None, format: Format = "json"
):
    """Value of the stock on hand by category, at cost and at sale price."""
    rows = [StockValuationRow(**row) for row in reports.stock_valuation(db, branch_id)]
    return respond(rows, format, f"stock-valuation_{today(db)}", StockValuationRow)


@router.get("/cashier-performance", response_model=list[CashierRow])
def cashier_performance(
    db: DbSession, _user: ManagerUser, period: PeriodDep, format: Format = "json"
):
    rows = [CashierRow(**row) for row in reports.cashier_performance(db, period)]
    return respond(
        rows, format, f"cashier-performance_{period.date_from}_{period.date_to}", CashierRow
    )
