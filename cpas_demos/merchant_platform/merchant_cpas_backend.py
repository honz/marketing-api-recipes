"""
Merchant Platform Backend

Backend logic for the merchant CPAS platform.
Provides high-level functions for the merchant UI workflow.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.cpas_api_client import (
    validate_access_token,
    get_business_info,
    get_collaboration_requests,
    accept_collaboration_request,
    reject_collaboration_request,
    get_owned_catalog_segments,
    share_catalog_segment,
    get_collaborative_ads_merchants,
    create_ad_account,
    create_cpas_campaign_with_ad_set,
)
from shared.constants import (
    CollabRequestStatus,
    DEFAULT_TIMEZONE_ID,
    DEFAULT_CURRENCY,
    DEFAULT_DAILY_BUDGET,
)


def validate_merchant_setup(
    access_token: str,
    merchant_business_id: str,
) -> Tuple[Dict, Optional[str]]:
    """
    Validate the merchant setup.

    Args:
        access_token: Facebook access token
        merchant_business_id: Merchant's Business Manager ID

    Returns:
        Tuple of (validation_result_dict, error_message)
    """
    result = {
        "token_valid": False,
        "merchant_valid": False,
        "merchant_info": None,
        "user_info": None,
    }

    # Validate token
    user_info, error = validate_access_token(access_token)
    if error:
        return result, f"Invalid access token: {error}"

    result["token_valid"] = True
    result["user_info"] = user_info

    # Validate merchant BM
    merchant_info, error = get_business_info(access_token, merchant_business_id)
    if error:
        return result, f"Invalid merchant Business Manager: {error}"

    result["merchant_valid"] = True
    result["merchant_info"] = merchant_info

    return result, None


def get_dashboard_stats(
    access_token: str,
    merchant_business_id: str,
) -> Dict:
    """
    Get dashboard statistics for the merchant.

    Args:
        access_token: Facebook access token
        merchant_business_id: Merchant's Business Manager ID

    Returns:
        Dict with dashboard statistics
    """
    stats = {
        "pending_requests": 0,
        "approved_requests": 0,
        "active_partners": 0,
        "catalog_segments": 0,
    }

    # Get pending requests
    pending, _ = get_collaboration_requests(
        access_token, merchant_business_id, status=CollabRequestStatus.PENDING
    )
    if pending:
        stats["pending_requests"] = len(pending)

    # Get approved requests
    approved, _ = get_collaboration_requests(
        access_token, merchant_business_id, status=CollabRequestStatus.APPROVED
    )
    if approved:
        stats["approved_requests"] = len(approved)
        stats["active_partners"] = len(approved)

    # Get catalog segments
    catalogs, _ = get_owned_catalog_segments(access_token, merchant_business_id)
    if catalogs:
        stats["catalog_segments"] = len(catalogs)

    return stats


def get_pending_requests(
    access_token: str,
    merchant_business_id: str,
) -> Tuple[Optional[List], Optional[str]]:
    """
    Get pending collaboration requests for the merchant.

    Args:
        access_token: Facebook access token
        merchant_business_id: Merchant's Business Manager ID

    Returns:
        Tuple of (list of pending requests, error_message)
    """
    return get_collaboration_requests(
        access_token, merchant_business_id, status=CollabRequestStatus.PENDING
    )


def get_all_requests(
    access_token: str,
    merchant_business_id: str,
    status: Optional[str] = None,
) -> Tuple[Optional[List], Optional[str]]:
    """
    Get all collaboration requests for the merchant.

    Args:
        access_token: Facebook access token
        merchant_business_id: Merchant's Business Manager ID
        status: Optional status filter

    Returns:
        Tuple of (list of requests, error_message)
    """
    return get_collaboration_requests(access_token, merchant_business_id, status)


def approve_request(
    access_token: str,
    request_id: str,
) -> Tuple[bool, Optional[str]]:
    """
    Approve a collaboration request.

    Args:
        access_token: Facebook access token
        request_id: Collaboration request ID

    Returns:
        Tuple of (success, error_message)
    """
    return accept_collaboration_request(access_token, request_id)


def reject_request(
    access_token: str,
    request_id: str,
) -> Tuple[bool, Optional[str]]:
    """
    Reject a collaboration request.

    Args:
        access_token: Facebook access token
        request_id: Collaboration request ID

    Returns:
        Tuple of (success, error_message)
    """
    return reject_collaboration_request(access_token, request_id)


def bulk_approve_requests(
    access_token: str,
    request_ids: List[str],
) -> Dict:
    """
    Bulk approve multiple collaboration requests.

    Args:
        access_token: Facebook access token
        request_ids: List of request IDs to approve

    Returns:
        Dict with results for each request
    """
    results = {
        "total": len(request_ids),
        "successful": 0,
        "failed": 0,
        "details": [],
    }

    for request_id in request_ids:
        success, error = approve_request(access_token, request_id)
        if success:
            results["successful"] += 1
            results["details"].append({"id": request_id, "status": "approved"})
        else:
            results["failed"] += 1
            results["details"].append({"id": request_id, "status": "failed", "error": error})

    return results


def bulk_reject_requests(
    access_token: str,
    request_ids: List[str],
) -> Dict:
    """
    Bulk reject multiple collaboration requests.

    Args:
        access_token: Facebook access token
        request_ids: List of request IDs to reject

    Returns:
        Dict with results for each request
    """
    results = {
        "total": len(request_ids),
        "successful": 0,
        "failed": 0,
        "details": [],
    }

    for request_id in request_ids:
        success, error = reject_request(access_token, request_id)
        if success:
            results["successful"] += 1
            results["details"].append({"id": request_id, "status": "rejected"})
        else:
            results["failed"] += 1
            results["details"].append({"id": request_id, "status": "failed", "error": error})

    return results


def get_active_partners(
    access_token: str,
    merchant_business_id: str,
) -> Tuple[Optional[List], Optional[str]]:
    """
    Get list of active brand partners.

    Args:
        access_token: Facebook access token
        merchant_business_id: Merchant's Business Manager ID

    Returns:
        Tuple of (list of active partners, error_message)
    """
    # Get approved requests as active partners
    return get_collaboration_requests(
        access_token, merchant_business_id, status=CollabRequestStatus.APPROVED
    )


def get_catalog_segments(
    access_token: str,
    merchant_business_id: str,
) -> Tuple[Optional[List], Optional[str]]:
    """
    Get catalog segments owned by the merchant.

    Args:
        access_token: Facebook access token
        merchant_business_id: Merchant's Business Manager ID

    Returns:
        Tuple of (list of catalog segments, error_message)
    """
    return get_owned_catalog_segments(access_token, merchant_business_id)


def share_catalog_with_brand(
    access_token: str,
    catalog_id: str,
    brand_business_id: str,
) -> Tuple[bool, Optional[str]]:
    """
    Share a catalog segment with a brand.

    Args:
        access_token: Facebook access token
        catalog_id: Catalog segment ID
        brand_business_id: Brand's Business Manager ID

    Returns:
        Tuple of (success, error_message)
    """
    return share_catalog_segment(access_token, catalog_id, brand_business_id)


# =============================================================================
# Brand Self-Service Functions
# =============================================================================

def brand_submit_request(
    access_token: str,
    merchant_business_id: str,
    brand_business_id: str,
    brand_name: str,
    contact_email: str,
    contact_name: str,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Submit a collaboration request from a brand (brand's perspective).

    Note: This is called from the brand's access token, not the merchant's.

    Args:
        access_token: Brand's Facebook access token
        merchant_business_id: Merchant's Business Manager ID
        brand_business_id: Brand's Business Manager ID
        brand_name: Brand name
        contact_email: Contact email
        contact_name: Contact name

    Returns:
        Tuple of (request_id, error_message)
    """
    from shared.cpas_api_client import send_collaboration_request
    from shared.constants import RequesterType

    return send_collaboration_request(
        access_token,
        brand_business_id,
        merchant_business_id,
        contact_email,
        contact_name,
        RequesterType.BRAND,
    )


def brand_check_request_status(
    access_token: str,
    brand_business_id: str,
    merchant_business_id: str,
) -> Dict:
    """
    Check the status of a brand's collaboration request.

    Args:
        access_token: Brand's Facebook access token
        brand_business_id: Brand's Business Manager ID
        merchant_business_id: Merchant's Business Manager ID

    Returns:
        Dict with request status information
    """
    requests, error = get_collaboration_requests(access_token, brand_business_id)

    if error:
        return {"status": "error", "message": error}

    # Find request for this merchant
    for request in requests or []:
        receiver = request.get("receiver_business", {})
        if receiver.get("id") == merchant_business_id:
            return {
                "status": request.get("request_status", "unknown"),
                "request_id": request.get("id"),
                "created_time": request.get("created_time"),
            }

    return {
        "status": "not_found",
        "message": "No collaboration request found for this merchant",
    }


def brand_get_shared_catalogs(
    access_token: str,
    brand_business_id: str,
) -> Tuple[Optional[List], Optional[str]]:
    """
    Get catalog segments shared with the brand.

    Args:
        access_token: Brand's Facebook access token
        brand_business_id: Brand's Business Manager ID

    Returns:
        Tuple of (list of shared catalog segments, error_message)
    """
    from shared.cpas_api_client import get_shared_catalog_segments
    return get_shared_catalog_segments(access_token, brand_business_id)


def brand_create_ad_account(
    access_token: str,
    brand_business_id: str,
    merchant_name: str,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Create an ad account for the brand for CPAS campaigns.

    Args:
        access_token: Brand's Facebook access token
        brand_business_id: Brand's Business Manager ID
        merchant_name: Merchant name (for naming)

    Returns:
        Tuple of (ad_account_id, error_message)
    """
    account_name = f"CPAS - {merchant_name}"
    return create_ad_account(
        access_token,
        brand_business_id,
        account_name,
        DEFAULT_TIMEZONE_ID,
        DEFAULT_CURRENCY,
    )


def brand_create_campaign(
    access_token: str,
    ad_account_id: str,
    catalog_segment_id: str,
    campaign_name: str,
    daily_budget: int = DEFAULT_DAILY_BUDGET,
) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Create a CPAS campaign for the brand.

    Args:
        access_token: Brand's Facebook access token
        ad_account_id: Ad account ID
        catalog_segment_id: Catalog segment ID
        campaign_name: Campaign name
        daily_budget: Daily budget in cents/paisa

    Returns:
        Tuple of (result_dict with campaign_id and ad_set_id, error_message)
    """
    ad_set_name = f"{campaign_name} - Ad Set"

    return create_cpas_campaign_with_ad_set(
        access_token,
        ad_account_id,
        catalog_segment_id,
        campaign_name,
        ad_set_name,
        daily_budget,
        {"geo_locations": {"countries": ["IN"]}},
    )
