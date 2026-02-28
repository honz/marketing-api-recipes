"""
Shared SQLite Cache DB for CPAS Demos

Both the merchant platform and brand portal use this single SQLite database
to cache CPAS partnership data.  The DB lives at shared/.cpas_cache.db so
that data written by the merchant platform (e.g. partnership status) can be
read instantly by the brand portal without redundant API calls.

Thread-safe: all writes are guarded by a threading.Lock and the DB uses WAL
journal mode for concurrent readers.
"""

import json
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional


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
        self._lock = threading.Lock()
        try:
            self._connect()
            self._init_schema()
        except (sqlite3.OperationalError, sqlite3.DatabaseError):
            # Corrupted DB or stale WAL/SHM files — wipe and recreate
            try:
                self._conn.close()
            except Exception:
                pass
            for suffix in ("", "-wal", "-shm"):
                try:
                    os.remove(self._db_path + suffix)
                except OSError:
                    pass
            self._connect()
            self._init_schema()

    def _connect(self):
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False, timeout=30)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.text_factory = lambda b: b.decode("utf-8", "replace")
        self._conn.row_factory = sqlite3.Row

    def _reconnect(self):
        """Reconnect. If the DB file is corrupted, delete and recreate it."""
        try:
            self._conn.close()
        except Exception:
            pass
        # If the DB file is corrupted, remove it so we start fresh
        try:
            self._connect()
            self._conn.execute("SELECT 1 FROM cache_meta LIMIT 1")
        except (sqlite3.DatabaseError, sqlite3.OperationalError):
            try:
                self._conn.close()
            except Exception:
                pass
            for suffix in ("", "-wal", "-shm"):
                try:
                    os.remove(self._db_path + suffix)
                except OSError:
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
        with self._lock:
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
        self,
        catalog_id: Optional[str] = None,
        merchant_bm_id: Optional[str] = None,
        business_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict]:
        if catalog_id:
            query = "SELECT * FROM partnerships WHERE catalog_id = ?"
            params: list = [catalog_id]
        elif merchant_bm_id:
            # Join with catalogs to get all partnerships for this merchant's segments
            query = """SELECT p.*, c.product_count FROM partnerships p
                   JOIN catalogs c ON p.catalog_id = c.id
                   WHERE c.merchant_bm_id = ? AND c.is_catalog_segment = 1"""
            params = [merchant_bm_id]
        else:
            return []

        if business_id:
            query += " AND business_id = ?"
            params.append(business_id)
        if status:
            query += " AND status = ?"
            params.append(status)

        rows = self._conn.execute(query, params).fetchall()

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
                "product_count": r["product_count"] if "product_count" in r.keys() else None,
            }
            for r in rows
        ]

    def store_partnerships(
        self, catalog_id: str, catalog_name: str, partnerships: List[Dict]
    ):
        now = time.time()
        with self._lock:
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

    def update_partnership_status(self, catalog_id: str, business_id: str, new_status: str):
        """Update status for a single partnership (e.g. PENDING -> ACCEPTED)."""
        with self._lock:
            self._conn.execute(
                "UPDATE partnerships SET status = ?, fetched_at = ? WHERE catalog_id = ? AND business_id = ?",
                (new_status, time.time(), catalog_id, business_id),
            )
            self._conn.commit()

    # ------------------------------------------------------------------
    # Invalidation
    # ------------------------------------------------------------------

    def invalidate_segment(self, catalog_id: str):
        """Invalidate cache for a specific catalog segment."""
        with self._lock:
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
        with self._lock:
            self._conn.execute(
                "DELETE FROM cache_meta WHERE cache_key LIKE 'partnerships:%'"
            )
            self._conn.execute("DELETE FROM partnerships")
            self._conn.commit()

    def invalidate_catalog_list(self):
        """Invalidate only the catalog list cache."""
        with self._lock:
            self._conn.execute(
                "DELETE FROM cache_meta WHERE cache_key LIKE 'catalogs:%'"
            )
            self._conn.commit()

    def invalidate_all(self):
        """Clear all cached data."""
        with self._lock:
            self._conn.execute("DELETE FROM cache_meta")
            self._conn.execute("DELETE FROM catalogs")
            self._conn.execute("DELETE FROM partnerships")
            self._conn.commit()

    def close(self):
        self._conn.close()
