#!/usr/bin/env python3
"""
Scale Good Ads Demo

This script identifies high-performing ads (based on ROAS) and scales them
by duplicating to multiple ad sets specified in a CSV file.
"""

import sys
import os
import time
import csv
import argparse
from datetime import datetime, timedelta

# Add the project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.exceptions import FacebookRequestError

from utils.constants import (
    AD_ACCOUNT_ID as ad_account_id,
    APP_ID as app_id,
    APP_SECRET as app_secret,
)
from utils.test_creds import LL_ACCESS_TOKEN as access_token
from utils.demo_utils import print_and_log

# Configuration
MIN_ROAS_THRESHOLD = 2.5  # Minimum ROAS to consider an ad successful
DEFAULT_LOOKBACK_DAYS = 7  # Default days to look back for performance metrics
DEFAULT_TARGET_ADSETS_FILE = os.path.join(script_dir, "target_adsets.txt")

# Initialize the Facebook API
FacebookAdsApi.init(app_id, app_secret, access_token)
RUN_ID = str(abs(hash(time.time())))[:8]

print_and_log(RUN_ID, "Starting Scale Good Ads Demo.")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Scale high-performing ads to multiple ad sets.")
    parser.add_argument(
        "-r", "--roas", type=float, default=MIN_ROAS_THRESHOLD,
        help=f"Minimum ROAS threshold (default: {MIN_ROAS_THRESHOLD})"
    )
    parser.add_argument(
        "-d", "--days", type=int, default=DEFAULT_LOOKBACK_DAYS,
        help=f"Number of days to look back for performance data (default: {DEFAULT_LOOKBACK_DAYS})"
    )
    parser.add_argument(
        "-f", "--file", type=str, default=DEFAULT_TARGET_ADSETS_FILE,
        help=f"Path to target ad sets CSV file (default: {DEFAULT_TARGET_ADSETS_FILE})"
    )
    parser.add_argument(
        "-n", "--dry-run", action="store_true",
        help="Dry run mode (no actual changes will be made)"
    )
    return parser.parse_args()


def load_target_adsets(file_path):
    """Load target ad sets from a file with line-separated adset IDs."""
    if not os.path.exists(file_path):
        print_and_log(RUN_ID, f"Error: Target ad sets file not found: {file_path}")
        print_and_log(RUN_ID, f"Please create a text file with one adset ID per line")
        return []
    
    target_adsets = []
    try:
        with open(file_path, 'r') as file:
            for line in file:
                adset_id = line.strip()
                if adset_id and not adset_id.startswith('#'):  # Skip empty lines and comments
                    # Fetch adset name if possible
                    adset_name = "Unknown"
                    try:
                        adset = AdSet(adset_id).api_get(fields=['name'])
                        if adset and 'name' in adset:
                            adset_name = adset['name']
                    except:
                        # Continue even if we can't get the name
                        pass
                    
                    target_adsets.append({
                        'id': adset_id,
                        'name': adset_name
                    })
    except Exception as e:
        print_and_log(RUN_ID, f"Error loading target ad sets: {str(e)}")
        return []
    
    print_and_log(RUN_ID, f"Loaded {len(target_adsets)} target ad sets from {file_path}")
    return target_adsets


def get_active_ads():
    """Get all active ads in the account."""
    try:
        account = AdAccount(ad_account_id)
        ads = account.get_ads(params={
            'status': ['ACTIVE'],
            'limit': 1000,
        })
        print_and_log(RUN_ID, f"Found {len(ads)} active ads in account {ad_account_id}")
        return ads
    except FacebookRequestError as e:
        print_and_log(RUN_ID, f"Error fetching ads: {e.api_error_message()}")
        return []


def get_ad_performance(ad_id, days):
    """Get performance metrics for a specific ad over the given time period."""
    try:
        ad = Ad(ad_id)
        today = datetime.now().date()
        since = (today - timedelta(days=days)).strftime('%Y-%m-%d')
        until = today.strftime('%Y-%m-%d')
        
        insights = ad.get_insights(params={
            'date_preset': 'lifetime',
            'time_range': {'since': since, 'until': until},
            'fields': [
                'ad_id',
                'spend',
                'actions',
                'action_values',
                'purchases',
                'cost_per_purchase',
            ],
            'action_attribution_windows': ['28d_click'],
        })
        
        if not insights:
            return None
        
        insight = insights[0]
        spend = float(insight.get('spend', 0))
        
        if spend <= 0:
            return None
            
        # Extract purchase value
        purchase_value = 0
        if 'action_values' in insight:
            for action_value in insight['action_values']:
                if action_value['action_type'] == 'purchase':
                    purchase_value = float(action_value['value'])
                    break
        
        # Calculate ROAS
        roas = purchase_value / spend if spend > 0 else 0
        
        return {
            'ad_id': ad_id,
            'spend': spend,
            'purchase_value': purchase_value,
            'roas': roas
        }
    
    except FacebookRequestError as e:
        print_and_log(RUN_ID, f"Error fetching insights for ad {ad_id}: {e.api_error_message()}")
        return None


def pause_ad(ad_id, dry_run=False):
    """Pause an ad."""
    if dry_run:
        print_and_log(RUN_ID, f"[DRY RUN] Would pause ad {ad_id}")
        return True
    
    try:
        ad = Ad(ad_id)
        ad.api_update(params={'status': 'PAUSED'})
        print_and_log(RUN_ID, f"Successfully paused ad {ad_id}")
        return True
    except FacebookRequestError as e:
        print_and_log(RUN_ID, f"Error pausing ad {ad_id}: {e.api_error_message()}")
        return False


def duplicate_ad_to_adset(ad_id, adset_id, adset_name, dry_run=False):
    """Duplicate an ad to a target ad set using the Ad Copy API."""
    if dry_run:
        print_and_log(RUN_ID, f"[DRY RUN] Would duplicate ad {ad_id} to ad set {adset_id} ({adset_name})")
        return True
    
    try:
        # Use the Ad Copy API to duplicate the ad to the target ad set
        ad = Ad(ad_id)
        
        # Prepare the copy parameters
        copy_params = {
            'adset_id': adset_id,
            'rename_options': {
                'rename_suffix': f" (Scaled to {adset_name})",
            },
            'status_option': Ad.StatusOption.paused,
        }
        
        # Execute the copy operation
        copy_result = ad.create_copy(params=copy_params)
        
        if not copy_result or not copy_result.get('success'):
            print_and_log(RUN_ID, f"Copy operation failed for ad {ad_id} to ad set {adset_id}")
            return False
        
        copied_ads = copy_result.get('copied_ad_ids', [])
        if not copied_ads:
            print_and_log(RUN_ID, f"No ads were copied for ad {ad_id} to ad set {adset_id}")
            return False
        
        print_and_log(RUN_ID, f"Successfully copied ad {ad_id} to ad set {adset_id} ({adset_name}), new ad ID: {copied_ads[0]}")
        return True
        
    except FacebookRequestError as e:
        print_and_log(RUN_ID, f"Error copying ad {ad_id} to ad set {adset_id}: {e.api_error_message()}")
        return False


def main():
    """Main entry point for the script."""
    args = parse_arguments()
    
    # Load target ad sets
    target_adsets = load_target_adsets(args.file)
    if not target_adsets:
        print_and_log(RUN_ID, "No target ad sets found. Exiting.")
        return
    
    # Get active ads
    active_ads = get_active_ads()
    if not active_ads:
        print_and_log(RUN_ID, "No active ads found. Exiting.")
        return
    
    print_and_log(RUN_ID, f"Checking {len(active_ads)} active ads for performance metrics...")
    
    # Check performance of each ad
    high_performing_ads = []
    for ad in active_ads:
        performance = get_ad_performance(ad['id'], args.days)
        if performance and performance['roas'] >= args.roas:
            high_performing_ads.append({
                'ad_id': ad['id'],
                'name': ad.get('name', 'Unknown'),
                'roas': performance['roas'],
            })
    
    print_and_log(RUN_ID, f"Found {len(high_performing_ads)} ads with ROAS greater than {args.roas}")
    
    # Scale high-performing ads
    for ad in high_performing_ads:
        print_and_log(RUN_ID, f"Scaling ad {ad['ad_id']} ({ad['name']}) with ROAS {ad['roas']:.2f} to {len(target_adsets)} target ad sets...")
        
        # Duplicate ad to each target ad set
        success_count = 0
        for adset in target_adsets:
            if duplicate_ad_to_adset(ad['ad_id'], adset['id'], adset['name'], args.dry_run):
                success_count += 1
        
        # Pause the original ad after successful duplication
        if success_count > 0:
            if pause_ad(ad['ad_id'], args.dry_run):
                print_and_log(RUN_ID, f"Original ad {ad['ad_id']} has been paused")
            else:
                print_and_log(RUN_ID, f"Failed to pause original ad {ad['ad_id']}")
    
    print_and_log(RUN_ID, "Scale Good Ads Demo completed.")


if __name__ == "__main__":
    main()