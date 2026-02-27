"""
SQLite Cache Layer for Merchant CPAS Platform

Thin re-export layer — all caching logic lives in shared/cache_manager.py.
Merchant backend and UI import from this module (unchanged import paths).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.cache_manager import (
    init_cache,
    get_cache,
    cached_get_owned_product_catalogs,
    cached_get_all_segment_partnerships,
    has_cached_partnerships,
    invalidate_segment_cache,
    invalidate_all_partnerships,
    invalidate_catalog_list,
    force_refresh_all,
)
