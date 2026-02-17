"""
Merchant Platform Backend

Backend logic for the merchant CPAS platform.
Provides high-level functions for the merchant UI workflow.

Partnership status is derived from catalog-level endpoints:
- {catalog_id}/collaborative_ads_share_settings → shared with (attempt list)
- {catalog_id}/agencies → accepted partners (success list)

Uses SQLite cache layer (cache.py) to minimize API calls.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Cached functions — hit SQLite first, API only on cache miss
from cache import (
    cached_get_owned_product_catalogs,
    cached_get_all_segment_partnerships,
    invalidate_segment_cache,
    invalidate_catalog_list,
    force_refresh_all,
    init_cache,
    get_cache,
)

# Non-cacheable imports — always hit API directly
from shared.cpas_api_client import (
    validate_access_token,
    get_business_info,
    share_catalog_segment,
    get_catalog_products,
    get_catalog_partnership_status,
    create_catalog_segment as api_create_catalog_segment,
    share_segment_with_utm,
)


def validate_merchant_setup(
    access_token: str,
    merchant_business_id: str,
) -> Tuple[Dict, Optional[str]]:
    """Validate the merchant setup (token + BM)."""
    result = {
        "token_valid": False,
        "merchant_valid": False,
        "merchant_info": None,
        "user_info": None,
    }

    user_info, error = validate_access_token(access_token)
    if error:
        return result, f"Invalid access token: {error}"

    result["token_valid"] = True
    result["user_info"] = user_info

    merchant_info, error = get_business_info(access_token, merchant_business_id)
    if error:
        return result, f"Invalid merchant Business Manager: {error}"

    result["merchant_valid"] = True
    result["merchant_info"] = merchant_info

    return result, None


def get_dashboard_stats(
    access_token: str,
    merchant_business_id: str,
    force_refresh: bool = False,
) -> Dict:
    """Get dashboard statistics for the merchant (cached)."""
    stats = {
        "pending_requests": 0,
        "accepted_partners": 0,
        "catalog_segments": 0,
        "total_partnerships": 0,
    }

    segments, _ = cached_get_owned_product_catalogs(
        access_token, merchant_business_id,
        segments_only=True, force_refresh=force_refresh,
    )
    if segments:
        stats["catalog_segments"] = len(segments)

    partnerships, _ = cached_get_all_segment_partnerships(
        access_token, merchant_business_id, force_refresh=force_refresh,
    )
    if partnerships:
        stats["total_partnerships"] = len(partnerships)
        pending_count = 0
        accepted_count = 0
        for p in partnerships:
            if p.get("status") == "PENDING":
                pending_count += 1
            elif p.get("status") == "ACCEPTED":
                accepted_count += 1
        stats["pending_requests"] = pending_count
        stats["accepted_partners"] = accepted_count

    return stats


def get_all_partnerships(
    access_token: str,
    merchant_business_id: str,
    status_filter: Optional[str] = None,
    force_refresh: bool = False,
) -> Tuple[Optional[List], Optional[str]]:
    """Get all partnerships across catalog segments (cached)."""
    partnerships, error = cached_get_all_segment_partnerships(
        access_token, merchant_business_id, force_refresh=force_refresh,
    )

    if error:
        return None, error

    if status_filter:
        partnerships = [p for p in partnerships if p.get("status") == status_filter]

    return partnerships, None


def get_pending_requests(
    access_token: str,
    merchant_business_id: str,
    force_refresh: bool = False,
) -> Tuple[Optional[List], Optional[str]]:
    """Get pending partnership requests (cached)."""
    return get_all_partnerships(
        access_token, merchant_business_id,
        status_filter="PENDING", force_refresh=force_refresh,
    )


def get_active_partners(
    access_token: str,
    merchant_business_id: str,
    force_refresh: bool = False,
) -> Tuple[Optional[List], Optional[str]]:
    """Get active brand partners (cached)."""
    return get_all_partnerships(
        access_token, merchant_business_id,
        status_filter="ACCEPTED", force_refresh=force_refresh,
    )


def get_catalog_segments(
    access_token: str,
    merchant_business_id: str,
    force_refresh: bool = False,
) -> Tuple[Optional[List], Optional[str]]:
    """Get catalog segments owned by the merchant (cached)."""
    return cached_get_owned_product_catalogs(
        access_token, merchant_business_id,
        segments_only=True, force_refresh=force_refresh,
    )


def get_full_catalogs(
    access_token: str,
    merchant_business_id: str,
    force_refresh: bool = False,
) -> Tuple[Optional[List], Optional[str]]:
    """Get full catalogs owned by the merchant (cached)."""
    return cached_get_owned_product_catalogs(
        access_token, merchant_business_id,
        catalogs_only=True, force_refresh=force_refresh,
    )


def share_catalog_with_brand(
    access_token: str,
    catalog_id: str,
    brand_business_id: str,
    catalog_name: str = "",
    utm_source: str = "",
    utm_medium: str = "",
    utm_campaign: str = "",
) -> Tuple[bool, Optional[str]]:
    """Share a catalog segment with a brand via /agencies endpoint.
    On success, eagerly fetches and caches that segment's partnerships
    so the share appears immediately on the Pending Requests tab.
    """
    success, error = share_catalog_segment(
        access_token, catalog_id, brand_business_id,
        utm_source=utm_source or None,
        utm_medium=utm_medium or None,
        utm_campaign=utm_campaign or None,
    )

    if success:
        # Invalidate stale cache for this segment, then eagerly re-fetch
        invalidate_segment_cache(catalog_id)
        partnerships, _ = get_catalog_partnership_status(access_token, catalog_id)
        if partnerships is not None:
            cache = get_cache()
            cache.store_partnerships(catalog_id, catalog_name, partnerships)

    return success, error


def refresh_all_data(
    access_token: str,
    merchant_business_id: str,
) -> Dict:
    """Force refresh all cached data. Returns fresh dashboard stats."""
    force_refresh_all()
    return get_dashboard_stats(access_token, merchant_business_id, force_refresh=True)


# =============================================================================
# Merchant Name
# =============================================================================

def get_merchant_name(
    access_token: str,
    merchant_business_id: str,
) -> str:
    """Get merchant name from BM ID. Used on startup."""
    info, error = get_business_info(access_token, merchant_business_id)
    if error:
        return merchant_business_id
    return info.get("name", merchant_business_id)


# =============================================================================
# Catalog Segment Creation
# =============================================================================

def get_brand_values(
    access_token: str,
    catalog_id: str,
) -> Tuple[Optional[List[str]], Optional[str]]:
    """Get distinct brand values from a catalog's products."""
    products, error = get_catalog_products(access_token, catalog_id, fields="brand")
    if error:
        return None, error

    brands = set()
    for product in (products or []):
        brand = product.get("brand")
        if brand:
            brands.add(brand)

    return sorted(brands), None


def create_catalog_segment(
    access_token: str,
    merchant_bm_id: str,
    catalog_id: str,
    segment_name: str,
    brand_filter_values: List[str],
) -> Tuple[Optional[str], Optional[str]]:
    """
    Create a catalog segment filtered by brand values.

    Uses POST /{business_id}/owned_product_catalogs with parent_catalog_id
    and catalog_segment_filter as per the Collaborative Ads documentation.
    Invalidates catalog cache on success.
    """
    # Build WCA rule format: {"and": [{"or": [{"brand": {"eq": "X"}}, ...]}]}
    brand_clauses = [{"brand": {"eq": v}} for v in brand_filter_values]
    catalog_segment_filter = {"and": [{"or": brand_clauses}]}

    segment_id, error = api_create_catalog_segment(
        access_token, merchant_bm_id, catalog_id, segment_name, catalog_segment_filter,
    )

    if error:
        return None, error

    # Invalidate catalog cache so the new segment shows up in lists
    invalidate_catalog_list()

    return segment_id, None
