#!/usr/bin/env python3
"""
Ad Duplication Demo

This script demonstrates how to duplicate a specific ad to a target ad set
using the Ad Copy API.
"""

import sys
import os
import argparse

# Add the project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adset import AdSet
from facebook_business.exceptions import FacebookRequestError

from utils.constants import (
    AD_ACCOUNT_ID as ad_account_id,
    APP_ID as app_id,
    APP_SECRET as app_secret,
)
from utils.test_creds import LL_ACCESS_TOKEN as access_token

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Duplicate an ad to a target ad set.")
    parser.add_argument("ad_id", help="ID of the ad to duplicate")
    parser.add_argument("adset_id", help="ID of the target ad set")
    parser.add_argument("--suffix", default="(Copy)", help="Suffix to add to the copied ad name")
    parser.add_argument("--status", choices=["active", "paused"], default="active", 
                       help="Status for the duplicated ad (active or paused)")
    return parser.parse_args()

def duplicate_ad(ad_id, adset_id, suffix="(Copy)", status="active"):
    """Duplicate an ad to a target ad set using the Ad Copy API."""
    # Initialize the Facebook API
    FacebookAdsApi.init(app_id, app_secret, access_token)
    
    try:
        # Get ad and adset names for better logging
        ad = Ad(ad_id)
        ad_details = ad.api_get(fields=['name'])
        ad_name = ad_details.get('name', ad_id)
        
        adset = AdSet(adset_id)
        adset_details = adset.api_get(fields=['name'])
        adset_name = adset_details.get('name', adset_id)
        
        print(f"Duplicating ad '{ad_name}' to ad set '{adset_name}'...")
        
        # Prepare the copy parameters
        copy_params = {
            'adset_id': adset_id,
            'rename_options': {
                'rename_suffix': f" {suffix}",
            },
            'status_option': Ad.StatusOption.active if status == "active" else Ad.StatusOption.paused,
        }
        
        # Execute the copy operation
        copy_result = ad.create_copy(params=copy_params)
        
        if not copy_result or not copy_result.get('success'):
            print(f"Copy operation failed: {copy_result}")
            return False
        
        copied_ads = copy_result.get('copied_ad_ids', [])
        if not copied_ads:
            print("No ads were copied")
            return False
        
        print(f"Successfully copied ad to ad set '{adset_name}'")
        print(f"New ad ID: {copied_ads[0]}")
        return True
        
    except FacebookRequestError as e:
        print(f"Error copying ad: {e.api_error_message()}")
        return False

if __name__ == "__main__":
    args = parse_arguments()
    duplicate_ad(args.ad_id, args.adset_id, args.suffix, args.status)