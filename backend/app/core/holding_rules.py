"""
Holding value rules (see GLOSSARY.md, "Holding" and "Purchase price").

Enforced when a holding is created or updated. Rows that already break a rule
still load; `app.tools.check_holdings` lists them so they can be fixed.
"""

import math
from typing import Optional

QUANTITY_NOT_FINITE = "quantity must be a finite number"
NEGATIVE_NON_CASH = "negative quantity is only allowed for cash"
PRICE_NOT_FINITE = "purchase price must be a finite number"
NEGATIVE_PRICE = "purchase price must not be negative"


def holding_violations(
    asset_type: str, quantity: float, purchase_price: Optional[float]
) -> list[tuple[str, str]]:
    """
    Check one holding against the rules.

    Args:
        asset_type: "cash", "stock", "crypto" or "derivative" (any case)
        quantity: units held; 0 is allowed, negative only for cash
        purchase_price: average cost per unit, or None; 0 means a free acquisition

    Returns:
        (field, message) pairs, empty when the holding is valid
    """
    violations = []
    is_cash = str(getattr(asset_type, "value", asset_type)).lower() == "cash"

    if quantity is None or not math.isfinite(quantity):
        violations.append(("quantity", QUANTITY_NOT_FINITE))
    elif quantity < 0 and not is_cash:
        violations.append(("quantity", NEGATIVE_NON_CASH))

    if purchase_price is not None:
        if not math.isfinite(purchase_price):
            violations.append(("purchase_price", PRICE_NOT_FINITE))
        elif purchase_price < 0:
            violations.append(("purchase_price", NEGATIVE_PRICE))

    return violations
