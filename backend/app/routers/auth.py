from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.db_types import utcnow
from app.deps import CurrentUser, DbSession
from app.models import User
from app.schemas.users import ChangePasswordIn, TokenOut, UserOut
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(db: DbSession, form: Annotated[OAuth2PasswordRequestForm, Depends()]) -> TokenOut:
    """Exchange a username and password for a bearer token (OAuth2 password flow)."""
    username = form.username.strip().lower()
    user = db.scalar(select(User).where(User.username == username))
    password_ok = verify_password(form.password, user.password_hash if user else None)
    if user is None or not password_ok or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user.last_login_at = utcnow()
    db.commit()
    token, expires_at = create_access_token(user.id, user.role.value)
    return TokenOut(access_token=token, expires_at=expires_at, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> User:
    return user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(payload: ChangePasswordIn, user: CurrentUser, db: DbSession) -> None:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is wrong")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
