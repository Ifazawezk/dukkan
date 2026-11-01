"""Demo data: a two branch mini market in Doha with a few weeks of trading.

Everything is created through the same services the API uses (purchase
orders, checkout, returns, adjustments), so the stock ledger, costs and
reports in the demo are consistent, not just random rows.

    python -m app.cli seed --reset
"""

import random
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import Base
from app.db_types import utcnow
from app.models import (
    AdjustmentReason,
    Branch,
    Category,
    PaymentMethod,
    Product,
    Role,
    Sale,
    Supplier,
    User,
)
from app.money import q
from app.security import hash_password
from app.services import inventory, pricing, purchasing, returns, sales
from app.services.shop import business_date, get_shop_settings

DEMO_PASSWORD = "dukkan123"
SHOP_TZ = ZoneInfo("Asia/Qatar")

# (name, Arabic name, sale price, cost price, popularity). Popularity 0 means
# the item never sells, which gives the slow movers report something to show.
CATALOG = {
    ("Beverages", "مشروبات", "BEV", "Gulf Foods Trading"): [
        ("Mineral Water 500ml", "مياه معدنية 500 مل", "1.00", "0.55", 10),
        ("Mineral Water 1.5L", "مياه معدنية 1.5 لتر", "2.00", "1.20", 6),
        ("Cola Can 330ml", "مشروب غازي كولا 330 مل", "2.50", "1.45", 8),
        ("Orange Juice 1L", "عصير برتقال 1 لتر", "7.75", "5.60", 4),
        ("Karak Tea Mix 10 Sachets", "خلطة شاي كرك 10 أكياس", "9.50", "6.20", 3),
        ("Energy Drink 250ml", "مشروب طاقة 250 مل", "6.00", "3.80", 4),
        ("Arabic Coffee 250g", "قهوة عربية 250 غ", "18.00", "12.50", 2),
    ],
    ("Dairy & Eggs", "ألبان وبيض", "DAI", "Doha Dairy Distribution"): [
        ("Fresh Milk 1L", "حليب طازج 1 لتر", "6.50", "5.10", 8),
        ("Laban 1L", "لبن 1 لتر", "6.00", "4.70", 6),
        ("Greek Yoghurt 500g", "زبادي يوناني 500 غ", "9.25", "6.90", 3),
        ("Eggs 30 Pieces", "بيض 30 حبة", "19.50", "15.80", 4),
        ("Halloumi Cheese 250g", "جبنة حلوم 250 غ", "14.00", "10.20", 2),
        ("Labneh 400g", "لبنة 400 غ", "11.50", "8.40", 3),
        ("Butter 200g", "زبدة 200 غ", "8.75", "6.60", 2),
    ],
    ("Bakery", "مخبوزات", "BAK", "Doha Dairy Distribution"): [
        ("Arabic Bread Pack", "خبز عربي", "2.00", "1.30", 9),
        ("Samoon Bread 6 Pieces", "خبز صامولي 6 حبات", "3.00", "1.90", 5),
        ("Croissant Plain", "كرواسون سادة", "3.50", "2.10", 4),
        ("Zaatar Manakish", "مناقيش زعتر", "4.00", "2.20", 4),
    ],
    ("Rice & Pantry", "أرز ومواد غذائية", "PAN", "Gulf Foods Trading"): [
        ("Basmati Rice 5kg", "أرز بسمتي 5 كغ", "42.00", "33.50", 3),
        ("Sugar 2kg", "سكر 2 كغ", "8.50", "6.40", 3),
        ("Sunflower Oil 1.5L", "زيت دوار الشمس 1.5 لتر", "14.25", "10.90", 3),
        ("Red Lentils 1kg", "عدس أحمر 1 كغ", "7.25", "5.10", 2),
        ("Tomato Paste 135g", "معجون طماطم 135 غ", "2.75", "1.70", 4),
        ("Tuna Can 160g", "تونة معلبة 160 غ", "6.50", "4.60", 4),
        ("Khalas Dates 1kg", "تمر خلاص 1 كغ", "25.00", "17.00", 2),
        ("Pasta 500g", "معكرونة 500 غ", "4.25", "2.80", 3),
    ],
    ("Snacks & Sweets", "وجبات خفيفة وحلويات", "SNK", "Gulf Foods Trading"): [
        ("Potato Chips 45g", "شيبس بطاطس 45 غ", "2.00", "1.10", 8),
        ("Chocolate Bar 50g", "لوح شوكولاتة 50 غ", "3.75", "2.30", 6),
        ("Mixed Nuts 200g", "مكسرات مشكلة 200 غ", "16.50", "11.00", 2),
        ("Biscuits Pack", "بسكويت", "3.25", "2.00", 5),
        ("Maamoul Box 12 Pieces", "علبة معمول 12 حبة", "22.00", "15.00", 1),
    ],
    ("Household", "منظفات منزلية", "HOU", "Al Waab Household Supplies"): [
        ("Dish Soap 750ml", "سائل جلي 750 مل", "9.50", "6.40", 2),
        ("Laundry Detergent 3kg", "مسحوق غسيل 3 كغ", "32.00", "24.00", 2),
        ("Tissue Box 5 Pack", "مناديل 5 علب", "10.00", "6.80", 3),
        ("Garbage Bags 30 Pieces", "أكياس قمامة 30 حبة", "7.50", "4.60", 2),
        ("Air Freshener", "معطر جو", "12.00", "7.90", 1),
    ],
    ("Personal Care", "عناية شخصية", "PER", "Al Waab Household Supplies"): [
        ("Shampoo 400ml", "شامبو 400 مل", "18.50", "12.60", 2),
        ("Toothpaste 100ml", "معجون أسنان 100 مل", "9.00", "5.90", 2),
        ("Hand Soap 250ml", "صابون يدين 250 مل", "7.00", "4.40", 2),
        ("Baby Diapers Size 4", "حفاضات أطفال مقاس 4", "52.00", "40.00", 1),
        ("Oud Perfume 50ml", "عطر عود 50 مل", "120.00", "70.00", 0),
    ],
    ("Phone Accessories", "إكسسوارات الهواتف", "ACC", "Smart Mobile Accessories"): [
        ("USB-C Charger 20W", "شاحن USB-C بقوة 20 واط", "35.00", "16.00", 2),
        ("USB-C Cable 1m", "كابل USB-C طول 1 متر", "25.00", "9.00", 2),
        ("Tempered Glass Screen Protector", "واقي شاشة زجاجي", "20.00", "5.00", 1),
        ("Power Bank 10000mAh", "باور بانك 10000 ملي أمبير", "89.00", "52.00", 1),
        ("Wired Earphones", "سماعات سلكية", "45.00", "22.00", 0),
        ("Silicone Phone Case", "غطاء جوال سيليكون", "30.00", "9.00", 1),
        ("Car Phone Holder", "حامل جوال للسيارة", "39.00", "18.00", 0),
    ],
}

SUPPLIERS = [
    ("Gulf Foods Trading", "Faisal Rahman", "+974 4400 1100", "orders@gulffoods.example"),
    ("Doha Dairy Distribution", "Nadia Saleh", "+974 4400 2200", "sales@dohadairy.example"),
    ("Al Waab Household Supplies", "Imran Qureshi", "+974 4400 3300", "info@alwaab.example"),
    ("Smart Mobile Accessories", "Kevin D'Souza", "+974 4400 4400", "b2b@smartmobile.example"),
]

BRANCHES = [
    # code, name, Arabic name, address, phone, sales per day, cashiers
    ("SAD", "Al Sadd", "السد", "Al Sadd Street, Doha", "+974 4000 1001", 30, ("rahul", "maria")),
    ("WAK", "Al Wakra", "الوكرة", "Al Wakra Main Road", "+974 4000 1002", 18, ("omar",)),
]

USERS = [
    ("owner", "Ahmed Hassan", Role.owner, None),
    ("manager", "Sara Mahmoud", Role.manager, "SAD"),
    ("rahul", "Rahul Nair", Role.cashier, "SAD"),
    ("maria", "Maria Santos", Role.cashier, "SAD"),
    ("omar", "Omar Farouk", Role.cashier, "WAK"),
]


def ean13(first_twelve: str) -> str:
    """Append the EAN-13 check digit."""
    total = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(first_twelve))
    return first_twelve + str((10 - total % 10) % 10)


@dataclass
class DemoResult:
    sales: int
    returns: int
    purchase_orders: int
    products: int
    days: int
    seconds: float


class Simulation:
    def __init__(self, db: Session, rng: random.Random):
        self.db = db
        self.rng = rng
        self.stock: dict[tuple[int, int], int] = defaultdict(int)
        self.popularity: dict[int, int] = {}
        self.supplier_of: dict[int, Supplier] = {}
        self.pending_returns: list[tuple[datetime, int]] = []
        self.open_orders: list[tuple[date, int]] = []
        self.counts = defaultdict(int)

    # ----- setup -------------------------------------------------------------

    def setup(self) -> None:
        db = self.db
        settings = get_shop_settings(db)
        settings.shop_name = "Al Noor Mart"
        settings.shop_name_ar = "النور ماركت"
        settings.receipt_footer = "Thank you for shopping with us"
        settings.receipt_footer_ar = "شكراً لتسوقكم معنا"

        self.branches = {}
        self.cashiers = {code: cashiers for code, *_, cashiers in BRANCHES}
        for code, name, name_ar, address, phone, _, _ in BRANCHES:
            branch = Branch(code=code, name=name, name_ar=name_ar, address=address, phone=phone)
            db.add(branch)
            self.branches[code] = branch
        db.flush()

        password_hash = hash_password(DEMO_PASSWORD)
        self.users = {}
        for username, full_name, role, branch_code in USERS:
            user = User(
                username=username,
                full_name=full_name,
                password_hash=password_hash,
                role=role,
                branch_id=self.branches[branch_code].id if branch_code else None,
            )
            db.add(user)
            self.users[username] = user

        suppliers = {}
        for name, contact, phone, email in SUPPLIERS:
            supplier = Supplier(name=name, contact_name=contact, phone=phone, email=email)
            db.add(supplier)
            suppliers[name] = supplier
        db.flush()

        self.products: list[Product] = []
        barcode_serial = 1
        for (category_name, category_ar, prefix, supplier_name), items in CATALOG.items():
            category = Category(name=category_name, name_ar=category_ar)
            db.add(category)
            db.flush()
            for number, (name, name_ar, price, cost, popularity) in enumerate(items, start=1):
                threshold = 15 if popularity >= 6 else 8 if popularity >= 3 else 4
                product = Product(
                    sku=f"{prefix}-{number:03d}",
                    barcode=ean13(f"200{barcode_serial:09d}"),
                    name=name,
                    name_ar=name_ar,
                    category_id=category.id,
                    cost_price=Decimal(cost),
                    sale_price=Decimal(price),
                    low_stock_threshold=threshold,
                )
                barcode_serial += 1
                db.add(product)
                db.flush()
                self.products.append(product)
                self.popularity[product.id] = popularity
                self.supplier_of[product.id] = suppliers[supplier_name]
        db.commit()

    # ----- helpers -----------------------------------------------------------

    def local(self, day: date, hour: float) -> datetime:
        minutes = int(hour * 60)
        naive = datetime(day.year, day.month, day.day) + timedelta(minutes=minutes)
        return naive.replace(tzinfo=SHOP_TZ)

    def target_stock(self, product: Product, branch_code: str) -> int:
        base = self.popularity[product.id] * 7 + 8
        return int(base * (1.0 if branch_code == "SAD" else 0.7))

    def order(self, branch: Branch, wanted: dict[int, int], at: datetime, receive: bool) -> None:
        by_supplier = defaultdict(list)
        for product_id, quantity in wanted.items():
            if quantity > 0:
                by_supplier[self.supplier_of[product_id].id].append((product_id, quantity))
        for supplier_id, lines in by_supplier.items():
            po = purchasing.create_purchase_order(
                self.db,
                supplier_id=supplier_id,
                branch_id=branch.id,
                lines=[purchasing.ItemLine(pid, qty) for pid, qty in lines],
                user=self.users["manager"],
                at=at,
            )
            purchasing.submit(po, at=at)
            self.counts["purchase_orders"] += 1
            if receive:
                self.receive(po.id, at)
            else:
                self.open_orders.append((at.date() + timedelta(days=1), po.id))

    def receive(self, po_id: int, at: datetime) -> None:
        po = purchasing.get_purchase_order(self.db, po_id)
        lines = []
        for item in po.items:
            # Supplier prices drift a little from delivery to delivery.
            drift = Decimal(str(self.rng.uniform(0.97, 1.05)))
            lines.append(purchasing.ReceiveLine(item.id, item.remaining, q(item.unit_cost * drift)))
        purchasing.receive(self.db, po, lines, user=self.users["manager"], at=at)
        for item in po.items:
            self.stock[(item.product_id, po.branch_id)] += item.quantity_received

    # ----- daily activity ----------------------------------------------------

    def opening_stock(self, day: date) -> None:
        for code, branch in self.branches.items():
            wanted = {p.id: self.target_stock(p, code) for p in self.products}
            self.order(branch, wanted, self.local(day, 8), receive=True)
        self.db.commit()

    def restock(self, day: date) -> None:
        for code, branch in self.branches.items():
            wanted = {}
            for product in self.products:
                on_hand = self.stock[(product.id, branch.id)]
                if not self.popularity[product.id] or on_hand > product.low_stock_threshold * 2:
                    continue
                if self.rng.random() < 0.2:
                    continue  # the supplier is out of it this week
                wanted[product.id] = self.target_stock(product, code) - on_hand
            if wanted:
                self.order(branch, wanted, self.local(day, 9), receive=False)

    def deliveries(self, day: date) -> None:
        due = [po_id for when, po_id in self.open_orders if when <= day]
        self.open_orders = [(when, po_id) for when, po_id in self.open_orders if when > day]
        for po_id in due:
            self.receive(po_id, self.local(day, 10))
        self.db.flush()

    def sell(self, branch_code: str, at: datetime) -> None:
        branch = self.branches[branch_code]
        sellable = [
            p for p in self.products if self.popularity[p.id] and self.stock[(p.id, branch.id)] > 0
        ]
        if not sellable:
            return
        weights = [self.popularity[p.id] for p in sellable]
        basket: dict[int, int] = {}
        for _ in range(self.rng.choices([1, 2, 3, 4, 5], [30, 30, 20, 12, 8])[0]):
            product = self.rng.choices(sellable, weights)[0]
            quantity = self.rng.choices([1, 2, 3], [70, 22, 8])[0]
            available = self.stock[(product.id, branch.id)] - basket.get(product.id, 0)
            if available >= quantity:
                basket[product.id] = basket.get(product.id, 0) + quantity
        if not basket:
            return

        # Morning and evening shifts where a branch has two cashiers.
        cashiers = self.cashiers[branch_code]
        shift = 0 if at.astimezone(SHOP_TZ).hour < 15 else len(cashiers) - 1
        cashier = self.users[cashiers[shift]]

        discount = None
        if self.rng.random() < 0.04:
            discount = sales.OrderDiscount("percent", Decimal(self.rng.choice([5, 10])))

        lines = [sales.CartLine(pid, qty) for pid, qty in basket.items()]
        total = self.quote(lines, discount)
        method = self.rng.choices(
            [PaymentMethod.cash, PaymentMethod.card, PaymentMethod.wallet], [45, 43, 12]
        )[0]
        amount = total
        if method == PaymentMethod.cash:
            # Customers hand over one of the two smallest notes that cover the bill.
            notes = [n for n in (5, 10, 20, 50, 100, 200, 500) if n >= total]
            amount = Decimal(self.rng.choice(notes[:2])) if notes else total
        payments = [pricing.PaymentInput(method, amount)] if total > 0 else []

        sale = sales.checkout(
            self.db,
            user=cashier,
            branch_id=branch.id,
            lines=lines,
            payments=payments,
            order_discount=discount,
            at=at,
        )
        for pid, qty in basket.items():
            self.stock[(pid, branch.id)] -= qty
        self.counts["sales"] += 1
        if self.rng.random() < 0.015:
            later = at + timedelta(hours=self.rng.uniform(1, 40))
            self.pending_returns.append((later, sale.id))

    def quote(self, lines: list[sales.CartLine], discount: sales.OrderDiscount | None) -> Decimal:
        products = {p.id: p for p in self.products}
        inputs = [
            pricing.LineInput(products[line.product_id].sale_price, line.quantity) for line in lines
        ]
        base = sum((q(i.unit_price * i.quantity) for i in inputs), Decimal("0"))
        off = q(base * discount.value / 100) if discount else Decimal("0")
        return pricing.price_cart(inputs, off).total

    def take_return(self, sale_id: int, at: datetime) -> None:
        sale = self.db.get(Sale, sale_id)
        open_items = [item for item in sale.items if item.returnable > 0]
        if not open_items:
            return
        item = self.rng.choice(open_items)
        restock = self.rng.random() < 0.85
        returns.process_return(
            self.db,
            sale=sale,
            lines=[returns.ReturnLine(item.id, 1, restock)],
            user=self.users["manager"],
            reason=self.rng.choice(["Changed mind", "Wrong item", "Damaged packaging"]),
            at=at,
        )
        if restock:
            self.stock[(item.product_id, sale.branch_id)] += 1
        self.counts["returns"] += 1

    def write_offs(self, day: date) -> None:
        sad = self.branches["SAD"]
        for product in self.products:
            if product.sku.startswith("BAK") and self.rng.random() < 0.25:
                on_hand = self.stock[(product.id, sad.id)]
                quantity = min(on_hand, self.rng.randint(1, 3))
                if quantity:
                    inventory.adjust_stock(
                        self.db,
                        product=product,
                        branch_id=sad.id,
                        user=self.users["manager"],
                        reason=AdjustmentReason.expired,
                        quantity_change=-quantity,
                        note="Past best before date",
                        at=self.local(day, 22.5),
                    )
                    self.stock[(product.id, sad.id)] -= quantity

    def run_day(self, day: date, now: datetime) -> None:
        events: list[tuple[datetime, str, object]] = []
        for code, _, _, _, _, per_day, _ in BRANCHES:
            factor = {3: 1.2, 4: 1.35, 5: 1.15}.get(day.weekday(), 1.0)  # Thu, Fri, Sat
            count = int(per_day * factor * self.rng.uniform(0.8, 1.2))
            for _ in range(count):
                hour = self.rng.uniform(7, 23.5)
                if day.weekday() == 4 and 11 <= hour < 13:
                    hour += 2  # quieter around Friday prayers
                events.append((self.local(day, hour), "sale", code))
        for when, sale_id in self.pending_returns:
            if when.astimezone(SHOP_TZ).date() == day:
                events.append((when, "return", sale_id))
        events.sort(key=lambda e: e[0])

        if self.local(day, 10) <= now:
            self.deliveries(day)
        if day.weekday() in (0, 3) and self.local(day, 9) <= now:
            self.restock(day)  # orders go out on Mondays and Thursdays
        for when, kind, value in events:
            if when > now:
                break
            if kind == "sale":
                self.sell(value, when)
            else:
                self.take_return(value, when)
        if self.local(day, 22.5) <= now:
            self.write_offs(day)
        self.db.commit()


def database_is_empty(db: Session) -> bool:
    return not db.scalar(select(func.count(User.id))) and not db.scalar(
        select(func.count(Product.id))
    )


def clear_database(db: Session) -> None:
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()
    db.expunge_all()  # forget objects whose rows are gone


def seed_demo(
    db: Session, days: int = 45, seed: int = 2026, now: datetime | None = None
) -> DemoResult:
    started = time.perf_counter()
    rng = random.Random(seed)
    now = now or utcnow()
    simulation = Simulation(db, rng)
    simulation.setup()

    today = business_date(get_shop_settings(db), now)
    first_day = today - timedelta(days=days - 1)
    simulation.opening_stock(first_day - timedelta(days=1))
    for offset in range(days):
        simulation.run_day(first_day + timedelta(days=offset), now)

    # Leave a draft order on the desk for the purchase orders screen.
    sad = simulation.branches["SAD"]
    phone_bits = [p for p in simulation.products if p.sku.startswith("ACC")][:3]
    purchasing.create_purchase_order(
        db,
        supplier_id=simulation.supplier_of[phone_bits[0].id].id,
        branch_id=sad.id,
        lines=[purchasing.ItemLine(p.id, 10) for p in phone_bits],
        user=simulation.users["manager"],
        notes="Ask about the new MagSafe range",
        at=now,
    )
    simulation.counts["purchase_orders"] += 1
    db.commit()

    return DemoResult(
        sales=simulation.counts["sales"],
        returns=simulation.counts["returns"],
        purchase_orders=simulation.counts["purchase_orders"],
        products=len(simulation.products),
        days=days,
        seconds=time.perf_counter() - started,
    )
