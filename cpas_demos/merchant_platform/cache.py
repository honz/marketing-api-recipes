"""
SQLite Cache Layer for Merchant CPAS Platform

Sits between merchant_cpas_backend.py and cpas_api_client.py to minimize
Graph API calls. Uses SQLite (ships with Python, zero dependencies).

Architecture:
    merchant_cpas_ui.py → merchant_cpas_backend.py → cache.py → cpas_api_client.py → Graph API

Cache strategy:
    - Catalog segment list: cached 30 min (rarely changes)
    - Partnership status per segment: cached 5 min (brand acceptances trickle in)
    - Proactive invalidation on write operations (e.g. sharing a segment)
    - Force refresh via UI button bypasses cache entirely
"""

import json
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.cpas_api_client import (
    get_owned_product_catalogs,
    get_catalog_partnership_status,
)
from shared.constants import (
    CACHE_TTL_CATALOGS,
    CACHE_TTL_PARTNERSHIPS,
)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS catalogs (
    id                  TEXT PRIMARY KEY,
    name                TEXT,
    product_count       INTEGER,
    vertical            TEXT,
    is_catalog_segment  INTEGER NOT NULL DEFAULT 0,
    merchant_bm_id      TEXT NOT NULL,
    fetched_at          REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS partnerships (
    catalog_id      TEXT NOT NULL,
    catalog_name    TEXT,
    business_id     TEXT NOT NULL,
    business_name   TEXT,
    status          TEXT NOT NULL,
    permitted_tasks TEXT,
    fetched_at      REAL NOT NULL,
    PRIMARY KEY (catalog_id, business_id)
);

CREATE TABLE IF NOT EXISTS cache_meta (
    cache_key   TEXT PRIMARY KEY,
    updated_at  REAL NOT NULL
);
"""


class CacheDB:
    """SQLite-backed cache for CPAS merchant data."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = str(Path(__file__).parent / ".cpas_cache.db")
        self._db_path = db_path
        self._connect()
        self._init_schema()

    def _connect(self):
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False, timeout=30)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.text_factory = lambda b: b.decode("utf-8", "replace")
        self._conn.row_factory = sqlite3.Row

    def _reconnect(self):
        """Reconnect if the connection is stale (e.g. DB file was deleted)."""
        try:
            self._conn.close()
        except Exception:
            pass
        self._connect()
        self._init_schema()

    def _init_schema(self):
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Freshness checks
    # ------------------------------------------------------------------

    def _set_meta(self, cache_key: str):
        self._conn.execute(
            "INSERT OR REPLACE INTO cache_meta (cache_key, updated_at) VALUES (?, ?)",
            (cache_key, time.time()),
        )

    def _get_meta(self, cache_key: str) -> Optional[float]:
        row = self._conn.execute(
            "SELECT updated_at FROM cache_meta WHERE cache_key = ?",
            (cache_key,),
        ).fetchone()
        return row["updated_at"] if row else None

    def is_fresh(self, cache_key: str, ttl_seconds: int) -> bool:
        updated_at = self._get_meta(cache_key)
        if updated_at is None:
            return False
        return (time.time() - updated_at) < ttl_seconds

    def has_data(self, merchant_bm_id: str) -> bool:
        """Check if the DB has any cached data for this merchant (ignoring TTL)."""
        row = self._conn.execute(
            "SELECT COUNT(*) as cnt FROM catalogs WHERE merchant_bm_id = ?",
            (merchant_bm_id,),
        ).fetchone()
        return row["cnt"] > 0

    def has_partnership_data(self) -> bool:
        """Check if the DB has any cached partnership data."""
        row = self._conn.execute(
            "SELECT COUNT(*) as cnt FROM partnerships",
        ).fetchone()
        return row["cnt"] > 0

    # ------------------------------------------------------------------
    # Catalogs
    # ------------------------------------------------------------------

    def get_catalogs(
        self,
        merchant_bm_id: str,
        segments_only: bool = False,
        catalogs_only: bool = False,
    ) -> List[Dict]:
        query = "SELECT * FROM catalogs WHERE merchant_bm_id = ?"
        params: list = [merchant_bm_id]

        if segments_only:
            query += " AND is_catalog_segment = 1"
        elif catalogs_only:
            query += " AND is_catalog_segment = 0"

        rows = self._conn.execute(query, params).fetchall()
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "product_count": r["product_count"],
                "vertical": r["vertical"],
                "is_catalog_segment": bool(r["is_catalog_segment"]),
            }
            for r in rows
        ]

    def store_catalogs(self, merchant_bm_id: str, catalogs: List[Dict]):
        now = time.time()
        # Clear old entries for this merchant
        self._conn.execute(
            "DELETE FROM catalogs WHERE merchant_bm_id = ?", (merchant_bm_id,)
        )
        for c in catalogs:
            self._conn.execute(
                """INSERT OR REPLACE INTO catalogs
                   (id, name, product_count, vertical, is_catalog_segment, merchant_bm_id, fetched_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    c.get("id"),
                    c.get("name"),
                    c.get("product_count"),
                    c.get("vertical"),
                    1 if c.get("is_catalog_segment") else 0,
                    merchant_bm_id,
                    now,
                ),
            )
        self._set_meta(f"catalogs:{merchant_bm_id}")
        self._conn.commit()

    # ------------------------------------------------------------------
    # Partnerships
    # ------------------------------------------------------------------

    def get_partnerships(
        self, catalog_id: Optional[str] = None, merchant_bm_id: Optional[str] = None
    ) -> List[Dict]:
        if catalog_id:
            rows = self._conn.execute(
                "SELECT * FROM partnerships WHERE catalog_id = ?", (catalog_id,)
            ).fetchall()
        elif merchant_bm_id:
            # Join with catalogs to get all partnerships for this merchant's segments
            rows = self._conn.execute(
                """SELECT p.* FROM partnerships p
                   JOIN catalogs c ON p.catalog_id = c.id
                   WHERE c.merchant_bm_id = ? AND c.is_catalog_segment = 1""",
                (merchant_bm_id,),
            ).fetchall()
        else:
            return []

        return [
            {
                "catalog_id": r["catalog_id"],
                "catalog_name": r["catalog_name"],
                "business_id": r["business_id"],
                "business_name": r["business_name"],
                "status": r["status"],
                "permitted_tasks": json.loads(r["permitted_tasks"])
                if r["permitted_tasks"]
                else [],
            }
            for r in rows
        ]

    def store_partnerships(
        self, catalog_id: str, catalog_name: str, partnerships: List[Dict]
    ):
        now = time.time()
        # Clear old entries for this catalog
        self._conn.execute(
            "DELETE FROM partnerships WHERE catalog_id = ?", (catalog_id,)
        )
        for p in partnerships:
            self._conn.execute(
                """INSERT OR REPLACE INTO partnerships
                   (catalog_id, catalog_name, business_id, business_name,
                    status, permitted_tasks, fetched_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    catalog_id,
                    catalog_name,
                    p.get("business_id"),
                    p.get("business_name"),
                    p.get("status"),
                    json.dumps(p.get("permitted_tasks", [])),
                    now,
                ),
            )
        self._set_meta(f"partnerships:{catalog_id}")
        self._conn.commit()

    # ------------------------------------------------------------------
    # Invalidation
    # ------------------------------------------------------------------

    def invalidate_segment(self, catalog_id: str):
        """Invalidate cache for a specific catalog segment."""
        self._conn.execute(
            "DELETE FROM cache_meta WHERE cache_key = ?",
            (f"partnerships:{catalog_id}",),
        )
        self._conn.execute(
            "DELETE FROM partnerships WHERE catalog_id = ?", (catalog_id,)
        )
        self._conn.commit()

    def invalidate_all_partnerships(self):
        """Invalidate only partnership cache."""
        self._conn.execute(
            "DELETE FROM cache_meta WHERE cache_key LIKE 'partnerships:%'"
        )
        self._conn.execute("DELETE FROM partnerships")
        self._conn.commit()

    def invalidate_catalog_list(self):
        """Invalidate only the catalog list cache."""
        self._conn.execute(
            "DELETE FROM cache_meta WHERE cache_key LIKE 'catalogs:%'"
        )
        self._conn.commit()

    def invalidate_all(self):
        """Clear all cached data."""
        self._conn.execute("DELETE FROM cache_meta")
        self._conn.execute("DELETE FROM catalogs")
        self._conn.execute("DELETE FROM partnerships")
        self._conn.commit()

    def close(self):
        self._conn.close()


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
    max_workers: int = 20,
) -> Tuple[List[Dict], Optional[str]]:
    """
    Get partnership status across all catalog segments with caching.

    Only fetches from API for segments whose cache is stale.
    With warm cache, makes 0 API calls.
    Stale segments are fetched in parallel using a thread pool.

    Args:
        progress_callback: Optional callable(completed, total) for progress tracking.
        max_workers: Max concurrent API requests (default 20).
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
                # Write to cache (serialized via SQLite WAL + timeout)
                cache.store_partnerships(cat_id, cat_name, partnerships or [])
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
    except sqlite3.OperationalError:
        cache._reconnect()
        cache.invalidate_segment(catalog_id)


def invalidate_all_partnerships():
    """Invalidate only partnership cache (call from partnerships/partners refresh)."""
    cache = get_cache()
    try:
        cache.invalidate_all_partnerships()
    except sqlite3.OperationalError:
        cache._reconnect()
        cache.invalidate_all_partnerships()


def invalidate_catalog_list():
    """Invalidate only the catalog list cache (call after creating a segment)."""
    cache = get_cache()
    try:
        cache.invalidate_catalog_list()
    except sqlite3.OperationalError:
        cache._reconnect()
        cache.invalidate_catalog_list()


def force_refresh_all():
    """Clear all cached data (call from UI refresh button)."""
    cache = get_cache()
    try:
        cache.invalidate_all()
    except sqlite3.OperationalError:
        cache._reconnect()
        cache.invalidate_all()
