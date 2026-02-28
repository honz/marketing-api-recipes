"""
Session-State Cache for Brand CPAS Dashboard

Lightweight in-memory cache using Streamlit session state.
Sits between brand_dashboard_ui.py and brand_dashboard_backend.py to prevent
redundant API calls on every Streamlit rerun.

Architecture:
    brand_dashboard_ui.py → cache.py → shared SQLite DB (populated by merchant platform)

    For pending shares, this module reads directly from the shared SQLite DB
    which is kept up-to-date by the merchant platform (writes on share, full
    resync on merchant refresh). This avoids the expensive full API resync
    that would otherwise re-fetch ALL segments and ALL partnerships for ALL
    brands. Falls back to a one-time full sync only if the DB is empty.

Cache strategy:
    - Data is stored in st.session_state with timestamps
    - TTL-based expiration (configurable per data type)
    - Data loaded once after validation, served from cache on subsequent reruns
    - Invalidation after write operations (e.g. sending a collab request)
    - Explicit Refresh button to re-fetch from API
"""

import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.cache_manager import (
    get_cache,
    cached_get_all_segment_partnerships,
)

from brand_dashboard_backend import (
    get_brand_shared_catalogs as _api_get_shared_catalogs,
    check_collab_request_status as _api_check_collab_status,
)


# Cache TTLs (seconds)
CACHE_TTL_SHARED_CATALOGS = 300     # 5 min
CACHE_TTL_COLLAB_STATUS = 300       # 5 min
CACHE_TTL_PENDING_SHARES = 300      # 5 min

# Session state keys
_KEY_SHARED_CATALOGS = "_cache_shared_catalogs"
_KEY_COLLAB_STATUS = "_cache_collab_status"
_KEY_PENDING_SHARES = "_cache_pending_shares"


def _get_cached(key: str, ttl: int) -> Optional[Any]:
    """Return cached value if fresh, else None."""
    entry = st.session_state.get(key)
    if entry is None:
        return None
    if (time.time() - entry["ts"]) > ttl:
        return None  # expired
    return entry["data"]


def _set_cached(key: str, data: Any):
    """Store data in session-state cache with current timestamp."""
    st.session_state[key] = {"data": data, "ts": time.time()}


# ======================================================================
# Cached API functions
# ======================================================================

def cached_get_shared_catalogs(
    brand_token: str,
    brand_bm_id: str,
    merchant_token: str = None,
    merchant_bm_id: str = None,
    force_refresh: bool = False,
) -> Tuple[Optional[List], Optional[str]]:
    """
    Get shared catalogs with session-state caching.
    If merchant credentials are provided, filters to only this merchant's catalogs.
    Returns (catalogs, error). On cache hit, makes 0 API calls.
    """
    if not force_refresh:
        cached = _get_cached(_KEY_SHARED_CATALOGS, CACHE_TTL_SHARED_CATALOGS)
        if cached is not None:
            return cached["result"], cached["error"]

    result, error = _api_get_shared_catalogs(
        brand_token, brand_bm_id,
        merchant_token=merchant_token,
        merchant_bm_id=merchant_bm_id,
    )
    _set_cached(_KEY_SHARED_CATALOGS, {"result": result, "error": error})
    return result, error


def cached_check_collab_status(
    brand_token: str,
    brand_bm_id: str,
    merchant_bm_id: str,
    force_refresh: bool = False,
) -> Dict:
    """
    Check collaboration request status with session-state caching.
    On cache hit, makes 0 API calls.
    """
    if not force_refresh:
        cached = _get_cached(_KEY_COLLAB_STATUS, CACHE_TTL_COLLAB_STATUS)
        if cached is not None:
            return cached

    result = _api_check_collab_status(brand_token, brand_bm_id, merchant_bm_id)
    _set_cached(_KEY_COLLAB_STATUS, result)
    return result


def cached_get_pending_shares(
    merchant_token: str,
    brand_bm_id: str,
    merchant_bm_id: str,
    force_refresh: bool = False,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> Tuple[Optional[List], Optional[str]]:
    """
    Get pending segment shares with session-state caching.

    Reads directly from the shared SQLite DB (populated by the merchant
    platform), avoiding the expensive full API resync. Only falls back to
    a full sync if the DB has no data at all (first-time bootstrap).

    Returns (list_of_shares, error). On cache hit, makes 0 API calls.
    """
    # 1. Session-state cache (skip on force_refresh)
    if not force_refresh:
        cached = _get_cached(_KEY_PENDING_SHARES, CACHE_TTL_PENDING_SHARES)
        if cached is not None:
            return cached["result"], cached["error"]

    # 2. Read from shared SQLite DB
    db = get_cache()
    db_populated = db.has_data(merchant_bm_id) or db.has_partnership_data()

    if db_populated:
        # DB has data — query only this brand's PENDING shares (0 API calls)
        partnerships = db.get_partnerships(
            merchant_bm_id=merchant_bm_id,
            business_id=brand_bm_id,
            status="PENDING",
        )
        pending = [
            {
                "segment_id": p["catalog_id"],
                "segment_name": p["catalog_name"],
                "product_count": p.get("product_count"),
                "status": p["status"],
                "business_id": p["business_id"],
                "business_name": p["business_name"],
            }
            for p in partnerships
        ]
        _set_cached(_KEY_PENDING_SHARES, {"result": pending, "error": None})
        return pending, None

    # 3. DB is empty — one-time full sync to bootstrap
    all_partnerships, error = cached_get_all_segment_partnerships(
        merchant_token, merchant_bm_id,
        force_refresh=False,
        progress_callback=progress_callback,
    )

    if error:
        _set_cached(_KEY_PENDING_SHARES, {"result": None, "error": error})
        return None, error

    pending = [
        {
            "segment_id": p["catalog_id"],
            "segment_name": p["catalog_name"],
            "product_count": None,
            "status": p["status"],
            "business_id": p["business_id"],
            "business_name": p["business_name"],
        }
        for p in all_partnerships
        if p.get("business_id") == brand_bm_id and p.get("status") == "PENDING"
    ]

    _set_cached(_KEY_PENDING_SHARES, {"result": pending, "error": None})
    return pending, None


# ======================================================================
# Cache state queries
# ======================================================================

def has_cached_shared_catalogs() -> bool:
    """Check if shared catalogs data is cached (any age)."""
    return _KEY_SHARED_CATALOGS in st.session_state


def has_cached_pending_shares() -> bool:
    """Check if pending shares data is cached (any age)."""
    return _KEY_PENDING_SHARES in st.session_state


# ======================================================================
# Invalidation
# ======================================================================

def invalidate_shared_catalogs():
    """Invalidate shared catalogs cache."""
    st.session_state.pop(_KEY_SHARED_CATALOGS, None)


def invalidate_collab_status():
    """Invalidate collaboration request status cache."""
    st.session_state.pop(_KEY_COLLAB_STATUS, None)


def invalidate_pending_shares():
    """Invalidate pending shares cache."""
    st.session_state.pop(_KEY_PENDING_SHARES, None)


def invalidate_all():
    """Clear all cached data."""
    invalidate_shared_catalogs()
    invalidate_collab_status()
    invalidate_pending_shares()


def optimistic_accept_segment(segment_id: str, segment_name: str, product_count):
    """
    After a successful accept_segment_share() call, update caches locally
    without re-fetching from the API. Moves the segment from pending to accepted.
    """
    # Remove from pending shares cache
    entry = st.session_state.get(_KEY_PENDING_SHARES)
    if entry and entry.get("data"):
        pending_list = entry["data"].get("result") or []
        entry["data"]["result"] = [
            s for s in pending_list if s.get("segment_id") != segment_id
        ]

    # Add to shared catalogs cache
    entry = st.session_state.get(_KEY_SHARED_CATALOGS)
    if entry and entry.get("data"):
        catalogs = entry["data"].get("result")
        if catalogs is None:
            catalogs = []
            entry["data"]["result"] = catalogs
        catalogs.append({
            "id": segment_id,
            "name": segment_name,
            "product_count": product_count,
        })

    # Also update the shared SQLite cache so merchant platform sees it immediately
    try:
        db = get_cache()
        brand_bm_id = st.session_state.get("brand_bm_id")
        if brand_bm_id:
            db.update_partnership_status(segment_id, brand_bm_id, "ACCEPTED")
    except Exception:
        pass  # non-critical, merchant refresh will fix
