"""
Agency Platform Backend

Backend logic for the agency CPAS onboarding platform.
Provides high-level functions for the agency UI workflow.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.cpas_api_client import (
    validate_access_token,
    get_business_info,
    send_collaboration_request,
    get_collaboration_requests,
    get_shared_catalog_segments,
    create_ad_account,
    get_ad_accounts,
    create_cpas_campaign_with_ad_set,
)
from shared.constants import (
    CollabRequestStatus,
    RequesterType,
    DEFAULT_TIMEZONE_ID,
    DEFAULT_CURRENCY,
    DEFAULT_DAILY_BUDGET,
)
from shared.merchants import (
    get_merchant_by_key,
    list_all_merchants,
)


def validate_setup(
    access_token: str,
    agency_business_id: str,
    brand_business_id: str,
) -> Tuple[Dict, Optional[str]]:
    """
    Validate the agency and brand setup.

    Args:
        access_token: Facebook access token
        agency_business_id: Agency's Business Manager ID
        brand_business_id: Brand's Business Manager ID

    Returns:
        Tuple of (validation_result_dict, error_message)
    """
    result = {
        "token_valid": False,
        "agency_valid": False,
        "brand_valid": False,
        "agency_info": None,
        "brand_info": None,
        "user_info": None,
    }

    # Validate token
    user_info, error = validate_access_token(access_token)
    if error:
        return result, f"Invalid access token: {error}"

    result["token_valid"] = True
    result["user_info"] = user_info

    # Validate agency BM
    agency_info, error = get_business_info(access_token, agency_business_id)
    if error:
        return result, f"Invalid agency Business Manager: {error}"

    result["agency_valid"] = True
    result["agency_info"] = agency_info

    # Validate brand BM
    brand_info, error = get_business_info(access_token, brand_business_id)
    if error:
        return result, f"Invalid brand Business Manager: {error}"

    result["brand_valid"] = True
    result["brand_info"] = brand_info

    return result, None


def get_available_merchants() -> List[Dict]:
    """
    Get list of available CPAS merchants.

    Returns:
        List of merchant configurations
    """
    return list_all_merchants()


def initiate_partnership(
    access_token: str,
    brand_business_id: str,
    merchant_key: str,
    contact_email: str,
    contact_name: str,
    is_agency: bool = True,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Send a collaboration request to a merchant on behalf of a brand.

    Args:
        access_token: Facebook access token
        brand_business_id: Brand's Business Manager ID
        merchant_key: Merchant key from merchants.py (e.g., 'swiggy')
        contact_email: Contact email for the request
        contact_name: Contact name for the request
        is_agency: Whether this is an agency request

    Returns:
        Tuple of (request_id, error_message)
    """
    # Get merchant info
    merchant = get_merchant_by_key(merchant_key)
    if not merchant:
        return None, f"Unknown merchant: {merchant_key}"

    merchant_business_id = merchant.get("business_id")
    if not merchant_business_id or merchant_business_id.startswith("PLACEHOLDER"):
        return None, f"Merchant {merchant['name']} does not have a configured Business Manager ID. Please update merchants.py with the actual BM ID."

    requester_type = RequesterType.AGENCY if is_agency else RequesterType.BRAND

    return send_collaboration_request(
        access_token,
        brand_business_id,
        merchant_business_id,
        contact_email,
        contact_name,
        requester_type,
    )


def get_sent_requests(
    access_token: str,
    brand_business_id: str,
    status: Optional[str] = None,
) -> Tuple[Optional[List], Optional[str]]:
    """
    Get collaboration requests sent by the brand.

    Args:
        access_token: Facebook access token
        brand_business_id: Brand's Business Manager ID
        status: Filter by status

    Returns:
        Tuple of (list of requests, error_message)
    """
    return get_collaboration_requests(access_token, brand_business_id, status)


def get_partnership_status(
    access_token: str,
    brand_business_id: str,
    merchant_key: str,
) -> Dict:
    """
    Check current partnership status with a specific merchant.

    Args:
        access_token: Facebook access token
        brand_business_id: Brand's Business Manager ID
        merchant_key: Merchant key

    Returns:
        Dict with partnership status info
    """
    merchant = get_merchant_by_key(merchant_key)
    if not merchant:
        return {"status": "error", "message": f"Unknown merchant: {merchant_key}"}

    requests, error = get_sent_requests(access_token, brand_business_id)
    if error:
        return {"status": "error", "message": error}

    merchant_bm_id = merchant.get("business_id")

    # Find request for this merchant
    for request in requests or []:
        if request.get("receiver_business", {}).get("id") == merchant_bm_id:
            return {
                "status": request.get("request_status", "unknown"),
                "request_id": request.get("id"),
                "merchant": merchant,
                "created_time": request.get("created_time"),
            }

    return {
        "status": "no_request",
        "merchant": merchant,
        "message": "No collaboration request found for this merchant",
    }


def get_available_catalog_segments(
    access_token: str,
    brand_business_id: str,
) -> Tuple[Optional[List], Optional[str]]:
    """
    Get catalog segments available to the brand (shared by merchants).

    Args:
        access_token: Facebook access token
        brand_business_id: Brand's Business Manager ID

    Returns:
        Tuple of (list of catalog segments, error_message)
    """
    return get_shared_catalog_segments(access_token, brand_business_id)


def setup_collab_ad_account(
    access_token: str,
    brand_business_id: str,
    merchant_name: str,
    timezone_id: int = DEFAULT_TIMEZONE_ID,
    currency: str = DEFAULT_CURRENCY,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Create a collaborative ad account for the brand.

    Args:
        access_token: Facebook access token
        brand_business_id: Brand's Business Manager ID
        merchant_name: Merchant name (for naming the ad account)
        timezone_id: Timezone ID
        currency: Currency code

    Returns:
        Tuple of (ad_account_id, error_message)
    """
    account_name = f"CPAS - {merchant_name}"
    return create_ad_account(
        access_token,
        brand_business_id,
        account_name,
        timezone_id,
        currency,
    )


def get_brand_ad_accounts(
    access_token: str,
    brand_business_id: str,
) -> Tuple[Optional[List], Optional[str]]:
    """
    Get ad accounts owned by the brand.

    Args:
        access_token: Facebook access token
        brand_business_id: Brand's Business Manager ID

    Returns:
        Tuple of (list of ad accounts, error_message)
    """
    return get_ad_accounts(access_token, brand_business_id)


def create_cpas_campaign(
    access_token: str,
    ad_account_id: str,
    catalog_segment_id: str,
    campaign_name: str,
    daily_budget: int = DEFAULT_DAILY_BUDGET,
    targeting_countries: Optional[List[str]] = None,
) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Create a complete CPAS campaign with ad set.

    Args:
        access_token: Facebook access token
        ad_account_id: Ad account ID
        catalog_segment_id: Catalog segment ID
        campaign_name: Campaign name
        daily_budget: Daily budget in cents/paisa
        targeting_countries: List of country codes for targeting

    Returns:
        Tuple of (result_dict with campaign_id and ad_set_id, error_message)
    """
    targeting = None
    if targeting_countries:
        targeting = {
            "geo_locations": {
                "countries": targeting_countries,
            },
        }

    ad_set_name = f"{campaign_name} - Ad Set"

    return create_cpas_campaign_with_ad_set(
        access_token,
        ad_account_id,
        catalog_segment_id,
        campaign_name,
        ad_set_name,
        daily_budget,
        targeting,
    )


def get_full_onboarding_status(
    access_token: str,
    brand_business_id: str,
    merchant_key: str,
) -> Dict:
    """
    Get the full onboarding status for a brand with a merchant.

    Returns a dict with status for each step:
    1. connection_request - Has a request been sent?
    2. request_approved - Has the request been approved?
    3. catalog_available - Is a catalog segment available?
    4. ad_account_ready - Is an ad account created?
    5. campaign_created - Has a campaign been created?

    Args:
        access_token: Facebook access token
        brand_business_id: Brand's Business Manager ID
        merchant_key: Merchant key

    Returns:
        Dict with status for each onboarding step
    """
    status = {
        "connection_request": False,
        "request_approved": False,
        "catalog_available": False,
        "ad_account_ready": False,
        "campaign_created": False,
        "details": {},
    }

    # Check partnership status
    partnership = get_partnership_status(access_token, brand_business_id, merchant_key)

    if partnership.get("status") != "no_request":
        status["connection_request"] = True
        status["details"]["request_id"] = partnership.get("request_id")
        status["details"]["request_status"] = partnership.get("status")

        if partnership.get("status") == CollabRequestStatus.APPROVED:
            status["request_approved"] = True

    # Check catalog segments
    catalogs, _ = get_available_catalog_segments(access_token, brand_business_id)
    if catalogs and len(catalogs) > 0:
        status["catalog_available"] = True
        status["details"]["catalog_count"] = len(catalogs)

    # Check ad accounts
    accounts, _ = get_brand_ad_accounts(access_token, brand_business_id)
    if accounts and len(accounts) > 0:
        status["ad_account_ready"] = True
        status["details"]["ad_account_count"] = len(accounts)

    return status
