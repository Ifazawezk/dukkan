"""All models are imported here so Base.metadata knows about every table."""

from app.models.catalog import Category, Product
from app.models.inventory import AdjustmentReason, MovementKind, StockLevel, StockMovement
from app.models.purchasing import (
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
    Supplier,
)
from app.models.sales import Payment, PaymentMethod, Sale, SaleItem, SaleStatus
from app.models.shop import Branch, DocumentCounter, ShopSettings
from app.models.user import Role, User

__all__ = [
    "AdjustmentReason",
    "Branch",
    "Category",
    "DocumentCounter",
    "MovementKind",
    "Payment",
    "PaymentMethod",
    "Product",
    "PurchaseOrder",
    "PurchaseOrderItem",
    "PurchaseOrderStatus",
    "Role",
    "Sale",
    "SaleItem",
    "SaleStatus",
    "ShopSettings",
    "StockLevel",
    "StockMovement",
    "Supplier",
    "User",
]
