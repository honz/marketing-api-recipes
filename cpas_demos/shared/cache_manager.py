"""
Shared SQLite Cache Manager for CPAS Platforms

Provides cached access to catalog and partnership data via SQLite.
Used by both the merchant platform and brand portal to ensure
consistent data regardless of which portal runs first.

Architecture:
    UI → backend → cache_manager.py → cpas_api_client.py → Graph API

Cache strategy:
    - Catalog segment list: cached 30 min (rarely changes)
    - Partnership status per segment: cached 5 min (brand acceptances trickle in)
    - Proactive invalidation on write operations (e.g. sharing a segment)
    - Force refresh via UI button bypasses cache entirely
"""

import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from .cache_db import CacheDB
from .cpas_api_client import (
    get_owned_product_catalogs,
    get_catalog_partnership_status,
)
from .constants import (
    CACHE_TTL_CATALOGS,
    CACHE_TTL_PARTNERSHIPS,
)


# ======================================================================
# Cached wrapper functions
# ======================================================================

# Module-level cache instance (set by init_cache or Streamlit cache_resource)
_cache: Optional[CacheDB] = None


def init_cache(db_path: Optional[str] = None) -> CacheDB:
    """Initialize the module-level cache. Returns the CacheDB instance."""
    global _cache
    if _cache is None:
        _cache = CacheDB(db_path)
    return _cache


def get_cache() -> CacheDB:
    """Get the cache instance, initializing with defaults if needed."""
    if _cache is None:
        init_cache()
    return _cache


def cached_get_owned_product_catalogs(
    access_token: str,
    business_id: str,
    segments_only: bool = False,
    catalogs_only: bool = False,
    force_refresh: bool = False,
) -> Tuple[Optional[List], Optional[str]]:
    """
    Get product catalogs with SQLite caching.
    On cache hit, returns stored data (0 API calls).
    On cache miss, fetches from API and stores result.
    """
    cache = get_cache()
    cache_key = f"catalogs:{business_id}"

    if not force_refresh and cache.is_fresh(cache_key, CACHE_TTL_CATALOGS):
        data = cache.get_catalogs(business_id, segments_only, catalogs_only)
        return data, None

    # Cache miss — fetch all catalogs from API (no filter, store everything)
    all_catalogs, error = get_owned_product_catalogs(
        access_token, business_id, segments_only=False, catalogs_only=False
    )

    if error:
        # On API error, return stale cache if available
        stale = cache.get_catalogs(business_id, segments_only, catalogs_only)
        if stale:
            return stale, None
        return None, error

    # Store all catalogs, then filter for return
    cache.store_catalogs(business_id, all_catalogs or [])

    # Apply filters for the caller
    data = all_catalogs or []
    if segments_only:
        data = [c for c in data if c.get("is_catalog_segment", False)]
    elif catalogs_only:
        data = [c for c in data if not c.get("is_catalog_segment", False)]

    return data, None


def cached_get_all_segment_partnerships(
    access_token: str,
    merchant_business_id: str,
    force_refresh: bool = False,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    max_workers: int = 10,
) -> Tuple[List[Dict], Optional[str]]:
    """
    Get partnership status across all catalog segments with caching.

    Only fetches from API for segments whose cache is stale.
    With warm cache, makes 0 API calls.
    Stale segments are fetched in parallel using a thread pool.

    Args:
        progress_callback: Optional callable(completed, total) for progress tracking.
        max_workers: Max concurrent API requests (default 10).
    """
    cache = get_cache()

    # Step 1: Get catalog segments (cached)
    segments, error = cached_get_owned_product_catalogs(
        access_token, merchant_business_id,
        segments_only=True, force_refresh=force_refresh,
    )

    if error:
        return [], error

    if not segments:
        return [], None

    all_partnerships = []
    stale_segments = []

    # Step 2: Separate cached vs stale segments
    for segment in segments:
        catalog_id = segment.get("id")
        catalog_name = segment.get("name", "Unknown")
        if not catalog_id:
            continue

        cache_key = f"partnerships:{catalog_id}"
        if not force_refresh and cache.is_fresh(cache_key, CACHE_TTL_PARTNERSHIPS):
            cached = cache.get_partnerships(catalog_id=catalog_id)
            all_partnerships.extend(cached)
        else:
            stale_segments.append({"id": catalog_id, "name": catalog_name})

    if not stale_segments:
        return all_partnerships, None

    # Step 3: Fetch stale segments in parallel
    total = len(stale_segments)
    completed = 0

    def _fetch_one(seg):
        """Fetch partnership status for a single segment (runs in thread)."""
        cat_id = seg["id"]
        partnerships, err = get_catalog_partnership_status(access_token, cat_id)
        return seg, partnerships, err

    with ThreadPoolExecutor(max_workers=min(max_workers, total)) as executor:
        futures = {executor.submit(_fetch_one, seg): seg for seg in stale_segments}

        for future in as_completed(futures):
            seg, partnerships, err = future.result()
            cat_id = seg["id"]
            cat_name = seg["name"]

            if err:
                stale = cache.get_partnerships(catalog_id=cat_id)
                if stale:
                    all_partnerships.extend(stale)
            else:
                # Write to cache (thread-safe via lock in store_partnerships)
                try:
                    cache.store_partnerships(cat_id, cat_name, partnerships or [])
                except (sqlite3.OperationalError, sqlite3.DatabaseError):
                    pass  # Skip cache write on DB error, data still returned
                for p in (partnerships or []):
                    p["catalog_id"] = cat_id
                    p["catalog_name"] = cat_name
                    all_partnerships.append(p)

            completed += 1
            if progress_callback:
                progress_callback(completed, total)

    return all_partnerships, None


def has_cached_partnerships() -> bool:
    """Check if partnership data is already cached (no API calls needed)."""
    cache = get_cache()
    return cache.has_partnership_data()


def invalidate_segment_cache(catalog_id: str):
    """Invalidate cache for a specific segment (call after sharing)."""
    cache = get_cache()
    try:
        cache.invalidate_segment(catalog_id)
    except (sqlite3.OperationalError, sqlite3.DatabaseError):
        cache._reconnect()
        cache.invalidate_segment(catalog_id)


def invalidate_all_partnerships():
    """Invalidate only partnership cache (call from partnerships/partners refresh)."""
    cache = get_cache()
    try:
        cache.invalidate_all_partnerships()
    except (sqlite3.OperationalError, sqlite3.DatabaseError):
        cache._reconnect()
        cache.invalidate_all_partnerships()


def invalidate_catalog_list():
    """Invalidate only the catalog list cache (call after creating a segment)."""
    cache = get_cache()
    try:
        cache.invalidate_catalog_list()
    except (sqlite3.OperationalError, sqlite3.DatabaseError):
        cache._reconnect()
        cache.invalidate_catalog_list()


def force_refresh_all():
    """Clear all cached data (call from UI refresh button)."""
    cache = get_cache()
    try:
        cache.invalidate_all()
    except (sqlite3.OperationalError, sqlite3.DatabaseError):
        cache._reconnect()
        cache.invalidate_all()
