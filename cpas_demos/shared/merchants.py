"""
India CPAS Merchants Configuration

Hardcoded merchant configurations for India quick commerce and delivery platforms.
Business Manager IDs are loaded from config.py if available, otherwise use placeholders.
"""

from typing import Dict, List, Optional

# Try to import config for merchant BM IDs
try:
    import config
    _MERCHANT_BM_IDS = getattr(config, 'MERCHANT_BM_IDS', {})
except ImportError:
    _MERCHANT_BM_IDS = {}


def _get_bm_id(merchant_key: str, placeholder: str) -> str:
    """Get BM ID from config or return placeholder."""
    config_id = _MERCHANT_BM_IDS.get(merchant_key)
    return config_id if config_id else placeholder


# India CPAS Merchants
# Business IDs are loaded from config.py if available
INDIA_MERCHANTS: Dict[str, Dict] = {
    "blinkit": {
        "name": "Blinkit",
        "business_id": _get_bm_id("blinkit", "PLACEHOLDER_BLINKIT_BM_ID"),
        "category": "Quick Commerce",
        "description": "India's last minute app - groceries delivered in 10 minutes",
        "logo_emoji": "🛒",
        "website": "https://blinkit.com",
        "verticals": ["Grocery", "Personal Care", "Baby Care", "Pet Care"],
    },
    "swiggy": {
        "name": "Swiggy",
        "business_id": _get_bm_id("swiggy", "PLACEHOLDER_SWIGGY_BM_ID"),
        "category": "Food & Grocery Delivery",
        "description": "Food, groceries, and more delivered to your door",
        "logo_emoji": "🍔",
        "website": "https://swiggy.com",
        "verticals": ["Food", "Grocery (Instamart)", "Genie"],
    },
    "zepto": {
        "name": "Zepto",
        "business_id": _get_bm_id("zepto", "PLACEHOLDER_ZEPTO_BM_ID"),
        "category": "Quick Commerce",
        "description": "Groceries delivered in 10 minutes",
        "logo_emoji": "⚡",
        "website": "https://zepto.com",
        "verticals": ["Grocery", "Fruits & Vegetables", "Dairy", "Personal Care"],
    },
    "bigbasket": {
        "name": "BigBasket",
        "business_id": _get_bm_id("bigbasket", "PLACEHOLDER_BIGBASKET_BM_ID"),
        "category": "Online Grocery",
        "description": "India's largest online grocery store",
        "logo_emoji": "🧺",
        "website": "https://bigbasket.com",
        "verticals": ["Grocery", "Fresh Produce", "Household", "Beauty"],
    },
    "amazon_fresh": {
        "name": "Amazon Fresh",
        "business_id": _get_bm_id("amazon_fresh", "PLACEHOLDER_AMAZON_FRESH_BM_ID"),
        "category": "Quick Commerce",
        "description": "Fresh groceries from Amazon",
        "logo_emoji": "📦",
        "website": "https://amazon.in/fresh",
        "verticals": ["Grocery", "Fresh", "Household"],
    },
}


def get_merchant_by_key(merchant_key: str) -> Optional[Dict]:
    """
    Get merchant configuration by key.

    Args:
        merchant_key: The merchant key (e.g., 'blinkit', 'swiggy')

    Returns:
        Merchant configuration dict or None if not found
    """
    merchant = INDIA_MERCHANTS.get(merchant_key)
    if merchant:
        return {"key": merchant_key, **merchant}
    return None


def get_merchant_by_business_id(business_id: str) -> Optional[Dict]:
    """
    Get merchant configuration by Business Manager ID.

    Args:
        business_id: The Business Manager ID

    Returns:
        Merchant configuration dict or None if not found
    """
    for key, merchant in INDIA_MERCHANTS.items():
        if merchant.get("business_id") == business_id:
            return {"key": key, **merchant}
    return None


def list_all_merchants() -> List[Dict]:
    """
    List all available merchants.

    Returns:
        List of merchant configuration dicts with keys included
    """
    return [{"key": key, **merchant} for key, merchant in INDIA_MERCHANTS.items()]


def list_active_merchants() -> List[Dict]:
    """
    List merchants that have real Business Manager IDs configured.

    Returns:
        List of merchant configuration dicts that have non-placeholder BM IDs
    """
    return [
        {"key": key, **merchant}
        for key, merchant in INDIA_MERCHANTS.items()
        if not merchant.get("business_id", "").startswith("PLACEHOLDER")
    ]


def update_merchant_business_id(merchant_key: str, business_id: str) -> bool:
    """
    Update a merchant's Business Manager ID.

    Args:
        merchant_key: The merchant key
        business_id: The new Business Manager ID

    Returns:
        True if updated, False if merchant not found
    """
    if merchant_key in INDIA_MERCHANTS:
        INDIA_MERCHANTS[merchant_key]["business_id"] = business_id
        return True
    return False
