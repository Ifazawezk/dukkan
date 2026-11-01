from sqlalchemy.orm import Session

from app.errors import InvalidRequest, NotFound, PermissionDenied
from app.models import Branch, Role, ShopSettings, User


def get_shop_settings(db: Session) -> ShopSettings:
    settings = db.get(ShopSettings, 1)
    if settings is None:
        settings = ShopSettings(id=1)
        db.add(settings)
        db.flush()
    return settings


def resolve_branch_id(db: Session, user: User, branch_id: int | None) -> int:
    """Pick the branch an operation applies to and check that the user may use it.

    Cashiers always work in their own branch. Owners and managers may pass any
    active branch and fall back to their home branch when none is given.
    """
    if user.role == Role.cashier:
        if user.branch_id is None:
            raise PermissionDenied("This cashier is not assigned to a branch")
        if branch_id is not None and branch_id != user.branch_id:
            raise PermissionDenied("Cashiers can only work in their own branch")
        return user.branch_id

    if branch_id is None:
        branch_id = user.branch_id
    if branch_id is None:
        raise InvalidRequest("branch_id is required")
    branch = db.get(Branch, branch_id)
    if branch is None or not branch.is_active:
        raise NotFound("Branch not found", branch_id=branch_id)
    return branch_id
