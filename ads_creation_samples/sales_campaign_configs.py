"""
This script demonstrates common configurations for sales campaigns that advertisers typically want to control.
It reads campaign configurations from a CSV file and creates campaigns accordingly.
"""

import csv
import sys
import time

sys.path.append(
    "/opt/homebrew/lib/python2.7/site-packages"
)
sys.path.append(
    "/opt/homebrew/lib/python2.7/site-packages/facebook_business-3.0.0-py2.7.egg-info"
)

from constants import (
    AD_ACCOUNT_ID as ad_account_id,
    APP_ID as app_id,
    APP_SECRET as app_secret,
    PAGE_ID as page_id,
)
from demo_utils import print_and_log
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.campaign import Campaign
from facebook_business.api import FacebookAdsApi
from test_creds import LL_ACCESS_TOKEN as access_token

# Initialize the Facebook API
FacebookAdsApi.init(app_id, app_secret, access_token)

RUN_ID = str(abs(hash(time.time())))[:8]

print_and_log(RUN_ID, "Sales campaign configuration demo beginning.")

def create_campaign_from_config(config):
    """Create a campaign, ad set, creative, and ad from a configuration dictionary."""
    
    # 1. Campaign Configuration
    campaign_params = {
        Campaign.Field.name: f"{config['campaign_name']} {RUN_ID}",
        Campaign.Field.objective: Campaign.Objective.outcome_sales,
        Campaign.Field.status: Campaign.Status.paused,
        Campaign.Field.special_ad_categories: [],
        Campaign.Field.promoted_object: {
            "pixel_id": config['pixel_id'],
            "custom_event_type": "PURCHASE",
        },
    }

    campaign = AdAccount(ad_account_id).create_campaign(
        fields=[],
        params=campaign_params,
    )
    print_and_log(RUN_ID, f"Campaign {campaign.get_id()} created.")

    # 2. Ad Set Configuration
    adset_params = {
        AdSet.Field.name: f"Ad Set for {config['campaign_name']} {RUN_ID}",
        AdSet.Field.campaign_id: campaign.get_id(),
        AdSet.Field.daily_budget: int(config['daily_budget']),
        AdSet.Field.billing_event: AdSet.BillingEvent.impressions,
        AdSet.Field.optimization_goal: AdSet.OptimizationGoal.conversion,
        AdSet.Field.bid_strategy: AdSet.BidStrategy.lowest_cost_without_cap,
        AdSet.Field.targeting: {
            "geo_locations": {
                "countries": [config['country']],
            },
            "age_min": int(config['age_min']),
            "age_max": int(config['age_max']),
            "genders": [int(config['gender'])],  # 1 for female, 2 for male
            "device_platforms": ["mobile", "desktop"],
            "facebook_positions": ["feed", "right_hand_column"],
            "instagram_positions": ["stream"],
        },
        AdSet.Field.optimization_sub_event: "PURCHASE",
        AdSet.Field.pacing_type: ["standard"],
        AdSet.Field.status: AdSet.Status.paused,
    }

    ad_set = AdAccount(ad_account_id).create_ad_set(
        fields=[],
        params=adset_params,
    )
    print_and_log(RUN_ID, f"Ad set {ad_set.get_id()} created.")

    # 3. Creative Configuration
    creative_params = {
        AdCreative.Field.name: f"Creative for {config['campaign_name']} {RUN_ID}",
        AdCreative.Field.object_story_spec: {
            "page_id": config['page_id'],
            "link_data": {
                "image_hash": config['image_hash'],
                "link": config['product_link'],
                "message": config['message'],
                "call_to_action": {
                    "type": "SHOP_NOW",
                },
            },
        },
        AdCreative.Field.dynamic_ad_voice: "active",
        AdCreative.Field.use_page_actor_override: True,
        AdCreative.Field.degrees_of_freedom_spec: {
            "creative_features_spec": {
                "standard_enhancements": {"enroll_status": "OPT_IN"},
                "use_standard_enhancements": True,
            },
        },
    }

    creative = AdAccount(ad_account_id).create_ad_creative(
        fields=[],
        params=creative_params,
    )
    print_and_log(RUN_ID, f"Creative {creative.get_id()} created.")

    # 4. Ad Configuration
    ad_params = {
        Ad.Field.name: f"Ad for {config['campaign_name']} {RUN_ID}",
        Ad.Field.adset_id: ad_set.get_id(),
        Ad.Field.creative: {
            "creative_id": creative.get_id(),
        },
        Ad.Field.tracking_specs: [
            {
                "action.type": ["offsite_conversion"],
                "offsite_pixel": config['pixel_id'],
            }
        ],
        Ad.Field.conversion_domain: config['conversion_domain'],
        Ad.Field.conversion_specs: [
            {
                "action.type": ["offsite_conversion"],
                "offsite_pixel": config['pixel_id'],
            }
        ],
        Ad.Field.status: Ad.Status.paused,
        Ad.Field.priority: 1,
    }

    ad = AdAccount(ad_account_id).create_ad(
        fields=[],
        params=ad_params,
    )
    print_and_log(RUN_ID, f"Ad {ad.get_id()} created.")

# Read configurations from CSV and create campaigns
with open("campaign_configs.csv", mode="r") as file:
    reader = csv.DictReader(file)
    for config in reader:
        try:
            create_campaign_from_config(config)
        except Exception as e:
            print_and_log(RUN_ID, f"Error creating campaign {config['campaign_name']}: {str(e)}")

print_and_log(RUN_ID, "Sales campaign configuration demo complete.") 