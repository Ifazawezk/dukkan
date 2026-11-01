from fastapi import APIRouter, status
from sqlalchemy import func, select

from app.deps import CurrentUser, DbSession, ManagerUser
from app.errors import Conflict, NotFound
from app.models import Category, Product
from app.schemas.catalog import CategoryIn, CategoryOut, CategoryUpdate
from app.schemas.common import changed_fields

router = APIRouter(prefix="/categories", tags=["categories"])


def _get(db: DbSession, category_id: int) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise NotFound("Category not found", category_id=category_id)
    return category


def _check_name(db: DbSession, name: str, exclude_id: int | None = None) -> None:
    stmt = select(Category.id).where(func.lower(Category.name) == name.strip().lower())
    if exclude_id is not None:
        stmt = stmt.where(Category.id != exclude_id)
    if db.scalar(stmt):
        raise Conflict("A category with this name already exists", name=name)


@router.get("", response_model=list[CategoryOut])
def list_categories(db: DbSession, _user: CurrentUser) -> list[CategoryOut]:
    counts = dict(
        db.execute(
            select(Product.category_id, func.count(Product.id))
            .where(Product.is_active.is_(True))
            .group_by(Product.category_id)
        ).all()
    )
    categories = db.scalars(select(Category).order_by(Category.name))
    return [
        CategoryOut(id=c.id, name=c.name, name_ar=c.name_ar, product_count=counts.get(c.id, 0))
        for c in categories
    ]


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoryIn, db: DbSession, _user: ManagerUser) -> Category:
    _check_name(db, payload.name)
    category = Category(name=payload.name.strip(), name_ar=payload.name_ar.strip())
    db.add(category)
    db.commit()
    return category


@router.patch("/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: int, payload: CategoryUpdate, db: DbSession, _user: ManagerUser
) -> Category:
    category = _get(db, category_id)
    changes = changed_fields(payload)
    if "name" in changes:
        _check_name(db, changes["name"], exclude_id=category.id)
    for field, value in changes.items():
        setattr(category, field, value.strip())
    db.commit()
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, db: DbSession, _user: ManagerUser) -> None:
    category = _get(db, category_id)
    in_use = db.scalar(select(func.count(Product.id)).where(Product.category_id == category.id))
    if in_use:
        raise Conflict("Move or remove the products in this category first", products=in_use)
    db.delete(category)
    db.commit()
