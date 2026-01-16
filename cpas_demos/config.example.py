"""
CPAS Configuration Example

Copy this file to config.py and fill in your actual values.
DO NOT commit config.py with real credentials to version control.

Usage:
  cp config.example.py config.py
  # Edit config.py with your values
"""

import os
from typing import Optional


# =============================================================================
# Access Tokens
# =============================================================================
# Option 1: Set via environment variable (recommended for production)
# export CPAS_ACCESS_TOKEN="your_token_here"

# Option 2: Set directly here (for local development only)
ACCESS_TOKEN: Optional[str] = os.environ.get("CPAS_ACCESS_TOKEN", None)
# ACCESS_TOKEN = "YOUR_ACCESS_TOKEN_HERE"  # Uncomment and set for local dev


# =============================================================================
# Agency Configuration
# =============================================================================

# Your agency's Business Manager ID
AGENCY_BUSINESS_ID: Optional[str] = os.environ.get("CPAS_AGENCY_BM_ID", None)
# AGENCY_BUSINESS_ID = "123456789"  # Uncomment and set

# Default brand to work with
DEFAULT_BRAND_BUSINESS_ID: Optional[str] = os.environ.get("CPAS_BRAND_BM_ID", None)
# DEFAULT_BRAND_BUSINESS_ID = "987654321"  # Uncomment and set

DEFAULT_BRAND_NAME: Optional[str] = os.environ.get("CPAS_BRAND_NAME", None)
# DEFAULT_BRAND_NAME = "My Brand"  # Uncomment and set

# Contact info for collaboration requests
DEFAULT_CONTACT_EMAIL: Optional[str] = os.environ.get("CPAS_CONTACT_EMAIL", None)
# DEFAULT_CONTACT_EMAIL = "contact@agency.com"  # Uncomment and set

DEFAULT_CONTACT_NAME: Optional[str] = os.environ.get("CPAS_CONTACT_NAME", None)
# DEFAULT_CONTACT_NAME = "John Doe"  # Uncomment and set


# =============================================================================
# Merchant Configuration (for Merchant Platform)
# =============================================================================

# Your merchant's Business Manager ID
MERCHANT_BUSINESS_ID: Optional[str] = os.environ.get("CPAS_MERCHANT_BM_ID", None)
# MERCHANT_BUSINESS_ID = "111222333"  # Uncomment and set

MERCHANT_NAME: Optional[str] = os.environ.get("CPAS_MERCHANT_NAME", None)
# MERCHANT_NAME = "My Merchant"  # Uncomment and set


# =============================================================================
# India Merchant Business IDs
# =============================================================================
# Fill in the Business Manager IDs for the merchants you work with
# These are used in the Agency Platform to send collaboration requests

MERCHANT_BM_IDS = {
    "blinkit": os.environ.get("CPAS_BLINKIT_BM_ID", None),
    # "blinkit": "BLINKIT_BM_ID",  # Uncomment and set

    "swiggy": os.environ.get("CPAS_SWIGGY_BM_ID", None),
    # "swiggy": "SWIGGY_BM_ID",  # Uncomment and set

    "zepto": os.environ.get("CPAS_ZEPTO_BM_ID", None),
    # "zepto": "ZEPTO_BM_ID",  # Uncomment and set

    "bigbasket": os.environ.get("CPAS_BIGBASKET_BM_ID", None),
    # "bigbasket": "BIGBASKET_BM_ID",  # Uncomment and set

    "amazon_fresh": os.environ.get("CPAS_AMAZON_FRESH_BM_ID", None),
    # "amazon_fresh": "AMAZON_FRESH_BM_ID",  # Uncomment and set
}


# =============================================================================
# API Settings (usually don't need to change)
# =============================================================================

# Graph API version
API_VERSION: str = "v22.0"

# Default timezone (Asia/Kolkata = 50)
DEFAULT_TIMEZONE_ID: int = 50

# Default currency
DEFAULT_CURRENCY: str = "INR"
