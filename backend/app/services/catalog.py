from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from app.errors import Conflict, NotFound
from app.models import Category, Product
from app.services.queries import like_pattern


def search_products(
    q: str | None = None,
    category_id: int | None = None,
    include_inactive: bool = False,
) -> Select:
    stmt = select(Product)
    if q:
        pattern = like_pattern(q.strip())
        stmt = stmt.where(
            or_(
                Product.name.ilike(pattern, escape="\\"),
                Product.name_ar.ilike(pattern, escape="\\"),
                Product.sku.ilike(pattern, escape="\\"),
                Product.barcode.ilike(pattern, escape="\\"),
            )
        )
    if category_id is not None:
        stmt = stmt.where(Product.category_id == category_id)
    if not include_inactive:
        stmt = stmt.where(Product.is_active.is_(True))
    return stmt


def find_by_code(db: Session, code: str) -> Product | None:
    """Exact match on barcode first, then on SKU. Used by barcode scanners."""
    code = code.strip()
    product = db.scalar(select(Product).where(Product.barcode == code))
    if product is None:
        product = db.scalar(select(Product).where(Product.sku == code.upper()))
    return product


def get_product(db: Session, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise NotFound("Product not found", product_id=product_id)
    return product


def check_unique_codes(
    db: Session, sku: str | None, barcode: str | None, exclude_id: int | None = None
) -> None:
    if sku is not None:
        stmt = select(Product.id).where(Product.sku == sku)
        if exclude_id is not None:
            stmt = stmt.where(Product.id != exclude_id)
        if db.scalar(stmt):
            raise Conflict("Another product already uses this SKU", sku=sku)
    if barcode is not None:
        stmt = select(Product.id).where(Product.barcode == barcode)
        if exclude_id is not None:
            stmt = stmt.where(Product.id != exclude_id)
        if db.scalar(stmt):
            raise Conflict("Another product already uses this barcode", barcode=barcode)


def check_category(db: Session, category_id: int | None) -> None:
    if category_id is not None and db.get(Category, category_id) is None:
        raise NotFound("Category not found", category_id=category_id)
