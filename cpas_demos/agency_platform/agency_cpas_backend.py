"""
Agency Platform Backend

Backend logic for the agency CPAS multi-brand dashboard.
Provides high-level functions for discovering brands, managing collaboration
requests (inbound + outbound), and creating ad accounts and campaigns.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.cpas_api_client import (
    validate_access_token,
    get_business_info,
    get_client_businesses,
    send_collaboration_request,
    get_collaboration_requests,
    accept_collaboration_request,
    reject_collaboration_request,
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


# =============================================================================
# Setup & Discovery
# =============================================================================

def validate_agency_setup(
    access_token: str,
    agency_business_id: str,
) -> Tuple[Dict, Optional[str]]:
    """
    Validate the agency token and Business Manager.

    Args:
        access_token: Facebook access token
        agency_business_id: Agency's Business Manager ID

    Returns:
        Tuple of (validation_result_dict, error_message)
    """
    result = {
        "token_valid": False,
        "agency_valid": False,
        "agency_info": None,
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

    return result, None


def discover_brands(
    access_token: str,
    agency_business_id: str,
) -> Tuple[Optional[List], Optional[str]]:
    """
    Discover brands (client businesses) partnered with this agency.

    Args:
        access_token: Facebook access token
        agency_business_id: Agency's Business Manager ID

    Returns:
        Tuple of (list of brand dicts, error_message)
    """
    return get_client_businesses(access_token, agency_business_id)


# =============================================================================
# Brand Summary
# =============================================================================

def get_brand_onboarding_summary(
    access_token: str,
    brand_bm_id: str,
) -> Dict:
    """
    Get an onboarding summary for a single brand.

    Returns counts for outbound requests, inbound requests, catalog segments,
    and ad accounts. Each API call is wrapped in try/except for graceful
    degradation — a failure in one call doesn't block the others.

    Args:
        access_token: Facebook access token
        brand_bm_id: Brand's Business Manager ID

    Returns:
        Dict with outbound_requests, inbound_requests, catalog_segments,
        ad_accounts counts and any errors encountered.
    """
    summary = {
        "outbound_requests": 0,
        "inbound_requests": 0,
        "catalog_segments": 0,
        "ad_accounts": 0,
        "errors": [],
    }

    # Collaboration requests (both directions)
    try:
        all_requests, error = get_collaboration_requests(access_token, brand_bm_id)
        if error:
            summary["errors"].append(f"requests: {error}")
        elif all_requests:
            outbound = []
            inbound = []
            for req in all_requests:
                sender = req.get("sender_business", {}).get("id")
                if sender == brand_bm_id:
                    outbound.append(req)
                else:
                    inbound.append(req)
            summary["outbound_requests"] = len(outbound)
            summary["inbound_requests"] = len(inbound)
    except Exception as e:
        summary["errors"].append(f"requests: {str(e)}")

    # Catalog segments
    try:
        catalogs, error = get_shared_catalog_segments(access_token, brand_bm_id)
        if error:
            summary["errors"].append(f"catalogs: {error}")
        elif catalogs:
            summary["catalog_segments"] = len(catalogs)
    except Exception as e:
        summary["errors"].append(f"catalogs: {str(e)}")

    # Ad accounts
    try:
        accounts, error = get_ad_accounts(access_token, brand_bm_id)
        if error:
            summary["errors"].append(f"ad_accounts: {error}")
        elif accounts:
            summary["ad_accounts"] = len(accounts)
    except Exception as e:
        summary["errors"].append(f"ad_accounts: {str(e)}")

    return summary


# =============================================================================
# Collaboration Requests — Inbound & Outbound
# =============================================================================

def get_outbound_requests(
    access_token: str,
    brand_bm_id: str,
) -> Tuple[Optional[List], Optional[str]]:
    """
    Get outbound collaboration requests (sent by the brand).

    Args:
        access_token: Facebook access token
        brand_bm_id: Brand's Business Manager ID

    Returns:
        Tuple of (list of outbound requests, error_message)
    """
    all_requests, error = get_collaboration_requests(access_token, brand_bm_id)
    if error:
        return None, error

    outbound = [
        req for req in (all_requests or [])
        if req.get("sender_business", {}).get("id") == brand_bm_id
    ]
    return outbound, None


def get_inbound_requests(
    access_token: str,
    brand_bm_id: str,
) -> Tuple[Optional[List], Optional[str]]:
    """
    Get inbound collaboration requests (received by the brand).

    Args:
        access_token: Facebook access token
        brand_bm_id: Brand's Business Manager ID

    Returns:
        Tuple of (list of inbound requests, error_message)
    """
    all_requests, error = get_collaboration_requests(access_token, brand_bm_id)
    if error:
        return None, error

    inbound = [
        req for req in (all_requests or [])
        if req.get("sender_business", {}).get("id") != brand_bm_id
    ]
    return inbound, None


def accept_inbound_request(
    access_token: str,
    request_id: str,
) -> Tuple[bool, Optional[str]]:
    """
    Accept a pending inbound collaboration request.

    Args:
        access_token: Facebook access token
        request_id: Collaboration request ID

    Returns:
        Tuple of (success, error_message)
    """
    return accept_collaboration_request(access_token, request_id)


def reject_inbound_request(
    access_token: str,
    request_id: str,
) -> Tuple[bool, Optional[str]]:
    """
    Reject a pending inbound collaboration request.

    Args:
        access_token: Facebook access token
        request_id: Collaboration request ID

    Returns:
        Tuple of (success, error_message)
    """
    return reject_collaboration_request(access_token, request_id)


# =============================================================================
# Merchant Discovery & Partnership Initiation
# =============================================================================

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
) -> Tuple[Optional[str], Optional[str]]:
    """
    Send a collaboration request to a merchant on behalf of a brand.

    Always sends as RequesterType.AGENCY.

    Args:
        access_token: Facebook access token
        brand_business_id: Brand's Business Manager ID
        merchant_key: Merchant key from merchants.py (e.g., 'swiggy')
        contact_email: Contact email for the request
        contact_name: Contact name for the request

    Returns:
        Tuple of (request_id, error_message)
    """
    merchant = get_merchant_by_key(merchant_key)
    if not merchant:
        return None, f"Unknown merchant: {merchant_key}"

    merchant_business_id = merchant.get("business_id")
    if not merchant_business_id or merchant_business_id.startswith("PLACEHOLDER"):
        return None, (
            f"Merchant {merchant['name']} does not have a configured Business Manager ID. "
            "Please update merchants.py with the actual BM ID."
        )

    return send_collaboration_request(
        access_token,
        brand_business_id,
        merchant_business_id,
        contact_email,
        contact_name,
        RequesterType.AGENCY,
    )


# =============================================================================
# Catalog Segments
# =============================================================================

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


# =============================================================================
# Ad Account Operations
# =============================================================================

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


# =============================================================================
# Campaign Operations
# =============================================================================

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
