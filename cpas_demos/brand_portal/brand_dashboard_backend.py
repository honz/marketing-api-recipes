"""
Brand Dashboard Backend (Merchant-Hosted)

Backend logic for the brand CPAS dashboard hosted by a merchant.

Dual-token model:
- Merchant's token (from config) — used for merchant-side API calls
  (show merchant name, filter shared catalogs to this merchant)
- Brand's token (entered in UI) — used for brand-side API calls
  (validate brand, view shared catalogs, send collaboration requests)

All data is retrieved from the brand's perspective using efficient
single-call APIs (client_product_catalogs, collaboration_requests).
No iteration over merchant segments is needed.
"""

import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import requests as http_requests

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.cpas_api_client import (
    validate_access_token,
    get_business_info,
    get_shared_catalog_segments,
    get_owned_product_catalogs,
    send_collaboration_request,
    get_collaboration_requests,
)
from shared.constants import GRAPH_API_VERSION, RequesterType


def get_merchant_info(
    merchant_token: str,
    merchant_bm_id: str,
) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Get merchant business info using the merchant's token.
    Used to display the merchant name in the dashboard header.
    """
    return get_business_info(merchant_token, merchant_bm_id)


def validate_brand(
    brand_token: str,
    brand_bm_id: str,
) -> Tuple[Dict, Optional[str]]:
    """
    Validate brand credentials (token + Business Manager ID).

    Returns:
        Tuple of (result_dict, error_message)
        result_dict contains: token_valid, brand_valid, brand_info, user_info
    """
    result = {
        "token_valid": False,
        "brand_valid": False,
        "brand_info": None,
        "user_info": None,
    }

    user_info, error = validate_access_token(brand_token)
    if error:
        return result, f"Invalid access token: {error}"

    result["token_valid"] = True
    result["user_info"] = user_info

    brand_info, error = get_business_info(brand_token, brand_bm_id)
    if error:
        return result, f"Invalid Brand Business Manager: {error}"

    result["brand_valid"] = True
    result["brand_info"] = brand_info

    return result, None


def get_merchant_catalog_ids(
    merchant_token: str,
    merchant_bm_id: str,
) -> Tuple[Optional[set], Optional[str]]:
    """
    Get the set of catalog/segment IDs owned by the hosting merchant.
    Used to filter client_product_catalogs to only this merchant's catalogs.
    One API call (paginated).
    """
    all_catalogs, error = get_owned_product_catalogs(
        merchant_token, merchant_bm_id,
    )
    if error:
        return None, error
    if not all_catalogs:
        return set(), None
    return {c.get("id") for c in all_catalogs if c.get("id")}, None


def get_brand_shared_catalogs(
    brand_token: str,
    brand_bm_id: str,
    merchant_token: str = None,
    merchant_bm_id: str = None,
) -> Tuple[Optional[List], Optional[str]]:
    """
    Get catalog segments shared with the brand (via client_product_catalogs).
    One API call from the brand side.

    If merchant credentials are provided, filters to only show catalogs
    owned by the hosting merchant (since client_product_catalogs returns
    catalogs shared by ALL merchants).
    """
    all_shared, error = get_shared_catalog_segments(brand_token, brand_bm_id)
    if error:
        return None, error
    if not all_shared:
        return all_shared, None

    # Filter to only this merchant's catalogs if we have merchant credentials
    if merchant_token and merchant_bm_id:
        merchant_ids, merr = get_merchant_catalog_ids(merchant_token, merchant_bm_id)
        if merchant_ids is not None and len(merchant_ids) > 0:
            filtered = [c for c in all_shared if c.get("id") in merchant_ids]
            return filtered, None
        # If we can't get merchant catalogs, fall through and return all

    return all_shared, None


def send_collab_request(
    brand_token: str,
    brand_bm_id: str,
    merchant_bm_id: str,
    email: str,
    name: str,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Send a collaboration request from the brand to the merchant.

    Returns:
        Tuple of (request_id, error_message)
    """
    return send_collaboration_request(
        brand_token,
        brand_bm_id,
        merchant_bm_id,
        email,
        name,
        RequesterType.BRAND,
    )


def check_collab_request_status(
    brand_token: str,
    brand_bm_id: str,
    merchant_bm_id: str,
) -> Dict:
    """
    Check the status of a brand's collaboration request with the merchant.
    One API call.

    Returns:
        Dict with 'status' key: PENDING, APPROVED, REJECTED, not_found, or error
    """
    requests_list, error = get_collaboration_requests(brand_token, brand_bm_id)

    if error:
        return {"status": "error", "message": error}

    for request in requests_list or []:
        receiver = request.get("receiver_business", {})
        if receiver.get("id") == merchant_bm_id:
            return {
                "status": request.get("request_status", "unknown"),
                "request_id": request.get("id"),
                "created_time": request.get("created_time"),
            }

    return {
        "status": "not_found",
        "message": "No collaboration request found for this merchant",
    }


def _send_batch(access_token: str, batch_requests: List[Dict]) -> List[Dict]:
    """
    Send a batch request to the Graph API.

    Args:
        access_token: Facebook access token
        batch_requests: List of batch sub-request dicts (method, relative_url)

    Returns:
        List of response dicts with code, headers, body fields.
    """
    resp = http_requests.post(
        f"https://graph.facebook.com/{GRAPH_API_VERSION}/",
        data={
            "access_token": access_token,
            "batch": json.dumps(batch_requests),
        },
    )
    resp.raise_for_status()
    return resp.json()


def get_pending_shares(
    merchant_token: str,
    brand_bm_id: str,
    merchant_bm_id: str,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> Tuple[Optional[List[Dict]], Optional[str]]:
    """
    Discover segments the merchant has shared with this brand but the brand
    hasn't accepted yet.

    Uses the Graph API batch endpoint (50 sub-requests per batch, 8 parallel
    threads) to scan all merchant segments efficiently.

    Algorithm:
    1. Fetch all merchant segments via get_owned_product_catalogs(segments_only=True)
    2. Batch-query each segment's collaborative_ads_share_settings
    3. Filter to segments where agency_business.id == brand_bm_id
    4. For matching segments, check /{segment_id}/agencies to determine
       PENDING vs ACCEPTED status

    Args:
        merchant_token: Merchant's access token
        brand_bm_id: Brand's Business Manager ID
        merchant_bm_id: Merchant's Business Manager ID
        progress_callback: Optional callback(segments_done, total_segments)

    Returns:
        Tuple of (list of segment dicts, error_message)
        Each segment dict: {segment_id, segment_name, product_count, status}
    """
    # Step 1: Get all merchant segments
    all_segments, error = get_owned_product_catalogs(
        merchant_token, merchant_bm_id, segments_only=True,
    )
    if error:
        return None, f"Failed to fetch merchant segments: {error}"
    if not all_segments:
        return [], None

    total = len(all_segments)
    segments_done = 0

    # Build a lookup for segment metadata
    seg_info = {}
    for seg in all_segments:
        sid = seg.get("id")
        if sid:
            seg_info[sid] = {
                "name": seg.get("name", "Unknown"),
                "product_count": seg.get("product_count", 0),
            }

    segment_ids = list(seg_info.keys())

    # Step 2: Batch-query share_settings (50 per batch)
    BATCH_SIZE = 50
    MAX_WORKERS = 8

    # Build batches of sub-requests
    all_batches = []
    for i in range(0, len(segment_ids), BATCH_SIZE):
        chunk = segment_ids[i : i + BATCH_SIZE]
        batch_requests = [
            {
                "method": "GET",
                "relative_url": (
                    f"{GRAPH_API_VERSION}/{sid}"
                    f"/collaborative_ads_share_settings"
                    f"?fields=id,agency_business&limit=50"
                ),
            }
            for sid in chunk
        ]
        all_batches.append((chunk, batch_requests))

    # Step 3: Send batches in parallel, collect matching segment IDs
    matching_segment_ids = set()

    def _process_batch(batch_tuple):
        chunk_ids, batch_reqs = batch_tuple
        try:
            responses = _send_batch(merchant_token, batch_reqs)
        except Exception as e:
            return chunk_ids, [], str(e)

        matches = []
        for sid, resp in zip(chunk_ids, responses):
            code = resp.get("code", 500) if isinstance(resp, dict) else 500
            if code != 200:
                continue
            body = resp.get("body", "{}")
            if isinstance(body, str):
                body = json.loads(body)
            data = body.get("data", [])
            for entry in data:
                agency_biz = entry.get("agency_business", {})
                if agency_biz.get("id") == brand_bm_id:
                    matches.append(sid)
                    break
        return chunk_ids, matches, None

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(_process_batch, batch): batch
            for batch in all_batches
        }
        for future in as_completed(futures):
            chunk_ids, matches, err = future.result()
            matching_segment_ids.update(matches)
            segments_done += len(chunk_ids)
            if progress_callback:
                progress_callback(min(segments_done, total), total)

    if not matching_segment_ids:
        return [], None

    # Step 4: Check agencies for matching segments to determine PENDING vs ACCEPTED
    # Build batch requests for agencies endpoint
    match_list = sorted(matching_segment_ids)
    agency_batches = []
    for i in range(0, len(match_list), BATCH_SIZE):
        chunk = match_list[i : i + BATCH_SIZE]
        batch_requests = [
            {
                "method": "GET",
                "relative_url": (
                    f"{GRAPH_API_VERSION}/{sid}/agencies"
                    f"?fields=id&limit=50"
                ),
            }
            for sid in chunk
        ]
        agency_batches.append((chunk, batch_requests))

    accepted_segment_ids = set()

    def _process_agency_batch(batch_tuple):
        chunk_ids, batch_reqs = batch_tuple
        try:
            responses = _send_batch(merchant_token, batch_reqs)
        except Exception:
            return []

        accepted = []
        for sid, resp in zip(chunk_ids, responses):
            code = resp.get("code", 500) if isinstance(resp, dict) else 500
            if code != 200:
                continue
            body = resp.get("body", "{}")
            if isinstance(body, str):
                body = json.loads(body)
            data = body.get("data", [])
            for agency in data:
                if agency.get("id") == brand_bm_id:
                    accepted.append(sid)
                    break
        return accepted

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [
            executor.submit(_process_agency_batch, batch)
            for batch in agency_batches
        ]
        for future in as_completed(futures):
            accepted_segment_ids.update(future.result())

    # Build results
    results = []
    for sid in match_list:
        status = "ACCEPTED" if sid in accepted_segment_ids else "PENDING"
        info = seg_info.get(sid, {})
        results.append({
            "segment_id": sid,
            "segment_name": info.get("name", "Unknown"),
            "product_count": info.get("product_count", 0),
            "status": status,
        })

    return results, None


def accept_segment_share(
    merchant_token: str,
    segment_id: str,
    brand_bm_id: str,
) -> Tuple[bool, Optional[str]]:
    """
    Accept a pending segment share using the merchant's token.

    Posts to /{segment_id}/agencies with business=brand_bm_id and
    permitted_tasks=["ADVERTISE"]. Must use the merchant's token because
    the brand token lacks permission for this endpoint.

    Args:
        merchant_token: Merchant's access token
        segment_id: Catalog segment ID to accept
        brand_bm_id: Brand's Business Manager ID

    Returns:
        Tuple of (success, error_message)
    """
    url = (
        f"https://graph.facebook.com/{GRAPH_API_VERSION}"
        f"/{segment_id}/agencies"
    )
    resp = http_requests.post(
        url,
        data={
            "access_token": merchant_token,
            "business": brand_bm_id,
            "permitted_tasks": '["ADVERTISE"]',
        },
    )
    try:
        data = resp.json()
    except Exception:
        return False, f"Non-JSON response (HTTP {resp.status_code})"

    if resp.ok:
        return True, None

    error = data.get("error", {})
    msg = error.get("message", resp.text)
    code = error.get("code", resp.status_code)
    return False, f"API Error {code}: {msg}"
