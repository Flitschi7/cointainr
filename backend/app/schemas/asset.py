from pydantic import BaseModel, ConfigDict
from app.models.asset import AssetType  # Use our existing AssetType enum
from typing import Optional


# Shared properties
class AssetBase(BaseModel):
    type: AssetType
    name: str
    quantity: float
    symbol: str | None = None
    currency: str | None = None
    purchase_price: float | None = None


# Properties to receive on asset creation
class AssetCreate(AssetBase):
    pass


# Properties to return to client
class AssetRead(AssetBase):
    id: int

    # This tells Pydantic to read the data even if it's not a dict,
    # but an ORM model (or any other arbitrary object with attributes)
    model_config = ConfigDict(from_attributes=True)


class AssetUpdate(BaseModel):
    type: Optional[AssetType] = None
    name: Optional[str] = None
    quantity: Optional[float] = None
    symbol: Optional[str] = None
    currency: Optional[str] = None
    purchase_price: Optional[float] = None
