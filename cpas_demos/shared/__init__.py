"""
Shared modules for CPAS demos.
"""

from .constants import (
    GRAPH_API_VERSION,
    GRAPH_API_BASE_URL,
    DEFAULT_TIMEZONE_ID,
    DEFAULT_CURRENCY,
    DEFAULT_DAILY_BUDGET,
    CollabRequestStatus,
    RequesterType,
    CampaignObjective,
    AdSetBillingEvent,
    AdSetOptimizationGoal,
    CTAType,
)
from .merchants import (
    INDIA_MERCHANTS,
    get_merchant_by_key,
    get_merchant_by_business_id,
    list_all_merchants,
    list_active_merchants,
)
from .cpas_api_client import (
    make_api_request,
    send_collaboration_request,
    get_collaboration_requests,
    accept_collaboration_request,
    reject_collaboration_request,
    get_suggested_partners,
    get_collaborative_ads_merchants,
    get_owned_catalog_segments,
    get_shared_catalog_segments,
    share_catalog_segment,
    create_ad_account,
    get_ad_accounts,
    create_campaign,
    create_ad_set,
    get_business_info,
    validate_access_token,
    create_cpas_campaign_with_ad_set,
)
