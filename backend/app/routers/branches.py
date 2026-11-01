from fastapi import APIRouter, status
from sqlalchemy import select

from app.deps import CurrentUser, DbSession, OwnerUser
from app.errors import Conflict, NotFound
from app.models import Branch
from app.schemas.common import changed_fields
from app.schemas.shop import BranchCreate, BranchOut, BranchUpdate

router = APIRouter(prefix="/branches", tags=["branches"])


@router.get("", response_model=list[BranchOut])
def list_branches(db: DbSession, _user: CurrentUser) -> list[Branch]:
    return list(db.scalars(select(Branch).order_by(Branch.id)))


@router.post("", response_model=BranchOut, status_code=status.HTTP_201_CREATED)
def create_branch(payload: BranchCreate, db: DbSession, _owner: OwnerUser) -> Branch:
    if db.scalar(select(Branch.id).where(Branch.code == payload.code)):
        raise Conflict("Branch code is already used", code=payload.code)
    branch = Branch(**payload.model_dump())
    db.add(branch)
    db.commit()
    return branch


@router.patch("/{branch_id}", response_model=BranchOut)
def update_branch(
    branch_id: int, payload: BranchUpdate, db: DbSession, _owner: OwnerUser
) -> Branch:
    branch = db.get(Branch, branch_id)
    if branch is None:
        raise NotFound("Branch not found", branch_id=branch_id)
    for field, value in changed_fields(payload).items():
        setattr(branch, field, value)
    db.commit()
    return branch
