from fastapi import APIRouter

from app.deps import CurrentUser, DbSession, OwnerUser
from app.models import ShopSettings
from app.schemas.common import changed_fields
from app.schemas.shop import ShopSettingsOut, ShopSettingsUpdate
from app.services.shop import get_shop_settings

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=ShopSettingsOut)
def read_settings(db: DbSession, _user: CurrentUser) -> ShopSettings:
    settings = get_shop_settings(db)
    db.commit()
    return settings


@router.patch("", response_model=ShopSettingsOut)
def update_settings(payload: ShopSettingsUpdate, db: DbSession, _owner: OwnerUser) -> ShopSettings:
    settings = get_shop_settings(db)
    for field, value in changed_fields(payload).items():
        setattr(settings, field, value)
    db.commit()
    return settings
