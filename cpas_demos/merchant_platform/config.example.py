"""
Merchant Platform Configuration

Copy this file to config.py and fill in your actual values.
DO NOT commit config.py with real credentials to version control.

Usage:
  cp config.example.py config.py
  # Edit config.py with your values
"""

import os
from typing import Optional


# =============================================================================
# Access Token
# =============================================================================
# Option 1: Set via environment variable (recommended for production)
# export CPAS_ACCESS_TOKEN="your_token_here"

# Option 2: Set directly here (for local development only)
ACCESS_TOKEN: Optional[str] = os.environ.get("CPAS_ACCESS_TOKEN", None)
# ACCESS_TOKEN = "YOUR_ACCESS_TOKEN_HERE"  # Uncomment and set for local dev


# =============================================================================
# Merchant Configuration
# =============================================================================

# Your merchant's Business Manager ID
MERCHANT_BUSINESS_ID: Optional[str] = os.environ.get("CPAS_MERCHANT_BM_ID", None)
# MERCHANT_BUSINESS_ID = "111222333"  # Uncomment and set
