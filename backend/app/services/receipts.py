"""Plain text receipts for 80 mm thermal printers (42 characters per line)."""

from decimal import Decimal
from zoneinfo import ZoneInfo

from app.models import Sale, ShopSettings

WIDTH = 42


def _money(amount: Decimal) -> str:
    return f"{amount:,.2f}"


def _row(left: str, right: str) -> str:
    space = WIDTH - len(right) - 1
    return f"{left[:space]:<{space}} {right}"


def render_text_receipt(sale: Sale, settings: ShopSettings) -> str:
    rule = "-" * WIDTH
    local_time = sale.created_at.astimezone(ZoneInfo(settings.timezone))
    lines = [settings.shop_name.center(WIDTH).rstrip()]
    if settings.shop_name_ar:
        lines.append(settings.shop_name_ar.center(WIDTH).rstrip())
    lines.append(sale.branch.name.center(WIDTH).rstrip())
    if sale.branch.phone:
        lines.append(f"Tel {sale.branch.phone}".center(WIDTH).rstrip())
    lines += [
        rule,
        f"Receipt: {sale.receipt_no}",
        f"Date:    {local_time:%Y-%m-%d %H:%M}",
        f"Cashier: {sale.cashier.full_name}",
        rule,
    ]

    for item in sale.items:
        lines.append(item.product_name[:WIDTH])
        lines.append(
            _row(
                f"  {item.quantity} x {_money(item.unit_price)}",
                _money(item.unit_price * item.quantity),
            )
        )
        if item.discount:
            lines.append(_row("  Discount", f"-{_money(item.discount)}"))

    lines += [rule, _row("Subtotal", _money(sale.subtotal))]
    if sale.discount_total:
        lines.append(_row("Discount", f"-{_money(sale.discount_total)}"))
    if sale.tax_total:
        lines.append(_row("Tax", _money(sale.tax_total)))
    lines.append(_row(f"TOTAL {settings.currency}", _money(sale.total)))
    for payment in sale.payments:
        lines.append(_row(payment.method.value.capitalize(), _money(payment.amount)))
    if sale.change_due:
        lines.append(_row("Tendered", _money(sale.amount_tendered)))
        lines.append(_row("Change", _money(sale.change_due)))
    lines.append(rule)
    for footer in (settings.receipt_footer, settings.receipt_footer_ar):
        if footer:
            lines.append(footer.center(WIDTH).rstrip())
    return "\n".join(lines) + "\n"
