"""
CPAS API Client

Graph API wrapper for Collaborative Ads (CPAS) operations.
Follows patterns from partnership_ads_booster.py.
"""

from typing import Dict, List, Optional, Tuple

import requests

from .constants import (
    GRAPH_API_VERSION,
    GRAPH_API_BASE_URL,
    DEFAULT_TIMEZONE_ID,
    DEFAULT_CURRENCY,
    DEFAULT_DAILY_BUDGET,
    CollabRequestStatus,
    CampaignObjective,
    AdSetBillingEvent,
    AdSetOptimizationGoal,
)


def make_api_request(
    access_token: str,
    endpoint: str,
    method: str = "GET",
    params: Optional[Dict] = None,
    data: Optional[Dict] = None,
    api_version: str = GRAPH_API_VERSION,
) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Generic Graph API request wrapper with error handling.

    Args:
        access_token: Facebook access token
        endpoint: API endpoint (e.g., "123/collaborative_ads_collaboration_requests")
        method: HTTP method (GET, POST, DELETE)
        params: Query parameters
        data: POST body data
        api_version: Graph API version

    Returns:
        Tuple of (response_data, error_message)
    """
    url = f"https://graph.facebook.com/{api_version}/{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }

    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, params=params, json=data)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, params=params)
        else:
            return None, f"Unsupported HTTP method: {method}"

        response_data = response.json()

        if response.status_code == 200:
            return response_data, None
        else:
            error = response_data.get("error", {})
            error_msg = error.get("message", response.text)
            error_code = error.get("code", response.status_code)
            return None, f"API Error {error_code}: {error_msg}"

    except requests.exceptions.RequestException as e:
        return None, f"Request error: {str(e)}"
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"


# =============================================================================
# Collaboration Request APIs
# =============================================================================

def send_collaboration_request(
    access_token: str,
    brand_business_id: str,
    merchant_business_id: str,
    contact_email: str,
    contact_name: str,
    requester_type: str = "BRAND",
) -> Tuple[Optional[str], Optional[str]]:
    """
    Send a CPAS collaboration request from brand to merchant.

    Args:
        access_token: Facebook access token
        brand_business_id: Brand's Business Manager ID
        merchant_business_id: Merchant's Business Manager ID
        contact_email: Contact email for the request
        contact_name: Contact name for the request
        requester_type: "BRAND" or "AGENCY"

    Returns:
        Tuple of (request_id, error_message)
    """
    endpoint = f"{brand_business_id}/collaborative_ads_collaboration_requests"
    params = {
        "brands": merchant_business_id,
        "contact_email": contact_email,
        "contact_name": contact_name,
        "requester_agency_or_brand": requester_type,
    }

    response, error = make_api_request(
        access_token, endpoint, method="POST", params=params
    )

    if error:
        return None, error

    if response and "id" in response:
        return response["id"], None

    return None, "Request ID not found in response"


def get_collaboration_requests(
    access_token: str,
    business_id: str,
    status: Optional[str] = None,
    limit: int = 50,
) -> Tuple[Optional[List], Optional[str]]:
    """
    Get collaboration requests for a business (sent or received).

    Args:
        access_token: Facebook access token
        business_id: Business Manager ID
        status: Filter by status (PENDING, APPROVED, REJECTED)
        limit: Maximum number of requests to fetch

    Returns:
        Tuple of (list of requests, error_message)
    """
    endpoint = f"{business_id}/collaborative_ads_collaboration_requests"
    params = {"limit": limit}

    if status:
        params["status"] = status

    response, error = make_api_request(access_token, endpoint, params=params)

    if error:
        return None, error

    if response and "data" in response:
        return response["data"], None

    return [], None


def accept_collaboration_request(
    access_token: str,
    request_id: str,
) -> Tuple[bool, Optional[str]]:
    """
    Accept a pending collaboration request.

    Args:
        access_token: Facebook access token
        request_id: Collaboration request ID

    Returns:
        Tuple of (success, error_message)
    """
    endpoint = request_id
    params = {"request_status": "approve"}

    response, error = make_api_request(
        access_token, endpoint, method="POST", params=params
    )

    if error:
        return False, error

    return True, None


def reject_collaboration_request(
    access_token: str,
    request_id: str,
) -> Tuple[bool, Optional[str]]:
    """
    Reject a pending collaboration request.

    Args:
        access_token: Facebook access token
        request_id: Collaboration request ID

    Returns:
        Tuple of (success, error_message)
    """
    endpoint = request_id
    params = {"request_status": "reject"}

    response, error = make_api_request(
        access_token, endpoint, method="POST", params=params
    )

    if error:
        return False, error

    return True, None


# =============================================================================
# Partner Discovery APIs
# =============================================================================

def get_suggested_partners(
    access_token: str,
    business_id: str,
    limit: int = 50,
) -> Tuple[Optional[List], Optional[str]]:
    """
    Get suggested CPAS partners for a business.

    Args:
        access_token: Facebook access token
        business_id: Business Manager ID
        limit: Maximum number of suggestions

    Returns:
        Tuple of (list of suggested partners, error_message)
    """
    endpoint = f"{business_id}/collaborative_ads_suggested_partners"
    params = {"limit": limit}

    response, error = make_api_request(access_token, endpoint, params=params)

    if error:
        return None, error

    if response and "data" in response:
        return response["data"], None

    return [], None


def get_collaborative_ads_merchants(
    access_token: str,
    business_id: str,
    limit: int = 50,
) -> Tuple[Optional[List], Optional[str]]:
    """
    Get merchants with active collaborative agreements.

    Args:
        access_token: Facebook access token
        business_id: Business Manager ID
        limit: Maximum number of merchants

    Returns:
        Tuple of (list of merchants, error_message)
    """
    endpoint = f"{business_id}/collaborative_ads_merchants"
    params = {"limit": limit}

    response, error = make_api_request(access_token, endpoint, params=params)

    if error:
        return None, error

    if response and "data" in response:
        return response["data"], None

    return [], None


# =============================================================================
# Catalog Segment APIs
# =============================================================================

def get_owned_catalog_segments(
    access_token: str,
    business_id: str,
    limit: int = 50,
) -> Tuple[Optional[List], Optional[str]]:
    """
    Get catalog segments owned by a business.

    Args:
        access_token: Facebook access token
        business_id: Business Manager ID
        limit: Maximum number of segments

    Returns:
        Tuple of (list of catalog segments, error_message)
    """
    endpoint = f"{business_id}/owned_product_catalogs"
    params = {
        "limit": limit,
        "fields": "id,name,product_count,vertical",
    }

    response, error = make_api_request(access_token, endpoint, params=params)

    if error:
        return None, error

    if response and "data" in response:
        return response["data"], None

    return [], None


def get_shared_catalog_segments(
    access_token: str,
    business_id: str,
    limit: int = 50,
) -> Tuple[Optional[List], Optional[str]]:
    """
    Get catalog segments shared with a business (as producer/brand).

    Args:
        access_token: Facebook access token
        business_id: Business Manager ID
        limit: Maximum number of segments

    Returns:
        Tuple of (list of shared catalog segments, error_message)
    """
    endpoint = f"{business_id}/client_product_catalogs"
    params = {
        "limit": limit,
        "fields": "id,name,product_count,vertical",
    }

    response, error = make_api_request(access_token, endpoint, params=params)

    if error:
        return None, error

    if response and "data" in response:
        return response["data"], None

    return [], None


def share_catalog_segment(
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
    endpoint = f"{catalog_id}/agencies"
    params = {
        "business": brand_business_id,
        "permitted_tasks": ["ADVERTISE"],
    }

    response, error = make_api_request(
        access_token, endpoint, method="POST", params=params
    )

    if error:
        return False, error

    return True, None


# =============================================================================
# Ad Account APIs
# =============================================================================

def create_ad_account(
    access_token: str,
    business_id: str,
    name: str,
    timezone_id: int = DEFAULT_TIMEZONE_ID,
    currency: str = DEFAULT_CURRENCY,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Create a new ad account in a Business Manager.

    Args:
        access_token: Facebook access token
        business_id: Business Manager ID
        name: Ad account name
        timezone_id: Timezone ID (default: Asia/Kolkata)
        currency: Currency code (default: INR)

    Returns:
        Tuple of (ad_account_id, error_message)
    """
    endpoint = f"{business_id}/adaccount"
    params = {
        "name": name,
        "timezone_id": timezone_id,
        "currency": currency,
        "end_advertiser": business_id,
        "media_agency": business_id,
        "partner": "NONE",
    }

    response, error = make_api_request(
        access_token, endpoint, method="POST", params=params
    )

    if error:
        return None, error

    if response and "id" in response:
        return response["id"], None

    return None, "Ad account ID not found in response"


def get_ad_accounts(
    access_token: str,
    business_id: str,
    limit: int = 50,
) -> Tuple[Optional[List], Optional[str]]:
    """
    Get ad accounts for a business.

    Args:
        access_token: Facebook access token
        business_id: Business Manager ID
        limit: Maximum number of accounts

    Returns:
        Tuple of (list of ad accounts, error_message)
    """
    endpoint = f"{business_id}/owned_ad_accounts"
    params = {
        "limit": limit,
        "fields": "id,name,account_status,currency,timezone_name",
    }

    response, error = make_api_request(access_token, endpoint, params=params)

    if error:
        return None, error

    if response and "data" in response:
        return response["data"], None

    return [], None


# =============================================================================
# Campaign APIs
# =============================================================================

def create_campaign(
    access_token: str,
    ad_account_id: str,
    name: str,
    objective: str = CampaignObjective.OUTCOME_SALES,
    special_ad_categories: Optional[List[str]] = None,
    status: str = "PAUSED",
) -> Tuple[Optional[str], Optional[str]]:
    """
    Create a campaign in an ad account.

    Args:
        access_token: Facebook access token
        ad_account_id: Ad account ID (with or without 'act_' prefix)
        name: Campaign name
        objective: Campaign objective
        special_ad_categories: Special ad categories (empty list for none)
        status: Campaign status (PAUSED recommended)

    Returns:
        Tuple of (campaign_id, error_message)
    """
    # Ensure ad_account_id has act_ prefix
    if not ad_account_id.startswith("act_"):
        ad_account_id = f"act_{ad_account_id}"

    endpoint = f"{ad_account_id}/campaigns"
    params = {
        "name": name,
        "objective": objective,
        "status": status,
        "special_ad_categories": special_ad_categories or [],
    }

    response, error = make_api_request(
        access_token, endpoint, method="POST", params=params
    )

    if error:
        return None, error

    if response and "id" in response:
        return response["id"], None

    return None, "Campaign ID not found in response"


def create_ad_set(
    access_token: str,
    ad_account_id: str,
    campaign_id: str,
    name: str,
    catalog_segment_id: str,
    daily_budget: int = DEFAULT_DAILY_BUDGET,
    targeting: Optional[Dict] = None,
    billing_event: str = AdSetBillingEvent.IMPRESSIONS,
    optimization_goal: str = AdSetOptimizationGoal.OFFSITE_CONVERSIONS,
    status: str = "PAUSED",
) -> Tuple[Optional[str], Optional[str]]:
    """
    Create an ad set for CPAS campaigns.

    Args:
        access_token: Facebook access token
        ad_account_id: Ad account ID
        campaign_id: Campaign ID
        name: Ad set name
        catalog_segment_id: Catalog segment ID for promoted object
        daily_budget: Daily budget in cents/paisa
        targeting: Targeting spec (defaults to India)
        billing_event: Billing event
        optimization_goal: Optimization goal
        status: Ad set status

    Returns:
        Tuple of (ad_set_id, error_message)
    """
    # Ensure ad_account_id has act_ prefix
    if not ad_account_id.startswith("act_"):
        ad_account_id = f"act_{ad_account_id}"

    endpoint = f"{ad_account_id}/adsets"

    # Default targeting to India
    if targeting is None:
        targeting = {
            "geo_locations": {
                "countries": ["IN"],
            },
        }

    params = {
        "name": name,
        "campaign_id": campaign_id,
        "daily_budget": daily_budget,
        "billing_event": billing_event,
        "optimization_goal": optimization_goal,
        "targeting": targeting,
        "promoted_object": {
            "product_catalog_id": catalog_segment_id,
        },
        "status": status,
    }

    response, error = make_api_request(
        access_token, endpoint, method="POST", params=params
    )

    if error:
        return None, error

    if response and "id" in response:
        return response["id"], None

    return None, "Ad set ID not found in response"


# =============================================================================
# Business Info APIs
# =============================================================================

def get_business_info(
    access_token: str,
    business_id: str,
) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Get information about a Business Manager.

    Args:
        access_token: Facebook access token
        business_id: Business Manager ID

    Returns:
        Tuple of (business_info_dict, error_message)
    """
    endpoint = business_id
    params = {
        "fields": "id,name,primary_page,verification_status",
    }

    response, error = make_api_request(access_token, endpoint, params=params)

    if error:
        return None, error

    return response, None


def validate_access_token(
    access_token: str,
) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Validate an access token and get associated user/app info.

    Args:
        access_token: Facebook access token

    Returns:
        Tuple of (token_info_dict, error_message)
    """
    endpoint = "me"
    params = {"fields": "id,name"}

    response, error = make_api_request(access_token, endpoint, params=params)

    if error:
        return None, error

    return response, None


# =============================================================================
# Full Flow Helpers
# =============================================================================

def create_cpas_campaign_with_ad_set(
    access_token: str,
    ad_account_id: str,
    catalog_segment_id: str,
    campaign_name: str,
    ad_set_name: str,
    daily_budget: int = DEFAULT_DAILY_BUDGET,
    targeting: Optional[Dict] = None,
) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Create a complete CPAS campaign with ad set.

    Args:
        access_token: Facebook access token
        ad_account_id: Ad account ID
        catalog_segment_id: Catalog segment ID
        campaign_name: Name for the campaign
        ad_set_name: Name for the ad set
        daily_budget: Daily budget in cents/paisa
        targeting: Targeting spec

    Returns:
        Tuple of (result_dict with campaign_id and ad_set_id, error_message)
    """
    # Create campaign
    campaign_id, error = create_campaign(
        access_token,
        ad_account_id,
        campaign_name,
        objective=CampaignObjective.OUTCOME_SALES,
    )

    if error:
        return None, f"Failed to create campaign: {error}"

    # Create ad set
    ad_set_id, error = create_ad_set(
        access_token,
        ad_account_id,
        campaign_id,
        ad_set_name,
        catalog_segment_id,
        daily_budget=daily_budget,
        targeting=targeting,
    )

    if error:
        return None, f"Campaign created ({campaign_id}) but failed to create ad set: {error}"

    return {
        "campaign_id": campaign_id,
        "ad_set_id": ad_set_id,
    }, None
