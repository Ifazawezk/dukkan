from fastapi import APIRouter, Query, status

from app.deps import CurrentUser, DbSession, ManagerUser
from app.errors import NotFound
from app.models import Product, User
from app.schemas.catalog import ProductCreate, ProductOut, ProductUpdate
from app.schemas.common import Page, changed_fields
from app.services import catalog
from app.services.shop import get_shop_settings

router = APIRouter(prefix="/products", tags=["products"])

NULLABLE_FIELDS = ("barcode", "category_id", "tax_rate")


def to_out(product: Product, user: User) -> ProductOut:
    out = ProductOut.model_validate(product)
    if not user.is_manager:
        out.cost_price = None
    return out


@router.get("", response_model=Page[ProductOut])
def list_products(
    db: DbSession,
    user: CurrentUser,
    q: str | None = None,
    category_id: int | None = None,
    include_inactive: bool = False,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> Page[ProductOut]:
    stmt = catalog.search_products(q, category_id, include_inactive)
    total = catalog.count_matching(db, stmt)
    products = db.scalars(stmt.order_by(Product.name).limit(limit).offset(offset))
    return Page(items=[to_out(p, user) for p in products], total=total)


@router.get("/lookup", response_model=ProductOut)
def lookup_product(code: str, db: DbSession, user: CurrentUser) -> ProductOut:
    """Find one product by exact barcode or SKU, as sent by a scanner."""
    product = catalog.find_by_code(db, code)
    if product is None:
        raise NotFound("No product with this barcode or SKU", code=code)
    return to_out(product, user)


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: DbSession, user: CurrentUser) -> ProductOut:
    return to_out(catalog.get_product(db, product_id), user)


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
