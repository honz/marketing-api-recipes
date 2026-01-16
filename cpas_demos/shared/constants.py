"""
CPAS Constants

Constants and configuration values for CPAS demo applications.
"""

# API Configuration
GRAPH_API_VERSION = "v22.0"
GRAPH_API_BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

# Default timezone and currency for India
DEFAULT_TIMEZONE_ID = 50  # Asia/Kolkata
DEFAULT_CURRENCY = "INR"

# Targeting defaults
DEFAULT_TARGETING_COUNTRIES = ["IN"]


class CollabRequestStatus:
    """Collaboration request status values."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    IN_PROGRESS = "IN_PROGRESS"


class RequesterType:
    """Requester type for collaboration requests."""
    BRAND = "BRAND"
    AGENCY = "AGENCY"


class CampaignObjective:
    """Campaign objectives for CPAS campaigns."""
    OUTCOME_SALES = "OUTCOME_SALES"
    OUTCOME_TRAFFIC = "OUTCOME_TRAFFIC"
    OUTCOME_AWARENESS = "OUTCOME_AWARENESS"


class AdSetBillingEvent:
    """Billing events for ad sets."""
    IMPRESSIONS = "IMPRESSIONS"
    LINK_CLICKS = "LINK_CLICKS"


class AdSetOptimizationGoal:
    """Optimization goals for ad sets."""
    OFFSITE_CONVERSIONS = "OFFSITE_CONVERSIONS"
    LINK_CLICKS = "LINK_CLICKS"
    IMPRESSIONS = "IMPRESSIONS"


# CTA Types for ads
class CTAType:
    """Call to action types for ads."""
    SHOP_NOW = "SHOP_NOW"
    LEARN_MORE = "LEARN_MORE"
    SIGN_UP = "SIGN_UP"
    BUY_NOW = "BUY_NOW"
    ORDER_NOW = "ORDER_NOW"
    GET_OFFER = "GET_OFFER"


# Default daily budget in paisa (100 INR = 10000 paisa)
DEFAULT_DAILY_BUDGET = 100000  # 1000 INR in paisa
