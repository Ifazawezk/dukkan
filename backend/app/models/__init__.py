"""All models are imported here so Base.metadata knows about every table."""

from app.models.catalog import Category, Product
from app.models.shop import Branch, ShopSettings
from app.models.user import Role, User

__all__ = ["Branch", "Category", "Product", "Role", "ShopSettings", "User"]
