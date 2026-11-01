"""All models are imported here so Base.metadata knows about every table."""

from app.models.shop import Branch, ShopSettings
from app.models.user import Role, User

__all__ = ["Branch", "Role", "ShopSettings", "User"]
