from fastapi import APIRouter, status
from sqlalchemy import select

from app.deps import DbSession, ManagerUser, OwnerUser
from app.errors import Conflict, InvalidRequest, NotFound
from app.models import Branch, Role, User
from app.schemas.common import changed_fields
from app.schemas.users import UserCreate, UserOut, UserUpdate
from app.security import hash_password

router = APIRouter(prefix="/users", tags=["users"])


def _check_branch(db: DbSession, role: Role, branch_id: int | None) -> None:
    if branch_id is not None and db.get(Branch, branch_id) is None:
        raise NotFound("Branch not found", branch_id=branch_id)
    if role == Role.cashier and branch_id is None:
        raise InvalidRequest("Cashiers must be assigned to a branch")


@router.get("", response_model=list[UserOut])
def list_users(db: DbSession, _user: ManagerUser) -> list[User]:
    return list(db.scalars(select(User).order_by(User.role, User.username)))


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: DbSession, _owner: OwnerUser) -> User:
    if db.scalar(select(User.id).where(User.username == payload.username)):
        raise Conflict("Username is already taken", username=payload.username)
    _check_branch(db, payload.role, payload.branch_id)
    user = User(
        username=payload.username,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role=payload.role,
        branch_id=payload.branch_id,
    )
    db.add(user)
    db.commit()
    return user


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: DbSession, _user: ManagerUser) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFound("User not found", user_id=user_id)
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, db: DbSession, owner: OwnerUser) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFound("User not found", user_id=user_id)
    changes = changed_fields(payload, nullable=("branch_id",))

    if user.id == owner.id and (
        changes.get("is_active") is False or changes.get("role", Role.owner) != Role.owner
    ):
        raise Conflict("You cannot deactivate or demote your own account")

    if "password" in changes:
        user.password_hash = hash_password(changes.pop("password"))
    for field, value in changes.items():
        setattr(user, field, value)
    _check_branch(db, user.role, user.branch_id)
    db.commit()
    return user
