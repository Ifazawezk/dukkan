from fastapi import APIRouter, Query, status

from app.deps import CurrentUser, DbSession, ManagerUser
from app.errors import NotFound
from app.models import Product, User
from app.schemas.catalog import ProductCreate, ProductOut, ProductUpdate
from app.schemas.common import Page, changed_fields
from app.services import catalog, inventory
from app.services.shop import get_shop_settings, resolve_branch_id

router = APIRouter(prefix="/products", tags=["products"])

NULLABLE_FIELDS = ("barcode", "category_id", "tax_rate")


def to_out(product: Product, user: User, stock: int | None = None) -> ProductOut:
    out = ProductOut.model_validate(product)
    out.stock = stock
    if not user.is_manager:
        out.cost_price = None
    return out


def stock_branch(db: DbSession, user: User, branch_id: int | None) -> int | None:
    """Branch whose stock is shown next to products: the one asked for, else the user's own."""
    if branch_id is None and user.branch_id is None:
        return None
    return resolve_branch_id(db, user, branch_id)


@router.get("", response_model=Page[ProductOut])
def list_products(
    db: DbSession,
    user: CurrentUser,
    q: str | None = None,
    category_id: int | None = None,
    include_inactive: bool = False,
    branch_id: int | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> Page[ProductOut]:
    stmt = catalog.search_products(q, category_id, include_inactive)
    total = catalog.count_matching(db, stmt)
    products = list(db.scalars(stmt.order_by(Product.name).limit(limit).offset(offset)))
    branch = stock_branch(db, user, branch_id)
    stock = (
        inventory.quantities_in_branch(db, branch, [p.id for p in products])
        if branch is not None
        else {}
    )
    return Page(items=[to_out(p, user, stock.get(p.id)) for p in products], total=total)


@router.get("/lookup", response_model=ProductOut)
def lookup_product(
    code: str, db: DbSession, user: CurrentUser, branch_id: int | None = None
) -> ProductOut:
    """Find one product by exact barcode or SKU, as sent by a scanner."""
    product = catalog.find_by_code(db, code)
    if product is None:
        raise NotFound("No product with this barcode or SKU", code=code)
    branch = stock_branch(db, user, branch_id)
    stock = inventory.quantity_on_hand(db, product.id, branch) if branch is not None else None
    return to_out(product, user, stock)


@router.get("/{product_id}", response_model=ProductOut)
def get_product(
    product_id: int, db: DbSession, user: CurrentUser, branch_id: int | None = None
) -> ProductOut:
    product = catalog.get_product(db, product_id)
    branch = stock_branch(db, user, branch_id)
    stock = inventory.quantity_on_hand(db, product.id, branch) if branch is not None else None
    return to_out(product, user, stock)


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: DbSession, user: ManagerUser) -> ProductOut:
    catalog.check_unique_codes(db, payload.sku, payload.barcode)
    catalog.check_category(db, payload.category_id)
    data = payload.model_dump()
    if data["low_stock_threshold"] is None:
        data["low_stock_threshold"] = get_shop_settings(db).default_low_stock_threshold
    product = Product(**data)
    db.add(product)
    db.commit()
    return to_out(product, user)


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int, payload: ProductUpdate, db: DbSession, user: ManagerUser
) -> ProductOut:
    product = catalog.get_product(db, product_id)
    changes = changed_fields(payload, nullable=NULLABLE_FIELDS)
    catalog.check_unique_codes(
        db, changes.get("sku"), changes.get("barcode"), exclude_id=product.id
    )
    catalog.check_category(db, changes.get("category_id"))
    for field, value in changes.items():
        setattr(product, field, value)
    db.commit()
    return to_out(product, user)
