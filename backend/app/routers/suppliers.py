from fastapi import APIRouter, status
from sqlalchemy import func, select

from app.deps import DbSession, ManagerUser
from app.errors import Conflict, NotFound
from app.models import Supplier
from app.schemas.common import changed_fields
from app.schemas.purchasing import SupplierIn, SupplierOut, SupplierUpdate

router = APIRouter(prefix="/suppliers", tags=["purchasing"])


def _check_name(db: DbSession, name: str, exclude_id: int | None = None) -> None:
    stmt = select(Supplier.id).where(func.lower(Supplier.name) == name.strip().lower())
    if exclude_id is not None:
        stmt = stmt.where(Supplier.id != exclude_id)
    if db.scalar(stmt):
        raise Conflict("A supplier with this name already exists", name=name)


@router.get("", response_model=list[SupplierOut])
def list_suppliers(
    db: DbSession, _user: ManagerUser, include_inactive: bool = False
) -> list[Supplier]:
    stmt = select(Supplier).order_by(Supplier.name)
    if not include_inactive:
        stmt = stmt.where(Supplier.is_active.is_(True))
    return list(db.scalars(stmt))


@router.post("", response_model=SupplierOut, status_code=status.HTTP_201_CREATED)
def create_supplier(payload: SupplierIn, db: DbSession, _user: ManagerUser) -> Supplier:
    _check_name(db, payload.name)
    supplier = Supplier(**payload.model_dump())
    db.add(supplier)
    db.commit()
    return supplier


@router.patch("/{supplier_id}", response_model=SupplierOut)
def update_supplier(
    supplier_id: int, payload: SupplierUpdate, db: DbSession, _user: ManagerUser
) -> Supplier:
    supplier = db.get(Supplier, supplier_id)
    if supplier is None:
        raise NotFound("Supplier not found", supplier_id=supplier_id)
    changes = changed_fields(payload)
    if "name" in changes:
        _check_name(db, changes["name"], exclude_id=supplier.id)
    for field, value in changes.items():
        setattr(supplier, field, value)
    db.commit()
    return supplier
