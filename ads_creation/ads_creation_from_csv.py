"""
This script creates ads from a CSV file. For the example CSV file, the output structure is:
- Campaign 1: 1-1-1
- Campaign 2: 1-n-1
- Campaign 3: 1-1-n
- Campaign 4: 1-2-*
"""

import csv
import sys
import time

sys.path.append(
    "/opt/homebrew/lib/python2.7/site-packages"
)  # Replace this with the place you installed facebookads using pip
sys.path.append(
    "/opt/homebrew/lib/python2.7/site-packages/facebook_business-3.0.0-py2.7.egg-info"
)  # same as above

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

print_and_log(RUN_ID, "Ad setup from csv beginning.")


# Read the CSV file and build the hierarchy
hierarchy = {}
with open("demo_input.csv", mode="r") as file:
    reader = csv.DictReader(file)
    for row in reader:
        obj_type = row["type"]
        identifier = row["identifier"]
        name = row["name"]
        parent_identifier = row["parent_identifier"]

        if obj_type == "CAMPAIGN":
            hierarchy[identifier] = {"name": name, "adsets": {}}
        elif obj_type == "ADSET":
            hierarchy[parent_identifier]["adsets"][identifier] = {
                "name": name,
                "ads": [],
            }
        elif obj_type == "AD":
            for campaign in hierarchy.values():
                if parent_identifier in campaign["adsets"]:
                    campaign["adsets"][parent_identifier]["ads"].append(name)

# Create campaigns, ad sets, and ads based on the hierarchy
for campaign_id, campaign_data in hierarchy.items():
    campaign_params = {
        Campaign.Field.name: campaign_data["name"],
        Campaign.Field.objective: Campaign.Objective.outcome_sales,
        Campaign.Field.status: "PAUSED",
        Campaign.Field.special_ad_categories: [],
    }

    campaign = AdAccount(ad_account_id).create_campaign(
        fields=[],
        params=campaign_params,
    )
    print_and_log(RUN_ID, f"Campaign {campaign.get_id()} created.")

    for adset_id, adset_data in campaign_data["adsets"].items():
        adset_params = {
            AdSet.Field.name: adset_data["name"],
            AdSet.Field.campaign_id: campaign.get_id(),
            AdSet.Field.daily_budget: 100,
            AdSet.Field.billing_event: AdSet.BillingEvent.impressions,
            AdSet.Field.optimization_goal: AdSet.OptimizationGoal.reach,
            AdSet.Field.bid_strategy: AdSet.BidStrategy.lowest_cost_without_cap,
            AdSet.Field.targeting: {
                "geo_locations": {
                    "countries": ["US"],
                },
            },
            AdSet.Field.status: AdSet.Status.paused,
        }
        ad_set = AdAccount(ad_account_id).create_ad_set(
            fields=[],
            params=adset_params,
        )
        adset_id = ad_set.get_id()
        print_and_log(RUN_ID, f"Ad set {adset_id} created.")

        for ad_name in adset_data["ads"]:
            creative_params = {
                AdCreative.Field.name: ad_name,
                AdCreative.Field.object_story_spec: {
                    "page_id": page_id,
                    "link_data": {
                        "image_hash": "bf6823a7c358936b7a99e9a2efc78fc6",
                        "link": "https://scontent-sjc3-1.xx.fbcdn.net/v/t45.1600-4/474708412_120216956652780558_5968519555980627928_n.png?stp=dst-jpg_tt6&_nc_cat=101&ccb=1-7&_nc_sid=890911&_nc_ohc=_5CLqLZ2zn0Q7kNvgHHQCrj&_nc_zt=1&_nc_ht=scontent",
                        "message": "Check out our website!",
                    },
                },
                AdCreative.Field.degrees_of_freedom_spec: {
                    "creative_features_spec": {
                        "standard_enhancements": {"enroll_status": "OPT_IN"}
                    }
                },
            }
            creative = AdAccount(ad_account_id).create_ad_creative(
                fields=[],
                params=creative_params,
            )
            print_and_log(RUN_ID, f"Creative {creative.get_id()} created.")

            params = {
                Ad.Field.name: ad_name,
                Ad.Field.adset_id: ad_set.get_id(),
                Ad.Field.creative: {
                    "creative_id": creative.get_id(),
                },
                Ad.Field.status: Ad.Status.paused,
            }
            ad = AdAccount(ad_account_id).create_ad(
                fields=[],
                params=params,
            )
            print_and_log(RUN_ID, f"Ad {ad.get_id()} created.")

print_and_log(RUN_ID, "Ad setup from csv complete")
