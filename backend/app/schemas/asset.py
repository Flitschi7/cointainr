from pydantic import BaseModel, ConfigDict, model_validator
from app.core.holding_rules import holding_violations
from app.models.asset import AssetType
from typing import Optional


# --- Shared Asset Properties ---
class AssetBase(BaseModel):
    """
    Shared properties for Asset schemas.
    Used as base for create, read, and update schemas.
    """

    type: AssetType
    name: str
    assetname: str | None = None
    quantity: float
    symbol: str | None = None
    currency: str | None = None
    purchase_price: float | None = None
    buy_currency: str | None = None


# --- Asset Creation Schema ---
class AssetCreate(AssetBase):
    """
    Properties required to create an Asset.
    Inherits all fields from AssetBase and enforces the holding rules.
    """

    @model_validator(mode="after")
    def check_holding_rules(self) -> "AssetCreate":
        violations = holding_violations(self.type, self.quantity, self.purchase_price)
        if violations:
            raise ValueError("; ".join(message for _, message in violations))
        return self


# --- Asset Read Schema ---
class AssetRead(AssetBase):
    """
    Properties returned to client when reading an Asset.
    Includes the asset ID.
    """

    id: int
    model_config = ConfigDict(from_attributes=True)


# --- Asset Update Schema ---
class AssetUpdate(BaseModel):
    """
    Properties allowed for updating an Asset.
    All fields are optional.
    """

    type: Optional[AssetType] = None
    assetname: Optional[str] = None
    name: Optional[str] = None
    quantity: Optional[float] = None
    symbol: Optional[str] = None
    currency: Optional[str] = None
    purchase_price: Optional[float] = None
    buy_currency: Optional[str] = None
